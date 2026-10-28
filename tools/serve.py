"""Local, read-only snapshot API. No request handler calls an agency service."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from pathlib import Path
import json,argparse,math
ROOT=Path(__file__).resolve().parents[1]
TABLES={'parcels','buildings','streets','neighborhoods','zoning','parks','permits','businesses','sources','quality','building_review','heights','height_quality','assets','asset_quality','scene_validation','pilot','source_catalog','pedestrian_access','crosswalk_candidates'}
class SnapshotMismatch(ValueError):pass
def active_folder(root=ROOT):
 p=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
 folder=(root/p['relative_path']).resolve()
 if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid snapshot pointer')
 return folder,p['snapshot']
def read_table(name,root=ROOT):
 if name not in TABLES:raise KeyError(name)
 folder,snapshot=active_folder(root)
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
  return json.loads(path.read_text(encoding='utf-8')),snapshot
 if name in ['heights','height_quality']:
  rows=json.loads((root/'data/heights/building_heights.json').read_text(encoding='utf-8'))
  if any(h['source_snapshot']!=snapshot for h in rows):raise SnapshotMismatch('Rebuild heights against active snapshot')
  if name=='heights':return rows,snapshot
  return json.loads((root/'data/heights/height_quality.json').read_text(encoding='utf-8')),snapshot
 data=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
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
def page_table(name,query,root=ROOT):
 data,snapshot=read_table(name,root)
 if isinstance(data,dict) and data.get('type')!='FeatureCollection':return data
 rows=data['features'] if isinstance(data,dict) else data
 field=query.get('parcel_id',[''])[0]
 if field:
  rows=[r for r in rows if (r.get('properties',r)).get('parcel_id')==field]
 limit=min(1000,max(1,int(query.get('limit',[100])[0])));offset=max(0,int(query.get('offset',[0])[0]))
 return {'snapshot':snapshot,'total':len(rows),'limit':limit,'offset':offset,'rows':rows[offset:offset+limit]}
class Handler(BaseHTTPRequestHandler):
 def send(self,body,status=200,kind='application/json; charset=utf-8'):
  raw=body.encode() if isinstance(body,str) else json.dumps(body,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  url=urlparse(self.path);path=url.path
  try:
   if path=='/':return self.send((ROOT/'web/index.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/source-coverage':return self.send((ROOT/'data/processed/source_coverage.html').read_text(encoding='utf-8'),kind='text/html; charset=utf-8')
   if path=='/api/v1/health':
    _,snapshot=active_folder();return self.send({'status':'ready','snapshot':snapshot,'mode':'local-read-only-snapshots','agency_calls_per_request':0})
   if path=='/api/v1/map':
    import sys
    sys.path.insert(0,str(ROOT/'.dependencies'))
    from pyproj import Transformer
    from shapely.geometry import shape,mapping
    from shapely.ops import transform
    folder,snapshot=active_folder();data={k:read_table(k)[0] for k in ['parcels','streets','neighborhoods','parks','buildings']}
    projection=Transformer.from_crs(4326,32617,always_xy=True)
    def xy(x,y,z=None):return projection.transform(x,y)
    for name in ['parcels','streets','neighborhoods','parks']:
     for f in data[name]['features']:f['geometry']=mapping(transform(xy,shape(f['geometry'])))
    low=projection.transform(-81.398,28.5605);high=projection.transform(-81.379,28.5845)
    return self.send({'snapshot':snapshot,'map_crs':'EPSG:32617','bounds':[low[0],low[1],high[0],high[1]],**data})
   if path.startswith('/api/v1/'):
    name=path.removeprefix('/api/v1/');return self.send(page_table(name,parse_qs(url.query)))
   return self.send({'error':'Not found'},404)
  except FileNotFoundError:return self.send({'error':'Required local snapshot or derived artifact unavailable; build the requested data product'},503)
  except SnapshotMismatch as exc:return self.send({'error':str(exc)},409)
  except KeyError:return self.send({'error':'Unknown table'},404)
  except (ValueError,TypeError):return self.send({'error':'Invalid query'},400)
 def do_POST(self):self.send({'error':'Read-only API'},405)
 def do_PUT(self):self.send({'error':'Read-only API'},405)
 def do_DELETE(self):self.send({'error':'Read-only API'},405)
 def log_message(self,*args):pass
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8768);a=p.parse_args();print('TWIN snapshot API: http://127.0.0.1:'+str(a.port),flush=True);ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
