"""Verified historical SJRWMD context packet and optional default-off USD."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
import argparse,collections,datetime,hashlib,html,json,math,re,struct,sys,urllib.request,zipfile,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
import shapely
from shapely.geometry import Polygon,shape,mapping,box,Point
from shapely.ops import unary_union
from pyproj import Transformer,CRS
from pxr import Usd,UsdGeom,UsdShade,UsdUtils,Sdf,Gf,Work
Work.SetConcurrencyLimit(1)
from data_pipeline import Client,arcgis,atomic_json,now
from build_corridor_ground import mesh_footprint,polygons

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def fresh_scene(root):
    """Fresh anonymous layer copies; never reload or save an editor's layers."""
    copies={}
    def copy(path):
        path=Path(path).resolve()
        if str(path) in copies:return copies[str(path)]
        anchor=Sdf.Layer.FindOrOpen(str(path));layer=Sdf.Layer.OpenAsAnonymous(str(path));copies[str(path)]=layer
        children=[Sdf.ComputeAssetPathRelativeToLayer(anchor,p) for p in layer.subLayerPaths]
        UsdUtils.ModifyAssetPaths(layer,lambda value:Sdf.ComputeAssetPathRelativeToLayer(anchor,value))
        layer.subLayerPaths=[copy(child).identifier for child in children]
        return layer
    stage=Usd.Stage.Open(copy(root/'scene/college_park_connected.usda'))
    return stage,copies

def geometry_fingerprint(source):
    cache=UsdGeom.XformCache();records=[]
    for path in ('/World/Ground','/World/Water'):
        parent=source.GetPrimAtPath(path)
        if not parent:records.append({'path':path,'missing':True});continue
        for prim in Usd.PrimRange(parent):
            if not prim.IsA(UsdGeom.Mesh):continue
            mesh=UsdGeom.Mesh(prim);records.append({'path':str(prim.GetPath()),'points':[[float(v) for v in p] for p in mesh.GetPointsAttr().Get() or []],
                'counts':list(mesh.GetFaceVertexCountsAttr().Get() or []),'indices':list(mesh.GetFaceVertexIndicesAttr().Get() or []),
                'world_transform':[[float(v) for v in row] for row in cache.GetLocalToWorldTransform(prim)],'visibility':str(UsdGeom.Imageable(prim).ComputeVisibility())})
    return hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()

def previous_outputs(root):
    folder=root/'data/transport/water_context';receipt_path=folder/'layer_receipt.json';layer=root/'scene/water_landcover_context.usda';coverage=folder/'coverage.svg';packet=root/'data/transport/water_context.json'
    if not receipt_path.exists():
        if layer.exists() or coverage.exists():raise ValueError('Existing water layer/coverage lacks generation receipt; preserve manual content before rebuilding')
        return {}
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'));expected={layer:receipt['layer_sha256'],packet:receipt['packet_sha256']}
    old=json.loads(packet.read_text(encoding='utf-8'))
    # Upgrade an older receipt only if its SVG exactly matches its receipted
    # previous packet's deterministic coverage rendering.
    expected[coverage]=receipt.get('coverage_sha256') or hashlib.sha256(coverage_svg(old).encode('utf-8')).hexdigest()
    for path,digest in expected.items():
        loaded=Sdf.Layer.Find(str(path)) if path.suffix=='.usda' else None
        if loaded and loaded.dirty:raise ValueError('Unsaved water-layer edits; rebuild refused')
        if not path.is_file() or sha(path)!=digest:raise ValueError('Water output manually changed or missing; rebuild refused: '+path.name)
    return expected

def preserve_previous(root,expected):
    if not expected:return
    if any(not path.is_file() or sha(path)!=digest for path,digest in expected.items()):raise ValueError('Water outputs changed during build; no overwrite performed')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=root/'data/transport/water_context/backups'/stamp;folder.mkdir(parents=True)
    for path in [*expected,root/'data/transport/water_context/layer_receipt.json']:
        if path.exists():shutil.copy2(path,folder/path.name)
    atomic_json(folder/'backup_manifest.json',{'created_utc':stamp,'files':{p.name:d for p,d in expected.items()},'rollback':'Restore these generated artifacts together; active/manual source layers were never written.'})
