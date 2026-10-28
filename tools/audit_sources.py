"""Read-only local source audit; output stays private and outside public exports."""
from pathlib import Path
import argparse,csv,json,collections,hashlib,datetime,re
ROOT=Path(__file__).resolve().parents[1]
def profile(path,key):
 if not path.exists():return {'path':str(path),'available':False}
 if path.suffix=='.geojson':
  d=json.loads(path.read_text(encoding='utf-8'));rows=[f['properties'] for f in d['features']];fields=list(rows[0]) if rows else []
 else:
  with path.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);rows=list(r);fields=r.fieldnames
 norm=lambda x:re.sub('[^A-Z0-9]','',str(x or '').upper())
 ids=[norm(r.get(key)) for r in rows];counts=collections.Counter(ids);valid=set(ids)-{''}
 return {'path':str(path),'available':True,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows),'unique_nonblank_ids':len(valid),'blank_ids':sum(not x for x in ids),'duplicate_nonblank_ids':{k:v for k,v in counts.items() if k and v>1},'fields':fields,'null_counts':{k:sum(r.get(k) in [None,''] for r in rows) for k in fields},'release_tiers':dict(collections.Counter(r.get('booms_public_release_tier','not stated') for r in rows)),'ids_for_reconciliation':sorted(valid)}
def audit(base):
 specs={'booms_raw':('data/raw/Local_Program_FL050651.csv','parcel_pin'),'booms_completion':('College_Park_ED_Vault/Data/Operations/booms_completion_tracker.csv','parcel_pin'),'parcel_spine':('data/processed/parcel_spine_clean.csv','parcel_pin'),'parcel_polygons':('College_Park_ED_Vault/Data/Operations/parcel_polygons_ocpa.geojson','PARCEL')}
 profiles={name:profile(base/p,key) for name,(p,key) in specs.items()}
 primary=set(profiles['booms_raw'].get('ids_for_reconciliation',[]));reconciliation={}
 for name,p in profiles.items():
  ids=set(p.pop('ids_for_reconciliation',[]));reconciliation[name]={'ids_missing_from_raw':sorted(ids-primary),'raw_ids_missing_from_this_source':sorted(primary-ids)}
 report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_project_modified':False,'raw_records_copied':False,'profiles':profiles,'reconciliation':reconciliation,'field_mapping':{'parcel_pin':'parcel_id','cp_uid':'program_record_id','street_address':'observed_address','num_floors':'reported_floors_not_measured_height','vacancy_status':'observed_vacancy','last_edit_date':'observation_edit_date','booms_public_release_tier':'release_gate'},'publication_policy':'No BOOMS values enter active map/API/scene until existing source release gates are met; owner/contact/notes excluded from public exports.'}
 out=ROOT/'data/private/source_audit.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2));print(json.dumps({'profiles':{n:{k:v for k,v in p.items() if k in ['rows','unique_nonblank_ids','blank_ids','duplicate_nonblank_ids','release_tiers']} for n,p in profiles.items()},'reconciliation':{n:{k:len(v) for k,v in r.items()} for n,r in reconciliation.items()}},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();audit(a.source_root)
