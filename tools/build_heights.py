"""Evidence-labeled building height layer; source geometry remains recoverable."""
from data_pipeline import ROOT,atomic_json
import sys,json,collections,math,datetime
sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np
from pxr import Usd,UsdGeom,Gf
from shapely.geometry import Polygon,Point,box
from shapely.ops import unary_union,transform
from shapely.strtree import STRtree
from pyproj import Transformer
from scipy.spatial import cKDTree

def positive_floor(value):
 try:
  v=float(value)
  return int(v) if v.is_integer() and 1<=v<=80 else None
 except (TypeError,ValueError):return None
def floor_estimate(floors,commercial):
 return round(floors*(3.6 if commercial else 3.0)+(.7 if commercial else 1.2),2)
def choose_floors(building_floor,parcel_floor,unique_building):
 if unique_building and parcel_floor and building_floor and abs(parcel_floor-building_floor)>1:
  return building_floor,'building_floor_records_parcel_story_outlier_needs_review'
 if unique_building and parcel_floor:
  if building_floor and building_floor>parcel_floor:return building_floor,'building_floor_records_conflict_with_parcel'
  return parcel_floor,'appraiser_stories_single_building_parcel'
 if building_floor:return building_floor,'maximum_building_footprint_floor_number'
 return None,'unknown'

