"""Hide out-of-map illustrative objects in an additive, reversible display layer."""
from pathlib import Path
import sys,json,datetime,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf,Gf
from shapely.geometry import Polygon,box,LineString,Point
from shapely.ops import unary_union
from data_pipeline import atomic_json

def ground_footprint(stage):
    m=UsdGeom.Mesh(stage.GetPrimAtPath('/World/Ground'));pts=m.GetPointsAttr().Get();indices=m.GetFaceVertexIndicesAttr().Get();counts=m.GetFaceVertexCountsAttr().Get();parts=[];offset=0
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

def constrain(root=ROOT):
    root=Path(root);assembly=root/'scene/college_park_connected.usda';source=Usd.Stage.Open(str(assembly))
    # Inspect without the previous guard, so rebuilding is deterministic and reversible.
    guard=root/'scene/map_extent_guard.usda'
    if guard.exists():source.MuteLayer(str(guard.resolve()))
    ground=ground_footprint(source);cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'],useExtentsHint=False);transforms=UsdGeom.XformCache()
    layer=Usd.Stage.CreateInMemory();hidden=[]
    for scope in ['Buildings','Roofs','Streets','Storefronts','StreetFurniture','ParkedVehicles','Water','Parks']:
        for prim in source.GetPrimAtPath('/World/'+scope).GetChildren():
            if UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
            if not object_fits(prim,cache,transforms,ground):
                UsdGeom.Imageable(layer.OverridePrim(prim.GetPath())).CreateVisibilityAttr('invisible');hidden.append(str(prim.GetPath()))
    inst=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'));positions=inst.GetPositionsAttr().Get();ids=inst.GetIdsAttr().Get();ids=list(ids) if ids else list(range(len(positions)))
    outside=[]
    for i in range(len(positions)):
        if not fits(cache.ComputePointInstanceWorldBound(inst,i).ComputeAlignedRange(),ground):outside.append(ids[i])
    # Preserve existing invisibility unrelated to this generated layer.
    inherited=set(inst.GetInvisibleIdsAttr().Get() or [])
    tree=UsdGeom.PointInstancer(layer.OverridePrim('/World/Trees'));tree.CreateInvisibleIdsAttr(sorted(inherited|set(outside)))
    UsdGeom.Imageable(layer.OverridePrim('/World/Context/SurroundingGround')).CreateVisibilityAttr('invisible')
    layer.GetRootLayer().customLayerData={'purpose':'Display boundary guard; source geometry retained','boundary':'actual base ground polygon, not official district boundary','tree_policy':'full transformed canopy bounding box inside ground','reversible':True}
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
    atomic_json(root/'data/processed/map_extent_quality.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['hidden_object_paths','hidden_tree_ids']},indent=2));return report

if __name__=='__main__':constrain()
