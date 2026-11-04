"""Prepare inactive surface/asset overrides against the final rendered ground.

Contract: fresh ignored output only; no downloads, activation, editor or GPU.
Road families are atomic. Original source-face UV maps and XY holes/outlines
are retained while clipping to actual ground triangles. Assets retain rigid
shape; point instances change positions only. Physical water is held pending
water-stage interpretation. See generated manifest for every World scope.
"""
from pathlib import Path
import os,sys,json,argparse,hashlib,collections,re,importlib.util
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from pxr import Usd,UsdGeom,Sdf,Gf,Vt
SAMPLER_ARCHIVE='data/diagnostics/terrain_buildings_20261102_b/captured_helper.py'
_spec=importlib.util.spec_from_file_location('frozen_terrain_ground',ROOT/SAMPLER_ARCHIVE)
_ground_module=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_ground_module)
TerrainSurfaceSampler=_ground_module.TerrainSurfaceSampler

GROUND='data/diagnostics/terrain_buildings_20261102_b/ground_surface.npz'
GROUND_SHA='c88936bdcc444296ddb678af5aa7f9baaf76d669608fe2df6956d3f38a87b806'
OWNED=['Streets','Water','Parks','Trees','StreetFurniture','ParkedVehicles','ParcelBoundaries',
       'StudyBoundaries','RearParkingSamples','Information','WaterLandcoverContext','CampusHardscapeCandidate']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def visible(p):return UsdGeom.Imageable(p).ComputeVisibility()!='invisible'
def mesh_faces(p,cache):
    mesh=UsdGeom.Mesh(p);v=np.asarray(mesh.GetPointsAttr().Get(),float)
    matrix=cache.GetLocalToWorldTransform(p)
    v=np.array([matrix.Transform(Gf.Vec3d(*x)) for x in v])
    ix=np.asarray(mesh.GetFaceVertexIndicesAttr().Get(),int);counts=mesh.GetFaceVertexCountsAttr().Get();off=0;faces=[]
    for n in counts:faces.append(ix[off:off+n]);off+=n
    return v,faces,matrix
def geometry(p,cache):
    v,f,_=mesh_faces(p,cache)
    return unary_union([Polygon(v[x,:2]) for x in f if Polygon(v[x,:2]).is_valid and Polygon(v[x,:2]).area>1e-9])

