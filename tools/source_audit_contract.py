"""Aggregate-only read-only source inventory; never exports private row values."""
from pathlib import Path
import argparse,csv,json,collections,hashlib,datetime,re,sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
SPECS={'booms_inventory':('data/raw/Local_Program_FL050651.csv','parcel_pin'),
 'booms_completion_tracker':('College_Park_ED_Vault/Data/Operations/booms_completion_tracker.csv','parcel_pin'),
 'normalized_parcel_spine':('data/processed/parcel_spine_clean.csv','parcel_pin'),
 'parcel_polygon_snapshot':('College_Park_ED_Vault/Data/Operations/parcel_polygons_ocpa.geojson','PARCEL')}
FIELD_MAP={'parcel_pin':('parcel_id','String identifier; leading zeros retained; exact feature identity separate.'),
 'cp_uid':('program_record_id','BOOMS inventory identity, not appraiser building/tenant identity.'),
 'num_floors':('reported_floors','Program observation; not measured height or automatic building storeys.'),
 'vacancy_status':('observed_vacancy','Dated observation; not current market availability.'),
 'building_use':('observed_building_use','Separate from OCPA tax use and City zoning.'),
 'parcel_use':('observed_parcel_use','Program observation; not a building/storefront entity.'),
 'parcel_in_use_yn':('observed_parcel_use_state','Do not infer vacancy or public access.'),
 'last_edit_date':('observation_edit_date','Not retrieval/acquisition date.'),
 'b_buildings_complete':('buildings_completion_gate','Tracker state; not public acceptance.'),
 'o_owners_complete':('owners_completion_gate','Completion flag only; no owner/contact content allowed.'),
 'm_merchants_complete':('merchants_completion_gate','Completion flag, not current tenant identity.'),
 's_spaces_complete':('spaces_completion_gate','Completion flag, not verified suites.'),
 'overall_complete':('overall_completion_gate','Program completion is separate from release authorization.'),
 'completion_score':('completion_score','Source workflow score, not accuracy/confidence.'),
 'booms_record_status':('record_workflow_status','Source workflow status preserved behind release gates.'),
 'booms_public_release_tier':('release_gate','Preserve source gate; no automatic public eligibility.')}
PUBLIC_ALLOWLIST=['id','parcel_id','source_parcel_id','source_object_id','site_address','property_use_code','zoning_code','stories','stories_quality','year_built','area_acres','source','attribute_quality_flags']

def normalized_id(value):return re.sub('[^A-Z0-9]','',str(value or '').upper())
def fingerprint(path):return hashlib.sha256(path.read_bytes()).hexdigest()
RELEASE_TIERS={'internal_only','staff_validation','public_aggregate','public_record_detail','suppress_from_public'}
REGISTRIES=('College_Park_ED_Vault/Data/Operations/source_refresh_registry.csv','College_Park_ED_Vault/Data/Operations/parcel_polygon_source_registry.csv')
MAPS=('web/public/data/A016_parcels-json.json','web/public/data/ontology_parcels_profiles.json')

def safe_date(value):
 try:
  text=str(value or '').strip()
  if not re.match(r'^\d{4}-\d{2}-\d{2}',text):return None
  result=datetime.date.fromisoformat(text[:10])
  return result.isoformat() if 1900<=result.year<=2100 else None
 except ValueError:return None

def schema_type(value):
 if value is None or value=='':return 'null_or_blank'
 if isinstance(value,bool):return 'boolean'
 if isinstance(value,(int,float)):return 'number'
 if isinstance(value,dict):return 'object'
 if isinstance(value,list):return 'array'
 return 'string'

