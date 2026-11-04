"""Bounded apartment/condo evidence inventory; no automatic geometry promotion."""
from pathlib import Path
import sys,json,collections,argparse,datetime,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
from data_pipeline import Client,atomic_json,now
URL='https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4'
FIELDS=['OBJECTID','PARCEL','SITUS','DOR_CODE','PROP_NAME','STYS','FLOOR_NO','CONDO_FLAG','PARENT_ID','AYB']

def normalized_attributes(record):
    raw=record.get('STYS');story=float(raw) if raw is not None else None
    if story is not None and not 0<story<=100:story=None
    year=record.get('AYB');year=int(year) if year and 1700<=int(year)<=datetime.date.today().year+1 else None
    return story,year

def category(code):
    prefix=str(code or '').zfill(4)[:2]
    return {'03':'apartment_candidate','08':'small_multifamily_candidate','04':'condominium_record','12':'mixed_use_review'}.get(prefix)

def build(offline=False):
    active=json.loads((ROOT/'data/processed/active.json').read_text());folder=ROOT/active['relative_path']
    parcels=json.loads((folder/'parcels.json').read_text())['features']
    buildings=json.loads((folder/'buildings.json').read_text());by_parcel=collections.defaultdict(list)
    for b in buildings:by_parcel[b.get('parcel_id')].append(b)
    heights={h['building_id']:h for h in json.loads((ROOT/'data/heights/building_heights.json').read_text())}
    if any(h['source_snapshot']!=active['snapshot'] for h in heights.values()):raise ValueError('Height evidence is stale')
    boundaries=json.loads((ROOT/'data/processed/study_boundaries.geojson').read_text())['features']
    main=shape(next(f for f in boundaries if f['id']=='main_street')['geometry'])
    project=Transformer.from_crs(4326,32617,always_xy=True).transform
    center=transform(project,shape(json.loads((ROOT/'data/processed/pilot.json').read_text())['centerline'])).centroid
    candidates=[f for f in parcels if category(f['properties'].get('property_use_code'))]
    client=Client(ROOT/'data/cache/multifamily',offline=offline);evidence={}
    for i in range(0,len(candidates),75):
        ids=[f['properties']['source_object_id'] for f in candidates[i:i+75]]
        response=client.get(URL+'/query',{'f':'json','objectIds':','.join(map(str,ids)),'outFields':','.join(FIELDS),'returnGeometry':'false'})
        if response.get('exceededTransferLimit'):raise ValueError('Truncated property evidence')
        for f in response.get('features',[]):evidence[f['attributes']['OBJECTID']]=f['attributes']
        if set(ids)-set(evidence):raise ValueError('Property evidence missing requested source IDs')
    identity_path=ROOT/'data/imagery/princeton_parcel_review/identity_evidence.json'
    identity_packet=json.loads(identity_path.read_text(encoding='utf-8')) if identity_path.exists() else {}
    identities={r['parcel_id']:r for r in identity_packet.get('subjects',[])} if identity_packet.get('source_snapshot')==active['snapshot'] else {}
    rows=[]
    for f in candidates:
        p=f['properties'];e=evidence[p['source_object_id']];geom=shape(f['geometry']);associated=by_parcel[p['parcel_id']]
        accepted=[b for b in associated if b['match_method']=='id_and_geometry'];issues=[]
        source_candidates=[{'id':b['id'],'assigned_parcel_id':b.get('parcel_id'),'match_method':b['match_method']} for b in buildings if b.get('source_parcel_id')==p['parcel_id']]
        story=e.get('STYS') or 0
        modeled=[{'id':b['id'],'match_method':b['match_method'],'floors_used':heights.get(b['id'],{}).get('floors_used'),'height_m':heights.get(b['id'],{}).get('height_m'),'height_quality':heights.get(b['id'],{}).get('quality')} for b in associated]
        if not accepted:issues.append('no_accepted_current_building_link')
        if story>=2 and accepted and not any((heights.get(b['id'],{}).get('floors_used') or 0)>=story for b in accepted):issues.append('parcel_storeys_exceed_all_accepted_modeled_counts')
        normalized_stories,normalized_year=normalized_attributes(e)
        if normalized_year!=p.get('year_built') or normalized_stories!=p.get('stories'):issues.append('source_changed_since_snapshot')
        if str(e.get('DOR_CODE'))!=p.get('property_use_code'):issues.append('use_code_changed_since_snapshot')
        if category(p.get('property_use_code'))=='condominium_record':issues.append('unit_or_component_record_not_independent_building')
        if category(p.get('property_use_code'))=='mixed_use_review':issues.append('residential_component_not_established')
        rows.append({'parcel_id':p['parcel_id'],'parcel_feature_id':p['id'],'site_address':p.get('site_address'),'property_name':e.get('PROP_NAME'),'source_use_code':e.get('DOR_CODE'),'candidate_category':category(p.get('property_use_code')),'reported_parcel_stories':e.get('STYS'),'reported_unit_floor':e.get('FLOOR_NO'),'year_built':e.get('AYB'),'condo_flag':e.get('CONDO_FLAG'),'parent_id':e.get('PARENT_ID'),'intersects_main_street':main.intersects(geom),'distance_to_pilot_center_m':round(transform(project,geom).distance(center),2),'accepted_model_links':len(accepted),'source_id_candidates_not_accepted_links':source_candidates,'associated_model_groups':modeled,'review_flags':issues,'geometry_change_allowed':False})
    for row in rows:
        identity=identities.get(row['parcel_id'])
        if identity:
            row['reviewed_identity']={'address_aliases':sorted({p['properties']['ADDR_FULL'] for p in identity['source_address_points']}),'photo_caption_date':identity['official_photo']['caption_capture_date'],'two_storey_front_observed':identity['official_photo']['two_storey_front_facade_observed'],'own_parcel_footprint_overlap_fraction':identity['legacy_geometry']['own_parcel_overlap_fraction'],'upper_story_semantics':'Source FUS describes an upper story even while FLOOR_NUM is 1; whole-building extrusion is not supported.','geometry_accepted':False}
    rows.sort(key=lambda r:(r['distance_to_pilot_center_m']>350,not r['intersects_main_street'],-(r['reported_parcel_stories'] or 0),r['distance_to_pilot_center_m']))
    report={'height_evidence_sha256':hashlib.sha256((ROOT/'data/heights/building_heights.json').read_bytes()).hexdigest(),'source_snapshot':active['snapshot'],'reviewed_utc':now(),'source_url':URL,'source_requests':client.accesses,'candidate_records':len(rows),'candidate_categories':dict(collections.Counter(r['candidate_category'] for r in rows)),'main_street_records':sum(r['intersects_main_street'] for r in rows),'within_350m_of_pilot':sum(r['distance_to_pilot_center_m']<=350 for r in rows),'unlinked_records_by_category':dict(collections.Counter(r['candidate_category'] for r in rows if r['accepted_model_links']==0)),'records_without_accepted_building_link':sum(r['accepted_model_links']==0 for r in rows),'rows':rows,'limits':['Record counts are not apartment units, complexes or physical buildings.','03/08/04/12 prefixes select review candidates from DOR use families; county subtypes and mixed residential use need individual review.','Unit FLOOR_NO and parcel STYS are distinct; neither is measured roof height.','No missing roof shape or redevelopment lineage is invented.','Current agency attributes and historical geometry may describe different dates.']}
    if identities:report['identity_evidence_sha256']=hashlib.sha256(identity_path.read_bytes()).hexdigest()
    atomic_json(ROOT/'data/processed/multifamily_review.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['rows','source_requests']},indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');build(p.parse_args().offline)
