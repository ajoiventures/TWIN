from pathlib import Path
import sys,json,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from review_corridor_buildings import record_state

def context(**changes):
    result={'reconstructed':False,'proposal_ready':False,'condo_or_shared':False,'land_only':False,'visible_geometry':False,
            'source_displaced':False,'accepted_links':0,'building_attributes':True}
    result.update(changes);return result

class CorridorReviewTests(unittest.TestCase):
    def test_registered_form_not_counted_missing_again(self):
        self.assertEqual(record_state({'parcel_id':'office'},context(reconstructed=True)),'already_reconstructed_historical')
    def test_ready_uncomposed_form_kept_separate_from_active_model(self):
        self.assertEqual(record_state({'parcel_id':'post'},context(proposal_ready=True)),'historical_source_form_ready_uncomposed')
    def test_condo_and_parking_records_are_not_automatic_buildings(self):
        self.assertEqual(record_state({'parcel_id':'unit'},context(condo_or_shared=True)),'condo_or_shared_building_record')
        self.assertEqual(record_state({'parcel_id':'parking'},context(land_only=True)),'parking_or_unimproved_land_review')
    def test_spatial_geometry_presence_is_not_promoted_to_accepted_tax_identity(self):
        self.assertEqual(record_state({'parcel_id':'shop'},context(visible_geometry=True)),'identity_link_review_existing_geometry')
    def test_no_model_only_raises_unverified_omission_candidate(self):
        self.assertEqual(record_state({'parcel_id':'house'},context()),'potential_physical_omission_unverified')
    def test_full_existing_artifact_has_all_queue_rows_and_outside_unknowns(self):
        path=ROOT/'data/processed/corridor_building_review.json'
        if not path.exists():self.skipTest('Ignored local review artifact absent')
        report=json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(len(report['original_35_queue']),35);self.assertEqual(len(report['original_17_queue']),17)
        self.assertEqual(report['coverage']['main_street']['percent_area_in_extraction'],100)
        self.assertLess(report['coverage']['neighborhood']['percent_area_in_extraction'],61)
        self.assertIsNone(report['coverage']['neighborhood']['parcel_or_building_count_outside_extraction'])
        self.assertFalse(any(r['physical_omission_confirmed'] for r in report['rows']))
        self.assertEqual(report['corrected_building_count'],0)
        self.assertFalse(report['active_model_modified'])
        self.assertEqual(report['official_subarea_floor_underuse'],[])

if __name__=='__main__':unittest.main()
