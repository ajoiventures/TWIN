"""Compose an inactive full-corridor civil/environment workview with fixed cameras."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import hashlib,json,math,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdUtils,Gf
from shapely.geometry import shape,box
from shapely.ops import transform,unary_union
from pyproj import Transformer
from build_corridor_ground import mesh_footprint

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(root=ROOT):
    # Preserve user opinions and the accepted display extent above every draft.
    layer_names=[name for name in ('manual_edits.usda','map_extent_guard.usda') if (root/'scene'/name).exists()]
    layer_names+=['corridor_ground_proposal.usda','asset_upgrade_proposal.usda','college_park_connected.usda']
    inputs={name:sha(root/'scene'/name) for name in layer_names}
    report=json.loads((root/'data/transport/corridor_ground_report.json').read_text())
    if inputs['corridor_ground_proposal.usda']!=report['layer_sha256']:raise ValueError('Corridor proposal/report hash mismatch')
    active=json.loads((root/'data/processed/active.json').read_text())
    if active['snapshot']!=report['source_snapshot']:raise ValueError('Corridor ground snapshot is stale')
    output=root/'scene/corridor_workview.usda'
    stage=Usd.Stage.CreateInMemory();stage.GetRootLayer().subLayerPaths=[str(root/'scene'/name) for name in layer_names]
    UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    stage.SetDefaultPrim(stage.GetPrimAtPath('/World'))
    study=json.loads((root/'config/study_area.json').read_text());projection=Transformer.from_crs(4326,32617,always_xy=True)
    ox,oy=projection.transform(*study['local_origin_wgs84'])
    def local(x,y,z=None):a,b=projection.transform(x,y);return a-ox,b-oy
    features=json.loads((root/'data/processed/study_boundaries.geojson').read_text())['features']
    main=transform(local,shape(next(f['geometry'] for f in features if f['id']=='main_street')))
    cache=UsdGeom.XformCache();ground=mesh_footprint(stage.GetPrimAtPath('/World/Ground'),cache)
    cameras=[]
    def camera(name,bounds,offset,focal=38):
        x0,y0,x1,y1=bounds;target=Gf.Vec3d((x0+x1)/2,(y0+y1)/2,2)
        important=Gf.Range3d(Gf.Vec3d(x0,y0,0),Gf.Vec3d(x1,y1,35))
        schema=UsdGeom.Camera.Define(stage,'/World/Cameras/'+name)
        schema.CreateFocalLengthAttr(focal);schema.CreateHorizontalApertureAttr(36);schema.CreateVerticalApertureAttr(20.25)
        schema.CreateClippingRangeAttr(Gf.Vec2f(.1,20000));operation=schema.AddTransformOp()
        for step in range(30):
            eye=target+Gf.Vec3d(*offset)*(1.08**step)
            operation.Set(Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse())
            frustum=schema.GetCamera().frustum;clip=frustum.ComputeViewMatrix()*frustum.ComputeProjectionMatrix()
            projected=[clip.Transform(important.GetCorner(i)) for i in range(8)]
            if all(abs(p[0])<=.9 and abs(p[1])<=.9 and -1<p[2]<1 for p in projected):break
        else:raise ValueError('Cannot frame camera '+name)
        schema.GetPrim().SetCustomData({'purpose':'Fixed review camera; no automatic selection tracking','renderAspect':'16:9','framing':'All review bounds corners within NDC ±0.9'})
        cameras.append({'name':name,'path':str(schema.GetPath()),'eye':list(eye),'target':list(target),'focal_mm':focal,'review_bounds':list(bounds),'max_abs_ndc_xy':max(abs(p[i]) for p in projected for i in (0,1))})
    span=max(ground.bounds[2]-ground.bounds[0],ground.bounds[3]-ground.bounds[1])
    camera('CivilDistrictOverview',ground.bounds,(span*.9,-span*1.1,span*1.25),36)
    span=max(main.bounds[2]-main.bounds[0],main.bounds[3]-main.bounds[1])
    camera('CivilMainStreetOverview',main.buffer(22).bounds,(span*.6,-span*.75,span*1.0),42)
    junction=json.loads((root/'data/transport/princeton_road_review.json').read_text())['junction_utm17_m']
    x,y=junction[0]-ox,junction[1]-oy
    camera('CivilPrincetonEdgewater',(x-100,y-135,x+100,y+135),(230,-290,280),38)
    # Check actual composition, not only each proposal in isolation.
    blocks=[];roads=[]
    for name,target in [('Buildings',blocks),('Landmarks',blocks),('Water',blocks),('Streets',roads)]:
        parent=stage.GetPrimAtPath('/World/'+name)
        if not parent:continue
        for prim in Usd.PrimRange(parent):
            if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
            if name=='Streets' and not prim.GetName().startswith('Road_'):continue
            target.append(mesh_footprint(prim,cache))
    obstacles=unary_union(blocks);road_union=unary_union(roads)
    overlap=[];mesh_count=0;points_count=0
    for prim in Usd.PrimRange(stage.GetPrimAtPath('/World/CorridorGround')):
        if not prim.IsA(UsdGeom.Mesh):continue
        mesh=UsdGeom.Mesh(prim);points=mesh.GetPointsAttr().Get();ids=mesh.GetFaceVertexIndicesAttr().Get();counts=mesh.GetFaceVertexCountsAttr().Get()
        if sum(counts)!=len(ids) or any(i<0 or i>=len(points) for i in ids) or any(not math.isfinite(v) for p in points for v in p):raise ValueError('Invalid mesh '+str(prim.GetPath()))
        g=mesh_footprint(prim,cache)
        row={'path':str(prim.GetPath()),'road_overlap_m2':g.intersection(road_union).area,'visible_building_water_overlap_m2':g.intersection(obstacles).area,'outside_ground_m2':g.difference(ground).area}
        if max(row[k] for k in row if k!='path')>.03:raise ValueError('Composed geometry conflict '+json.dumps(row))
        overlap.append(row);mesh_count+=1;points_count+=len(points)
    if any(sha(root/'scene'/name)!=digest for name,digest in inputs.items()):raise ValueError('Input layer changed during workview build; retry')
    validation={'source_snapshot':active['snapshot'],'layer_strength_order':layer_names,'input_sha256':inputs,
                'cameras':cameras,'corridor_meshes_checked':mesh_count,'corridor_points_checked':points_count,
                'composed_surface_overlap_checks':overlap,'environment_placement':'Inherited proposal arrays/transforms; vegetation/vehicle clearance remains review, not certified.',
                'ground_report_connected_hash_matches':report['dependencies']['scene/college_park_connected.usda']==inputs['college_park_connected.usda']}
    stage.GetRootLayer().customLayerData={'purpose':'Inactive combined full Main Street civil/environment workview; explicit parent review before any active composition change.','sourceSnapshot':active['snapshot'],'validationJson':json.dumps(validation,sort_keys=True)}
    # Relative sublayers retain all original references in their owning layers.
    stage.GetRootLayer().Export(str(output))
    composed=Usd.Stage.Open(str(output))
    composed.GetRootLayer().subLayerPaths=layer_names
    composed.GetRootLayer().Save()
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(output))
    if unresolved:raise ValueError('Unresolved workview dependencies: '+str(unresolved))
    validation.update({'output':str(output),'layer_sha256':sha(output),'resolved_layers':len(layers),'resolved_assets':len(assets),'unresolved_assets':list(unresolved)})
    (root/'data/transport/corridor_workview.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in validation.items() if key!='composed_surface_overlap_checks'},indent=2));return validation

if __name__=='__main__':build()
