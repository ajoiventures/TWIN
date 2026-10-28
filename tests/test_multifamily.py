import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from review_multifamily import normalized_attributes

class MultifamilySourceChecks(unittest.TestCase):
 def test_zero_unit_storeys_remain_unknown_not_source_change(self):
  self.assertEqual(normalized_attributes({'STYS':0,'AYB':2006}),(None,2006))
  self.assertEqual(normalized_attributes({'STYS':None,'AYB':2006}),(None,2006))
 def test_real_upper_storeys_not_discarded(self):
  self.assertEqual(normalized_attributes({'STYS':6.0,'AYB':2019}),(6,2019))
 def test_invalid_values_use_same_snapshot_normalization(self):
  self.assertEqual(normalized_attributes({'STYS':101,'AYB':0}),(None,None))

if __name__=='__main__':unittest.main()