def build():
 active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'));folder=ROOT/active['relative_path'];records=json.loads((folder/'buildings.json').read_text(encoding='utf-8'));by_id={r['id']:r for r in records};parcel_counts=collections.Counter(r['parcel_id'] for r in records if r['parcel_id']);parcels=json.loads((folder/'parcels.json').read_text(encoding='utf-8'))['features'];pby={f['properties']['id']:f['properties'] for f in parcels}
 raw=json.loads((ROOT/'data/buildings.geojson').read_text(encoding='utf-8'))['features'];by_object={str(f['properties']['OBJECTID']):f['properties'] for f in raw}
 source=Usd.Stage.Open(str(ROOT/'scene/college_park.usda'));layer=Usd.Stage.CreateNew(str(ROOT/'scene/building_heights.usda'));results=[]
 lidar_file=ROOT/'data/heights/pilot_points.npz';unit_file=ROOT/'data/heights/vertical_unit_check.json';use_lidar=lidar_file.exists() and unit_file.exists() and json.loads(unit_file.read_text(encoding='utf-8')).get('accepted')
 roof_tree=None;ground_tree=None
 if use_lidar:
  data=np.load(lidar_file)['points'];roof=data[data[:,3]==6,:3];ground=data[data[:,3]==2,:3];projection=Transformer.from_crs(3857,32617,always_xy=True);origin=Transformer.from_crs(4326,32617,always_xy=True).transform(-81.389,28.572)
  for points in [roof,ground]:
   xx,yy=projection.transform(points[:,0],points[:,1]);points[:,0]=xx-origin[0];points[:,1]=yy-origin[1]
  import shapely
  roof_tree=STRtree(shapely.points(roof[:,:2]));ground_tree=cKDTree(ground[:,:2])
  print('Classified roof points',len(roof),'ground points',len(ground),flush=True)
  roi_proj=Transformer.from_crs(4326,32617,always_xy=True)
  a=roi_proj.transform(-81.391,28.570);b=roi_proj.transform(-81.387,28.574);roi=box(a[0]-origin[0],a[1]-origin[1],b[0]-origin[0],b[1]-origin[1])
 for prim in source.GetPrimAtPath('/World/Buildings').GetChildren():
  m=UsdGeom.Mesh(prim);pts=m.GetPointsAttr().Get();ids=m.GetFaceVertexIndicesAttr().Get();sizes=m.GetFaceVertexCountsAttr().Get();triangles=[];k=0
  for size in sizes:
   if size==3:triangles.append(Polygon([(pts[j][0],pts[j][1]) for j in ids[k:k+3]]))
   k+=size
  footprint=unary_union(triangles);rawdata=prim.GetCustomData();record=by_id[prim.GetName()];parcel=pby.get(record.get('parcel_feature_id'),{});commercial=rawdata.get('classification')=='Commercial';old=float(rawdata.get('heightMeters',6.5 if commercial else 4.2))
  floor_values=[positive_floor(by_object.get(s,{}).get('FLOOR_NUM')) for s in rawdata.get('sourceObjectIds','').split(',')];building_floor=max([f for f in floor_values if f],default=None);parcel_floor=positive_floor(parcel.get('stories')) if record['match_method']=='id_and_geometry' else None
  floors,method=choose_floors(building_floor,parcel_floor,parcel_counts.get(record.get('parcel_id'))==1)
  height=floor_estimate(floors,commercial) if floors else old;quality='floor_count_estimate' if floors else 'unverified_fallback';notes=[];samples=0;roof_z=None;ground_z=None
  if parcel_counts.get(record.get('parcel_id'),0)>1:notes.append('Parcel has multiple building groups; parcel story count not applied to each building.')
  if footprint.geom_type=='MultiPolygon':notes.append('Multiple footprint components share this building group; a single mass height is approximate.')
  if 'conflict' in method or 'outlier' in method:notes.append('Building-level and parcel-level floor counts conflict; parcel outlier not applied; review required.')
  if roof_tree is not None and roi.contains(footprint.buffer(2)) and not (parcel.get('year_built') and parcel['year_built']>2019):
   interior=footprint.buffer(-.4)
   if not interior.is_empty:
    ri=roof_tree.query(interior,predicate='contains');samples=len(ri);center=footprint.representative_point();dist,gi=ground_tree.query((center.x,center.y),k=64);near=gi[dist<=35]
    if samples>=30 and len(near)>=12:
     roof_z=float(np.percentile(roof[ri,2],95));ground_z=float(np.median(ground[near,2]));candidate=roof_z-ground_z;spread=float(np.percentile(roof[ri,2],95)-np.percentile(roof[ri,2],10))
     expected=floor_estimate(floors,commercial) if floors else None
     density=samples/max(footprint.area,1)
     consistent=expected is None or (candidate<=expected*1.8 and candidate>=expected*.45)
     if 2<=candidate<=80 and spread<=max(12,candidate*.75) and density>=1 and consistent:
      height=round(candidate,2);method='classified_lidar_roof_p95_minus_local_ground_median';quality='historical_lidar_derived';notes.append('2018–2019 acquisition; current condition needs dated reference review. Flat ground is still used in the scene.')
     else:notes.append('LiDAR failed height/spread/density/floor-consistency checks; floor estimate retained for review.')
  elif roof_tree is not None and parcel.get('year_built') and parcel['year_built']>2019:notes.append('Appraiser year built is newer than LiDAR acquisition; historical roof not applied.')
  if height<4.2 and commercial:notes.append('Existing illustrative storefront trims may need adjustment to the lower roofline.')
  target=layer.OverridePrim(prim.GetPath());new_points=[(float(p[0]),float(p[1]),.10+(float(p[2])-.10)*height/old) for p in pts];mesh=UsdGeom.Mesh(target);mesh.CreatePointsAttr(new_points);mesh.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in new_points) for i in range(3))),Gf.Vec3f(*(max(p[i] for p in new_points) for i in range(3)))])
  datum={'height_m':height,'method':method,'quality':quality,'floors_used':floors or 0,'source_snapshot':active['snapshot'],'source_building_floor':building_floor or 0,'source_parcel_stories':parcel_floor or 0,'lidar_roof_points':samples,'review_notes':' '.join(notes)}
  if roof_z is not None:datum.update({'roof_elevation_m':roof_z,'nearby_ground_elevation_m':ground_z,'vertical_reference':'source NAVD88; EPT Z meters independently checked against EPQS'})
  target.SetCustomDataByKey('height',datum);target.SetCustomDataByKey('heightMeters',height);target.SetCustomDataByKey('heightQuality',quality)
  roof_prim=source.GetPrimAtPath('/World/Roofs/Roof_'+prim.GetName().split('_')[-1])
  if roof_prim:
   r=UsdGeom.Mesh(layer.OverridePrim(roof_prim.GetPath()));rpoints=[(float(p[0]),float(p[1]),.10+height+.02) for p in UsdGeom.Mesh(roof_prim).GetPointsAttr().Get()];r.CreatePointsAttr(rpoints);r.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in rpoints) for i in range(3))),Gf.Vec3f(*(max(p[i] for p in rpoints) for i in range(3)))])
  # Generic parapet strips were built for the former uniform height; move them with the roof.
  details=ROOT/'scene/edgewater_details.usdc'
  if details.exists():
   if 'detail_stage' not in locals():detail_stage=Usd.Stage.Open(str(details))
   facade=detail_stage.GetPrimAtPath('/World/Storefronts/'+prim.GetName())
   if facade:
    if height<3.7:UsdGeom.Imageable(layer.OverridePrim(facade.GetPath())).CreateVisibilityAttr('invisible')
    for front in facade.GetChildren():
     cap=front.GetChild('Parapet')
     if cap:
      capmesh=UsdGeom.Mesh(layer.OverridePrim(cap.GetPath()));cappts=[(float(p[0]),float(p[1]),float(p[2])+height-old) for p in UsdGeom.Mesh(cap).GetPointsAttr().Get()];capmesh.CreatePointsAttr(cappts)
  results.append({'building_id':prim.GetName(),'parcel_id':record.get('parcel_id'),'site_address':record.get('site_address'),'previous_height_m':old,**datum})
 layer.GetRootLayer().customLayerData={'purpose':'Building-height evidence layer; no invented surveyed precision','ground':'flat prototype terrain; heights are relative to local ground','lidar_scope':'central pilot only','source':'OCPA floor attributes / public footprint FLOOR_NUM / USGS Orange EPT classified roof points'};layer.GetRootLayer().Save()
 quality=collections.Counter(r['quality'] for r in results);report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'buildings':len(results),'height_quality':dict(quality),'changed_heights':sum(abs(r['height_m']-r['previous_height_m'])>.01 for r in results),'height_range_m':[min(r['height_m'] for r in results),max(r['height_m'] for r in results)],'lidar_unit_validation_accepted':bool(use_lidar),'source_footprint_max_floor_counts':dict(collections.Counter(str(r['source_building_floor']) for r in results)),'limitations':['Only a central pilot has classified LiDAR sampling.','Floor-derived heights use assumed floor-to-floor and roof allowances, not measurements.','Historic LiDAR may not represent current roofs.','Flat prototype ground remains; no surveyed terrain or roof forms are claimed.']}
 atomic_json(ROOT/'data/heights/building_heights.json',results);atomic_json(ROOT/'data/heights/height_quality.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':build()
