"""Inactive coordinated terrain/building-family candidate from cached originals.

Contract: full original DEM lookup, rendered Ground clipped to its original XY
extent; original Context clipped only out of that extent. Buildings preserve
rigid shape/relative roof heights per connected source component. Historical
source-frame translations propagate to appearance/tower members. No activation,
acquisition, editor, API, camera or lighting writes. Outputs require fresh ignored
folder. See generated README/report; independent review remains mandatory.
"""
from pathlib import Path
import os,sys,json,argparse,hashlib
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import Polygon,MultiPoint,Point
from shapely.ops import unary_union
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
from acquire_dem import inspect_tile,parse_metadata,paste_tile
from anchor_terrain_proposal import GroundSampler
from build_terrain_proposal import coarse_mesh
from prepare_church_legacy_mask import author as clip_original_surface

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class TerrainSurfaceSampler:
    """Sample the final serialized TRIANGULATED render ground, not the DEM.

    Public points/triangles/triangle_polygons/tree are available for exact surface
    clipping by coordinated roads/detail builders. XY/Z are project meters.
    """
    def __init__(self,points,triangles):
        self.points=np.asarray(points,dtype=float);self.triangles=np.asarray(triangles,dtype=int)
        self.triangle_polygons=shapely.polygons(self.points[self.triangles,:2])
        self.tree=shapely.STRtree(self.triangle_polygons)
    @classmethod
    def from_npz(cls,path):
        with np.load(path,allow_pickle=False) as a:return cls(a['points'],a['triangles'])
    def sample(self,xy):
        xy=np.asarray(xy,dtype=float).reshape(-1,2);out=np.full(len(xy),np.nan)
        if not len(xy):return out
        pairs=self.tree.query(shapely.points(xy),predicate='intersects')
        if pairs.shape[1]:
            pi,ti=pairs;v=self.points[self.triangles[ti]];p=xy[pi];a=v[:,0,:2];b=v[:,1,:2]-a;c=v[:,2,:2]-a;d=p-a
            den=b[:,0]*c[:,1]-b[:,1]*c[:,0]
            u=(d[:,0]*c[:,1]-d[:,1]*c[:,0])/den;w=(b[:,0]*d[:,1]-b[:,1]*d[:,0])/den
            values=v[:,0,2]+u*(v[:,1,2]-v[:,0,2])+w*(v[:,2,2]-v[:,0,2]);out[pi]=values
        if not np.isfinite(out).all():raise ValueError('outside_final_rendered_ground')
        return out

def load_dem(root,deps):
    config_path=root/'config/terrain_sources.json';config=json.loads(config_path.read_text());deps['config/terrain_sources.json']=sha(config_path)
    rows=[]
    for tile in config['tiles']:
        p=root/'data/heights/dem'/(tile['id']+'.tif');xml=p.with_suffix('.xml')
        for source in (p,xml):
            receipt=Path(str(source)+'.source.json');deps[receipt.relative_to(root).as_posix()]=sha(receipt)
            evidence=json.loads(receipt.read_text())
            if sha(source)!=evidence['sha256']:raise ValueError('DEM source bytes changed')
            deps[source.relative_to(root).as_posix()]=evidence['sha256']
        info,values,valid=inspect_tile(p,parse_metadata(xml),config);rows.append((info,values,valid))
    left=min(r[0]['source_bounds_ft'][0] for r in rows);right=max(r[0]['source_bounds_ft'][2] for r in rows)
    top=max(r[0]['source_bounds_ft'][3] for r in rows);bottom=min(r[0]['source_bounds_ft'][1] for r in rows);step=rows[0][0]['pixel_scale_source_ft'][0]
    grid={'left_ft':left,'top_ft':top,'width':round((right-left)/step),'height':round((top-bottom)/step),'pixel_size_ft':step,'horizontal_epsg':6438}
    values=np.full((grid['height'],grid['width']),np.nan,np.float32);covered=np.zeros(values.shape,bool)
    for info,tile,valid in rows:paste_tile(values,covered,grid,info,tile,valid)
    origin=json.loads((root/'config/study_area.json').read_text())['local_origin_wgs84'];deps['config/study_area.json']=sha(root/'config/study_area.json')
    return GroundSampler(values,grid,origin,z_origin=30.),grid,origin

