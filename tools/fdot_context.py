"""Bounded, cached FDOT RCI/AADT context; no active geometry or API writes.

Default replay is offline; --live may populate missing public-source cache.
Contract and source/null/direction limits: docs/FDOT_CONTEXT.md.
"""
from pathlib import Path
import os,sys,json,hashlib,datetime,io,zipfile,shutil,re,math,urllib.request
from xml.etree import ElementTree as ET
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapefile
import shapely
from shapely.geometry import shape,mapping,Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import CRS,Transformer
from data_pipeline import Client,arcgis,SOURCES,atomic_json

OUT=Path('data/processed/fdot_context');BINARY=Path('data/transport/fdot_context')
ORG='O1JpcwDW8sjYuddV';MAP='https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/MapServer'
AGO='https://www.arcgis.com/sharing/rest/content/items/'
LAYERS={
 'road_names':{'url':MAP+'/13'},'rci_top30':{'url':MAP+'/29'},
 'aadt':{'item':'ceb698fb86d446c08f0b8e54acab6293'},
 'portable_sites':{'url':MAP+'/9'},'telemetered_sites':{'url':MAP+'/16'},
 'lanes':{'item':'3f217f88f25347709458ee7f9f651e03'},
 'speed':{'item':'4a61f17ab4784202ae10d7d5fb3bf9de'},
 'sidewalk_width_sep':{'item':'9ccec088b77e4f3ebe9b2deccda7347d'},
 'sidewalk_gaps':{'item':'4c970deb696d451283e8e4b7f4464667'},
 'city_streets':{'url':SOURCES['streets']['url'],'publisher':'City of Orlando'},
}
REQUIRED={'road_names':{'ROADWAY','NAME','BEGIN_POST','END_POST'},'rci_top30':{'ROADWAY','NOLANES_R','NOLANES_L','SECTADT','MAXSPEED_R','MAXSPEED_L','BEGIN_POST','END_POST'},'aadt':{'ROADWAY','COSITE','YEAR_','AADT','AADTFLG','BEGIN_POST','END_POST'},'portable_sites':{'SECTION_','COSITE','YEAR_','AADT','LOCATION','ACTIVE'},'telemetered_sites':{'SECTION_','COSITE','YEAR_','AADT','LOCATION','ACTIVE'},'lanes':{'ROADWAY','ROAD_SIDE','LANE_CNT','BEGIN_POST','END_POST'},'speed':{'ROADWAY','ROAD_SIDE','SPEED','BEGIN_POST','END_POST'},'sidewalk_width_sep':{'ROADWAY','ROAD_SIDE','DIRFMRD','SWSCD','DISTFMRD','BEGIN_POST','END_POST'},'sidewalk_gaps':{'ROADWAY','RDWYSIDE','EFFDT','LASTINVDT','NEXTINVDT','BEGIN_POST','END_POST'},'city_streets':set(SOURCES['streets']['fields'])}
BINARIES={
 'surface_width_metadata':('surface_width_metadata.xml','https://ftp.fdot.gov/public/file/orx24p1f70wc9nrxq3rjpg/surface_width.shp.xml',2000000),
 'surface_width_zip':('surface_width_zip.zip','https://ftp.fdot.gov/public/file/7haqhkucfeizcbq_wua8kw/surface_width.zip',16000000),
 'sidewalk_metadata':('sidewalk_metadata.xml',AGO+'9ccec088b77e4f3ebe9b2deccda7347d/info/metadata/metadata.xml',2000000),
 'lanes_metadata':('lanes_metadata.xml',AGO+'3f217f88f25347709458ee7f9f651e03/info/metadata/metadata.xml',2000000),
 'aadt_metadata':('aadt_metadata.xml',AGO+'ceb698fb86d446c08f0b8e54acab6293/info/metadata/metadata.xml',2000000),
 'speed_metadata':('speed_metadata.xml',AGO+'4a61f17ab4784202ae10d7d5fb3bf9de/info/metadata/metadata.xml',2000000),
 'handbook_f216':('handbook_f216.pdf','https://ftp.fdot.gov/public/file/FEpK78STbEepvxkCCln3Dw/FDOT_RCI_Handbook_F216.pdf',3000000),
 'handbook_f311':('handbook_f311.pdf','https://ftp.fdot.gov/public/file/3Sk3Lfw5_0WgiGgjclpuaA/FDOT_RCI_Handbook_F311.pdf',2000000),
}

def transform(project,geometry):return shapely.transform(geometry,project,interleaved=False)

