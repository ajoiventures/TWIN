import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from property_search import search_parcels

class PropertySearchTests(unittest.TestCase):
    rows=[{'id':'a','properties':{'site_address':'1615 EDGEWATER DR','parcel_id':'292214147800150'}},
          {'id':'b','properties':{'site_address':'644 W PRINCETON ST','parcel_id':'001234567890123'}},
          {'id':'c','properties':{'site_address':'1615 OTHER ST','parcel_id':'292223149200010'}}]
    def ids(self,q):return [r['id'] for r in search_parcels(self.rows,q)]
    def test_address_abbreviations_order_and_prefix(self):
        self.assertEqual(self.ids('1615 Edgewater Drive'),['a'])
        self.assertEqual(self.ids('edgewater 1615'),['a'])
        self.assertEqual(self.ids('644 west princeton street'),['b'])
        self.assertEqual(self.ids('edgew'),['a'])
    def test_parcel_number_format_and_leading_zeroes(self):
        self.assertEqual(self.ids('001234567890123'),['b'])
        self.assertEqual(self.ids('14-22-29-1478-00-150'),['a'])
        self.assertEqual(self.ids('292223149200010'),['c'])
    def test_empty_unknown_and_invalid_input(self):
        self.assertEqual(self.ids(''),[]);self.assertEqual(self.ids('---'),[])
        self.assertEqual(self.ids('9999 missing avenue'),[])
        with self.assertRaises(ValueError):self.ids('a'*161)
    def test_no_numeric_coercion_or_raw_owner_field_search(self):
        self.assertEqual(self.ids('1234567890123'),['b']) # Explicit partial PIN search
        self.assertEqual(self.ids('someone private'),[])
