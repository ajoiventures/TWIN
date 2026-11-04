"""Bounded public pedestrian-service discovery; never promotes geometry to accepted scene data."""
from pathlib import Path
import argparse, collections, concurrent.futures, datetime, hashlib, json, os, math
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SAFE_FIELDS = ('OBJECTID','UID','UID_updated','UID_Updated','UID_Updated022226','PAINTED','FADED',
 'Crosswalk_Type','Width','length','PedPlan','SidewalkReq','Orientation',
 'ROADNAME','ROADWAY','SIDEWALK','SURF_WIDTH','SPEED','AADT')
STATUS_FIELDS = ('PAINTED','FADED','PedPlan','SidewalkReq','SIDEWALK')

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, path)

class PublicClient:
    def __init__(self, cache, offline=False):
        self.cache, self.offline = Path(cache), offline
    def get(self, url, params=None):
        target = url + ('?' + urllib.parse.urlencode(params) if params else '')
        host = urllib.parse.urlsplit(target).hostname or ''
        if host.endswith('.cit'):
            raise ValueError('Internal .cit host is not a public data source; no request attempted')
        path = self.cache / (hashlib.sha256(target.encode()).hexdigest() + '.json')
        if self.offline:
            if not path.exists(): raise RuntimeError('Offline cache miss')
            return json.loads(path.read_text(encoding='utf-8'))
        request = urllib.request.Request(target, headers={'User-Agent':'TWIN-pedestrian-discovery/1.0'})
        with urllib.request.urlopen(request, timeout=25) as response:
            value = json.load(response)
        if isinstance(value, dict) and value.get('error'):
            raise ValueError('ArcGIS error: ' + json.dumps(value['error']))
        write_json(path, value)
        return value
    def get_text(self, url):
        host=urllib.parse.urlsplit(url).hostname or ''
        if host.endswith('.cit'):raise ValueError('Internal host not permitted')
        path=self.cache/(hashlib.sha256(url.encode()).hexdigest()+'.text.json')
        if self.offline:
            if not path.exists():raise RuntimeError('Offline text cache miss')
            return json.loads(path.read_text(encoding='utf-8'))['text']
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TWIN-pedestrian-discovery/1.0'}),timeout=25) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('Metadata response too large')
        text=raw.decode('utf-8');write_json(path,{'text':text,'sha256':hashlib.sha256(raw).hexdigest()})
        return text

def query_params(bbox):
    return {'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),
            'geometryType':'esriGeometryEnvelope','inSR':4326,
            'spatialRel':'esriSpatialRelIntersects'}

def normalize_sample(feature, source_id):
    p = feature.get('properties', feature.get('attributes', {}))
    return {'source_id':source_id, 'source_object_id':p.get('OBJECTID'),
            'attributes':{k:p[k] for k in SAFE_FIELDS if k in p},
            'facility_status':'unresolved_source_codes', 'width_unit':None,
            'geometry_acceptance':'reference_only_not_accepted_for_modeling'}

def metadata_definitions(text):
    """Preserve published field descriptions; never manufacture units from XY CRS."""
    root=ET.fromstring(text);result={}
    for attr in root.findall('.//attr'):
        name=attr.findtext('attrlabl')
        if name:result[name.lower()]={'definition':attr.findtext('attrdef'),
             'definition_source':attr.findtext('attrdefs')}
    return result

def valid_candidate_geometry(geometry):
    if not geometry or geometry.get('type') not in ['LineString','MultiLineString']:return False
    lines=[geometry.get('coordinates')] if geometry['type']=='LineString' else geometry.get('coordinates')
    if not isinstance(lines,list) or not lines:return False
    for line in lines:
        if not isinstance(line,list) or len(line)<2:return False
        for position in line:
            if not isinstance(position,list) or len(position)<2:return False
            x,y=position[:2]
            if isinstance(x,bool) or isinstance(y,bool) or not isinstance(x,(int,float)) or not isinstance(y,(int,float)):return False
            if not math.isfinite(x) or not math.isfinite(y) or not(-180<=x<=180 and -90<=y<=90):return False
    return True

