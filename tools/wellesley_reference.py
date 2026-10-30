"""Independent historical Wellesley height reference and shape-review evidence only."""
from pathlib import Path
import argparse, collections, hashlib, json, subprocess, sys, urllib.request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from imagery_reference import Client,write_json,read_json,pixel_resolution,stamp

PDF_URL='https://metroplanorlando.gov/wp-content/uploads/2040-LRTP-TR1-Sustainable-Land-Use-Forecast.pdf'
OLD_PIN='292214147406110'
SERVICE='https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer'

def reported_height():
    return {'value_feet':75,'converted_m':75*.3048,'reported_stories':7,
      'quality':'historical_planning_reported_nominal_height_not_surveyed',
      'scope':'Identified Wellesley Condos at 2305 Edgewater; not every condo parcel or roof zone',
      'pdf_physical_page':62,'printed_page':'B-7','figure':'B-5',
      'reported_label':'Building Size: 7 stories, 75 ft tall',
      'whole_footprint_uniform_height_approved':False}

def floor_union_evidence(rows,parcel_by_id,projection):
    from shapely.geometry import shape,mapping
    from shapely import transform
    from shapely.ops import unary_union
    groups=collections.defaultdict(list)
    for row in rows:
        feature=parcel_by_id.get(row['PARCEL'])
        if not feature:raise ValueError('Condo source parcel missing: '+row['PARCEL'])
        groups[str(row.get('FLOOR_NO'))].append(feature)
    results=[]
    for floor,features in sorted(groups.items()):
        union=unary_union([shape(f['geometry']) for f in features]);local=transform(union,projection.transform,interleaved=False)
        results.append({'type':'Feature','geometry':mapping(union),'properties':{
          'source_unit_floor_no':floor,'source_record_count':len(features),'projected_union_area_m2':round(local.area,2),
          'meaning':'Tax/unit geometry union; not an accepted architectural floor plate or roof zone',
          'accepted_for_uniform_extrusion':False}})
    return results

