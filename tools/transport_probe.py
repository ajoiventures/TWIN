"""Discover documented transportation services without guessing facility accuracy."""
from pathlib import Path
import json,urllib.request,urllib.parse,concurrent.futures,re
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data'/'transport';OUT.mkdir(exist_ok=True)
queries={
 'city_pedestrian_catalog':'https://www.arcgis.com/sharing/rest/search?f=json&num=100&q='+urllib.parse.quote('orgid:mMuoPCaIYD4wEgDl AND (sidewalk OR ramp OR crosswalk)'),
 'fdot_catalog':'https://www.arcgis.com/sharing/rest/search?f=json&num=50&q='+urllib.parse.quote('owner:FDOT_OpenData AND (sidewalk OR AADT OR lanes)'),
 'pedestrian_reference':'https://services.arcgis.com/04HiymDgLlsbhaV4/ArcGIS/rest/services/Orlando_Sidewalks_AGOL/FeatureServer/layers?f=json',
 'lynx_page':'https://www.golynx.com/maps-schedules/data-download.stml'}
def run(item):
 name,url=item
 try:
  with urllib.request.urlopen(url,timeout=60) as r:raw=r.read().decode('utf-8')
  if name=='lynx_page':
   links=re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',raw,flags=re.S|re.I);result=[{'url':urllib.parse.urljoin(url,u),'label':re.sub('<[^>]+>','',t).strip()} for u,t in links if any(s in (u+t).lower() for s in ['gtfs','gis data','arcgis'])]
  else:
   data=json.loads(raw)
   if 'results' in data:result=[{k:x.get(k) for k in ['id','title','owner','url','modified','accessInformation','licenseInfo']} for x in data['results']]
   else:result=data
  (OUT/(name+'.json')).write_text(json.dumps(result,indent=2));return name,result
 except Exception as e:return name,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for name,result in pool.map(run,queries.items()):
  if name=='pedestrian_reference':result=[{'id':x['id'],'name':x['name'],'fields':[(f['name'],f.get('alias')) for f in x.get('fields',[])]} for x in result.get('layers',[])]
  print(name,json.dumps(result))