def candidate_geometry(source, result, client):
    """Export review-only WGS84 linework; all lifecycle categories stay unresolved."""
    if result.get('public_access') not in ['accessible_with_study_features','accessible_no_study_features']:
        raise ValueError('Candidate source has no validated coverage query')
    features=[];ids=result.get('object_ids',[]);schema={f['name'] for f in result.get('fields',[])}
    safe=[f for f in SAFE_FIELDS if f in schema]
    for start in range(0,len(ids),100):
        batch=ids[start:start+100]
        data=client.get(source['url']+'/query',{'f':'geojson','objectIds':','.join(map(str,batch)),
                   'outFields':','.join(safe),'outSR':4326,'returnGeometry':'true'})
        if data.get('exceededTransferLimit'):raise ValueError('Truncated candidate geometry batch')
        rows=data.get('features',[]);got=[f['properties'].get('OBJECTID') for f in rows]
        if len(got)!=len(batch) or set(got)!=set(batch):raise ValueError('Candidate geometry ID/count mismatch')
        for f in rows:
            if not valid_candidate_geometry(f.get('geometry')):raise ValueError('Invalid WGS84 candidate line geometry')
            row=normalize_sample(f,source['id'])
            features.append({'type':'Feature','id':source['id']+':'+str(row['source_object_id']),
               'geometry':f['geometry'],'properties':{**row,'source_url':source['url'],
               'source_pedplan_code':row['attributes'].get('PedPlan'),'lifecycle_bucket':'unresolved',
               'existing_status':None,'proposed_status':None,'geometry_crs':'EPSG:4326',
               'review_flags':['draft_source','pedplan_meaning_unknown','width_units_unknown','current_condition_unverified']}})
    return {'type':'FeatureCollection','features':features,'source_id':source['id'],
            'scope':'intersects extraction rectangle; not official district membership',
            'accepted_for_modeling':False,'lifecycle_counts':{'existing':0,'proposed':0,'unresolved':len(features)}}

def inspect_dictionary(source, result, client):
    service_url=source['url'].rsplit('/',1)[0];root=client.get(service_url,{'f':'json'})
    layer=client.get(source['url'],{'f':'json'});item_id=root.get('serviceItemId')
    evidence={'service_url':service_url,'service_item_id':item_id,'geometry_xy_unit':root.get('units'),
      'attribute_unit_note':'Service/CRS units describe geometry, not Width or length attribute units.',
      'field_domains':{f['name']:f.get('domain') for f in layer.get('fields',[])},
      'subtypes':[{'id':t.get('id'),'name':t.get('name'),'domains':t.get('domains')} for t in layer.get('types',[])],
      'renderer_values':[{k:v.get(k) for k in ['value','label','description']}
          for v in layer.get('drawingInfo',{}).get('renderer',{}).get('uniqueValueInfos',[])],
      'status_resolution':'unresolved_numeric_labels_only','width_unit':None,'field_dictionary':[]}
    definitions={}
    if item_id:
        item=client.get('https://www.arcgis.com/sharing/rest/content/items/'+item_id,{'f':'json'})
        evidence['item']={k:item.get(k) for k in ['id','owner','title','description','access','modified','licenseInfo','accessInformation']}
        xml_url='https://www.arcgis.com/sharing/rest/content/items/'+item_id+'/info/metadata/metadata.xml'
        try:
            text=client.get_text(xml_url);definitions=metadata_definitions(text)
            evidence['xml_metadata']={'url':xml_url,'sha256':hashlib.sha256(text.encode()).hexdigest(),
                'note':'Published field definitions retained below; XML CRS units alone do not define attribute units.'}
        except Exception as exc:evidence['xml_metadata']={'url':xml_url,'error':str(exc)}
    for field in layer.get('fields',[]):
        name=field['name'];definition=definitions.get(name.lower(),{})
        evidence['field_dictionary'].append({'name':name,'alias':field.get('alias'),
          'source_type':field.get('type'),'nullable':field.get('nullable'),'domain':field.get('domain'),
          'published_definition':definition.get('definition'),'definition_source':definition.get('definition_source'),
          'attribute_unit':None,'safe_values_exported':name in SAFE_FIELDS,
          'interpretation':'raw code; lifecycle semantics unresolved' if name in STATUS_FIELDS else 'source attribute; no added semantic claim'})
    return evidence

