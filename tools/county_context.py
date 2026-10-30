"""Bounded Orange County pilot references; no scene/snapshot activation."""
from pathlib import Path
import os,sys,json,hashlib,datetime,re,shutil,urllib.request
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import Client,arcgis,atomic_json,now,clean_address,clean_pin
from city_adapter_contract import CheckedClient
import city_adapter_contract
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
import shapely
def transform(fn,geometry):return shapely.transform(geometry,fn,interleaved=False)
from pyproj import Transformer,CRS
BASE='https://ocgis4.ocfl.net/arcgis/rest/services/'
ORG='0U8EQ1FrumPeIqDb';OUT='data/processed/county_context'
SOURCES={
 'addresses':{'url':BASE+'AGOL_Open_Data/MapServer/0','item_id':'f68552fa78914e47a28e8229b60ab820','fields':['OBJECTID','ENTERPRISE_ADDRESS_ID','OFFICIAL_PARCEL_ID','COMPLETE_ADDRESS','MUNICIPAL_JURISDICTION','ADDRESS_TYPE','ADDRESS_STATUS','DT_CREATED','DT_LAST_MOD']},
 'roads':{'url':BASE+'AGOL_Open_Data/MapServer/67','item_id':'953da4dea1f1493bb4ee3572e49cb82a','fields':['OBJECTID','OC_ROADS_ID','COMPLETE_STREETNAME','LANES','DESIGNATION','DESIGNATION_ID','S_OWNER','MAINTENANCE','STREET_CLASSIFICATION','DT_CREATED','DT_LAST_MOD']},
 'drainage_basins':{'url':BASE+'AGOL_Open_Data/MapServer/33','item_id':'6ebb12f6dd7a408094e8596d186b3640','fields':['OBJECTID','BASIN','BASIN_ABBR','BASIN_ID','CREATE_DATE','EDIT_DATE']},
 'stormwater_structures':{'url':BASE+'AGOL_Open_Data2/MapServer/5','item_id':'34811d4fd2c1434ba0e91fac51054b98','fields':['OBJECTID','CS_TYPE','CS_ID','MATERIAL','DATUM','SOURCE','ACCURACY','PLAN_DATE','DATE_EDITED','MAINTAINED_BY']},
 'stormwater_pipes':{'url':BASE+'AGOL_Open_Data2/MapServer/7','item_id':'9f595f859a504927976e04963a04d5f6','fields':['OBJECTID','P_TYPE','P_ID','MATERIAL','DATUM','SOURCE','ACCURACY','PLAN_DATE','DATE_EDITED','MAINTAINED_BY']},
 'unopened_row':{'url':'https://services1.arcgis.com/'+ORG+'/arcgis/rest/services/UnopenedRow/FeatureServer/0','item_id':'f90fd274ed164a29a66e9ccc8ab245da','fields':['OBJECTID']}}
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plain(s):return re.sub(r'<[^>]+>',' ',str(s or '')).strip()
class Probe:
 def __init__(self,root,offline):self.root=root;self.offline=offline;self.client=Client(root/'data/cache/county_context',offline=offline,opener=lambda req,timeout:urllib.request.urlopen(req,timeout=min(20,timeout)));self.failures=[]
 def get(self,url,params=None):
  from urllib.parse import urlencode
  target=url+('?' +urlencode(params) if params else '');path=self.root/'data/cache/county_context/failures'/(hashlib.sha256(target.encode()).hexdigest()+'.json')
  if self.offline and path.exists():
   failure=read(path);self.failures.append(failure);raise ValueError('Recorded public access failure: '+failure['error_type'])
  try:return self.client.get(url,params)
  except Exception as exc:
   if self.offline:raise
   failure={'url':target,'retrieved_utc':now(),'error_type':type(exc).__name__,'message':str(exc),'status':'public_request_unavailable_not_zero_features'};atomic_json(path,failure);self.failures.append(failure);raise

