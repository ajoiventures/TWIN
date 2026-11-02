"""Prepare reversible Church source-group clipping, never active source writes.

Reuses Princeton's partial source-footprint subtraction policy, but clips each
original planar surface and interpolates its original UVs instead of replacing
all retained wings with a new parcel extrusion. Run with --output <new diagnostic
folder>. Original roof heights, material bindings and ambiguous identity remain.
Original legacy bodies are open-bottom render shells, not closed solid surveys.
"""
from pathlib import Path
import os,sys,json,hashlib,argparse
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np,shapely
from shapely.geometry import Polygon,LineString,box,mapping
from shapely.ops import unary_union
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
from pyproj import Transformer
from correct_wellesley import polygon_parts
EXPECTED={'Building_2919':{'building_number':'1','ids':{'1164930','1185989','1175733','1172347','1178840','1174819','1182924'}},
          'Building_3065':{'building_number':'2','ids':{'1186545','1165872','1177992'}}}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def projected_mesh(prim):
    mesh=UsdGeom.Mesh(prim);p=np.array(mesh.GetPointsAttr().Get(),float);ct=mesh.GetFaceVertexCountsAttr().Get();ix=mesh.GetFaceVertexIndicesAttr().Get();at=0;parts=[]
    for n in ct:
        face=p[np.array(ix[at:at+n])];at+=n;polygon=Polygon(face[:,:2])
        if polygon.is_valid and polygon.area>1e-8:parts.append(polygon)
    return unary_union(parts)

