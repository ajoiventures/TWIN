import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from wellesley_reference import reported_height,floor_union_evidence

class WellesleyReferenceTests(unittest.TestCase):
    def test_reported_height_is_scoped_historical_not_uniform_extrusion(self):
        r=reported_height();self.assertEqual(r['reported_stories'],7);self.assertAlmostEqual(r['converted_m'],22.86)
        self.assertFalse(r['whole_footprint_uniform_height_approved']);self.assertIn('not_surveyed',r['quality'])
    def test_tax_floor_union_is_not_architectural_plate(self):
        from pyproj import Transformer
        polygon={'type':'Polygon','coordinates':[[[-81.39,28.57],[-81.389,28.57],[-81.389,28.571],[-81.39,28.57]]]}
        rows=[{'PARCEL':'00123','FLOOR_NO':'7'}];result=floor_union_evidence(rows,{'00123':{'geometry':polygon}},Transformer.from_crs(4326,32617,always_xy=True))
        self.assertEqual(result[0]['properties']['source_unit_floor_no'],'7');self.assertFalse(result[0]['properties']['accepted_for_uniform_extrusion'])
    def test_missing_condo_geometry_fails_without_inventing_shape(self):
        with self.assertRaisesRegex(ValueError,'missing'):floor_union_evidence([{'PARCEL':'00123','FLOOR_NO':'7'}],{},None)

if __name__=='__main__':unittest.main()
