from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import county_context as county

class CountyDependencyTests(unittest.TestCase):
 def test_city_cache_only_change_invalidates_county_read_and_build(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)
   def write(name,value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value),encoding='utf-8');return path
   active=write('data/processed/active.json',{'snapshot':'fixture'})
   write('data/processed/pilot.json',{'source_snapshot':'fixture','context_geometry':{'type':'Polygon','coordinates':[[[-81.4,28.5],[-81.3,28.5],[-81.3,28.6],[-81.4,28.6],[-81.4,28.5]]]},'centerline':{'type':'LineString','coordinates':[[-81.35,28.52],[-81.35,28.58]]}})
   cache=write('data/cache/city_fixture.json',{'source':'original'})
   city=write('data/processed/city_adapter_contract/packet.json',{'source_snapshot':'fixture','dependencies':{'data/cache/city_fixture.json':county.sha(cache)}})
   write('data/processed/city_adapter_contract/receipt.json',{'source_snapshot':'fixture','sha256':county.sha(city)})
   fixed=write('county_reference.json',{'source':'unchanged'})
   packet=write(county.OUT+'/packet.json',{'schema':'twin.county-context/1','source_snapshot':'fixture','dependencies':{'county_reference.json':county.sha(fixed)}})
   write(county.OUT+'/references.geojson',{'type':'FeatureCollection','features':[]});write(county.OUT+'/coverage.svg','fixture')
   write(county.OUT+'/receipt.json',{'source_snapshot':'fixture','artifacts':{name:county.sha(root/county.OUT/name) for name in ('packet.json','references.geojson','coverage.svg')}})
   self.assertEqual(county.validate(root)['source_snapshot'],'fixture')
   original_packet=packet.read_bytes();original_active=active.read_bytes();cache.write_text('{"source":"changed"}')
   with self.assertRaisesRegex(ValueError,'City adapter source changed'):county.validate(root)
   with patch.object(county,'Probe',side_effect=AssertionError('No agency request expected')):
    with self.assertRaisesRegex(ValueError,'City adapter source changed'):county.build(root,offline=True)
   self.assertEqual(packet.read_bytes(),original_packet);self.assertEqual(active.read_bytes(),original_active)

if __name__=='__main__':unittest.main()