def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def rel(p,root):return str(Path(p).relative_to(root)).replace('\\','/')
def iso_epoch(v):return datetime.datetime.fromtimestamp(v/1000,datetime.timezone.utc).isoformat() if isinstance(v,(int,float)) else None
def numeric(v,zero_ok=False):return float(v) if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and (v>=0 if zero_ok else v>0) else None

def binary(root,name,offline):
 filename,url,cap=BINARIES[name];folder=root/BINARY;folder.mkdir(parents=True,exist_ok=True);path=folder/filename;rp=folder/(filename+'.receipt.json')
 if not rp.exists() and path.exists():
  legacy=read(folder/'download_probes.json');matches=[r for r in legacy if r.get('file')==filename and r.get('url')==url and r.get('sha256')==sha(path)]
  if len(matches)!=1:raise ValueError('Unreceipted or modified source binary: '+filename)
  atomic_json(rp,matches[0])
 if path.exists():
  receipt=read(rp)
  if receipt['url']!=url or receipt['sha256']!=sha(path):raise ValueError('Source binary changed: '+filename)
  return path,receipt
 if offline:raise ValueError('Offline binary cache miss: '+filename)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*'}),timeout=45) as response:
  data=response.read(cap+1);headers=dict(response.headers);final=response.url
 if len(data)>cap:raise ValueError('Source download exceeds bounded cap')
 if name.endswith('metadata') and not data.lstrip().startswith(b'<?xml'):raise ValueError('Expected source metadata XML')
 if name.endswith('zip') and not data.startswith(b'PK'):raise ValueError('Expected original source ZIP')
 if name.startswith('handbook') and not data.startswith(b'%PDF'):raise ValueError('Expected original handbook PDF')
 path.write_bytes(data);receipt={'url':url,'final_url':final,'retrieved_utc':now(),'file':filename,'bytes':len(data),'sha256':sha(path),'headers':headers};atomic_json(rp,receipt);return path,receipt

def xml_dictionary(path):
 root=ET.fromstring(path.read_bytes());fields={}
 for node in root.findall('.//attr'):
  key=node.findtext('attrlabl')
  if not key:continue
  fields[key]={'definition':node.findtext('attrdef'),'type':node.findtext('attrtype'),'units_or_domain_notes':[' '.join(n.itertext()).strip() for n in node.findall('attrdomv/udom')],'coded_values':{n.findtext('edomv'):n.findtext('edomvd') for n in node.findall('attrdomv/edom')}}
 published=root.findtext('.//pubdate');return fields,{'publication_date':datetime.datetime.strptime(published,'%Y%m%d').date().isoformat() if published and re.fullmatch(r'\d{8}',published) else None,'refresh_cadence':root.findtext('.//update'),'use_constraints':root.findtext('.//useconst'),'abstract':root.findtext('.//idAbs')}