def profile(path,key):
 if not path.exists():return {'available':False,'source_key':key,'status':'unavailable_not_zero'},set()
 before=fingerprint(path);crs=None;invalid=None;extent=None
 if path.suffix in ('.geojson','.json'):
  document=json.loads(path.read_text(encoding='utf-8-sig'))
  if isinstance(document,list):rows=[r for r in document if isinstance(r,dict)]
  elif document.get('type')=='FeatureCollection':
   rows=[f.get('properties') or {} for f in document.get('features',[])];crs=document.get('crs',{}).get('properties',{}).get('name');invalid=0;bounds=[]
   from shapely.geometry import shape
   for feature in document.get('features',[]):
    try:
     geometry=shape(feature.get('geometry'));good=not geometry.is_empty and geometry.is_valid and geometry.geom_type in ('Polygon','MultiPolygon')
    except (ValueError,TypeError,KeyError,IndexError,AttributeError):good=False
    if not good:invalid+=1
    else:bounds.append(geometry.bounds)
   if bounds:extent=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)]
  else:raise ValueError('Unsupported map structure; no raw payload printed')
  fields=sorted({k for row in rows for k in row})
 else:
  with path.open(encoding='utf-8-sig',newline='') as stream:
   reader=csv.DictReader(stream);fields=reader.fieldnames or [];rows=list(reader)
 ids=[normalized_id(row.get(key)) for row in rows];counts=collections.Counter(ids);valid=set(ids)-{''}
 original_forms=collections.defaultdict(set)
 for row,identifier in zip(rows,ids):
  if identifier:original_forms[identifier].add(str(row.get(key) or ''))
 collisions=sum(len(forms)>1 for forms in original_forms.values())
 dates={}
 for field in fields:
  if any(token in field.lower() for token in ('date','updated','modified')):
   values=[safe_date(row.get(field)) for row in rows];known=[v for v in values if v]
   dates[field]={'valid_date_count':len(known),'unknown_or_unparseable_count':len(values)-len(known),'minimum':min(known) if known else None,'maximum':max(known) if known else None,'meaning':'Source field date only; not retrieval or release.'}
 tiers=collections.Counter(str(row.get('booms_public_release_tier') or '').strip() for row in rows)
 release={tier:tiers[tier] for tier in sorted(RELEASE_TIERS)}
 release['unknown_or_other_count']=sum(n for k,n in tiers.items() if k not in RELEASE_TIERS)
 result={'available':True,'sha256':before,'rows':len(rows),'unique_nonblank_ids':len(valid),'blank_ids':sum(not value for value in ids),
   'normalization_collision_groups':collisions,'identifier_comparison':'Uppercase alphanumeric comparison only; collisions queued, never accepted entity links.','row_accounting_valid':len(rows)==len(valid)+sum(n-1 for identifier,n in counts.items() if identifier)+sum(not value for value in ids),
   'duplicate_nonblank_id_groups':sum(n>1 for identifier,n in counts.items() if identifier),'duplicate_excess_rows':sum(n-1 for identifier,n in counts.items() if identifier),
   'fields':fields,'schema':{name:sorted({schema_type(row.get(name)) for row in rows}) for name in fields},'mapping_fields_present':{name:name in fields for name in FIELD_MAP},'source_key_present':key in fields,
   'null_counts':{name:sum(row.get(name) in (None,'') for row in rows) for name in fields},'invalid_polygon_rows':invalid,
   'coverage_scope':'Local source membership; not assumed identical to current TWIN official study boundaries. No spatial coverage inferred from CSV addresses.','coverage_bounds':extent,'declared_crs':crs,'crs_quality':'explicit_source_declaration' if crs else 'unknown_not_inferred','retrieved_utc':None,'acquisition_date':None,'effective_date':None,
   'local_file_modified_utc':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),
   'source_date_aggregates':dates,'release_tier_counts':release,'release_authorization':'none; source tier is not proof of release approval',
   'freshness_note':'Local mtime is not source observation/retrieval/release date.','license_redistribution':'Unknown; no source records exported.',
   'source_url':None,'source_kind':'local_snapshot_not_live_api','release_posture':'source_gates_preserved_no_public_export'}
 if fingerprint(path)!=before:raise ValueError('Read-only source changed during audit')
 return result,valid

