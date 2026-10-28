"""Aggregate-only read-only source inventory; never exports private row values."""
from pathlib import Path
import argparse,csv,json,collections,hashlib,datetime,re,sys
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
def profile(path,key):
 if not path.exists():return {'available':False,'source_key':key},set()
 before=fingerprint(path);crs=None;invalid=None;extent=None
 if path.suffix=='.geojson':
  from shapely.geometry import shape
  document=json.loads(path.read_text(encoding='utf-8'));rows=[f.get('properties') or {} for f in document.get('features',[])];fields=sorted({k for row in rows for k in row});crs=document.get('crs',{}).get('properties',{}).get('name');invalid=0;bounds=[]
  for feature in document.get('features',[]):
   try:
    geometry=shape(feature.get('geometry'));good=not geometry.is_empty and geometry.is_valid and geometry.geom_type in ('Polygon','MultiPolygon')
   except (ValueError,TypeError,KeyError,IndexError,AttributeError):good=False
   if not good:invalid+=1
   else:bounds.append(geometry.bounds)
  if bounds:extent=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)]
 else:
  with path.open(encoding='utf-8-sig',newline='') as stream:
   reader=csv.DictReader(stream);fields=reader.fieldnames or [];rows=list(reader)
 ids=[normalized_id(row.get(key)) for row in rows];counts=collections.Counter(ids);valid=set(ids)-{''}
 # IDs exist transiently in memory for reconciliation, never in any report.
 result={'available':True,'sha256':before,'rows':len(rows),'unique_nonblank_ids':len(valid),'blank_ids':sum(not value for value in ids),
   'duplicate_nonblank_id_groups':sum(n>1 for identifier,n in counts.items() if identifier),'duplicate_excess_rows':sum(n-1 for identifier,n in counts.items() if identifier),
   'fields':fields,'mapping_fields_present':{name:name in fields for name in FIELD_MAP},'source_key_present':key in fields,
   'null_counts':{name:sum(row.get(name) in (None,'') for row in rows) for name in fields},'invalid_polygon_rows':invalid,
   'coverage_bounds':extent,'declared_crs':crs,'retrieved_utc':None,'local_file_modified_utc':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),
   'freshness_note':'Local mtime is not source observation/retrieval/release date.','license_redistribution':'Unknown; no source records exported.',
   'source_url':None,'source_kind':'local_snapshot_not_live_api','release_posture':'source_gates_preserved_no_public_export'}
 if fingerprint(path)!=before:raise ValueError('Read-only source changed during audit')
 return result,valid

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
 refresh={}
 for name in ('refresh_ocpa_parcels.py','fetch_ocpa_parcel_polygons.py','build_booms_completion_tracker.py','run_weekly_source_refresh.py','check_release_gate.py'):
  refresh[name]={'available':(base/'scripts'/name).is_file(),'executed':False,'reuse_posture':'Review interface; do not run source-writing generators from TWIN audit.'}
 maps=[]
 for relative in ('web/public/data/A016_parcels-json.json','web/public/data/ontology_parcels_profiles.json'):
  path=base/relative;maps.append({'source_locator':relative,'available':path.is_file(),'sha256':fingerprint(path) if path.is_file() else None,'reuse_status':'Source-side generated map output; no payload imported; release eligibility not inferred.'})
 report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_project_modified':False,'private_row_values_exported':False,
  'held_2026_data_exported':False,'booms_api_available':'not_established_local_export_only','profiles':profiles,'reconciliation_counts':reconciliation,
  'field_mapping':{key:{'target':value[0],'meaning':value[1]} for key,value in FIELD_MAP.items()},'official_public_field_allowlist':PUBLIC_ALLOWLIST,'booms_public_field_allowlist':[],
  'source_refresh_logic_inventory':refresh,'map_output_metadata_inventory':maps,
  'governance':'BTR source remains read-only. Held2026 reconciliation/release-tier/BOOMS/source-registry/QA gates remain in force. Inventory, tracker and current OCPA snapshots are separate.',
  'unresolved':['Observation/retrieval dates, license and release eligibility unknown unless explicitly documented.','Exception identities and staff acceptance stay in source project; aggregate audit authorizes no release.','Map payload/source revision reconciliation needs source-side review; no live BOOMS API assumed.']}
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
