"""Curated commercial-source evidence snapshots; no automatic market or model activation."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,os,re
ROOT=Path(__file__).resolve().parents[1]
FACT_FIELDS={'component_area_sf','area_basis','building_story_context','retail_gla_sf','suite_area_sf',
 'building_area_sf','building_area_basis','year_built','page_available_area_sf_min','page_available_area_sf_max',
 'brochure_suites','building_stories','space_area_sf_approx','reported_dimensions_feet'}

def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
def normalized_address(value,strip_suite=False):
    text=re.sub(r'[^A-Z0-9# ]',' ',str(value or '').upper())
    text=re.sub(r'\bDRIVE\b','DR',text);text=re.sub(r'\bSTREET\b','ST',text)
    if strip_suite:text=re.split(r'\b(?:UNIT|SUITE|STE)\b|#',text)[0]
    return ' '.join(text.split())

def freshness(source,now,days=30):
    stamp=source.get('observed_utc');checked=None
    try:checked=datetime.datetime.fromisoformat(stamp.replace('Z','+00:00')) if stamp else None
    except (ValueError,TypeError):pass
    if checked is not None and checked.tzinfo is None:checked=None
    age=(now-checked).total_seconds()/86400 if checked else None
    if source.get('date_conflicts'):state='conflicting_source_dates'
    elif not source.get('status_as_of_date'):state='status_as_of_unknown'
    else:
        try:
            effective=datetime.date.fromisoformat(source['status_as_of_date'])
            state='future_source_date_review' if effective>now.date() else 'stale_status_evidence' if (now.date()-effective).days>days else 'recent_source_report_not_live_verification'
        except ValueError:state='invalid_source_date'
    return {'state':state,'source_checked_utc':stamp,'checked_age_days':round(age,2) if age is not None else None,
      'source_check_needs_refresh':age is None or age>days,'status_as_of_date':source.get('status_as_of_date'),
      'note':'A current check of an undated page/document does not prove current availability.'}

def grouped_claims(claims):
    """Only explicit provenance groups deduplicate; address alone never merges sale/lease/suites."""
    groups={}
    for claim in claims:
        key=claim.get('claim_group') or claim['id']
        if key not in groups:groups[key]={**claim,'source_ids':list(claim['source_ids']),'member_claim_ids':[claim['id']]}
        else:
            current=groups[key]
            if any(current.get(k)!=claim.get(k) for k in ['address','scope','suite','reported_status','facts']):
                raise ValueError('Conflicting scope/status in explicit syndication group: '+key)
            current['source_ids']=sorted(set(current['source_ids']+claim['source_ids']));current['member_claim_ids'].append(claim['id'])
    return list(groups.values())

def entity_links(claim,parcels,buildings):
    address=normalized_address(claim['address'],True)
    matches=[p for p in parcels if normalized_address(p.get('site_address'),True)==address]
    pinset={p['parcel_id'] for p in matches};candidate_buildings=[b for b in buildings if b.get('parcel_id') in pinset]
    identity=claim.get('identity_evidence',{});explicit=identity.get('parcel_id')
    accepted=[];context=[];physical=[]
    # An explicit source parcel ID still cannot assign a suite or condo component without component proof.
    if identity.get('kind')=='explicit_source_parcel_id' and explicit in pinset and identity.get('evidence_url'):
        if claim['scope']=='whole_building' and identity.get('scope_verified') and len(pinset)==1:
            for b in candidate_buildings:
                if b.get('match_method')=='id_and_geometry' and b.get('parcel_id')==explicit:
                    accepted.append({'claim_id':claim['id'],'parcel_id':explicit,'building_id':b['id'],
                       'scope':'whole_building','evidence_url':identity['evidence_url'],'listing_status_activated':False})
    if identity.get('kind')=='reviewed_property_address_context' and explicit in pinset and len(pinset)==1 and identity.get('scope_verified')=='property_context_only' and identity.get('evidence_url'):
        context.append({'claim_id':claim['id'],'parcel_id':explicit,'scope':'property_address_context_only',
             'source_facts':{k:v for k,v in claim['facts'].items() if k in ['building_area_sf','building_area_basis','year_built']},
             'evidence_url':identity['evidence_url'],'suite_assignment_accepted':False,'listing_status_activated':False})
    if identity.get('kind')=='reviewed_building_physical_reference' and claim['scope']=='building_physical_reference' and not claim.get('suite') and len(pinset)==1 and len(candidate_buildings)==1 and explicit in pinset and identity.get('scope_verified')=='physical_building_metadata_only' and identity.get('evidence_url'):
        for b in candidate_buildings:
            if b.get('match_method')=='id_and_geometry' and b.get('parcel_feature_id')==identity.get('parcel_feature_id') and b.get('source_parcel_id')==explicit:
                accepted.append({'claim_id':claim['id'],'parcel_id':explicit,'building_id':b['id'],'scope':'physical_building_metadata_only',
                    'evidence_url':identity['evidence_url'],'listing_status_activated':False})
                physical=[{'building_id':b['id'],'field':k,'value':v,'source_ids':claim['source_ids'],
                    'quality':'broker_reported_physical_metadata_with_reviewed_government_entity_link',
                    'geometry_resize_allowed':False,'listing_status_update_allowed':False} for k,v in claim['facts'].items() if k in ['building_area_sf','building_stories']]
    return {'claim_id':claim['id'],'listing_scope':claim['scope'],'suite':claim.get('suite'),
      'candidate_parcel_ids':sorted(pinset),'candidate_parcel_feature_ids':sorted(p['id'] for p in matches),
      'candidate_buildings':[{'building_id':b['id'],'parcel_id':b.get('parcel_id'),'government_match_method':b.get('match_method')} for b in candidate_buildings],
      'accepted_entity_links':accepted,'accepted_property_context':context,'accepted_physical_metadata':physical,'address_only_link_accepted':False,
      'review_reason':'Address identifies candidates only; suite/retail scope, source parcel identity and current availability need independent confirmation.' if matches else 'No exact normalized base-address parcel candidate in current snapshot; storefront may share another situs address.'}

def build(root=ROOT,now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc);config_path=root/'config/commercial_evidence.json';config=read_json(config_path)
    source_index={s['id']:s for s in config['sources']}
    if len(source_index)!=len(config['sources']):raise ValueError('Duplicate commercial source IDs')
    pointer=read_json(root/'data/processed/active.json');folder=(root/pointer['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Snapshot escaped allowed directory')
    parcels=[f['properties'] for f in read_json(folder/'parcels.json')['features']];buildings=read_json(folder/'buildings.json')
    listings=[];links=[];source_rows=[]
    for source in config['sources']:
        source_rows.append({**source,'freshness':freshness(source,now,config['review_after_days']),
          'approved_for_ml':False,'ml_eligibility':'unestablished','source_licensing':'No copyrighted brochure/image redistribution permission inferred.'})
    for claim in grouped_claims(config['claims']):
        if set(claim.get('facts',{}))-FACT_FIELDS:raise ValueError('Non-allowlisted commercial fact')
        if not all(s in source_index for s in claim['source_ids']):raise ValueError('Unknown commercial source reference')
        link=entity_links(claim,parcels,buildings);links.append(link)
        listings.append({k:v for k,v in claim.items() if k!='identity_evidence'} | {
          'source_checked_utc':min(source_index[s]['observed_utc'] for s in claim['source_ids']),
          'source_status_freshness':[{'source_id':s,**freshness(source_index[s],now,config['review_after_days'])} for s in claim['source_ids']],
          'current_verified_status':'unknown','status_quality':'source_reported_only_not_live_market_confirmation',
          'physical_occupancy':'unknown','whole_building_status':'unknown',
          'model_status_update_allowed':False,'accepted_entity_link_count':len(link['accepted_entity_links']),
          'physical_metadata_update_allowed':bool(link['accepted_physical_metadata']),
          'approved_for_ml':False,'snapshot':pointer['snapshot']})
    verification_queue=[]
    for row,link in zip(listings,links):
        reasons=['Current availability is not independently confirmed.']
        reasons.extend(row.get('conflicts',[]))
        reasons.extend('Source '+s['source_id']+': '+s['state'] for s in row['source_status_freshness'] if s['state']!='recent_source_report_not_live_verification')
        if not link['accepted_entity_links']:reasons.append(link['review_reason'])
        verification_queue.append({'claim_id':row['id'],'scope':row['scope'],'suite':row.get('suite'),
             'reasons':reasons,'status':'unresolved_review','source_ids':row['source_ids']})
    summary={'normalized_claim_groups':len(listings),'source_records':len(source_rows),
      'source_reported_status_groups':dict(collections.Counter(r['reported_status'] for r in listings)),
      'current_verified_unknown_groups':sum(r['current_verified_status']=='unknown' for r in listings),
      'accepted_entity_links':sum(len(r['accepted_entity_links']) for r in links),
      'accepted_property_context_links':sum(len(r['accepted_property_context']) for r in links),
      'accepted_physical_metadata_facts':sum(len(r['accepted_physical_metadata']) for r in links),
      'candidate_groups_with_parcels':sum(bool(r['candidate_parcel_ids']) for r in links),
      'candidate_groups_without_parcels':sum(not r['candidate_parcel_ids'] for r in links),
      'model_status_updates':0,'note':'Counts describe bounded scoped evidence groups, not unique vacant buildings, citywide listings or available floor area.'}
    result={'schema_version':1,'created_utc':now.isoformat(),'mode':'offline_curated_evidence_normalization_no_network',
      'source_snapshot':pointer['snapshot'],'scope':config['scope'],'configuration_sha256':hashlib.sha256(config_path.read_bytes()).hexdigest(),
      'sources':source_rows,'listings':listings,'entity_link_review':links,'verification_queue':verification_queue,'quality':summary,
      'limitations':['Sale of a retail condominium component does not list the residential tower for sale.',
         'A suite lease advertisement does not establish whole-building vacancy or a verified tenant.',
         'Brochure creation/copyright dates and listing start dates are not current-status as-of dates.',
         'Broker-authored syndication copies are one evidence campaign, not independent confirmation.',
         'No contacts, rents, prices, financial metrics, private BOOMS or broker imagery enter normalized outputs.']}
    out=root/'data/commercial';write_json(out/'commercial_evidence.json',result)
    write_json(out/'commercial_listing_status.json',listings);write_json(out/'commercial_entity_review.json',links)
    write_json(out/'commercial_verification_queue.json',verification_queue)
    write_json(out/'commercial_preview.json',{'listing_fields':sorted(listings[0]) if listings else [],'first_five_rows':listings[:5],
      'first_five_entity_reviews':links[:5],'quality':summary})
    print(json.dumps(summary,indent=2));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true',help='Always offline; uses curated verified source facts and local public snapshot.')
    parser.parse_args();build()
