"""Compose official context without changing source geometry or manual edits."""
from pathlib import Path
import sys,json,collections
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Gf
from pyproj import Transformer
from activate_environment_assets import validated_environment_layer
from activate_flood_context import validate_active_flood
from activate_water_context import validate_active_water
from activate_pilot_aerial_review import validate_active_aerial
from build_wellesley_architecture import validate_active_wellesley
from refine_office_frontage import validated_active_detail
from activate_landmark_reconstructions import validated_post_office
from accepted_scene_layers import validated_layer
def connect():
 wellesley_active=validate_active_wellesley(ROOT)
 office_detail=validated_active_detail(ROOT)
 post_office=validated_post_office(ROOT)
 campus_hardscape=validated_layer('campus_hardscape',ROOT)
 active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'));folder=ROOT/active['relative_path'];scene=ROOT/'scene'
 buildings=json.loads((folder/'buildings.json').read_text(encoding='utf-8'));permits=json.loads((folder/'permits.json').read_text(encoding='utf-8'));parcels=json.loads((folder/'parcels.json').read_text(encoding='utf-8'));counts=collections.Counter(p['parcel_id'] for p in permits)
 stage=Usd.Stage.CreateNew(str(scene/'official_context.usda'))
 for b in buildings:
  prim=stage.OverridePrim(b['usd_path']);data={k:v for k,v in b.items() if v is not None and k!='candidate_parcels'}
  data.update({'snapshot':active['snapshot'],'source':'Orange County Property Appraiser','recent_permit_count':counts.get(b.get('parcel_id'),0),'match_accepted':b['match_method']=='id_and_geometry'})
  prim.SetCustomDataByKey('official',data)
 projection=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=projection.transform(-81.389,28.572)
 scope=UsdGeom.Xform.Define(stage,'/World/ParcelBoundaries');scope.CreateVisibilityAttr('invisible')
 for feature in parcels['features']:
  geom=feature['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']];pts=[];sizes=[]
  for polygon in polys:
   for ring in polygon:
    sizes.append(len(ring))
    for p in ring:
     x,y=projection.transform(p[0],p[1]);pts.append((x-ox,y-oy,.14))
  path='/World/ParcelBoundaries/Parcel_'+str(feature['properties']['source_object_id']);curves=UsdGeom.BasisCurves.Define(stage,path);curves.CreateTypeAttr('linear');curves.CreateCurveVertexCountsAttr(sizes);curves.CreatePointsAttr(pts);curves.CreateWidthsAttr([.10]);curves.SetWidthsInterpolation('constant');curves.CreateDisplayColorAttr([Gf.Vec3f(.8,.55,.10)]);curves.GetPrim().SetCustomDataByKey('official',{k:v for k,v in feature['properties'].items() if v is not None})
 stage.GetRootLayer().customLayerData={'snapshot':active['snapshot'],'quality':'Official reference data; spatial-only links are unaccepted; outlines are not a survey'};stage.GetRootLayer().Save()
 manual=scene/'manual_edits.usda'
 if not manual.exists():
  manual_stage=Usd.Stage.CreateNew(str(manual));manual_stage.GetRootLayer().Save()
 assembly=Usd.Stage.Open(str(scene/'college_park_connected.usda')) if (scene/'college_park_connected.usda').exists() else Usd.Stage.CreateNew(str(scene/'college_park_connected.usda'));layers=['map_extent_guard.usda'] if (scene/'map_extent_guard.usda').exists() else []
 layers+=['manual_edits.usda']
 if office_detail:layers.append(office_detail)
 if post_office:layers.append('post_office_historical.usda')
 if campus_hardscape:layers.append(campus_hardscape)
 activated_environment=validated_environment_layer(ROOT)
 if activated_environment:layers.append(activated_environment)
 activated_flood=validate_active_flood(ROOT)
 if activated_flood:layers.append(activated_flood)
 activated_aerial=validate_active_aerial(ROOT)
 if activated_aerial:layers.append(activated_aerial)
 activated_water=validate_active_water(ROOT)
 if activated_water:layers.append(activated_water)
 if wellesley_active:layers.append('wellesley_architecture.usda')
 if (scene/'main_street_presentation.usda').exists():layers.append('main_street_presentation.usda')
 layers+=['official_context.usda']
 for name in ['final_omission_roofs.usda','retail_block.usda','landmark_buildings.usda','rear_parking_samples.usda','road_materials.usda','main_street_palms.usda','study_scope.usda','commercial_context.usda','landmark_corrections.usda','princeton_correction.usda','semantic_assets.usda','building_heights.usda','asset_upgrade.usda','edgewater_details.usdc','college_park.usda']:
  if (scene/name).exists():layers.append(name)
 assembly.GetRootLayer().subLayerPaths=layers;UsdGeom.SetStageMetersPerUnit(assembly,1);UsdGeom.SetStageUpAxis(assembly,'Z');assembly.SetDefaultPrim(assembly.GetPrimAtPath('/World'));assembly.GetRootLayer().Save()
 print('Connected',len(buildings),'building records and',len(parcels['features']),'parcel outlines; snapshot',active['snapshot'])
if __name__=='__main__':connect()
