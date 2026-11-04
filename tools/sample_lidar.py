"""Read only the EPT nodes intersecting a pilot area, not the county point cloud."""
from data_pipeline import ROOT,Client,atomic_json
import sys,math,json,urllib.request,concurrent.futures,io,collections,time
sys.path.insert(0,str(ROOT/'.dependencies'))
import numpy as np,laspy
from pyproj import Transformer
URL='https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_FDEM_Orange_2018/'
OUT=ROOT/'data/heights';CACHE=ROOT/'data/cache/ept';CACHE.mkdir(exist_ok=True,parents=True)
OUT.mkdir(exist_ok=True,parents=True)
client=Client(CACHE);meta=client.get(URL+'ept.json');bounds=meta['bounds'];proj=Transformer.from_crs(4326,3857,always_xy=True)
lo=proj.transform(-81.391,28.570);hi=proj.transform(-81.387,28.574);roi=[lo[0],lo[1],hi[0],hi[1]]
MAX_DEPTH=10
def intersects(key):
 d,x,y,z=map(int,key.split('-'));size=(bounds[3]-bounds[0])/2**d;x0=bounds[0]+x*size;y0=bounds[1]+y*size
 return x0<=roi[2] and x0+size>=roi[0] and y0<=roi[3] and y0+size>=roi[1]
nodes={};seen=set()
def hierarchy(key):
 if key in seen:return
 seen.add(key);data=client.get(URL+'ept-hierarchy/'+key+'.json')
 for node,count in data.items():
  depth=int(node.split('-')[0])
  if depth>MAX_DEPTH or not intersects(node):continue
  if count==-1:hierarchy(node)
  elif count>0:nodes[node]=count
hierarchy('0-0-0-0')
print('Pilot EPT nodes:',len(nodes),'maximum depth:',MAX_DEPTH,'node points before clipping:',sum(nodes.values()),flush=True)
def read(node):
 path=CACHE/(node+'.laz')
 if not path.exists():
  for attempt in range(3):
   try:
    with urllib.request.urlopen(URL+'ept-data/'+node+'.laz',timeout=60) as r:raw=r.read()
    part=path.with_suffix('.part');part.write_bytes(raw);part.replace(path);break
   except Exception:
    if attempt==2:raise
    time.sleep(2**attempt)
 las=laspy.read(str(path));x=np.asarray(las.x);y=np.asarray(las.y);z=np.asarray(las.z);c=np.asarray(las.classification)
 keep=(x>=roi[0])&(x<=roi[2])&(y>=roi[1])&(y<=roi[3])
 return np.column_stack([x[keep],y[keep],z[keep],c[keep]])
chunks=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for i,data in enumerate(pool.map(read,sorted(nodes))):
  if len(data):chunks.append(data)
  if i%20==0:print('EPT nodes read:',i+1,'/',len(nodes),flush=True)
points=np.concatenate(chunks) if chunks else np.empty((0,4));np.savez_compressed(OUT/'pilot_points.npz',points=points)
report={'ept_url':URL+'ept.json','source_metadata':'https://www.fisheries.noaa.gov/inport/item/69496','pilot_bbox_wgs84':[-81.391,28.570,-81.387,28.574],'horizontal_crs':'EPSG:3857','source_project_acquisition':'2018-12-04 to 2019-04-12 (project metadata)','project_vertical_unit':'US survey foot per project metadata; EPT samples require independent ground check','max_depth':MAX_DEPTH,'clipped_points':len(points),'classifications':dict(collections.Counter(str(int(x)) for x in points[:,3])),'z_range':[float(points[:,2].min()),float(points[:,2].max())] if len(points) else []}
atomic_json(OUT/'pilot_points_metadata.json',report);print(json.dumps(report,indent=2))
