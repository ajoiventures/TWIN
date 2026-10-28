"""Acquire bounded historical LiDAR for two missing institutional/office sites."""
from pathlib import Path
import argparse,collections,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np
from shapely.geometry import shape
from princeton_evidence import read_points
from data_pipeline import Client,atomic_json,now

SITES=[('college_park_post_office','292223149200010'),('andersen_office_1615','292223016600090')]
FOOTPRINT='https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28/query'

def build(live=False):
    active=json.loads((ROOT/'data/processed/active.json').read_text());parcels=json.loads((ROOT/active['relative_path']/'parcels.json').read_text())['features']
    config=json.loads((ROOT/'config/princeton_sources.json').read_text());client=Client(ROOT/'data/cache/landmark_footprints',offline=not live);records=[]
    for name,pin in SITES:
        feature=next(f for f in parcels if f['properties']['parcel_id']==pin)
        footprint=client.get(FOOTPRINT,{'f':'geojson','where':"PID = '"+pin+"'",'outFields':'OBJECTID,PID,BLDG_NUM,FLOOR_NUM,SUB_DESC','outSR':4326,'returnGeometry':'true'})
        if footprint.get('error') or footprint.get('exceededTransferLimit'):raise ValueError('Unreliable footprint response')
        points,receipt=read_points(config,shape(feature['geometry']),ROOT,live)
        out=ROOT/'data/heights/landmarks'/name;out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'points.npz',points=points)
        ground=points[points[:,3]==2,2];buildings=points[points[:,3]==6,2]
        report={'site_id':name,'parcel_id':pin,'site_address':feature['properties']['site_address'],'source_snapshot':active['snapshot'],'created_utc':now(),'ocpa_footprint_features':len(footprint.get('features',[])),'point_count':len(points),'classification_counts':{str(int(k)):int(v) for k,v in zip(*np.unique(points[:,3],return_counts=True))},'ground_median_navd88_m':float(np.median(ground)) if len(ground) else None,'classified_building_z_p10_p50_p90_m':np.percentile(buildings,[10,50,90]).tolist() if len(buildings) else None,'cloud_sha256':hashlib.sha256((out/'points.npz').read_bytes()).hexdigest(),'source':receipt,'ocpa_requests':client.accesses.copy(),'geometry_activated':False,'limits':['Historical 2018–2019 source; current shape/occupancy and local flight date unverified.','Parcel is search boundary, not building footprint. Classification and roof/ground interpretation require review.']}
        atomic_json(out/'evidence.json',report);records.append({k:v for k,v in report.items() if k not in ['source','ocpa_requests','limits']})
    print(json.dumps(records,indent=2));return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--live',action='store_true');build(p.parse_args().live)
