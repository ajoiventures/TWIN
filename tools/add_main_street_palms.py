"""Use original palm assets at three screened illustrative tree placements."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Gf
from shapely.geometry import Point,shape
from shapely.ops import unary_union,transform
from pyproj import Transformer
from constrain_scene import ground_footprint,mesh_footprint
from data_pipeline import atomic_json

def build():
    source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'))
    output=ROOT/'scene/main_street_palms.usda'
    if output.exists():source.MuteLayer(str(output.resolve()))
    trees=UsdGeom.PointInstancer(source.GetPrimAtPath('/World/Trees'))
    positions=trees.GetPositionsAttr().Get();indices=list(trees.GetProtoIndicesAttr().Get());scales=list(trees.GetScalesAttr().Get());hidden=set(trees.GetInvisibleIdsAttr().Get() or [])
    targets=trees.GetPrototypesRel().GetTargets()
    if len(targets)!=7 or targets[6].name!='Tree_6':raise ValueError('Detailed palm prototype mapping changed')
    project=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=project.transform(-81.389,28.572)
    def xy(x,y,z=None):
        a,b=project.transform(x,y)
        try:return [v-ox for v in a],[v-oy for v in b]
        except TypeError:return a-ox,b-oy
    features=json.loads((ROOT/'data/processed/study_boundaries.geojson').read_text(encoding='utf-8'))['features']
    main=transform(xy,shape(next(f for f in features if f['id']=='main_street')['geometry']))
    blocked=unary_union([mesh_footprint(p) for scope in ['Buildings','Streets'] for p in source.GetPrimAtPath('/World/'+scope).GetChildren() if p.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(p).ComputeVisibility()!='invisible'])
    ground=ground_footprint(source);candidates=[]
    for i,p in enumerate(positions):
        point=Point(p[0],p[1])
        # Palm XY scale is fixed at .9 (canopy <4 m); 4.6 m is a conservative screen.
        if i not in hidden and indices[i]!=6 and main.covers(point) and ground.covers(point.buffer(4.6)) and point.distance(blocked)>4.6:candidates.append(i)
    candidates.sort(key=lambda i:Point(positions[i][0],positions[i][1]).distance(Point(-44,-50)))
    chosen=candidates[:3]
    if len(chosen)<3:raise ValueError('Not enough clear existing illustrative placements; previous layer preserved')
    for i in chosen:indices[i]=6;scales[i]=Gf.Vec3f(.9,.9,1.1)
    layer=Usd.Stage.CreateInMemory();inst=UsdGeom.PointInstancer.Define(layer,'/World/Trees');inst.CreateProtoIndicesAttr(indices);inst.CreateScalesAttr(scales)
    layer.GetRootLayer().customLayerData={'quality':'Three original palms at illustrative existing tree placements; not a surveyed inventory','placement_policy':'Main Street; conservative 4.6m horizontal screen against rendered buildings/street surfaces; no new positions'}
    layer.GetRootLayer().Export(str(output))
    report={'converted_tree_indices':chosen,'palms_added':len(chosen),'new_tree_positions':0,'placement_quality':'illustrative','road_building_screen_radius_m':4.6,'layer':'scene/main_street_palms.usda'}
    atomic_json(ROOT/'data/processed/main_street_palms.json',report);print(json.dumps(report,indent=2));return report

if __name__=='__main__':build()
