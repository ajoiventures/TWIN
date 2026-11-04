"""Cached projected OCPA footprint layer, preserving source-group identities.

Run with the existing Python runtime from TWIN: python tools/build_map_footprints.py.
Writes immutable local GeoJSON plus a guarded processed pointer/receipt only.
No source snapshots, 3D geometry, selection, network or agency requests change.
read_packet(root) serves verified cached EPSG:32617 geometry for the linked map.
Source subareas are not necessarily separate physical buildings or wall surveys.
"""
from pathlib import Path
import argparse,hashlib,json,os,sys,collections
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pyproj import Transformer
from shapely.geometry import shape,mapping
from shapely import transform
from shapely.ops import unary_union
from build_building_lineage import validate as validate_lineage

POINTER='data/processed/map_building_footprints.json'
FIELDS={
 'entity_id':'Existing registry source-membership identity; null for unrepresented source groups.',
 'local_building_id':'Existing source-model alias, not a parcel number or physical-building count.',
 'source_object_ids':'Exact original OCPA OBJECTID strings contributing to this geometry.',
 'source_building_key':'Original PID and BLDG_NUM source group; not accepted physical/tax identity.',
 'source_building_number':'Original BLDG_NUM string, preserving leading zeroes.',
 'source_parcel_id':'Original OCPA footprint PID string, preserved separately from assigned context.',
 'source_subarea_count':'Number of original OBJECTID members in this feature; not physical buildings.',
 'usd_path':'Existing registry source-group path, or null for unrepresented raw subareas.',
 'assigned_parcel_id':'Existing assigned parcel-number context; does not establish an accepted link.',
 'assigned_parcel_feature_id':'Existing assigned active parcel-feature context; may be unaccepted.',
 'candidate_parcel_features':'Distinct active parcel FEATURE contexts; duplicate parcel-number geometries retained.',
 'parcel_link_accepted':'Existing registry acceptance flag only; this layer accepts no new association.',
 'join_state':'Verified lineage relationship state; accepted, spatial review, ambiguous or unmatched.',
 'membership_status':'Registry members or unrepresented raw-subarea review; neither certifies current form.',
 'source_floor_values':'Original subarea FLOOR_NUM values; not inferred building storey counts.',
 'source_acquisition_date':'Null: footprint observation/acquisition date not established.',
 'source_effective_date':'Null: footprint effective date not established.',
 'current_conditions_verified':'Always false; downloading/publishing does not verify current conditions.',
 'physical_building_count':'Null: source subarea/group membership does not establish physical building count.',
 'projected_area_m2':'Union area in EPSG:32617 meters; not surveyed floor or site area.',
 'geometry_scope':'Original OCPA subarea union, not current 3D reconstruction or surveyed wall lines.',
 'geometry':'Union of original member polygons in absolute EPSG:32617 meters; no simplification or imagery.'}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def local(root,path):
 p=(root/path).resolve()
 if not p.is_relative_to(root):raise ValueError('Footprint path leaves project')
 return p

