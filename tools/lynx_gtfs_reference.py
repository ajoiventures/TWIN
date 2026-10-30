"""Official static LYNX GTFS inspection and cached study-area schedule references."""
from pathlib import Path
import os,sys,json,csv,io,zipfile,hashlib,datetime,urllib.request,re,shutil,collections,math
from zoneinfo import ZoneInfo
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import atomic_json,now
import shapely
from shapely.geometry import Point,LineString,box,mapping,shape
from pyproj import Transformer
CACHE='data/cache/lynx_gtfs_reference';OUT='data/processed/lynx_gtfs_reference'
PAGE='https://www.golynx.com/maps-schedules/data-download.stml';INDEX='http://gtfsrt.golynx.com/gtfsrt/';ZIP=INDEX+'google_transit.zip'
FILES=('agency.txt','feed_info.txt','calendar.txt','calendar_dates.txt','stops.txt','routes.txt','trips.txt','shapes.txt','stop_times.txt')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def date(s):return datetime.datetime.strptime(s,'%Y%m%d').date()
def today():return datetime.datetime.now(ZoneInfo('America/New_York')).date()
def acquire(root,offline):
 cache=root/CACHE;cache.mkdir(parents=True,exist_ok=True)
 specs=[('official_page.html','official_page.receipt.json',PAGE,2*1024*1024),('download_index.body','download_index.receipt.json',INDEX,2*1024*1024),('google_transit.zip','google_transit.receipt.json',ZIP,16*1024*1024)]
 for name,receipt_name,url,limit in specs:
  path=cache/name;receipt=cache/receipt_name
  if path.exists()!=receipt.exists():raise ValueError('Partial GTFS source cache; preserve and explicitly review')
  if path.exists():
   proof=read(receipt)
   if proof['url']!=url or proof['sha256']!=sha(path):raise ValueError('GTFS source cache changed')
   continue
  if offline:raise ValueError('GTFS offline source missing')
  with urllib.request.urlopen(url,timeout=20) as response:data=response.read(limit+1);final=response.geturl();ctype=response.headers.get('Content-Type')
  if len(data)>limit or name.endswith('.zip') and not data.startswith(b'PK'):raise ValueError('GTFS source size/signature invalid')
  path.write_bytes(data);atomic_json(receipt,{'url':url,'final_url':final,'retrieved_utc':now(),'sha256':sha(path),'bytes':len(data),'content_type':ctype})
 page=(cache/'official_page.html').read_text(encoding='utf-8');index=(cache/'download_index.body').read_text(encoding='utf-8')
 if not re.search(r'href=["\']http://gtfsrt\.golynx\.com/gtfsrt/["\']',page,re.I) or not re.search(r'href=["\']/gtfsrt/google_transit\.zip["\']',index,re.I):raise ValueError('Official page/index download association changed')
 return cache

def load_tables(path):
 z=zipfile.ZipFile(path)
 if any(Path(i.filename).name!=i.filename for i in z.infolist()) or sum(i.file_size for i in z.infolist())>64*1024*1024:raise ValueError('GTFS ZIP path/expanded-size rejected')
 if any(n not in z.namelist() for n in FILES):raise ValueError('Required feed tables missing')
 tables={};schemas={}
 for name in FILES:
  reader=csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig')));schemas[name]=reader.fieldnames;tables[name]=list(reader)
  if any(None in row for row in tables[name]):raise ValueError('Malformed GTFS CSV row')
 return tables,schemas

def unique(rows,key):
 values=[r.get(key) for r in rows]
 if any(not isinstance(v,str) or not v.strip() for v in values) or len(set(values))!=len(values):raise ValueError('Missing/duplicate original GTFS identity: '+key)
 return {r[key]:r for r in rows}

def checked_coordinates(latitude,longitude):
 lat,lon=float(latitude),float(longitude)
 if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError('Nonfinite or out-of-range GTFS coordinates')
 return lon,lat

