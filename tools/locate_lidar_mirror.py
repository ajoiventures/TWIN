from data_pipeline import ROOT,atomic_json
import urllib.request,urllib.parse,json,xml.etree.ElementTree as ET
out=ROOT/'data/heights';item=json.loads((out/'lidar_catalog.json').read_text(encoding='utf-8'))['items'][0]
prefix=urllib.parse.parse_qs(urllib.parse.urlparse(item['vendorMetaUrl']).query)['prefix'][0]
url='https://prd-tnm.s3.amazonaws.com/?'+urllib.parse.urlencode({'list-type':2,'prefix':prefix,'max-keys':1000})
with urllib.request.urlopen(url,timeout=60) as r:tree=ET.fromstring(r.read())
ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
keys=[e.text for e in tree.findall('.//s:Key',ns)];print('METADATA_KEYS',json.dumps(keys[:30]))
for key in keys:
 if key.endswith('.xml'):
  with urllib.request.urlopen('https://prd-tnm.s3.amazonaws.com/'+key,timeout=60) as r:raw=r.read()
  (out/'project_metadata.xml').write_bytes(raw);break
cloud=item['previewGraphicURL'].replace('/browse/','/LAZ/').replace('.jpg','.laz')
with urllib.request.urlopen(urllib.request.Request(cloud,method='HEAD'),timeout=60) as r:print('CLOUD_MIRROR',r.status,r.headers.get('Content-Length'))
item['official_cloud_download_url']=cloud;atomic_json(out/'lidar_download_source.json',item)
