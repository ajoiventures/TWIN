import urllib.request,json,concurrent.futures
prefix='https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/'
urls={k:prefix+v+'/FeatureServer/0?f=json' for k,v in {'streets':'Street_Centerline','neighborhoods':'OrlandoPoliticalNeighborhoods','zoning':'OrlandoLUZoning','addresses':'Address_Point','parks':'OrlandoParks'}.items()}
urls.update({'businesses':'https://data.cityoforlando.net/api/views/7388-4re5.json','mainstreets':'https://data.cityoforlando.net/api/views/38c3-xmnz.json'})
def run(kv):
 k,u=kv
 try:
  d=json.load(urllib.request.urlopen(u,timeout=60));return k,{'name':d.get('name'),'geometryType':d.get('geometryType'),'fields':[f.get('name') for f in d.get('fields',[])] or [(c.get('fieldName'),c.get('dataTypeName')) for c in d.get('columns',[]) if not c['fieldName'].startswith(':')],'error':d.get('error')}
 except Exception as e:return k,str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as p:
 for k,d in p.map(run,urls.items()):print(k,json.dumps(d))