def plain(value):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]*>',' ',value or ''))).replace('\ufffd','').strip()
def date(value):return datetime.datetime.fromtimestamp(value/1000,datetime.timezone.utc).isoformat() if isinstance(value,(float,int)) else None
def binary(url,path,offline=False,limit=8388608):
    receipt=path.with_suffix(path.suffix+'.receipt.json')
    if path.exists():
        meta=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {'url':url,'retrieved_utc':None,'retrieval_quality':'existing_cache_original_receipt_unavailable','sha256':sha(path)}
        if meta['sha256']!=sha(path):raise ValueError('Binary cache checksum mismatch')
        return path.read_bytes(),meta
    if offline:raise ValueError('Offline missing resource '+url)
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'TWIN environmental GIS context'}),timeout=30) as response:raw=response.read(limit+1)
    if len(raw)>limit:raise ValueError('Resource exceeds bounded download')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);meta={'url':url,'retrieved_utc':now(),'retrieval_quality':'network_response','sha256':sha(path)};atomic_json(receipt,meta);return raw,meta

def index_shapes(raw):
    """Read bounded official polygon SHP/DBF index, without extra GIS packages."""
    import io
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names=archive.namelist();shp=archive.read(next(n for n in names if n.lower().endswith('.shp')));dbf=archive.read(next(n for n in names if n.lower().endswith('.dbf')));prj=archive.read(next(n for n in names if n.lower().endswith('.prj'))).decode('utf-8')
    count=struct.unpack_from('<I',dbf,4)[0];header,length=struct.unpack_from('<HH',dbf,8);fields=[];offset=32
    while dbf[offset]!=13:
        name=dbf[offset:offset+11].split(b'\x00')[0].decode('ascii');fields.append((name,chr(dbf[offset+11]),dbf[offset+16]));offset+=32
    rows=[]
    for i in range(count):
        start=header+i*length;cursor=start+1;row={}
        for name,kind,width in fields:
            value=dbf[cursor:cursor+width].decode('cp1252').strip();cursor+=width
            row[name]=None if not value else value
        rows.append(row)
    features=[];offset=100;index=0
    while offset<len(shp):
        number,words=struct.unpack_from('>II',shp,offset);offset+=8;body=shp[offset:offset+words*2];offset+=words*2;kind=struct.unpack_from('<I',body)[0]
        if kind==0:index+=1;continue
        if kind not in (5,15,25):raise ValueError('Unexpected DEM index geometry type')
        nparts,npoints=struct.unpack_from('<II',body,36);starts=list(struct.unpack_from('<'+'I'*nparts,body,44))+[npoints];points=[struct.unpack_from('<dd',body,44+4*nparts+i*16) for i in range(npoints)];outer=[];holes=[]
        for a,b in zip(starts,starts[1:]):
            ring=points[a:b];polygon=Polygon(ring)
            (holes if polygon.exterior.is_ccw else outer).append(polygon)
        geometry=unary_union(outer).difference(unary_union(holes))
        features.append({'id':'dem-index:'+str(number),'properties':rows[index],'geometry':geometry});index+=1
    return features,CRS.from_wkt(prj),fields

