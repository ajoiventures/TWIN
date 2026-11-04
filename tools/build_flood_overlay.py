"""Bounded FEMA effective NFHL information overlay; offline cache and provenance."""
from pathlib import Path
import os,sys,json,argparse,datetime,hashlib,html
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapely
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from data_pipeline import Client,now,atomic_json
from verify_retail_block import sha,inside
BASE='https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer'
FIELDS={28:['OBJECTID','GlobalID','DFIRM_ID','VERSION_ID','FLD_AR_ID','STUDY_TYP','FLD_ZONE','ZONE_SUBTY','SFHA_TF','STATIC_BFE','V_DATUM','DEPTH','LEN_UNIT','VELOCITY','VEL_UNIT','SOURCE_CIT'],3:['OBJECTID','GlobalID','DFIRM_ID','VERSION_ID','FIRM_ID','ST_FIPS','PCOMM','PANEL','SUFFIX','FIRM_PAN','PANEL_TYP','PRE_DATE','EFF_DATE','SCALE','SOURCE_CIT'],1:['OBJECTID','GlobalID','DFIRM_ID','VERSION_ID','LOMR_ID','EFF_DATE','CASE_NO','STATUS','SOURCE_CIT'],0:['OBJECTID','STUDY_ID','GlobalID']}
NAMES={28:'hazard_zones',3:'effective_panels',1:'effective_revisions',0:'availability'}
COLORS={'AE':'#337cb6','A':'#527fb2','X':'#e7dcb3'}
def date(value):
 if value is None:return None
 try:
  d=datetime.datetime.fromtimestamp(value/1000,datetime.timezone.utc)
  return d.date().isoformat() if 1900<=d.year<=2100 else None
 except (ValueError,OverflowError,OSError):return None

def fetch(client,layer,bbox):
 meta=client.get(f'{BASE}/{layer}',{'f':'json'})
 if 'error' in meta:raise ValueError(meta['error'])
 ids=client.get(f'{BASE}/{layer}/query',{'f':'json','geometry':','.join(map(str,bbox)),'geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true','where':'1=1'})
 if 'error' in ids or 'objectIds' not in ids:raise ValueError('FEMA ID query failed')
 ids=sorted(set(ids['objectIds'] or []))
 if len(ids)>1000:raise ValueError('Bounded FEMA feature limit exceeded')
 features=[]
 for start in range(0,len(ids),50):
  data=client.get(f'{BASE}/{layer}/query',{'f':'geojson','objectIds':','.join(map(str,ids[start:start+50])),'outFields':','.join(FIELDS[layer]),'outSR':4326,'returnGeometry':'true'})
  if data.get('error') or data.get('exceededTransferLimit'):raise ValueError('FEMA feature query incomplete')
  features.extend(data['features'])
 if len(features)!=len(ids) or {f['properties']['OBJECTID'] for f in features}!=set(ids):raise ValueError('FEMA feature completeness mismatch')
 return meta,features

def safe_write(path,content,previous):
 if path.suffix=='.html':content=content.encode('ascii','xmlcharrefreplace').decode('ascii')
 if path.exists() and (str(path.relative_to(ROOT)).replace('\\','/') not in previous or sha(path)!=previous[str(path.relative_to(ROOT)).replace('\\','/')]):raise ValueError('Preserve manually changed flood artifact: '+str(path))
 if path.exists():
  backup=ROOT/'data/flood/backups'/now().replace(':','_')/path.name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(content,encoding='utf-8');os.replace(temporary,path)

