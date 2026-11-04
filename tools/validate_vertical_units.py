from data_pipeline import ROOT,Client,atomic_json
import sys,json
sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
points=np.load(ROOT/'data/heights/pilot_points.npz')['points'];g=points[points[:,3]==2];tree=cKDTree(g[:,:2]);project=Transformer.from_crs(4326,3857,always_xy=True);client=Client(ROOT/'data/cache/heights');rows=[]
for lon,lat in [(-81.389,28.572),(-81.390,28.571),(-81.388,28.573)]:
 distances,ids=tree.query(project.transform(lon,lat),k=30);z=float(np.median(g[ids[distances<=3],2]))
 data=client.get('https://epqs.nationalmap.gov/v1/json',{'x':lon,'y':lat,'units':'Meters','wkid':4326,'includeDate':'false'})
 value=float(data['value']);rows.append({'lon':lon,'lat':lat,'ept_ground_z':z,'epqs_ground_m':value,'difference_if_meters':abs(z-value),'difference_if_us_feet':abs(z*1200/3937-value),'epqs_source':data.get('attributes',{})})
meter_error=float(np.median([r['difference_if_meters'] for r in rows]));foot_error=float(np.median([r['difference_if_us_feet'] for r in rows]));valid=meter_error<2 and foot_error>10
report={'samples':rows,'ept_z_unit':'meters' if valid else 'unresolved','accepted':valid,'meter_hypothesis_median_error_m':meter_error,'foot_hypothesis_median_error_m':foot_error,'note':'Original source project used US survey feet; EPT has been transformed. Unit acceptance requires independent ground-elevation agreement. This is a unit sanity check, not a surveyed accuracy test.'}
atomic_json(ROOT/'data/heights/vertical_unit_check.json',report);print(json.dumps(report,indent=2))
if not valid:raise SystemExit('Vertical units are unresolved; no LiDAR heights will be applied')
