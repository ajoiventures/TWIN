"""Primary parcel/address/photo evidence for two displaced Princeton sketch groups."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,os,sys,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from imagery_reference import image_statistics
PROPERTY_FIELDS='OBJECTID,PARCEL,SITUS,PROP_NAME,STYS,FLOOR_NO,DOR_CODE,BLDG_DOR_CODE,GROSS_AREA,LIVING_AREA,AYB,EYB,CONDO_FLAG,PARENT_ID,LATITUDE,LONGITUDE,ACREAGE'
FOOTPRINT_FIELDS='OBJECTID,PID,PID_BLDG,BLDG_NUM,FLOOR_NUM,SUBAREA,SUB_DESC,AREA_FT,SKETCH_DT,PULL_DT,X_COORD,Y_COORD'
ADDRESS_FIELDS='OBJECTID,PID,ADDR_FULL,STR_NUM,PRE_DIR,STR_NAME,POST_TYPE,UNIT_TYPE,UNIT_NUM,SOURCE,STATUS'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
class Client:
    def __init__(self,cache,offline=False):self.cache,self.offline=cache,offline
    def json(self,url,params):
        target=url+'?'+urllib.parse.urlencode(params)
        if urllib.parse.urlsplit(target).hostname!='vgispublic.ocpafl.org':raise ValueError('Public OCPA GIS host only')
        path=self.cache/(hashlib.sha256(target.encode()).hexdigest()+'.json')
        if self.offline:
            if not path.exists():raise RuntimeError('Offline reference cache miss')
            return read(path)
        with urllib.request.urlopen(target,timeout=25) as response:raw=response.read(3*1024*1024+1)
        if len(raw)>3*1024*1024:raise ValueError('Response too large')
        data=json.loads(raw)
        if data.get('error'):raise ValueError('ArcGIS source error')
        result={'url':target,'retrieved_utc':now(),'sha256':hashlib.sha256(raw).hexdigest(),'data':data};write(path,result);return result

def area_reconciliation(parts,property_row):
    areas=collections.Counter()
    for f in parts:
        p=f['properties'];areas[p['SUBAREA']]+=p.get('AREA_FT') or 0
    living=areas.get('BAS',0)+areas.get('FUS',0)
    return {'source_subarea_area_ft2':dict(areas),'bas_plus_fus_ft2':living,
       'reported_living_area_ft2':property_row.get('LIVING_AREA'),
       'living_area_matches_bas_plus_fus':living==property_row.get('LIVING_AREA'),
       'sum_subareas_ft2':sum(areas.values()),'reported_gross_area_ft2':property_row.get('GROSS_AREA'),
       'all_floor_num_values':sorted({str(f['properties'].get('FLOOR_NUM')) for f in parts}),
       'interpretation':'FUS is explicitly described as upper story while FLOOR_NUM remains1; not a whole-building storey count or instruction to uniformly extrude.'}

def build(root=ROOT,offline=False):
    from shapely.geometry import shape,Point
    from shapely.ops import unary_union
    from shapely import transform
    from pyproj import Transformer
    config=read(root/'config/princeton_identity_sources.json');out=root/'data/imagery/princeton_parcel_review';client=Client(out/'cache',offline)
    pins=[s['parcel_id'] for s in config['subjects']]+config['confounder_parcels'];where="PARCEL IN ("+','.join("'"+p+"'" for p in pins)+')'
    prop=client.json(config['property_service']+'/query',{'f':'json','where':where,'outFields':PROPERTY_FIELDS,'returnGeometry':'false'})
    native=client.json(config['footprint_service'],{'f':'json'})
    native_sr=native['data'].get('extent',{}).get('spatialReference',{})
    if native_sr.get('latestWkid',native_sr.get('wkid')) not in [2236,102658]:raise ValueError('Native sketch CRS changed; reference point units require review')
    footprint=client.json(config['footprint_service']+'/query',{'f':'geojson','where':where.replace('PARCEL','PID'),'outFields':FOOTPRINT_FIELDS,'outSR':4326,'returnGeometry':'true'})
    addr=client.json(config['address_service']+'/query',{'f':'geojson','where':where.replace('PARCEL','PID'),'outFields':ADDRESS_FIELDS,'outSR':4326,'returnGeometry':'true'})
    pointer=read(root/'data/processed/active.json');folder=(root/pointer['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Invalid snapshot pointer')
    parcels=read(folder/'parcels.json')['features'];by={f['properties']['parcel_id']:f for f in parcels}
    properties={f['attributes']['PARCEL']:f['attributes'] for f in prop['data']['features']};projection=Transformer.from_crs(4326,32617,always_xy=True)
    subjects=[]
    for spec in config['subjects']:
        pin=spec['parcel_id'];p=properties[pin]
        if p['SITUS']!=spec['expected_situs']:raise ValueError('Subject situs changed; review before applying fixed visual annotations')
        parts=[f for f in footprint['data']['features'] if f['properties']['PID']==pin];g=unary_union([shape(f['geometry']) for f in parts]);local=transform(g,projection.transform,interleaved=False)
        parcel=shape(by[pin]['geometry']);parcel_m=transform(parcel,projection.transform,interleaved=False)
        addresses=[f for f in addr['data']['features'] if f['properties']['PID']==pin]
        anchors=[]
        for row in { (f['properties']['X_COORD'],f['properties']['Y_COORD']) for f in parts }:
            lon,lat=Transformer.from_crs(2236,4326,always_xy=True).transform(*row)
            a=Point(*projection.transform(lon,lat));b=Point(*projection.transform(p['LONGITUDE'],p['LATITUDE']))
            anchors.append({'source_xy_epsg2236':list(row),'transformed_wgs84':[lon,lat],'distance_to_property_latlon_m':round(a.distance(b),6),
               'note':'Source reference point, not an approved translation vector or surveyed building center.'})
        photo=out/(pin+'_photo.jpg');photo_url=config['photo_template'].format(parcel_id=pin)
        if not offline:
            with urllib.request.urlopen(photo_url,timeout=25) as response:raw=response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError('Property reference image too large')
            image_statistics(raw);photo.write_bytes(raw)
        elif not photo.exists():raise RuntimeError('Offline property photo missing')
        subjects.append({'parcel_id':pin,'safe_property':p,'source_address_points':addresses,
            'address_points_inside_subject_parcel':all(parcel.covers(shape(f['geometry'])) for f in addresses),
            'subarea_records':[{**f['properties'],'sketch_date_utc':datetime.datetime.fromtimestamp(f['properties']['SKETCH_DT']/1000,datetime.timezone.utc).isoformat(),
              'pull_date_utc':datetime.datetime.fromtimestamp(f['properties']['PULL_DT']/1000,datetime.timezone.utc).isoformat()} for f in parts],
            'legacy_geometry':{'area_m2':round(local.area,3),'own_parcel_overlap_fraction':round(local.intersection(parcel_m).area/local.area,6),
                'centroid_distance_to_parcel_centroid_m':round(local.centroid.distance(parcel_m.centroid),3),
                'geographic_bounds':list(g.bounds),'geometry_accepted':False,'automatic_translation_allowed':False},
            'reference_points':anchors,'area_reconciliation':area_reconciliation(parts,p),
            'official_photo':{'url':photo_url,'path':photo.relative_to(root).as_posix(),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),
               'caption_capture_date':spec['observed_photo_caption_date'],'capture_date_basis':'manual read of source image caption',
               'visual_review':spec['photo_visual_review'],'two_storey_front_facade_observed':spec['two_storey_front_facade_observed'],
               'reuse_status':config['reuse_policy']},'promotion_status':'identity evidence only; no geometry, match or height changes'})
    result={'created_utc':now(),'offline':offline,'source_snapshot':pointer['snapshot'],'subjects':subjects,
      'request_receipts':[{k:r[k] for k in ['url','retrieved_utc','sha256']} for r in [prop,footprint,addr,native]],
      'source_native_crs':native_sr,
      'photo_endpoint_discovery':config['photo_endpoint_discovery'],
      'sketch_access_note':'Observed GetPIDSketch public requests for both subjects returned404; no authentication or bypass attempted.',
      'limits':['Address points support alias/parcel identity, not measured roof geometry or current occupancy.',
          'Do not promote high-overlap church/Harvard geometry to these identities.',
          'Do not convert STYS2 or FLOOR_NUM1 into uniform whole-mass heights; verify partial upper-story zones.',
          'Property photos and2025aerial are historical; source image reproduction/ML eligibility is not established.']}
    suffix='_offline' if offline else '';write(out/('identity_evidence'+suffix+'.json'),result)
    print(json.dumps([{'parcel_id':r['parcel_id'],'addresses':[f['properties']['ADDR_FULL'] for f in r['source_address_points']],
         'geometry':r['legacy_geometry'],'areas':r['area_reconciliation']} for r in subjects],indent=2));return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');build(offline=parser.parse_args().offline)
