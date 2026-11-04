"""Bounded public City adapters and read-only supplemental quality packet."""
from pathlib import Path
import os,sys,json,hashlib,collections,datetime,shutil,math
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import Client,arcgis,socrata,SOURCES,GIS,atomic_json,now
from shapely.geometry import shape,box
from pyproj import CRS
EXTRA={
 'addresses':{'url':GIS+'Address_Point/FeatureServer/22','publisher':'City of Orlando','oid':'OBJECTID','fields':['OBJECTID','GlobalID','AddressID','ADDRKEY','SitusAddress','PID','AddrStatus','AddrType','CaptureMethod','FieldCheck','IsCurrent','MaintenanceDate','last_edited_date']},
 'future_land_use':{'url':GIS+'OrlandoLUFutureLandUse/FeatureServer/0','publisher':'City of Orlando','oid':'OBJECTID','fields':['OBJECTID','GlobalID','LanduseType']}}
OUT='data/processed/city_adapter_contract'
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class CheckedClient:
 def __init__(self,client):self.client=client
 def get(self,url,params=None):
  data=self.client.get(url,params)
  if isinstance(data,dict) and data.get('error'):raise ValueError('Agency error; preserve prior packet')
  if params and params.get('returnIdsOnly')=='true' and (not isinstance(data,dict) or 'objectIds' not in data or data['objectIds'] is not None and not isinstance(data['objectIds'],list)):raise ValueError('Malformed ID response is not an empty dataset')
  return data

def fetch_arcgis(client,source,bbox):return arcgis(CheckedClient(client),source,bbox)
def fetch_socrata(client,source,where):
 rows,meta=socrata(CheckedClient(client),source,where)
 if any(not isinstance(r.get('source_row_id'),str) or not r['source_row_id'].strip() for r in rows):raise ValueError('Missing original portal row identity')
 return rows,meta

def normalize(name,data,source,bbox):
 geo=isinstance(data,dict);rows=data.get('features',[]) if geo else data;normalized=[];issues=[];seen=set();oid=source.get('oid','source_row_id')
 for index,row in enumerate(rows):
  props=row.get('properties',{}) if geo else row;identifier=props.get(oid)
  if identifier is None or str(identifier).strip()=='':issues.append({'row_index':index,'reason':'missing_source_identity'});continue
  source_id=str(identifier)
  if source_id in seen:raise ValueError('Duplicate source feature identity; preserve prior packet')
  seen.add(source_id);geometry=row.get('geometry') if geo else props.get('geocoded_column') if isinstance(props.get('geocoded_column'),dict) and props['geocoded_column'].get('type') else None;quality='nonspatial_record'
  if geometry:
   try:
    g=shape(geometry);bounds=g.bounds
    if g.is_empty or not g.is_valid or not all(math.isfinite(v) for v in bounds):raise ValueError('invalid')
    if bounds[0]<-180 or bounds[2]>180 or bounds[1]<-90 or bounds[3]>90:raise ValueError('invalid')
    if not g.intersects(box(*bbox)):issues.append({'source_id':source_id,'reason':'outside_bbox_context_or_coordinate_review'});quality='outside_query_review'
    else:quality='publisher_WGS84_reference_not_surveyed'
   except (ValueError,TypeError,KeyError,IndexError):issues.append({'source_id':source_id,'reason':'invalid_geometry'});geometry=None;quality='invalid_geometry_quarantined'
  elif geo:issues.append({'source_id':source_id,'reason':'missing_geometry'});quality='missing_geometry'
  fields={k:props.get(k) for k in source['fields']}
  if quality=='invalid_geometry_quarantined' and 'geocoded_column' in fields:fields['geocoded_column']=None
  if 'source_row_id' in props:fields['source_row_id']=str(props['source_row_id'])
  normalized.append({'entity_id':'city:'+name+':'+source_id,'entity_type':{'addresses':'address','permits':'permit_record','businesses':'business_license_record','future_land_use':'planning_polygon'}.get(name,'public_asset_or_reference'),'source_id':source_id,'source_fields':fields,'geometry':geometry,'geometry_quality':quality,'source_dates':{k:props.get(k) for k in source['fields'] if any(v in k.lower() for v in ('date','edited'))},'missing_optional_fields':[k for k in source['fields'] if k not in props]})
 return normalized,{'source_rows':len(rows),'normalized_rows':len(normalized),'empty_response':not rows,'issues':issues,'geometry_quality':dict(collections.Counter(r['geometry_quality'] for r in normalized))}

