import urllib.request, urllib.parse, json, concurrent.futures
from pathlib import Path
urls={
 'permits':'https://data.cityoforlando.net/api/views/ryhf-m453.json',
 'parcel':'https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4?f=pjson',
 'catalog':'https://api.us.socrata.com/api/catalog/v1?domains=data.cityoforlando.net&limit=100',
 'gis':'https://www.arcgis.com/sharing/rest/search?f=json&num=100&q='+urllib.parse.quote('Orlando AND type:"Feature Service"')}
def fetch(kv):
 k,u=kv
 try:
  d=json.load(urllib.request.urlopen(u,timeout=60));p=Path(__file__).resolve().parents[1]/'data'/'cache';p.mkdir(exist_ok=True);(p/(k+'_metadata.json')).write_text(json.dumps(d))
  if k=='permits':return k,{'name':d.get('name'),'columns':[(c.get('fieldName'),c.get('dataTypeName')) for c in d.get('columns',[]) if not c['fieldName'].startswith(':')]}
  if k=='parcel':return k,{'name':d.get('name'),'fields':[f['name'] for f in d.get('fields',[])]}
  if k=='catalog':return k,[(x['resource']['id'],x['resource']['name']) for x in d.get('results',[])]
  return k,[(x['id'],x['title'],x['owner'],x.get('url')) for x in d.get('results',[])]
 except Exception as e:return k,str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for k,d in pool.map(fetch,urls.items()):print(k,json.dumps(d))