def meshes(prim):
    return [p for p in Usd.PrimRange(prim,Usd.TraverseInstanceProxies()) if p.GetTypeName()=='Mesh']

def world_points(prim,cache):
    p=UsdGeom.Mesh(prim).GetPointsAttr().Get();m=cache.GetLocalToWorldTransform(prim)
    return np.array([m.Transform(v) for v in p],float)

def projection(prim,cache):
    v=world_points(prim,cache);m=UsdGeom.Mesh(prim);indices=m.GetFaceVertexIndicesAttr().Get();counts=m.GetFaceVertexCountsAttr().Get();polys=[];off=0
    for n in counts:
        p=Polygon(v[np.array(indices[off:off+n]),:2]);off+=n
        if p.is_valid and p.area>1e-7:polys.append(p)
    return unary_union(polys)

def parts(geometry):
    if geometry.geom_type=='Polygon':return [geometry]
    return [p for p in geometry.geoms if p.geom_type=='Polygon' and p.area>.00001]

def make_ground(source,sampler,grid,origin,cache):
    prim=source.GetPrimAtPath('/World/Ground');outline=projection(prim,cache)
    coords=np.array(outline.exterior.coords);x,y=sampler.to_source.transform(coords[:,0]+sampler.origin[0],coords[:,1]+sampler.origin[1]);step=grid['pixel_size_ft']
    c0=max(0,int(np.floor((min(x)-grid['left_ft'])/step))-16);c1=min(grid['width'],int(np.ceil((max(x)-grid['left_ft'])/step))+17)
    r0=max(0,int(np.floor((grid['top_ft']-max(y))/step))-16);r1=min(grid['height'],int(np.ceil((grid['top_ft']-min(y))/step))+17)
    render_grid={**grid,'left_ft':grid['left_ft']+c0*step,'top_ft':grid['top_ft']-r0*step,'width':c1-c0,'height':r1-r0}
    v,q,metrics=coarse_mesh(sampler.values[r0:r1,c0:c1],np.isfinite(sampler.values[r0:r1,c0:c1]),render_grid,origin,stride=8,z_origin_m=30.)
    tri=np.concatenate([q[:,[0,1,2]],q[:,[0,2,3]]]);polys=shapely.polygons(v[tri,:2]);hit=shapely.intersects(polys,outline);tri=tri[hit];polys=polys[hit]
    inside=shapely.covered_by(polys,outline);faces=tri[inside].tolist();vertices=v[:,:2].astype(float).tolist();lookup={tuple(np.round(p,5)):i for i,p in enumerate(vertices)};dropped=0.
    for poly in polys[~inside]:
        clipped=poly.intersection(outline)
        for piece in shapely.constrained_delaunay_triangles(clipped).geoms:
            if piece.area<.0001:dropped+=piece.area;continue
            xy=np.array(piece.exterior.coords)[:3];a,b=xy[1]-xy[0],xy[2]-xy[0]
            if a[0]*b[1]-a[1]*b[0]<0:xy=xy[::-1]
            f=[]
            for point in xy:
                key=tuple(np.round(point,5))
                if key not in lookup:lookup[key]=len(vertices);vertices.append(point.tolist())
                f.append(lookup[key])
            faces.append(f)
    faces=np.array(faces);used,inverse=np.unique(faces,return_inverse=True);xy=np.array(vertices)[used];z=sampler.sample(xy)
    points=np.c_[xy,z].astype(np.float32);triangles=inverse.reshape(-1,3)
    # UV transform fitted to ORIGINAL ground face coordinates preserves texture
    # scale instead of silently switching the existing grass material's scale.
    mesh=UsdGeom.Mesh(prim);raw=world_points(prim,cache);indices=np.array(mesh.GetFaceVertexIndicesAttr().Get());uv=UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st').ComputeFlattened();A=np.c_[raw[indices,:2],np.ones(len(indices))]
    fit=np.linalg.lstsq(A,np.array(uv),rcond=None)[0]
    if abs(A@fit-np.array(uv)).max()>.0001:raise ValueError('Original ground UV is not one affine map')
    uv=np.c_[points[:,:2],np.ones(len(points))]@fit
    metrics.update(accepted_extent_area_m2=outline.area,explicit_triangles=len(triangles),vertices=len(points),boundary_sliver_area_omitted_m2=dropped,
        render_extent_policy='Original composed Ground XY projection only; fullcachedlookup is NOT expandedrenderextent',uv_source_affine_fit_residual=float(abs(A@fit-np.array(UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st').ComputeFlattened())).max()))
    return points,triangles,uv,outline,metrics

def build(output,root=ROOT):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Fresh diagnostic output required')
    output.mkdir(parents=True);output.joinpath('captured_helper.py').write_bytes(Path(__file__).read_bytes());frozen=sha(Path(__file__))
    deps={'tools/prepare_terrain_buildings.py':frozen}
    for p in ['tools/acquire_dem.py','tools/anchor_terrain_proposal.py','tools/build_terrain_proposal.py','tools/prepare_church_legacy_mask.py','config/study_area.json','data/processed/active.json','data/processed/reconstructions.json']:
        deps[p]=sha(root/p)
    protected=[p for p in ['scene/college_park_connected.usda','scene/manual_edits.usda','data/processed/active.json','scene/church_historical.usda','scene/church_southeast_wing.usda','scene/landmark_buildings.usda','scene/post_office_historical.usda','scene/campus_hardscape.usda'] if (root/p).is_file()]
    before={p:sha(root/p) for p in protected};deps.update(before)
    source=Usd.Stage.Open(str(root/'scene/college_park_connected.usda'));cache=UsdGeom.XformCache()
    for layer in source.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath).resolve()
            if p.is_relative_to(root):deps[p.relative_to(root).as_posix()]=sha(p)
    sampler,grid,origin=load_dem(root,deps)
    points,triangles,uv,outline,ground_metrics=make_ground(source,sampler,grid,origin,cache)
    np.savez_compressed(output/'ground_surface.npz',points=points,triangles=triangles)
    field={'schema':'twin.final-ground-surface/1','source_snapshot':json.loads((root/'data/processed/active.json').read_text())['snapshot'],
        'npz':(output/'ground_surface.npz').relative_to(root).as_posix(),'sha256':sha(output/'ground_surface.npz'),
        'units':'meters','up_axis':'Z','scene_z_origin_navd88_m':30.,'rule':'barycentric height on these final serialized triangles, not separate bilinear DEM',
        'sampler_class':'tools.prepare_terrain_buildings.TerrainSurfaceSampler','metrics':ground_metrics}
    (output/'ground_field.json').write_text(json.dumps(field,indent=2),encoding='utf-8')
    print(json.dumps({'ground_field_ready':field['npz'],'sha256':field['sha256']}),flush=True)
    rendered=TerrainSurfaceSampler(points,triangles)
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1.)
    g=UsdGeom.Mesh(stage.OverridePrim('/World/Ground'));inverse=cache.GetLocalToWorldTransform(source.GetPrimAtPath('/World/Ground')).GetInverse()
    g.CreatePointsAttr([inverse.Transform(Gf.Vec3d(*map(float,p))) for p in points]);g.CreateFaceVertexCountsAttr([3]*len(triangles));g.CreateFaceVertexIndicesAttr(triangles.reshape(-1).tolist());g.CreateSubdivisionSchemeAttr('none');g.CreateNormalsAttr().Block()
    var=UsdGeom.PrimvarsAPI(g).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'vertex');var.Set(uv.tolist());var.CreateIndicesAttr().Block()
    g.CreateExtentAttr([Gf.Vec3f(*map(float,points.min(0))),Gf.Vec3f(*map(float,points.max(0)))])
    applied=[{'path':'/World/Ground','policy':'Original XY extent retained; points/topology/UV replaced by historical explicittriangleground; visibility unchanged'}];held=[];families=[];contacts=[]
    context=source.GetPrimAtPath('/World/Context/SurroundingGround')
    if context and cache.GetLocalToWorldTransform(context)==Gf.Matrix4d(1):
        original=projection(context,cache);proof=clip_original_surface(stage,context,outline)
        applied.append({'path':str(context.GetPath()),'policy':'Exact original flatContext surfaces removed ONLY inside acceptedGround; no visibilitytoggle',
            'masked_projection_m2':original.intersection(outline).area,'retained_outer_projection_m2':original.difference(outline).area})
        held.append({'path':str(context.GetPath()),'policy':'Outer Context outsideacceptedGround staysschematicflat; E/south exceedsoriginalcache; outerterrainseams unresolved','partial':True})
    else:held.append({'path':'/World/Context','policy':'Transform/source requires explicit reconciliation; potentialocclusion unresolved'})
    def translate(path,delta,policy,family):
        p=source.GetPrimAtPath(path)
        if not p:return
        if UsdGeom.Imageable(p).ComputeVisibility()=='invisible':held.append({'path':path,'policy':'Source hidden; visibility unchanged','family':family});return
        xf=UsdGeom.Xformable(p)
        if not xf:
            children=[child for child in p.GetChildren() if UsdGeom.Xformable(child) or meshes(child)]
            if children:
                for child in children:translate(str(child.GetPath()),delta,policy+'; inheritedthroughuntypedcontainer',family)
                return
            held.append({'path':path,'policy':'Nongeometric/untyped familymember unchanged','family':family});return
        if any('terrainAnchor' in str(op.GetOpName()) for op in xf.GetOrderedXformOps()):raise ValueError('Existing terrainanchor cannot be appliedtwice')
        target=UsdGeom.Xformable(stage.OverridePrim(path));op=target.AddTranslateOp(opSuffix='terrainAnchor')
        # Least-local translation BEFORE original ops (after reset token).
        # Only the effective parent frame transforms this new translation;
        # rotation/scale of the original prim must not alter its world-Z delta.
        parent_matrix=Gf.Matrix4d(1) if xf.GetResetXformStack() else cache.GetLocalToWorldTransform(p.GetParent())
        local=parent_matrix.GetInverse().TransformDir(Gf.Vec3d(0,0,float(delta)));op.Set(local)
        target.SetXformOpOrder([op]+list(xf.GetOrderedXformOps()),xf.GetResetXformStack())
        applied.append({'path':path,'policy':policy,'delta_z_m':delta,'family':family})
    # Recover explicit historical source-frame origins from accepted records.
    registry=json.loads((root/'data/processed/reconstructions.json').read_text());known={}
    for record in registry['records']:
        ground=[float(c[k]) for c in record.get('components',[]) for k in ['ground_m','ground_z_m'] if isinstance(c.get(k),(int,float))]
        if ground and max(ground)-min(ground)<.0001:known[record['id']]=ground[0]
    for p in ['data/heights/retail_edgewater/verification.json','data/heights/final_omissions/activation.json','data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3/manifest.json']:
        deps[p]=sha(root/p)
    known['edgewater_retail_1305_1319']=json.loads((root/'data/heights/retail_edgewater/verification.json').read_text())['ground_reference_navd88_m']
    for site in json.loads((root/'data/heights/final_omissions/activation.json').read_text())['sites']:known[site['site_id']]=site['ground_reference_navd88_m']
    church_ground=json.loads((root/'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3/manifest.json').read_text())['ground_navd88_m']
    known['church_on_drive_sanctuary']=known['church_southeast_wing_existing_2892_correction']=church_ground
    family_deltas={}
    for record in registry['records']:
        id=record['id'];path=record.get('usd_path')
        if not path:continue
        if id not in known:held.append({'path':path,'policy':'Historicalsourceorigin missing; no naivebaseanchor','family':id});continue
        delta=known[id]-30.;members=[path]
        if id=='andersen_office_1615':members+=['/World/OfficeFrontageProposal','/World/OfficeFrontageDetail']
        if id=='church_on_drive_sanctuary':members+=['/World/Landmarks/ChurchOnDriveSteepleCandidate','/World/ChurchFrontageAppearance','/World/ChurchBelfryAppearance']
        for member in members:translate(member,delta,'Historicalsourceframe conversion only, no secondDEMbase offset',id)
        families.append({'id':id,'familymembers':members,'delta_z_m':delta,'frame':'sourceNAVD88 minus30m sceneorigin; existingdisplayoffset preserved','source_ground_reference_navd88_m':known[id],
            'policy':'Absolute historicalframe preserved; originalroofshape/relativeheight/appearance inheritance; notsurveyedfoundationcontact'})
        family_deltas[id]=delta
    raw_part_mapping={}
    def hold_pair(path,roof,policy,**detail):
        for member in [path]+([str(roof.GetPath())] if roof else []):held.append({'path':member,'policy':policy,**detail})
    for prim in source.GetPrimAtPath('/World/Buildings').GetChildren():
        path=str(prim.GetPath());number=prim.GetName().split('_')[-1];roof=source.GetPrimAtPath('/World/Roofs/Roof_'+number)
        if prim.GetTypeName()!='Mesh' or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':hold_pair(path,roof,'Source hidden/nonmesh unchanged');continue
        d=prim.GetCustomData();h=d.get('height',{});sourceground=h.get('nearby_ground_elevation_m')
        if prim.GetName()=='Building_2892':sourceground=church_ground
        if isinstance(sourceground,(float,int)):
            delta=float(sourceground)-30.;family='source_frame:'+prim.GetName()
            for target in [prim]+([roof] if roof else []):translate(str(target.GetPath()),delta,'Sourceground/NAVD88frame preserved; no independentDEMdoubleanchor',family)
            raw_part_mapping[prim.GetName()]=[{'geometry':projection(prim,cache),'delta':delta}]
            families.append({'id':family,'familymembers':[path]+([str(roof.GetPath())] if roof else []),'delta_z_m':delta,'source_ground_reference_navd88_m':sourceground,'frame':'sourceNAVD88minus30','policy':'Source-frame group, relativeheight unchanged'})
            continue
        geometry=projection(prim,cache);polygons=parts(geometry);v=world_points(prim,cache);units=[]
        # Source faces define immutable geometric coupling. Merge projected
        # islands linked by an original face instead of warping that face or
        # pretending the islands are independent physical buildings.
        if len(polygons)>1:
            parent=list(range(len(polygons)));failure=None
            def find(i):
                while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
                return i
            for target in [prim]+([roof] if roof else []):
                q=world_points(target,cache);dist=np.array([shapely.distance(shapely.points(q[:,:2]),p) for p in polygons]);labels=dist.argmin(0)
                if dist.min(0).max()>.005:failure='Pairedroof/sourcevertexoutsideexactcomponentassignment';break
                counts=UsdGeom.Mesh(target).GetFaceVertexCountsAttr().Get();idx=np.array(UsdGeom.Mesh(target).GetFaceVertexIndicesAttr().Get());off=0
                for n in counts:
                    linked=set(labels[idx[off:off+n]]);off+=n
                    first=min(linked)
                    for other in linked:parent[find(int(other))]=find(int(first))
            if failure:hold_pair(path,roof,failure,multipart_components=len(polygons));continue
            coupled={}
            for i,p in enumerate(polygons):coupled.setdefault(find(i),[]).append(p)
            polygons=[unary_union(p) for p in coupled.values()]
        for i,polygon in enumerate(polygons):
            base=polygon.representative_point()
            try:
                target=float(rendered.sample([[base.x,base.y]])[0]);boundary=np.concatenate([np.array(p.exterior.coords) for p in parts(polygon)]);z=rendered.sample(boundary)
            except ValueError as error:hold_pair(path,roof,str(error),component=i);units=[];break
            dist=shapely.distance(shapely.points(v[:,:2]),polygon);minz=float(v[dist<.001,2].min())
            delta=target+.1-minz;units.append({'geometry':polygon,'delta':delta})
            contacts.append({'path':path,'component':i,'policy':'Rigidcomponent atinside-footprintrepresentativepoint; notfoundationmodel',
                'delta_z_m':delta,'base_ground_relief_m':float(np.ptp(z)),'base_clearance_boundary_minmax_m':[float(target+.1-z.max()),float(target+.1-z.min())]})
        if not units:continue
        if len(units)==1:
            for target in [prim]+([roof] if roof else []):translate(str(target.GetPath()),units[0]['delta'],'Rigidactualconnectedfootprint base onfinalrenderground; roofpaired',prim.GetName())
        else:
            # Per-component rigid translations, not a single campus hull offset.
            # Require every source face to stay within one component; otherwise
            # hold the complete group instead of warping a cross-component face.
            pending=[];failure=None
            for target in [prim]+([roof] if roof else []):
                if target.GetChildren():failure='Multipartgroupwithchildren requires acceptedchildmembership';break
                q=world_points(target,cache);dist=np.array([shapely.distance(shapely.points(q[:,:2]),u['geometry']) for u in units]);assignment=dist.argmin(0)
                if dist.min(0).max()>.005:failure='Pairedroof/sourcevertexoutsideexactcomponentassignment';break
                mesh=UsdGeom.Mesh(target);counts=mesh.GetFaceVertexCountsAttr().Get();indices=np.array(mesh.GetFaceVertexIndicesAttr().Get());off=0
                for n in counts:
                    if len(set(assignment[indices[off:off+n]]))!=1:failure='Sourceface spansdisconnectedcomponents';break
                    off+=n
                if failure:break
                shifted=q.copy();shifted[:,2]+=np.array([u['delta'] for u in units])[assignment]
                inv=cache.GetLocalToWorldTransform(target).GetInverse();local=[inv.Transform(Gf.Vec3d(*p)) for p in shifted];pending.append((target,local))
            if failure:hold_pair(path,roof,failure,multipart_components=len(units));continue
            for target,local in pending:
                mesh=UsdGeom.Mesh(stage.OverridePrim(target.GetPath()));mesh.CreatePointsAttr(local)
                bounds=np.asarray(local,dtype=float)
                mesh.CreateExtentAttr([Gf.Vec3f(*map(float,bounds.min(0))),Gf.Vec3f(*map(float,bounds.max(0)))])
                applied.append({'path':str(target.GetPath()),'policy':'Exactsourcefaces preserved, eachconnectedcomponent shiftedrigidly withpairedroof','component_deltas_z_m':[u['delta'] for u in units]})
        raw_part_mapping[prim.GetName()]=units
    storefront=source.GetPrimAtPath('/World/Storefronts')
    for group in storefront.GetChildren():
        units=raw_part_mapping.get(group.GetName())
        if not units:held.append({'path':str(group.GetPath()),'policy':'No acceptedsource-building anchor mapping; sourcevisibility unchanged'});continue
        if len(units)==1:translate(str(group.GetPath()),units[0]['delta'],'Inherits sourcebuilding anchor, not independentdetailminZ',group.GetName());continue
        for front in group.GetChildren():
            mm=[p for p in meshes(front) if UsdGeom.Imageable(p).ComputeVisibility()!='invisible']
            if not mm:held.append({'path':str(front.GetPath()),'policy':'Hidden/nongeometry detail unchanged'});continue
            q=np.concatenate([world_points(p,cache) for p in mm]);center=MultiPoint(q[:,:2]).convex_hull.representative_point();dist=np.array([center.distance(u['geometry']) for u in units]);index=int(dist.argmin())
            if dist[index]>3.:held.append({'path':str(front.GetPath()),'policy':'Multipartdetail component association beyond3m, unresolved'});continue
            translate(str(front.GetPath()),units[index]['delta'],'Wholefront detail inherits nearestactualsourcecomponent; associative/display only',group.GetName())
    # Contact of historical sourcebase is diagnostic, never used to re-anchor
    # attached towers/cornices separately. FinalOmissions is handled by its sites.
    for family in families:
        path=family['familymembers'][0];prim=source.GetPrimAtPath(path)
        if not prim:continue
        mm=meshes(prim)
        if not mm:continue
        q=np.concatenate([world_points(p,cache) for p in mm]);foot=MultiPoint(q[:,:2]).convex_hull
        try:
            sampled=rendered.sample(np.array(foot.exterior.coords));base=float(q[:,2].min()+family['delta_z_m'])
            contacts.append({'path':path,'family':family['id'],'policy':'Source-envelope context, notsurveyedfoundation; attachedpartminZisNOTground',
                'source_frame_delta_z_m':family['delta_z_m'],'base_clearance_boundary_minmax_m':[float(base-sampled.max()),float(base-sampled.min())],'base_ground_relief_m':float(np.ptp(sampled))})
        except ValueError as error:held.append({'path':path,'policy':'Contactcontext '+str(error),'partial':True})
    # Serialize no sublayers/cameras/lights; root integrator owns review assembly.
    layer=output/'terrain_buildings.usda';stage.GetRootLayer().customLayerData={'status':'inactive_incomplete_terrain_building_candidate','sourceSnapshot':field['source_snapshot'],'verticalDatum':'NAVD88','sceneZOriginNAVD88Meters':30.}
    stage.GetRootLayer().Export(str(layer))
    # Actual composed verification, not merely requested translations. Source
    # faces must each remain rigid; different disconnected units may translate
    # independently. Geometry topology/UV/materials/source custom data survive.
    check=Usd.Stage.CreateInMemory();check.GetRootLayer().subLayerPaths=[str(layer),str(root/'scene/college_park_connected.usda')]
    after_cache=UsdGeom.XformCache();seen=set();max_xy=max_face_shift=max_linear=0.;verified_meshes=0
    for row in applied:
        path=row['path']
        if path in ['/World/Ground','/World/Context/SurroundingGround']:continue
        parent=source.GetPrimAtPath(path)
        for prim in meshes(parent):
            name=str(prim.GetPath())
            if name in seen:continue
            seen.add(name);other=check.GetPrimAtPath(name);v=world_points(prim,cache);w=world_points(other,after_cache)
            linear=float(abs(np.array(cache.GetLocalToWorldTransform(prim))[:3,:3]-np.array(after_cache.GetLocalToWorldTransform(other))[:3,:3]).max())
            max_linear=max(max_linear,linear)
            if linear>1e-10:raise ValueError('Anchor changed source worldrotation/scale/shear: '+name)
            if v.shape!=w.shape:raise ValueError('Anchor changed source vertex count: '+name)
            xy_error=float(abs(v[:,:2]-w[:,:2]).max());max_xy=max(max_xy,xy_error)
            if xy_error>.0002:raise ValueError('Anchor changed XY: '+name)
            mesh=UsdGeom.Mesh(prim);out=UsdGeom.Mesh(other)
            for attr in ['GetFaceVertexCountsAttr','GetFaceVertexIndicesAttr','GetNormalsAttr']:
                if str(getattr(mesh,attr)().Get())!=str(getattr(out,attr)().Get()):raise ValueError('Anchor changed source topology/normals: '+name)
            if prim.GetCustomData()!=other.GetCustomData():raise ValueError('Anchor changed original customData: '+name)
            for rel in prim.GetRelationships():
                if rel.GetTargets()!=other.GetRelationship(rel.GetName()).GetTargets():raise ValueError('Anchor changed source relationship: '+name)
            for var in UsdGeom.PrimvarsAPI(prim).GetPrimvars():
                other_var=UsdGeom.PrimvarsAPI(other).GetPrimvar(var.GetPrimvarName())
                if str(var.Get())!=str(other_var.Get()) or str(var.GetIndices())!=str(other_var.GetIndices()):raise ValueError('Anchor changed source appearance primvar: '+name)
            zdelta=w[:,2]-v[:,2];idx=np.array(mesh.GetFaceVertexIndicesAttr().Get());off=0
            for n in mesh.GetFaceVertexCountsAttr().Get():
                error=float(np.ptp(zdelta[idx[off:off+n]]));off+=n;max_face_shift=max(max_face_shift,error)
                if error>.00002:raise ValueError('Anchor deformed original source face: '+name)
            verified_meshes+=1
    applied_paths={r['path'] for r in applied}
    contacts=[r for r in contacts if r['path'] in applied_paths]
    preservation={'actual_composed_meshes_verified':verified_meshes,'maximum_world_xy_change_m':max_xy,
        'maximum_original_face_delta_spread_m':max_face_shift,'maximum_world_linear_matrix_change':max_linear,
        'topology_uv_normals_relationships_source_customData_preserved':True}
    sample_tri=triangles[::23];xy=points[sample_tri,:2].mean(1);renderz=points[sample_tri,2].mean(1);residual=abs(sampler.sample(xy)-renderz)
    ground_metrics['triangle_centroid_vs_sourceDEM_abs_residual_p50_p95_max_m']=np.percentile(residual,[50,95,100]).tolist()
    after={p:sha(root/p) for p in protected}
    changed=[p for p,h in deps.items() if not (root/p).is_file() or sha(root/p)!=h]
    if before!=after or changed:raise ValueError('Source changed during candidate build: '+','.join(changed))
    report={'schema':'twin.terrain-buildings-candidate/1','source_snapshot':field['source_snapshot'],'layer':layer.relative_to(root).as_posix(),'layer_sha256':sha(layer),
        'dependencies':deps,'protected_before':before,'protected_after':after,'helper_archive_sha256':frozen,'activated':False,
        'ground_field':field,'ground_metrics':ground_metrics,'applied':applied,'held':held,'families':families,'contacts':contacts,
        'actual_composed_preservation':preservation,
        'raw_part_mapping':{k:[{'geometry':shapely.to_geojson(u['geometry']),'delta_z_m':u['delta']} for u in v] for k,v in raw_part_mapping.items()},
        'scope':'Ground/Context plus rawBuildings/Roofs/Storefronts/historicalfamilies only; surfaces/assets handledseparately',
        'limits':['OuterContextflat fallback explicitlyheld, no globalactivationacceptance','Rigidgroundbase gaps/intersections remain contactdiscrepancies, notsurveyedfoundation model',
            'Historicalsourceframe conversions preserve relativegeometry, no currenttax/floorpromotion','Roads/vegetation/vehicles/furniture/thematics are outside thislayer ownership',
            'No independentvisualreview or sourceaccuracyclaim; wholecomposition acceptancepending']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {'layer':report['layer'],'layer_sha256':report['layer_sha256'],'applied':len(applied),'held':len(held),'families':len(families),'manifest_sha256':sha(output/'manifest.json')}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(build(ROOT/args.output),indent=2))
