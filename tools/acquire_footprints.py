"""Expand official footprint coverage while preserving retained source-row order."""
from pathlib import Path
import json,hashlib,sys
from data_pipeline import ROOT,Client,atomic_json,now
URL='https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28'
FIELDS=['OBJECTID','SUBTYPE','TYPE_CODE','PID','BLDG_NUM','FLOOR_NUM','SUB_DESC','BLDG_TYPE']

def acquire():
    bbox=json.loads((ROOT/'config/study_area.json').read_text(encoding='utf-8'))['acquisition_bbox_wgs84'];client=Client(ROOT/'data/cache/footprints')
    meta=client.get(URL,{'f':'json'})
    if set(FIELDS)-{f['name'] for f in meta['fields']}:raise ValueError('Footprint schema changed')
    result=client.get(URL+'/query',{'f':'json','where':'1=1','geometry':','.join(map(str,bbox)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'})
    ids=set(result.get('objectIds') or [])
    if not ids:raise ValueError('No footprint IDs returned; previous coverage preserved')
    path=ROOT/'data/buildings.geojson';old=json.loads(path.read_text(encoding='utf-8'))['features'] if path.exists() else []
    kept=[f for f in old if f['properties']['OBJECTID'] in ids];known={f['properties']['OBJECTID'] for f in kept};missing=sorted(ids-known);new=[]
    for i in range(0,len(missing),50):
        data=client.get(URL+'/query',{'f':'geojson','objectIds':','.join(map(str,missing[i:i+50])),'outFields':','.join(FIELDS),'outSR':4326,'returnGeometry':'true'})
        if data.get('exceededTransferLimit'):raise ValueError('Truncated footprint batch')
        new.extend(data['features']);print('New footprint subareas',len(new),'/',len(missing),flush=True)
    features=kept+sorted(new,key=lambda f:f['properties']['OBJECTID']);received=[f['properties']['OBJECTID'] for f in features]
    if set(received)!=ids or len(received)!=len(ids):raise ValueError('Footprint coverage count mismatch')
    if path.exists():
        backup=ROOT/'data/cache/footprints'/('previous-'+hashlib.sha256(path.read_bytes()).hexdigest()+'.geojson')
        if not backup.exists():backup.write_bytes(path.read_bytes())
    atomic_json(path,{'type':'FeatureCollection','features':features})
    report={'bbox_wgs84':bbox,'source_url':URL,'source_fields':FIELDS,'source_object_count':len(ids),'reused_existing_source_rows':len(kept),'new_source_rows':len(new),'removed_source_rows':len(old)-len(kept),'source_updated':meta.get('editingInfo',{}).get('lastEditDate'),'created_utc':now(),'requests':client.accesses,'reused_source_retrieval_time':None,'reuse_note':'Existing source rows preserve earlier geometry; original legacy fetch times unknown. Acquisition extent and source-ID completeness were checked now.','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    atomic_json(ROOT/'data/footprint_manifest.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['requests','source_fields']},indent=2));return report

if __name__=='__main__':acquire()