def metadata_registries(base):
 result=[]
 for rel in REGISTRIES:
  path=base/rel
  entry={'source_locator':rel,'available':path.is_file(),'safe_metadata':[]}
  if path.is_file():
   before=fingerprint(path)
   with path.open(encoding='utf-8-sig',newline='') as stream:
    reader=csv.DictReader(stream);entry['fields']=reader.fieldnames or []
    for row in reader:
     url=row.get('source_url') or '';parsed=urlparse(url)
     # Never copy notes, arbitrary URLs, query tokens or identifier-bearing request URLs.
     try:standard_port=parsed.port in (None,443)
     except ValueError:standard_port=False
     if parsed.scheme=='https' and parsed.username is None and parsed.password is None and standard_port and parsed.hostname in ('vgispublic.ocpafl.org','data.cityoforlando.net','www.orlando.gov'):
      entry['safe_metadata'].append({'official_source_url':parsed._replace(query='',fragment='').geturl(),'checked_date':safe_date(row.get('checked_date') or row.get('last_checked')),'downloaded_date':safe_date(row.get('last_downloaded')),'date_scope':'source registry report; not verified acquisition date'})
   entry['sha256']=before
   if fingerprint(path)!=before:raise ValueError('Source metadata changed during audit')
  result.append(entry)
 return result

def exception_queue(profiles,reconciliation):
 queue=[]
 def add(name,reason,count,action):
  if count:queue.append({'queue_id':f'{name}:{reason}','source':name,'reason':reason,'count':count,'scope':'aggregate only; resolve identities inside read-only source project using source-side authorized workflow','next_action':action,'status':'unresolved_source_side','owner_role':'GIS/Data Analyst'})
 for name,p in profiles.items():
  if not p['available']:add(name,'source_unavailable',1,'Restore original local export; do not substitute a zero-row success.');continue
  for reason,field in [('normalization_collision','normalization_collision_groups'),('blank_identity','blank_ids'),('duplicate_identity_groups','duplicate_nonblank_id_groups'),('invalid_geometry','invalid_polygon_rows')]:add(name,reason,p.get(field) or 0,'Inspect corresponding source rows in source project; do not auto-deduplicate, relocate or publish.')
  for reason in ('source_ids_absent_from_inventory_count','inventory_ids_absent_from_source_count'):add(name,reason,reconciliation[name][reason],'Reconcile input grain/vintage and original key; membership differences are not deletions or new physical buildings.')
  add(name,'retrieval_or_license_unknown',1,'Record publisher receipt and redistribution terms before release; do not replace unknown dates with mtime.')
 return queue