def surface(p,ground,cache):
    """Return a prepared override, or fail before any property is authored."""
    if p.IsInstanceProxy() or p.IsInstance():raise ValueError('instance_surface_requires_separate_contract')
    if any(c.GetTypeName()=='GeomSubset' for c in p.GetChildren()):raise ValueError('face_subset_mapping_required')
    v,faces,matrix=mesh_faces(p,cache)
    if not len(v) or not np.isfinite(v).all():raise ValueError('empty_or_nonfinite_surface')
    if np.ptp(v[:,2])>.001:raise ValueError('nonflat_surface_needs_explicit_grade_or_vertical_face_contract')
    api=UsdGeom.PrimvarsAPI(p);st=api.GetPrimvar('st');uv=None;interp=None
    if st and st.Get() is not None:
        uv=np.asarray(st.ComputeFlattened(),float);interp=st.GetInterpolation()
        if interp not in ('vertex','faceVarying'):raise ValueError('unsupported_st_interpolation')
    for var in api.GetPrimvars():
        if var.Get() is not None and var.GetPrimvarName()!='st' and var.GetInterpolation()!='constant':
            raise ValueError('nonconstant_extra_primvar_requires_explicit_interpolation:'+var.GetName())
    vertices=[];newuv=[];triangles=[];original=[];offset=0
    for face in faces:
        xy=v[face,:2];poly=Polygon(xy)
        if not poly.is_valid or poly.area<1e-9:raise ValueError('nonplanar_projected_or_vertical_source_face')
        original.append(poly)
        if uv is not None:
            values=uv[face] if interp=='vertex' else uv[offset:offset+len(face)]
            fit=np.linalg.lstsq(np.c_[xy,np.ones(len(xy))],values,rcond=None)[0]
            if np.max(np.abs(np.c_[xy,np.ones(len(xy))]@fit-values))>1e-5:raise ValueError('nonaffine_source_face_uv_requires_explicit_mapping')
        offset+=len(face)
        covered=[]
        for ti in ground.tree.query(poly,predicate='intersects'):
            piece=poly.intersection(ground.triangle_polygons[ti])
            if piece.is_empty or piece.area<1e-10:continue
            covered.append(piece)
            gp=ground.points[ground.triangles[ti]];coef=np.linalg.solve(np.c_[gp[:,:2],np.ones(3)],gp[:,2])
            for tr in shapely.constrained_delaunay_triangles(piece).geoms:
                q=np.asarray(tr.exterior.coords)[:3]
                if tr.area<1e-10:continue
                aa,bb=q[1]-q[0],q[2]-q[0]
                if aa[0]*bb[1]-aa[1]*bb[0]<0:q=q[::-1]
                xyz=np.c_[q,np.c_[q,np.ones(3)]@coef+v[0,2]]
                triangles.append([len(vertices),len(vertices)+1,len(vertices)+2]);vertices.extend(xyz.tolist())
                if uv is not None:newuv.extend((np.c_[q,np.ones(3)]@fit).tolist())
        if not covered or poly.difference(unary_union(covered)).area>1e-5:raise ValueError('outside_final_ground_triangle_support')
    out=np.asarray(vertices);inverse=matrix.GetInverse();local=np.array([inverse.Transform(Gf.Vec3d(*x)) for x in out],np.float32)
    old=unary_union(original);new=unary_union([Polygon(out[t,:2]) for t in triangles])
    if old.symmetric_difference(new).area>max(.001,old.area*1e-8):raise ValueError('surface_outline_or_hole_changed')
    return local,np.asarray(triangles,int),np.asarray(newuv,np.float32) if uv is not None else None,{
        'path':str(p.GetPath()),'policy':'source_face_UV_exact_affine; XY_outline_holes_preserved; clipped_to_final_ground_triangles',
        'original_offset_m':float(v[0,2]),'original_area_m2':old.area,'outline_symdiff_m2':old.symmetric_difference(new).area,
        'triangles':len(triangles),'grade_status':'unverified; DEM does not establish engineered road grade'}

