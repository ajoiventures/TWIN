"""Inactive estimated render closures below unchanged anchored source bases.

Uses actual bottom wall/slab edges and the frozen final triangulated ground.
No foundation/basement, stairs, doors, floor-count, roof or terrain modification.
Large gaps and penetrations are held. Outputs require a fresh ignored folder.
"""
from pathlib import Path
import os,sys,json,argparse,hashlib,importlib.util,collections
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import Polygon,LineString,Point,shape
from shapely.ops import transform as transform_geometry
from pyproj import Transformer
from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
FOLDER='data/diagnostics/terrain_buildings_20261102_f/'
SCENE='scene/terrain_candidate_review_20261102.usda'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build(output,root=ROOT,max_gap=.75,building_folder=FOLDER,review_scene=SCENE):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Fresh ignored diagnostic directory required')
    if not 0<max_gap<=1.:raise ValueError('Render-closure cap must be positive and at most1m')
    folder=(root/building_folder).resolve().relative_to(root)
    review=(root/review_scene).resolve().relative_to(root).as_posix()
    candidate_inputs=[(folder/name).as_posix() for name in ('manifest.json','ground_surface.npz','captured_helper.py')]
    deps={p:sha(root/p) for p in ['tools/prepare_terrain_contacts.py',review,*candidate_inputs,'data/processed/study_boundaries.geojson','tools/acquire_dem.py','tools/anchor_terrain_proposal.py','tools/build_terrain_proposal.py','tools/prepare_church_legacy_mask.py']}
    f=json.loads((root/folder/'manifest.json').read_text())
    flagged={'rows':[row for row in f['contacts'] if max(map(abs,row['base_clearance_boundary_minmax_m']))>.30]}
    for path,digest in f['dependencies'].items():
        if sha(root/path)!=digest:raise ValueError('Stale building candidate dependency: '+path)
        deps[path]=digest
    if sha(root/f['layer'])!=f['layer_sha256']:raise ValueError('Frozen building candidate changed')
    if sha(root/folder/'ground_surface.npz')!=f['ground_field']['sha256']:raise ValueError('Frozen ground field changed')
    module_spec=importlib.util.spec_from_file_location('frozen_terrain_contact_support',root/folder/'captured_helper.py');support=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(support)
    ground=support.TerrainSurfaceSampler.from_npz(root/folder/'ground_surface.npz')
    scene=Usd.Stage.Open(str(root/review));original=Usd.Stage.Open(str(root/'scene/college_park_connected.usda'));cache=UsdGeom.XformCache();base_cache=UsdGeom.XformCache()
    used_paths=set()
    for layer in scene.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath).resolve()
            if not p.is_relative_to(root):raise ValueError('Unexpected external scene dependency')
            relative=p.relative_to(root).as_posix()
            used_paths.add(relative)
            deps.setdefault(relative,sha(p))
    if f['layer'] not in used_paths:raise ValueError('Review stage does not compose the specified building candidate')
    output.mkdir(parents=True);(output/'captured_helper.py').write_bytes(Path(__file__).read_bytes())
    protected={p:sha(root/p) for p in ['scene/college_park_connected.usda','scene/manual_edits.usda','data/processed/active.json',f['layer']]}
    def xyz(prim,xc=cache):
        v=UsdGeom.Mesh(prim).GetPointsAttr().Get();m=xc.GetLocalToWorldTransform(prim)
        return np.array([m.Transform(p) for p in v],float)
    def resolve_material(prim,face):
        for subset in prim.GetChildren():
            if subset.GetTypeName()=='GeomSubset' and face in list(UsdGeom.Subset(subset).GetIndicesAttr().Get() or []):
                m=UsdShade.MaterialBindingAPI(subset).ComputeBoundMaterial()[0]
                if m:return str(m.GetPath())
        material=UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
        return str(material.GetPath()) if material else None
    def face_uv(mesh,face,off,n):
        var=UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st')
        if not var:return None
        values=var.ComputeFlattened()
        if values is None:return None
        values=np.array(values);mode=var.GetInterpolation()
        if mode=='faceVarying':return values[off:off+n]
        if mode in ('vertex','varying'):return values[np.array(mesh.GetFaceVertexIndicesAttr().Get())[off:off+n]]
        return None
    target_specs=[]
    for name,units in f['raw_part_mapping'].items():
        path='/World/Buildings/'+name;p=scene.GetPrimAtPath(path);old=original.GetPrimAtPath(path)
        if not p or not old:continue
        v=xyz(old,base_cache);base_units=[]
        for u in units:
            poly=shape(json.loads(u['geometry']));dist=shapely.distance(shapely.points(v[:,:2]),poly);base=float(v[dist<.001,2].min()+u['delta_z_m']);base_units.append((poly,base))
        target_specs.append((path,p,base_units,'source_bottom_wall'))
    for family in f['families']:
        path=family['familymembers'][0]
        if not path.startswith('/World/Landmarks/'):continue
        p=scene.GetPrimAtPath(path)
        if not p:continue
        meshes=[m for m in Usd.PrimRange(p) if m.GetTypeName()=='Mesh' and UsdGeom.Imageable(m).ComputeVisibility()!='invisible']
        if not meshes:continue
        base=min(xyz(m)[:,2].min() for m in meshes)
        for m in meshes:target_specs.append((path,m,[(None,float(base))],'historical_envelope_bottom_wall'))
    sf=scene.GetPrimAtPath('/World/Storefronts')
    for p in Usd.PrimRange(sf):
        if p.GetTypeName()!='Mesh' or UsdGeom.Imageable(p).ComputeVisibility()=='invisible':continue
        if p.GetName() not in ('Plinth','EntryPaving'):continue
        names=str(p.GetPath()).split('/');alias=next((s for s in names if s.startswith('Building_')),None)
        if alias not in f['raw_part_mapping']:continue
        base=float(xyz(p)[:,2].min());target_specs.append(('/World/Buildings/'+alias,p,[(None,base)],'illustrative_entry_slab_edge' if p.GetName()=='EntryPaving' else 'illustrative_plinth_bottom_wall'))
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1.)
    parent=UsdGeom.Xform.Define(stage,'/World/TerrainContactClosures').GetPrim();parent.SetCustomData({'quality':'illustrative_estimated_render_base_closure_not_survey_foundation','sourceSnapshot':f['source_snapshot'],'currentConditionsVerified':False,'rawTaxLinksAccepted':False,'publicDerivativeReleaseAccepted':False,'purpose':'Close bounded visible gaps below unchanged original wall/slab bases; no foundation/basement/entrance/floor claim','maximumGapM':max_gap})
    applied=[];held=[];edge_rows=[];owners=collections.defaultdict(lambda:collections.Counter());generated_faces=0;seen_edges=set();lower_contact_errors=[];max_normal_error=0.
    for owner,prim,base_units,kind in target_specs:
        if UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        mesh=UsdGeom.Mesh(prim);v=xyz(prim);counts=list(mesh.GetFaceVertexCountsAttr().Get());indices=np.array(mesh.GetFaceVertexIndicesAttr().Get());off=0;edges=[]
        if kind=='illustrative_entry_slab_edge':
            incidence=collections.defaultdict(list)
            for fi,n in enumerate(counts):
                ids=indices[off:off+n];uv=face_uv(mesh,fi,off,n);off+=n
                for j in range(n):
                    a,b=ids[j],ids[(j+1)%n];key=tuple(sorted((tuple(np.round(v[a],5)),tuple(np.round(v[b],5)))))
                    incidence[key].append((v[a],v[b],fi,None,uv,None))
            for values in incidence.values():
                if len(values)==1:
                    a,b,fi,_,_,_=values[0];d=b-a;normal=np.array([d[1],-d[0],0.]);normal/=max(np.linalg.norm(normal),1e-12);edges.append((a,b,fi,normal,None,None))
        else:
            for fi,n in enumerate(counts):
                q=v[indices[off:off+n]];uv=face_uv(mesh,fi,off,n);off+=n
                normal=np.cross(q[1]-q[0],q[2]-q[0]);length=np.linalg.norm(normal)
                if length<1e-8:continue
                normal/=length
                if abs(normal[2])>.2:continue
                for j in range(n):
                    a,b=q[j],q[(j+1)%n]
                    if np.linalg.norm(b[:2]-a[:2])<.03:continue
                    midpoint=(a+b)/2
                    unit=min(base_units,key=lambda u:Point(midpoint[:2]).distance(u[0]) if u[0] is not None else 0)
                    if max(abs(a[2]-unit[1]),abs(b[2]-unit[1]))>.005:continue
                    edges.append((a,b,fi,normal,q,uv))
        vertices=[];faces=[];normals=[];uvs=[];materials=[];source_edges=0
        for a,b,fi,normal,q,source_uv in edges:
            key=(str(prim.GetPath()),tuple(sorted((tuple(np.round(a,5)),tuple(np.round(b,5))))))
            if key in seen_edges:continue
            seen_edges.add(key);source_edges+=1;owners[owner]['source_edges']+=1
            line=LineString([a[:2],b[:2]]);direction=b[:2]-a[:2];length2=float(direction@direction);cuts=[0.,1.]
            for ti in ground.tree.query(line,predicate='intersects'):
                hit=line.intersection(ground.triangle_polygons[ti]);pieces=list(hit.geoms) if hasattr(hit,'geoms') else [hit]
                for part in pieces:
                    if part.geom_type=='LineString' and not part.is_empty:
                        cuts.extend(float((np.array(p)-a[:2])@direction/length2) for p in [part.coords[0],part.coords[-1]])
            cuts=sorted(set(round(max(0,min(1,t)),10) for t in cuts));samples=np.array([a[:2]+direction*t for t in cuts])
            try:gz=ground.sample(samples)
            except ValueError:
                held.append({'path':str(prim.GetPath()),'owner':owner,'reason':'outside_final_ground_edge_support','source_face':fi});owners[owner]['outside_ground_edges']+=1;continue
            tops=a[2]+(b[2]-a[2])*np.array(cuts);gaps=tops-gz;maxgap=float(gaps.max());mingap=float(gaps.min())
            if maxgap>max_gap:
                held.append({'path':str(prim.GetPath()),'owner':owner,'reason':'gap_exceeds_estimated_render_cap_no_truncated_skirt','source_face':fi,'max_gap_m':maxgap});owners[owner]['capped_large_edges']+=1;continue
            if mingap<-.03:owners[owner]['terrain_above_original_base_edges']+=1
            material=resolve_material(prim,fi)
            if not material:
                held.append({'path':str(prim.GetPath()),'owner':owner,'reason':'missing_original_face_material','source_face':fi});continue
            source_direction=direction/np.sqrt(length2);uv_fit=None
            if q is not None and source_uv is not None:
                local=np.c_[(q[:,:2]-a[:2])@source_direction,q[:,2],np.ones(len(q))];fit=np.linalg.lstsq(local,source_uv,rcond=None)[0]
                if abs(local@fit-source_uv).max()<.0001:uv_fit=fit
            for j,(t0,t1) in enumerate(zip(cuts,cuts[1:])):
                if t1-t0<1e-8:continue
                ga,gb=float(gaps[j]),float(gaps[j+1])
                if max(ga,gb)<=.01:continue
                if ga*gb<0:
                    cross=t0+(t1-t0)*ga/(ga-gb)
                    if ga<0:t0=cross
                    else:t1=cross
                xy=np.array([a[:2]+direction*t0,a[:2]+direction*t1],dtype=np.float32).astype(float)
                if np.linalg.norm(xy[1]-xy[0])<.015:continue
                try:bottom=ground.sample(xy)
                except ValueError:continue
                ts=((xy-a[:2])@direction)/length2;top=a[2]+(b[2]-a[2])*ts
                z=np.array([[*xy[0],bottom[0]],[*xy[1],bottom[1]],[*xy[1],top[1]],[*xy[0],top[0]]],dtype=np.float32)
                unique=[]
                for point in z:
                    if not unique or np.linalg.norm(point-unique[-1])>.00001:unique.append(point)
                if len(unique)>2 and np.linalg.norm(unique[0]-unique[-1])<.00001:unique.pop()
                z=np.array(unique)
                if len(z)<3:continue
                authored=np.cross(z[1]-z[0],z[2]-z[0]);area=np.linalg.norm(authored)
                if area<.00001:continue
                authored/=area
                if authored@normal<0:z=z[::-1];authored=-authored
                max_normal_error=max(max_normal_error,float(1-authored@normal))
                if uv_fit is not None:coords=np.c_[(z[:,:2]-a[:2])@source_direction,z[:,2],np.ones(len(z))]@uv_fit
                else:coords=np.c_[(z[:,:2]-a[:2])@source_direction,z[:,2]]
                index=len(vertices);vertices.extend(z.tolist());faces.append(list(range(index,index+len(z))));uvs.extend(coords.tolist());normals.append(authored.tolist());materials.append(material);generated_faces+=1
                lower_contact_errors.extend(abs(np.array(bottom,dtype=np.float32).astype(float)-bottom).tolist());owners[owner]['closure_faces']+=1
            edge_rows.append({'source_path':str(prim.GetPath()),'owner':owner,'source_face':fi,'kind':kind,'min_gap_m':mingap,'max_gap_m':maxgap,'uv_policy':'source_face_affine_extension' if uv_fit is not None else 'meter_based_fallback_original_material','support':'FinalGroundtriangle intersections, no independentDEMcontactfield'})
        if not faces:
            held.append({'path':str(prim.GetPath()),'owner':owner,'reason':'no_eligible_positive_bounded_source_base_gap','source_edges':source_edges});continue
        name='Closure_'+hashlib.sha256(str(prim.GetPath()).encode()).hexdigest()[:18];p='/World/TerrainContactClosures/'+name;out=UsdGeom.Mesh.Define(stage,p)
        out.CreatePointsAttr(vertices);out.CreateFaceVertexCountsAttr([len(f) for f in faces]);out.CreateFaceVertexIndicesAttr([i for face in faces for i in face]);out.CreateNormalsAttr(normals);out.SetNormalsInterpolation('uniform');out.CreateSubdivisionSchemeAttr('none');out.CreateDoubleSidedAttr(True)
        var=UsdGeom.PrimvarsAPI(out).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,'vertex');var.Set(uvs)
        out.GetPrim().SetCustomData({'quality':'illustrative_estimated_render_base_closure_not_survey_foundation','sourcePrimitive':str(prim.GetPath()),'existingOwner':owner,'sourceSnapshot':f['source_snapshot'],'currentConditionsVerified':False,'foundationOrBasementClaim':False,'newPhysicalEntity':False,'policy':'Only additional geometry below unchanged wall/slab edge; no stairs,doors,floors orroof/bodywarp'})
        for mat in sorted(set(materials)):
            selected=[i for i,m in enumerate(materials) if m==mat];sub=UsdGeom.Subset.CreateGeomSubset(out,'Material_'+str(len(selected))+'_'+hashlib.sha256(mat.encode()).hexdigest()[:8],'face',selected,'materialBind')
            UsdShade.MaterialBindingAPI.Apply(sub.GetPrim());sub.GetPrim().CreateRelationship('material:binding').SetTargets([Sdf.Path(mat)])
        UsdGeom.Subset.SetFamilyType(out,'materialBind','partition')
        applied.append({'path':p,'source_path':str(prim.GetPath()),'owner':owner,'faces':len(faces),'policy':'Estimated renderclosure only; source geometry/identity/visibility/materialdefinitions unchanged'})
    layer=output/'terrain_contacts.usda';stage.GetRootLayer().customLayerData={'status':'inactive_estimated_render_contact_closure','sourceSnapshot':f['source_snapshot'],'sourceGeometryChanged':False};stage.GetRootLayer().Export(str(layer))
    # Locate coarsening residuals without regenerating F's ground.
    dem,grid,origin=support.load_dem(root,deps);tri=ground.triangles;centers=ground.points[tri,:2].mean(1);z=ground.points[tri,2].mean(1);source_z=dem.sample(centers);res=abs(source_z-z)
    boundaries=json.loads((root/'data/processed/study_boundaries.geojson').read_text());project=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=dem.origin
    scopes={feature['id']:transform_geometry(lambda x,y,z=None:(np.asarray(project.transform(x,y)[0])-ox,np.asarray(project.transform(x,y)[1])-oy),shape(feature['geometry'])) for feature in boundaries['features']}
    worst=[]
    sampled=np.arange(len(tri))[::23];selected=np.unique(np.r_[sampled[np.argsort(res[sampled])[-10:]],np.argsort(res)[-20:]])
    bbox=UsdGeom.BBoxCache(0,['default','render'],useExtentsHint=True)
    candidates=[]
    for prefix in ['/World/Buildings','/World/Landmarks','/World/Streets']:
        parent=scene.GetPrimAtPath(prefix)
        if parent:
            for p in parent.GetChildren():
                if UsdGeom.Imageable(p).ComputeVisibility()!='invisible':candidates.append(p)
    for index in selected:
        polygon=ground.triangle_polygons[index];lo=np.array(polygon.bounds[:2]);hi=np.array(polygon.bounds[2:]);hits=[]
        for p in candidates:
            bounds=bbox.ComputeWorldBound(p).ComputeAlignedRange();a,b=bounds.GetMin(),bounds.GetMax()
            if b[0]<lo[0] or a[0]>hi[0] or b[1]<lo[1] or a[1]>hi[1]:continue
            hits.append(str(p.GetPath()))
        point=Point(centers[index]);worst.append({'triangle_index':int(index),'in_original_every23_centroid_screen':bool(index%23==0),'local_xy_m':centers[index].tolist(),'coarse_scene_z_m':float(z[index]),'source_dem_scene_z_m':float(source_z[index]),'absolute_residual_m':float(res[index]),'official_scopes':{k:bool(g.covers(point)) for k,g in scopes.items()},'candidate_bbox_intersection_paths':hits,'bbox_hits_not_exact_surface_contact':True})
    flagged_paths=set(r['path'] for r in flagged['rows']);owner_report=[{'path':k,**dict(v),'F_contact_flagged':k in flagged_paths} for k,v in owners.items()]
    after={p:sha(root/p) for p in protected}
    changed=[p for p,h in deps.items() if not (root/p).is_file() or sha(root/p)!=h]
    if after!=protected or changed:raise ValueError('Frozen source changed during contact build: '+','.join(changed))
    manifest={'schema':'twin.terrain-contacts-candidate/1','source_snapshot':f['source_snapshot'],'layer':layer.relative_to(root).as_posix(),'layer_sha256':sha(layer),'activated':False,'dependencies':deps,'protected_before':protected,'protected_after':after,'applied':applied,'held':held,'source_edges':edge_rows,'owners':owner_report,'faces':generated_faces,'maximum_float32_lower_contact_error_m':max(lower_contact_errors,default=0.),'maximum_authored_normal_alignment_error':max_normal_error,'F_flagged_contact_rows':len(flagged['rows']),'F_flagged_paths':len(flagged_paths),'F_flagged_paths_with_closure_geometry':sum(r['F_contact_flagged'] and r.get('closure_faces',0)>0 for r in owner_report),'render_gap_cap_m':max_gap,'max_gap_policy':'Whole original edge held when gap exceeds cap; never truncated floating skirt','residual_analysis':{'all_triangle_centroids':len(tri),'all_centroid_abs_residual_p50_p95_max_m':np.percentile(res,[50,95,100]).tolist(),'original_every23_abs_residual_p50_p95_max_m':np.percentile(res[sampled],[50,95,100]).tolist(),'worst_cases':worst,'ground_regenerated':False},'limits':['Estimated visualbase/slabedge closure, not surveyedfoundation/basement/ADAgrade','Negativegroundpenetrations/largegaps remainheld; geometryadditiondoesnotresolve originalbuildinggradeaccuracy','Body/roof/XY/identity/materialdefinitions/visibility untouched','No terrainchange or engineeringclosure; actualvisualreview pending']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return {'layer':manifest['layer'],'layer_sha256':manifest['layer_sha256'],'closure_meshes':len(applied),'faces':generated_faces,'F_flagged_paths_with_closures':manifest['F_flagged_paths_with_closure_geometry'],'held_records':len(held),'manifest_sha256':sha(output/'manifest.json'),'coarse_all_centroid_residual_max_m':float(res.max())}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--max-gap',type=float,default=.75)
    parser.add_argument('--building-folder',default=FOLDER)
    parser.add_argument('--review-scene',default=SCENE)
    args=parser.parse_args()
    print(json.dumps(build(ROOT/args.output,max_gap=args.max_gap,building_folder=args.building_folder,review_scene=args.review_scene),indent=2))