def shoreline_comparison(a,b,step=5,clip_boundary=None):
    values=[]
    first=a.boundary.difference(clip_boundary.buffer(.5)) if clip_boundary is not None else a.boundary
    second=b.boundary.difference(clip_boundary.buffer(.5)) if clip_boundary is not None else b.boundary
    for source,target in ((first,second),(second,first)):
        if source.is_empty or target.is_empty:continue
        for i in range(max(2,math.ceil(source.length/step))):values.append(source.interpolate(min(i*step,source.length)).distance(target))
    values.sort();intersection=a.intersection(b).area;union=a.union(b).area
    return {'iou':intersection/union if union else None,'symmetric_difference_m2':a.symmetric_difference(b).area,'median_boundary_distance_m':values[len(values)//2] if values else None,'p95_boundary_distance_m':values[min(len(values)-1,int(len(values)*.95))] if values else None,'hausdorff_m':first.hausdorff_distance(second) if not first.is_empty and not second.is_empty else None,'meaning':'Cross-source historical boundary disagreement, not surveyed error; artificial study-frame edges excluded from shoreline distances.'}

def build(root=ROOT,offline=False):
    expected=previous_outputs(root)
    config=json.loads((root/'config/water_context_sources.json').read_text(encoding='utf-8'));study=json.loads((root/'config/study_area.json').read_text(encoding='utf-8'));active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'));area=box(*study['acquisition_bbox_wgs84'])
    cache=root/'data/cache/water_context';cache.mkdir(parents=True,exist_ok=True);client=Client(cache,offline=offline)
    projection=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=projection.transform(*study['local_origin_wgs84'])
    def local(x,y):a,b=projection.transform(x,y);return a-ox,b-oy
    local_area=shapely.transform(area,local,interleaved=False)
    source,source_copies=fresh_scene(root);source_fingerprint=geometry_fingerprint(source);xforms=UsdGeom.XformCache();ground=mesh_footprint(source.GetPrimAtPath('/World/Ground'),xforms)
    ground_points=UsdGeom.Mesh(source.GetPrimAtPath('/World/Ground')).GetPointsAttr().Get();ground_matrix=xforms.GetLocalToWorldTransform(source.GetPrimAtPath('/World/Ground'));ground_z=[float(ground_matrix.Transform(Gf.Vec3d(p))[2]) for p in ground_points]
    packet={'schema':'twin.water-landcover/1.0','source_snapshot':active['snapshot'],'built_utc':now(),'offline_cache_replay':offline,'study_bbox_wgs84':study['acquisition_bbox_wgs84'],'publisher':config['publisher'],'official_catalog':config['official_catalog'],'sources':{},'collections':{},'field_dictionary':{},'quality':{},'unresolved':[]}
    domain={};local_features={}
    for name in ('water','landcover'):
        spec=config[name];collection,metadata=arcgis(client,spec,study['acquisition_bbox_wgs84']);item=client.get('https://www.arcgis.com/sharing/rest/content/items/'+spec['item_id'],{'f':'json'})
        decoded={f['name']:{str(v['code']):v['name'] for v in (f.get('domain') or {}).get('codedValues',[])} for f in metadata['fields']}
        if name=='landcover':domain=decoded
        features=[];local_rows=[];rejects=[]
        for feature in collection['features']:
            geometry=shapely.force_2d(shape(feature['geometry']))
            if not geometry.is_valid or geometry.is_empty:rejects.append(feature['properties']['OBJECTID']);continue
            clipped=geometry.intersection(area)
            if clipped.is_empty:continue
            props={key:feature['properties'].get(key) for key in spec['fields']}
            props.update(source_id=name,provider_object_id=str(props['OBJECTID']),quality='historical_published_context_not_surveyed_or_current',condition_status='historical_observation',acquisition_start=spec['acquisition_start'],acquisition_end=spec['acquisition_end'],effective_date=spec['effective_date'],source_updated=spec.get('source_updated'))
            if name=='landcover':
                props.update(landcover_code=str(props['LCCODE']) if props['LCCODE'] is not None else None,landcover_label=decoded['LCCODE'].get(str(props['LCCODE'])),landuse_code=str(props['LUCODE']) if props['LUCODE'] is not None else None,landuse_label=decoded['LUCODE'].get(str(props['LUCODE'])))
                if 'under construction' in (props['landcover_label'] or '').lower():props['condition_status']='historical_under_construction_not_current'
            fid='sjrwmd:'+name+':'+props['provider_object_id'];features.append({'type':'Feature','id':fid,'properties':props,'geometry':mapping(clipped)});local_rows.append({'id':fid,'properties':props,'geometry':shapely.transform(clipped,local,interleaved=False)})
        packet['collections'][name]={'type':'FeatureCollection','features':features};local_features[name]=local_rows
        accesses=[a for a in client.accesses if a['url'].split('?')[0] in (spec['url'],spec['url']+'/query')];times=[a['retrieved_utc'] for a in accesses if a.get('retrieved_utc')]
        native=CRS.from_epsg(metadata['extent']['spatialReference'].get('latestWkid',metadata['extent']['spatialReference']['wkid']))
        packet['sources'][name]={'publisher':config['publisher'],'url':spec['url'],'item_id':spec['item_id'],'layer_name':metadata['name'],'item_owner':item.get('owner'),'item_modified_utc':date(item.get('modified')),'data_edit_utc':date(metadata.get('editingInfo',{}).get('dataLastEditDate')),'source_updated':spec.get('source_updated'),'acquisition_start':spec['acquisition_start'],'acquisition_end':spec['acquisition_end'],'effective_date':spec['effective_date'],'date_precision':spec['date_precision'],'request_retrieval_range_utc':[min(times),max(times)] if times else None,'native_crs':native.name,'native_epsg':native.to_epsg(),'horizontal_unit':native.axis_info[0].unit_name,'output_crs':'EPSG:4326','vertical_datum':'not applicable to 2D geometry; NHDELEVATION units/datum unverified and unused','reuse_conditions':plain(item.get('licenseInfo')),'request_receipts':accesses,'metadata_sha256':hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest()}
        packet['field_dictionary'][name]=[{'name':f['name'],'alias':f.get('alias'),'type':f.get('type'),'domain':decoded.get(f['name']) or None,'units':'source field units unknown; do not interpret as elevation/length' if f['name']=='NHDELEVATION' else 'classification code' if f['name'] in ('LCCODE','LUCODE','NHDFTYPE') else None} for f in metadata['fields'] if f['name'] in spec['fields']]
        union=unary_union([r['geometry'] for r in local_rows]);packet['quality'][name]={'source_returned':len(collection['features']),'clipped_features':len(features),'invalid_source_object_ids':rejects,'unique_object_ids':len({f['properties']['provider_object_id'] for f in features}),'coverage_area_m2':union.area,'study_area_fraction':union.intersection(local_area).area/local_area.area,'outside_ground_m2':union.difference(ground).area}
    accepted=[r for r in local_features['landcover'] if r['properties']['LCCODE'] is not None and 5000<=int(r['properties']['LCCODE'])<6000]
    packet['accepted_context_policy']={'water':'LCCODE5000-family decoded by official domain, Orange imageryDecember 2020 to March 2021; visual/historical context only.','landcover':'Official source coded classes; not parcel zoning or current physical surface.','older_waterbody':'August2012 update, reference shoreline only; wetlands and NHD types are not indiscriminately filled as open water.','proposed_features_activated':False,'water_level_or_depth_accepted':False}
    comparisons=[]
    for row in local_features['water']:
        candidates=[(candidate,row['geometry'].intersection(candidate['geometry']).area) for candidate in accepted];best=max(candidates,key=lambda item:item[1]) if candidates else None
        if best and best[1]>0:comparisons.append({'reference_id':row['id'],'name':row['properties'].get('NAME'),'landcover_id':best[0]['id'],**shoreline_comparison(row['geometry'],best[0]['geometry'],clip_boundary=local_area.boundary)})
    existing=[]
    parent=source.GetPrimAtPath('/World/Water')
    for prim in parent.GetChildren() if parent else []:
        if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':existing.append({'path':str(prim.GetPath()),'geometry':mesh_footprint(prim,xforms)})
    existing_comparisons=[]
    for row in accepted:
        matches=[(candidate,row['geometry'].intersection(candidate['geometry']).area) for candidate in existing];best=max(matches,key=lambda p:p[1]) if matches else None
        existing_comparisons.append({'context_id':row['id'],'existing_path':best[0]['path'] if best and best[1]>0 else None,'comparison':shoreline_comparison(row['geometry'],best[0]['geometry'].intersection(local_area),clip_boundary=local_area.boundary) if best and best[1]>0 else None})
    packet['shoreline_alignment']={'reference_vs_landcover':comparisons,'landcover_vs_existing_scene':existing_comparisons,'acceptance':'Historical disagreement measured; no surveyed alignment sign-off or replacement of active water.'}
    raw,index_receipt=binary(config['dem_index']['url'],cache/'DEMIndex_SJRWMD.zip',offline,config['dem_index']['maximum_bytes']);indices,index_crs,index_fields=index_shapes(raw);to_wgs=Transformer.from_crs(index_crs,4326,always_xy=True);index_matches=[]
    packet['binary_receipts']={'dem_index':{**index_receipt,'path':'data/cache/water_context/DEMIndex_SJRWMD.zip'}}
    for feature in indices:
        geometry=shapely.transform(feature['geometry'],to_wgs.transform,interleaved=False)
        if geometry.intersects(area):index_matches.append({'id':feature['id'],'properties':feature['properties'],'study_overlap_fraction':shapely.transform(geometry.intersection(area),local,interleaved=False).area/local_area.area})
    for key in ('dem_index','cfca_ne_dem','imagery_2009'):
        url=config[key]['metadata_url'];_,receipt=binary(url,cache/(key+'.html'),offline,2097152);packet['binary_receipts'][key+'_metadata']={**receipt,'path':'data/cache/water_context/'+key+'.html'}
    dem_config=json.loads((root/'config/terrain_sources.json').read_text(encoding='utf-8'));tile_union=unary_union([box(*tile['index_bbox_wgs84']) for tile in dem_config['tiles']])
    cfca=box(*config['cfca_ne_dem']['bbox_wgs84'])
    packet['elevation_candidates']={'historic_dem_index':{'publication_date':config['dem_index']['publication_date'],'metadata_url':config['dem_index']['metadata_url'],'source_crs':index_crs.name,'features_total':len(indices),'actual_study_intersections':index_matches,'receipt':index_receipt,'raster_values_loaded':False},'cfca_ne_2009':{**config['cfca_ne_dem'],'bbox_intersects_study':cfca.intersects(area),'accepted':False},'existing_usgs_2018_2019':{'acquisition_interval':dem_config['expected_acquisition_interval'],'vertical_datum':dem_config['expected_vertical_datum'],'vertical_unit':dem_config['expected_vertical_unit'],'indexed_study_overlap_fraction':shapely.transform(tile_union.intersection(area),local,interleaved=False).area/local_area.area,'new_raster_downloaded':False},'decision':'No historic SJRWMD DEM is installed or substituted for the independently investigated newer USGS terrain; index footprint is not proof of raster values/suitability.'}
    imagery=json.loads((root/'data/imagery/pilot_imagery_manifest.json').read_text(encoding='utf-8'));frame=imagery['references'][0]['export_extent'];aerial=box(frame['xmin'],frame['ymin'],frame['xmax'],frame['ymax']);to_utm=Transformer.from_crs(2236,32617,always_xy=True);aerial=shapely.transform(aerial,to_utm.transform,interleaved=False);aerial=shapely.transform(aerial,lambda x,y:(x-ox,y-oy),interleaved=False)
    packet['imagery_overlap']={'sjrwmd_2009':config['imagery_2009'],'ocpa_2025_pilot':{'acquisition':'2025-01','study_area_overlap_fraction':aerial.intersection(local_area).area/local_area.area,'water_context_overlap_m2':aerial.intersection(unary_union([r['geometry'] for r in accepted])).area,'scope':'Existing pilot export only; not full neighborhood aerial coverage.'},'landcover_source_imagery':{'county':'Orange','acquisition_start':'2020-12','acquisition_end':'2021-03','effective_today':False}}
    # A bounded dated reference for an actual named shoreline, not a texture.
    adair=next(row for row in local_features['water'] if row['properties'].get('NAME')=='Lake Adair')
    to_state=Transformer.from_crs(32617,2236,always_xy=True)
    extent=shapely.transform(adair['geometry'].buffer(45),lambda x,y:to_state.transform(x+ox,y+oy),interleaved=False).bounds
    export=client.get('https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/export',{'bbox':','.join(map(str,extent)),'bboxSR':2236,'imageSR':2236,'size':'1024,768','format':'jpg','f':'json'})
    image_path=cache/'lake_adair_2025.jpg';_,image_receipt=binary(export['href'],image_path,offline,4194304)
    frame=export['extent'];to_local=Transformer.from_crs(2236,32617,always_xy=True)
    def pixel(x,y):
        e=frame['xmin']+x/1024*(frame['xmax']-frame['xmin']);n=frame['ymax']-y/768*(frame['ymax']-frame['ymin']);e,n=to_local.transform(e,n);return [e-ox,n-oy]
    corners=[pixel(x,y) for x,y in ((0,0),(1024,0),(0,768),(1024,768))]
    residual=math.hypot(corners[3][0]-(corners[1][0]+corners[2][0]-corners[0][0]),corners[3][1]-(corners[1][1]+corners[2][1]-corners[0][1]))
    packet['shoreline_aerial_reference']={'source':'OCPA Aerials2025','acquisition':'2025-01','reuse':'Local review only; not redistributed as texture or source pixels in Git.','image_path':str(image_path.relative_to(root)).replace('\\','/'),'image_api_path':'/water-reference/lake-adair-2025','image_sha256':image_receipt['sha256'],'receipt':image_receipt,'width':1024,'height':768,'extent_epsg2236':frame,'corners_local_m':corners,'display_affine_residual_m':residual,'native_accuracy':'unknown; export sampling is not source accuracy','inspection_status':'Actual JPEG viewed: visible lake portion, roads and irregular vegetated banks. Study-frame clipping and tree canopy limit shoreline interpretation; no surveyed/current shoreline sign-off.'}
    packet['ground_intersection']={'actual_ground_z_range':list((min(ground_z),max(ground_z))),'context_landcover_display_z_m':.008,'context_water_display_z_m':.04,'display_z_is_water_elevation':False,'water_surface_ground_offset_m':.04-max(ground_z),'flat_ground_only':max(ground_z)-min(ground_z)<.001,'outside_ground_m2':unary_union([r['geometry'] for r in accepted]).difference(ground).area,'decision':'Flat display overlays only; no water/terrain hydrological intersection or elevation claim.'}
    packet['unresolved']=['Actual water-surface elevation/datum/depth and current shoreline remain unverified; NHDELEVATION is not used.','Historical and land-cover boundaries differ; source-scale/date disagreement stays visible.','Landcover labels are not current parcel use, parking geometry, canopy inventory or zoning.','Historic DEM index/raster suitability is separate; district properties are not assumed to cover urban Orlando.','No private BOOMS or held2026 source data imported.']
    packet['display']={'bounds':list(local_area.bounds),'map_crs':'local EPSG32617 metres','local_origin_wgs84':study['local_origin_wgs84'],'water':{'type':'FeatureCollection','features':[{'type':'Feature','id':r['id'],'properties':r['properties'],'geometry':mapping(r['geometry'])} for r in accepted]},'landcover':{'type':'FeatureCollection','features':[{'type':'Feature','id':r['id'],'properties':r['properties'],'geometry':mapping(r['geometry'])} for r in local_features['landcover']]},'reference':{'type':'FeatureCollection','features':[{'type':'Feature','id':r['id'],'properties':r['properties'],'geometry':mapping(r['geometry'])} for r in local_features['water']]}}
    packet['display']['existing_water']={'type':'FeatureCollection','features':[{'type':'Feature','id':row['path'],'properties':{'quality':'legacy_OSM_scene_water_reference','source_path':row['path']},'geometry':mapping(row['geometry'].intersection(local_area))} for row in existing if row['geometry'].intersects(local_area)]}
    packet['cache_receipts']=client.accesses
    packet['dependency_sha256']={relative:sha(root/relative) for relative in ('config/water_context_sources.json','config/study_area.json','data/processed/study_boundaries.geojson','config/terrain_sources.json')}
    packet['composed_geometry_fingerprint']=source_fingerprint
    folder=root/'data/transport/water_context';folder.mkdir(parents=True,exist_ok=True)
    current,_copies=fresh_scene(root)
    if geometry_fingerprint(current)!=source_fingerprint:raise ValueError('Contributing ground/water geometry changed during build')
    preserve_previous(root,expected)
    atomic_json(folder/'first_five.json',{name:{'fields':packet['field_dictionary'][name],'rows':[f['properties'] for f in packet['collections'][name]['features'][:5]]} for name in ('water','landcover')})
    atomic_json(folder/'packet.json',packet);atomic_json(root/'data/transport/water_context.json',packet)
    write_coverage(root,packet)
    create_layer(root,packet,source)
    print(json.dumps({'packet':str(folder/'packet.json'),'quality':packet['quality'],'accepted_water_context_features':len(accepted),'dem_index_intersections':index_matches,'ground':packet['ground_intersection']},indent=2));return packet

def create_layer(root,packet,source):
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    group=UsdGeom.Xform.Define(stage,'/World/WaterLandcoverContext');group.CreateVisibilityAttr('invisible')
    retrieval=packet['sources']['landcover']['request_retrieval_range_utc']
    source_data={'publisher':packet['publisher'],'sourceSnapshot':packet['source_snapshot'],'acquisitionStart':'2020-12','acquisitionEnd':'2021-03','effectiveDate':'unknown','retrievedUTC':retrieval[1] if retrieval else 'unknown','builtUTC':packet['built_utc'],'quality':'historical_reference_context_not_current_or_surveyed'}
    group.GetPrim().SetCustomDataByKey('sourceContext',source_data)
    def material(name,color):
        m=UsdShade.Material.Define(stage,'/World/WaterLandcoverContext/Materials/'+name);s=UsdShade.Shader.Define(stage,m.GetPath().AppendChild('Surface'));s.CreateIdAttr('UsdPreviewSurface');s.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));s.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.8);m.CreateSurfaceOutput().ConnectToSource(s.ConnectableAPI(),'surface');return m
    water=material('Water',(.13,.40,.49));green=material('Landscape',(.28,.41,.22));urban=material('UrbanContext',(.48,.46,.37))
    ground=mesh_footprint(source.GetPrimAtPath('/World/Ground'),UsdGeom.XformCache())
    for name,features,z in [('Landcover',packet['display']['landcover']['features'],.008),('Water',packet['display']['water']['features'],.04)]:
        for feature in features:
            geometry=shape(feature['geometry']).intersection(ground);points=[]
            for polygon in polygons(geometry):
                for triangle in shapely.constrained_delaunay_triangles(polygon).geoms:
                    if polygon.covers(triangle):points.extend([(x,y,z) for x,y in list(shapely.orient_polygons(triangle).exterior.coords)[:3]])
            if not points:continue
            path='/World/WaterLandcoverContext/'+name+'/Feature_'+feature['properties']['provider_object_id'];mesh=UsdGeom.Mesh.Define(stage,path);mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr([3]*(len(points)//3));mesh.CreateFaceVertexIndicesAttr(list(range(len(points))));mesh.CreateSubdivisionSchemeAttr('none');mesh.CreateDoubleSidedAttr(True)
            code=feature['properties'].get('LCCODE') or 0;UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(water if name=='Water' else green if 3000<=code<7000 or code in (1820,1850) else urban)
            info={**source_data,'sourceFeatureId':feature['id'],'sourceURL':packet['sources']['landcover']['url'],'classification':feature['properties'].get('landcover_label') or 'unknown'};mesh.GetPrim().SetCustomDataByKey('sourceContext',info)
    for feature in packet['display']['reference']['features']:
        geometry=shape(feature['geometry']).intersection(ground);points=[];counts=[]
        for polygon in polygons(geometry):
            for ring in (polygon.exterior,*polygon.interiors):
                coords=list(ring.coords);points.extend([(x,y,.055) for x,y in coords]);counts.append(len(coords))
        curve=UsdGeom.BasisCurves.Define(stage,'/World/WaterLandcoverContext/ShorelineReference/Feature_'+feature['properties']['provider_object_id']);curve.CreateTypeAttr('linear');curve.CreateCurveVertexCountsAttr(counts);curve.CreatePointsAttr(points);curve.CreateWidthsAttr([.16]);curve.SetWidthsInterpolation('constant');curve.CreateDisplayColorAttr([Gf.Vec3f(.92,.61,.15)])
        ref=packet['sources']['water'];times=ref['request_retrieval_range_utc'];curve.GetPrim().SetCustomDataByKey('sourceContext',{**source_data,'acquisitionStart':'unknown','acquisitionEnd':'unknown','effectiveDate':'unknown','sourceUpdated':'2012-08','retrievedUTC':times[1] if times else 'unknown','sourceFeatureId':feature['id'],'sourceURL':ref['url'],'quality':'historical_2012_waterbody_wetland_shoreline_reference'})
    stage.GetRootLayer().customLayerData={'purpose':'Optional default-off historical water/landcover context. Never replaces active water, source geometry, terrain or manual layers.','sourceSnapshot':packet['source_snapshot'],'packetSha256':sha(root/'data/transport/water_context.json'),'defaultVisible':False,'rollback':'Remove this optional sublayer; source/manual layers are untouched.'}
    output=root/'scene/water_landcover_context.usda';stage.GetRootLayer().Export(str(output))
    atomic_json(root/'data/transport/water_context/layer_receipt.json',{'layer_sha256':sha(output),'coverage_sha256':sha(root/'data/transport/water_context/coverage.svg'),'packet_sha256':sha(root/'data/transport/water_context.json'),'source_snapshot':packet['source_snapshot'],'default_off':True,'active_scene_modified':False})

def validate_water_context(root=ROOT):
    """Read-only activation/serving guard; never alters the scene assembly."""
    packet_path=root/'data/transport/water_context.json';packet=json.loads(packet_path.read_text(encoding='utf-8'));receipt=json.loads((root/'data/transport/water_context/layer_receipt.json').read_text(encoding='utf-8'))
    if json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))['snapshot']!=packet['source_snapshot']:raise ValueError('Water context snapshot changed; rebuild packet')
    if sha(packet_path)!=receipt['packet_sha256'] or sha(root/'scene/water_landcover_context.usda')!=receipt['layer_sha256']:raise ValueError('Water context packet/layer checksum mismatch')
    if receipt.get('coverage_sha256') and sha(root/'data/transport/water_context/coverage.svg')!=receipt['coverage_sha256']:raise ValueError('Water context coverage checksum mismatch')
    source,_copies=fresh_scene(root)
    if geometry_fingerprint(source)!=packet['composed_geometry_fingerprint']:raise ValueError('Contributing ground/water geometry or visibility changed; rebuild context')
    for relative,digest in packet['dependency_sha256'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root.resolve()) or sha(path)!=digest:raise ValueError('Water context dependency changed: '+relative)
    for item in packet['cache_receipts']:
        path=root/'data/cache/water_context'/(hashlib.sha256(item['url'].encode()).hexdigest()+'.json')
        if item.get('sha256') and sha(path)!=item['sha256']:raise ValueError('Water context request cache changed')
    image=root/packet['shoreline_aerial_reference']['image_path']
    if sha(image)!=packet['shoreline_aerial_reference']['image_sha256']:raise ValueError('Shoreline reference image changed')
    for item in packet['binary_receipts'].values():
        if sha(root/item['path'])!=item['sha256']:raise ValueError('Water context binary/metadata cache changed')
    return packet

