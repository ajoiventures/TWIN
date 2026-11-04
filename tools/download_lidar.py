from data_pipeline import ROOT,Client,atomic_json
import urllib.request,json,time
out=ROOT/'data/heights';catalog=json.loads((out/'lidar_catalog.json').read_text(encoding='utf-8'));item=catalog['items'][0]
target=out/(item['title'].replace(' ','_')+'.laz')
if target.exists() and target.stat().st_size==item['sizeInBytes']:print('Cached',target)
else:
 req=urllib.request.Request(item['downloadURL'],headers={'User-Agent':'TWIN-CollegePark-lidar/0.3'})
 with urllib.request.urlopen(req,timeout=60) as src,target.with_suffix('.part').open('wb') as dst:
  total=0;previous=-1
  while True:
   chunk=src.read(4*1024*1024)
   if not chunk:break
   dst.write(chunk);total+=len(chunk);pct=int(total/item['sizeInBytes']*10)
   if pct!=previous:print('LiDAR download',round(total/1e6),'/',round(item['sizeInBytes']/1e6),'MB',flush=True);previous=pct
 if total!=item['sizeInBytes']:raise RuntimeError('Incomplete LiDAR download; partial file retained')
 target.with_suffix('.part').replace(target)
atomic_json(out/'active_lidar.json',{'path':str(target.relative_to(ROOT)),'source':item})
print('Tile ready',target,flush=True)
try:
 data=Client(ROOT/'data/cache/heights').get(item['metaUrl'],{'format':'json'});atomic_json(out/'sciencebase_metadata.json',data);print('METADATA',json.dumps({k:data.get(k) for k in ['title','dates','files','webLinks','temporal','spatial']}))
except Exception as e:print('METADATA_FETCH',str(e))
