"""Official-source adapters and atomic, offline-readable College Park snapshots.

No private BOOMS values or owner/contact columns are imported by this pipeline.
"""
from pathlib import Path
import sys,os,json,hashlib,time,datetime,urllib.request,urllib.parse,urllib.error,re,concurrent.futures,argparse,collections,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape,mapping,box
from shapely.ops import transform,unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

BBOX=json.loads((ROOT/'config/study_area.json').read_text(encoding='utf-8'))['acquisition_bbox_wgs84'] if (ROOT/'config/study_area.json').exists() else [-81.398,28.5605,-81.379,28.5845]
SINCE='2024-10-27T00:00:00'
GIS='https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/'
SODA='https://data.cityoforlando.net'
SOURCES={
 'parcels':{'url':'https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4','publisher':'Orange County Property Appraiser','fields':['OBJECTID','PARCEL','SITUS','DOR_CODE','ZONING_CODE','STYS','AYB','ACREAGE'],'oid':'OBJECTID'},
 'streets':{'url':GIS+'Street_Centerline/FeatureServer/0','publisher':'City of Orlando','fields':['OBJECTID','GlobalID','FullStreetName','CenterlineID','RoadClass','Speed','PaveType'],'oid':'OBJECTID'},
 'neighborhoods':{'url':GIS+'OrlandoPoliticalNeighborhoods/FeatureServer/0','publisher':'City of Orlando','fields':['Object_ID','NeighborhoodName','NeighborhoodID'],'oid':'Object_ID'},
 'zoning':{'url':GIS+'OrlandoLUZoning/FeatureServer/0','publisher':'City of Orlando','fields':['OBJECTID','Zoning','PD_NAME','FormatDate'],'oid':'OBJECTID'},
 'parks':{'url':GIS+'OrlandoParks/FeatureServer/0','publisher':'City of Orlando','fields':['OBJECTID','NAME','ADDRESS','TYPE','CLASS'],'oid':'OBJECTID'},
 'permits':{'dataset':'ryhf-m453','url':SODA+'/resource/ryhf-m453.json','publisher':'City of Orlando','fields':['permit_number','parcel_number','permit_address','application_type','application_status','processed_date','issue_permit_date','final_date','neighborhood','mainstreet_district']},
 'businesses':{'dataset':'7388-4re5','url':SODA+'/resource/7388-4re5.json','publisher':'City of Orlando','fields':['case_number','business_name','business_address','license_status','license_type','license_category','last_licensed_issue_date','business_close_date','neighborhood_name','main_street_district_name','geocoded_column']}}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(exist_ok=True,parents=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)
def clean_pin(value):
 # String identifiers retain leading zeros. Do not silently reverse STR/RTS segments.
 if value is None:return ''
 return re.sub('[^A-Za-z0-9]','',str(value)).upper()
def clean_address(value):
 text=str(value or '').upper().split(',')[0]
 return re.sub(r'\s+',' ',re.sub('[^A-Z0-9 ]',' ',text)).strip()
def valid_polygon(geo):
 if not geo:return None
 try:g=shape(geo)
 except (ValueError,TypeError,KeyError,IndexError):return None
 if g.is_empty or not g.is_valid or g.geom_type not in ['Polygon','MultiPolygon']:return None
 return g

class Client:
 def __init__(self,cache,offline=False,refresh=False,opener=None,sleeper=time.sleep):
  self.cache=Path(cache);self.cache.mkdir(exist_ok=True,parents=True);self.offline=offline;self.refresh=refresh;self.opener=opener or urllib.request.urlopen;self.sleeper=sleeper;self.accesses=[]
 def get(self,url,params=None):
  target=url+('?' + urllib.parse.urlencode(params) if params else '')
  path=self.cache/(hashlib.sha256(target.encode()).hexdigest()+'.json')
  provenance=path.with_suffix('.provenance.json')
  if path.exists() and (self.offline or not self.refresh):
   meta=json.loads(provenance.read_text(encoding='utf-8')) if provenance.exists() else {'retrieved_utc':None,'retrieval_quality':'legacy_cache_original_retrieval_unknown'}
   digest=hashlib.sha256(path.read_bytes()).hexdigest()
   if meta.get('sha256') and meta['sha256']!=digest:
    raise ValueError('Cached response checksum mismatch; quarantine and explicitly refresh this request')
   self.accesses.append({'url':target,'cache_hit':True,'read_utc':now(),**meta});return json.loads(path.read_text(encoding='utf-8'))
  if self.offline:raise RuntimeError('Offline cache miss: '+url)
  req=urllib.request.Request(target,headers={'User-Agent':'TWIN/0.3 official-data-snapshot','Accept':'application/json'})
  for attempt in range(3):
   try:
    with self.opener(req,timeout=60) as response:data=json.load(response)
    if isinstance(data,dict) and data.get('error'):raise ValueError(str(data['error']))
    atomic_json(path,data);meta={'retrieved_utc':now(),'retrieval_quality':'network_response','sha256':hashlib.sha256(path.read_bytes()).hexdigest()};atomic_json(provenance,meta);self.accesses.append({'url':target,'cache_hit':False,'read_utc':now(),**meta});return data
   except urllib.error.HTTPError as exc:
    if exc.code not in [429,500,502,503,504] or attempt==2:raise
   except (TimeoutError,urllib.error.URLError):
    if attempt==2:raise
   self.sleeper(2**attempt)
  raise RuntimeError('Request failed')

