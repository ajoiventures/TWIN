from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
sys.path.insert(0, str(ROOT / 'tools'))
from storey_audit import SAFE_FIELDS, condo_floor_evidence, evidence_client, height_contradictions, parcel_representation, positive_integer


class StoreyAuditTests(unittest.TestCase):
    def test_zero_fractional_and_missing_storeys_are_unknown(self):
        for value in [None, '', 0, '0', '1.5', -1, 'unknown']:
            self.assertIsNone(positive_integer(value))
        self.assertEqual(positive_integer('7'), 7)

    def test_accessory_one_floor_not_forced_to_match_taller_main_building(self):
        rows = [{'match_method': 'id_and_geometry', 'floors_used': 2}, {'match_method': 'id_and_geometry', 'floors_used': 1}]
        self.assertEqual(parcel_representation(2, rows), 'represented_by_at_least_one_building')
        self.assertEqual(rows[1]['floors_used'], 1)

    def test_unresolved_multibuilding_parcel_requires_review(self):
        rows = [{'match_method': 'id_and_geometry', 'floors_used': 1}] * 2
        self.assertEqual(parcel_representation(2, rows), 'multi_building_parcel_no_matching_storey_evidence')

    def test_spatial_match_is_not_promoted_by_matching_story_count(self):
        rows = [{'match_method': 'spatial_review', 'floors_used': 6}]
        self.assertEqual(parcel_representation(6, rows), 'no_accepted_building_link')

    def test_extreme_parcel_story_count_is_not_automatically_applied(self):
        self.assertEqual(parcel_representation(11, [{'match_method': 'id_and_geometry', 'floors_used': 2}]), 'parcel_story_outlier_or_building_floor_conflict')

    def test_unit_floor_positions_do_not_claim_whole_building_storeys(self):
        rows = [{'PROP_NAME': 'CONDO', 'FLOOR_NO': '7', 'STYS': 0}, {'PROP_NAME': 'CONDO', 'FLOOR_NO': '2', 'STYS': 1}]
        evidence = condo_floor_evidence(rows)
        self.assertEqual(evidence['highest_reported_unit_floor'], 7)
        self.assertIsNone(evidence['whole_building_storey_count'])
        self.assertEqual(evidence['parcel_stys_distribution'], {'0': 1, '1': 1})

    def test_unit_address_digits_are_not_inferred_as_floor_numbers(self):
        evidence = condo_floor_evidence([{'PROP_NAME': 'CONDO', 'SITUS': '2305 EDGEWATER DR UNIT 1701', 'FLOOR_NO': '0', 'STYS': 0}])
        self.assertIsNone(evidence['highest_reported_unit_floor'])

    def test_rejected_tall_lidar_candidate_is_flagged_without_changing_height(self):
        row = {'floors_used': 1, 'source_building_floor': 1, 'height_m': 4.3, 'roof_elevation_m': 47.91, 'nearby_ground_elevation_m': 31.95}
        self.assertIn('rejected_lidar_candidate_much_taller_than_applied_mass', height_contradictions(row))
        self.assertEqual(row['height_m'], 4.3)

    def test_low_two_floor_height_is_explicit_review_case(self):
        row = {'floors_used': 2, 'source_building_floor': 2, 'height_m': 3.5}
        self.assertIn('low_height_per_reported_floor_needs_review', height_contradictions(row))

    def test_source_floor_lost_in_height_record_is_detected(self):
        self.assertIn('raw_building_floor_exceeds_floors_used', height_contradictions({'floors_used': 1, 'source_building_floor': 2, 'height_m': 4.2}))

    def test_safe_property_request_fields_exclude_owner_contact_columns(self):
        for field in ['NAME1', 'NAME2', 'ADD1', 'ADD2', 'CITY', 'STATE', 'ZIP', 'COUNTRY']:
            self.assertNotIn(field, SAFE_FIELDS)
        self.assertIn('FLOOR_NO', SAFE_FIELDS)
        self.assertIn('PROP_NAME', SAFE_FIELDS)

    def test_offline_cache_miss_stays_unknown_and_never_connects(self):
        with tempfile.TemporaryDirectory() as tmp, patch('urllib.request.urlopen', side_effect=AssertionError('network called')):
            data, receipt = evidence_client({'f': 'json', 'where': '1=1'}, Path(tmp), live=False)
            self.assertIsNone(data)
            self.assertEqual(receipt['status'], 'unknown_offline_cache_miss')


if __name__ == '__main__':
    unittest.main()
