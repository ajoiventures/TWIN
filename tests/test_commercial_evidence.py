import datetime,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from commercial_evidence import freshness,grouped_claims,entity_links,build,normalized_address
NOW=datetime.datetime(2026,10,28,tzinfo=datetime.timezone.utc)

def claim(identifier='x',scope='individual_suite',status='offered_for_lease'):
    return {'id':identifier,'claim_group':identifier,'address':'2305 EDGEWATER DR','scope':scope,'suite':'I' if scope=='individual_suite' else None,
      'reported_status':status,'source_ids':['source'],'facts':{'suite_area_sf':945},'identity_evidence':{'kind':'unverified'}}
def parcel():return {'id':'ocpa:1','parcel_id':'00123','site_address':'2305 EDGEWATER DR','stories':2}
def building(method='id_and_geometry'):
    return {'id':'Building_1','parcel_id':'00123','source_parcel_id':'00123','parcel_feature_id':'ocpa:1','match_method':method}

class CommercialEvidenceTests(unittest.TestCase):
    def test_listing_start_or_pdf_creation_does_not_become_fresh_status(self):
        r=freshness({'observed_utc':'2026-10-28T00:00:00Z','reported_date':'2026-10-27','reported_date_kind':'date_on_market_not_status_update'},NOW)
        self.assertEqual(r['state'],'status_as_of_unknown')
    def test_stale_status_and_future_dates_are_explicit(self):
        self.assertEqual(freshness({'status_as_of_date':'2026-01-01'},NOW)['state'],'stale_status_evidence')
        self.assertEqual(freshness({'status_as_of_date':'2027-01-01'},NOW)['state'],'future_source_date_review')
    def test_conflicting_syndicated_dates_remain_conflicting(self):
        self.assertEqual(freshness({'date_conflicts':[{'value':'2026-08-17'},{'value':'2026-09-16'}]},NOW)['state'],'conflicting_source_dates')
    def test_explicit_syndication_group_counts_once(self):
        a=claim();b={**a,'id':'copy','source_ids':['copy_source']};rows=grouped_claims([a,b])
        self.assertEqual(len(rows),1);self.assertEqual(set(rows[0]['source_ids']),{'source','copy_source'})
    def test_same_address_sale_and_suite_lease_do_not_merge(self):
        rows=grouped_claims([claim('sale','retail_condominium_component','offered_for_sale'),claim('lease')]);self.assertEqual(len(rows),2)
    def test_conflicting_facts_in_same_campaign_do_not_silently_overwrite(self):
        a=claim();b={**a,'id':'copy','facts':{'suite_area_sf':1000}}
        with self.assertRaisesRegex(ValueError,'Conflicting'):grouped_claims([a,b])
    def test_explicit_parcel_id_cannot_promote_unverified_suite_or_retail_component(self):
        for scope in ['individual_suite','retail_condominium_component']:
            c=claim(scope=scope);c['identity_evidence']={'kind':'explicit_source_parcel_id','parcel_id':'00123','evidence_url':'https://broker.example','scope_verified':True}
            r=entity_links(c,[parcel()],[building()]);self.assertEqual(r['accepted_entity_links'],[])
    def test_address_candidate_alone_never_activates_any_building(self):
        r=entity_links(claim(scope='building_physical_reference'),[parcel()],[building()]);self.assertFalse(r['address_only_link_accepted']);self.assertEqual(r['accepted_entity_links'],[])
    def test_reviewed_physical_building_metadata_is_separate_from_market_status(self):
        c=claim(scope='building_physical_reference',status='unknown');c['facts']={'building_stories':2,'building_area_sf':15556}
        c['identity_evidence']={'kind':'reviewed_building_physical_reference','parcel_id':'00123','building_id':'Building_1','parcel_feature_id':'ocpa:1','scope_verified':'physical_building_metadata_only','evidence_url':'https://broker.example'}
        r=entity_links(c,[parcel()],[building()]);self.assertEqual(len(r['accepted_physical_metadata']),2)
        self.assertFalse(r['accepted_entity_links'][0]['listing_status_activated'])
        self.assertEqual(entity_links(c,[parcel()],[building('spatial_review')])['accepted_entity_links'],[])
        replacement=building();replacement['id']='Building_9999'
        self.assertEqual(entity_links(c,[parcel()],[replacement])['accepted_entity_links'][0]['building_id'],'Building_9999')
        self.assertEqual(entity_links(c,[parcel()],[building(),replacement])['accepted_entity_links'],[])
    def test_property_address_context_is_not_a_suite_link(self):
        c=claim(scope='office_suite_bundle');c['facts']={'building_area_sf':25324,'year_built':2002}
        c['identity_evidence']={'kind':'reviewed_property_address_context','parcel_id':'00123','scope_verified':'property_context_only','evidence_url':'https://broker.example'}
        r=entity_links(c,[parcel()],[building()]);self.assertEqual(len(r['accepted_property_context']),1);self.assertFalse(r['accepted_property_context'][0]['suite_assignment_accepted']);self.assertEqual(r['accepted_entity_links'],[])
    def test_unknown_current_status_is_not_zero_available_or_off_market(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'data/processed').mkdir(parents=True);folder=root/'data/snapshots/test';folder.mkdir(parents=True)
            (root/'config/commercial_evidence.json').write_text(json.dumps({'scope':'test','review_after_days':30,'sources':[{'id':'source','observed_utc':'2026-10-28T00:00:00Z'}],'claims':[claim()]}))
            (root/'data/processed/active.json').write_text(json.dumps({'snapshot':'test','relative_path':'data/snapshots/test'}))
            (folder/'parcels.json').write_text(json.dumps({'features':[{'properties':parcel()}]}));(folder/'buildings.json').write_text(json.dumps([building()]))
            r=build(root,NOW);self.assertEqual(r['quality']['current_verified_unknown_groups'],1);self.assertEqual(r['listings'][0]['current_verified_status'],'unknown')
            self.assertEqual(r['listings'][0]['whole_building_status'],'unknown');self.assertEqual(r['quality']['model_status_updates'],0)
    def test_address_normalization_keeps_suite_distinct_when_requested(self):
        self.assertEqual(normalized_address('2305 Edgewater Drive Suite I'), '2305 EDGEWATER DR SUITE I')
        self.assertEqual(normalized_address('2305 Edgewater Drive Suite I',True),'2305 EDGEWATER DR')

if __name__=='__main__':unittest.main()