def arcgis(client,source,bbox=BBOX):
 meta=client.get(source['url'],{'f':'json'});schema={f['name'] for f in meta.get('fields',[])}
 missing=set(source['fields'])-schema
 if missing:raise ValueError(f"Schema change at {source['url']}: missing {sorted(missing)}")
 params={'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'}
 result=client.get(source['url']+'/query',params)
 ids=sorted(set(result.get('objectIds') or []));features=[]
 if len(ids)>source.get('max_features',100000):raise ValueError('ArcGIS bounded-query feature cap exceeded')
 for i in range(0,len(ids),50):
  data=client.get(source['url']+'/query',{'f':'geojson','objectIds':','.join(map(str,ids[i:i+50])),'outFields':','.join(source['fields']),'outSR':4326,'returnGeometry':'true'})
  if data.get('exceededTransferLimit'):raise ValueError('Truncated ArcGIS ID batch')
  features.extend(data['features'])
 received={f['properties'][source['oid']] for f in features}
 if received!=set(ids) or len(features)!=len(ids):raise ValueError('ArcGIS count mismatch: missing, duplicate or unexpected source IDs')
 return {'type':'FeatureCollection','features':sorted(features,key=lambda f:f['properties'][source['oid']])},meta

def socrata(client,source,where):
 meta=client.get(SODA+'/api/views/'+source['dataset']+'.json');schema={c['fieldName'] for c in meta.get('columns',[])}
 if set(source['fields'])-schema:raise ValueError('Socrata schema changed: '+source['dataset'])
 rows=[];offset=0
 # Stable source row ID handles multiple license categories for one case number.
 while True:
  page=client.get(source['url'],{'$select':','.join(source['fields'])+','+':id as source_row_id','$where':where,'$order':':id ASC','$limit':1000,'$offset':offset})
  if not isinstance(page,list):raise ValueError('Expected Socrata row array')
  rows.extend(page)
  if len(page)<1000:break
  offset+=1000
  if offset>100000:raise ValueError('Query unexpectedly exceeds study-area cap')
 ids=[r['source_row_id'] for r in rows]
 if len(ids)!=len(set(ids)):raise ValueError('Socrata pagination produced duplicate source rows')
 return rows,meta

def normalize_parcels(collection):
 features=[];rejects=[]
 for f in collection['features']:
  p=f.get('properties') or {};g=valid_polygon(f.get('geometry'));pin=clean_pin(p.get('PARCEL'))
  reason='invalid_geometry' if not g else 'blank_parcel_id' if not pin else 'missing_source_object_id' if p.get('OBJECTID') is None else 'outside_study_extent' if not g.intersects(box(*BBOX)) else None
  if reason:
   rejects.append({'source_object_id':p.get('OBJECTID'),'reason':reason});continue
  flags=[]
  def number(value,field):
   if value in (None,''):return None
   try:result=float(value)
   except (ValueError,TypeError):flags.append(field+'_unusable');return None
   if isinstance(value,bool) or not math.isfinite(result):flags.append(field+'_unusable');return None
   return result
  raw_stories=p.get('STYS');stories=number(raw_stories,'stories')
  # Source zero values mean unknown, not a verified zero-story structure.
  if stories is not None and not 0<stories<=100:stories=None
  raw_year=number(p.get('AYB'),'year_built');year=int(raw_year) if raw_year and raw_year.is_integer() and 1700<=raw_year<=datetime.date.today().year+1 else None
  props={'id':'ocpa:'+str(p['OBJECTID']),'parcel_id':pin,'source_parcel_id':str(p['PARCEL']),'source_object_id':p['OBJECTID'],'site_address':p.get('SITUS'),'property_use_code':p.get('DOR_CODE'),'zoning_code':p.get('ZONING_CODE'),'stories':stories,'stories_quality':'appraiser attribute; not measured height' if stories else 'unknown','year_built':year,'area_acres':number(p.get('ACREAGE'),'area_acres'),'source':'parcels','attribute_quality_flags':flags}
  features.append({'type':'Feature','id':props['id'],'geometry':mapping(g),'properties':props})
 return {'type':'FeatureCollection','features':features},rejects