def build(offline=False):
 active=read(ROOT/'data/processed/active.json')
 if not (ROOT/active['relative_path']).resolve().is_relative_to((ROOT/'data/snapshots').resolve()):raise ValueError('Invalid source snapshot path')
 bound_path=ROOT/'data/processed/study_boundaries.geojson';bounds=read(bound_path)['features'];union=unary_union([shape(f['geometry']) for f in bounds]);project=Transformer.from_crs(4326,32617,always_xy=True);back=Transformer.from_crs(32617,4326,always_xy=True);project_g=lambda g:shapely.transform(g,project.transform,interleaved=False);utm=project_g(union)
 scopes={f['id']:project_g(shape(f['geometry'])) for f in bounds};pilot_path=ROOT/'data/processed/pilot.json';pilot=read(pilot_path)
 if pilot['source_snapshot']!=active['snapshot']:raise ValueError('Stale pilot scope')
 scopes['pilot_review_context']=project_g(shape(pilot['centerline'])).buffer(60)
 client=Client(ROOT/'data/cache/flood',offline=offline);service=client.get(BASE,{'f':'json'});tables={};metadata={};dictionary={};unresolved=[]
 for layer,name in NAMES.items():
  meta,features=fetch(client,layer,union.bounds);metadata[name]={'layer_url':f'{BASE}/{layer}','source_crs':meta['extent']['spatialReference'],'copyrightText':meta.get('copyrightText'),'description':meta.get('description'),'source_feature_count_bbox':len(features)};dictionary[name]=[{k:f.get(k) for k in ['name','alias','type','length','domain']} for f in meta['fields'] if f['name'] in FIELDS[layer]];rows=[]
  for feature in features:
   original=shape(feature['geometry'])
   if not original.is_valid:
    reason=shapely.is_valid_reason(original);repaired=shapely.make_valid(original)
    if repaired.geom_type=='GeometryCollection':repaired=unary_union([g for g in repaired.geoms if g.geom_type in ['Polygon','MultiPolygon']])
    if repaired.is_empty or repaired.geom_type not in ['Polygon','MultiPolygon'] or not repaired.is_valid:raise ValueError('Unrepairable FEMA source geometry')
    unresolved.append({'reason':'Source polygon made valid for analysis; raw cached bytes retained','layer':name,'OBJECTID':feature['properties']['OBJECTID'],'source_geometry_issue':reason,'source_geographic_area':original.area,'repaired_geographic_area':repaired.area});original=repaired
   full=project_g(original);clipped=full.intersection(utm)
   if clipped.is_empty or clipped.area<.001:continue
   p=feature['properties'];id=str(p.get('FLD_AR_ID') or p.get('FIRM_PAN') or p.get('LOMR_ID') or p.get('STUDY_ID'))
   if id=='None':id='OBJECTID:'+str(p['OBJECTID'])
   properties={**p,'source_id':id,'source_global_id':p.get('GlobalID'),'product_status':'effective_NFHL','clipped_area_m2':clipped.area}
   if 'EFF_DATE' in p:properties['effective_date_utc']=date(p['EFF_DATE'])
   if 'PRE_DATE' in p:properties['preliminary_date_utc']=date(p['PRE_DATE']);properties['preliminary_date_note']='Original numeric date preserved; unrepresentative/sentinel dates normalize to null, not a preliminary product.'
   rows.append({'type':'Feature','id':id,'geometry':mapping(shapely.transform(clipped,back.transform,interleaved=False)),'properties':properties})
  tables[name]={'type':'FeatureCollection','features':rows}
 zones=tables['hazard_zones']['features'];panels=tables['effective_panels']['features'];zone_g=[project_g(shape(f['geometry'])) for f in zones];panel_g=[project_g(shape(f['geometry'])) for f in panels]
 for zone,g in zip(zones,zone_g):
  refs=[{'FIRM_PAN':p['properties']['FIRM_PAN'],'effective_date_utc':p['properties']['effective_date_utc'],'intersection_m2':g.intersection(pg).area} for p,pg in zip(panels,panel_g) if g.intersection(pg).area>.01]
  zone['properties']['effective_panel_refs']=refs
  if not refs:unresolved.append({'source_id':zone['id'],'reason':'No intersecting effective panel metadata'})
 coverage={};available=unary_union([project_g(shape(f['geometry'])) for f in tables['availability']['features']]);zone_union=unary_union(zone_g);panel_union=unary_union(panel_g)
 for name,g in scopes.items():
  intersection=g.intersection(utm);coverage[name]={'scope_area_m2':g.area,'query_clip_area_m2':intersection.area,'availability_m2':g.intersection(available).area,'zones_mapped_m2':g.intersection(zone_union).area,'panel_metadata_m2':g.intersection(panel_union).area,'unmapped_in_query_m2':intersection.difference(zone_union).area,'mapped_hazard_area_sfha_m2':g.intersection(unary_union([z for z,f in zip(zone_g,zones) if f['properties']['SFHA_TF']=='T'])).area}
 if zone_union.area>sum(g.area for g in zone_g)+.01:raise ValueError('Zone union area invariant failed')
 overlap=sum(g.area for g in zone_g)-zone_union.area
 if overlap>.05:unresolved.append({'reason':'Source hazard-zone polygon overlap','overlap_m2':overlap})
 parcel_path=ROOT/active['relative_path']/'parcels.json';parcels=read(parcel_path)['features'];tree=STRtree(zone_g);joins=[];area_failures=0
 for parcel in parcels:
  g=project_g(shape(parcel['geometry']));hits=[]
  for idx in tree.query(g):
   idx=int(idx);a=g.intersection(zone_g[idx]).area
   if a<=.01:continue
   if a>g.area+.01:area_failures+=1
   hits.append({'source_zone_id':zones[idx]['id'],'FLD_ZONE':zones[idx]['properties']['FLD_ZONE'],'ZONE_SUBTY':zones[idx]['properties']['ZONE_SUBTY'],'SFHA_TF':zones[idx]['properties']['SFHA_TF'],'intersection_m2':a})
  if hits:joins.append({'parcel_feature_id':parcel['id'],'parcel_id':parcel['properties']['parcel_id'],'zone_intersections':hits,'scope':'mapped parcel intersection, not building/insurance determination'})
 if area_failures:raise ValueError('Spatial join area validation failed')
 out=ROOT/'data/flood';out.mkdir(parents=True,exist_ok=True);packet_path=out/'effective_nfhl.json';previous=read(packet_path).get('artifacts',{}) if packet_path.exists() else {}
 # A fixed visual lift on the flat prototype is not a vertical flood/water elevation.
 from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf
 stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z);stage.SetMetadata('metersPerUnit',1.);rootprim=UsdGeom.Xform.Define(stage,'/World/Information/FemaEffectiveFloodHazards');rootprim.CreateVisibilityAttr('invisible');rootprim.GetPrim().SetCustomData({'classification':'FEMA mapped effective hazard information; not live flood/depth','sourceSnapshot':active['snapshot'],'displayLiftMeters':.035,'displayLiftMeaning':'flat prototype cartographic offset only, not flood elevation','productStatus':'effective_NFHL'})
 origin=project.transform(*read(ROOT/'config/study_area.json')['local_origin_wgs84'])
 source_times=sorted({a.get('retrieved_utc') for a in client.accesses if a.get('retrieved_utc')});effective_dates=sorted({f['properties']['effective_date_utc'] for f in panels if f['properties']['effective_date_utc']})
 rootprim.GetPrim().SetCustomDataByKey('sourceContext',{'publisher':'FEMA','sourceSnapshot':active['snapshot'],'acquisitionStart':'unknown','acquisitionEnd':'unknown','effectiveDate':effective_dates[0] if len(effective_dates)==1 else 'varies by effective panel; inspect packet','retrievedUTC':source_times[-1] if source_times else 'unknown','quality':'effective NFHL cartographic context, not flood depth/elevation','sourceURL':BASE})
 for i,(f,g) in enumerate(zip(zones,zone_g)):
  if f['properties']['SFHA_TF']!='T':
   node=UsdGeom.Xform.Define(stage,str(rootprim.GetPath())+'/Zone'+str(i)).GetPrim();node.SetCustomData({'sourceZoneId':f['id'],'zoneCode':f['properties']['FLD_ZONE'],'sourceStatus':'effective_NFHL','displayPolicy':'inspector_only_no_fill','sourcePropertiesJSON':json.dumps(f['properties'])});continue
  points=[];indices=[];counts=[]
  for triangle in shapely.constrained_delaunay_triangles(g).geoms:
   coords=list(triangle.exterior.coords)[:-1];start=len(points);points.extend([(x-origin[0],y-origin[1],.035) for x,y in coords]);indices.extend(range(start,start+3));counts.append(3)
  triangle_area=sum(Polygon([(p[0]+origin[0],p[1]+origin[1]) for p in points[start:start+3]]).area for start in range(0,len(points),3))
  if abs(triangle_area-g.area)>.05:raise ValueError('Flood overlay triangulation area mismatch')
  mesh=UsdGeom.Mesh.Define(stage,str(rootprim.GetPath())+'/Zone'+str(i));mesh.CreateSubdivisionSchemeAttr('none');mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr(counts);mesh.CreateFaceVertexIndicesAttr(indices);mesh.CreateDoubleSidedAttr(True);mesh.GetPrim().SetCustomDataByKey('sourceZoneId',f['id']);mesh.GetPrim().SetCustomDataByKey('zoneCode',f['properties']['FLD_ZONE']);mesh.GetPrim().SetCustomDataByKey('sourceStatus','effective_NFHL');mesh.GetPrim().SetCustomDataByKey('sourcePropertiesJSON',json.dumps(f['properties']));mesh.GetPrim().SetCustomDataByKey('displayPolicy','opaque_blue_mapped_SFHA_cartographic_tint')
  color='#164f78' if f['properties']['SFHA_TF']=='T' else COLORS.get(f['properties']['FLD_ZONE'],'#a887bc');rgb=tuple(int(color[j:j+2],16)/255 for j in [1,3,5]);mesh.CreateDisplayColorAttr([Gf.Vec3f(*rgb)])
  mesh.CreateDisplayOpacityAttr([1.]);mat=UsdShade.Material.Define(stage,'/World/FloodMaterials/M'+str(i));shader=UsdShade.Shader.Define(stage,str(mat.GetPath())+'/Surface');shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb));shader.CreateInput('opacity',Sdf.ValueTypeNames.Float).Set(1.);mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mat)
 stage.GetRootLayer().customLayerData={'sourceSnapshot':active['snapshot'],'defaultVisibility':'invisible','overlayRole':'mapped hazard information only; no water simulation'};layer_path=ROOT/'scene/fema_effective_hazards.usda';safe_write(layer_path,stage.GetRootLayer().ExportToString(),previous)
 # Isolated review-only camera and visibility opinion; never a user/base camera.
 focus=unary_union([g.intersection(scopes['main_street']) for f,g in zip(zones,zone_g) if f['properties']['SFHA_TF']=='T'])
 if focus.is_empty:raise ValueError('No mapped MainStreet SFHA for review camera')
 target=Gf.Vec3d(focus.centroid.x-origin[0],focus.centroid.y-origin[1],.035);extent=max(100.,focus.bounds[2]-focus.bounds[0],focus.bounds[3]-focus.bounds[1]);review=Usd.Stage.CreateInMemory();camera=UsdGeom.Camera.Define(review,'/World/Cameras/FemaMainStreetHazardEvidence');camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(target+Gf.Vec3d(-extent*.8,-extent*.9,extent*1.15),target,Gf.Vec3d(0,0,1)).GetInverse());camera.CreateFocalLengthAttr(32);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25)
 UsdGeom.Imageable(review.OverridePrim(str(rootprim.GetPath()))).CreateVisibilityAttr('inherited');review.GetRootLayer().customLayerData={'reviewOnly':True,'sourceSnapshot':active['snapshot'],'hazardLayerSha256':sha(layer_path),'cameraTarget':'centroid of actual effective SFHA intersection with official MainStreet polygon; not water level','mappedSFHAFocusAreaM2':focus.area};review_path=ROOT/'scene/fema_hazard_review.usda';safe_write(review_path,review.GetRootLayer().ExportToString(),previous)
 # Geographic coverage artifact, all source polygons clipped to official union.
 x0,y0,x1,y1=utm.bounds;scale=min(900/(x1-x0),680/(y1-y0));svg=[]
 def path_svg(g):
  parts=[]
  for p in getattr(g,'geoms',[g]):
   if p.geom_type!='Polygon':continue
   for ring in [p.exterior,*p.interiors]:parts.append('M'+' L'.join(f'{(x-x0)*scale+25:.3f},{(y1-y)*scale+25:.3f}' for x,y in ring.coords)+' Z')
  return ' '.join(parts)
 for f,g in zip(zones,zone_g):svg.append('<path fill="'+('none' if f['properties']['SFHA_TF']!='T' else COLORS.get(f['properties']['FLD_ZONE'],'#a887bc'))+'" fill-rule="evenodd" stroke="#70808a" stroke-width=".5" d="'+path_svg(g)+'"><title>'+html.escape(f['id']+' | '+f['properties']['FLD_ZONE']+' | '+str(f['properties']['ZONE_SUBTY']))+'</title></path>')
 svg.append('<path fill="none" stroke="#111" stroke-width="2" d="'+path_svg(scopes['main_street'])+'"/>');map_path=out/'coverage.html';safe_write(map_path,'<!doctype html><meta charset="utf-8"><title>FEMA mapped effective hazards — College Park</title><h1>Mapped effective flood-hazard information</h1><p>Blue: A/AE special flood hazard; outline only: X (preserve subtype). Black: Main Street. Clipped to official neighborhood/Main Street union. Not live flooding or water depth.</p><svg viewBox="0 0 950 750" style="max-width:950px">'+''.join(svg)+'</svg>',previous)
 dependencies={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [bound_path,parcel_path,pilot_path,ROOT/'config/study_area.json',Path(__file__)]}
 for access in client.accesses:
  target=access['url'];cache=client.cache/(hashlib.sha256(target.encode()).hexdigest()+'.json');dependencies[str(cache.relative_to(ROOT)).replace('\\','/')]=sha(cache)
  prov=cache.with_suffix('.provenance.json')
  if prov.exists():dependencies[str(prov.relative_to(ROOT)).replace('\\','/')]=sha(prov)
 artifacts={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in [layer_path,map_path,review_path]}
 unresolved.extend([{'reason':'Acquisition/survey date of original hazard studies is not supplied by these feature layers; effective panel date is not survey or retrieval date.'},{'reason':'LOMA/property-specific determinations and FIS supporting profiles are not joined; parcel intersections are informational only.'},{'reason':'Publisher-specific dataset reuse license absent from service metadata; retain FEMA attribution and service provenance, do not imply certification.'},{'reason':'Scene lift .035m is flat cartographic placement, not terrain-draped shoreline or measured water surface; lake/shore intersections remain mapped hazard polygons.'},{'reason':'Parcel joins cover current extracted parcels only; full official boundary hazard query does not invent parcels outside extraction.'}])
 packet={'source_snapshot':active['snapshot'],'created_utc':now(),'publisher':'Federal Emergency Management Agency (FEMA)','source_url':BASE,'official_map_service_center':'https://msc.fema.gov/portal/home','source_product':'effective_NFHL','preliminary_products_imported':False,'preliminary_status':'separate product not fetched; PRE_DATE attribute is not product status','source_xy_crs':'EPSG:4269 NAD83 geographic degrees','normalized_xy_crs':'EPSG:4326 WGS84 geographic degrees','analysis_crs':'EPSG:32617 meters','vertical_values':'Original STATIC_BFE/DEPTH fields and LEN_UNIT/V_DATUM preserved; no Z conversion or water-depth surface; -9999 source sentinel retained verbatim','reuse_conditions':'Public official service; explicit dataset license not supplied in layer metadata (unresolved); attribution and original provenance retained','source_requests':client.accesses,'metadata':metadata,'normalized_field_dictionary':{'source_id':'FLD_AR_ID/FIRM_PAN/LOMR_ID/STUDY_ID; original string key, OBJECTID fallback identified','source_global_id':'Original source GlobalID, nullable; GFID is dataset-level and is not used as feature identity','effective_date_utc':'EFF_DATE epoch milliseconds normalized to UTC YYYY-MM-DD; original preserved','preliminary_date_utc':'PRE_DATE within1900–2100 normalized; source year9999 sentinel becomes null, not preliminary product status','product_status':'effective_NFHL; source service product classification','clipped_area_m2':'EPSG32617 intersection area in square meters','effective_panel_refs':'All positive-area intersecting panel IDs/dates; no single-date nearest assignment'},'field_dictionary':dictionary,'first_five_safe_rows':{name:[f['properties'] for f in table['features'][:5]] for name,table in tables.items()},'tables':tables,'coverage_boundaries':{'type':'FeatureCollection','features':bounds},'coverage':coverage,'parcel_joins':joins,'spatial_validation':{'parcel_features_checked':len(parcels),'join_records':len(joins),'join_area_failures':area_failures,'zone_overlap_m2':overlap,'geometry_valid':all(g.is_valid for g in zone_g),'panel_join_method':'positive-area intersection inEPSG32617; all intersecting panel dates retained, no nearest-date assumption'},'unresolved':unresolved,'dependencies':dependencies,'artifacts':artifacts,'default_on':False,'scene_prim':'/World/Information/FemaEffectiveFloodHazards','scene_lift_m':.035,'display_policy':'Only SFHA=T polygons filled in scene; X retained in inspector with no scene fill. Dedicated review layer/camera is not active.','limits':['Mapped effective hazard zones, not live flooding, water depth, engineering simulation or parcel insurance determination.','Existing effective regulatory map product; historic/preliminary/under-construction/proposed products are not merged.','No private BOOMS data accessed.']}
 if read(ROOT/'data/processed/active.json')['snapshot']!=active['snapshot']:raise ValueError('Snapshot changed during flood build')
 atomic_json(packet_path,packet);atomic_json(out/'effective_nfhl.receipt.json',{'source_snapshot':active['snapshot'],'packet_sha256':sha(packet_path),'packet_path':'data/flood/effective_nfhl.json'});print(json.dumps({'packet':str(packet_path),'zone_count':len(zones),'panels':len(panels),'revisions':len(tables['effective_revisions']['features']),'coverage':coverage,'parcel_joins':len(joins)},indent=2));return packet

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def validate_packet(root=ROOT):
 root=Path(root).resolve();packet_path=root/'data/flood/effective_nfhl.json';packet=read(packet_path);receipt=read(root/'data/flood/effective_nfhl.receipt.json')
 if receipt.get('packet_path')!='data/flood/effective_nfhl.json' or receipt.get('source_snapshot')!=packet.get('source_snapshot') or receipt.get('packet_sha256')!=sha(packet_path):raise ValueError('FEMA normalized packet checksum/snapshot changed')
 if not isinstance(packet.get('dependencies'),dict) or not packet['dependencies'] or not isinstance(packet.get('artifacts'),dict) or not packet['artifacts']:raise ValueError('FEMA dependency and artifact checksums required')
 if packet['source_snapshot']!=read(root/'data/processed/active.json')['snapshot']:raise ValueError('FEMA snapshot stale')
 for relative,digest in {**packet['dependencies'],**packet['artifacts']}.items():
  if sha(inside(root,relative))!=digest:raise ValueError('FEMA cached evidence changed: '+relative)
 return packet
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');build(p.parse_args().offline)