def surface_width(path,bbox,metadata_path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if sum(i.file_size for i in z.infolist())>200000000:raise ValueError('Unexpected uncompressed source package size')
  def member(ext):return next(n for n in names if n.lower().endswith(ext))
  if hashlib.sha256(z.read(next(n for n in names if n.lower().endswith('.shp.xml')))).hexdigest()!=sha(metadata_path):raise ValueError('External source metadata does not match original ZIP metadata')
  crs=CRS.from_wkt(z.read(member('.prj')).decode('utf8'));to_native=Transformer.from_crs(4326,crs,always_xy=True);to_wgs=Transformer.from_crs(crs,4326,always_xy=True)
  native_bounds=to_native.transform_bounds(*bbox,densify_pts=21)
  reader=shapefile.Reader(shp=io.BytesIO(z.read(member('.shp'))),shx=io.BytesIO(z.read(member('.shx'))),dbf=io.BytesIO(z.read(member('.dbf'))),encoding='utf8')
  fields=reader.fields[1:];features=[]
  if {'ROADWAY','ROAD_SIDE','BEGIN_POST','END_POST','WIDTH'}-{f[0] for f in fields}:raise ValueError('Original surface-width source schema changed')
  for record in reader.iterShapeRecords(bbox=native_bounds):
   geometry=transform(to_wgs.transform,shape(record.shape.__geo_interface__));properties=record.record.as_dict();properties['SOURCE_RECORD_INDEX']=record.record.oid
   features.append({'type':'Feature','geometry':mapping(geometry),'properties':properties})
  return {'type':'FeatureCollection','features':features},{'fields':[{'name':f[0],'type':f[1],'width':f[2],'decimal':f[3]} for f in fields],'native_crs':crs.to_string(),'native_crs_wkt':crs.to_wkt(),'external_metadata_equals_package_metadata':True,'source_record_index_is_package_revision_local':True,'original_file_feature_count':reader.numRecords,'oid':'SOURCE_RECORD_INDEX','zip_members':names}

def normalized_fields(table,p,fields):
 result={};notes=[]
 if table=='surface_width':
  v=numeric(p.get('WIDTH'));result={'through_lane_surface_width_ft':v,'through_lane_surface_width_m':v*.3048 if v is not None else None,'width_scope':'sum_of_through_lanes_for_source_roadside_not_ROW_or_sidewalk'}
 elif table=='sidewalk_width_sep':
  w=numeric(p.get('SWSCD'));offset=numeric(p.get('DISTFMRD'),zero_ok=True);result={'sidewalk_width_ft':w,'sidewalk_width_m':w*.3048 if w is not None else None,'sidewalk_separation_ft':offset,'sidewalk_separation_m':offset*.3048 if offset is not None else None,'width_precision':'nearest_foot_per_source_metadata','offset_precision':'nearest_half_foot_per_F216_handbook','compass_side':None}
 elif table=='lanes':result={'through_lane_count':numeric(p.get('LANE_CNT')),'lane_scope':'per_native_ROAD_SIDE; composite and divided records must not be blindly summed'}
 elif table=='speed':result={'posted_speed_mph':numeric(p.get('SPEED')),'posted_speed_mps':numeric(p.get('SPEED'))*.44704 if numeric(p.get('SPEED')) is not None else None,'effective_date':None}
 elif table in ('aadt','portable_sites','telemetered_sites'):result={'aadt_vehicles_per_day':numeric(p.get('AADT')),'count_year':p.get('YEAR_'),'count_observation_start':None,'count_observation_end':None,'live_traffic':False,'annual_average_not_current_flow':True}
 elif table=='sidewalk_gaps':result={'inventory_status':'source_coded_gap' if p.get('RDWYSIDE')=='G' else 'source_sidewalk_reference','effective_date':iso_epoch(p.get('EFFDT')),'last_inventory_date':iso_epoch(p.get('LASTINVDT')),'next_inventory_date':iso_epoch(p.get('NEXTINVDT')),'physical_current_condition_verified':False}
 if table=='aadt':
  flag=p.get('AADTFLG');result['native_estimate_method_flag']=flag;result['estimate_method']={'S':'last survey with prior-year factors; interim','F':'last survey with same-year factors; final','C':'telemetered monitoring station estimate; final'}.get(flag);result['method_flag_definition_verified']=flag in ['S','F','C']
 if table!='city_streets':
  for field in ('ROAD_SIDE','DIRFMRD','RDWYSIDE'):
   if field in p:
    domain=(fields.get(field,{}).get('domain') or {}).get('codedValues') or [];labels={str(x['code']):x['name'] for x in domain} or fields.get(field,{}).get('coded_values',{});result[field.lower()+'_label']=labels.get(str(p[field]));result['compass_side']=None
  result['side_alignment_verified_for_geometry_promotion']=False
  notes.append('Native side/offset codes retained; no east/west or City travel-direction identity inferred')
 if any(v is None or isinstance(v,str) and not v.strip() for v in p.values()):notes.append('Source null/blank retained; not a zero or absence claim')
 return result,notes

def screen_backbone(city_rows,tables,project):
 names=['lanes','surface_width','speed','sidewalk_width_sep','aadt'];trees={};geoms={}
 for name in names:
  geoms[name]=[transform(project,shape(r['clipped_geometry_wgs84'])) for r in tables[name]['rows']];trees[name]=STRtree(geoms[name])
 rows=[]
 for city in city_rows:
  g=transform(project,shape(city['clipped_geometry_wgs84']));lines=list(g.geoms) if g.geom_type=='MultiLineString' else [g];samples=[]
  for line in lines:
   if line.geom_type!='LineString' or line.length<.1:continue
   count=max(1,int(math.ceil(line.length/10)))
   for i in range(count):
    d=line.length*(i+.5)/count;p=line.interpolate(d);a=line.interpolate(max(0,d-3));b=line.interpolate(min(line.length,d+3));dx=b.x-a.x;dy=b.y-a.y;samples.append((p,dx,dy,line.length/count))
  coverage={};candidates={}
  for name in names:
   covered=0.;ids={}
   for point,dx,dy,weight in samples:
    hit=[]
    for index in trees[name].query(point.buffer(12)):
     candidate=geoms[name][int(index)]
     for line in list(candidate.geoms) if candidate.geom_type=='MultiLineString' else [candidate]:
      if line.geom_type!='LineString' or line.distance(point)>12 or line.length<.1:continue
      d=line.project(point);a=line.interpolate(max(0,d-3));b=line.interpolate(min(line.length,d+3));ex=b.x-a.x;ey=b.y-a.y;den=math.hypot(dx,dy)*math.hypot(ex,ey);cos=abs((dx*ex+dy*ey)/den) if den else 0
      if cos>=math.cos(math.radians(20)):hit.append(int(index));break
    if hit:
     covered+=weight
     for index in hit:ids[tables[name]['rows'][index]['id']]=tables[name]['rows'][index].get('roadway_id')
   coverage[name]={'parallel_sample_coverage_fraction':covered/g.length if g.length else None,'sampled_length_m':g.length,'uncovered_sampled_length_m':max(0,g.length-covered),'gap_meaning':'No qualifying source line nearby; not proof the physical facility is absent'};candidates[name]=[{'fdot_row_id':k,'roadway_id':v} for k,v in sorted(ids.items())]
  rows.append({'city_feature_id':city['id'],'city_object_id':city['original_fields']['OBJECTID'],'city_centerline_id':city['original_fields'].get('CenterlineID'),'city_global_id':city['original_fields'].get('GlobalID'),'street_name':city['original_fields'].get('FullStreetName'),'geometry_wgs84':city['clipped_geometry_wgs84'],'coverage':coverage,'candidate_fdot_rows':candidates,'join_status':'spatial_parallel_screen_only_not_promoted_identity','osm_id':None,'osm_identity_note':'No OSM source was imported; FDOT and City identifiers remain distinct'})
 return rows

def coverage_html(scopes,tables,gaps,project,register):
 bound=transform(project,scopes['neighborhood']);xmin,ymin,xmax,ymax=bound.bounds;scale=min(850/(xmax-xmin),850/(ymax-ymin))
 def xy(x,y):return ((x-xmin)*scale+15,(ymax-y)*scale+15)
 def svgpath(g):
  chunks=[]
  for part in getattr(g,'geoms',[g]):
   if part.geom_type=='Point':
    x,y=xy(part.x,part.y);chunks.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3"/>')
   elif part.geom_type in ('LineString','LinearRing'):chunks.append('<path d="M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(*v[:2]) for v in part.coords])+'"/>')
   elif part.geom_type=='Polygon':
    chunks.append('<path fill-rule="evenodd" d="'+' '.join('M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in [xy(*v[:2]) for v in ring.coords])+' Z' for ring in [part.exterior,*part.interiors])+'"/>')
  return ''.join(chunks)
 svg='<svg viewBox="0 0 900 900" xmlns="http://www.w3.org/2000/svg"><g fill="#f0f4ed" stroke="#777">'+svgpath(bound)+'</g><g fill="none" stroke="#d2a148" stroke-width="2">'+svgpath(transform(project,scopes['main_street']))+'</g>'
 gap_by_id={r['city_feature_id']:r for r in gaps};datasets=dict(tables);datasets['sidewalk_gap_screen']={'rows':[dict(r,coverage_screen=gap_by_id[r['id']]['coverage']['sidewalk_width_sep']) for r in tables['city_streets']['rows'] if gap_by_id[r['id']]['coverage']['sidewalk_width_sep']['parallel_sample_coverage_fraction']<.8]}
 colors={'sidewalk_gap_screen':'#c65353','city_streets':'#b5b7b4','lanes':'#1b865f','sidewalk_width_sep':'#d17b13','aadt':'#7545a5','portable_sites':'#1268b2'}
 for name,color in colors.items():
  svg+=f'<g id="{name}" fill="{color if name.endswith("sites") else "none"}" stroke="{color}" stroke-width="{2 if name!="city_streets" else 1}">'
  for row in datasets[name]['rows']:svg+='<g data-row="'+name+':'+str(row['source_object_id'])+'">'+svgpath(transform(project,shape(row['clipped_geometry_wgs84'])))+'</g>'
  svg+='</g>'
 svg+='</svg>'
 labels={'city_streets':'City streets','sidewalk_gap_screen':'Sidewalk inventory gap screen','lanes':'Lane inventory','sidewalk_width_sep':'Sidewalk attributes','aadt':'Annual traffic','portable_sites':'Count sites'}
 controls=' '.join(f'<label><input type="checkbox" checked data-layer="{n}">{labels[n]}</label>' for n in colors)
 dataset={name:{str(r['source_object_id']):r for r in datasets[name]['rows']} for name in colors};encoded=json.dumps(dataset).replace('<','\\u003c');sources=json.dumps({r['table']:r for r in register}).replace('<','\\u003c')
 return '<!doctype html><meta charset="utf-8"><title>FDOT coverage reference</title><style>body{font:15px system-ui;margin:22px;color:#24352d}main{display:grid;grid-template-columns:900px 1fr}svg{width:100%;max-height:85vh}pre{white-space:pre-wrap;overflow-wrap:anywhere}label{margin-right:12px}.selected path,.selected circle{stroke:#111;stroke-width:4}</style><h1>College Park FDOT reference coverage</h1><p>Official City network in gray; green lane inventory, orange sidewalk attributes, purple annual traffic events and blue historical count sites. Gold outline: Main Street. Red marks City segments with less than80% nearby parallel FDOT sidewalk-line coverage; it does not mean a sidewalk is physically missing. All are references, not measured curb/sidewalk edges or live traffic.</p>'+controls+'<main>'+svg+'<pre id="detail">Select a source line or count site. No nearby line means an inventory gap, not a missing sidewalk.</pre></main><script>const rows='+encoded+';const sources='+sources+';document.querySelectorAll("[data-layer]").forEach(x=>x.onchange=()=>document.getElementById(x.dataset.layer).style.display=x.checked?"":"none");document.querySelectorAll("[data-row]").forEach(x=>x.onclick=()=>{document.querySelectorAll(".selected").forEach(y=>y.classList.remove("selected"));x.classList.add("selected");const [t,id]=x.dataset.row.split(":");document.getElementById("detail").textContent=JSON.stringify({source:sources[t==="sidewalk_gap_screen"?"city_streets":t],record:rows[t][id]},null,2)});</script>'

def build(root=ROOT,offline=True):
 root=Path(root).resolve();out=root/OUT;receipt=out/'receipt.json';expected={'packet.json','coverage.html'}
 if receipt.exists():
  prior=read(receipt)
  if set(prior.get('artifacts',{}))!=expected or any(sha(out/n)!=h for n,h in prior['artifacts'].items()):raise ValueError('Preserve modified prior FDOT outputs')
 elif any((out/n).exists() for n in expected):raise ValueError('Unreceipted prior FDOT output')
 active=read(root/'data/processed/active.json');boundary=root/'data/processed/study_boundaries.geojson';scopes={f['properties']['scope']:shape(f['geometry']) for f in read(boundary)['features']};scope=scopes['neighborhood'];project=Transformer.from_crs(4326,32617,always_xy=True).transform
 client=Client(root/'data/cache/fdot_context',offline=offline);portal=client.get('https://fdot.maps.arcgis.com/sharing/rest/portals/self',{'f':'json'})
 if portal.get('id')!=ORG or portal.get('name')!='Florida Department of Transportation':raise ValueError('Official FDOT organization association changed')
 downloads={};binary_paths=[]
 for name in BINARIES:
  path,r=binary(root,name,offline);downloads[name]=r;binary_paths.extend([path,path.with_name(path.name+'.receipt.json')])
 dictionaries={};xml_info={}
 for name in ['surface_width','sidewalk','lanes','speed','aadt']:
  dictionaries[name],xml_info[name]=xml_dictionary(root/BINARY/BINARIES[name+'_metadata'][0])
 # A changed source dictionary must not silently alter normalized units.
 if 'feet' not in dictionaries['surface_width']['WIDTH']['definition'].lower() or not any('foot' in x.lower() for x in dictionaries['sidewalk']['SWSCD']['units_or_domain_notes']):raise ValueError('Verified source width unit definition changed')
 tables={};register=[];metadata_paths=[]
 for name,spec in LAYERS.items():
  item=None;url=spec.get('url')
  if spec.get('item'):
   item=client.get(AGO+spec['item'],{'f':'json'})
   if item.get('orgId')!=ORG or item.get('access')!='public' or not item.get('url','').startswith('https://services1.arcgis.com/'+ORG+'/'):raise ValueError('Official hosted FDOT item association changed')
   service=client.get(item['url'],{'f':'json'});url=item['url']+'/'+str(service['layers'][0]['id'])
  meta=client.get(url,{'f':'json'});fields=[f['name'] for f in meta['fields'] if f['type']!='esriFieldTypeGeometry' and not f['name'].startswith('Shape.')];oid=next(f['name'] for f in meta['fields'] if f['type']=='esriFieldTypeOID')
  if REQUIRED[name]-set(fields):raise ValueError('Required source schema changed: '+name+' '+str(sorted(REQUIRED[name]-set(fields))))
  if name=='city_streets':fields=SOURCES['streets']['fields']
  geo,meta=arcgis(client,{'url':url,'fields':fields,'oid':oid,'max_features':5000},scope.bounds)
  tables[name]={'source_query_bbox_count':len(geo['features']),'source_object_id_field':oid,'field_dictionary':{f['name']:f for f in meta['fields']},'features':geo['features'],'rows':[]}
  description=item.get('description','') if item else meta.get('description','');date=re.search(r'created on:\s*(\d{2}/\d{2}/\d{4})',description)
  register.append({'table':name,'publisher':spec.get('publisher','Florida Department of Transportation'),'endpoint':url,'item_id':spec.get('item'),'source_native_crs':meta.get('extent',{}).get('spatialReference'),'output_crs':'EPSG4326','analysis_crs':'EPSG32617 meters','vertical_datum':'not used; no height interpretation','source_spatial_publication_date':datetime.datetime.strptime(date.group(1),'%m/%d/%Y').date().isoformat() if date else None,'source_updated_epoch_ms':item.get('modified') if item else meta.get('editingInfo',{}).get('lastEditDate'),'acquisition_date':None,'effective_date':None,'description':description,'license_or_reuse':item.get('licenseInfo') if item else meta.get('copyrightText') or 'No layer-specific license supplied; FDOT GIS disclaimer applies, not a survey warranty','refresh_cadence':'weekly GIS publication; underlying inventory dates vary/unknown','authentication_observed':'public query succeeded without token','published_request_rate_limit':None,'max_record_count':meta.get('maxRecordCount'),'query_batch_size':50,'all_source_ID_batches_verified':True})
 surface,smeta=surface_width(root/BINARY/BINARIES['surface_width_zip'][0],scope.bounds,root/BINARY/BINARIES['surface_width_metadata'][0]);tables['surface_width']={'source_query_bbox_count':len(surface['features']),'source_object_id_field':'SOURCE_RECORD_INDEX','field_dictionary':dictionaries['surface_width'],'source_package_schema':smeta,'features':surface['features'],'rows':[]}
 register.append({'table':'surface_width','publisher':'Florida Department of Transportation','download_url':BINARIES['surface_width_zip'][1],'metadata_url':BINARIES['surface_width_metadata'][1],'source_native_crs':smeta['native_crs'],'output_crs':'EPSG4326','analysis_crs':'EPSG32617 meters','source_spatial_publication_date':xml_info['surface_width']['publication_date'],'acquisition_date':None,'effective_date':None,'refresh_cadence':xml_info['surface_width']['refresh_cadence'],'license_or_reuse':xml_info['surface_width']['use_constraints'],'definition':xml_info['surface_width']['abstract'],'package_bytes_sha256':downloads['surface_width_zip']['sha256'],'authentication_observed':'public download succeeded without credentials','published_request_rate_limit':None})
 excluded=[]
 for name,table in tables.items():
  for f in table.pop('features'):
   p=f['properties'];g=shape(f['geometry']);oid=p[table['source_object_id_field']]
   if not g.is_valid or g.is_empty:raise ValueError('Invalid source geometry: '+name+':'+str(oid))
   clipped=g.intersection(scope)
   if clipped.is_empty or g.geom_type in ('LineString','MultiLineString') and transform(project,clipped).length<=.01:excluded.append({'table':name,'source_object_id':oid,'reason':'bbox_candidate_without_positive_length_or_point_in_official_neighborhood'});continue
   roadway=p.get('ROADWAY') or p.get('SECTION_')
   if roadway is not None and (not isinstance(roadway,str) or not re.fullmatch(r'\d{8}',roadway)):raise ValueError('Native FDOT roadway string changed')
   normalized,notes=normalized_fields(name,p,table['field_dictionary']);key={'ROADWAY':roadway,'ROAD_SIDE':p.get('ROAD_SIDE'),'BEGIN_POST':p.get('BEGIN_POST'),'END_POST':p.get('END_POST'),'COSITE':p.get('COSITE'),'YEAR_':p.get('YEAR_'),'DIRFMRD':p.get('DIRFMRD')}
   row={'id':('city:street:' if name=='city_streets' else 'fdot:'+name+':')+str(oid),'source_object_id':oid,'roadway_id':roadway,'native_event_key':key,'original_fields':p,'normalized':normalized,'quality_notes':notes,'clipped_geometry_wgs84':mapping(clipped),'main_street_intersection':not g.intersection(scopes['main_street']).is_empty and (g.geom_type=='Point' or transform(project,g.intersection(scopes['main_street'])).length>.01),'main_street_overlap_length_m':transform(project,g.intersection(scopes['main_street'])).length if g.geom_type!='Point' else None,'source_geometry_mutated':False,'scene_geometry_promoted':False};table['rows'].append(row)
  xmlkey={'surface_width':'surface_width','sidewalk_width_sep':'sidewalk','lanes':'lanes','speed':'speed','aadt':'aadt'}.get(name)
  if xmlkey and name!='surface_width':
   for field,metadata in table['field_dictionary'].items():metadata['source_xml_definition']=dictionaries[xmlkey].get(field)
  table['neighborhood_count']=len(table['rows']);table['main_street_count']=sum(r['main_street_intersection'] for r in table['rows']);table['first_five_safe_rows']=table['rows'][:5]
  table['raw_null_blank_zero_profiles']={field:{'null':sum(r['original_fields'].get(field) is None for r in table['rows']),'blank':sum(isinstance(r['original_fields'].get(field),str) and not r['original_fields'][field].strip() for r in table['rows']),'zero':sum(isinstance(r['original_fields'].get(field),(int,float)) and r['original_fields'][field]==0 for r in table['rows'])} for field in sorted({k for r in table['rows'] for k in r['original_fields']})}
 # Original source names remain ROADWAY-based events, not a spatially guessed name.
 names={}
 for r in tables['road_names']['rows']:names.setdefault(r['roadway_id'],set()).add(r['original_fields']['NAME'])
 for name,table in tables.items():
  for row in table['rows']:row['same_native_roadway_names']=sorted(names.get(row['roadway_id'],set()))
 joins=[]
 for station in tables['portable_sites']['rows']+tables['telemetered_sites']['rows']:
  p=station['original_fields'];matches=[r for r in tables['aadt']['rows'] if r['original_fields'].get('COSITE')==p.get('COSITE') and r['roadway_id']==station['roadway_id'] and r['original_fields'].get('YEAR_')==p.get('YEAR_')];sg=transform(project,shape(station['clipped_geometry_wgs84']))
  joins.append({'station_row_id':station['id'],'cosite':p.get('COSITE'),'roadway_id':station['roadway_id'],'count_year':p.get('YEAR_'),'matching_aadt_row_ids':[r['id'] for r in matches],'source_key_match':'COSITE+ROADWAY/SECTION_+YEAR_; not nearest-location identity','aadt_value_agreement':all(r['original_fields'].get('AADT')==p.get('AADT') for r in matches) if matches else None,'station_to_event_distances_m':[transform(project,shape(r['clipped_geometry_wgs84'])).distance(sg) for r in matches],'status':'matched_native_keys' if matches else 'no_aadt_event_with_same_native_keys_in_neighborhood'})
 gaps=screen_backbone(tables['city_streets']['rows'],tables,project)
 for source in register:
  accesses=[r for r in client.accesses if r['url'].split('?')[0].startswith(source.get('endpoint','!'))];times=sorted(r['retrieved_utc'] for r in accesses if r.get('retrieved_utc'));source['retrieval_range_utc']=[times[0],times[-1]] if times else None;source['source_count_years']=sorted({r['original_fields']['YEAR_'] for r in tables[source['table']]['rows'] if r['original_fields'].get('YEAR_') is not None})
 install_receipt=root/BINARY/'pyshp_install_receipt.json'
 if shapefile.__version__!='2.3.1':raise ValueError('Install pinned pyshp2.3.1 before replay')
 if not install_receipt.exists():atomic_json(install_receipt,{'package':'pyshp','version':shapefile.__version__,'installed_shapefile_py_sha256':sha(root/'.dependencies/shapefile.py'),'official_release_json':'https://pypi.org/pypi/pyshp/2.3.1/json','installed_source_identical_to_official_wheel':None,'verification_scope':'Runtime file fingerprint only; official-wheel comparison not performed in this environment'})
 if read(install_receipt).get('installed_shapefile_py_sha256')!=sha(root/'.dependencies/shapefile.py'):raise ValueError('Installed shapefile source changed; review dependency receipt')
 deps=[install_receipt,boundary,root/'data/processed/active.json',root/'tools/fdot_context.py',root/'tools/data_pipeline.py',root/'.dependencies/shapefile.py',*binary_paths]
 for access in client.accesses:
  path=client.cache/(hashlib.sha256(access['url'].encode()).hexdigest()+'.json');deps.extend([path,path.with_suffix('.provenance.json')])
 packet={'schema':'twin.fdot-context/1','source_snapshot':active['snapshot'],'built_utc':now(),'scope':'full_official_College_Park_neighborhood_with_separate_MainStreet_intersections','query_bbox_wgs84':list(scope.bounds),'source_register':register,'original_binary_receipts':downloads,'requests':client.accesses,'JSON_cache_receipt_scope':'Checksums bind parsed/reserialized JSON cache files, not original HTTP wire bytes; binary checksums bind exact downloaded bytes','source_xml_dictionaries':dictionaries,'source_xml_metadata':xml_info,'tables':tables,'station_event_joins':joins,'city_backbone_coverage':gaps,'spatial_screen_method':{'interval_m':10,'maximum_separation_m':12,'maximum_parallel_angle_degrees':20,'purpose':'inventory coverage screen only; not accepted entity links, surveyed edge accuracy or cardinal-side validation'},'target_road_records':{n:[r['id'] for table in tables.values() for r in table['rows'] if n in ' '.join(r['same_native_roadway_names']).upper() or n in str(r['original_fields'].get('FullStreetName','')).upper()] for n in ['EDGEWATER','PRINCETON']},'envelope_exclusions':excluded,'dependencies':{rel(p,root):sha(p) for p in set(deps)},'runtime_dependency':{'name':'pyshp','version':shapefile.__version__,'installation':'project .dependencies; python -m pip install --target .dependencies --no-deps pyshp==2.3.1','upstream':'https://pypi.org/project/pyshp/2.3.1/','source':'official PyPI; no shared lock edits'},'null_semantics':['Original null, blank, zero and source codes retained without coercion.','Nonpositive width/lane/speed/AADT values normalize to unknown, not physical absence.','Zero sidewalk separation is valid; source instructions permit zero/blank for back-of-curb cases, so blank is not converted to zero.'],'limits':['Current publication dates are not inventory acquisition dates; YEAR_ is the annual count year, not a live timestamp.','Source-side domains are preserved, but compass direction and City travel-direction alignment are unverified; no offset sidewalks authored.','Missing coverage is an inventory gap, not proof a road/sidewalk is absent.','Surface width is total through-lane width for one source roadside, not total pavement/ROW/curb-to-frontage width.','AADT aggregate and site ACTIVE flag do not provide live traffic, speed, occupancy or vehicle positions.','Ticket15 parking capacities, restrictions, occupancy/turnover and bike/scooter inventories remain separate unfinished scope.'],'active_snapshot_changed':False,'scene_changed':False,'private_booms_read':False}
 payloads={'packet.json':json.dumps(packet,indent=2,allow_nan=False).encode(),'coverage.html':coverage_html(scopes,tables,gaps,project,register).encode('utf8')}
 if receipt.exists():
  if any(sha(out/n)!=h for n,h in prior['artifacts'].items()):raise ValueError('FDOT output changed during build')
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for name in [*expected,'receipt.json']:shutil.copy2(out/name,backup/name)
 out.mkdir(parents=True,exist_ok=True)
 for name,body in payloads.items():path=out/(name+'.tmp');path.write_bytes(body);path.replace(out/name)
 atomic_json(receipt,{'source_snapshot':active['snapshot'],'artifacts':{n:sha(out/n) for n in expected}});return packet

def validate(root=ROOT):
 root=Path(root).resolve();out=root/OUT;receipt=read(out/'receipt.json');p=read(out/'packet.json')
 if p.get('schema')!='twin.fdot-context/1' or not p.get('dependencies') or set(receipt.get('artifacts',{}))!={'packet.json','coverage.html'}:raise ValueError('Incomplete FDOT integrity proof')
 if p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or receipt['source_snapshot']!=p['source_snapshot']:raise ValueError('FDOT snapshot stale')
 for name,h in receipt['artifacts'].items():
  if sha(out/name)!=h:raise ValueError('FDOT artifact modified')
 for name,h in p['dependencies'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or sha(path)!=h:raise ValueError('FDOT source/dependency changed')
 return p

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args();p=build(offline=not args.live);validate();print(json.dumps({'snapshot':p['source_snapshot'],'counts':{n:{'neighborhood':t['neighborhood_count'],'main_street':t['main_street_count']} for n,t in p['tables'].items()},'native_station_event_joins':len(p['station_event_joins'])},indent=2))