def build(root=ROOT,offline=False):
 root=Path(root).resolve();active=read(root/'data/processed/active.json');folder=(root/active['relative_path']).resolve()
 if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Active City snapshot escapes snapshot directory')
 bbox=read(root/'config/study_area.json')['acquisition_bbox_wgs84'];client=Client(root/'data/cache/city_adapter_discovery',offline=offline);catalog=client.get(GIS.rstrip('/'),{'f':'json'});services=[r['name'] for r in catalog.get('services',[])];manifest=read(folder/'sources.json');by_source={r['id']:r for r in manifest};tables={};quality={};register=[];dependencies={};metadata={}
 for name in [n for n in SOURCES if n!='parcels']+list(EXTRA):
  source=EXTRA.get(name,SOURCES.get(name));supplemental=name in EXTRA
  if supplemental:data,meta=fetch_arcgis(client,source,bbox)
  else:
   path=folder/(name+'.json');mpath=folder/(name+'_metadata.json');data=read(path);meta=read(mpath);dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path);dependencies[str(mpath.relative_to(root)).replace('\\','/')]=sha(mpath)
  declared={f['fieldName'] for f in meta.get('columns',[])} if source.get('dataset') else {f['name'] for f in meta.get('fields',[])}
  if set(source['fields'])-declared:raise ValueError('Cached City schema differs from approved request contract: '+name)
  rows,q=normalize(name,data,source,bbox);tables[name]=rows;quality[name]=q;metadata[name]=meta
  original=by_source.get(name,{})
  register.append({'id':name,'publisher':'City of Orlando','dataset_service_id':source.get('dataset') or source['url'].split('/services/')[-1],'api_url':source['url'],'metadata_url':'https://data.cityoforlando.net/api/views/'+source['dataset']+'.json' if source.get('dataset') else source['url']+'?f=json','pagination':'Socrata :id ordered 1000-row offset pages' if source.get('dataset') else 'ArcGIS object-ID discovery +50-ID batches;100000feature ceiling','authentication':'Public requests observed without credentials; no key stored','rate_limit':'Not published in cached metadata;429retry/backoff, no unverified numeric quota','timeout_seconds':60,'maximum_attempts':3,'backoff_seconds':[1,2],'incremental_refresh':'Not used; bounded full query. No verified delta/deletion token supplied; explicit refresh preserves snapshots.','update_frequency':meta.get('metadata',{}).get('custom_fields',{}).get('Dataset Information',{}).get('Update Frequency') or None,'source_update_value':original.get('source_updated') or meta.get('editingInfo',{}).get('lastEditDate'),'source_update_unit':'epoch_seconds' if source.get('dataset') else 'epoch_milliseconds','source_date_scope':'Dataset update, not acquisition/effective date','acquisition_date':None,'effective_date':None,'retrieved_utc':original.get('retrieved_utc'),'request_retrieval_range_utc':original.get('request_retrieval_range_utc'),'source_xy_crs':meta.get('extent',{}).get('spatialReference') or 'portal optional WGS84 geocoded column; not used as exact identity','output_xy_crs':'EPSG4326','horizontal_units':'degrees','native_horizontal_units':CRS.from_epsg(meta['extent']['spatialReference'].get('latestWkid',meta['extent']['spatialReference']['wkid'])).axis_info[0].unit_name if meta.get('extent',{}).get('spatialReference') else None,'vertical_datum':'not supplied/not used; no elevation inference','redistribution':'No affirmative dataset license inferred; agency source terms apply','license_id':meta.get('licenseId'),'copyright_text':meta.get('copyrightText'),'field_dictionary':[{k:f.get(k) for k in ('name','alias','type','domain')} for f in meta.get('fields',[]) if f['name'] in source['fields']] if not source.get('dataset') else [{'name':f['fieldName'],'type':f.get('dataTypeName'),'alias':f.get('name')} for f in meta.get('columns',[]) if f['fieldName'] in source['fields']],'public_fields':source['fields'],'supplemental_not_active_snapshot':supplemental})
 benchmark=client.get(GIS+'City_of_Orlando_NAVD_88_Published_Benchmarks_WFL1/FeatureServer/1',{'f':'json'})
 requests=client.accesses
 for entry in register:
  if entry['supplemental_not_active_snapshot']:
   accesses=[a for a in requests if a['url'].split('?')[0] in (entry['api_url'],entry['api_url']+'/query')];known=sorted(a['retrieved_utc'] for a in accesses if a.get('retrieved_utc'));entry['retrieved_utc']=known[-1] if known and len(known)==len(accesses) else None;entry['request_retrieval_range_utc']=[known[0],known[-1]] if known else None
 for access in requests:
  target=access['url'];path=root/'data/cache/city_adapter_discovery'/(hashlib.sha256(target.encode()).hexdigest()+'.json');dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 for path in [root/'data/processed/active.json',root/'config/study_area.json',root/'tools/city_adapter_contract.py',root/'tools/data_pipeline.py']:dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 packet={'schema':'twin.city-adapter/1','source_snapshot':active['snapshot'],'created_utc':now(),'source_register':register,'tables':tables,'quality':quality,'normalized_field_dictionary':{'entity_id':'Source/dataset-scoped original row identity, not a permanent cross-republication physical entity','entity_type':'Address, permit, business license, planning polygon or public reference remain distinct','source_fields':'Approved source fields only; nulls retained, original source identifiers/dates not replaced by build time','geometry':'Publisher geometry normalized to WGS84; invalid geometry quarantined as null','geometry_quality':'Reference/invalid/missing/outside context; not surveyed accuracy','source_dates':'Original source field values and names; acquisition/effective definitions remain unknown unless separately documented'},'first_five_safe_rows':{name:rows[:5] for name,rows in tables.items()},'discovery':{'official_catalog':'https://www.orlando.gov/Our-Government/Records-and-Documents/Map-Library/GIS-Data-Download','portal':'https://data.cityoforlando.net/','service_directory':GIS.rstrip('/'),'published_services':services,'benchmark_candidate':{'source_url':GIS+'City_of_Orlando_NAVD_88_Published_Benchmarks_WFL1/FeatureServer/1','oid':benchmark.get('objectIdField'),'geometry_type':benchmark.get('geometryType'),'source_crs':benchmark.get('extent',{}).get('spatialReference'),'elevation_units':None,'coverage':'Metadata only; no control elevation/urban DEM accepted'},'address_layer_verified':'Address_Point/FeatureServer/22','tree_inventory':'No tree-named service in inspected official131-service directory; not proof no inventory exists. Unrelated-city web tree results excluded.','elevation':'City published NAVD88 benchmark POINT layer1 exists; not a City bare-earth DEM. Elevation controls/units still require point-record review. USGS/NOAA/SJRWMD sources remain separate.','parcels_buildings':'County OCPA adapter, not assumed City source; source catalog and lineage retain separate identities.'},'coverage':{'query_bbox_wgs84':bbox,'main_street_extent':'covered by active extraction, not feature completeness','neighborhood_extent_percent':None,'scope_note':'Supplemental addresses/FLU use the configured bounded extraction; no full-neighborhood feature-completeness claim. Full-neighborhood ownership/parks/current-vacancy/FLU-PD review remains separate.'},'limits':['Historical business licenses never become current storefront tenants. Permit joins remain parcel context, not subject-building identity.','Addresses, parcels, building groups, licenses and permit records remain separate entities; address points do not promote parcel/building links.','No private BOOMS inputs or credentials used. No scene or snapshot activation.','Ownership/vacancy and governing ordinance/PD effective conditions are not established by zoning/FLU polygons.'],'requests':requests,'dependencies':dependencies}
 out=root/OUT;path=out/'packet.json';receipt=out/'receipt.json'
 if path.exists()!=receipt.exists():raise ValueError('Incomplete City packet; preserve prior output')
 if path.exists():
  previous=read(receipt)
  if previous.get('sha256')!=sha(path):raise ValueError('Preserve manually modified City packet')
  backup=out/'backups'/now().replace(':','_');backup.mkdir(parents=True);shutil.copy2(path,backup/path.name);shutil.copy2(receipt,backup/receipt.name)
 atomic_json(path,packet);atomic_json(receipt,{'source_snapshot':active['snapshot'],'sha256':sha(path)})
 return packet

def validate(root=ROOT):
 root=Path(root).resolve();path=root/OUT/'packet.json';p=read(path);receipt=read(root/OUT/'receipt.json')
 if sha(path)!=receipt['sha256'] or receipt['source_snapshot']!=p['source_snapshot'] or p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot']:raise ValueError('City packet snapshot/checksum stale')
 for name,value in p['dependencies'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or sha(path)!=value:raise ValueError('City adapter source changed')
 return p
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
 try:p=build(offline=args.offline)
 except Exception as exc:
  atomic_json(ROOT/OUT/'last_failure.json',{'created_utc':now(),'status':'failed_preserved_prior_packet_and_active_snapshot','error_type':type(exc).__name__,'message':str(exc)});raise
 print(json.dumps({'source_snapshot':p['source_snapshot'],'counts':{n:len(v) for n,v in p['tables'].items()},'issues':{n:len(v['issues']) for n,v in p['quality'].items()},'active_snapshot_modified':False}))