def clip_faces(prim,mask):
    mesh=UsdGeom.Mesh(prim);p=np.array(mesh.GetPointsAttr().Get(),float);ct=mesh.GetFaceVertexCountsAttr().Get();ix=np.array(mesh.GetFaceVertexIndicesAttr().Get(),int)
    matrix=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    if matrix!=Gf.Matrix4d(1):raise ValueError('Source target transform changed; reconcile clipping frame')
    pv=UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st');uv=np.array(pv.ComputeFlattened(),float) if pv and pv.Get() else None
    if uv is not None and (pv.GetInterpolation()!='faceVarying' or len(uv)!=len(ix)):raise ValueError('Unsupported source UV contract')
    points=[];tex=[];face_rows=[];at=0;removed_area=0.;retained_area=0.;uv_residual=0.
    for face_index,n in enumerate(ct):
        face=p[ix[at:at+n]];faceuv=uv[at:at+n] if uv is not None else None;at+=n
        cross=np.cross(face[1]-face[0],face[2]-face[0]);length=np.linalg.norm(cross)
        if length<1e-9:raise ValueError('Degenerate original source face')
        normal=cross/length
        if abs(normal[2])>1e-8:
            local=face[:,:2];polygon=Polygon(local);kept=polygon.difference(mask)
            def expand(q):return np.array([q[0],q[1],face[0,2]-(normal[0]*(q[0]-face[0,0])+normal[1]*(q[1]-face[0,1]))/normal[2]])
            area_factor=1/abs(normal[2])
        else:
            delta=next((v[:2]-face[0,:2] for v in face[1:] if np.linalg.norm(v[:2]-face[0,:2])>1e-8),None)
            if delta is None:raise ValueError('Invalid vertical source face')
            direction=delta/np.linalg.norm(delta);station=(face[:,:2]-face[0,:2])@direction;local=np.c_[station,face[:,2]];polygon=Polygon(local)
            line=LineString([face[0,:2]+direction*station.min(),face[0,:2]+direction*station.max()]);remaining=line.difference(mask);pieces=[]
            for segment in shapely.get_parts(remaining):
                if segment.geom_type!='LineString' or segment.length<1e-8:continue
                t=(np.array(segment.coords)-face[0,:2])@direction;pieces.append(polygon.intersection(box(t.min(),face[:,2].min()-1,t.max(),face[:,2].max()+1)))
            kept=unary_union(pieces)
            def expand(q):return np.r_[face[0,:2]+direction*q[0],q[1]]
            area_factor=1.
        if not polygon.is_valid:raise ValueError('Nonplanar/self-crossing original source face')
        removed_area+=(polygon.area-kept.area)*area_factor;retained_area+=kept.area*area_factor
        coeff=None
        if faceuv is not None:
            A=np.c_[local,np.ones(len(local))];coeff=np.linalg.lstsq(A,faceuv,rcond=None)[0]
            uv_residual=max(uv_residual,float(np.max(abs(A@coeff-faceuv))))
            if uv_residual>2e-5:raise ValueError('Non-affine original UVs require separate treatment')
        before=len(points)
        for polygon_part in polygon_parts(kept):
            for triangle in shapely.constrained_delaunay_triangles(polygon_part).geoms:
                q=np.array(list(triangle.exterior.coords)[:3]);v=np.array([expand(x) for x in q])
                if np.dot(np.cross(v[1]-v[0],v[2]-v[0]),normal)<0:v=v[::-1];q=q[::-1]
                v=v.astype(np.float32).astype(float)
                if np.linalg.norm(np.cross(v[1]-v[0],v[2]-v[0]))<1e-8:raise ValueError('Retained face collapsed in float serialization')
                points.extend(v.tolist())
                if coeff is not None:tex.extend((np.c_[q,np.ones(3)]@coeff).tolist())
        face_rows.append({'original_face':face_index,'original_surface_area_m2':polygon.area*area_factor,'retained_surface_area_m2':kept.area*area_factor,'output_triangles':(len(points)-before)//3})
    return points,tex,{'original_faces':len(ct),'retained_original_surface_area_m2':retained_area,'removed_original_surface_area_m2':removed_area,'face_provenance':face_rows,'maximum_original_face_uv_affine_fit_residual':uv_residual,'uv_policy':'Affine interpolation of each original face UVs; no replacement texture coordinates for retained surfaces'}

def author(stage,source,mask):
    points,uv,proof=clip_faces(source,mask);prim=stage.OverridePrim(source.GetPath())
    if not points:
        UsdGeom.Imageable(prim).CreateVisibilityAttr('invisible');proof['action']='only_this_mesh_fully_inside_replacement_projection';return proof
    mesh=UsdGeom.Mesh(prim);mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr([3]*(len(points)//3));mesh.CreateFaceVertexIndicesAttr(list(range(len(points))));mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
    mesh.CreateExtentAttr([Gf.Vec3f(*np.min(points,axis=0)),Gf.Vec3f(*np.max(points,axis=0))])
    # Original body has no authored normals. New faces preserve planar surface
    # orientation; block stale normals rather than indexing an old-size array.
    mesh.CreateNormalsAttr().Block()
    if uv:
        var=UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying);var.Set(uv);prim.CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block()
    prim.SetCustomDataByKey('displayMask',{'quality':'source_surface_remainder_only_not_physical_identity_acceptance','sourcePrim':str(source.GetPath()),'originalIdentityUnchanged':True})
    proof['action']='retain_every_original_surface_outside_candidate_projection';proof['output_triangles']=len(points)//3;return proof

def build(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Use new diagnostic folder')
    active=root/'data/processed/active.json';snapshot=json.loads(active.read_text())['snapshot'];assembly=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(assembly));v3folder=root/'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3';manifest=json.loads((v3folder/'manifest.json').read_text());v3=Usd.Stage.Open(str(v3folder/'site.usda'));candidate=v3.GetPrimAtPath(manifest['candidate_mesh_prim']);mask=projected_mesh(candidate)
    dependencies={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in [Path(__file__),root/'tools/correct_wellesley.py',assembly,active,v3folder/'manifest.json',v3folder/'site.usda',v3folder/'review.usda',root/'data/buildings.geojson']}
    for layer in source.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath).resolve();dependencies[str(p.relative_to(root)).replace('\\','/')]=sha(p)
    proposal=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(proposal,'Z');UsdGeom.SetStageMetersPerUnit(proposal,1);records=[]
    raw={str(f['properties']['OBJECTID']):f for f in json.loads((root/'data/buildings.geojson').read_text())['features']}
    transformer=Transformer.from_crs(4326,32617,always_xy=True);origin=Transformer.from_crs(4326,32617,always_xy=True).transform(-81.389,28.572)
    for name,expected in EXPECTED.items():
        prim=source.GetPrimAtPath('/World/Buildings/'+name);data=prim.GetCustomData()
        if data.get('parcelId')!='292214146004210' or str(data.get('buildingNumber'))!=expected['building_number'] or set(data.get('sourceObjectIds','').split(','))!=expected['ids']:raise ValueError('Legacy source identity changed')
        original=projected_mesh(prim);overlap=original.intersection(mask);remainder=original.difference(mask)
        row={'source_group':name,'source_pid':data['parcelId'],'source_object_ids':sorted(expected['ids']),'assigned_pid':data['official']['parcel_id'],'assigned_link_accepted':data['official']['match_accepted'],'source_area_m2':original.area,'actual_projection_overlap_m2':overlap.area,'retained_remainder_area_m2':remainder.area,'original_material':str(UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0].GetPath())}
        component_geometries=[];component_rows=[]
        for oid in sorted(expected['ids']):
            feature=raw[oid];properties=feature['properties']
            if properties['PID']!=data['parcelId'] or str(properties['BLDG_NUM'])!=expected['building_number']:raise ValueError('Original footprint component identity changed')
            absolute=shapely.transform(__import__('shapely.geometry',fromlist=['shape']).shape(feature['geometry']),transformer.transform,interleaved=False)
            geometry=shapely.transform(absolute,lambda x,y:(x-origin[0],y-origin[1]),interleaved=False);component_geometries.append(geometry)
            component_rows.append({'source_object_id':oid,'source_pid':properties['PID'],'building_number':properties['BLDG_NUM'],'floor_num_original':properties['FLOOR_NUM'],'original_area_m2':geometry.area,'inside_candidate_m2':geometry.intersection(mask).area,'outside_candidate_m2':geometry.difference(mask).area})
        row['original_source_components']=component_rows
        row['raw_component_union_vs_model_footprint_symdiff_m2']=unary_union(component_geometries).symmetric_difference(original).area
        if overlap.area<=.001:row['action']='leave_entire_group_roof_and_storefront_unmodified';records.append(row);continue
        row['body']=author(proposal,prim,mask);roof=source.GetPrimAtPath('/World/Roofs/Roof_'+name.split('_')[-1]);row['roof']=author(proposal,roof,mask);row['derived_storefronts']=[]
        storefront=source.GetPrimAtPath('/World/Storefronts/'+name)
        if storefront:
            for p in Usd.PrimRange(storefront):
                if p.IsA(UsdGeom.Mesh):row['derived_storefronts'].append({'prim':str(p.GetPath()),**author(proposal,p,mask)})
        records.append(row)
    output.mkdir(parents=True);proposal.GetRootLayer().customLayerData={'sourceSnapshot':snapshot,'proposalOnly':True,'maskPolicy':'Exact original-surface clipping outside v3 roof projection; source identity ambiguity preserved; not whole campus hide'};proposal.GetRootLayer().Export(str(output/'legacy_mask.usda'))
    review=Usd.Stage.CreateInMemory();review.GetRootLayer().subLayerPaths=[str(output/'legacy_mask.usda'),str(v3folder/'site.usda'),str(assembly)];UsdGeom.SetStageUpAxis(review,'Z');UsdGeom.SetStageMetersPerUnit(review,1)
    camera_path='/World/Cameras/SanctuarySourceCandidate';Sdf.CreatePrimInLayer(review.GetRootLayer(),'/World/Cameras')
    Sdf.CopySpec(Sdf.Layer.FindOrOpen(str(v3folder/'review.usda')),camera_path,review.GetRootLayer(),camera_path)
    review.GetRootLayer().Export(str(output/'review.usda'));composed=Usd.Stage.Open(str(output/'review.usda'));checks=[]
    if composed.GetCompositionErrors():raise ValueError('Mask review composition failed')
    for row in records:
        if 'body' not in row:continue
        name=row['source_group'];p=composed.GetPrimAtPath('/World/Buildings/'+name);actual=projected_mesh(p);expected=projected_mesh(source.GetPrimAtPath(p.GetPath())).difference(mask);body=UsdGeom.Mesh(p);z=[float(q[2]) for q in body.GetPointsAttr().Get()];oldz=[float(q[2]) for q in UsdGeom.Mesh(source.GetPrimAtPath(p.GetPath())).GetPointsAttr().Get()]
        if actual.symmetric_difference(expected).area>.01 or abs(min(z)-min(oldz))>1e-5 or abs(max(z)-max(oldz))>1e-5:raise ValueError('Legacy remainder geometry or height not preserved')
        if str(UsdShade.MaterialBindingAPI(p).ComputeBoundMaterial()[0].GetPath())!=row['original_material']:raise ValueError('Retained material changed')
        roof_path='/World/Roofs/Roof_'+name.split('_')[-1];roof_before=UsdGeom.Mesh(source.GetPrimAtPath(roof_path));roof_after=UsdGeom.Mesh(composed.GetPrimAtPath(roof_path));roof_expected=projected_mesh(roof_before.GetPrim()).difference(mask);roof_actual=projected_mesh(roof_after.GetPrim());old_roof_z=sorted(set(float(q[2]) for q in roof_before.GetPointsAttr().Get()));new_roof_z=sorted(set(float(q[2]) for q in roof_after.GetPointsAttr().Get()))
        if roof_actual.symmetric_difference(roof_expected).area>.01 or old_roof_z!=new_roof_z:raise ValueError('Retained roof area or elevation changed')
        checks.append({'group':name,'remainder_footprint_symdiff_m2':actual.symmetric_difference(expected).area,'remaining_inside_mask_m2':actual.intersection(mask).area,'z_range_unchanged':[min(z),max(z)],'material_unchanged':True,'roof_remainder_symdiff_m2':roof_actual.symmetric_difference(roof_expected).area,'roof_original_and_retained_z_m':old_roof_z})
    if any(sha(root/n)!=v for n,v in dependencies.items()):raise ValueError('Source changed during mask preparation')
    report={'schema':'twin.church-legacy-mask/1','source_snapshot':snapshot,'candidate_footprint_m2':mask.area,'groups':records,'remainder_checks':checks,'review_camera':camera_path,'dependencies':dependencies,'outputs':{n:sha(output/n) for n in ['legacy_mask.usda','review.usda']},'activated':False,'raw_links_promoted':False,'decision':'Technical exact-source remainder candidate ready; physical replacement and actual visual integration still pending','limits':['Building2919 bbox overlap was false positive; no original surfaces there removed.','Building3065 original body is already an open-bottom render shell; clipping preserves original exterior surfaces, not a new certified closed solid. Cut interface remains inside proposed replacement mass.','No cap, wallline, parcel extrusion, uniform new campus height or unrelated campus hide introduced.','Source UVs interpolated per original face; retained heights/materials/identity unchanged.','Derived storefront fragments outside roof mask are deliberately retained, including small end-protrusion strips; inspect with separate appearance layer before acceptance.','V3 roof envelope/overhang/wallline remains approximate; technical preservation does not certify historical/current architectural accuracy.']}
    (output/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({'groups':[{k:r[k] for k in ['source_group','source_area_m2','actual_projection_overlap_m2','retained_remainder_area_m2']} for r in records],'checks':checks,'manifest_sha256':sha(output/'manifest.json')},indent=2));return report

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();build(a.output)
