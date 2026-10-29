from pathlib import Path
import copy,json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_building_lineage as m

class LineageTests(unittest.TestCase):
 def fixture(self):
  old={'id':'B1','usd_path':'/World/Buildings/B1','source_parcel_id':'0001','parcel_feature_id':None,'match_method':'ambiguous_or_unmatched','stories':None,'height_m':4.2}
  new={**old,'source_building_key':'ocpa-building:0001:01','source_building_number':'01','source_object_ids':['002','001'],'candidate_parcel_features':[{'parcel_feature_id':'ocpa:01','parcel_id':'0001','overlap_ratio':.9},{'parcel_feature_id':'ocpa:02','parcel_id':'0001','overlap_ratio':.9}],'match_confidence_basis':'overlap fraction, not probability','join_state':'ambiguous'}
  return old,new
 def test_all_old_fields_and_stable_membership(self):
  old,new=self.fixture();record=m.reconcile([old],[new])[0]
  self.assertEqual(len(record['candidate_parcel_features']),2);self.assertEqual(record['join_state'],'ambiguous')
  reversed_row={**new,'source_object_ids':['001','002']};self.assertEqual(m.reconcile([old],[reversed_row])[0]['entity_id'],record['entity_id'])
  for field in ('stories','height_m'):
   changed=copy.deepcopy(new);changed[field]=100
   with self.assertRaises(ValueError):m.reconcile([old],[changed])
  registry={'records':[{'local_building_id':'B1','entity_id':record['entity_id'],'source_feature_ids':['001','002']}]}
  raw={'features':[{'properties':{'OBJECTID':i,'PID':'0001','BLDG_NUM':'01'}} for i in ('001','002','003')]}
  result=m.verify_membership([record],raw,registry);self.assertEqual(result['orphan_subareas'],1);self.assertEqual(result['orphan_source_groups'],1)
  registry['records'][0]['source_feature_ids']=['001']
  with self.assertRaises(ValueError):m.verify_membership([record],raw,registry)
 def test_immutable_publication_and_manual_guard(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);report={'source_snapshot':'snap','records':[]}
   m.publish(root,report);first=(root/m.OUTPUT).read_bytes();m.publish(root,report);self.assertEqual(first,(root/m.OUTPUT).read_bytes())
   pointer=m.read(root/m.OUTPUT);packet=root/pointer['packet_path'];self.assertEqual(packet.name,pointer['packet_sha256']+'.json')
   m.publish(root,{**report,'records':[{'id':'B1'}]});self.assertTrue(packet.exists());self.assertEqual(len(list((root/'data/derived/ocpa-lineage/backups').iterdir())),1)
   packet=root/m.read(root/m.OUTPUT)['packet_path'];packet.write_text('{}')
   with self.assertRaises(ValueError):m.publish(root,report)
 def test_manifest_tamper_and_path_escape(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);m.publish(root,{'source_snapshot':'snap','records':[]});(root/m.OUTPUT).write_text('{}')
   with self.assertRaises(ValueError):m.previous(root)
   with self.assertRaises(ValueError):m.local(root,'../escape')

if __name__=='__main__':unittest.main()