def build(root=ROOT,offline=False):
 root=Path(root).resolve();active=read(root/'data/processed/active.json');pilot=read(root/'data/processed/pilot.json');context=shape(pilot['context_geometry']);centerline=shape(pilot['centerline']);bbox=list(context.bounds)
 if pilot['source_snapshot']!=active['snapshot']:raise ValueError('Pilot snapshot stale')
 city_dependency=city_adapter_contract.validate(root);city_dependency_sha=sha(root/'data/processed/city_adapter_contract/packet.json')
 out=root/OUT;packet_path=out/'packet.json';receipt_path=out/'receipt.json';previous=None
 if packet_path.exists()!=receipt_path.exists():raise ValueError('Incomplete County publication; preserve files')
 if packet_path.exists():
  receipt=read(receipt_path)
  for n,h in receipt['artifacts'].items():
   if Path(n).name!=n or sha(out/n)!=h:raise ValueError('Preserve modified County output: '+n)
  previous=read(packet_path)
 probe=Probe(root,offline);organization=probe.get('https://www.arcgis.com/sharing/rest/portals/'+ORG,{'f':'json'})
 if organization.get('id')!=ORG or organization.get('name')!='Orange County Government GIS':raise ValueError('County publisher verification changed')
 project=Transformer.from_crs(4326,32617,always_xy=True).transform;utmcontext=transform(project,context);layers={};register=[];decisions=[];unresolved=[];dictionaries={};candidate_counts={};extra_dependencies=[]
 for name,source in SOURCES.items():
  item={}
  try:
   item=probe.get('https://www.arcgis.com/sharing/rest/content/items/'+source['item_id'],{'f':'json'})
   if item.get('orgId')!=ORG or item.get('access')!='public':raise ValueError('Unverified County public organization item')
   if str(item.get('url') or '').rstrip('/')!=source['url'].rstrip('/'):raise ValueError('County item does not identify selected service URL')
   data,meta=arcgis(CheckedClient(probe),{**source,'oid':'OBJECTID'},bbox=bbox)
  except Exception as exc:
   if name=='unopened_row':
    try:probe.get(source['url'],{'f':'json'})
    except Exception:pass
   if previous and previous['source_decisions'].get(name,{}).get('status')=='accepted_reference':raise ValueError('Previously good County layer failed; preserve prior packet: '+name) from exc
   layers[name]={'type':'FeatureCollection','features':[]};dictionaries[name]=[];candidate_counts[name]=None;decisions.append((name,{'status':'unavailable_public_service','reason':'Public service request failed; feature coverage unknown, not zero','error_type':type(exc).__name__}));unresolved.append({'source':name,'reason':'Portal item is discoverable but public service unavailable; no coverage/geometry assumed'});register.append({'id':name,'publisher':'Orange County Government GIS','item_id':source['item_id'],'api_url':source['url'],'item_url':'https://www.arcgis.com/sharing/rest/content/items/'+source['item_id'],'item_modified_epoch_ms':item.get('modified'),'license_info':plain(item.get('licenseInfo')),'acquisition_date':None,'effective_date':None,'coverage_status':'unknown_service_unavailable'});continue
  candidate_counts[name]=len(data['features']);features=[];exceptions=[];oidseen=set()
  for f in data['features']:
   p=f['properties'];oid=str(p['OBJECTID'])
   if oid in oidseen:raise ValueError('Duplicate County source OBJECTID')
   oidseen.add(oid)
   try:g=shape(f['geometry'])
   except Exception:exceptions.append({'source_object_id':oid,'reason':'invalid_geometry'});continue
   if not g.is_valid or g.is_empty:exceptions.append({'source_object_id':oid,'reason':'invalid_geometry'});continue
   clip=g.intersection(context)
   if clip.is_empty:exceptions.append({'source_object_id':oid,'reason':'envelope_candidate_outside_actual_pilot_context'});continue
   attrs={k:p.get(k) for k in source['fields']};props={'source_object_id':oid,'entity_id':'ocfl:'+name+':'+oid,'original_fields':attrs,'quality':'official_reference_not_surveyed_or_current_field_verified','physical_geometry_accepted':False,'source_status':'publisher_reference_temporal_status_unknown','geometry_role':'clipped_reference_only; not curb/ROW boundary or hydraulic model'}
   features.append({'type':'Feature','id':props['entity_id'],'properties':props,'geometry':mapping(clip)})
  layers[name]={'type':'FeatureCollection','features':features};dictionaries[name]=[{k:f.get(k) for k in ('name','alias','type','domain')} for f in meta.get('fields',[]) if f['name'] in source['fields']]
  decisions.append((name,{'status':'accepted_reference','scope':'supplemental clipped government reference only, no scene activation','envelope_candidates':len(data['features']),'pilot_context_features':len(features),'exceptions':exceptions,'zero_means':'No features returned/intersected for this service and dated query, not proof no asset exists'}))
  accesses=[a for a in probe.client.accesses if a['url'].split('?')[0] in (source['url'],source['url']+'/query')];known=sorted(a['retrieved_utc'] for a in accesses if a.get('retrieved_utc'));sr=meta.get('extent',{}).get('spatialReference',{});wkid=sr.get('latestWkid',sr.get('wkid'))
  register.append({'id':name,'publisher':'Orange County Government GIS','item_id':source['item_id'],'item_url':'https://www.arcgis.com/sharing/rest/content/items/'+source['item_id'],'api_url':source['url'],'metadata_url':source['url']+'?f=json','item_modified_epoch_ms':item.get('modified'),'source_updated_epoch_ms':meta.get('editingInfo',{}).get('lastEditDate'),'acquisition_date':None,'effective_date':None,'retrieved_utc':known[-1] if known and len(known)==len(accesses) else None,'retrieval_range_utc':[known[0],known[-1]] if known else None,'native_horizontal_crs':sr,'native_horizontal_units':CRS.from_epsg(wkid).axis_info[0].unit_name if wkid else None,'output_crs':'EPSG4326; displayarea EPSG32617 metres','vertical_datum':'Not used; original DATUM code retained only. No elevations, depths or sizes imported.','license_info':plain(item.get('licenseInfo')),'copyright':plain(meta.get('copyrightText')),'reuse':'Observed public API access is not a survey warranty or affirmative ML/imagery license','source_fields':source['fields'],'source_id_scope':'Original OBJECTID for service version; asset/enterprise IDs retained separately','source_description':plain(meta.get('description')),'pagination':'ID discovery and50-IDbatches; bounded pilot envelope; retries/backoff/60-secondclientcap; transporttimeout20seconds','query_bbox':bbox,'source_date_fields_unit':'ArcGIS esriFieldTypeDate epoch milliseconds; raw original values preserved','imagery_or_ml_use':'Not evaluated or authorized by this reference-data adapter'})
  unresolved.extend({'source':name,**x} for x in exceptions)
 # City/County matching is context reconciliation only, never accepted identity.
 city_path=root/'data/processed/city_adapter_contract/packet.json';city=city_dependency;cityaddresses=city['tables']['addresses'];by_address={}
 for row in cityaddresses:
  address=clean_address(row['source_fields'].get('SitusAddress'))
  if address:by_address.setdefault(address,[]).append(row)
 comparison=[]
 for f in layers['addresses']['features']:
  p=f['properties'];raw=p['original_fields'];matches=by_address.get(clean_address(raw.get('COMPLETE_ADDRESS')),[]);sourcepoint=shape(f['geometry']);distances=[transform(project,sourcepoint).distance(transform(project,shape(m['geometry']))) for m in matches if m.get('geometry')];comparison.append({'county_source_object_id':p['source_object_id'],'county_enterprise_address_id':raw.get('ENTERPRISE_ADDRESS_ID'),'county_reported_municipal_jurisdiction':raw.get('MUNICIPAL_JURISDICTION'),'city_source_ids':[m['source_id'] for m in matches],'match_method':'exact_normalized_address_text_context_only' if matches else 'no_exact_text_candidate','minimum_reference_point_separation_m':min(distances) if distances else None,'candidate_count':len(matches),'identity_accepted':False,'parcel_steward':'OCPA; original County/City PID strings retained, not auto-promoted'})
 city_street_path=(root/active['relative_path']/'streets.json').resolve()
 if not city_street_path.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('City street snapshot path escapes')
 citystreets=[f for f in read(city_street_path)['features'] if shape(f['geometry']).intersects(context)]
 road_comparisons=[]
 for f in layers['roads']['features']:
  attrs=f['properties']['original_fields'];matches=[c for c in citystreets if clean_address(c['properties'].get('FullStreetName'))==clean_address(attrs.get('COMPLETE_STREETNAME'))];g=transform(project,shape(f['geometry']));reference=unary_union([transform(project,shape(c['geometry']).intersection(context)) for c in matches]);samples=[g.interpolate(g.length*i/max(1,int(g.length/2))) for i in range(max(1,int(g.length/2))+1)]
  road_comparisons.append({'county_source_object_id':f['properties']['source_object_id'],'county_asset_id':attrs.get('OC_ROADS_ID'),'city_source_object_ids':[str(c['properties']['OBJECTID']) for c in matches],'comparison_method':'same normalized street text, directed County centerline samples every~2m to union of City reference segments','maximum_directed_reference_separation_m':max(point.distance(reference) for point in samples) if matches else None,'county_reported_owner_code':attrs.get('S_OWNER'),'county_reported_maintenance':attrs.get('MAINTENANCE'),'county_reported_lanes':attrs.get('LANES'),'lane_count_current_verified':False,'identity_accepted':False,'curb_width_inferred':False})
 for row in comparison:row['geometry_review_threshold_m']=5.;row['geometry_review_required']=row['minimum_reference_point_separation_m'] is None or row['minimum_reference_point_separation_m']>5.;row['threshold_scope']='Triage only, not positional acceptance tolerance'

 stewardship={'parcel_geometry':'Orange County Property Appraiser; County GIS copies do not replace OCPA','municipal_addresses':'City Address_Point layer22 is existing municipal reference; County enterprise addresses are corroborating context. Text matches do not establish shared permanent ID.','roads':'City Street_Centerline and County OC_ROADS are separate source namespaces; County S_OWNER/MAINTENANCE remain original coded attributes, not inferred jurisdiction. No width field imported.','drainage':'Majorbasins are watershed context, not complete inlets/pipes/ROW. Zero County structures/pipes does not establish no municipal drainage.','right_of_way':'UnopenedROW is a narrower inventory, never general current publicROW/curb geometry; service failure remains unknown. Proposedroadlayer is not selected.','city_street_context_features':len(citystreets),'county_city_address_comparisons':comparison,'road_comparisons':road_comparisons,'proposed_roads_excluded':True,'county_publisher_verified_org_id':ORG,'address_comparison_summary':{'text_unique_candidates':sum(x['candidate_count']==1 for x in comparison),'geometry_review_over_5m_or_unknown':sum(x['geometry_review_required'] for x in comparison),'maximum_reference_point_separation_m':max([x['minimum_reference_point_separation_m'] for x in comparison if x['minimum_reference_point_separation_m'] is not None],default=None),'identity_promotions':0}}
 unresolved.extend({'source':'county_city_address_comparison','county_source_object_id':row['county_source_object_id'],'reason':'Reference points exceed5m triage threshold or separation unknown; address-text match never promotes identity','reference_separation_m':row['minimum_reference_point_separation_m']} for row in comparison if row['geometry_review_required'])
 unresolved.extend({'source':'county_city_road_comparison','county_source_object_id':row['county_source_object_id'],'reason':'Reference centerline alignment/segment-endpoint review; no snapping or width inference','maximum_directed_reference_separation_m':row['maximum_directed_reference_separation_m']} for row in road_comparisons if row['maximum_directed_reference_separation_m'] is None or row['maximum_directed_reference_separation_m']>5.)
 dependencies={}
 for pth in [root/'data/processed/active.json',root/'data/processed/pilot.json',city_path,root/'data/processed/city_adapter_contract/receipt.json',city_street_path,root/'tools/county_context.py',root/'tools/data_pipeline.py',root/'tools/city_adapter_contract.py']:
  dependencies[str(pth.relative_to(root)).replace('\\','/')]=sha(pth)
 for a in probe.client.accesses:
  pth=root/'data/cache/county_context'/(hashlib.sha256(a['url'].encode()).hexdigest()+'.json');dependencies[str(pth.relative_to(root)).replace('\\','/')]=sha(pth)
 for failure in probe.failures:
  pth=root/'data/cache/county_context/failures'/(hashlib.sha256(failure['url'].encode()).hexdigest()+'.json');dependencies[str(pth.relative_to(root)).replace('\\','/')]=sha(pth)
 city_adapter_contract.validate(root)
 if sha(city_path)!=city_dependency_sha or any(sha(root/n)!=h for n,h in dependencies.items()):raise ValueError('County or City comparison source changed while building')
 packet={'schema':'twin.county-context/1','source_snapshot':active['snapshot'],'built_utc':now(),'pilot_id':pilot['pilot_id'],'pilot_context':pilot['context_geometry'],'scope_note':'Frozen continuous pilot plus60mreviewcontext; not right-of-way or wholeCollegePark','source_register':register,'source_decisions':dict(decisions),'layers':layers,'normalized_field_dictionary':{'entity_id':'County dataset-scoped original source OBJECTID, not cross-agency physical identity','source_object_id':'Original OBJECTID preserved as string; original enterprise/asset IDs remain distinct','original_fields':'Only explicitly allowlisted source attributes, nulls and date values retained','geometry':'WGS84 clipped to frozen pilot reviewcontext, not surveyed curb or parcel boundary','physical_geometry_accepted':'False; references never autoactivate modeled geometry'},'field_dictionary':dictionaries,'first_five_safe_rows':{n:[f['properties'] for f in layer['features'][:5]] for n,layer in layers.items()},'coverage':{'bbox_wgs84':bbox,'pilot_context_area_m2':utmcontext.area,'envelope_candidates':candidate_counts,'actual_context_counts':{n:len(v['features']) if dict(decisions)[n]['status']=='accepted_reference' else None for n,v in layers.items()}},'stewardship':stewardship,'unresolved':unresolved+[{'reason':'Exactcurbs/currentROW,widths,fullmunicipaldrainage,ownership/vacancyandFLU/PDordinanceconditionsnotestablished; expanded#22scope remainsopen'}],'requests':probe.client.accesses,'access_failures':probe.failures,'dependencies':dependencies,'active_snapshot_changed':False,'scene_changed':False,'private_booms_read':False,'geometry_activated':False}
 # Pixel-free geometry coverage map, retaining missing-service labels.
 xmin,ymin,xmax,ymax=utmcontext.bounds;scale=min(700/(xmax-xmin),850/(ymax-ymin));svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 950 950"><rect width="950" height="950" fill="#f5f7f4"/>']
 def path(g):
  parts=[]
  for child in getattr(g,'geoms',[g]):
   if child.geom_type=='Polygon':lines=[child.exterior,*child.interiors]
   elif child.geom_type=='Point':
    x,y=child.coords[0];parts.append(f'<circle cx="{(x-xmin)*scale+15:.2f}" cy="{(ymax-y)*scale+15:.2f}" r="2"/>');continue
   elif hasattr(child,'coords'):lines=[child]
   else:continue
   for line in lines:parts.append('<path fill="none" d="M '+' L '.join(f'{(x-xmin)*scale+15:.2f},{(ymax-y)*scale+15:.2f}' for x,y in line.coords)+'"/>')
  return ''.join(parts)
 svg.append('<g stroke="#222" stroke-width="2">'+path(utmcontext)+'</g>')
 for name,color in [('drainage_basins','#69a4ad'),('roads','#b45f35'),('addresses','#395c85'),('stormwater_structures','#9a3c63'),('stormwater_pipes','#738d3b')]:
  svg.append('<g stroke="'+color+'" fill="'+color+'" stroke-width="1.2">'+''.join(path(transform(project,shape(f['geometry']))) for f in layers[name]['features'])+'</g>')
 import html
 svg.append('<text x="15" y="910" font-size="15">County pilot references; black: review context, blue: address, rust: roads, teal: basin</text>')
 svg.append('<text x="15" y="935" font-size="13">'+html.escape('Counts: '+str(packet['coverage']['actual_context_counts']))+'</text></svg>')
 geo={'type':'FeatureCollection','features':[f for layer in layers.values() for f in layer['features']]};payloads={'packet.json':json.dumps(packet,indent=2).encode(),'references.geojson':json.dumps(geo,indent=2).encode(),'coverage.svg':''.join(svg).encode()}
 if previous:
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for n in [*read(receipt_path)['artifacts'],'receipt.json']:shutil.copy2(out/n,backup/n)
 elif any((out/n).exists() for n in payloads):raise ValueError('Unreceipted County output exists')
 out.mkdir(parents=True,exist_ok=True)
 for n,body in payloads.items():temp=out/(n+'.tmp');temp.write_bytes(body);temp.replace(out/n)
 atomic_json(receipt_path,{'source_snapshot':active['snapshot'],'artifacts':{n:sha(out/n) for n in payloads}});return packet

def validate(root=ROOT):
 root=Path(root).resolve();city_adapter_contract.validate(root);out=root/OUT;p=read(out/'packet.json');receipt=read(out/'receipt.json')
 if p.get('schema')!='twin.county-context/1' or not p.get('dependencies') or set(receipt.get('artifacts',{}))!={'packet.json','references.geojson','coverage.svg'}:raise ValueError('County validation proof incomplete')
 if p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or receipt['source_snapshot']!=p['source_snapshot']:raise ValueError('County snapshot stale')
 for n,h in receipt['artifacts'].items():
  if Path(n).name!=n or sha(out/n)!=h:raise ValueError('County output changed')
 for n,h in p['dependencies'].items():
  path=(root/n).resolve()
  if not path.is_relative_to(root) or sha(path)!=h:raise ValueError('County source dependency changed')
 return p
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args();p=build(offline=args.offline);print(json.dumps({'coverage':p['coverage'],'decisions':{n:v['status'] for n,v in p['source_decisions'].items()},'city_context_streets':p['stewardship']['city_street_context_features']}))