def build(output):
    output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(ROOT/'data/diagnostics'):raise ValueError('Fresh ignored output required')
    if sha(ROOT/GROUND)!=GROUND_SHA:raise ValueError('Final ground field changed')
    output.mkdir(parents=True);(output/'captured_helper.py').write_bytes(Path(__file__).read_bytes())
    deps={GROUND:GROUND_SHA,SAMPLER_ARCHIVE:sha(ROOT/SAMPLER_ARCHIVE),
          'tools/prepare_terrain_surfaces.py':sha(__file__)}
    for p in [ROOT/'data/diagnostics/terrain_buildings_20261102_b/ground_field.json',ROOT/'data/processed/active.json',ROOT/'data/openstreetmap.json']:
        deps[p.relative_to(ROOT).as_posix()]=sha(p)
    # Receipt-verified original TIFF/XML provenance remains explicit, even though
    # contact is evaluated against the serialized final render interpolant.
    config=json.loads((ROOT/'config/terrain_sources.json').read_text());deps['config/terrain_sources.json']=sha(ROOT/'config/terrain_sources.json')
    for tile in config['tiles']:
        for ext in ['tif','xml']:
            p=ROOT/'data/heights/dem'/(tile['id']+'.'+ext);receipt=Path(str(p)+'.source.json');record=json.loads(receipt.read_text())
            if sha(p)!=record['sha256']:raise ValueError('Original DEM bytes mismatch')
            deps[p.relative_to(ROOT).as_posix()]=record['sha256'];deps[receipt.relative_to(ROOT).as_posix()]=sha(receipt)
    source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'));cache=UsdGeom.XformCache()
    for layer in source.GetUsedLayers():
        if layer.realPath:deps[Path(layer.realPath).resolve().relative_to(ROOT).as_posix()]=sha(layer.realPath)
    for prim in source.Traverse():
        for attr in prim.GetAuthoredAttributes():
            value=attr.Get()
            if isinstance(value,Sdf.AssetPath) and value.path:
                asset=Path(value.resolvedPath or value.path).resolve()
                if not asset.is_file() or not asset.is_relative_to(ROOT):raise ValueError('Unresolved or external source asset:'+str(attr.GetPath()))
                deps[asset.relative_to(ROOT).as_posix()]=sha(asset)
    protected={p:sha(ROOT/p) for p in ['scene/college_park_connected.usda','scene/manual_edits.usda','data/processed/active.json','data/processed/selection_bridge.json']}
    ground=TerrainSurfaceSampler.from_npz(ROOT/GROUND);stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1.)
    applied=[];held=[];families=[]
    def hold(path,policy,**kw):held.append({'path':str(path),'policy':policy,**kw})
    def write_surface(p,result):
        points,triangles,uv,row=result;mesh=UsdGeom.Mesh(stage.OverridePrim(p.GetPath()))
        mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points));mesh.CreateFaceVertexCountsAttr([3]*len(triangles));mesh.CreateFaceVertexIndicesAttr(triangles.ravel().tolist());mesh.CreateNormalsAttr().Block()
        mesh.CreateExtentAttr([Gf.Vec3f(*map(float,points.min(0))),Gf.Vec3f(*map(float,points.max(0)))])
        if uv is not None:
            UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'vertex').Set(Vt.Vec2fArray.FromNumpy(uv))
            stage.OverridePrim(p.GetPath()).CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block()
        applied.append(row)
    osm={str(e['id']):e.get('tags',{}) for e in json.loads((ROOT/'data/openstreetmap.json').read_text())['elements']}
    roadgroups=collections.defaultdict(list);roads=[];roadmeta=[]
    for p in source.GetPrimAtPath('/World/Streets').GetChildren():roadgroups[p.GetName().rsplit('_',1)[-1]].append(p)
    for id,members in roadgroups.items():
        tags=osm.get(id);reason=None
        if not tags:reason='missing_cached_OSM_grade_tags'
        elif str(tags.get('bridge','no')).lower() not in ('no','false','0') or str(tags.get('tunnel','no')).lower() not in ('no','false','0') or str(tags.get('layer','0'))!='0':reason='explicit_bridge_tunnel_or_nonzero_layer_family_hold'
        elif not all(visible(p) for p in members):reason='hidden_family_preserved'
        prepared=[]
        if not reason:
            try:prepared=[(p,surface(p,ground,cache)) for p in members]
            except ValueError as e:reason=str(e)
        for p in members:
            if p.GetName().startswith('Road_'):
                try:roads.append(geometry(p,cache));roadmeta.append({'held':reason,'offset':float(mesh_faces(p,cache)[0][0,2]),'path':str(p.GetPath())})
                except ValueError:pass
        families.append({'id':'OSM:'+id,'members':[str(p.GetPath()) for p in members],'policy':reason or 'atomic_final_ground_triangle_drape; bridge_status_unverified_unless_explicit_no','grade_tags':tags})
        if reason:
            for p in members:hold(p.GetPath(),reason)
        else:
            for p,result in prepared:write_surface(p,result)
    roadtree=shapely.STRtree(roads)
    def support(xy):
        xy=np.asarray(xy,float);z=ground.sample(xy);offset=np.zeros(len(xy));pairs=roadtree.query(shapely.points(xy),predicate='intersects')
        for i,j in pairs.T:
            meta=roadmeta[j]
            if meta['held']:raise ValueError('contact_on_held_road:'+meta['held'])
            offset[i]=max(offset[i],meta['offset'])
        return z+offset
    # Other visible physical horizontal surfaces use the same exact interpolant.
    for root in ['Parks','RearParkingSamples','CampusHardscapeCandidate']:
        parent=source.GetPrimAtPath('/World/'+root)
        if not parent:continue
        for p in Usd.PrimRange(parent):
            if not p.IsA(UsdGeom.Mesh):continue
            if not visible(p):hold(p.GetPath(),'hidden_surface_unchanged');continue
            try:write_surface(p,surface(p,ground,cache))
            except ValueError as e:hold(p.GetPath(),str(e))
    def meshpoints(p,relative=None):
        q=np.array(UsdGeom.Mesh(p).GetPointsAttr().Get(),float)
        matrix=cache.GetLocalToWorldTransform(p) if relative is None else cache.ComputeRelativeTransform(p,relative)[0]
        return np.array([matrix.Transform(Gf.Vec3d(*x)) for x in q])
    def rigid(p,contacts,kind):
        contacts=np.asarray(contacts,float)
        if not len(contacts):raise ValueError('no_actual_contact_geometry')
        required=support(contacts[:,:2])-contacts[:,2];delta=float(required.max());gap=delta-required
        if np.ptp(required)>.20:raise ValueError('rigid_contact_relief_over_20cm_requires_orientation_or_grade_review')
        # Preserve every inherited op and reset token. Insert a least-local op,
        # whose frame is the source parent, never the object's rotated axes.
        source_xf=UsdGeom.Xformable(p);reset=source_xf.GetResetXformStack()
        parent_matrix=Gf.Matrix4d(1) if reset else cache.GetParentToWorldTransform(p)
        local=parent_matrix.GetInverse().TransformDir(Gf.Vec3d(0,0,delta))
        xf=UsdGeom.Xformable(stage.OverridePrim(p.GetPath()))
        op=xf.AddTranslateOp(opSuffix='terrainSurfaceAnchor');op.Set(local)
        original=list(source_xf.GetXformOpOrderAttr().Get() or [])
        order=[x for x in original if x!='!resetXformStack!']
        xf.GetXformOpOrderAttr().Set((['!resetXformStack!'] if reset else [])+[op.GetOpName()]+order)
        applied.append({'path':str(p.GetPath()),'policy':'rigid_actual_'+kind+'_contact; source_geometry_rotations_scales_unchanged',
                        'delta_z_m':delta,'contact_points':len(contacts),'contact_gap_minmax_m':[float(gap.min()),float(gap.max())]})
    # Group furniture supports atomically, avoiding independent bench/shrub moves.
    for parent in source.GetPrimAtPath('/World/StreetFurniture').GetChildren():
        if not visible(parent):hold(parent.GetPath(),'hidden_furniture_family_unchanged');continue
        points=[]
        for p in Usd.PrimRange(parent):
            if p.IsA(UsdGeom.Mesh) and any(x in p.GetName() for x in ['Leg','Base','Post']):
                q=meshpoints(p);points.extend(q[q[:,2]<=q[:,2].min()+.001].tolist())
            elif p.IsA(UsdGeom.Cylinder) and p.GetName().startswith('Base'):
                cyl=UsdGeom.Cylinder(p);radius=cyl.GetRadiusAttr().Get();height=cyl.GetHeightAttr().Get();axis=str(cyl.GetAxisAttr().Get())
                axial={'X':0,'Y':1,'Z':2}[axis];other=[i for i in range(3) if i!=axial];matrix=cache.GetLocalToWorldTransform(p)
                angles=np.linspace(0,2*np.pi,64,endpoint=False);local=[]
                for z in [-height/2,height/2]:
                    for theta in angles:
                        q=np.zeros(3);q[axial]=z;q[other]=radius*np.array([np.cos(theta),np.sin(theta)]);local.append(q)
                q=np.array([matrix.Transform(Gf.Vec3d(*x)) for x in local]);points.extend(q[q[:,2]<=q[:,2].min()+.001].tolist())
        try:rigid(parent,points,'furniture_leg_base')
        except ValueError as e:hold(parent.GetPath(),str(e))
    for parent in source.GetPrimAtPath('/World/ParkedVehicles').GetChildren():
        if not visible(parent):hold(parent.GetPath(),'hidden_vehicle_unchanged');continue
        points=[]
        for p in Usd.PrimRange(parent,Usd.TraverseInstanceProxies()):
            if p.IsA(UsdGeom.Mesh) and 'Wheel' in p.GetName() and not any(x in p.GetName() for x in ['Rim','Spoke']):
                q=meshpoints(p);points.extend(q[q[:,2]<=q[:,2].min()+.001].tolist())
        try:rigid(parent,points,'actual_tire_bottom')
        except ValueError as e:hold(parent.GetPath(),str(e))
    trees=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'));prim=trees.GetPrim()
    if cache.GetLocalToWorldTransform(prim)!=Gf.Matrix4d(1):hold(prim.GetPath(),'pointinstancer_nonidentity_frame_requires_conversion')
    else:
        positions=np.array(trees.GetPositionsAttr().Get(),float);original=positions.copy();indices=np.array(trees.GetProtoIndicesAttr().Get());targets=trees.GetPrototypesRel().GetTargets();proto=[]
        for target in targets:
            p=source.GetPrimAtPath(target);points=[]
            for q in Usd.PrimRange(p,Usd.TraverseInstanceProxies()):
                if q.IsA(UsdGeom.Mesh) and 'Trunk' in q.GetName():points.extend(meshpoints(q,p).tolist())
            proto.append(np.array(points));hold(target,'shared_prototype_geometry_and_transform_unchanged; placement_only')
        matrices=trees.ComputeInstanceTransformsAtTime(Usd.TimeCode.Default(),Usd.TimeCode.Default(),UsdGeom.PointInstancer.IncludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
        mask=trees.ComputeMaskAtTime(Usd.TimeCode.Default());mask=list(mask) if len(mask) else [True]*len(positions);details=[]
        for i,(matrix,pi) in enumerate(zip(matrices,indices)):
            if not mask[i]:details.append({'index':i,'policy':'invisible_instance_position_unchanged'});continue
            if not len(proto[pi]):details.append({'index':i,'policy':'held_no_actual_trunk_geometry'});continue
            q=np.array([matrix.Transform(Gf.Vec3d(*x)) for x in proto[pi]]);contact=q[q[:,2]<=q[:,2].min()+.005]
            try:
                required=support(contact[:,:2])-contact[:,2];delta=float(required.max())
                if np.ptp(required)>.2:raise ValueError('trunk_contact_relief_over_20cm')
                positions[i,2]+=delta;details.append({'index':i,'policy':'actual_scaled_oriented_trunk_base_contact','delta_z_m':delta,'contact_points':len(contact),'max_gap_m':float(np.ptp(required))})
            except ValueError as e:details.append({'index':i,'policy':'held_'+str(e)})
        UsdGeom.PointInstancer(stage.OverridePrim(prim.GetPath())).CreatePositionsAttr(Vt.Vec3fArray.FromNumpy(positions.astype(np.float32)))
        applied.append({'path':str(prim.GetPath()),'policy':'pointinstancer_positions_only; IDs/protoIndices/scales/orientations/invisibleIds/prototypes_unchanged','instance_count':len(positions),'moved_instances':int(np.sum(np.any(original!=positions,axis=1))),'instance_details':details})
    for name in ['Water','Information','WaterLandcoverContext','ParcelBoundaries','StudyBoundaries']:
        p=source.GetPrimAtPath('/World/'+name)
        if p:hold(p.GetPath(),('physical_water_horizontal_unchanged; hydroflattened_stage_or_shoreline_review_pending' if name=='Water' else 'cartographic_overlay_unchanged; explicit_display_offset_and_hidden_state_preserved'),visibility=UsdGeom.Imageable(p).ComputeVisibility())
    # Exhaustive top-level inventory includes nonphysical/other-builder ownership.
    inventory=[]
    for p in source.GetPrimAtPath('/World').GetChildren():
        name=p.GetName();policy='surface_asset_family_detailed_above' if name in OWNED else 'delegated_GIS_ground_building_context_family' if name in ['Ground','Context','Buildings','Roofs','Landmarks','Storefronts','OfficeFrontageProposal','OfficeFrontageDetail','ChurchFrontageAppearance','ChurchBelfryAppearance'] else 'nonphysical_material_camera_light_scope_unchanged'
        inventory.append({'path':str(p.GetPath()),'policy':policy,'boundable_descendants':sum(x.IsA(UsdGeom.Boundable) for x in Usd.PrimRange(p))})
        if name not in OWNED:hold(p.GetPath(),policy)
    for p,digest in deps.items():
        if sha(ROOT/p)!=digest:raise ValueError('Source changed during build: '+p)
    if protected!={p:sha(ROOT/p) for p in protected}:raise ValueError('Protected source changed')
    layer=output/'surfaces.usda';stage.GetRootLayer().customLayerData={'status':'INACTIVE_INCOMPLETE_SURFACE_CONTACT_CANDIDATE','sceneZOriginNAVD88Meters':30.,'groundFieldSHA256':GROUND_SHA};stage.GetRootLayer().Export(str(layer))
    # Verify the actual serialized composition, not merely authored deltas.
    composed_layer=Sdf.Layer.CreateAnonymous();composed_layer.subLayerPaths=[str(layer),str(ROOT/'scene/college_park_connected.usda')]
    composed=Usd.Stage.Open(composed_layer);newcache=UsdGeom.XformCache();rigid_checks=[]
    for row in applied:
        if 'delta_z_m' not in row:continue
        p=source.GetPrimAtPath(row['path']);q=composed.GetPrimAtPath(row['path']);a=np.array(cache.GetLocalToWorldTransform(p));b=np.array(newcache.GetLocalToWorldTransform(q));d=b[3,:3]-a[3,:3]
        if np.max(np.abs(a[:3,:3]-b[:3,:3]))>1e-10 or max(abs(d[0]),abs(d[1]),abs(d[2]-row['delta_z_m']))>1e-8:raise ValueError('Serialized rigid world transform mismatch:'+row['path'])
        oldops=list(UsdGeom.Xformable(p).GetXformOpOrderAttr().Get() or []);newops=list(UsdGeom.Xformable(q).GetXformOpOrderAttr().Get() or [])
        if [x for x in newops if x!='xformOp:translate:terrainSurfaceAnchor']!=oldops:raise ValueError('Source transform order/reset changed')
        for op in UsdGeom.Xformable(p).GetOrderedXformOps():
            if str(op.GetAttr().Get())!=str(q.GetAttribute(op.GetOpName()).Get()):raise ValueError('Source transform value changed')
        rigid_checks.append({'path':row['path'],'world_linear_xy_and_delta_verified':True,'source_oporder_reset_values_preserved':True})
    report={'schema':'twin.terrain-surface-assets/1','source_snapshot':json.loads((ROOT/'data/processed/active.json').read_text())['snapshot'],'activated':False,'layer':layer.relative_to(ROOT).as_posix(),'layer_sha256':sha(layer),'scene_z_origin_navd88_m':30.,'ground_field':GROUND,'ground_field_sha256':GROUND_SHA,'dependencies':deps,'protected_before':protected,'protected_after':{p:sha(ROOT/p) for p in protected},'applied':applied,'held':held,'road_families':families,'world_scope_inventory':inventory,'serialized_rigid_checks':rigid_checks,'producer_archive':(output/'captured_helper.py').relative_to(ROOT).as_posix(),'producer_sha256':sha(output/'captured_helper.py'),'limits':['Incomplete inactive inspection candidate; physical water and cartographic overlays explicitly held.','No surveyed grade, sidewalk/curb inventory, bridge clearance, current-condition or engineering accuracy acceptance.','Rigid wheel/trunk placements retain source rotations; gaps up to20cm are recorded, not an all-wheels-grade fit.','Geometry/source outline/UV preservation and actual rendered visual acceptance require independent review.']}
    dump(output/'manifest.json',report)
    return {'output':output.relative_to(ROOT).as_posix(),'applied':len(applied),'held':len(held),'layer_sha256':sha(layer)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args();print(json.dumps(build(ROOT/args.output),indent=2))
