from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from source_audit_contract import audit,profile,SPECS

class SourceAuditTests(unittest.TestCase):
 def test_private_values_never_written_and_source_unchanged(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);source=root/'read_only_source';out=root/'twin';paths=[]
   for name,(relative,key) in SPECS.items():
    path=source/relative;path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.csv':path.write_text(key+',owner_notes,vacancy_status\nPRIVATEPIN001,SECRET CONTACT,CONFIDENTIAL STATUS\nPRIVATEPIN001,SECRET CONTACT,CONFIDENTIAL STATUS\n')
    else:path.write_text(json.dumps({'type':'FeatureCollection','features':[{'properties':{key:'PRIVATEPIN002','owner_notes':'SECRET CONTACT'},'geometry':None}]}))
    paths.append((path,path.read_bytes()))
   report=audit(source,out);encoded=json.dumps(report)
   for value in ('PRIVATEPIN001','PRIVATEPIN002','SECRET CONTACT','CONFIDENTIAL STATUS'):self.assertNotIn(value,encoded)
   self.assertEqual(report['booms_public_field_allowlist'],[]);self.assertFalse(report['held_2026_data_exported'])
   self.assertEqual(report['profiles']['booms_inventory']['duplicate_nonblank_id_groups'],1)
   self.assertEqual(report['profiles']['parcel_polygon_snapshot']['invalid_polygon_rows'],1)
   for path,before in paths:self.assertEqual(path.read_bytes(),before)
   register=(out/'data/processed/source_audit_register.json').read_text();self.assertNotIn('PRIVATEPIN',register);self.assertNotIn('rows',register)
 def test_missing_sources_do_not_look_empty_and_reconciled(self):
  with tempfile.TemporaryDirectory() as temporary:
   result,ids=profile(Path(temporary)/'missing.csv','parcel_pin');self.assertFalse(result['available']);self.assertEqual(ids,set());self.assertNotIn('rows',result)

if __name__=='__main__':unittest.main()
