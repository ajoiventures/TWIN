"""Focused denominator and safe-reference contracts; no network/live fixtures."""
import sys,unittest,tempfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from shapely.geometry import box
from shapely.strtree import STRtree
from city_planning_reference import denominator,memberships,split_code,verify_previous,OUT

class PlanningReferenceTests(unittest.TestCase):
    def test_overlapping_tax_records_do_not_double_land_area(self):
        result=denominator([box(0,0,6,10),box(0,0,6,10),box(4,0,8,10)],box(0,0,10,10))
        self.assertAlmostEqual(result['source_feature_area_sum_m2'],160)
        self.assertAlmostEqual(result['unique_covered_area_m2'],80)
        self.assertAlmostEqual(result['overlapping_source_area_excess_m2'],80)
        self.assertAlmostEqual(result['unrepresented_area_m2'],20)
    def test_split_context_preserves_code_and_unknown_dates_without_entitlements(self):
        fs=[{'source_feature_id':'city:zoning:1','properties':{'OBJECTID':1,'Zoning':'PD/T/AR','PD_NAME':'SOURCE PLAN','FormatDate':None},'projected':box(0,0,4,10)},
            {'source_feature_id':'city:zoning:2','properties':{'OBJECTID':2,'Zoning':'C','PD_NAME':None,'FormatDate':'2/2019'},'projected':box(4,0,10,10)}]
        rows=memberships(box(0,0,10,10),fs,STRtree([f['projected'] for f in fs]),'zoning')
        self.assertEqual([r['parcel_clipped_area_fraction'] for r in rows],[.4,.6])
        self.assertEqual(rows[0]['zoning'],{'original':'PD/T/AR','base':'PD','overlay_tokens':['T','AR']})
        self.assertIsNone(rows[0]['source_format_date'])
        self.assertEqual(rows[1]['zoning']['original'],'C')
        self.assertEqual(split_code(None),{'original':None,'base':None,'overlay_tokens':[]})
        self.assertNotIn('permitted_use',rows[0])
    def test_unreceipted_manual_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/OUT;out.mkdir(parents=True);p=out/'packet.json';p.write_text('{"manual":true}')
            before=p.read_bytes()
            with self.assertRaisesRegex(ValueError,'unreceipted'):verify_previous(root)
            self.assertEqual(p.read_bytes(),before)

if __name__=='__main__':unittest.main()
