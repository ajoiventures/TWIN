import sys,json,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from serve import read_table,page_table,SnapshotMismatch,active_folder

class ApiContractTests(unittest.TestCase):
 def setup_root(self,folder):
  r=Path(folder);(r/'data/processed').mkdir(parents=True);(r/'data/snapshots/s1').mkdir(parents=True);(r/'data/heights').mkdir()
  (r/'data/processed/active.json').write_text(json.dumps({'snapshot':'s1','relative_path':'data/snapshots/s1'}));return r
 def test_snapshot_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.setup_root(d);(r/'data/processed/active.json').write_text(json.dumps({'snapshot':'bad','relative_path':'../../outside'}))
   with self.assertRaises(ValueError):active_folder(r)
 def test_stale_height_evidence_cannot_be_served_as_current(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.setup_root(d);(r/'data/heights/building_heights.json').write_text(json.dumps([{'source_snapshot':'old'}]))
   with self.assertRaises(SnapshotMismatch):read_table('heights',r)
 def test_stale_registry_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.setup_root(d);(r/'data/processed/asset_registry.json').write_text(json.dumps({'source_snapshot':'old','records':[]}))
   with self.assertRaises(SnapshotMismatch):read_table('assets',r)
 def test_parcel_filter_preserves_ids_and_limit(self):
  with tempfile.TemporaryDirectory() as d:
   r=self.setup_root(d);(r/'data/snapshots/s1/buildings.json').write_text(json.dumps([{'id':'b1','parcel_id':'001','height_m':4.2},{'id':'b2','parcel_id':'1','height_m':7.2}]))
   page=page_table('buildings',{'parcel_id':['001'],'limit':['5000']},r);self.assertEqual(page['total'],1);self.assertEqual(page['rows'][0]['id'],'b1');self.assertEqual(page['limit'],1000)

if __name__=='__main__':unittest.main()
