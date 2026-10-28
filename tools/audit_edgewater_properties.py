"""Full extracted Main Street/Edgewater parcel audit, not a physical building census."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer
from shapely.affinity import translate
from shapely.strtree import STRtree
from pxr import Usd,UsdGeom
from constrain_scene import mesh_footprint
from data_pipeline import Client,atomic_json,now

OCPA='https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4'
FIELDS=['OBJECTID','PARCEL','SITUS','DOR_CODE','PROP_NAME','STYS','FLOOR_NO','AYB','CONDO_FLAG','PARENT_ID','LAND_DOR_CODE','BLDG_DOR_CODE']

def build(offline=False,root=ROOT):
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    active=read(root/'data/processed/active.json');folder=root/active['relative_path'];boundaries=read(root/'data/processed/study_boundaries.geojson')['features']
    main=shape(next(f for f in boundaries if f['id']=='main_street')['geometry']);project=Transformer.from_crs(4326,32617,always_xy=True).transform
    parcels=read(folder/'parcels.json')['features'];buildings=read(folder/'buildings.json');zones=read(folder/'zoning.json')['features'];heights=read(root/'data/heights/building_heights.json')
    if any(h['source_snapshot']!=active['snapshot'] for h in heights):raise ValueError('Height evidence is stale')
    height_index={h['building_id']:h for h in heights};zone_shapes=[(z['properties'],transform(project,shape(z['geometry']))) for z in zones]
    selected=[p for p in parcels if shape(p['geometry']).intersection(main).area>1e-12 or 'EDGEWATER' in str(p['properties'].get('site_address','')).upper()]
    client=Client(root/'data/cache/edgewater_audit',offline=offline);fresh={}
    for i in range(0,len(selected),75):
        ids=[p['properties']['source_object_id'] for p in selected[i:i+75]]
        data=client.get(OCPA+'/query',{'f':'json','objectIds':','.join(map(str,ids)),'outFields':','.join(FIELDS),'returnGeometry':'false'})
        if data.get('error') or data.get('exceededTransferLimit'):raise ValueError('Incomplete OCPA response')
        fresh.update({f['attributes']['OBJECTID']:f['attributes'] for f in data.get('features',[])})
        if any(n not in fresh for n in ids):raise ValueError('Missing OCPA source records')
    stage=Usd.Stage.Open(str(root/'scene/college_park_connected.usda'));geometry_paths=[];geometry_shapes=[]
    for b in buildings:
        prim=stage.GetPrimAtPath(b['usd_path'])
        if prim and prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':geometry_paths.append(b['usd_path']);geometry_shapes.append(mesh_footprint(prim))
    tree=STRtree(geometry_shapes);origin=Transformer.from_crs(4326,32617,always_xy=True).transform(*read(root/'config/study_area.json')['local_origin_wgs84'])
    associated=collections.defaultdict(list);source_ids=collections.defaultdict(list)
    for b in buildings:associated[b.get('parcel_id')].append(b);source_ids[b.get('source_parcel_id')].append(b)
    rows=[]
    for feature in selected:
        p=feature['properties'];e=fresh[p['source_object_id']];pin=p['parcel_id'];g=transform(project,shape(feature['geometry']))
        if str(e['PARCEL'])!=str(p['source_parcel_id']):raise ValueError('OCPA parcel identity changed')
        intersections=[]
        for z,zg in zone_shapes:
            area=g.intersection(zg).area
            if area>1:intersections.append({'code':z.get('Zoning'),'pd_name':z.get('PD_NAME'),'intersection_m2':round(area,2),'source_object_id':z['OBJECTID']})
        accepted=[b for b in associated[pin] if b['match_method']=='id_and_geometry']
        local=translate(g,xoff=-origin[0],yoff=-origin[1]);spatial=[]
        for index in tree.query(local):
            overlap=geometry_shapes[index].intersection(local).area
            if overlap>1:spatial.append({'usd_path':geometry_paths[index],'parcel_overlap_m2':round(overlap,2)})
        tax_candidate=str(e.get('DOR_CODE') or '').zfill(4)[:2].isdigit() and 10<=int(str(e.get('DOR_CODE') or '').zfill(4)[:2])<=39
        zone_candidate=any(str(z['code']).split('/')[0] in ['MU-1','MU-2','AC-1','AC-2','AC-3','O-1','O-2','O-3','I-C'] for z in intersections)
        flags=[]
        if not accepted:flags.append('no_accepted_model_link_not_proof_of_missing_building')
        if len({z['code'] for z in intersections})>1:flags.append('multiple_city_zoning_codes_review_split_or_sliver')
        if not intersections:flags.append('no_city_zoning_overlap_above_1m2')
        if e.get('CONDO_FLAG'):flags.append('condominium_record_not_independent_physical_building')
        modeled=[{'id':b['id'],'match_method':b['match_method'],'height_m':height_index.get(b['id'],{}).get('height_m'),'floors_used':height_index.get(b['id'],{}).get('floors_used'),'quality':height_index.get(b['id'],{}).get('quality')} for b in associated[pin]]
        rows.append({'parcel_feature_id':p['id'],'parcel_id':pin,'site_address':e.get('SITUS'),'property_name':e.get('PROP_NAME'),'in_main_street':shape(feature['geometry']).intersection(main).area>1e-12,'edgewater_address':'EDGEWATER' in str(e.get('SITUS','')).upper(),'ocpa_use_code':e.get('DOR_CODE'),'ocpa_land_use_code':e.get('LAND_DOR_CODE'),'ocpa_building_use_code':e.get('BLDG_DOR_CODE'),'ocpa_reported_storeys':e.get('STYS'),'unit_floor_separate':e.get('FLOOR_NO'),'year_built':e.get('AYB'),'commercial_tax_family_review':tax_candidate,'commercial_or_mixed_zoning_review':zone_candidate,'city_zoning':intersections,'accepted_model_links':len(accepted),'modeled_groups':modeled,'spatial_footprint_candidates_not_accepted_identity':spatial,'source_parcel_candidates':[b['id'] for b in source_ids[pin]],'review_flags':flags,'ocpa_record_url':'https://ocpaweb.ocpafl.org/propertycard/'+pin,'physical_building_verified':False,'current_listing_status':'unknown'})
    rows.sort(key=lambda r:(not r['commercial_tax_family_review'],r['accepted_model_links']>0,r['site_address'] or '',r['parcel_id']))
    commercial=[r for r in rows if r['commercial_tax_family_review']];report={'source_snapshot':active['snapshot'],'created_utc':now(),'scope':'All parcels intersecting official Main Street plus Edgewater-address parcels in current extraction; not the entire Edgewater roadway beyond project bounds','parcel_features':len(rows),'unique_parcel_ids':len({r['parcel_id'] for r in rows}),'tax_commercial_family_records':len(commercial),'tax_commercial_without_accepted_model_link':sum(r['accepted_model_links']==0 for r in commercial),'ocpa_requests':client.accesses,'source_fields':FIELDS,'rows':rows,'limits':['Tax family screening is a review queue, not verified occupancy or entitlement. County subcodes need OCPA-specific definitions.','No accepted link does not prove a missing building; condo units, parking/vacant land, spatial links and historical geometry need review.','Zoning, actual use, physical buildings, storefront suites and listing availability are different entities.','City polygon overlaps use current snapshot geometry; fresh OCPA attributes do not refresh that geometry.','Other-source and current physical verification remain open for each row.']}
    report['tax_commercial_without_visible_legacy_footprint_candidate']=sum(not r['spatial_footprint_candidates_not_accepted_identity'] for r in commercial)
    paths=[folder/(n+'.json') for n in ['parcels','buildings','zoning']]+[root/'data/heights/building_heights.json',root/'data/processed/study_boundaries.geojson',root/'config/study_area.json']
    paths+=list({Path(layer.realPath) for layer in stage.GetUsedLayers() if layer.realPath and Path(layer.realPath).is_relative_to(root.resolve())})
    report['dependencies']={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    out=root/'data/commercial';out.mkdir(exist_ok=True);atomic_json(out/'edgewater_property_audit.json',report)
    with (out/'edgewater_property_audit.csv').open('w',newline='',encoding='utf-8') as f:
        columns=['parcel_id','site_address','property_name','ocpa_use_code','ocpa_reported_storeys','unit_floor_separate','year_built','accepted_model_links','physical_building_verified','current_listing_status','ocpa_record_url'];writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows({k:r.get(k) for k in columns} for r in rows)
    print(json.dumps({k:v for k,v in report.items() if k not in ['rows','ocpa_requests','dependencies','source_fields','limits']},indent=2));print('First review rows:',json.dumps([{k:r[k] for k in ['site_address','ocpa_use_code','accepted_model_links']} for r in rows[:5]],indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');build(parser.parse_args().offline)