def build(root=ROOT,offline=False):
    from pypdf import PdfReader
    from shapely.geometry import shape,mapping
    from shapely import transform
    from shapely.ops import unary_union
    from pyproj import Transformer
    out=root/'data/imagery/wellesley';out.mkdir(parents=True,exist_ok=True)
    pdf=out/'metroplan_2040_tr1.pdf'
    if not pdf.exists():
        if offline:raise RuntimeError('Offline PDF missing')
        with urllib.request.urlopen(PDF_URL,timeout=30) as response:pdf.write_bytes(response.read(20*1024*1024))
    reader=PdfReader(pdf);cover=reader.pages[0].extract_text();table=reader.pages[56].extract_text()
    if 'January 2016' not in cover or 'Wellesley' not in table or '2305 Edgewater' not in table:
        raise ValueError('Expected primary-document identity/date/table not found; review changed PDF')
    page=out/'figure_page62.png'
    if not page.exists():subprocess.run(['pdftoppm','-f','62','-l','62','-scale-to','1600','-png','-singlefile',str(pdf),str(out/'figure_page62')],check=True,capture_output=True)
    pointer=read_json(root/'data/processed/active.json');folder=(root/pointer['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Snapshot escaped expected path')
    parcels=read_json(folder/'parcels.json')['features'];by={f['properties']['parcel_id']:f for f in parcels}
    audit=read_json(root/'data/heights/storey_audit.json')
    if audit['source_snapshot']!=pointer['snapshot']:raise ValueError('Storey audit and active snapshot differ')
    condo_rows=audit['wellesley']['safe_property_rows'];projection=Transformer.from_crs(4326,32617,always_xy=True)
    unit_union=unary_union([shape(by[r['PARCEL']]['geometry']) for r in condo_rows])
    family=[f for f in parcels if f['properties']['parcel_id'].startswith('2922149132')]
    context=unary_union([shape(f['geometry']) for f in family])
    # Geographic padding is only framing, never a building/ROW boundary.
    bbox=context.bounds;b=[bbox[0]-.00020,bbox[1]-.00018,bbox[2]+.00020,bbox[3]+.00018]
    raw=read_json(root/'data/buildings.geojson')['features'];old=[f for f in raw if str(f['properties'].get('PID'))==OLD_PIN and str(f['properties'].get('BLDG_NUM'))=='1']
    old_union=unary_union([shape(f['geometry']) for f in old]);old_m=transform(old_union,projection.transform,interleaved=False)
    unit_m=transform(unit_union,projection.transform,interleaved=False)
    groups=floor_union_evidence(condo_rows,by,projection)
    to=Transformer.from_crs(4326,2236,always_xy=True);a=to.transform(b[0],b[1]);z=to.transform(b[2],b[3])
    client=Client(out/'cache',offline,False);meta=client.json(SERVICE,{'f':'json'});item=client.json(SERVICE+'/info/iteminfo',{'f':'json'})
    dest=out/'wellesley2025.jpg';prior=out/'reference_evidence.json'
    if offline:
        previous=read_json(prior)
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=previous['aerial']['image']['sha256']:raise ValueError('Preview checksum mismatch')
        aerial=previous['aerial']
    else:
        export=client.json(SERVICE+'/export',{'f':'json','bbox':','.join(map(str,[*a,*z])),'bboxSR':2236,'imageSR':2236,'size':'1280,960','format':'jpg','transparent':'false'},force_live=True)
        aerial={'source_url':SERVICE,'item_metadata_url':SERVICE+'/info/iteminfo?f=json','acquisition_month':'2025-01',
          'date_evidence':item['data']['snippet'],'exact_capture_day':None,'native_gsd_m':None,
          'image':client.image(export['data']['href'],dest),'export_extent':export['data']['extent'],
          'export_sampling':pixel_resolution(export['data']),'reuse_status':'Public reference export observed; redistribution/AI eligibility unestablished',
          'source_licenseInfo':item['data'].get('licenseInfo'),'preview_path':dest.relative_to(root).as_posix()}
    heights=read_json(root/'data/heights/building_heights.json');current=next(h for h in heights if h['building_id']=='Building_2933')
    evidence={'created_utc':stamp(),'offline':offline,'snapshot':pointer['snapshot'],'height_reference':reported_height(),
      'document':{'url':PDF_URL,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'bytes':pdf.stat().st_size,
        'physical_pages':len(reader.pages),'cover_publication':'Final Adopted Plan, January 2016',
        'appendix_context':'Appendix B reproduces prior density examples; figure footer says Technical Report #3 though cover is Technical Report #1',
        'figure_verification':'Figure text is embedded raster; manually verified on rendered physical page62, printedB-7.',
        'independent_table_reference':'Physical page57, printedB-2 TableB1 identifies Wellesley Condo2305Edgewater and7stories'},
      'current_height_record':{k:current.get(k) for k in ['building_id','parcel_id','height_m','method','quality','floors_used','source_snapshot']},
      'aerial':aerial,'shape_evidence':{'old_source_pid':OLD_PIN,'old_building_number':'1','old_subarea_ids':[f['properties']['OBJECTID'] for f in old],
         'old_subarea_count':len(old),'old_union_area_m2':round(old_m.area,2),'old_union_bounds_wgs84':list(old_union.bounds),
         'address_linked_condo_records':len(condo_rows),'tax_union_area_m2':round(unit_m.area,2),'tax_union_bounds_wgs84':list(unit_union.bounds),
         'tax_area_outside_old_footprint_m2':round(unit_m.difference(old_m).area,2),
         'warning':'Tax union includes common/courtyard/land envelope. Its difference is not measured missing roof area.',
         'shape_acceptance':'Incomplete old component representation; new architectural roof zones require aerial/LiDAR/reference alignment. No new footprint accepted.'},
      'source_floor_groups':[f['properties'] for f in groups],
      'limits':['75ft is a historical planning reference, not a current survey or independent vertical datum.',
          'Do not extrude the full condo parcel union at7stories or convert every FLOOR_NO into whole-building stories.',
          'Current aerial shows a multiwing roof and courtyard with separate eastern blocks; lower roof/deck/garage heights remain unresolved.',
          'No scene, height layer or parcel link is changed by this helper.']}
    geometry={'type':'FeatureCollection','features':[
      {'type':'Feature','geometry':mapping(old_union),'properties':{'role':'old_source_subareas','source_pid':OLD_PIN,'accepted_current_roof':False}},
      {'type':'Feature','geometry':mapping(unit_union),'properties':{'role':'address_tax_parcel_union_not_roof','accepted_current_roof':False}},*groups]}
    suffix='_offline' if offline else ''
    write_json(out/('reference_evidence'+suffix+'.json'),evidence);write_json(out/('shape_candidates'+suffix+'.geojson'),geometry)
    print(json.dumps({'height_reference':evidence['height_reference'],'shape_evidence':evidence['shape_evidence']},indent=2));return evidence

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');build(offline=parser.parse_args().offline)
