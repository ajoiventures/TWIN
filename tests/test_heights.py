import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_heights import positive_floor,floor_estimate,choose_floors
class HeightEvidenceTests(unittest.TestCase):
 def test_zero_and_fractional_floor_values_are_not_silently_counted(self):
  self.assertIsNone(positive_floor('0'));self.assertIsNone(positive_floor('1.5'));self.assertIsNone(positive_floor(None));self.assertEqual(positive_floor('2'),2)
 def test_multiple_buildings_do_not_inherit_parcel_story_count(self):
  self.assertEqual(choose_floors(1,6,False),(1,'maximum_building_footprint_floor_number'))
 def test_implausible_parcel_story_conflict_is_queued(self):
  count,method=choose_floors(2,11,True);self.assertEqual(count,2);self.assertIn('outlier',method)
 def test_estimates_use_explicit_floor_and_roof_allowances(self):
  self.assertEqual(floor_estimate(2,False),7.2);self.assertEqual(floor_estimate(1,True),4.3)
 def test_unknown_stays_unknown(self):self.assertEqual(choose_floors(None,None,True),(None,'unknown'))
if __name__=='__main__':unittest.main()