def building_joins(parcels,base_path):
 from pxr import Usd,UsdGeom
 stage=Usd.Stage.Open(str(base_path));features=parcels['features'];geoms=[shape(f['geometry']) for f in features];tree=STRtree(geoms)
 to_meters=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=to_meters.transform(-81.389,28.572)
 def project(x,y,z=None):
  xx,yy=to_meters.transform(x,y);return xx-ox,yy-oy
 local=[transform(project,g) for g in geoms];local_tree=STRtree(local)
 by_id=collections.defaultdict(list)
 for i,f in enumerate(features):by_id[f['properties']['parcel_id']].append(i)
 buildings=[]
 for prim in stage.GetPrimAtPath('/World/Buildings').GetChildren():
  mesh=UsdGeom.Mesh(prim);pts=mesh.GetPointsAttr().Get();ids=mesh.GetFaceVertexIndicesAttr().Get();sizes=mesh.GetFaceVertexCountsAttr().Get();k=0;tris=[]
  from shapely.geometry import Polygon
  for size in sizes:
   if size==3:tris.append(Polygon([(pts[j][0],pts[j][1]) for j in ids[k:k+3]]))
   k+=size
  footprint=unary_union(tris);raw=prim.GetCustomData();source_pin=clean_pin(raw.get('parcelId'));candidates=[]
  if footprint.area<=0:continue
  for idx in local_tree.query(footprint):
   idx=int(idx);ratio=footprint.intersection(local[idx]).area/footprint.area
   if ratio>=.5:candidates.append((idx,ratio))
  exact=[(i,r) for i,r in candidates if features[i]['properties']['parcel_id']==source_pin and r>=.8]
  best=exact or sorted(candidates,key=lambda p:p[1],reverse=True)
  # Repeated PINs/condo polygons are distinct feature rows. Multiple exact
  # candidates are ambiguous, never an arbitrary first-feature acceptance.
  chosen=best[0] if best and (len(exact)==1 or not exact and (len(best)==1 or best[0][1]-best[1][1]>.15)) else None
  p=features[chosen[0]]['properties'] if chosen else {}
  buildings.append({'id':prim.GetName(),'usd_path':str(prim.GetPath()),'source_parcel_id':source_pin,'parcel_id':p.get('parcel_id'),'parcel_feature_id':p.get('id'),'site_address':p.get('site_address'),'match_method':'id_and_geometry' if chosen and exact else 'spatial_review' if chosen else 'ambiguous_or_unmatched','overlap_ratio':round(chosen[1],4) if chosen else None,'candidate_parcels':sorted(set(features[i]['properties']['parcel_id'] for i,_ in candidates)),'geometry_quality':'public footprint, estimated height','height_m':raw.get('heightMeters'),'stories':p.get('stories')})
  buildings[-1].update({'source_building_number':str(raw.get('buildingNumber','')),'source_object_ids':str(raw.get('sourceObjectIds','')).split(',') if raw.get('sourceObjectIds') else [],'source_building_key':'ocpa-building:'+source_pin+':'+str(raw.get('buildingNumber','')),'candidate_parcel_features':[{'parcel_feature_id':features[i]['properties']['id'],'parcel_id':features[i]['properties']['parcel_id'],'overlap_ratio':round(ratio,4),'source_pin_matches':features[i]['properties']['parcel_id']==source_pin} for i,ratio in sorted(candidates,key=lambda item:(-item[1],features[item[0]]['properties']['id']))],'match_confidence_basis':'overlap fraction, not statistical probability','join_state':'accepted' if chosen and exact else 'spatial_review' if chosen else 'ambiguous' if candidates else 'unmatched'})
 return buildings

