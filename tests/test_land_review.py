import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from review_land import city_pin

class LandIdentityTests(unittest.TestCase):
    def test_section_township_range_reordered_without_losing_zeroes(self):
        self.assertEqual(city_pin('03-23-29-0180-02-240'),'292303018002240')
        self.assertEqual(city_pin('292303018002240'),'292303018002240')
    def test_bad_identifiers_remain_unknown(self):
        for value in [None,'','3-23-29-0180-02-240','03-23-29-0180-02-X40','123']:
            with self.subTest(value=value):self.assertIsNone(city_pin(value))