def inspect_source(source, bbox, client):
    result = {**source, 'public_access':'unresolved','study_feature_count':None,
              'geometry_accepted':False, 'facility_status':'unresolved',
              'acquisition_date':None, 'width_unit':None, 'sample_rows':[]}
    if source['kind'] == 'internal_reference_not_public':
        result.update(public_access='not_public_not_queried', reason='Internal .cit URL appears in a public web map; not contacted.')
        return result
    try:
        meta = client.get(source['url'], {'f':'json'})
        schema = {f['name']:f for f in meta.get('fields', [])}
        oid = meta.get('objectIdField') or next((f['name'] for f in meta.get('fields',[]) if f.get('type')=='esriFieldTypeOID'), None)
        if not oid: raise ValueError('Missing object ID field')
        result.update(public_access='accessible', layer_name=meta.get('name'),
                      geometry_type=meta.get('geometryType'), spatial_reference=meta.get('extent',{}).get('spatialReference'),
                      description=meta.get('description'), editing_info=meta.get('editingInfo'),
                      fields=[{'name':f['name'],'alias':f.get('alias'),'type':f.get('type'),'domain':f.get('domain')} for f in meta.get('fields',[])])
        params=query_params(bbox)
        count=client.get(source['url']+'/query', {**params,'returnCountOnly':'true'})
        result['study_feature_count']=count['count']
        result['public_access']='accessible_with_study_features' if count['count'] else 'accessible_no_study_features'
        ids=client.get(source['url']+'/query', {**params,'returnIdsOnly':'true'}).get('objectIds') or []
        if len(ids)!=len(set(ids)) or len(ids)!=count['count']:
            raise ValueError('Object ID/count mismatch; source may have changed during discovery')
        result['object_ids']=sorted(ids)
        safe=[f for f in SAFE_FIELDS if f in schema]
        if oid not in safe:safe.insert(0,oid)
        hist={k:collections.Counter() for k in STATUS_FIELDS if k in schema}
        samples=[]
        for start in range(0,len(ids),100):
            batch=ids[start:start+100]
            data=client.get(source['url']+'/query', {'f':'json','objectIds':','.join(map(str,batch)),
                 'outFields':','.join(safe),'returnGeometry':'false'})
            if data.get('exceededTransferLimit'):raise ValueError('Truncated query batch')
            features=data.get('features',[])
            got=[f['attributes'][oid] for f in features]
            if len(got)!=len(batch) or set(got)!=set(batch):raise ValueError('Missing/duplicate feature batch')
            for f in features:
                attrs=f['attributes']
                for k,c in hist.items():c[json.dumps(attrs.get(k),ensure_ascii=False)]+=1
                samples.append(normalize_sample(f,source['id']))
        result['status_counts']={k:dict(c) for k,c in hist.items()}
        result['sample_rows']=sorted(samples,key=lambda r:r['source_object_id'])[:5]
        result['reason']='Accessible candidate only: source status codes, final City adoption, width units and current geometry require confirmation.'
        if source['kind']=='roadway_attributes_not_walkway_edges':
            result['reason']='Roads in RCI description and roadway attributes: not actual sidewalk edge geometry, regardless of layer name.'
        return result
    except Exception as exc:
        result.update(public_access='error_or_incomplete',error=str(exc))
        return result

def run(offline=False):
    config=json.loads((ROOT/'config/pedestrian_sources.json').read_text(encoding='utf-8'))
    client=PublicClient(ROOT/'data/cache/pedestrian_discovery',offline)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(lambda s:inspect_source(s,config['study_bbox_wgs84'],client),config['sources']))
    reference_maps=[]
    for item_id in config['city_reference_maps']:
        try:
            item=client.get('https://www.arcgis.com/sharing/rest/content/items/'+item_id,{'f':'json'})
            content=client.get('https://www.arcgis.com/sharing/rest/content/items/'+item_id+'/data',{'f':'json'})
            linked=[]
            def walk(layers):
                for layer in layers:
                    if layer.get('url'):linked.append({'title':layer.get('title'),'url':layer['url']})
                    walk(layer.get('layers',[]))
            walk(content.get('operationalLayers',[]))
            reference_maps.append({k:item.get(k) for k in ['id','title','owner','orgId','access','modified']}
                                  | {'linked_layers':linked})
        except Exception as exc:reference_maps.append({'id':item_id,'error':str(exc)})
    candidates=None;dictionary=None;candidate_error=None
    selected=next(s for s in config['sources'] if s['id']==config['candidate_geometry_source_id'])
    selected_result=next(r for r in results if r['id']==selected['id'])
    try:
        dictionary=inspect_dictionary(selected,selected_result,client)
        candidates=candidate_geometry(selected,selected_result,client)
    except Exception as exc:candidate_error=str(exc)
    report={'report_created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'offline_cache_replay':offline,'bbox_wgs84':config['study_bbox_wgs84'],'extent_note':config['extent_note'],
      'sources':results,'accepted_geometry_sources':[],
      'unresolved':['Actual sidewalk segment/edge geometry','Curb ramp geometry and construction/status codes',
                    'Crosswalk source authority/currentness/status meanings/width units','Official pilot-block endpoints'],
      'city_reference_maps':reference_maps,'latest_candidate_dictionary':dictionary,
      'candidate_geometry_error':candidate_error,
      'candidate_geometry_summary':{k:candidates.get(k) for k in ['source_id','accepted_for_modeling','lifecycle_counts']} if candidates else None,
      'date_note':'Layer names/modified timestamps are not acquisition dates; offline replay does not establish current source freshness.'}
    suffix='_offline' if offline else ''
    write_json(ROOT/('data/transport/pedestrian_access_report'+suffix+'.json'),report)
    write_json(ROOT/('data/transport/pedestrian_safe_samples'+suffix+'.json'),{r['id']:r['sample_rows'] for r in results})
    if candidates:write_json(ROOT/('data/transport/crosswalk_candidates'+suffix+'.geojson'),candidates)
    if dictionary:write_json(ROOT/('data/transport/crosswalk_field_dictionary'+suffix+'.json'),dictionary)
    print(json.dumps([{k:r.get(k) for k in ['id','public_access','study_feature_count','geometry_accepted','error']} for r in results],indent=2))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true')
    run(parser.parse_args().offline)
