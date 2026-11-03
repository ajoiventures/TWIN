from pathlib import Path
import copy,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from parcel_audit import disposition_records

class DispositionTests(unittest.TestCase):
    def fixture(self):
        row={'id':'Building_1','usd_path':'/World/Buildings/Building_1','source_parcel_id':'000123','parcel_id':'000456','parcel_feature_id':'ocpa:b','match_method':'spatial_review','source_building_floor':1,'source_parcel_stories':3,'floors_used':1,'severity':'large_conflict','height_quality':'floor_count_estimate'}
        identity={'id':'Building_1','usd_path':row['usd_path'],'entity_id':'existing:source','source_building_key':'ocpa-building:000123:01','source_object_ids':['0007'],'join_state':'spatial_review','candidate_parcel_features':[{'parcel_feature_id':'ocpa:a','parcel_id':'000456'},{'parcel_feature_id':'ocpa:b','parcel_id':'000456'}]}
        parcels=[{'id':id,'properties':{'parcel_id':'000456'}} for id in ['ocpa:a','ocpa:b']]
        return {'non_exact_links':[row],'floor_conflicts':[row]},[identity],parcels,{'rows':[]},[{'id':'form','parcel_id':'000456','quality':'historical_current_unknown'}],[{'source_parcel_id':'000123','source_building_number':'01','source_object_ids':['0007'],'dated_reference_ids':['historical2024'],'frame_disposition':'partial_frame'}]
    def test_exact_identity_context_preserves_unknowns_and_component_conflict(self):
        args=self.fixture();before=copy.deepcopy(args);rows=disposition_records(*args)
        self.assertEqual(args,before);self.assertEqual(len(rows),2)
        for row in rows:
            self.assertFalse(row['new_link_accepted']);self.assertFalse(row['current_conditions_verified']);self.assertFalse(row['height_change_authorized'])
            self.assertEqual(row['source_parcel_id'],'000123');self.assertEqual(row['assigned_parcel_feature_id'],'ocpa:b');self.assertEqual(len(row['candidate_parcel_features']),2)
            self.assertEqual(row['registered_historical_evidence'][0]['association'],'parcel_context_only_not_identity_acceptance')
            self.assertEqual(row['dated_aerial_observations'][0]['source_object_ids'],['0007'])
            self.assertEqual(row['source_building_floor'],1);self.assertEqual(row['source_parcel_stories'],3);self.assertEqual(row['existing_floors_used'],1)
            self.assertEqual(row['status'],'deferred_pending_property_component_evidence')
    def test_changed_membership_never_reuses_aerial_or_accepts_link(self):
        args=list(self.fixture());args[-1][0]['source_object_ids']=['different'];rows=disposition_records(*args)
        self.assertTrue(all(not r['dated_aerial_observations'] for r in rows))
        args[1][0]['join_state']='accepted'
        with self.assertRaises(ValueError):disposition_records(*args)
        args=list(self.fixture());args[0]['non_exact_links'][0]['parcel_feature_id']='ocpa:missing'
        with self.assertRaises(ValueError):disposition_records(*args)

if __name__=='__main__':unittest.main()