def write_coverage(root,packet):
    (root/'data/transport/water_context/coverage.svg').write_text(coverage_svg(packet),encoding='utf-8')

def coverage_svg(packet):
    """Standalone clipped vector coverage map; contains no source image pixels."""
    from html import escape
    a,b,c,d=packet['display']['bounds'];width=c-a;height=d-b
    def ring(coords):return ' '.join(('M' if i==0 else 'L')+f'{x-a:.3f},{d-y:.3f}' for i,(x,y,*_) in enumerate(coords))+' Z'
    paths=[]
    for feature in packet['display']['landcover']['features']:
        geometry=shape(feature['geometry']);code=feature['properties']['LCCODE'] or 0;color='#6ba8bb' if 5000<=code<6000 else '#91b384' if 3000<=code<7000 or code in (1820,1850) else '#c7bfa9'
        content=' '.join(ring(list(line.coords)) for p in polygons(geometry) for line in (p.exterior,*p.interiors));label=escape(feature['properties']['landcover_label'] or 'Unknown')
        paths.append(f'<path d="{content}" fill="{color}" stroke="#647b6c" stroke-width="1" fill-rule="evenodd"><title>{label}</title></path>')
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="900" height="1400"><title>Clipped College Park SJRWMD historical land cover and water coverage</title><desc>Orange imagery December2020–March2021. Source classes are historical context, not current parcel use or water elevation.</desc><rect width="{width}" height="{height}" fill="#edf0e9"/>'+''.join(paths)+'</svg>'
    return svg

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args();build(offline=args.offline)
