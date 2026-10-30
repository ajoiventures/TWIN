"""Hide out-of-map illustrative objects in an additive, reversible display layer."""
from pathlib import Path
import sys,json,datetime,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf,Gf
from shapely.geometry import Polygon,box,LineString,Point
from shapely.ops import unary_union
from data_pipeline import atomic_json

def ground_footprint(stage):
    return mesh_footprint(stage.GetPrimAtPath('/World/Ground'))

def mesh_footprint(prim):
    m=UsdGeom.Mesh(prim);pts=m.GetPointsAttr().Get();indices=m.GetFaceVertexIndicesAttr().Get();counts=m.GetFaceVertexCountsAttr().Get();parts=[];offset=0
    for n in counts:
        parts.append(Polygon([(pts[i][0],pts[i][1]) for i in indices[offset:offset+n]]));offset+=n
    return unary_union(parts)

def fits(bounds,footprint,tolerance=.03):
    lo,hi=bounds.GetMin(),bounds.GetMax()
    return footprint.buffer(tolerance).covers(box(lo[0],lo[1],hi[0],hi[1]))

def object_fits(prim,cache,transforms,footprint):
    bounds=cache.ComputeWorldBound(prim).ComputeAlignedRange()
    if bounds.IsEmpty() or fits(bounds,footprint):return True
    buffered=footprint.buffer(.03)
    # A world-axis bounding box can cross a slanted map edge even when a
    # clipped mesh is fully inside it. Inspect transformed mesh vertices.
    for child in Usd.PrimRange(prim,Usd.TraverseInstanceProxies()):
        if not child.IsA(UsdGeom.Imageable) or UsdGeom.Imageable(child).ComputeVisibility()=='invisible':continue
        if child.IsA(UsdGeom.Mesh):
            matrix=transforms.GetLocalToWorldTransform(child)
            for p in UsdGeom.Mesh(child).GetPointsAttr().Get() or []:
                q=matrix.Transform(Gf.Vec3d(*p))
                if not buffered.covers(Point(q[0],q[1])):return False
        elif child.IsA(UsdGeom.Boundable) and not fits(cache.ComputeWorldBound(child).ComputeAlignedRange(),footprint):return False
    return True

def reconstruction_volumes(stage,cache):
    """Conservative roof-zone volumes, never a surveyed clearance envelope."""
    project=stage.GetPrimAtPath('/World/Landmarks/PrincetonAtCollegePark')
    if not project or UsdGeom.Imageable(project).ComputeVisibility()=='invisible':return []
    volumes=[]
    for prim in Usd.PrimRange(project):
        if not prim.IsA(UsdGeom.Mesh):continue
        mesh=UsdGeom.Mesh(prim);points=mesh.GetPointsAttr().Get();indices=mesh.GetFaceVertexIndicesAttr().Get();offset=0;parts=[]
        matrix=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
        for count in mesh.GetFaceVertexCountsAttr().Get():
            coords=[matrix.Transform(Gf.Vec3d(*points[i])) for i in indices[offset:offset+count]];offset+=count
            polygon=Polygon([(p[0],p[1]) for p in coords])
            if polygon.is_valid and polygon.area>1e-6:parts.append(polygon)
        if parts:
            bounds=cache.ComputeWorldBound(prim).ComputeAlignedRange()
            volumes.append((unary_union(parts),float(bounds.GetMin()[2]),float(bounds.GetMax()[2])))
    return volumes

def intersects_reconstruction(bounds,volumes):
    if bounds.IsEmpty():return False
    lo,hi=bounds.GetMin(),bounds.GetMax();footprint=box(lo[0],lo[1],hi[0],hi[1])
    return any(hi[2]>bottom+.05 and lo[2]<top-.05 and footprint.intersection(roof).area>.02 for roof,bottom,top in volumes)

