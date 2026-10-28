import io
import json
from pathlib import Path
import sys
import struct
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from source_catalog import ProbeClient, acquisition_groups, coverage_html, iso_summary, normalize_use_restrictions, probe_source, run_discoveries, select_candidates, snapshot_evidence, tiff_pixel_scale


class Response(io.BytesIO):
    status = 200
    headers = {'Content-Type': 'application/json'}

    def geturl(self):
        return 'https://official.example/test'


class CatalogTests(unittest.TestCase):
    def test_offline_miss_does_not_connect_or_claim_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            def forbidden(*args, **kwargs):
                raise AssertionError('Network called in offline mode')
            source = {'id': 'x', 'url': 'https://official.example/test', 'kind': 'arcgis'}
            result = probe_source(source, [0, 0, 1, 1], ProbeClient(tmp, offline=True, opener=forbidden), Path(tmp))
            self.assertEqual(result['coverage']['state'], 'unknown')
            self.assertIsNone(result['coverage']['feature_count'])

    def test_cached_probe_preserves_original_fetch_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            def opener(*args, **kwargs):
                calls.append(1)
                return Response(b'{"ok":true}')
            client = ProbeClient(tmp, opener=opener)
            first = client.get('https://official.example/test')
            second = client.get('https://official.example/test')
            self.assertEqual(first['checked_utc'], second['checked_utc'])
            self.assertEqual(second['read_mode'], 'cached')
            self.assertEqual(len(calls), 1)

    def test_html_access_is_not_observed_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = ProbeClient(tmp, opener=lambda *a, **kw: Response(b'<html>GIS portal</html>'))
            result = probe_source({'id': 'x', 'url': 'https://official.example/test', 'kind': 'portal'}, [0, 0, 1, 1], client, Path(tmp))
            self.assertEqual(result['probe']['status'], 'reachable')
            self.assertEqual(result['coverage']['state'], 'unknown')

    def test_service_error_is_not_a_zero_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = ProbeClient(tmp, opener=lambda *a, **kw: Response(b'{"error":{"code":499,"message":"Token required"}}'))
            result = probe_source({'id': 'x', 'url': 'https://official.example/test', 'kind': 'arcgis'}, [0, 0, 1, 1], client, Path(tmp))
            self.assertEqual(result['probe']['status'], 'service_error')
            self.assertIsNone(result['coverage']['feature_count'])

    def test_bbox_count_requires_successful_count_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            def opener(request, **kw):
                return Response(b'{"count":0}' if '/query?' in request.full_url else b'{"type":"Feature Layer","fields":[]}')
            result = probe_source({'id': 'x', 'url': 'https://official.example/test', 'kind': 'arcgis'}, [0, 0, 1, 1], ProbeClient(tmp, opener=opener), Path(tmp))
            self.assertEqual(result['coverage']['state'], 'observed_bbox_query')
            self.assertEqual(result['coverage']['feature_count'], 0)

    def test_only_explicit_evidenced_acquisitions_deduplicate(self):
        sources = [{'id': 'a', 'acquisition_id': 'flight1', 'acquisition_evidence': 'metadata'},
                   {'id': 'b', 'acquisition_id': 'flight1', 'acquisition_evidence': 'metadata'},
                   {'id': 'c', 'acquisition_id': 'flight2'}, {'id': 'd'}]
        groups = acquisition_groups(sources)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]['source_ids'], ['a', 'b'])
        self.assertEqual(groups[0]['independent_measurement_count'], 1)

    def test_snapshot_preview_is_allowlisted_and_keeps_zeroes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / 'data/snapshots/test'
            folder.mkdir(parents=True)
            (root / 'data/processed').mkdir()
            (root / 'data/processed/active.json').write_text(json.dumps({'snapshot': 'test', 'relative_path': 'data/snapshots/test'}))
            (folder / 'parcels.json').write_text(json.dumps([{'parcel_id': '00123', 'owner': 'EXCLUDED', 'notes': 'EXCLUDED', 'stories': None}]))
            result = snapshot_evidence({'snapshot_table': 'parcels', 'safe_fields': ['parcel_id', 'stories']}, root)
            self.assertEqual(result['first_five_rows'], [{'parcel_id': '00123', 'stories': None}])

    def test_snapshot_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data/processed').mkdir(parents=True)
            (root / 'data/processed/active.json').write_text(json.dumps({'snapshot': 'bad', 'relative_path': '../outside'}))
            with self.assertRaises(ValueError):
                snapshot_evidence({'snapshot_table': 'parcels'}, root)

    def test_tiff_pixel_scale_comes_from_binary_tag(self):
        raw = bytearray(50)
        raw[:8] = b'II' + struct.pack('<HI', 42, 8)
        raw[8:10] = struct.pack('<H', 1)
        raw[10:22] = struct.pack('<HHII', 33550, 12, 3, 26)
        raw[26:50] = struct.pack('<ddd', 2.5, 2.5, 1)
        class Client:
            def binary_range(self, *args):
                return {'status': 'reachable', 'range_honored': True, 'data_hex': raw.hex()}
        result = tiff_pixel_scale('https://official.example/dem.tif', Client())
        self.assertEqual(result['pixel_scale_source_units'], [2.5, 2.5, 1])

    def test_unknown_tiles_are_not_accepted(self):
        result = select_candidates([], [-81.398, 28.5605, -81.379, 28.5845])
        self.assertEqual(result[0]['decision'], 'pending')
        self.assertEqual(result[0]['coverage_boxes_wgs84'], [])
        self.assertIsNone(result[0]['resolution_m'])

    def test_nodata_canopy_is_pending_not_valid_tree_locations(self):
        result = select_candidates([{'id': 'florida_noaa_canopy_2020_2021', 'pilot_pixel_samples': [{'value': ''}]}], [0, 0, 1, 1])
        canopy = next(c for c in result if c['id'] == 'florida_noaa_canopy')
        self.assertTrue(canopy['pilot_sample_nodata'])
        self.assertEqual(canopy['decision'], 'pending')
        self.assertEqual(canopy['coverage_boxes_wgs84'], [])

    def test_iso_envelope_is_not_valid_pixel_coverage(self):
        xml = '''<root xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">
        <gmd:westBoundLongitude><gco:Decimal>-82</gco:Decimal></gmd:westBoundLongitude>
        <gmd:eastBoundLongitude><gco:Decimal>-80</gco:Decimal></gmd:eastBoundLongitude>
        <gmd:southBoundLatitude><gco:Decimal>27</gco:Decimal></gmd:southBoundLatitude>
        <gmd:northBoundLatitude><gco:Decimal>29</gco:Decimal></gmd:northBoundLatitude></root>'''
        summary = iso_summary(xml)
        self.assertEqual(summary['bbox_wgs84'], [-82, 27, -80, 29])
        result = select_candidates([{'id': 'noaa_florida_east1_dem', 'metadata_summary': summary, 'resolution_m': 3}], [-81.398, 28.5605, -81.379, 28.5845])
        regional = next(c for c in result if c['id'] == 'noaa_east1_regional_dem')
        self.assertTrue(regional['metadata_bbox_intersects_study'])
        self.assertIn('not valid-pixel', regional['coverage_basis'])
        self.assertEqual(regional['decision'], 'reject_for_precise_streetscape')

    def test_map_leaves_unknown_coverage_undrawn(self):
        candidates = select_candidates([], [-81.398, 28.5605, -81.379, 28.5845])
        result = coverage_html({'study_bbox_wgs84': [-81.398, 28.5605, -81.379, 28.5845], 'created_utc': 'test', 'candidate_selections': candidates})
        self.assertIn('Unknown coverage is not drawn', result)
        self.assertIn('<g id="florida_noaa_canopy"></g>', result)

    def test_oversize_metadata_has_distinct_unreadable_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = ProbeClient(tmp, opener=lambda *a, **kw: Response(b'x' * (2 * 1024 * 1024 + 1)))
            self.assertEqual(client.get('https://official.example/test')['status'], 'metadata_unreadable')

    def test_malformed_optional_local_snapshot_does_not_discard_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data/processed').mkdir(parents=True)
            (root / 'data/processed/active.json').write_text('not JSON')
            source = {'id': 'x', 'url': 'https://official.example/test', 'kind': 'portal', 'snapshot_table': 'parcels'}
            result = probe_source(source, [0, 0, 1, 1], ProbeClient(root / 'cache', opener=lambda *a, **kw: Response(b'<html>portal</html>')), root)
            self.assertEqual(result['probe']['status'], 'reachable')
            self.assertIn('local_snapshot_error', result)

    def test_ecopia_license_excludes_ml_and_does_not_infer_expiry(self):
        license_text = '<p>USE RESTRICTIONS: This land cover data may not be used for the purpose of creating, training, improving, modifying, validating, testing, or evaluating machine learning algorithms, or otherwise leverage the product for the purposes of machine learning for a period of five years from its date of creation, except with the express written consent of Ecopia Tech Corporation.</p>'
        policy = normalize_use_restrictions({'licenseInfo': license_text, 'created': 1262304000000}, 'https://official.example/item')
        self.assertFalse(policy['ml_use_allowed'])
        self.assertEqual(policy['duration_years'], 5)
        self.assertIn('validating', policy['restricted_purposes'])
        self.assertIn('evaluating machine learning algorithms', policy['restriction_text'])
        self.assertIsNone(policy['original_product_creation_date'])
        self.assertIsNone(policy['restriction_expiry_date'])
        self.assertIsNone(policy['written_consent_evidence'])
        self.assertEqual(policy['arcgis_item_created_epoch_ms'], 1262304000000)

    def test_ml_restriction_excludes_candidate_even_if_canopy_pixel_exists(self):
        row = {'id': 'florida_noaa_canopy_2020_2021', 'pilot_pixel_samples': [{'value': '77'}], 'use_restrictions': {'ml_use_allowed': False}}
        result = next(c for c in select_candidates([row], [0, 0, 1, 1]) if c['id'] == 'florida_noaa_canopy')
        self.assertEqual(result['decision'], 'exclude_from_ai_candidate_use')
        self.assertFalse(result['ai_use_allowed'])

    def test_empty_license_never_grants_ml_permission(self):
        self.assertIsNone(normalize_use_restrictions({'licenseInfo': ''}, 'metadata')['ml_use_allowed'])

    def test_empty_bounded_search_is_not_general_no_data(self):
        class Client:
            def get(self, url, params):
                return {'status': 'reachable', 'payload': {'total': 0, 'nextStart': -1, 'results': []}}
        cfg = {'study_bbox_wgs84': [0, 0, 1, 1], 'discovery_queries': [{'id': 'transport', 'domain': 'transportation', 'query': 'owner:specific'}]}
        result = run_discoveries(cfg, Client())[0]
        self.assertTrue(result['bounded_search_complete'])
        self.assertIn('no general no-data claim', result['outcome'])
        self.assertEqual(result['query'], 'owner:specific')

    def test_discovery_result_limit_is_recorded_not_claimed_exhaustive(self):
        class Client:
            def get(self, url, params):
                return {'status': 'reachable', 'payload': {'total': 100, 'nextStart': 31, 'results': [{'id': 'item1', 'title': 'Imagery'}]}}
        cfg = {'study_bbox_wgs84': [0, 0, 1, 1], 'discovery_queries': [{'id': 'imagery', 'domain': 'imagery', 'query': 'imagery', 'limit': 30}]}
        result = run_discoveries(cfg, Client())[0]
        self.assertFalse(result['bounded_search_complete'])
        self.assertEqual(result['total'], 100)
        self.assertIn('not selected', result['results'][0]['disposition'])


if __name__ == '__main__':
    unittest.main()
