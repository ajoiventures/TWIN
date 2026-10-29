"""Full official neighborhood park reference inventory; no active scene writes."""
from pathlib import Path
import sys,json,hashlib,datetime,html,shutil,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import Client,SOURCES,arcgis,atomic_json,now
from shapely.geometry import shape,mapping
from shapely.ops import transform
from pyproj import Transformer
OUT='data/land/full_neighborhood_parks'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build(root=ROOT,offline=False):
 root=Path(root).resolve();out=root/OUT;out.mkdir(parents=True,exist_ok=True)
 receipt=out/'receipt.json'
 if not receipt.exists() and any((out/name).exists() for name in ('inventory.json','inventory.geojson','coverage.svg')):raise ValueError('Unreceipted park outputs require recovery; preserve them')
 if receipt.exists():
  for name,digest in read(receipt)['artifacts'].items():
   if Path(name).name!=name or sha(out/name)!=digest:raise ValueError('Preserve modified park inventory output: '+name)
 boundary_path=root/'data/processed/study_boundaries.geojson';active_path=root/'data/processed/active.json';active=read(active_path)
 old_path=(root/active['relative_path']/'parks.json').resolve()
 if not old_path.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid active snapshot path')
 dependencies={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in [boundary_path,active_path,old_path,root/'tools/data_pipeline.py',root/'tools/inventory_neighborhood_parks.py']}
 scopes={f['properties']['scope']:shape(f['geometry']) for f in read(boundary_path)['features']}
 client=Client(root/'data/cache/full_neighborhood_parks',offline=offline)
 raw,metadata=arcgis(client,SOURCES['parks'],bbox=scopes['neighborhood'].bounds)
 original_ids={str(f['properties']['OBJECTID']) for f in read(old_path)['features']}
 project=Transformer.from_crs(4326,32617,always_xy=True).transform
 rows=[];features=[];excluded=[]
 for f in raw['features']:
  p=f['properties'];g=shape(f['geometry'])
  if not g.is_valid or g.is_empty:raise ValueError('Invalid source park geometry; review required')
  clipped=g.intersection(scopes['neighborhood']);area=transform(project,clipped).area
  if area<=0:
   excluded.append({'source_object_id':str(p['OBJECTID']),'name':p.get('NAME'),'reason':'Envelope candidate has no area in official neighborhood'});continue
  row={'id':'orlando-park:'+str(p['OBJECTID']),'source_object_id':str(p['OBJECTID']),'name':p.get('NAME'),'address':p.get('ADDRESS'),'type':p.get('TYPE'),'class':p.get('CLASS'),
       'neighborhood_intersection_m2':area,'main_street_intersection_m2':transform(project,g.intersection(scopes['main_street'])).area,
       'in_prior_extract':str(p['OBJECTID']) in original_ids,'legal_ownership':None,'public_access_verified':False,'opening_hours':None,'amenities_verified':False,
       'source_url':SOURCES['parks']['url'],'quality':'Official park reference footprint; ownership/access/amenities not inferred'}
  rows.append(row);features.append({'type':'Feature','id':row['id'],'properties':row,'geometry':mapping(clipped)})
 report={'schema':'twin.full-neighborhood-parks/1','built_utc':now(),'comparison_snapshot':active['snapshot'],'publisher':SOURCES['parks']['publisher'],'source_url':SOURCES['parks']['url'],
   'source_item_id':metadata.get('serviceItemId'),'acquisition_date':None,'effective_date':None,'source_last_edit_unix_ms':metadata.get('editingInfo',{}).get('lastEditDate'),
   'source_copyright':metadata.get('copyrightText'),'reuse_conditions':'Public API access observed; explicit redistribution terms not inferred from access',
   'source_geometry_crs':metadata.get('extent',{}).get('spatialReference'),'output_crs':'EPSG:4326','area_crs':'EPSG:32617 metres','vertical_datum':'Not applicable to 2D reference footprints',
   'field_dictionary':{'id':'Publisher-prefixed original object ID for this service version','source_object_id':'Original ID preserved as string','name/address/type/class':'Unmodified safe City fields; nulls retained','neighborhood_intersection_m2':'Planar clipped reference area, not surveyed legal park area','main_street_intersection_m2':'Separate intersection with official Main Street polygon','in_prior_extract':'Original ID occurs in prior frozen parks table; not proof that its geometry is unchanged','legal_ownership/opening_hours':'Unknown in this bounded inventory','public_access_verified/amenities_verified':'False; not established by park category'},
   'source_fields':metadata['fields'],'requests':client.accesses,'counts':{'envelope_candidates':len(raw['features']),'neighborhood_park_features':len(rows),'main_street_park_features':sum(r['main_street_intersection_m2']>0 for r in rows),'outside_neighborhood_candidates':len(excluded),'new_to_prior_extract':sum(not r['in_prior_extract'] for r in rows)},
   'rows':rows,'first_five_safe_rows':rows[:5],'excluded':excluded,'boundary_sources':[f['properties'] for f in read(boundary_path)['features']],
   'dependencies':dependencies,'active_snapshot_changed':False,'scene_changed':False,
   'limitations':['Complete response for this City service and official polygon, not a census of all private, County, school or publicly accessible open space.',
    'New park coverage does not expand 3D ground or establish legal ownership, vacancy, available development land, access, hours or amenities.',
    'Source edit dates are not acquisition or legal effective dates; park and boundary geometries are reference information.']}
 for request in client.accesses:
  name=hashlib.sha256(request['url'].encode()).hexdigest()+'.json';path=root/'data/cache/full_neighborhood_parks'/name;dependencies[str(path.relative_to(root)).replace('\\','/')]=sha(path)
 if any(sha(root/name)!=digest for name,digest in dependencies.items()):raise ValueError('Park source changed while preparing inventory')
 xmin,ymin,xmax,ymax=transform(project,scopes['neighborhood']).bounds;scale=min(850/(xmax-xmin),850/(ymax-ymin))
 def svg_shape(g,color,label):
  parts=[]
  for poly in getattr(g,'geoms',[g]):
   rings=[poly.exterior,*poly.interiors];d=' '.join('M '+' L '.join(f'{(x-xmin)*scale+15:.2f},{(ymax-y)*scale+15:.2f}' for x,y in ring.coords)+' Z' for ring in rings)
   parts.append('<path d="'+d+'" fill="'+color+'" fill-rule="evenodd" stroke="#224d41" stroke-width="1"><title>'+html.escape(label)+'</title></path>')
  return ''.join(parts)
 svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 930"><rect width="900" height="930" fill="#f5f7f1"/><text x="15" y="905" font-size="15">College Park: City park reference footprints across the full official neighborhood</text>'+svg_shape(transform(project,scopes['neighborhood']),'#e1e7dd','Official neighborhood')
 for f in features:svg+=svg_shape(transform(project,shape(f['geometry'])),'#2f9365' if f['properties']['in_prior_extract'] else '#d88b37',f['properties']['name'] or f['id'])
 svg+='<text x="15" y="925" font-size="13">Green: present in prior extract; orange: additional source records. Not an ownership or access map.</text></svg>'
 payloads={'inventory.json':json.dumps(report,indent=2).encode(),'inventory.geojson':json.dumps({'type':'FeatureCollection','features':features},indent=2).encode(),'coverage.svg':svg.encode()}
 if receipt.exists():
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for name in [*read(receipt)['artifacts'],'receipt.json']:shutil.copy2(out/name,backup/name)
 for name,raw_bytes in payloads.items():
  temp=out/(name+'.tmp');temp.write_bytes(raw_bytes);temp.replace(out/name)
 atomic_json(receipt,{'artifacts':{name:sha(out/name) for name in payloads}})
 return report

def validate(root=ROOT):
 root=Path(root).resolve();out=root/OUT;receipt=read(out/'receipt.json')
 if set(receipt.get('artifacts',{}))!={'inventory.json','inventory.geojson','coverage.svg'}:raise ValueError('Incomplete park inventory receipt')
 for name,digest in receipt['artifacts'].items():
  if sha(out/name)!=digest:raise ValueError('Park inventory output changed')
 report=read(out/'inventory.json')
 if not report.get('dependencies'):raise ValueError('Park source dependencies missing')
 for name,digest in report['dependencies'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or sha(path)!=digest:raise ValueError('Park inventory source is stale')
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args();print(json.dumps(build(offline=args.offline)['counts']))