def check_sequence_key(seen,identifier,value):
 text=str(value).strip()
 if not text.isdigit():raise ValueError('Invalid nonnegative integer GTFS sequence')
 key=(identifier,int(text))
 if key in seen:raise ValueError('Duplicate semantic numeric GTFS sequence')
 seen.add(key)
 return key

def active_services(calendar,exceptions,day):
 weekday=('monday','tuesday','wednesday','thursday','friday','saturday','sunday')[day.weekday()];active=set()
 for r in calendar:
  if any(r[k] not in ('0','1') for k in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday')):raise ValueError('Invalid calendar weekday code')
  if date(r['end_date'])<date(r['start_date']):raise ValueError('Calendar period reversed')
  if date(r['start_date'])<=day<=date(r['end_date']) and r[weekday]=='1':active.add(r['service_id'])
 seen=set()
 for r in exceptions:
  key=(r['service_id'],r['date'])
  if key in seen or r['exception_type'] not in ('1','2'):raise ValueError('Duplicate/conflicting calendar exception')
  seen.add(key)
  if date(r['date'])==day:
   if r['exception_type']=='1':active.add(r['service_id'])
   else:active.discard(r['service_id'])
 return active

def build(root=ROOT,offline=False,service_date=None):
 root=Path(root).resolve();out=root/OUT;receipt=out/'receipt.json';names={'packet.json','stops.geojson','shapes.geojson'}
 if receipt.exists():
  proof=read(receipt)
  if set(proof.get('artifacts',{}))!=names or any(sha(out/n)!=h for n,h in proof['artifacts'].items()):raise ValueError('Preserve modified GTFS publication')
 elif any((out/n).exists() for n in names):raise ValueError('Unreceipted GTFS publication')
 cache=acquire(root,offline);index_text=(cache/'download_index.body').read_text(encoding='utf-8');index_stamp=re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)\s+\d+\s+<A\s+HREF=[\"\']/gtfsrt/google_transit\.zip',index_text,re.I);tables,schemas=load_tables(cache/'google_transit.zip');active=read(root/'data/processed/active.json');study=read(root/'config/study_area.json');roi=box(*study['acquisition_bbox_wgs84']);day=datetime.date.fromisoformat(service_date) if service_date else today();stops=unique(tables['stops.txt'],'stop_id');routes=unique(tables['routes.txt'],'route_id');trips=unique(tables['trips.txt'],'trip_id');calendar=unique(tables['calendar.txt'],'service_id');serviceids=set(calendar)|{r['service_id'] for r in tables['calendar_dates.txt']};services=active_services(tables['calendar.txt'],tables['calendar_dates.txt'],day)
 if any(t['route_id'] not in routes or t['service_id'] not in serviceids for t in trips.values()):raise ValueError('GTFS trip references missing route/calendar')
 selected_stops={};stop_features=[]
 for ident,r in stops.items():
  lon,lat=checked_coordinates(r['stop_lat'],r['stop_lon'])
  point=Point(lon,lat)
  if not point.intersects(roi):continue
  selected_stops[ident]=r;stop_features.append({'type':'Feature','id':'lynx-gtfs-stop:'+ident,'geometry':mapping(point),'properties':{**r,'quality':'published_static_stop_reference_not_surveyed_accessibility','wheelchair_code_scope':'Original GTFS code, not an audited accessible route'}})
 grouped=collections.defaultdict(list);sequence_keys=set()
 for r in tables['shapes.txt']:
  if not r['shape_id'].strip():raise ValueError('Missing GTFS shape identity')
  check_sequence_key(sequence_keys,r['shape_id'],r['shape_pt_sequence']);checked_coordinates(r['shape_pt_lat'],r['shape_pt_lon']);grouped[r['shape_id']].append(r)
 shape_features=[];selected_shape_ids=set()
 for ident,rows in grouped.items():
  rows=sorted(rows,key=lambda r:int(r['shape_pt_sequence']));line=LineString([(float(r['shape_pt_lon']),float(r['shape_pt_lat'])) for r in rows])
  if not line.is_valid:raise ValueError('Invalid GTFS shape')
  if not line.intersects(roi):continue
  selected_shape_ids.add(ident);shape_features.append({'type':'Feature','id':'lynx-gtfs-shape:'+ident,'geometry':mapping(line.intersection(roi)),'properties':{'shape_id':ident,'geometry_role':'clipped GTFS scheduled path, not a carriageway edge or surveyed lane'}})
 if any(r.get('shape_id') and r['shape_id'] not in grouped for r in trips.values()):raise ValueError('Trip shape missing')
 serving_trip_ids=set();stop_times=[];maxhour=0;trip_sequences=set()
 for r in tables['stop_times.txt']:
  check_sequence_key(trip_sequences,r['trip_id'],r['stop_sequence'])
  if r['trip_id'] not in trips or r['stop_id'] not in stops:raise ValueError('Dangling trip/stop in stop_times')
  for key in ('arrival_time','departure_time'):
   if not r.get(key):continue
   pieces=r[key].strip().split(':')
   if len(pieces)!=3 or not all(v.isdigit() for v in pieces) or not 0<=int(pieces[1])<60 or not 0<=int(pieces[2])<60:raise ValueError('Invalid GTFS service-day time')
   maxhour=max(maxhour,int(pieces[0]))
  if r['stop_id'] in selected_stops:serving_trip_ids.add(r['trip_id']);stop_times.append(r)
 selected_trips=[r for r in trips.values() if r['trip_id'] in serving_trip_ids or r.get('shape_id') in selected_shape_ids];selected_route_ids={r['route_id'] for r in selected_trips};selected_service_ids={r['service_id'] for r in selected_trips};selected_routes=[r for r in routes.values() if r['route_id'] in selected_route_ids];feed=tables['feed_info.txt'][0]
 if len(tables['feed_info.txt'])!=1:raise ValueError('Ambiguous feed-info period')
 start,end=date(feed['feed_start_date']),date(feed['feed_end_date'])
 if end<start:raise ValueError('Feed validity reversed')
 date_status='expired' if day>end else 'not_yet_effective' if day<start else 'within_published_feed_period'
 selected={'stops':list(selected_stops.values()),'routes':selected_routes,'trips':selected_trips,'stop_times':stop_times,'calendar':[r for r in tables['calendar.txt'] if r['service_id'] in selected_service_ids],'calendar_dates':[r for r in tables['calendar_dates.txt'] if r['service_id'] in selected_service_ids],'feed_info':tables['feed_info.txt'],'agency':[{k:v for k,v in r.items() if k in ('agency_id','agency_name','agency_url','agency_timezone')} for r in tables['agency.txt']]}
 gispath=root/'data/transport/lynx_transit.json';gis=read(gispath)
 if gis['source_snapshot']!=active['snapshot']:raise ValueError('GIS comparison snapshot stale')
 by_trim=collections.defaultdict(list)
 for ident in selected_stops:by_trim[ident.strip()].append(ident)
 project=Transformer.from_crs(4326,32617,always_xy=True).transform;comparisons=[]
 for f in gis['stops']['features']:
  raw=str(f['properties'].get('StopId'));matches=by_trim.get(raw.strip(),[]);a=shapely.transform(shape(f['geometry']),project,interleaved=False);distances=[a.distance(shapely.transform(Point(float(selected_stops[k]['stop_lon']),float(selected_stops[k]['stop_lat'])),project,interleaved=False)) for k in matches];comparisons.append({'gis_source_object_id':f['properties']['source_object_id'],'gis_StopId':f['properties'].get('StopId'),'gtfs_original_stop_ids':matches,'match_method':'same-provider identifier after explicit whitespace-only trim; original raw IDs preserved','minimum_point_separation_m':min(distances) if distances else None,'identity_promoted':False})
 gtfs_labels={r['route_short_name'].strip() for r in selected_routes};gis_labels={str(f['properties'].get('LineAbbr')) for f in gis['routes']['features']};dependencies={}
 for path in [root/'data/processed/active.json',root/'config/study_area.json',root/'tools/lynx_gtfs_reference.py',gispath,*[cache/n for n in ('official_page.html','official_page.receipt.json','download_index.body','download_index.receipt.json','google_transit.zip','google_transit.receipt.json')]]:dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 packet={'schema':'twin.lynx-static-gtfs/1','source_snapshot':active['snapshot'],'built_utc':now(),'publisher':'Central Florida Regional Transportation Authority / LYNX','official_download_page':PAGE,'actual_provider_index':INDEX,'static_feed_url':ZIP,'source_receipt':read(cache/'google_transit.receipt.json'),'feed_validity':{'start':start.isoformat(),'end':end.isoformat(),'evaluation_service_date':day.isoformat(),'status':date_status,'agency_timezone':selected['agency'][0]['agency_timezone'],'current_service_verified':False},'source_field_dictionary':schemas,'normalized_field_dictionary':{'source_IDs':'Exact original strings, including provider padding/leading zeroes; no numeric coercion','calendar':'Scheduled weekday/date applicability plus explicit add/remove exceptions','stop_times':'Scheduled service-day HH:MM:SS; times beyond24h stay next-day service times, not UTC or actual arrival','shapes':'Scheduled route path clipped to study rectangle, not lane geometry','wheelchair_boarding':'Original provider GTFS enum only, no independently verified ADA/path claim'},'tables':selected,'coverage':{'bbox_wgs84':study['acquisition_bbox_wgs84'],'stops_in_study':len(selected_stops),'shape_variants_intersect_study':len(shape_features),'route_short_names_intersect_study':sorted(gtfs_labels),'trips_serving_stops_or_intersecting_shapes':len(selected_trips),'trips_serving_study_stops':len(serving_trip_ids),'source_table_rows':{n:len(r) for n,r in tables.items()}},'schedule_summary':{'active_service_ids_on_evaluation_date':sorted(services&selected_service_ids),'active_selected_trip_count':sum(r['service_id'] in services for r in selected_trips),'active_trips_serving_study_stops':sum(trips[k]['service_id'] in services for k in serving_trip_ids),'maximum_source_service_hour':maxhour,'realtime_available':False,'observed_vehicle_positions_or_arrivals':False},'gis_reconciliation':{'stop_candidates':comparisons,'route_short_name_context_only':True,'gis_labels_not_in_current_intersecting_GTFS_shapes':sorted(gis_labels-gtfs_labels),'GTFS_labels_not_in_GIS_scope':sorted(gtfs_labels-gis_labels),'automatic_route_or_stop_replacement':False},'first_five_safe_rows':{**{n:r[:5] for n,r in selected.items()},'shape_points':[r for r in tables['shapes.txt'] if r['shape_id'] in selected_shape_ids][:5]},'shape_point_preview_scope':'First five original shape-point rows whose original shape_id is one of the four study-intersecting variants; preview only, full source table not duplicated','source_dates':{'provider_index_file_timestamp':index_stamp.group(1) if index_stamp else None,'provider_index_timestamp_timezone':None,'provider_index_timestamp_scope':'Original directory text, not acquisition/effective time','feed_dates_mean':'Published schedule validity, not real-time service/last survey','acquisition_date':None},'reference_system':{'stop_shape_xy':'GTFS WGS84 latitude/longitude, normalized output EPSG4326','comparison_distances':'EPSG32617 metres','vertical_datum':'not supplied/not used'},'rights':{'terms':'Official LYNX page supplies data as-is; original terms page retained and linked','refresh_cadence':'LYNX GIS page states three bid changes per year; does not promise exact GTFS publication schedule','authentication':'Public HTTP download observed, no key','rate_limit':'Not published; one bounded cached feed download','public_redistribution_permission':'Not inferred beyond official data access; no rawZIP committed'},'limits':['Static scheduled references, not observed bus movement, arrival predictions, live traffic or proof every trip actually operates.','Dates and calendar exceptions are provider schedule evidence; expired/not-yet-effective feeds retain explicit status.','GIS/GTFS identifiers and route geometry can differ by vintage; candidates remain independent without automatic merge.','Feed includes raw identifier whitespace; preserved exactly, explicit trim is only a recorded reconciliation candidate.','No phone/email/fare data published; no realtime protobuf endpoint fetched.'],'dependencies':dependencies,'active_snapshot_changed':False,'scene_changed':False}
 for source in gis.get('sources',{}).values():
  for access in source.get('request_receipts',[]):
   path=root/'data/cache/transit'/(hashlib.sha256(access['url'].encode()).hexdigest()+'.json')
   if not path.exists() or access.get('sha256') and sha(path)!=access['sha256']:raise ValueError('LYNX GIS transitive source cache changed')
   dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
   receipt_path=path.with_suffix('.provenance.json')
   if receipt_path.exists():dependencies[str(receipt_path.relative_to(root)).replace('\\','/')]=sha(receipt_path)
 if any(sha(root/n)!=h for n,h in dependencies.items()):raise ValueError('GTFS comparison inputs changed during build')
 stopsgeo={'type':'FeatureCollection','features':stop_features};shapesgeo={'type':'FeatureCollection','features':shape_features};payloads={'packet.json':json.dumps(packet,indent=2).encode(),'stops.geojson':json.dumps(stopsgeo,indent=2).encode(),'shapes.geojson':json.dumps(shapesgeo,indent=2).encode()}
 if receipt.exists():
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for n in [*names,'receipt.json']:shutil.copy2(out/n,backup/n)
 out.mkdir(parents=True,exist_ok=True)
 for n,body in payloads.items():temp=out/(n+'.tmp');temp.write_bytes(body);temp.replace(out/n)
 atomic_json(receipt,{'source_snapshot':active['snapshot'],'artifacts':{n:sha(out/n) for n in names}});return packet

def validate(root=ROOT,service_date=None):
 root=Path(root).resolve();out=root/OUT;p=read(out/'packet.json');receipt=read(out/'receipt.json')
 if p.get('schema')!='twin.lynx-static-gtfs/1' or set(receipt.get('artifacts',{}))!={'packet.json','stops.geojson','shapes.geojson'} or not p.get('dependencies'):raise ValueError('GTFS proof incomplete')
 if p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or receipt['source_snapshot']!=p['source_snapshot']:raise ValueError('GTFS comparison snapshot stale')
 for n,h in receipt['artifacts'].items():
  if sha(out/n)!=h:raise ValueError('GTFS output changed')
 for n,h in p['dependencies'].items():
  path=(root/n).resolve()
  if not path.is_relative_to(root) or sha(path)!=h:raise ValueError('GTFS dependency changed')
 day=datetime.date.fromisoformat(service_date) if service_date else today();start=datetime.date.fromisoformat(p['feed_validity']['start']);end=datetime.date.fromisoformat(p['feed_validity']['end']);p['read_time_validity']={'service_date':day.isoformat(),'status':'expired' if day>end else 'not_yet_effective' if day<start else 'within_published_feed_period','scheduled_only':True}
 services=active_services(p['tables']['calendar'],p['tables']['calendar_dates'],day);serving={r['trip_id'] for r in p['tables']['stop_times']};p['read_time_schedule_summary']={'service_date':day.isoformat(),'active_service_ids':sorted(services),'scheduled_selected_trip_count':sum(r['service_id'] in services for r in p['tables']['trips']),'scheduled_trips_serving_study_stops':sum(r['service_id'] in services and r['trip_id'] in serving for r in p['tables']['trips']),'actual_operation_verified':False};return p
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--service-date');args=parser.parse_args();p=build(offline=args.offline,service_date=args.service_date);print(json.dumps({'coverage':p['coverage'],'feed_validity':p['feed_validity'],'schedule_summary':p['schedule_summary'],'GIS_route_gaps':p['gis_reconciliation']['gis_labels_not_in_current_intersecting_GTFS_shapes']}))