def refresh(offline=False,force=False):
 client=Client(ROOT/'data'/'cache'/'official',offline,force)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=ROOT/'data'/'snapshots'/stamp;folder.mkdir(parents=True)
 collections_out={};metadata={};manifest=[]
 def load_arc(item):
  name,source=item;data,meta=arcgis(client,source);return name,data,meta
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
  for name,data,meta in pool.map(load_arc,[(n,s) for n,s in SOURCES.items() if 'dataset' not in s]):collections_out[name]=data;metadata[name]=meta
 clean,rejects=normalize_parcels(collections_out['parcels']);collections_out['parcels']=clean
 pins=sorted(set(f['properties']['parcel_id'] for f in clean['features']))
 permit_rows=[];meta=None
 # Parcel-based retrieval includes records without map coordinates, unlike within_box alone.
 for i in range(0,len(pins),35):
  where="parcel_number in ("+','.join("'"+p+"'" for p in pins[i:i+35])+") AND processed_date >= '"+SINCE+"'"
  rows,meta=socrata(client,SOURCES['permits'],where);permit_rows.extend(rows)
  if i%350==0:print('Permit parcels queried',min(i+35,len(pins)),'/',len(pins),flush=True)
 collections_out['permits']=permit_rows;metadata['permits']=meta
 where="upper(neighborhood_name) = 'COLLEGE PARK' OR upper(main_street_district_name) like '%COLLEGE PARK%' OR within_box(geocoded_column,"+','.join(map(str,[BBOX[3],BBOX[0],BBOX[1],BBOX[2]]))+")"
 businesses,meta=socrata(client,SOURCES['businesses'],where);collections_out['businesses']=businesses;metadata['businesses']=meta
 buildings=building_joins(clean,ROOT/'scene'/'college_park.usda');collections_out['buildings']=buildings
 parcel_index=collections.defaultdict(list)
 for b in buildings:
  if b['parcel_id']:parcel_index[b['parcel_id']].append(b['id'])
 for row in permit_rows:
  row['parcel_id']=clean_pin(row.get('parcel_number'));row['building_ids']=parcel_index.get(row['parcel_id'],[]);row['match_scope']='parcel_context_not_exact_subject_address'
 for name,data in collections_out.items():
  atomic_json(folder/(name+'.json'),data)
  if name in SOURCES:
   source=SOURCES[name];meta=metadata[name]
   count=len(data.get('features',[])) if isinstance(data,dict) else len(data)
   manifest.append({'id':name,'publisher':source['publisher'],'api_url':source['url'],'metadata_url':SODA+'/api/views/'+source['dataset']+'.json' if 'dataset' in source else source['url']+'?f=json','retrieved_utc':now(),'source_updated':meta.get('rowsUpdatedAt') or meta.get('editingInfo',{}).get('lastEditDate'),'rows':count,'fields_requested':source['fields'],'license_note':'Agency source terms apply; metadata is not a redistribution license.','geometry_crs':'EPSG:4326' if name not in ['permits','businesses'] else 'optional source WGS84 point','scope':BBOX,'since':SINCE if name=='permits' else None})
   atomic_json(folder/(name+'_metadata.json'),meta)
 # A snapshot build/read time is not the original retrieval time of cached agency data.
 for entry in manifest:
  accesses=[a for a in client.accesses if a['url'].split('?')[0] in [entry['api_url'],entry['api_url']+'/query',entry['metadata_url'].split('?')[0]]]
  known=[a['retrieved_utc'] for a in accesses if a.get('retrieved_utc')]
  entry['snapshot_built_utc']=entry.pop('retrieved_utc');entry['retrieved_utc']=max(known) if known and all(a.get('retrieved_utc') for a in accesses) else None
  entry['request_retrieval_range_utc']=[min(known),max(known)] if known else None
  entry['retrieval_quality']='all_request_times_known' if accesses and all(a.get('retrieved_utc') for a in accesses) else 'some_or_all_cached_request_times_unknown'
  entry['requests']=accesses
 issues=[r for r in buildings if r['match_method']!='id_and_geometry']
 report={'snapshot':stamp,'created_utc':now(),'bbox_wgs84':BBOX,'counts':{n:len(d['features']) if isinstance(d,dict) else len(d) for n,d in collections_out.items()},'parcel_rejects':rejects,'building_match_methods':dict(collections.Counter(b['match_method'] for b in buildings)),'unmatched_or_review_buildings':len(issues),'permit_scope':'last two years, queried by parcel ID; includes ungeocoded records','business_scope':'source College Park neighborhood/district OR bounding box; includes historical licenses, not verified current tenants','private_booms_imported':False,'limitations':['Parcel attributes do not establish surveyed building heights.','Spatial-only and ambiguous building links require review.','A business license is not verification of a current storefront.']}
 atomic_json(folder/'sources.json',manifest);atomic_json(folder/'quality.json',report);atomic_json(folder/'building_review.json',issues)
 # Publish pointer only after every source and normalization stage succeeds.
 atomic_json(ROOT/'data'/'processed'/'active.json',{'snapshot':stamp,'relative_path':'data/snapshots/'+stamp,'activated_utc':now()})
 print(json.dumps(report,indent=2));return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--force',action='store_true');args=parser.parse_args();refresh(args.offline,args.force)
