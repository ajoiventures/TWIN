"""Profile cached parks/zoning and the City's vacant-lot inventory; no ownership inference."""
from pathlib import Path
import collections,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from shapely.geometry import shape,box
from shapely.ops import transform,unary_union
from pyproj import Transformer

def city_pin(value):
    parts=str(value or '').split('-')
    # City's printed section-township-range differs from OCPA range-township-section.
    if len(parts)==6:
        if [len(p) for p in parts]!=[2,2,2,4,2,3] or not all(p.isdigit() for p in parts):return None
        return parts[2]+parts[1]+parts[0]+''.join(parts[3:])
    digits=''.join(c for c in str(value or '') if c.isdigit())
    return digits if len(digits)==15 else None

def build(root=ROOT):
    active=json.loads((root/'data/processed/active.json').read_text());folder=root/active['relative_path']
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    boundaries={f['id']:shape(f['geometry']) for f in read(root/'data/processed/study_boundaries.geojson')['features']}
    bbox=box(*read(root/'config/study_area.json')['acquisition_bbox_wgs84'])
    project=Transformer.from_crs(4326,32617,always_xy=True).transform
    parks=read(folder/'parks.json')['features'];zones=read(folder/'zoning.json')['features'];parcels=read(folder/'parcels.json')['features']
    parcel_index=collections.defaultdict(list)
    for f in parcels:parcel_index[f['properties']['parcel_id']].append(shape(f['geometry']))
    vacant_path=root/'data/land/city_vacant_rows.json';vacant=read(vacant_path);metadata=read(root/'data/land/city_vacant_metadata.json')
    scoped={}
    for name,boundary in boundaries.items():
        studied=boundary.intersection(bbox);by_code=collections.defaultdict(list)
        for f in zones:
            g=shape(f['geometry']).intersection(studied)
            if not g.is_empty:by_code[f['properties'].get('Zoning') or 'UNKNOWN'].append(transform(project,g))
        rows=[{'zoning_code':code,'clipped_area_m2':round(unary_union(gs).area,2)} for code,gs in sorted(by_code.items())]
        matched=[];unlocated=0
        for r in vacant:
            pin=city_pin(r.get('parcel'));geoms=parcel_index.get(pin,[])
            g=unary_union(geoms) if geoms else shape(r['geocoded_column']) if r.get('geocoded_column') else None
            if g is None:unlocated+=1;continue
            if g.intersects(boundary):matched.append({'property_id':r.get('property_id'),'parcel_id':pin,'address':r.get('address'),'zoning':r.get('zoning'),'status':r.get('status'),'disposition_status':r.get('disposition_status'),'notes':r.get('notes'),'match_method':'exact_parcel_polygon' if geoms else 'publisher_geocoded_point_not_boundary'})
        scoped[name]={'park_records':[f['properties'] for f in parks if shape(f['geometry']).intersects(boundary)],'zoning_area_by_exact_code':rows,'zoning_union_covered_area_m2':round(unary_union([g for gs in by_code.values() for g in gs]).area,2),'scope_area_m2':round(transform(project,boundary).area,2),'extraction_scope_area_m2':round(transform(project,studied).area,2),'city_inventory_matches':matched,'city_inventory_records_without_location_or_local_parcel':unlocated}
    report={'source_snapshot':active['snapshot'],'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'city_inventory_url':'https://data.cityoforlando.net/resource/bkpt-5h2w.json','city_inventory_rows':len(vacant),'city_inventory_rows_updated_utc':datetime.datetime.fromtimestamp(metadata['rowsUpdatedAt'],datetime.timezone.utc).isoformat(),'city_inventory_sha256':hashlib.sha256(vacant_path.read_bytes()).hexdigest(),'scopes':scoped,'limits':['Snapshot parks/zoning cover the extraction, not necessarily the whole neighborhood.','City vacant inventory is not a comprehensive City-owned property register; zero matches do not prove no City-owned land.','Inventory notes may describe housing or constraints; dataset title does not prove present vacancy or availability.','Exact zoning codes retain overlays; district permissions require current code, future land use, PD conditions and site review.','Park/recreation function, tax use, ownership, zoning and redevelopment availability are distinct.']}
    inputs=[folder/(name+'.json') for name in ['parks','zoning','parcels']]+[root/'data/processed/study_boundaries.geojson',root/'config/study_area.json',vacant_path,root/'data/land/city_vacant_metadata.json']
    report['dependencies']={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    out=root/'data/land/land_review.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:{'park_records':len(v['park_records']),'city_inventory_matches':len(v['city_inventory_matches']),'zoning_codes':len(v['zoning_area_by_exact_code'])} for k,v in scoped.items()},indent=2));return report

if __name__=='__main__':build()
