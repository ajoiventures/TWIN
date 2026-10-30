import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from parcel_audit import audit_records,source_key,positive_integer,active_folder

def parcel(pin='00123',feature='ocpa:1'):
    return {'id':feature,'parcel_id':pin,'source_parcel_id':pin,'source_object_id':int(feature.split(':')[-1]),'stories':1,'owner':'DO NOT EXPORT'}
def building(identifier='Building_1',method='id_and_geometry',pin='00123',feature='ocpa:1'):
    return {'id':identifier,'usd_path':'/World/Buildings/'+identifier,'source_parcel_id':'00123','parcel_id':pin,'parcel_feature_id':feature,
            'match_method':method,'overlap_ratio':1.0,'candidate_parcels':[pin] if pin else []}

class ParcelAuditTests(unittest.TestCase):
    def test_duplicate_pin_preserves_distinct_source_features(self):
        summary,q,_=audit_records([parcel(),parcel(feature='ocpa:2')],[] ,[],'s')
        self.assertEqual(summary['parcel_features'],2);self.assertEqual(summary['unique_parcel_ids'],1)
        self.assertEqual(len(q['duplicate_parcel_ids'][0]['features']),2)
        self.assertNotIn('owner',q['duplicate_parcel_ids'][0]['features'][0])
    def test_spatial_match_remains_unaccepted(self):
        b=building(method='spatial_review');summary,q,_=audit_records([parcel()],[b],[],'s')
        self.assertEqual(summary['match_methods'],{'spatial_review':1});self.assertFalse(q['non_exact_links'][0]['accepted'])
        self.assertEqual(b['match_method'],'spatial_review');self.assertEqual(summary['accepted_linked_parcels'],0)
    def test_bad_exact_match_is_exception_not_fixed(self):
        b=building(pin='99999');_,q,_=audit_records([parcel()],[b],[],'s')
        self.assertEqual(len(q['link_integrity']),1);self.assertEqual(b['parcel_id'],'99999')
    def test_one_to_many_counts_only_exact_links(self):
        buildings=[building('Building_1'),building('Building_2'),building('Building_3',method='spatial_review')]
        s,q,_=audit_records([parcel()],buildings,[],'s')
        self.assertEqual(s['accepted_one_to_many_parcels'],1);self.assertEqual(q['multiple_buildings_per_parcel'][0]['accepted_building_count'],2)
    def test_stale_heights_are_not_used_for_floor_conflicts(self):
        heights=[{'building_id':'Building_1','source_snapshot':'old','source_building_floor':2,'source_parcel_stories':11}]
        s,q,_=audit_records([parcel()],[building()],heights,'new')
        self.assertEqual(s['current_snapshot_height_rows'],0);self.assertEqual(len(q['stale_height_evidence']),1);self.assertEqual(q['floor_conflicts'],[])
    def test_floor_disagreements_keep_raw_counts_and_decision(self):
        h={'building_id':'Building_1','source_snapshot':'s','source_building_floor':2,'source_parcel_stories':11,'floors_used':2}
        p=parcel();p['stories']=11;_,q,_=audit_records([p],[building()],[h],'s')
        self.assertEqual(q['floor_conflicts'][0]['severity'],'large_conflict');self.assertEqual(h['floors_used'],2)
    def test_copied_parcel_count_cannot_hide_current_conflict(self):
        p=parcel();p['stories']=11;h={'building_id':'Building_1','source_snapshot':'s','source_building_floor':2,'source_parcel_stories':2}
        _,q,_=audit_records([p],[building()],[h],'s');self.assertEqual(q['floor_conflicts'][0]['source_parcel_stories'],11);self.assertEqual(len(q['stale_height_evidence']),1)
    def test_nonfinite_and_out_of_range_overlaps_fail(self):
        for value in [float('nan'),float('inf'),-1,1.1,'1',True]:
            b=building();b['overlap_ratio']=value;_,q,_=audit_records([parcel()],[b],[],'s');self.assertTrue(q['link_integrity'])
    def test_source_key_keeps_leading_zeroes(self):
        self.assertEqual(source_key('00123','01'),'ocpa-building:00123:01');self.assertIsNone(source_key('00123',''))
        self.assertIsNone(positive_integer(.5));self.assertIsNone(positive_integer(True));self.assertIsNone(positive_integer(float('nan')))
    def test_ambiguous_and_unmatched_have_different_counts(self):
        a=building('A',method='ambiguous_or_unmatched',pin=None,feature=None)
        b=building('B',method='ambiguous_or_unmatched',pin=None,feature=None);b['candidate_parcels']=['00123','00456']
        s,_,_=audit_records([parcel()],[a,b],[],'s');self.assertEqual(s['ambiguous_with_candidates'],1);self.assertEqual(s['unmatched_without_candidates'],1)
    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data/processed').mkdir(parents=True)
            (root/'data/processed/active.json').write_text(json.dumps({'relative_path':'../outside','snapshot':'x'}))
            with self.assertRaises(ValueError):active_folder(root)

if __name__=='__main__':unittest.main()
