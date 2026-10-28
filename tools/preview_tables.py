"""Read-only five-row previews; raw private-source values never enter the repository."""
import json,csv,urllib.request,urllib.parse,concurrent.futures,datetime,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
_bounds=json.loads((ROOT/'config/study_area.json').read_text(encoding='utf-8'))['acquisition_bbox_wgs84']
BBOX=','.join(map(str,_bounds))
GIS='https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/'
def get(url,params=None):
 if params:url+='?'+urllib.parse.urlencode(params)
 with urllib.request.urlopen(url,timeout=60) as response:d=json.load(response)
 if isinstance(d,dict) and d.get('error'):raise RuntimeError(d['error'])
 return d
def arc(name,url,fields,oid='OBJECTID'):
 meta=get(url,{'f':'json'})
 existing=[f['name'] for f in meta.get('fields',[])]
 fields=[f for f in fields if f in existing]
 d=get(url+'/query',{'f':'geojson','where':'1=1','geometry':BBOX,'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outSR':4326,'outFields':','.join(fields),'orderByFields':oid+' ASC','resultRecordCount':5,'returnGeometry':'false'})
 return {'name':name,'source':url,'source_fields':existing,'preview_fields':fields,'rows':[x['properties'] for x in d['features']],'order':oid+' ascending; study-area intersection'}
def soda(name,dataset,fields,order):
 url='https://data.cityoforlando.net'
 meta=get(url+'/api/views/'+dataset+'.json')
 west,south,east,north=_bounds
 d=get(url+'/resource/'+dataset+'.json',{'$select':','.join(fields),'$where':f'within_box(geocoded_column,{north},{west},{south},{east})','$order':order,'$limit':5})
 return {'name':name,'source':url+'/d/'+dataset,'source_fields':[c['fieldName'] for c in meta['columns'] if not c['fieldName'].startswith(':')],'preview_fields':fields,'rows':d,'order':order+'; point within study area'}
jobs=[
 lambda:arc('OCPA parcels','https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4',['OBJECTID','PARCEL','SITUS','DOR_CODE','ZONING_CODE','STYS','AYB']),
 lambda:arc('Orlando streets',GIS+'Street_Centerline/FeatureServer/0',['OBJECTID','FullStreetName','CenterlineID','RoadClass','Speed']),
 lambda:arc('Orlando neighborhoods',GIS+'OrlandoPoliticalNeighborhoods/FeatureServer/0',['Object_ID','NeighborhoodName','NeighborhoodID'],'Object_ID'),
 lambda:arc('Orlando zoning',GIS+'OrlandoLUZoning/FeatureServer/0',['OBJECTID','Zoning','PD_NAME','FormatDate']),
 lambda:arc('Orlando parks',GIS+'OrlandoParks/FeatureServer/0',['OBJECTID','NAME','TYPE','CLASS','ADMIN']),
 lambda:soda('Orlando permit applications','ryhf-m453',['permit_number','parcel_number','permit_address','application_type','application_status','processed_date'],'processed_date DESC,permit_number ASC'),
 lambda:soda('Orlando business tax receipts','7388-4re5',['case_number','business_name','business_address','license_status','license_type','last_licensed_issue_date'],'case_number ASC'),
]
def safe(job):
 try:return job()
 except Exception as e:return {'error':str(e)}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--booms-tracker',type=Path,help='Optional explicitly selected local CSV; never modified')
 parser.add_argument('--output',type=Path,default=ROOT/'data/private/previews',help='Local preview directory (default is excluded from Git)')
 args=parser.parse_args()
 if args.booms_tracker and not args.booms_tracker.is_file():parser.error('The selected BOOMS tracker does not exist')
 with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:tables=list(pool.map(safe,jobs))
 buildings=json.loads((ROOT/'data'/'buildings.geojson').read_text(encoding='utf-8'))['features']
 fields=['OBJECTID','PID','BLDG_NUM','FLOOR_NUM','SUBTYPE','SUB_DESC']
 tables.append({'name':'OCPA building footprint subareas','source':'https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28','source_fields':list(buildings[0]['properties']),'preview_fields':fields,'rows':[{k:f['properties'].get(k) for k in fields} for f in sorted(buildings,key=lambda f:f['properties']['OBJECTID'])[:5]],'order':'OBJECTID ascending; cached study-area snapshot. These are subareas, not five distinct buildings.'})
 local=args.booms_tracker
 if local:
  with local.open(encoding='utf-8-sig',newline='') as h:
   r=csv.DictReader(h);fields=['parcel_pin','street_address','num_floors','vacancy_status','building_use','last_edit_date','booms_public_release_tier'];rows=[]
   for _,row in zip(range(5),r):rows.append({k:row.get(k) for k in fields})
   tables.append({'name':'Local BOOMS completion tracker','source':str(local),'source_fields':r.fieldnames,'preview_fields':fields,'rows':rows,'order':'Original file order. Read-only preview; release status is preserved. Owner/contact/free-text note values excluded.'})
 out=args.output;out.mkdir(exist_ok=True,parents=True)
 (out/'source-table-preview.json').write_text(json.dumps(tables,indent=2),encoding='utf-8')
 def fmt(v):
  if v is None or v=='':return '—'
  return str(v).replace('|','\\|').replace('\n',' ')
 lines=['# Source fields and first five rows','',f'Retrieved {datetime.datetime.now(datetime.timezone.utc).isoformat()}. Only the College Park study rectangle is queried. These are real source rows, not synthetic examples. Blank values remain unknown. Full source field lists are shown; row previews use the selected clean fields. Geometry coordinates and owner/contact/note values are omitted from the preview.','']
 for t in tables:
  if 'error' in t:lines+=['Query failed: '+t['error'],''];continue
  lines+=['## '+t['name'],'','Source: '+t['source'],'','Source fields: '+', '.join('`'+f+'`' for f in t['source_fields']), '', 'Order: '+t['order'],'','| '+' | '.join(t['preview_fields'])+' |','| '+' | '.join('---' for _ in t['preview_fields'])+' |']
  lines+=['| '+' | '.join(fmt(row.get(f)) for f in t['preview_fields'])+' |' for row in t['rows']]
  if len(t['rows'])<5:lines+=['',f"Only {len(t['rows'])} records returned within this study area; no rows fabricated."]
  lines+=['']
 (out/'source-table-preview.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps(tables,indent=2))
