from data_pipeline import Client,ROOT,arcgis,atomic_json,BBOX
import urllib.parse,json,urllib.request,re
client=Client(ROOT/'data/cache/transport')
out=ROOT/'data/transport';out.mkdir(exist_ok=True)
report=[]
for item in ['a6b83c314766472cae5e1479f68f7e65','e65f6e0935e4456f946554f4f4600c60']:
 data=client.get('https://www.arcgis.com/sharing/rest/content/items/'+item+'/data',{'f':'json'})
 atomic_json(out/(item+'.json'),data)
 layers=[]
 def walk(xs):
  for x in xs:
   if x.get('url'):layers.append({'title':x.get('title'),'url':x['url']})
   walk(x.get('layers',[]))
 walk(data.get('operationalLayers',[]));print('CITY_MAP',item,json.dumps(layers))
 report.extend(layers)
# This consultant-hosted reference is roadway linework, not measured sidewalk-edge polygons.
url='https://services.arcgis.com/04HiymDgLlsbhaV4/ArcGIS/rest/services/Orlando_Sidewalks_AGOL/FeatureServer/1'
source={'url':url,'fields':['OBJECTID','ROADNAME','ROADWAY','SIDEWALK','SPEED','AADT','SURF_WIDTH','THRU_LANES','SW_FLUSH'],'oid':'OBJECTID'}
data,meta=arcgis(client,source);atomic_json(out/'roadway_sidewalk_attributes.geojson',data);atomic_json(out/'roadway_sidewalk_metadata.json',meta)
print('REFERENCE_ROADWAY_ROWS',len(data['features']))
print('EDGEWATER_SAMPLE',json.dumps([f['properties'] for f in data['features'] if 'EDGEWATER' in str(f['properties'].get('ROADNAME','')).upper()][:3]))
for url in ['https://gtfsrt.golynx.com/gtfsrt/','http://gtfsrt.golynx.com/gtfsrt/']:
 try:
  with urllib.request.urlopen(url,timeout=30) as r:raw=r.read().decode()
  print('LYNX_LINKS',url,re.findall(r'<a[^>]+href=["\']([^"\']+)["\']',raw,re.I)[:30]);(out/'lynx_download_index.html').write_text(raw);break
 except Exception as e:print('LYNX_ERROR',url,str(e))
atomic_json(out/'pedestrian_layer_candidates.json',report)