def derive(raw,registry,lineage,parcels=()):
 """Pure derivation: every raw ID has exactly one represented/review disposition."""
 indexed={str(f['properties']['OBJECTID']):f for f in raw['features']}
 if len(indexed)!=len(raw['features']):raise ValueError('Duplicate raw footprint OBJECTID')
 rows={r['id']:r for r in lineage};groups=[];used=set();entities=set();projection=Transformer.from_crs(4326,32617,always_xy=True)
 for record in registry:
  alias=record['local_building_id'];entity=record['entity_id'];ids=sorted(map(str,record['source_feature_ids']))
  if entity in entities or len(ids)!=len(set(ids)):raise ValueError('Duplicate registry identity or member')
  entities.add(entity);row=rows.get(alias)
  if not row or row['entity_id']!=entity or set(row['source_object_ids'])!=set(ids):raise ValueError('Registry/lineage membership differs')
  if any(i not in indexed or i in used for i in ids):raise ValueError('Missing or multiply assigned raw footprint')
  used.update(ids);groups.append((entity,ids,record,row))
 unrepresented=collections.defaultdict(list)
 for id,f in indexed.items():
  if id not in used:
   p=f['properties'];unrepresented['ocpa-building:'+str(p['PID'])+':'+str(p['BLDG_NUM'])].append(id)
 for key,ids in sorted(unrepresented.items()):groups.append(('ocpa:unrepresented-footprint:'+hashlib.sha256(key.encode()).hexdigest()[:24],sorted(ids),None,None))
 parcel_context=collections.defaultdict(list)
 for f in parcels:
  parcel_context[str(f['properties']['parcel_id'])].append({'parcel_feature_id':str(f.get('id') or f['properties']['id']),'parcel_id':str(f['properties']['parcel_id']),'relationship':'original_source_PID_context_only','geometry_link_accepted':False})
 features=[]
 for id,ids,record,row in groups:
  source=[indexed[i] for i in ids];keys={'ocpa-building:'+str(f['properties']['PID'])+':'+str(f['properties']['BLDG_NUM']) for f in source}
  if len(keys)!=1 or (row and row['source_building_key'] not in keys):raise ValueError('Mixed original source PID/building-number membership')
  shapes=[shape(f['geometry']) for f in source]
  if any(g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon') for g in shapes):raise ValueError('Invalid source footprint geometry; repair review required')
  projected=[transform(g,projection.transform,interleaved=False) for g in shapes];geometry=unary_union(projected)
  p=source[0]['properties'];properties={'entity_id':record['entity_id'] if record else None,'local_building_id':record['local_building_id'] if record else None,
   'source_building_key':next(iter(keys)),'source_parcel_id':str(p['PID']),'source_building_number':str(p['BLDG_NUM']),
   'source_object_ids':ids,'source_subarea_count':len(ids),'source_floor_values':sorted({str(f['properties']['FLOOR_NUM']) if f['properties'].get('FLOOR_NUM') is not None else None for f in source},key=lambda x:str(x)),
   'membership_status':'registry_members' if record else 'unrepresented_raw_subareas_review','usd_path':record['usd_path'] if record else None,
   'assigned_parcel_id':record.get('parcel_id') if record else None,'assigned_parcel_feature_id':record.get('parcel_feature_id') if record else None,
   'parcel_link_accepted':record.get('parcel_link_accepted') is True if record else False,'join_state':row['join_state'] if row else 'unrepresented_source_review',
   'candidate_parcel_features':row.get('candidate_parcel_features',[]) if row else parcel_context[str(p['PID'])],'source_acquisition_date':None,'source_effective_date':None,
   'current_conditions_verified':False,'physical_building_count':None,'projected_area_m2':geometry.area,
   'geometry_scope':'original_OCPA_subarea_union_not_surveyed_wallline_or_current_3D_reconstruction'}
  features.append({'type':'Feature','id':id,'geometry':mapping(geometry),'properties':properties})
 return features,{'raw_subareas':len(indexed),'represented_source_groups':len(registry),'unrepresented_source_review_groups':len(unrepresented),'unrepresented_raw_subareas':sum(map(len,unrepresented.values())),'output_features':len(features),'all_raw_ids_assigned_once':sum(f['properties']['source_subarea_count'] for f in features)==len(indexed)}

def previous(root):
 p=root/POINTER;receipt=Path(str(p)+'.receipt')
 if p.exists()!=receipt.exists():raise ValueError('Incomplete map footprint publication; preserve for review')
 if not p.exists():return None
 if read(receipt).get('sha256')!=sha(p):raise ValueError('Map footprint pointer was modified; preserve for review')
 return sha(p)

def build(root=ROOT):
 root=Path(root).resolve();expected=previous(root);active=read(root/'data/processed/active.json');folder=local(root,active['relative_path'])
 lineage=validate_lineage(root);pointer=read(root/'data/processed/building_lineage.json')
 paths=['data/processed/active.json','data/buildings.geojson','data/processed/asset_registry.json','data/processed/building_lineage.json',pointer['packet_path'],(folder/'parcels.json').relative_to(root).as_posix()]
 deps={p:sha(root/p) for p in paths};features,counts=derive(read(root/'data/buildings.geojson'),read(root/'data/processed/asset_registry.json')['records'],lineage['records'],read(folder/'parcels.json')['features'])
 packet={'type':'FeatureCollection','schema':'twin.map-building-footprints/1','snapshot':active['snapshot'],'source_snapshot':active['snapshot'],'map_crs':'EPSG:32617',
  'publisher':'Orange County Property Appraiser','source_url':'https://vgispublic.ocpafl.org/server/rest/services','source_acquisition_date':None,'source_effective_date':None,
  'geometry_scope':'full_cached_raw_extraction; source subareas grouped by exact registry membership, review-only orphan groups separate',
  'current_conditions_verified':False,'new_parcel_links_accepted':False,'dependencies':deps,'producer_sha256':sha(Path(__file__)),'field_dictionary':FIELDS,'counts':counts,
  'identity_closure':{'lineage_packet_path':pointer['packet_path'],'lineage_packet_sha256':pointer['packet_sha256'],'fingerprints':lineage['fingerprints']},
  'limitations':['Source footprint/subarea unions are not surveyed wall lines, physical-building counts or current modeled roof geometry.','Original source parcel IDs and assigned/candidate parcel FEATURE contexts remain separate; no new tax links accepted.','Footprint observation/effective dates unknown; active snapshot timestamp is not acquisition date.','No imagery included; full neighborhood/Main Street coverage and external basemap registration remain separate.'],'features':features}
 content=canonical(packet);digest=hashlib.sha256(content).hexdigest();relative='data/derived/map-footprints/'+digest+'.geojson';target=root/relative
 if any(sha(root/p)!=v for p,v in deps.items()) or previous(root)!=expected:raise ValueError('Footprint source/pointer changed during derivation')
 if target.exists() and target.read_bytes()!=content:raise ValueError('Immutable footprint content-address conflict')
 target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():
  pending=target.with_suffix('.pending');pending.write_bytes(content);os.replace(pending,target)
 manifest={'schema':'twin.map-footprint-pointer/1','source_snapshot':active['snapshot'],'packet_path':relative,'packet_sha256':digest}
 p=root/POINTER;pending=Path(str(p)+'.pending');pending.write_bytes(canonical(manifest));os.replace(pending,p)
 proof=Path(str(p)+'.receipt');pending=Path(str(proof)+'.pending');pending.write_bytes(canonical({'sha256':sha(p),'source_snapshot':active['snapshot']}));os.replace(pending,proof)
 return {'packet_path':relative,'packet_sha256':digest,'counts':counts}

def read_packet(root=ROOT):
 root=Path(root).resolve()
 if not previous(root):raise ValueError('Map building footprints not built')
 pointer=read(root/POINTER);path=local(root,pointer['packet_path'])
 if pointer.get('schema')!='twin.map-footprint-pointer/1' or path.name!=pointer.get('packet_sha256','')+'.geojson' or sha(path)!=pointer['packet_sha256']:raise ValueError('Map footprint packet identity/hash changed')
 packet=read(path);active=read(root/'data/processed/active.json');snapshot=active['snapshot']
 if packet.get('type')!='FeatureCollection' or packet.get('schema')!='twin.map-building-footprints/1' or packet.get('snapshot')!=snapshot or packet.get('source_snapshot')!=snapshot or pointer.get('source_snapshot')!=snapshot or packet.get('map_crs')!='EPSG:32617':raise ValueError('Map footprint snapshot/coordinate frame stale')
 lineage=read(root/'data/processed/building_lineage.json');folder=local(root,active['relative_path'])
 verified_lineage=validate_lineage(root)
 if packet.get('identity_closure')!={'lineage_packet_path':lineage['packet_path'],'lineage_packet_sha256':lineage['packet_sha256'],'fingerprints':verified_lineage['fingerprints']}:raise ValueError('Map footprint transitive source identity changed')
 required={'data/processed/active.json','data/buildings.geojson','data/processed/asset_registry.json','data/processed/building_lineage.json',lineage['packet_path'],(folder/'parcels.json').relative_to(root).as_posix()}
 if set(packet.get('dependencies',{}))!=required or packet.get('field_dictionary')!=FIELDS or packet.get('current_conditions_verified') is not False or packet.get('new_parcel_links_accepted') is not False:raise ValueError('Map footprint source/field/policy contract changed')
 if not packet.get('dependencies') or any(sha(local(root,p))!=v for p,v in packet['dependencies'].items()):raise ValueError('Map footprint source dependencies changed; rebuild')
 if any(set(f['properties'])!=set(FIELDS)-{'geometry'} for f in packet.get('features',[])):raise ValueError('Map footprint property dictionary incomplete')
 return packet

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--validate',action='store_true');args=parser.parse_args()
 result=read_packet() if args.validate else build();print(json.dumps({k:v for k,v in result.items() if k!='features'},indent=2))
