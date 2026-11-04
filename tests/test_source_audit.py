from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from source_audit_contract import audit,profile,SPECS,MAPS,REGISTRIES

class SourceAuditTests(unittest.TestCase):
 def test_private_values_never_written_and_source_unchanged(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'read_only_source';out=root/'twin';paths=[]
   for name,(relative,key) in SPECS.items():
    path=source/relative;path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.csv':path.write_text(key+',owner_notes,vacancy_status\nPRIVATEPIN001,SECRET CONTACT,CONFIDENTIAL STATUS\nPRIVATEPIN001,SECRET CONTACT,CONFIDENTIAL STATUS\n')
    else:path.write_text(json.dumps({'type':'FeatureCollection','features':[{'properties':{key:'PRIVATEPIN002','owner_notes':'SECRET CONTACT'},'geometry':None}]}))
    paths.append((path,path.read_bytes()))
   for relative in MAPS:
    path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps([{'parcel_pin':'PRIVATEPIN001','nested':{'owner_notes':'NESTED PRIVATE OWNER','contact':'NESTED PRIVATE CONTACT'},'items':['NESTED PRIVATE LIST']}]),encoding='utf-8');paths.append((path,path.read_bytes()))
   path=source/REGISTRIES[0];path.parent.mkdir(parents=True,exist_ok=True);path.write_text('source_url,last_checked\nhttps://SECRETUSER:SECRETPASSWORD@data.cityoforlando.net/resource/test?token=QUERYSECRET,2025-01-01\nhttps://data.cityoforlando.net:8443/resource/PORTSECRET,2025-01-01\nhttps://data.cityoforlando.net/resource/safe?token=QUERYSECRET#FRAGMENTSECRET,2025-01-01\n',encoding='utf-8');paths.append((path,path.read_bytes()))
   report=audit(source,out);encoded=json.dumps(report)
   for relative in MAPS:
    m=report['profiles'][Path(relative).stem];self.assertEqual(m['rows'],1);self.assertEqual(m['schema']['nested'],['object']);self.assertEqual(m['schema']['items'],['array'])
   metadata=report['metadata_registry_inventory'][0]['safe_metadata'];self.assertEqual(len(metadata),1);self.assertEqual(metadata[0]['official_source_url'],'https://data.cityoforlando.net/resource/safe')
   for value in ('PRIVATEPIN001','PRIVATEPIN002','SECRET CONTACT','CONFIDENTIAL STATUS','NESTED PRIVATE OWNER','NESTED PRIVATE CONTACT','NESTED PRIVATE LIST','SECRETUSER','SECRETPASSWORD','QUERYSECRET','FRAGMENTSECRET','PORTSECRET'):self.assertNotIn(value,encoded)
   self.assertEqual(report['booms_public_field_allowlist'],[]);self.assertFalse(report['held_2026_data_exported'])
   self.assertEqual(report['profiles']['booms_inventory']['duplicate_nonblank_id_groups'],1)
   self.assertEqual(report['profiles']['parcel_polygon_snapshot']['invalid_polygon_rows'],1)
   for path,before in paths:self.assertEqual(path.read_bytes(),before)
   register=(out/'data/processed/source_audit_register.json').read_text();self.assertNotIn('PRIVATEPIN',register);self.assertNotIn('rows',register)
 def test_missing_sources_do_not_look_empty_and_reconciled(self):
  with tempfile.TemporaryDirectory() as temporary:
   result,ids=profile(Path(temporary)/'missing.csv','parcel_pin');self.assertFalse(result['available']);self.assertEqual(ids,set());self.assertNotIn('rows',result)
   path=Path(temporary)/'example.csv';path.write_text('parcel_pin,last_edit_date,booms_public_release_tier\nAB-01,2025-01-02,staff_validation\nAB01,NOT_A_DATE,PRIVATE_SECRET_TIER\n',encoding='utf-8')
   result,ids=profile(path,'parcel_pin');self.assertEqual(result['normalization_collision_groups'],1);self.assertTrue(result['row_accounting_valid']);self.assertEqual(result['source_date_aggregates']['last_edit_date']['valid_date_count'],1);self.assertEqual(result['release_tier_counts']['unknown_or_other_count'],1);self.assertNotIn('PRIVATE_SECRET_TIER',json.dumps(result))

if __name__=='__main__':unittest.main()
