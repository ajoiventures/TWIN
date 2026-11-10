import hashlib, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pedestrian_discovery import (
    PublicClient, inspect_source, normalize_sample, query_params, candidate_geometry,
    valid_candidate_geometry, metadata_definitions, edgewater_crossing_review, CROSSING_REVIEW, MAY_DRAFT,
)

class PedestrianDiscoveryTests(unittest.TestCase):
    def test_internal_source_is_never_contacted(self):
        class FailClient:
            def get(self,*args):self.fail('No internal request permitted')
        result=inspect_source({'id':'internal','kind':'internal_reference_not_public','url':'https://x.orlando.cit/foo'},[],FailClient())
        self.assertEqual(result['public_access'],'not_public_not_queried')
        self.assertFalse(result['geometry_accepted'])
    def test_public_client_rejects_internal_host(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'Internal'):PublicClient(d).get('https://x.orlando.cit/foo')
    def test_sample_allowlist_does_not_release_notes(self):
        sample=normalize_sample({'attributes':{'OBJECTID':1,'Width':5,'Notes':'private','Owner':'someone','CityReview':'free text','PedPlan':'Future'}},'crosswalk')
        self.assertEqual(sample['attributes'],{'OBJECTID':1,'Width':5,'PedPlan':'Future'})
        self.assertIsNone(sample['width_unit']);self.assertEqual(sample['facility_status'],'unresolved_source_codes')
    def test_bbox_is_explicit_wgs84_intersection(self):
        p=query_params([-81.4,28.5,-81.3,28.6]);self.assertEqual(p['inSR'],4326)
        self.assertEqual(p['spatialRel'],'esriSpatialRelIntersects')
    def test_no_features_is_not_no_sidewalks(self):
        class Stub:
            def get(self,url,params):
                if not url.endswith('/query'):return {'fields':[{'name':'OBJECTID','type':'esriFieldTypeOID'}],'description':'Roads in RCI'}
                if params.get('returnCountOnly'):return {'count':0}
                return {'objectIds':[]}
        r=inspect_source({'id':'roads','url':'https://example.invalid/0','kind':'roadway_attributes_not_walkway_edges'},[],Stub())
        self.assertEqual(r['public_access'],'accessible_no_study_features');self.assertFalse(r['geometry_accepted'])
    def test_inconsistent_ids_cannot_be_accepted(self):
        class Stub:
            def get(self,url,params):
                if not url.endswith('/query'):return {'fields':[{'name':'OBJECTID','type':'esriFieldTypeOID'}]}
                if params.get('returnCountOnly'):return {'count':2}
                return {'objectIds':[1]}
        r=inspect_source({'id':'cross','url':'https://example.invalid/0','kind':'crosswalk_candidate'},[],Stub())
        self.assertEqual(r['public_access'],'error_or_incomplete');self.assertIn('mismatch',r['error'])
    def test_offline_miss_fails_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'Offline cache miss'):PublicClient(d,True).get('https://example.invalid')
    def test_candidate_retains_unknown_lifecycle_and_width_units(self):
        class Stub:
            def get(self,url,params):return {'features':[{'properties':{'OBJECTID':1,'PedPlan':2,'Width':8,'Notes':'excluded'},'geometry':{'type':'LineString','coordinates':[[-81.39,28.57],[-81.389,28.57]]}}]}
        result={'public_access':'accessible_with_study_features','object_ids':[1], 'fields':[{'name':x} for x in ['OBJECTID','PedPlan','Width']]}
        data=candidate_geometry({'url':'https://example.invalid/0','id':'may'},result,Stub())
        p=data['features'][0]['properties'];self.assertEqual(p['source_pedplan_code'],2)
        self.assertEqual(p['lifecycle_bucket'],'unresolved');self.assertIsNone(p['proposed_status'])
        self.assertIsNone(p['width_unit']);self.assertNotIn('Notes',p['attributes']);self.assertFalse(data['accepted_for_modeling'])
    def test_failed_candidate_access_does_not_become_empty_coverage(self):
        with self.assertRaisesRegex(ValueError,'validated coverage'):
            candidate_geometry({'url':'x','id':'x'},{'public_access':'error_or_incomplete'},None)
    def test_projected_or_nonfinite_coordinates_are_not_wgs84(self):
        self.assertFalse(valid_candidate_geometry({'type':'LineString','coordinates':[[500000,3100000],[500001,3100000]]}))
        self.assertFalse(valid_candidate_geometry({'type':'LineString','coordinates':[[float('nan'),28.5],[-81.3,28.5]]}))
    def test_xml_preserves_definition_without_invented_units(self):
        definitions=metadata_definitions('<metadata><attr><attrlabl>Width</attrlabl><attrdef>Raw field</attrdef><attrmfrq>daily</attrmfrq></attr></metadata>')
        self.assertEqual(definitions['width']['definition'],'Raw field');self.assertNotIn('unit',definitions['width'])

    def test_review_classifies_only_matched_rows_and_rejects_changed_draft(self):
        from build_edgewater_focus_corridor import OUT

        scope = {'source_snapshot': 'test', 'features': [{
            'id': 'edgewater_focus_corridor', 'geometry': {'type': 'Polygon',
            'coordinates': [[[-81.40, 28.56], [-81.38, 28.56], [-81.38, 28.58],
                             [-81.40, 28.58], [-81.40, 28.56]]]}}]}
        draft = {'source_id': 'crosswalk_may2026', 'accepted_for_modeling': False, 'features': [
            {'id': str(object_id), 'geometry': {'type': 'LineString',
             'coordinates': [[-81.39, 28.57], [-81.389, 28.57]]},
             'properties': {'source_object_id': object_id, 'source_pedplan_code': 2}}
            for object_id in (1, 2)
        ]}
        with tempfile.TemporaryDirectory() as directory, patch('build_edgewater_focus_corridor.validate', return_value=scope):
            root = Path(directory)

            def write(path, value):
                path = root / path
                path.parent.mkdir(parents=True, exist_ok=True)
                content = json.dumps(value).encode()
                path.write_bytes(content)
                return hashlib.sha256(content).hexdigest()

            write(CROSSING_REVIEW, {'source_snapshot': 'test', 'accepted_for_scene_geometry': False,
                'checked_date': '2026-11-10', 'scope_sha256': write(OUT, scope),
                'draft_crosswalk_reconciliation': {'may_draft_sha256': write(MAY_DRAFT, draft),
                    'matched_status_counts': {'Existing Crosswalk': 0, 'Proposed Crosswalk': 1},
                    'rows': [{'may_draft_object_id': 1, 'may_draft_pedplan_code': 2, 'prioritization_layer': 19,
                              'prioritization_status': 'Proposed Crosswalk', 'prioritization_project_id': 8,
                              'geometry_hausdorff_delta_m': 0, 'verified_current_existing_condition': False}]}})
            packet = edgewater_crossing_review(root)
            self.assertEqual([f['properties']['planning_classification'] for f in packet['features']],
                             ['proposed_new', 'unresolved'])
            self.assertFalse(packet['accepted_for_scene_geometry'])
            draft['features'][0]['geometry']['coordinates'][0][0] = -81.395
            write(MAY_DRAFT, draft)
            with self.assertRaisesRegex(ValueError, 'exact reviewed scope and draft'):
                edgewater_crossing_review(root)

if __name__=='__main__':unittest.main()
