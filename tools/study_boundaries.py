"""Official, separate College Park neighborhood and Main Street reference polygons."""
from data_pipeline import ROOT,Client,atomic_json
import json,hashlib,argparse,datetime
from shapely.geometry import shape,mapping,box
from shapely.ops import transform
from shapely.affinity import translate
from pyproj import Transformer
GIS='https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/'
SOURCES={
 'main_street':{'url':GIS+'OrlandoMainStreetProgram/FeatureServer/0','where':"BUISNESSNE='College Park'",'fields':['OBJECTID','BUISNESSNE','GlobalID'],'item':'ed1b7be7058549aeb78444eb0dc517cc'},
 'neighborhood':{'url':GIS+'OrlandoPoliticalNeighborhoods/FeatureServer/0','where':"NeighborhoodName='College Park'",'fields':['Object_ID','NeighborhoodName','NeighborhoodID','GlobalID'],'item':'b1ad1f3447af4451adaacb9007741a20'}}

def memberships(geometry,main,neighborhood):
    p=geometry.representative_point()
    return {'main_street_member':main.covers(p),'college_park_neighborhood_member':neighborhood.covers(p),'membership_method':'representative_point; separate scopes, not nested'}

def build(offline=False):
    c=Client(ROOT/'data/cache/boundaries',offline=offline);features=[];evidence=[]
    for key,source in SOURCES.items():
        meta=c.get(source['url'],{'f':'json'});item=c.get('https://www.arcgis.com/sharing/rest/content/items/'+source['item'],{'f':'json'})
        fields={f['name'] for f in meta['fields']}
        if set(source['fields'])-fields:raise ValueError('Boundary schema changed')
        data=c.get(source['url']+'/query',{'f':'geojson','where':source['where'],'outFields':','.join(source['fields']),'outSR':4326,'returnGeometry':'true'})
        if len(data.get('features',[]))!=1 or data.get('exceededTransferLimit'):raise ValueError('Expected exactly one full College Park boundary')
        f=data['features'][0];g=shape(f['geometry'])
        if not g.is_valid or g.is_empty or g.geom_type not in ['Polygon','MultiPolygon']:raise ValueError('Invalid boundary')
        source_props=f['properties'];features.append({'type':'Feature','id':key,'properties':{'scope':key,'name':'College Park Main Street' if key=='main_street' else 'College Park neighborhood','source_url':source['url'],'source_item_id':source['item'],'source_feature_ids':source_props,'publisher':'City of Orlando','item_owner':item.get('owner'),'item_access':item.get('access'),'item_modified_unix_ms':item.get('modified'),'layer_last_edit_unix_ms':meta.get('editingInfo',{}).get('lastEditDate'),'effective_date':None,'quality':'official reference polygon; not surveyed legal boundary'},'geometry':mapping(g)})
        evidence.append({'scope':key,'query_without_bbox':True,'response_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'source_native_crs':meta.get('extent',{}).get('spatialReference'),'source_units':meta.get('units'),'terms':meta.get('copyrightText'),'item_license':item.get('licenseInfo')})
    geoms={f['id']:shape(f['geometry']) for f in features};project=Transformer.from_crs(4326,32617,always_xy=True).transform;main=transform(project,geoms['main_street']);neigh=transform(project,geoms['neighborhood'])
    active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'));folder=ROOT/active['relative_path'];quality=json.loads((folder/'quality.json').read_text(encoding='utf-8'));extent=transform(project,box(*quality['bbox_wgs84']))
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'areas_m2':{'main_street':main.area,'neighborhood':neigh.area,'main_street_outside_neighborhood':main.difference(neigh).area},'existing_extraction_coverage':{k:{'area_fraction':transform(project,g).intersection(extent).area/transform(project,g).area,'complete':extent.covers(transform(project,g))} for k,g in geoms.items()},'full_bounds_wgs84':{k:list(g.bounds) for k,g in geoms.items()},'policy':{'primary_detail_scope':'main_street','context_scope':'neighborhood','combined_scope':'union, never discard Main Street portions outside neighborhood','source_geometry_extent':'current rectangular extraction; full district coverage not yet built'},'evidence':evidence,'request_provenance':c.accesses}
    if (ROOT/'scene/college_park.usda').exists():
        from pxr import Usd
        from constrain_scene import ground_footprint
        origin=project(-81.389,28.572);ground=translate(ground_footprint(Usd.Stage.Open(str(ROOT/'scene/college_park.usda'))),origin[0],origin[1])
        report['actual_3d_ground_coverage']={k:{'area_fraction':transform(project,g).intersection(ground).area/transform(project,g).area,'uncovered_area_m2':transform(project,g).difference(ground).area,'complete':ground.covers(transform(project,g))} for k,g in geoms.items()}
        report['base_geometry_sha256']=hashlib.sha256((ROOT/'scene/college_park.usda').read_bytes()).hexdigest()
        report['policy']['source_geometry_extent']='expanded rectangular extraction fully containing Main Street; neighborhood context remains partial' if report['actual_3d_ground_coverage']['main_street']['complete'] else 'incomplete Main Street ground coverage'
    atomic_json(ROOT/'data/processed/study_boundaries.geojson',{'type':'FeatureCollection','features':features,'provenance':report})
    atomic_json(ROOT/'data/processed/study_scope_quality.json',report)
    print(json.dumps({k:report[k] for k in ['areas_m2','existing_extraction_coverage','full_bounds_wgs84','policy']},indent=2));return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');build(p.parse_args().offline)
