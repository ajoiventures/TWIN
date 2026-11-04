"""Bounded pedestrian source probes; offline replay by default, never scene activation.

Run with project Python: tools/pedestrian_source_evidence.py --live (initial cache)
or without arguments (replay). Public candidate geometry remains unaccepted.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, sys, urllib.request, urllib.parse
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
from shapely.geometry import shape, mapping

OUT = ROOT / 'data/processed/pedestrian_source_evidence'
ITEMS = [
    ('metroplan_crossings', '7689d18e7f8f49d9b0ffb08e57a14e42', [0]),
    ('orlando_task_force', '3a0cc13f4606423ba2e4da700a019920', [0]),
    ('consultant_curb_ramps_geography_check', 'd2277f2ca92b4865b83967525d2df209', []),
    ('consultant_sidewalk_geography_check', 'af1034dd7033443f97f7788114ce6ab7', []),
]
SAFE = {'OBJECTID','ObjectID','FID','GlobalID','UID','PedPlan','Width','length',
        'PAINTED','FADED','ABOVE','EDGEDUP','UID_Updated','Crosswalk_Type','SidewalkReq','ROADNAME','NAME','TYPE',
        'Status','STATUS','Recommendation','RECOMMENDATION','Location','LOCATION'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=True), encoding='utf-8')

class Client:
    def __init__(self, live): self.live, self.receipts = live, []
    def get(self, url, params=None):
        target=url+('?' + urllib.parse.urlencode(params) if params else '')
        key=hashlib.sha256(target.encode()).hexdigest()
        p=OUT/'sources'/(key+'.json'); receipt=p.with_suffix('.receipt.json')
        if not p.exists():
            if not self.live: raise ValueError('Offline source cache missing: '+target)
            req=urllib.request.Request(target, headers={'User-Agent':'TWIN-public-pedestrian-evidence/1'})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw=r.read(12_000_001)
                if len(raw)>12_000_000: raise ValueError('Bounded response limit exceeded')
                final=r.url
            value=json.loads(raw)
            if value.get('error'): raise ValueError(str(value['error']))
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
            dump(receipt, {'url':target,'final_url':final,'sha256':sha(p),
                 'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        rec=json.loads(receipt.read_text())
        if rec['sha256']!=sha(p) or rec['url']!=target: raise ValueError('Source receipt mismatch')
        self.receipts.append({'path':str(p.relative_to(ROOT)).replace('\\','/'), **rec})
        return json.loads(p.read_text(encoding='utf-8'))

def main():
    args=argparse.ArgumentParser(); args.add_argument('--live',action='store_true'); a=args.parse_args()
    client=Client(a.live)
    boundary=ROOT/'data/processed/study_boundaries.geojson'
    scopes={f['properties']['scope']:shape(f['geometry']) for f in json.loads(boundary.read_text())['features']}
    bbox=scopes['neighborhood'].bounds
    city_search=client.get('https://www.arcgis.com/sharing/rest/search', {'f':'json',
        'q':'orgid:mMuoPCaIYD4wEgDl (sidewalk OR ramp OR crosswalk OR ADA)','num':100})
    sources=[]; features=[]
    for name, iid, layer_ids in ITEMS:
        item=client.get('https://www.arcgis.com/sharing/rest/content/items/'+iid, {'f':'json'})
        row={'source_id':name,'item_id':iid,'title':item.get('title'),'item_owner':item.get('owner'),
             'item_modified_unix_ms':item.get('modified'),'source_url':item.get('url'),
             'license_original':item.get('licenseInfo'),'extent_original':item.get('extent'),
             'description_original':item.get('description'), 'attribution_original':item.get('accessInformation'),
             'acquisition_date':None,'effective_date':None,'accuracy_m':None,
             'publisher_verification':'hosting owner preserved; agency endorsement not established by title',
             'layers':[]}
        if not layer_ids: row['disposition']='reject_wrong_geography_metadata_extent'; sources.append(row); continue
        service=client.get(item['url'],{'f':'json'})
        for lid in layer_ids:
            url=item['url']+'/'+str(lid); meta=client.get(url,{'f':'json'})
            params={'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),
                    'geometryType':'esriGeometryEnvelope','inSR':4326,
                    'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'}
            ids=client.get(url+'/query',params).get('objectIds') or []
            oid=meta['objectIdField']; safe=sorted(({f['name'] for f in meta['fields']} & SAFE)|{oid})
            layer={'id':lid,'title':meta['name'],'geometry_type':meta.get('geometryType'),
                   'spatial_reference':meta.get('extent',{}).get('spatialReference'),
                   'layer_updated_unix_ms':meta.get('editingInfo',{}).get('lastEditDate'),
                   'fields':meta['fields'],'safe_preview_fields':safe,'bbox_feature_count':len(ids),
                   'neighborhood_feature_count':0,'main_street_feature_count':0,'first_five':[],
                   'status':'proposed_draft' if 'recommend' in meta['name'].lower() else 'unresolved_lifecycle',
                   'width_units':None,'grade':None,'geometry_acceptance':'review_only'}
            for start in range(0,len(ids),100):
                batch=ids[start:start+100]
                fc=client.get(url+'/query',{'f':'geojson','objectIds':','.join(map(str,batch)),
                     'outFields':','.join(safe),'outSR':4326,'returnGeometry':'true'})
                got=[f['properties'].get(oid) for f in fc.get('features',[])]
                if set(got)!=set(batch) or len(got)!=len(batch) or fc.get('exceededTransferLimit'):
                    raise ValueError('Source feature count/identity mismatch')
                for f in fc['features']:
                    g=shape(f['geometry'])
                    if not g.is_valid: raise ValueError('Invalid source geometry')
                    if not g.intersects(scopes['neighborhood']): continue
                    layer['neighborhood_feature_count']+=1
                    ms=g.intersects(scopes['main_street']); layer['main_street_feature_count']+=int(ms)
                    if len(layer['first_five'])<5: layer['first_five'].append(f['properties'])
                    features.append({'type':'Feature','geometry':mapping(g.intersection(scopes['neighborhood'])),
                        'properties':{'source_id':name,'source_item_id':iid,'layer_id':lid,
                          'source_object_id':f['properties'][oid],'source_attributes':f['properties'],
                          'main_street_intersects':ms,'status':('synthetic_edge_duplicate_not_physical_crossing' if f['properties'].get('EDGEDUP')==1 else layer['status']),'geometry_acceptance':'review_only'}})
            row['layers'].append(layer)
        row['disposition']='review_only_not_accepted_existing_geometry'; sources.append(row)
    packet={'schema':'twin.pedestrian-source-evidence/1','sources':sources,
        'city_public_catalog_search':city_search,
        'coverage_bbox_wgs84':bbox,'coverage_basis':'official College Park neighborhood polygon intersection',
        'dependencies':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [Path(__file__),boundary]},
        'source_receipts':client.receipts,
        'limits':['No sidewalk or ramp inventory acquired by these crossing probes.',
            'Draft recommendations never establish existing crossings.',
            'MetroPlan EDGEDUP=1 marks analytical duplicate points where a crosswalk does not exist; exclude from physical inventory.',
            'MetroPlan point geometry is a crossing reference, never a crossing paint footprint or curb line.',
            'Width units, lifecycle domains and physical positional accuracy remain unresolved.',
            'No curb, grade, tree-well, driveway or obstruction geometry inferred.',
            'Engineering scope/standards are not signed or as-built geometry.']}
    dump(OUT/'candidate_crossings.geojson',{'type':'FeatureCollection','features':features})
    packet['candidate_geometry_sha256']=sha(OUT/'candidate_crossings.geojson')
    dump(OUT/'packet.json',packet)
    print(json.dumps({'packet_sha256':sha(OUT/'packet.json'),'candidate_features':len(features),
          'layers':[(s['source_id'],[(l['title'],l['neighborhood_feature_count'],l['main_street_feature_count']) for l in s['layers']]) for s in sources]}))

if __name__=='__main__': main()
