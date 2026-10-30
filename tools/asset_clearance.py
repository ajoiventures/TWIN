"""Reversible modeled-placement collision audit; never invents surveyed placement."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf,Gf,Work
Work.SetConcurrencyLimit(1)
from shapely.geometry import MultiPoint,Polygon,box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from build_corridor_ground import mesh_footprint

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def world_points(prim,cache,extra=None):
    points=UsdGeom.Mesh(prim).GetPointsAttr().Get()
    matrix=cache.GetLocalToWorldTransform(prim) if extra is None else extra
    return [matrix.Transform(Gf.Vec3d(p)) for p in points]

def footprint(points):return MultiPoint([(p[0],p[1]) for p in points]).convex_hull

def instance_mesh_points(instancer,index,prototype,mesh,cache,transforms=None):
    transforms=transforms if transforms is not None else instancer.ComputeInstanceTransformsAtTime(Usd.TimeCode.Default(),Usd.TimeCode.Default(),UsdGeom.PointInstancer.IncludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
    relative=cache.GetLocalToWorldTransform(mesh)*cache.GetLocalToWorldTransform(prototype).GetInverse()
    matrix=relative*transforms[index]*cache.GetLocalToWorldTransform(instancer.GetPrim())
    return world_points(mesh,cache,matrix)

def add_inactive_ids(stage,path,ids):
    if not ids:return
    # inactiveIds is a list operation, unlike the replacement invisibleIds
    # array. Prepending additions preserves independent extent/user masks.
    prim=stage.OverridePrim(path)
    prim.SetMetadata('inactiveIds',Sdf.Int64ListOp.Create(prependedItems=sorted(set(ids))))

def collision_records(geometry,low,high,records,index):
    result=[]
    if geometry.is_empty or geometry.area<=1e-8:return result
    for identifier in index.query(geometry) if index is not None else []:
        row=records[int(identifier)]
        if high<=row['low']+.02 or low>=row['high']-.02:continue
        overlap=geometry.intersection(row['geometry']).area
        if overlap>.02 and overlap/geometry.area>.2:
            result.append({'path':row['path'],'kind':row['kind'],'overlap_m2':round(overlap,4),'fraction':round(overlap/geometry.area,4)})
    return result

def build(root=ROOT):
    root=Path(root).resolve();source_path=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(source_path));cache=UsdGeom.XformCache();bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'])
    active=json.loads((root/'data/processed/active.json').read_text());dependencies={str(Path(layer.realPath).relative_to(root)).replace('\\','/'):sha(Path(layer.realPath)) for layer in source.GetUsedLayers() if layer.realPath and Path(layer.realPath).is_relative_to(root)}
    objects=[];roads=[];water=[];parking=[]
    for scope,kind in [('Buildings','building'),('Landmarks','building'),('Water','water'),('Streets','carriageway'),('RearParkingSamples','parking')]:
        parent=source.GetPrimAtPath('/World/'+scope)
        if not parent:continue
        for prim in Usd.PrimRange(parent):
            if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
            if scope=='Streets' and not prim.GetName().startswith('Road_'):continue
            geometry=mesh_footprint(prim,cache)
            if geometry.is_empty or geometry.area<=0:continue
            bound=bounds.ComputeWorldBound(prim).ComputeAlignedRange();low=float(bound.GetMin()[2]);high=float(bound.GetMax()[2])
            row={'path':str(prim.GetPath()),'kind':kind,'geometry':geometry,'low':low,'high':high}
            if kind=='building':objects.append(row)
            elif kind=='water':water.append(row)
            elif kind=='carriageway':roads.append(row)
            else:parking.append(row)
    solid_index=STRtree([row['geometry'] for row in objects]) if objects else None
    road_geometry=unary_union([row['geometry'] for row in roads]);water_geometry=unary_union([row['geometry'] for row in water]);parking_geometry=unary_union([row['geometry'] for row in parking])
    instancer=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'));positions=instancer.GetPositionsAttr().Get();ids=list(instancer.GetIdsAttr().Get() or range(len(positions)))
    prototype_indices=instancer.GetProtoIndicesAttr().Get();targets=instancer.GetPrototypesRel().GetTargets();mask=list(instancer.ComputeMaskAtTime(Usd.TimeCode.Default())) or [True]*len(ids)
    transforms=instancer.ComputeInstanceTransformsAtTime(Usd.TimeCode.Default(),Usd.TimeCode.Default(),UsdGeom.PointInstancer.IncludeProtoXform,UsdGeom.PointInstancer.IgnoreMask)
    trunk_meshes={};foliage_bounds={}
    for target in targets:
        proto=source.GetPrimAtPath(target)
        trunk_meshes[str(target)]=[p for p in Usd.PrimRange(proto,Usd.TraverseInstanceProxies()) if p.IsA(UsdGeom.Mesh) and p.GetName()=='Trunk']
        foliage=Gf.Range3d()
        for prim in Usd.PrimRange(proto,Usd.TraverseInstanceProxies()):
            if not prim.IsA(UsdGeom.Mesh) or not prim.GetName().startswith(('Foliage','Canopy','Crown')):continue
            relative=cache.GetLocalToWorldTransform(prim)*cache.GetLocalToWorldTransform(proto).GetInverse()
            for point in UsdGeom.Mesh(prim).GetPointsAttr().Get():foliage.UnionWith(relative.Transform(Gf.Vec3d(point)))
        foliage_bounds[str(target)]=foliage
    hidden_trees=[];tree_rows=[];canopy_queue=[];valid_trunks=[]
    for i,identifier in enumerate(ids):
        if not mask[i]:continue
        target=targets[prototype_indices[i]];proto=source.GetPrimAtPath(target);points=[]
        for mesh in trunk_meshes[str(target)]:points.extend(instance_mesh_points(instancer,i,proto,mesh,cache,transforms))
        if not points:
            tree_rows.append({'id':identifier,'action':'review','reason':'No explicit trunk mesh; canopy bounds are not a trunk substitute.'});continue
        bottom=min(p[2] for p in points);base_points=[p for p in points if p[2]<=bottom+.6]
        trunk_base=footprint(base_points);trunk_low=footprint([p for p in points if p[2]<=bottom+2.2])
        collisions=collision_records(trunk_low,bottom,bottom+2.2,objects,solid_index)
        water_overlap=trunk_base.intersection(water_geometry).area
        road_overlap=trunk_base.intersection(road_geometry).area
        # These are unequivocal contradictions of this composed MODEL, not
        # certification that real roadway widths or actual trees are wrong.
        if water_overlap>.02 and water_overlap/max(trunk_base.area,1e-9)>.5:collisions.append({'kind':'water','overlap_m2':round(water_overlap,4)})
        if road_overlap>.02 and road_overlap/max(trunk_base.area,1e-9)>.8:collisions.append({'kind':'modeled_carriageway_trunk','overlap_m2':round(road_overlap,4),'road_edge_accuracy':'unverified OSM width fallback'})
        action='hide' if collisions else 'retain'
        if collisions:hidden_trees.append(identifier)
        else:valid_trunks.append({'id':identifier,'geometry':trunk_low,'low':bottom,'high':bottom+2.2,'path':f'/World/Trees instance {identifier}','kind':'trunk'})
        tree_rows.append({'id':identifier,'index':i,'action':action,'trunk_base_area_m2':round(trunk_base.area,4),'collisions':collisions})
        foliage=foliage_bounds[str(target)]
        if foliage.IsEmpty():continue
        canopy=Gf.BBox3d(foliage,transforms[i]*cache.GetLocalToWorldTransform(instancer.GetPrim())).ComputeAlignedRange();low=canopy.GetMin();high=canopy.GetMax()
        possible=collision_records(box(low[0],low[1],high[0],high[1]),low[2],high[2],objects,solid_index)
        if possible:canopy_queue.append({'id':identifier,'action':'review_only_canopy_bbox_not_proof','candidates':possible,'hidden_for_canopy':False})
    trunk_index=STRtree([r['geometry'] for r in valid_trunks]) if valid_trunks else None
    car_rows=[];hidden_cars=[];kept_bodies=[]
    parent=source.GetPrimAtPath('/World/ParkedVehicles');car_roots=list(parent.GetChildren()) if parent else []
    car_pre_hidden=[]
    for car in car_roots:
        if UsdGeom.Imageable(car).ComputeVisibility()=='invisible':car_pre_hidden.append(str(car.GetPath()));continue
        body_points=[];wheel_points=[]
        for prim in Usd.PrimRange(car,Usd.TraverseInstanceProxies()):
            if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
            if prim.GetName()=='Body':body_points.extend(world_points(prim,cache))
            if prim.GetName().startswith('Wheel_') and not any(token in prim.GetName() for token in ('Rim','Spoke')):wheel_points.append(world_points(prim,cache))
        if not body_points:
            car_rows.append({'path':str(car.GetPath()),'action':'review','reason':'No visible body geometry'});continue
        body=footprint(body_points);low=min(p[2] for p in body_points);high=max(p[2] for p in body_points)
        wheels=unary_union([footprint([p for p in group if p[2]<=min(q[2] for q in group)+.15]) for group in wheel_points])
        collisions=collision_records(body,low,high,objects,solid_index)+collision_records(body,low,high,valid_trunks,trunk_index)
        for other in kept_bodies:
            area=body.intersection(other['geometry']).area
            if area>.2 and min(high,other['high'])-max(low,other['low'])>.1:collisions.append({'kind':'vehicle_body','path':other['path'],'overlap_m2':round(area,4)})
        water_overlap=wheels.intersection(water_geometry).area
        if water_overlap>.02:collisions.append({'kind':'wheel_contacts_in_modeled_water','overlap_m2':round(water_overlap,4)})
        if collisions:hidden_cars.append(str(car.GetPath()))
        else:kept_bodies.append({'path':str(car.GetPath()),'geometry':body,'low':low,'high':high})
        car_rows.append({'path':str(car.GetPath()),'action':'hide' if collisions else 'retain','collisions':collisions,
            'wheel_contact_area_m2':round(wheels.area,4),'wheel_road_overlap_m2':round(wheels.intersection(road_geometry).area,4),
            'wheel_parking_reference_overlap_m2':round(wheels.intersection(parking_geometry).area,4),
            'parking_status':'unknown; roadside overlap may be legal curb parking, no stall/access acceptance',
            'road_overlap_action':'review_only_not_a_traffic_or_parking_lane_inventory'})
    layer=Usd.Stage.CreateInMemory();add_inactive_ids(layer,'/World/Trees',hidden_trees)
    for path in hidden_cars:UsdGeom.Imageable(layer.OverridePrim(path)).CreateVisibilityAttr('invisible')
    report={'source_snapshot':active['snapshot'],'source_root_sha256':sha(source_path),'dependency_sha256':dependencies,
        'tree_instances_total':len(ids),'tree_preexisting_masked':sum(not v for v in mask),'tree_visible_audited':sum(mask),'tree_new_hidden_ids':hidden_trees,
        'cars_total':len(car_roots),'car_preexisting_hidden':car_pre_hidden,'car_new_hidden_paths':hidden_cars,'trees':tree_rows,'cars':car_rows,'canopy_review_queue':canopy_queue,
        'policy':'Hide only modeled low-trunk/building/water/carriageway or vehicle-body/building/trunk/vehicle/wheel-water collisions. No relocations. Canopy bounds and parking/roadside context are review only.',
        'limitations':['Road widths, sidewalk edges and parking inventory remain unverified; model conflicts do not establish real-world errors.','Canopy bounding boxes overestimate sparse foliage; no trees hidden for canopy overlap alone.','Wheel contact projections approximate tire geometry; no ground-grade, suspension, ADA or traffic validation.','User and extent masks are preserved; no source arrays, transforms or assets changed.'],
        'relocations':0,'source_files_changed':False}
    layer.GetRootLayer().customLayerData={'purpose':'Inactive reversible asset model-clearance proposal; not surveyed placement','sourceSnapshot':active['snapshot'],'treeMaskPolicy':'inactiveIds prepend preserves independent invisibleIds/extent masks','auditJson':json.dumps({k:v for k,v in report.items() if k not in ('trees','cars','canopy_review_queue')},sort_keys=True)}
    output=root/'scene/asset_clearance_proposal.usda'
    if any(sha(root/name)!=digest for name,digest in dependencies.items()):raise ValueError('Composed dependency changed during audit')
    layer.GetRootLayer().Export(str(output));report['proposal_sha256']=sha(output)
    folder=root/'data/diagnostics/asset_clearance';folder.mkdir(parents=True,exist_ok=True);(folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('trees','cars','canopy_review_queue','dependency_sha256','car_preexisting_hidden')},indent=2));return report

if __name__=='__main__':build()
