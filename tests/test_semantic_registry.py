import unittest,sys,copy,tempfile,json,hashlib,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from semantic_registry import building_identity,validate_records,SCHEMA
from data_pipeline import Client

class SemanticContractTests(unittest.TestCase):
 def row(self):return {'schema':SCHEMA,'entity_id':building_identity(['01']),'usd_path':'/World/B1','height_m':4.2,'source_snapshot':'s1','source_feature_ids':['01'],'observation_kind':'estimated'}
 def test_identity_is_order_independent_but_sensitive_to_membership(self):
  self.assertEqual(building_identity(['2','01','2']),building_identity(['01','2']))
  self.assertNotEqual(building_identity(['01','2']),building_identity(['1','2']))
 def test_no_source_identity_is_rejected(self):
  with self.assertRaises(ValueError):building_identity([])
 def test_duplicate_entities_and_paths_fail(self):
  errors=validate_records([self.row(),self.row()]);self.assertEqual({e['code'] for e in errors},{'duplicate_or_missing_identity','duplicate_usd_path'})
 def test_nonfinite_height_and_missing_source_fail(self):
  r=self.row();r.update(height_m=float('nan'),source_snapshot=None);self.assertEqual({e['code'] for e in validate_records([r])},{'invalid_height','missing_evidence'})
 def test_roof_deck_and_raised_equipment_keep_distinct_height_scope(self):
  r=self.row();r.update(height_m=23.35,maximum_rendered_height_m=28.393,maximum_rendered_height_scope='historical_roof_or_equipment_surface_not_occupied_storeys')
  self.assertEqual(validate_records([r]),[])
  del r['maximum_rendered_height_scope'];self.assertIn('missing_maximum_height_scope',{e['code'] for e in validate_records([r])})
 def test_maximum_render_height_must_not_be_below_main_mass(self):
  r=self.row();r.update(maximum_rendered_height_m=3)
  self.assertIn('invalid_maximum_rendered_height',{e['code'] for e in validate_records([r])})
 def test_legacy_cache_does_not_invent_retrieval_time(self):
  with tempfile.TemporaryDirectory() as folder:
   url='https://example.invalid/data';Path(folder,hashlib.sha256(url.encode()).hexdigest()+'.json').write_text('{}')
   c=Client(folder,offline=True);c.get(url);self.assertIsNone(c.accesses[0]['retrieved_utc']);self.assertTrue(c.accesses[0]['cache_hit'])
 def test_bad_paths_height_types_and_source_identity_fail(self):
  r=self.row();r.update(usd_path=None,height_m='four',entity_id='wrong')
  self.assertEqual({e['code'] for e in validate_records([r])},{'invalid_usd_path','invalid_height','source_identity_mismatch'})
 def test_mutated_cache_downgrades_timestamp(self):
  with tempfile.TemporaryDirectory() as folder:
   url='https://example.invalid/data';c=Client(folder,opener=lambda *a,**k:io.StringIO('{}'));c.get(url)
   Path(folder,hashlib.sha256(url.encode()).hexdigest()+'.json').write_text('{"changed":true}')
   d=Client(folder,offline=True);self.assertTrue(d.get(url)['changed']);self.assertIsNone(d.accesses[0]['retrieved_utc']);self.assertEqual(d.accesses[0]['retrieval_quality'],'cache_provenance_hash_mismatch')
 def test_network_retrieval_time_survives_cache_read(self):
  with tempfile.TemporaryDirectory() as folder:
   c=Client(folder,opener=lambda *a,**k:io.StringIO('{}'));c.get('https://example.invalid/data');t=c.accesses[0]['retrieved_utc']
   d=Client(folder,offline=True);d.get('https://example.invalid/data');self.assertEqual(d.accesses[0]['retrieved_utc'],t);self.assertTrue(d.accesses[0]['cache_hit'])

if __name__=='__main__':unittest.main()
