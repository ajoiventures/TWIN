"""Bounded cached LYNX static GIS packet; no GTFS calendar or realtime inference."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
import argparse,collections,datetime,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
import shapely
from shapely.geometry import shape,mapping,box
from pyproj import Transformer
from data_pipeline import Client,arcgis,atomic_json,now

def utc(milliseconds):
    return datetime.datetime.fromtimestamp(milliseconds/1000,datetime.timezone.utc).isoformat() if isinstance(milliseconds,(int,float)) else None

def build(root=ROOT,offline=False,force=False):
    config=json.loads((root/'config/transit_sources.json').read_text());study=json.loads((root/'config/study_area.json').read_text());bbox=study['acquisition_bbox_wgs84'];area=box(*bbox)
    client=Client(root/'data/cache/transit',offline=offline,refresh=force);collections_out={};sources={};checks={}
    for name,source in config['sources'].items():
        collection,metadata=arcgis(client,source,bbox);features=[];rejects=[];outside=0
        for feature in collection['features']:
            try:geometry=shapely.force_2d(shape(feature.get('geometry')))
            except (ValueError,TypeError,KeyError):geometry=None
            properties={field:feature['properties'].get(field) for field in source['fields']}
            if geometry is None or not geometry.is_valid or geometry.is_empty:
                rejects.append({'source_object_id':properties['OBJECTID'],'reason':'invalid_or_empty_geometry'});continue
            if not geometry.intersects(area):outside+=1;continue
            if geometry.geom_type not in (('Point','MultiPoint') if name=='stops' else ('LineString','MultiLineString')):raise ValueError('Unexpected transit geometry type')
            features.append({'type':'Feature','id':'lynx:'+name+':'+str(properties['OBJECTID']),
                'properties':{'source_object_id':properties['OBJECTID'],'provider':config['publisher'],'geometry_quality':'published_static_GIS_not_survey_or_current_service_validation',**properties},'geometry':mapping(geometry)})
        ids=[f['properties']['source_object_id'] for f in features]
        if len(ids)!=len(set(ids)):raise ValueError('Duplicate provider OBJECTID')
        collections_out[name]={'type':'FeatureCollection','features':features}
        accesses=[entry for entry in client.accesses if entry['url'].split('?')[0] in (source['url'],source['url']+'/query')]
        times=[entry.get('retrieved_utc') for entry in accesses if entry.get('retrieved_utc')]
        fields=[{'name':f['name'],'alias':f.get('alias'),'type':f.get('type'),'coded_domain':f.get('domain')} for f in metadata['fields'] if f['name'] in source['fields']]
        sources[name]={'api_url':source['url'],'layer_name':metadata.get('name'),'publisher':config['publisher'],'layer_data_last_edit_utc':utc(metadata.get('editingInfo',{}).get('dataLastEditDate')),
            'layer_schema_last_edit_utc':utc(metadata.get('editingInfo',{}).get('schemaLastEditDate')),'observation_acquisition_date':None,
            'request_retrieval_range_utc':[min(times),max(times)] if times else None,'request_receipts':accesses,
            'fields':fields,'native_spatial_reference':metadata.get('extent',{}).get('spatialReference'),'output_crs':'EPSG:4326',
            'copyright':metadata.get('copyrightText'),'redistribution_license':'not_established_from_service_access','source_codes_interpreted':False}
        checks[name]={'source_returned':len(collection['features']),'in_study_features':len(features),'outside_actual_extent':outside,'geometry_rejects':rejects,'unique_object_ids':len(set(ids))}
    # Retain route and stop records independently, including repeated StopId or
    # same-coordinate records. Their provider OBJECTIDs remain the row keys.
    stop_ids=collections.Counter(str(f['properties'].get('StopId')) for f in collections_out['stops']['features'] if f['properties'].get('StopId') is not None)
    active=json.loads((root/'data/processed/active.json').read_text());folder=root/active['relative_path']
    projection=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=projection.transform(*study['local_origin_wgs84'])
    def local(x,y):a,b=projection.transform(x,y);return a-ox,b-oy
    def display(collection):
        output=[]
        for feature in collection['features']:
            geometry=shapely.force_2d(shape(feature['geometry'])).intersection(area)
            if geometry.is_empty:continue
            output.append({**feature,'geometry':mapping(shapely.transform(geometry,local,interleaved=False))})
        return {'type':'FeatureCollection','features':output}
    streets=json.loads((folder/'streets.json').read_text());boundaries=json.loads((root/'data/processed/study_boundaries.geojson').read_text())
    codes={field:{'interpretation':'source_coded_value_only','units':None,'ada_acceptance':False} for field in ('SdwlkPresn','SdwlkWdth','SdwlkConn','CrbCtsNear')}
    packet={'schema':'twin.transit-static/1.0','source_snapshot':active['snapshot'],'built_utc':now(),'offline_cache_replay':offline,'study_bbox_wgs84':bbox,
        'official_download_page':config['official_download_page'],'official_gis_group':config['official_gis_group'],'sources':sources,
        'stops':collections_out['stops'],'routes':collections_out['routes'],'quality':checks,'repeated_stop_id_groups':{k:n for k,n in stop_ids.items() if n>1},
        'stop_record_semantics':'Provider inventory rows; repeated StopId/coordinates may encode route/direction contexts, not duplicate physical poles.',
        'source_coded_pedestrian_fields':codes,'calendars':{'available':False,'reason':config['gtfs']['status'],'endpoint':config['gtfs']['url'],'probe_time_utc':config['gtfs']['probe_time_utc']},
        'realtime':{'available':False,'vehicle_positions':False,'arrivals':False},
        'display':{'map_crs':'EPSG:32617 local origin subtracted','local_origin_wgs84':study['local_origin_wgs84'],'bounds':list(shapely.transform(area,local,interleaved=False).bounds),
            'stops':display(collections_out['stops']),'routes':display(collections_out['routes']),'streets':display(streets),
            'main_street':display({'features':[f for f in boundaries['features'] if f['id']=='main_street']})},
        'limits':['Static GIS provider publication, not accepted present-day operations. April2026 layer label and later data edit dates do not establish stop observation dates.','Sidewalk presence/width/connectivity/curb codes have unresolved semantics/units; not sidewalk geometry or ADA compliance.','Original provider geometries retained in stops/routes. Display geometries alone are clipped to the study frame.','No demographics, AdminNotes, contacts or image pixels requested or included. No active3D scene changes.']}
    out=root/'data/transport';out.mkdir(parents=True,exist_ok=True);atomic_json(out/'lynx_transit.json',packet)
    atomic_json(out/'lynx_transit_first_five.json',{'source_snapshot':active['snapshot'],'stops_fields':config['sources']['stops']['fields'],'stops':[f['properties'] for f in collections_out['stops']['features'][:5]],'route_fields':config['sources']['routes']['fields'],'routes':[f['properties'] for f in collections_out['routes']['features'][:5]]})
    print(json.dumps({'output':str(out/'lynx_transit.json'),'source_snapshot':active['snapshot'],'quality':checks,'repeated_stop_id_groups':packet['repeated_stop_id_groups'],'source_dates':{n:s['layer_data_last_edit_utc'] for n,s in sources.items()},'calendars_available':False,'realtime_available':False},indent=2));return packet

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--force',action='store_true');args=parser.parse_args();build(offline=args.offline,force=args.force)
