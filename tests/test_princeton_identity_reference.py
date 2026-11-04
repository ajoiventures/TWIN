import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from princeton_identity_reference import area_reconciliation

class PrincetonIdentityTests(unittest.TestCase):
    def test_upper_story_code_does_not_become_uniform_height(self):
        parts=[{'properties':{'SUBAREA':'BAS','AREA_FT':1224,'FLOOR_NUM':'1'}}, {'properties':{'SUBAREA':'FUS','AREA_FT':1224,'FLOOR_NUM':'1'}}]
        r=area_reconciliation(parts,{'LIVING_AREA':2448,'GROSS_AREA':2448});self.assertTrue(r['living_area_matches_bas_plus_fus']);self.assertEqual(r['all_floor_num_values'],['1']);self.assertIn('not a whole-building',r['interpretation'])
    def test_partial_upstairs_624_reconciles_living_and_gross(self):
        parts=[{'properties':{'SUBAREA':c,'AREA_FT':a,'FLOOR_NUM':'1'}} for c,a in [('BAS',494),('BAS',494),('FUS',416),('FUS',416),('FGR',240),('FGR',240),('FOP',20),('FOP',20)]]
        r=area_reconciliation(parts,{'LIVING_AREA':1820,'GROSS_AREA':2340});self.assertTrue(r['living_area_matches_bas_plus_fus']);self.assertEqual(r['sum_subareas_ft2'],2340)
    def test_area_mismatch_stays_explicit(self):
        r=area_reconciliation([{'properties':{'SUBAREA':'BAS','AREA_FT':1000,'FLOOR_NUM':'1'}}],{'LIVING_AREA':1500});self.assertFalse(r['living_area_matches_bas_plus_fus'])

if __name__=='__main__':unittest.main()
