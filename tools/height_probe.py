from data_pipeline import ROOT,Client,atomic_json
import json,collections,urllib.parse
client=Client(ROOT/'data/cache/heights')
url='https://tnmaccess.nationalmap.gov/api/v1/products'
data=client.get(url,{'datasets':'Lidar Point Cloud (LPC)','bbox':'-81.391,28.570,-81.387,28.574','outputFormat':'JSON','max':20})
out=ROOT/'data/heights';out.mkdir(exist_ok=True);atomic_json(out/'lidar_catalog.json',data)
print('LIDAR',json.dumps([ {k:x.get(k) for k in ['title','publicationDate','dateCreated','sizeInBytes','downloadURL','boundingBox','sourceId','metaUrl']} for x in data.get('items',[])],indent=2))
features=json.loads((ROOT/'data/buildings.geojson').read_text(encoding='utf-8'))['features'];floors=collections.Counter(str(f['properties'].get('FLOOR_NUM')) for f in features);print('BUILDING_FLOOR_VALUES',dict(floors))
active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'));parcels=json.loads((ROOT/active['relative_path']/'parcels.json').read_text(encoding='utf-8'))['features'];print('PARCEL_STORIES',dict(collections.Counter(str(f['properties'].get('stories')) for f in parcels)))