def audit(base,root=ROOT):
 base=Path(base).resolve();root=Path(root).resolve();profiles={};ids={}
 for name,(relative,key) in SPECS.items():
  path=(base/relative).resolve()
  if not path.is_relative_to(base):raise ValueError('Source path escapes read-only project')
  result,identifiers=profile(path,key);result['source_locator']=relative;profiles[name]=result;ids[name]=identifiers
 primary=ids['booms_inventory'];reconciliation={}
 for name,identifiers in ids.items():
  reconciliation[name]={'source_ids_absent_from_inventory_count':len(identifiers-primary),'inventory_ids_absent_from_source_count':len(primary-identifiers),
   'shared_id_count':len(primary&identifiers),'details':'Review exceptions inside source project; no private identifier queue exported.'}
 for name in reconciliation:
  if not profiles[name]['available'] or not profiles['booms_inventory']['available']:
   reconciliation[name]={key:None for key in ('source_ids_absent_from_inventory_count','inventory_ids_absent_from_source_count','shared_id_count')};reconciliation[name]['details']='Unavailable input; reconciliation unknown, not zero.'
 refresh={}
 for name in ('refresh_ocpa_parcels.py','fetch_ocpa_parcel_polygons.py','build_booms_completion_tracker.py','run_weekly_source_refresh.py','check_release_gate.py'):
  path=base/'scripts'/name;refresh[name]={'available':path.is_file(),'sha256':fingerprint(path) if path.is_file() else None,'executed':False,'reuse_posture':'Bounded query/cache pattern reused in TWIN data_pipeline only; never run source-writing generators. Owner-related fields omitted. Polygon layer1 and parcel layer4 are distinct; tracker outputs staff_validation, not public acceptance.'}
 maps=[]
 for relative in MAPS:
  key='parcel_pin';result,identifiers=profile(base/relative,key);name=Path(relative).stem;result['source_locator']=relative;result['reuse_status']='Metadata/aggregate inspection only; payload never imported; owner/business/nested records blocked.';profiles[name]=result;ids[name]=identifiers
  reconciliation[name]={'source_ids_absent_from_inventory_count':len(identifiers-primary),'inventory_ids_absent_from_source_count':len(primary-identifiers),'shared_id_count':len(primary&identifiers),'details':'Source-side review only; no private IDs exported.'};maps.append({'source_locator':relative,'available':result['available'],'sha256':result.get('sha256'),'profile_ref':name})
 for name,p in profiles.items():
  if not p['available'] or not profiles['booms_inventory']['available']:
   reconciliation[name]={key:None for key in ('source_ids_absent_from_inventory_count','inventory_ids_absent_from_source_count','shared_id_count')};reconciliation[name]['details']='Unavailable input; reconciliation unknown, not zero.'
 report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_project_modified':False,'private_row_values_exported':False,
  'held_2026_data_exported':False,'booms_api_available':'not_established_local_export_only','profiles':profiles,'reconciliation_counts':reconciliation,
  'field_mapping':{key:{'target':value[0],'meaning':value[1]} for key,value in FIELD_MAP.items()},'official_public_field_allowlist':PUBLIC_ALLOWLIST,'booms_public_field_allowlist':[],
  'source_policy_receipts':{rel:fingerprint(base/rel) for rel in ('AGENTS.md','PROJECT_OPERATING_SYSTEM.md') if (base/rel).is_file()},'release_tier_vocabulary':sorted(RELEASE_TIERS),'source_refresh_logic_inventory':refresh,'map_output_metadata_inventory':maps,'metadata_registry_inventory':metadata_registries(base),
  'exception_queue':exception_queue(profiles,reconciliation),'freshness_report':{name:{key:p.get(key) for key in ('available','source_date_aggregates','retrieved_utc','local_file_modified_utc','freshness_note')} for name,p in profiles.items()},
  'reconciliation_method':'Normalized string identity sets, duplicate groups and excess-row arithmetic. Membership is not accepted physical identity; records with missing sources remain unavailable.',
  'governance':'BTR source remains read-only. Held2026 reconciliation/release-tier/BOOMS/source-registry/QA gates remain in force. Inventory, tracker and current OCPA snapshots are separate.',
  'unresolved':['Original acquisition/retrieval dates and redistribution approval remain unknown where absent from source receipts.','Exception identities and staff release acceptance stay in source project; aggregate audit authorizes no release.','Map schemas/counts/key membership are audited; nested owner/business payloads are excluded and no live BOOMS API is assumed.']}
 out=root/'data/private/source_audit_summary.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
 # Public-side register includes no private source counts, IDs or observations.
 entries=[];pointer=root/'data/processed/active.json'
 if pointer.is_file():
  active=json.loads(pointer.read_text());sources=json.loads((root/active['relative_path']/'sources.json').read_text())
  for source in sources:
   entries.append({key:source.get(key) for key in ('id','publisher','api_url','metadata_url','retrieved_utc','source_updated','snapshot_built_utc','retrieval_quality','geometry_crs','scope','license_note','fields_requested')})
 register={'generated_utc':report['created_utc'],'official_sources':entries,'first_class_catalogs':['https://data.cityoforlando.net/','https://www.orlando.gov/Our-Government/Records-and-Documents/Map-Library/GIS-Data-Download'],
  'private_source_posture':'Metadata mapping only; private counts/values and held snapshots absent from public register. BOOMS is a local export, tracker separate; API not established.',
  'booms_field_mapping':report['field_mapping'],'public_parcel_allowlist':PUBLIC_ALLOWLIST,'booms_public_field_allowlist':[]}
 target=root/'data/processed/source_audit_register.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(register,indent=2),encoding='utf-8')
 print(json.dumps({'local_aggregate_report':str(out),'public_metadata_register':str(target),'source_project_modified':False,'private_row_values_exported':False,'held_2026_data_exported':False,'available_sources':sum(p['available'] for p in profiles.values())},indent=2));return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args();audit(args.source_root)
