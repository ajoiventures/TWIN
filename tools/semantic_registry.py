"""Versioned evidence/asset registry and additive semantic USD layer.

This declares a local validation profile, not NVIDIA SimReady certification.
"""
from pathlib import Path
import sys,json,hashlib,collections,datetime,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf
from data_pipeline import atomic_json

SCHEMA='twin.asset/1.0'
PROFILE='college-park-evidence-visualization/1.0'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def building_identity(source_ids):
    values=sorted(set(str(x).strip() for x in source_ids if str(x).strip()))
    if not values:raise ValueError('Missing source footprint IDs')
    return 'ocpa:building-group:'+hashlib.sha256(','.join(values).encode()).hexdigest()[:24]

def validate_records(records):
    errors=[];ids=set();paths=set()
    for row in records:
        key=row.get('entity_id')
        if not key or key in ids:errors.append({'entity_id':key,'code':'duplicate_or_missing_identity'})
        ids.add(key)
        path=row.get('usd_path')
        if not isinstance(path,str) or not path.startswith('/') or not Sdf.Path.IsValidPathString(path) or not Sdf.Path(path).IsPrimPath():errors.append({'entity_id':key,'code':'invalid_usd_path'})
        if path in paths:errors.append({'entity_id':key,'code':'duplicate_usd_path'})
        paths.add(row.get('usd_path'))
        if row.get('schema')!=SCHEMA:errors.append({'entity_id':key,'code':'invalid_schema'})
        height=row.get('height_m')
        if isinstance(height,bool) or not isinstance(height,(float,int)) or not math.isfinite(height) or height<=0:errors.append({'entity_id':key,'code':'invalid_height'})
        if not row.get('source_snapshot') or not row.get('source_feature_ids'):errors.append({'entity_id':key,'code':'missing_evidence'})
        source_ids=row.get('source_feature_ids')
        if not isinstance(source_ids,list) or not source_ids or any(not isinstance(i,str) or not i.strip() for i in source_ids):errors.append({'entity_id':key,'code':'invalid_source_ids'})
        elif key!=building_identity(source_ids):errors.append({'entity_id':key,'code':'source_identity_mismatch'})
        if row.get('observation_kind') not in ['estimated','historical_lidar_derived']:errors.append({'entity_id':key,'code':'invalid_quality'})
    return errors

def build(root=ROOT):
    root=Path(root);active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'));folder=root/active['relative_path']
    buildings=json.loads((folder/'buildings.json').read_text(encoding='utf-8'))
    heights=json.loads((root/'data/heights/building_heights.json').read_text(encoding='utf-8'))
    if any(h['source_snapshot']!=active['snapshot'] for h in heights):raise ValueError('Stale height evidence; rebuild against active snapshot')
    by_height={h['building_id']:h for h in heights}
    if len(by_height)!=len(heights):raise ValueError('Duplicate height evidence')
    base=root/'scene/college_park.usda';base_hash=sha(base);stage=Usd.Stage.Open(str(base));records=[]
    for b in buildings:
        prim=stage.GetPrimAtPath(b['usd_path'])
        if not prim:raise ValueError('Missing source prim '+b['usd_path'])
        raw=prim.GetCustomData();h=by_height.get(b['id'])
        if h is None:raise ValueError('Missing height evidence '+b['id'])
        ids=[v for v in raw.get('sourceObjectIds','').split(',') if v]
        records.append({'schema':SCHEMA,'entity_id':building_identity(ids),'entity_type':'building_group','local_building_id':b['id'],
            'source_feature_ids':ids,'source_snapshot':active['snapshot'],'source_geometry_file_sha256':base_hash,'usd_path':b['usd_path'],
            'parcel_id':b.get('parcel_id'),'parcel_feature_id':b.get('parcel_feature_id'),'parcel_link_accepted':b['match_method']=='id_and_geometry',
            'parcel_match_method':b['match_method'],'height_m':h['height_m'],'height_method':h['method'],
            'observation_kind':'historical_lidar_derived' if h['quality']=='historical_lidar_derived' else 'estimated',
            'valid_time':{'start':None,'end':None,'quality':'current_validity_not_verified'},
            'acquisition_interval':{'start':'2018-12-04','end':'2019-04-12'} if h['quality']=='historical_lidar_derived' else None,
            'horizontal_reference':{'crs':'EPSG:32617','origin_wgs84':[-81.389,28.572],'local_units':'meters'},
            'vertical_reference':{'scene':'flat local prototype ground','height':'relative to local ground','surveyed_ground':False},
            'evidence_refs':[f"snapshot:{active['snapshot']}:buildings:{b['id']}",f"height:{b['id']}"],
            'review_status':'needs_review' if not b['match_method']=='id_and_geometry' or h.get('review_notes') else 'source_linked_not_field_verified',
            'notes':h.get('review_notes','')})
    errors=validate_records(records)
    if errors:raise ValueError(str(errors[:10]))
    scene=root/'scene';layer=Usd.Stage.CreateNew(str(scene/'semantic_assets.usda'))
    for r in records:
        prim=layer.OverridePrim(r['usd_path']);prim.SetCustomDataByKey('twin',{'entityId':r['entity_id'],'schema':SCHEMA,'semanticClass':'building_group','quality':r['observation_kind'],'sourceSnapshot':active['snapshot'],'validationProfile':PROFILE})
    layer.GetRootLayer().customLayerData={'profile':PROFILE,'certification':'local evidence/visualization checks only; no NVIDIA certification claim'};layer.GetRootLayer().Save()
    report={'schema':'twin.registry/1.0','profile':PROFILE,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'base_geometry_sha256':base_hash,'height_evidence_sha256':sha(root/'data/heights/building_heights.json'),'records':records}
    atomic_json(root/'data/processed/asset_registry.json',report)
    quality={'records':len(records),'unique_entities':len({r['entity_id'] for r in records}),'quality':dict(collections.Counter(r['observation_kind'] for r in records)),'unaccepted_parcel_links':sum(not r['parcel_link_accepted'] for r in records),'errors':errors,'profile':PROFILE}
    atomic_json(root/'data/processed/asset_registry_quality.json',quality);print(json.dumps(quality,indent=2));return quality

if __name__=='__main__':build()
