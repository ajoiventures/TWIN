from pathlib import Path
import copy,json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import build_map_footprints as m
from shapely.geometry import shape

class MapFootprintTests(unittest.TestCase):
 def fixture(self):
  geometry={'type':'Polygon','coordinates':[[[-81.39,28.57],[-81.389,28.57],[-81.389,28.571],[-81.39,28.571],[-81.39,28.57]],[[-81.3898,28.5702],[-81.3898,28.5704],[-81.3896,28.5704],[-81.3896,28.5702],[-81.3898,28.5702]]]}
  raw={'features':[{'geometry':geometry,'properties':{'OBJECTID':id,'PID':'000123','BLDG_NUM':'04','FLOOR_NUM':'01'}} for id in ['001','002']]}
  registry=[{'local_building_id':'Building_17','entity_id':'source:entity','source_feature_ids':['001'],'usd_path':'/World/Buildings/Building_17','parcel_id':'000456','parcel_feature_id':'ocpa:a','parcel_link_accepted':False}]
  lineage=[{'id':'Building_17','entity_id':'source:entity','source_object_ids':['001'],'source_building_key':'ocpa-building:000123:04','join_state':'ambiguous','candidate_parcel_features':[{'parcel_feature_id':'ocpa:a','parcel_id':'000456'},{'parcel_feature_id':'ocpa:b','parcel_id':'000456'}]}]
  parcels=[{'id':id,'properties':{'parcel_id':'000123'}} for id in ['ocpa:c','ocpa:d']]
  return raw,registry,lineage,parcels
 def test_holes_membership_orphans_and_duplicate_contexts_preserved(self):
  features,counts=m.derive(*self.fixture());self.assertEqual(counts['raw_subareas'],2);self.assertTrue(counts['all_raw_ids_assigned_once'])
  modeled,orphan=features;self.assertEqual(len(shape(modeled['geometry']).interiors),1)
  self.assertEqual(modeled['id'],'source:entity');self.assertEqual(modeled['properties']['local_building_id'],'Building_17')
  self.assertEqual(modeled['properties']['source_object_ids'],['001']);self.assertEqual(orphan['properties']['source_object_ids'],['002'])
  for f in features:self.assertFalse(f['properties']['parcel_link_accepted']);self.assertIsNone(f['properties']['source_acquisition_date']);self.assertEqual(len(f['properties']['candidate_parcel_features']),2)
  self.assertEqual(set(modeled['properties']),set(m.FIELDS)-{'geometry'})
  self.assertEqual(orphan['properties']['membership_status'],'unrepresented_raw_subareas_review')
 def test_conflicting_source_ids_rejected(self):
  raw,registry,lineage,parcels=self.fixture();raw['features'].append(copy.deepcopy(raw['features'][0]))
  with self.assertRaises(ValueError):m.derive(raw,registry,lineage,parcels)
  raw,registry,lineage,parcels=self.fixture();registry[0]['source_feature_ids']=['001','002']
  with self.assertRaises(ValueError):m.derive(raw,registry,lineage,parcels)
 def packet_fixture(self,root):
  files={'data/processed/active.json':{'snapshot':'s','relative_path':'data/snapshots/s'},'data/buildings.geojson':{},'data/processed/asset_registry.json':{},'data/processed/building_lineage.json':{'packet_path':'data/derived/lineage.json','packet_sha256':__import__('hashlib').sha256(m.canonical({})).hexdigest()},'data/derived/lineage.json':{},'data/snapshots/s/parcels.json':{}}
  for path,value in files.items():p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(m.canonical(value))
  packet={'type':'FeatureCollection','schema':'twin.map-building-footprints/1','source_snapshot':'s','snapshot':'s','map_crs':'EPSG:32617','field_dictionary':m.FIELDS,'current_conditions_verified':False,'new_parcel_links_accepted':False,'dependencies':{p:m.sha(root/p) for p in files},'features':[],'identity_closure':{'lineage_packet_path':'data/derived/lineage.json','lineage_packet_sha256':files['data/processed/building_lineage.json']['packet_sha256'],'fingerprints':{'base':'fixture'}}}
  content=m.canonical(packet);digest=__import__('hashlib').sha256(content).hexdigest();path='data/derived/map-footprints/'+digest+'.geojson';(root/path).parent.mkdir(parents=True,exist_ok=True);(root/path).write_bytes(content)
  pointer=root/m.POINTER;pointer.write_bytes(m.canonical({'schema':'twin.map-footprint-pointer/1','source_snapshot':'s','packet_path':path,'packet_sha256':digest}));Path(str(pointer)+'.receipt').write_bytes(m.canonical({'sha256':m.sha(pointer)}))
  return root/path
 @patch.object(m,'validate_lineage',return_value={'fingerprints':{'base':'fixture'}})
 def test_cached_provider_rejects_changed_snapshot_and_tampered_packet(self,validator):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);packet=self.packet_fixture(root);self.assertEqual(m.read_packet(root)['map_crs'],'EPSG:32617');packet.write_text('{}')
   with self.assertRaises(ValueError):m.read_packet(root)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.packet_fixture(root);validator.side_effect=ValueError('Transitive source membership changed')
   with self.assertRaises(ValueError):m.read_packet(root)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);self.packet_fixture(root);(root/'data/processed/active.json').write_text(json.dumps({'snapshot':'new','relative_path':'data/snapshots/s'}))
   with self.assertRaises(ValueError):m.read_packet(root)

if __name__=='__main__':unittest.main()
