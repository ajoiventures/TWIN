import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pedestrian_discovery import PublicClient, inspect_source, normalize_sample, query_params, candidate_geometry, valid_candidate_geometry, metadata_definitions

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

if __name__=='__main__':unittest.main()
