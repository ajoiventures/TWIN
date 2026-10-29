"""Cached snapshot API with local ephemeral selection exchange. No agency calls per request."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from pathlib import Path
import json,argparse,math,hashlib
from property_search import search_parcels
from selection_bridge import read_state as selection_state, publish as publish_selection, valid_origin, SelectionError, MAX_BODY
ROOT=Path(__file__).resolve().parents[1]
TABLES={'parcels','buildings','streets','neighborhoods','zoning','parks','permits','businesses','sources','quality','building_review','heights','height_quality','assets','asset_quality','scene_validation','pilot','source_catalog','pedestrian_access','crosswalk_candidates','study_boundaries','study_scope_quality','map_extent_quality','commercial_evidence','commercial_listings','commercial_model_quality','multifamily_review','multifamily_quality','reconstructions','corridor_building_review','corridor_building_quality'}
class SnapshotMismatch(ValueError):pass
class VerifiedReviewRows(list):pass
TABLES.update({'building_lineage','building_lineage_quality'})
TABLES.update({'city_addresses','city_future_land_use','city_adapter_quality','full_neighborhood_parks','full_neighborhood_parks_quality'})
TABLES.update({'county_addresses','county_roads','county_drainage_basins','county_context_quality'})
TABLES.update({'public_property_references','government_property_references','public_property_quality'})
def active_folder(root=ROOT):
 p=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
 folder=(root/p['relative_path']).resolve()
 if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid snapshot pointer')
 return folder,p['snapshot']
def current_report(path,snapshot):
 data=json.loads(path.read_text(encoding='utf-8'))
 if data.get('source_snapshot')!=snapshot:raise SnapshotMismatch('Rebuild '+path.name+' against active snapshot')
 return data

def read_table(name,root=ROOT):
 if name in ('public_property_references','government_property_references','public_property_quality'):
  from public_ownership import validate
  try:report=validate(root)
  except (ValueError,OSError) as exc:raise SnapshotMismatch('Government property references unavailable or stale') from exc
  if name=='public_property_quality':value={k:v for k,v in report.items() if k not in ('rows','excluded','first_five_safe_rows','first_five_government_reference_rows')}
  elif name=='government_property_references':value=[r for r in report['rows'] if r['government_reference_present']]
  else:value=report['rows']
  return value,report['source_snapshot']
 if name in ('county_addresses','county_roads','county_drainage_basins','county_context_quality'):
  from county_context import validate
  try:report=validate(root)
  except (ValueError,OSError) as exc:raise SnapshotMismatch('County context or its City comparison is unavailable or stale') from exc
  value=({k:v for k,v in report.items() if k!='layers'} if name=='county_context_quality' else report['layers'][name.removeprefix('county_')]['features'])
  return value,report['source_snapshot']
 if name in ('city_addresses','city_future_land_use','city_adapter_quality'):
  from city_adapter_contract import validate
  try:report=validate(root)
  except (ValueError,OSError) as exc:raise SnapshotMismatch('City source packet unavailable or stale') from exc
  value=({k:v for k,v in report.items() if k!='tables'} if name=='city_adapter_quality' else report['tables']['addresses' if name=='city_addresses' else 'future_land_use'])
  return value,report['source_snapshot']
 if name in ('full_neighborhood_parks','full_neighborhood_parks_quality'):
  from inventory_neighborhood_parks import validate
  try:report=validate(root)
  except (ValueError,OSError) as exc:raise SnapshotMismatch('Full-neighborhood park inventory unavailable or stale') from exc
  return (report['rows'] if name=='full_neighborhood_parks' else {k:v for k,v in report.items() if k!='rows'}),report['comparison_snapshot']
 if name in ('building_lineage','building_lineage_quality'):
  from build_building_lineage import validate
  try:report=validate(root)
  except (ValueError,OSError) as exc:raise SnapshotMismatch('Building source lineage unavailable; rebuild required') from exc
  return (report['records'] if name=='building_lineage' else {k:v for k,v in report.items() if k!='records'}),report['source_snapshot']
 if name=='land_review':
  _,snapshot=active_folder(root)
  report=current_report(root/'data/land/land_review.json',snapshot)
  if not report.get('dependencies'):raise SnapshotMismatch('Rebuild land review with source hashes')
  for relative,digest in report['dependencies'].items():
   path=(root/relative).resolve()
   if not path.is_relative_to(root.resolve()):raise SnapshotMismatch('Invalid land review dependency')
   if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SnapshotMismatch('Rebuild land review against current source files')
  return report,snapshot
 if name not in TABLES:raise KeyError(name)
 folder,snapshot=active_folder(root)
 if name in ('corridor_building_review','corridor_building_quality'):
  raw=(root/'data/processed/corridor_building_review.json').read_bytes();report=json.loads(raw)
  if report.get('source_snapshot')!=snapshot:raise SnapshotMismatch('Rebuild building review against active snapshot')
  report_digest=hashlib.sha256(raw).hexdigest()
  dependencies=report.get('dependencies')
  if not isinstance(dependencies,dict) or not dependencies:raise SnapshotMismatch('Building review requires source dependency hashes; rebuild it')
  for relative,digest in dependencies.items():
   if not isinstance(relative,str) or not isinstance(digest,str) or len(digest)!=64:raise SnapshotMismatch('Invalid building review dependency')
   path=(root/relative).resolve()
   if not path.is_relative_to(root.resolve()) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SnapshotMismatch('Building review is stale for current source files; rebuild it')
  if active_folder(root)[1]!=snapshot:raise SnapshotMismatch('Active snapshot changed while checking building review')
  if name=='corridor_building_review':
   rows=VerifiedReviewRows(report['rows']);rows.report_sha256=report_digest;return rows,snapshot
  return {**{k:v for k,v in report.items() if k not in ('rows','dependencies','original_35_queue','original_17_queue','upper_floor_review','official_subarea_floor_underuse')},'snapshot':snapshot,'report_sha256':report_digest},snapshot
 if name=='reconstructions':
  report=current_report(root/'data/processed/reconstructions.json',snapshot)
  for relative,digest in report['dependencies'].items():
   path=(root/relative).resolve()
   if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise SnapshotMismatch('Rebuild reconstruction register against current composition')
  return report['records'],snapshot
 if name in ['multifamily_review','multifamily_quality']:
  report=current_report(root/'data/processed/multifamily_review.json',snapshot)
  if report.get('identity_evidence_sha256') and report['identity_evidence_sha256']!=hashlib.sha256((root/'data/imagery/princeton_parcel_review/identity_evidence.json').read_bytes()).hexdigest():raise SnapshotMismatch('Rebuild housing review against current identity evidence')
  if report.get('height_evidence_sha256')!=hashlib.sha256((root/'data/heights/building_heights.json').read_bytes()).hexdigest():raise SnapshotMismatch('Rebuild housing review against current heights')
  return (report['rows'] if name=='multifamily_review' else {k:v for k,v in report.items() if k not in ['rows','source_requests']}),snapshot
 if name in ['commercial_evidence','commercial_listings','commercial_model_quality']:
  report=json.loads((root/'data/commercial/commercial_evidence.json').read_text(encoding='utf-8'))
  if report['source_snapshot']!=snapshot:raise SnapshotMismatch('Rebuild commercial evidence against active snapshot')
  if name=='commercial_listings':return report['listings'],snapshot
  if name=='commercial_model_quality':return current_report(root/'data/commercial/model_context_quality.json',snapshot),snapshot
  return report,snapshot
 if name in ['study_boundaries','study_scope_quality','map_extent_quality']:
  path=root/'data/processed'/('study_boundaries.geojson' if name=='study_boundaries' else name+'.json');data=json.loads(path.read_text(encoding='utf-8'))
  if name!='study_boundaries' and data.get('source_snapshot')!=snapshot:raise SnapshotMismatch('Rebuild scope/extent quality against active snapshot')
  if name=='map_extent_quality' and data.get('base_geometry_sha256')!=hashlib.sha256((root/'scene/college_park.usda').read_bytes()).hexdigest():raise SnapshotMismatch('Map extent evidence is stale for current geometry')
  return data,snapshot
 if name in ['source_catalog','pedestrian_access','crosswalk_candidates']:
  path=root/({'source_catalog':'data/processed/source_catalog.json','pedestrian_access':'data/transport/pedestrian_access_report.json','crosswalk_candidates':'data/transport/crosswalk_candidates.geojson'}[name])
  return json.loads(path.read_text(encoding='utf-8')),snapshot
 if name=='pilot':
  data=json.loads((root/'data/processed/pilot.json').read_text(encoding='utf-8'))
  if data['source_snapshot']!=snapshot:raise SnapshotMismatch('Rebuild pilot definition against active snapshot')
  return data,snapshot
 if name in ['assets','asset_quality','scene_validation']:
  registry=json.loads((root/'data/processed/asset_registry.json').read_text(encoding='utf-8'))
  if registry['source_snapshot']!=snapshot:raise SnapshotMismatch('Rebuild semantic registry against active snapshot')
  if name=='assets':return registry['records'],snapshot
  path=root/'data/processed'/('asset_registry_quality.json' if name=='asset_quality' else 'scene_validation.json')
  return current_report(path,snapshot),snapshot
 if name in ['heights','height_quality']:
  rows=json.loads((root/'data/heights/building_heights.json').read_text(encoding='utf-8'))
  if any(h['source_snapshot']!=snapshot for h in rows):raise SnapshotMismatch('Rebuild heights against active snapshot')
  if name=='heights':return rows,snapshot
  return current_report(root/'data/heights/height_quality.json',snapshot),snapshot
 data=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
 if name=='buildings':
  from build_building_lineage import validate,FIELDS
  try:
   lineage=validate(root);index={r['id']:r for r in lineage['records']}
   if lineage['source_snapshot']!=snapshot or set(index)!={r['id'] for r in data}:raise ValueError('Lineage census mismatch')
   for row in data:
    source=index[row['id']]
    row.update({key:source[key] for key in FIELDS if key not in row})
    row['source_lineage_status']='verified_against_frozen_snapshot'
  except (OSError,ValueError):
   for row in data:row['source_lineage_status']='unavailable_or_stale; original snapshot remains usable'
 if name=='buildings' and (root/'data/heights/building_heights.json').exists():
  index={h['building_id']:h for h in json.loads((root/'data/heights/building_heights.json').read_text(encoding='utf-8')) if h['source_snapshot']==snapshot}
  for row in data:
   h=index.get(row['id'])
   if h:row.update({'previous_estimated_height_m':row['height_m'],'height_m':h['height_m'],'height_quality':h['quality'],'height_method':h['method']})
 if name=='buildings' and (root/'data/processed/asset_registry.json').exists():
  registry=json.loads((root/'data/processed/asset_registry.json').read_text(encoding='utf-8'))
  if registry['source_snapshot']==snapshot:
   index={r['local_building_id']:r for r in registry['records']}
   for row in data:
    asset=index.get(row['id'])
    if asset:row.update({'entity_id':asset['entity_id'],'evidence_refs':asset['evidence_refs'],'parcel_link_accepted':asset['parcel_link_accepted'],'current_condition_verified':False})
 return data,snapshot
def matches_parcel_id(row, parcel_id):
 props=row.get('properties',row)
 return props.get('parcel_id')==parcel_id or parcel_id in props.get('parcel_ids',[])

def page_table(name,query,root=ROOT):
 data,snapshot=read_table(name,root)
 report_digest=getattr(data,'report_sha256',None)
 if isinstance(data,dict) and data.get('type')!='FeatureCollection':return data
 rows=data['features'] if isinstance(data,dict) else data
 if name=='corridor_building_review':
  for field in ('parcel_feature_id','state'):
   value=query.get(field,[''])[0]
   if value:rows=[r for r in rows if r.get(field)==value]
  scope=query.get('scope',[''])[0]
  if scope:rows=[r for r in rows if scope in r.get('scopes',[])]
  term=query.get('q',[''])[0].strip().casefold()
  if term:rows=[r for r in rows if any(term in str(r.get(k) or '').casefold() for k in ('site_address','parcel_feature_id','parcel_id','property_use_code'))]
 if name=='parcels' and 'q' in query:rows=search_parcels(rows,query['q'][0])
 field=query.get('parcel_id',[''])[0]
 if field:
  rows=[r for r in rows if matches_parcel_id(r,field)]
 limit=min(1000,max(1,int(query.get('limit',[100])[0])));offset=max(0,int(query.get('offset',[0])[0]))
 packet={'snapshot':snapshot,'total':len(rows),'limit':limit,'offset':offset,'rows':rows[offset:offset+limit]}
 if report_digest:packet['report_sha256']=report_digest
 return packet
class Handler(BaseHTTPRequestHandler):
 def send(self,body,status=200,kind='application/json; charset=utf-8'):
  raw=body if isinstance(body,bytes) else body.encode() if isinstance(body,str) else json.dumps(body,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  url=urlparse(self.path);path=url.path
  try:
   if path=='/':return self.send((ROOT/'web/index.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/source-browser':return self.send((ROOT/'web/source-browser.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/public-property/coverage':
    from public_ownership import validate,OUT
    try:validate(ROOT)
    except (ValueError,OSError):return self.send({'error':'Government property references unavailable or stale'},409)
    return self.send((ROOT/OUT/'coverage.svg').read_text(encoding='utf-8'),kind='image/svg+xml')
   if path=='/county-context/coverage':
    from county_context import validate,OUT
    try:validate(ROOT)
    except (ValueError,OSError) as exc:raise SnapshotMismatch('County coverage or its City comparison is stale') from exc
    return self.send((ROOT/OUT/'coverage.svg').read_bytes(),kind='image/svg+xml')
   if path=='/parks-inventory/coverage':
    from inventory_neighborhood_parks import validate,OUT
    try:validate(ROOT)
    except (ValueError,OSError) as exc:raise SnapshotMismatch('Park coverage is stale') from exc
    return self.send((ROOT/OUT/'coverage.svg').read_bytes(),kind='image/svg+xml')
   if path=='/land-review':return self.send((ROOT/'web/land-review.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/building-review':return self.send((ROOT/'web/building-review.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/transit':return self.send((ROOT/'web/transit.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/flood':return self.send((ROOT/'web/flood.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/water-context':return self.send((ROOT/'web/water-context.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/aerial-review':return self.send((ROOT/'web/aerial-review.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path in ('/api/v1/pilot_aerial_review','/aerial-review/coverage') or path.startswith('/aerial-review/reference/'):
    if path.startswith('/aerial-review/reference/') and path not in tuple('/aerial-review/reference/'+year for year in ('2022','2024','2025')):return self.send({'error':'Unknown dated reference'},404)
    from complete_pilot_aerial_review import validate_review
    try:report=validate_review(ROOT)
    except ValueError as exc:raise SnapshotMismatch(str(exc)) from exc
    if path=='/aerial-review/coverage':return self.send((ROOT/'data/imagery/pilot_complete/coverage.html').read_bytes(),kind='text/html; charset=utf-8')
    if path.startswith('/aerial-review/reference/'):
     year=path.rsplit('/',1)[-1]
     reference=next(r for r in report['references'] if r['acquisition']['month']==year+'-01')
     image=(ROOT/reference['image_path']).resolve()
     if not image.is_relative_to((ROOT/'data/imagery').resolve()) or image.suffix.lower() not in ('.jpg','.jpeg'):raise SnapshotMismatch('Invalid local aerial reference path')
     return self.send(image.read_bytes(),kind='image/jpeg')
    return self.send(report)
   if path in ('/api/v1/water_context','/water-reference/lake-adair-2025'):
    from build_water_context import validate_water_context
    try:report=validate_water_context(ROOT)
    except ValueError as exc:raise SnapshotMismatch(str(exc)) from exc
    if path=='/water-reference/lake-adair-2025':return self.send((ROOT/'data/cache/water_context/lake_adair_2025.jpg').read_bytes(),kind='image/jpeg')
    return self.send(report)
   if path in ('/api/v1/flood','/flood/coverage'):
    from build_flood_overlay import validate_packet
    try:report=validate_packet(ROOT)
    except ValueError as exc:raise SnapshotMismatch(str(exc)) from exc
    if path=='/flood/coverage':return self.send((ROOT/'data/flood/coverage.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
    return self.send(report)
   if path=='/api/v1/transit':
    _,snapshot=active_folder()
    report=current_report(ROOT/'data/transport/lynx_transit.json',snapshot)
    return self.send(report)
   if path=='/aerial-alignment':return self.send((ROOT/'data/imagery/aerial_alignment_review.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/road-review':return self.send((ROOT/'data/transport/road_reference_gallery.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path.startswith('/road-reference/'):
    files={'aerial2025':ROOT/'data/imagery/OCPA_Aerials2025_edgewater-princeton-smith-south-v1.jpg'}
    for resolution in ['1k','2k','4k']:
     files['asphalt-'+resolution]=ROOT/f'assets/generated/road_materials/{resolution}/asphalt_02_Diffuse_{resolution}.jpg'
    requested=path.removeprefix('/road-reference/')
    if requested not in files:return self.send({'error':'Unknown road reference'},404)
    return self.send(files[requested].read_bytes(),kind='image/jpeg')
   if path=='/source-coverage':return self.send((ROOT/'data/processed/source_coverage.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/api/v1/health':
    _,snapshot=active_folder();return self.send({'status':'ready','snapshot':snapshot,'mode':'local-read-only-snapshots','agency_calls_per_request':0})
   if path=='/api/v1/selection':return self.send(selection_state(ROOT))
   if path=='/api/v1/map':
    import sys
    sys.path.insert(0,str(ROOT/'.dependencies'))
    from pyproj import Transformer
    from shapely.geometry import shape,mapping,box
    from shapely.ops import transform
    folder,snapshot=active_folder();data={k:read_table(k)[0] for k in ['parcels','streets','neighborhoods','parks','buildings']}
    projection=Transformer.from_crs(4326,32617,always_xy=True)
    def xy(x,y,z=None):return projection.transform(x,y)
    for name in ['parcels','streets','neighborhoods','parks']:
     for f in data[name]['features']:
      geometry=shape(f['geometry'])
      if name=='parcels':
       point=geometry.representative_point();f['properties']['reference_point_wgs84']=[point.x,point.y]
      f['geometry']=mapping(transform(xy,geometry))
    extent=json.loads((folder/'quality.json').read_text(encoding='utf-8'))['bbox_wgs84'];extraction=transform(xy,box(*extent));data['extraction_geometry']=mapping(extraction)
    if (ROOT/'data/processed/study_boundaries.geojson').exists():
     boundaries=read_table('study_boundaries')[0]
     for f in boundaries['features']:f['geometry']=mapping(transform(xy,shape(f['geometry'])))
     data['study_boundaries']=boundaries
     try:data['study_scope_quality']=read_table('study_scope_quality')[0]
     except (SnapshotMismatch,FileNotFoundError):data['study_scope_quality']=None
    if (ROOT/'data/commercial/commercial_evidence.json').exists():
     try:data['commercial_evidence']=read_table('commercial_evidence')[0]
     except SnapshotMismatch:data['commercial_evidence']=None
    return self.send({'snapshot':snapshot,'map_crs':'EPSG:32617','bounds':list(extraction.bounds),**data})
   if path.startswith('/api/v1/'):
    name=path.removeprefix('/api/v1/');return self.send(page_table(name,parse_qs(url.query)))
   return self.send({'error':'Not found'},404)
  except SelectionError as exc:return self.send({'error':str(exc)},exc.status)
  except FileNotFoundError:return self.send({'error':'Required local snapshot or derived artifact unavailable; build the requested data product'},503)
  except SnapshotMismatch as exc:return self.send({'error':str(exc)},409)
  except KeyError:return self.send({'error':'Unknown table'},404)
  except (ValueError,TypeError):return self.send({'error':'Invalid query'},400)
 def do_POST(self):
  if urlparse(self.path).path!='/api/v1/selection':return self.send({'error':'Read-only API'},405)
  if not valid_origin(self.headers.get('Origin'),self.headers.get('Host'),self.server.server_address[1],self.client_address[0]):return self.send({'error':'Selection requires same-origin loopback access'},403)
  if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type','').split(';')[0].strip().lower()!='application/json':return self.send({'error':'Selection requires bounded JSON'},415)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=MAX_BODY:return self.send({'error':'Selection body too large or missing'},413)
   self.connection.settimeout(5)
   raw=self.rfile.read(length)
   if len(raw)!=length:raise ValueError('Incomplete body')
   payload=json.loads(raw)
   if not isinstance(payload,dict) or payload.get('sender')!='map':raise SelectionError('Browser endpoint accepts map selections only')
   return self.send(publish_selection(payload,ROOT))
  except SelectionError as exc:return self.send({'error':str(exc)},exc.status)
  except FileNotFoundError:return self.send({'error':'Selection context is unavailable'},503)
  except (ValueError,TypeError,TimeoutError):return self.send({'error':'Invalid selection JSON'},400)
 def do_PUT(self):self.send({'error':'Read-only API'},405)
 def do_DELETE(self):self.send({'error':'Read-only API'},405)
 def log_message(self,*args):pass
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8768);p.add_argument('--preserve-selection',action='store_true');a=p.parse_args()
 try:selection_state(ROOT,reset=not a.preserve_selection)
 except (OSError,ValueError) as exc:print('Selection bridge pending local snapshot:',str(exc),flush=True)
 print('TWIN snapshot API: http://127.0.0.1:'+str(a.port),flush=True);ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