def constrain(root=ROOT):
    root=Path(root);assembly=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(assembly))
    # Inspect without the previous guard, so rebuilding is deterministic and reversible.
    guard=root/'scene/map_extent_guard.usda'
    if guard.exists():source.MuteLayer(str(guard.resolve()))
    ground=ground_footprint(source);cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'],useExtentsHint=False);transforms=UsdGeom.XformCache()
    volumes=reconstruction_volumes(source,cache)
    layer=Usd.Stage.CreateInMemory();hidden=[];clearance_objects=[]
    for scope in ['Buildings','Roofs','Streets','Storefronts','StreetFurniture','ParkedVehicles','Water','Parks']:
        for prim in source.GetPrimAtPath('/World/'+scope).GetChildren():
            if UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
            collision=scope in ['Storefronts','StreetFurniture','ParkedVehicles'] and intersects_reconstruction(cache.ComputeWorldBound(prim).ComputeAlignedRange(),volumes)
            if collision:clearance_objects.append(str(prim.GetPath()))
            if collision or not object_fits(prim,cache,transforms,ground):
                UsdGeom.Imageable(layer.OverridePrim(prim.GetPath())).CreateVisibilityAttr('invisible');hidden.append(str(prim.GetPath()))
    inst=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'));positions=inst.GetPositionsAttr().Get();ids=inst.GetIdsAttr().Get();ids=list(ids) if ids else list(range(len(positions)))
    outside=[];clearance_trees=[]
    for i in range(len(positions)):
        bounds=cache.ComputePointInstanceWorldBound(inst,i).ComputeAlignedRange()
        collision=intersects_reconstruction(bounds,volumes)
        if collision:clearance_trees.append(ids[i])
        if collision or not fits(bounds,ground):outside.append(ids[i])
    # Preserve existing invisibility unrelated to this generated layer.
    inherited=set(inst.GetInvisibleIdsAttr().Get() or [])
    tree=UsdGeom.PointInstancer(layer.OverridePrim('/World/Trees'));tree.CreateInvisibleIdsAttr(sorted(inherited|set(outside)))
    UsdGeom.Imageable(layer.OverridePrim('/World/Context/SurroundingGround')).CreateVisibilityAttr('invisible')
    layer.GetRootLayer().customLayerData={'purpose':'Display boundary and reconstruction overlap guard; source geometry retained','boundary':'actual base ground polygon, not official district boundary','tree_policy':'full transformed canopy bounds inside ground; conservative reconstruction overlap screen','reversible':True}
    layer.GetRootLayer().Export(str(guard))
    cached=Sdf.Layer.Find(str(guard))
    if cached:cached.Reload()
    root_layer=source.GetRootLayer();paths=[p for p in root_layer.subLayerPaths if p!='map_extent_guard.usda'];paths.insert(0,'map_extent_guard.usda');root_layer.subLayerPaths=paths;root_layer.Save()
    # Re-open to inspect actual composed visibility, including user edits.
    check=Usd.Stage.Open(str(assembly));check.GetRootLayer().Reload();visible_outside=[];cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']);transforms=UsdGeom.XformCache()
    for scope in ['Buildings','Roofs','Streets','Storefronts','StreetFurniture','ParkedVehicles','Water','Parks']:
        for prim in check.GetPrimAtPath('/World/'+scope).GetChildren():
            if UsdGeom.Imageable(prim).ComputeVisibility()!='invisible' and not object_fits(prim,cache,transforms,ground):visible_outside.append(str(prim.GetPath()))
    check_inst=UsdGeom.PointInstancer(check.GetPrimAtPath('/World/Trees'));mask=set(check_inst.GetInvisibleIdsAttr().Get() or []);tree_spill=[ids[i] for i in range(len(positions)) if ids[i] not in mask and not fits(cache.ComputePointInstanceWorldBound(check_inst,i).ComputeAlignedRange(),ground)]
    active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
    report={'source_snapshot':active['snapshot'],'base_geometry_sha256':hashlib.sha256((root/'scene/college_park.usda').read_bytes()).hexdigest(),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hidden_object_paths':hidden,'hidden_tree_ids':outside,'hidden_object_count':len(hidden),'hidden_tree_count':len(outside),'remaining_visible_object_spillovers':visible_outside,'remaining_visible_tree_spillovers':tree_spill,'original_geometry_deleted':False,'boundary':'actual rendered ground footprint; official scopes stored separately','context_backdrop_hidden':True}
    report['reconstruction_overlap_screen']={'conservative_object_paths':clearance_objects,'conservative_tree_ids':clearance_trees,'surveyed_clearance':False,'note':'Illustrative placements crossing reconstructed roof-zone volumes are reversibly hidden; this is not physical collision or pedestrian-clearance certification.'}
    check_volumes=reconstruction_volumes(check,cache)
    remaining=[]
    for scope in ['Storefronts','StreetFurniture','ParkedVehicles']:
        for prim in check.GetPrimAtPath('/World/'+scope).GetChildren():
            if UsdGeom.Imageable(prim).ComputeVisibility()!='invisible' and intersects_reconstruction(cache.ComputeWorldBound(prim).ComputeAlignedRange(),check_volumes):remaining.append(str(prim.GetPath()))
    remaining_trees=[ids[i] for i in range(len(positions)) if ids[i] not in mask and intersects_reconstruction(cache.ComputePointInstanceWorldBound(check_inst,i).ComputeAlignedRange(),check_volumes)]
    report['reconstruction_overlap_screen'].update({'remaining_visible_object_overlaps':remaining,'remaining_visible_tree_overlaps':remaining_trees})
    atomic_json(root/'data/processed/map_extent_quality.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['hidden_object_paths','hidden_tree_ids']},indent=2));return report

if __name__=='__main__':constrain()
