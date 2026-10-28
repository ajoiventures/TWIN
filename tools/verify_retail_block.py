"""Bounded retail-row source verification and historical additive reconstruction."""
from pathlib import Path
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import sys,json,hashlib,datetime,urllib.parse,urllib.request,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
import shapely
from shapely.geometry import shape,box,mapping
from shapely.ops import unary_union
from pyproj import Transformer
from princeton_evidence import read_points
PINS=['292223001201050','292223001201042','292223001201041','292223001201031','292223001201030','292223001201032']

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');os.replace(temporary,path)

def acquire(live=False):
    active=read(ROOT/'data/processed/active.json');parcels=read(ROOT/active['relative_path']/'parcels.json')['features'];features=[f for f in parcels if f['properties']['parcel_id'] in PINS]
    if len(features)!=6:raise ValueError('Six retail tax records not resolved exactly')
    t=Transformer.from_crs(4326,32617,always_xy=True);back=Transformer.from_crs(32617,4326,always_xy=True)
    target=unary_union([shapely.transform(shape(f['geometry']),t.transform,interleaved=False) for f in features])
    region=target.buffer(8);wgs=shapely.transform(region,back.transform,interleaved=False)
    out=ROOT/'data/heights/retail_edgewater';out.mkdir(parents=True,exist_ok=True);points_path=out/'points.npz';evidence_path=out/'acquisition.json'
    if points_path.exists() and evidence_path.exists():
        evidence=read(evidence_path)
        if evidence['source_snapshot']!=active['snapshot'] or sha(points_path)!=evidence['points_sha256']:raise ValueError('Cached retail evidence changed')
        if not target.equals_exact(shape(evidence['target_union_utm']),1e-6):raise ValueError('Retail source parcel geometry changed')
        units=read(ROOT/'data/heights/vertical_unit_check.json')
        if not units.get('accepted') or units.get('ept_z_unit')!='meters':raise ValueError('Accepted EPT meter units required')
        return np.load(points_path)['points'],evidence,features,target
    units=read(ROOT/'data/heights/vertical_unit_check.json')
    if not units.get('accepted') or units.get('ept_z_unit')!='meters':raise ValueError('Accepted EPT meter units required')
    config=read(ROOT/'config/princeton_sources.json');config.update({'ept_max_depth':10,'maximum_ept_nodes':100,'maximum_node_bytes':16777216})
    points,receipt=read_points(config,wgs,ROOT,live);np.savez_compressed(points_path,points=points)
    safe=[]
    for f in features:safe.append(f['properties'])
    evidence={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'parcel_ids':PINS,'target_records':safe,
        'target_union_utm':mapping(target),'analysis_region_utm':mapping(region),'analysis_margin_m':8,
        'region_role':'bounded source search/context; never used as an extrusion footprint','point_count':len(points),
        'class_counts':{str(k):int(n) for k,n in zip(*np.unique(points[:,3].astype(int),return_counts=True))},
        'points_sha256':sha(points_path),'source':receipt,'dates':'Original accepted OrangeCounty2018 acquisition,2018-12-04 to2019-04-12; local flight day unknown',
        'aerial_review':'2025 OCPA frame is qualitative local review only; no tracing/textures/redistribution'}
    save(evidence_path,evidence);return points,evidence,features,target


def aerial(live=False):
    out=ROOT/'data/heights/retail_edgewater';receipt_path=out/'aerial_receipt.json';image=out/'aerial_2025_local_review.jpg'
    if receipt_path.exists() and image.exists():return read(receipt_path)
    if not live:raise RuntimeError('Offline aerial review cache missing')
    service='https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/export'
    params={'f':'json','bbox':'-81.38945,28.56305,-81.38865,28.56378','bboxSR':4326,'imageSR':3857,'size':'1000,1000','format':'jpg','transparent':'false'}
    url=service+'?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1024*1024)
    metadata=json.loads(raw)
    if 'error' in metadata:raise ValueError('Official aerial export error')
    with urllib.request.urlopen(metadata['href'],timeout=30) as response:pixels=response.read(8*1024*1024+1)
    if len(pixels)>8*1024*1024:raise ValueError('Aerial frame exceeded bound')
    image.write_bytes(pixels);receipt={'service':service,'request_url':url,'requested':params,'returned':metadata,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'image_sha256':sha(image),'nominal_year':2025,'actual_capture_date':'not independently established','eligibility':'local qualitative review only, no traced geometry or source-pixel assets'}
    save(receipt_path,receipt);return receipt


def reconstruct(live=False):
    from scipy import ndimage
    from pxr import Usd,UsdGeom,UsdShade,Gf,Sdf
    from constrain_scene import mesh_footprint
    from reconstruct_landmarks import planar_region_geometry,quantized_valid_geometry
    from princeton_evidence import write_surface
    from mesh_topology import closed_shell_report
    points,evidence,features,target=acquire(live);frame=aerial(live)
    out=ROOT/'data/heights/retail_edgewater';origin=Transformer.from_crs(4326,32617,always_xy=True).transform(-81.389,28.572)
    roi=shape(evidence['analysis_region_utm']);ground_all=points[points[:,3]==2,2]
    if len(ground_all)<100:raise ValueError('Insufficient classified ground')
    ground=float(np.median(ground_all));roof=points[(points[:,3]==6)&(points[:,2]>ground+2.5)&(points[:,2]<ground+4.1)]
    if len(roof)<1000:raise ValueError('Insufficient classified roof points; no parcel extrusion fallback')
    left,bottom=np.floor(roof[:,:2].min(axis=0));ix=np.floor(roof[:,0]-left).astype(int);iy=np.floor(roof[:,1]-bottom).astype(int)
    width,height=int(ix.max()+1),int(iy.max()+1);counts=np.bincount(iy*width+ix,minlength=height*width).reshape(height,width);raw=counts>=3
    mask=ndimage.binary_closing(raw,iterations=1)|raw
    auxiliary=points[np.isin(points[:,3],[1,6])&(points[:,2]>ground+2.5)&(points[:,2]<ground+4.1)]
    ax=np.floor(auxiliary[:,0]-left).astype(int);ay=np.floor(auxiliary[:,1]-bottom).astype(int)
    confirmed_infill=0
    for y,x in zip(*np.where(mask&~raw)):
        support=auxiliary[(ax==x)&(ay==y)]
        if len(support)<3:mask[y,x]=False
        else:confirmed_infill+=1
    labels,n=ndimage.label(mask);selected=[];raw_components=[]
    for label in range(1,n+1):
        yy,xx=np.where(labels==label)
        if len(xx)<12:continue
        geometry=unary_union([box(left+x,bottom+y,left+x+1,bottom+y+1) for y,x in zip(yy,xx)])
        overlap=geometry.intersection(target).area
        raw_components.append({'area_m2':geometry.area,'target_overlap_m2':overlap})
        if overlap>20:selected.append(geometry)
    if not selected:raise ValueError('No independent observed roof form intersecting retail records')
    observed=unary_union(selected);outline=observed.simplify(.65,preserve_topology=True)
    if not observed.buffer(.650001).covers(outline):raise ValueError('Roof edge simplification exceeds source tolerance')
    # The morphology never substitutes the tax envelope; it remains visibly
    # narrower and irregular, with rear extensions independently observed.
    if outline.area>target.area*.85:raise ValueError('Candidate too close to whole parcel envelope')
    current=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'));existing=[];overlap_records=[]
    if current.GetPrimAtPath('/World/Landmarks/EdgewaterRetail1305_1319'):raise ValueError('Retail reconstruction already visible; do not duplicate')
    local_roi=shapely.transform(roi,lambda x,y:(x-origin[0],y-origin[1]),interleaved=False)
    for prim in current.GetPrimAtPath('/World/Buildings').GetChildren():
        if not prim.IsA(UsdGeom.Mesh) or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        extent=UsdGeom.Mesh(prim).GetExtentAttr().Get()
        if not extent or box(extent[0][0],extent[0][1],extent[1][0],extent[1][1]).intersection(local_roi).area<=1:continue
        geometry=mesh_footprint(prim);absolute=shapely.transform(geometry,lambda x,y:(x+origin[0],y+origin[1]),interleaved=False)
        area=outline.intersection(absolute).area
        if area>.01:overlap_records.append({'usd_path':str(prim.GetPath()),'area_m2':area})
        existing.append(absolute)
    if existing:outline=outline.difference(unary_union(existing))
    if outline.area<100:raise ValueError('No substantial missing source-supported roof remains')
    q=roof[shapely.contains_xy(outline,roof[:,0],roof[:,1])];center=np.mean(q[:,:2],axis=0);A=np.c_[q[:,:2]-center,np.ones(len(q))];z=q[:,2];coef=np.array([0.,0.,np.median(z)])
    for _ in range(15):
        residual=A@coef-z;weights=np.minimum(1.,.10/np.maximum(np.abs(residual),1e-6));coef=np.linalg.lstsq(A*weights[:,None],z*weights,rcond=None)[0]
    residual=np.abs(A@coef-z);global_coef=[float(coef[0]),float(coef[1]),float(coef[2]+coef[0]*(left-center[0])+coef[1]*(bottom-center[1]))]
    near_ground=points[(points[:,3]==2)&shapely.contains_xy(outline.buffer(3),points[:,0],points[:,1])]
    if len(near_ground)<100:raise ValueError('Insufficient building-adjacent ground')
    ground=float(np.median(near_ground[:,2]));region={'geometry':outline,'coefficients_cell_xy':global_coef}
    geometry,proof=planar_region_geometry([region],{'left_utm_m':left,'bottom_utm_m':bottom,'cell_m':1},origin,ground)
    geometry,float_proof=quantized_valid_geometry(geometry,minimum_roof_xy_area_m2=0.)
    if float_proof['input_faces']!=float_proof['output_faces']:raise ValueError('Retail shell lost face')
    gate=closed_shell_report(*geometry)
    if not gate['passed_closed_shell']:raise ValueError('Retail shell is not closed')
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    path='/World/Landmarks/EdgewaterRetail1305_1319';root=UsdGeom.Xform.Define(stage,path)
    root.GetPrim().SetCustomData({'sourceSnapshot':evidence['source_snapshot'],'parcelIds':','.join(PINS),'siteAddressRange':'1305–1319 Edgewater Drive',
        'quality':'historical_classified_lidar_roof_derived_mass_current_wall_lines_unverified','physicalBuildingCount':'unknown; connected or abutting roof complex, not six buildings from six tax records',
        'aerialUse':'2025 local qualitative continuity review only; no traced geometry or pixels'})
    mesh=write_surface(stage,path+'/RoofDerivedBlock',geometry);mesh.GetPrim().CreateAttribute('primvars:st:indices',Sdf.ValueTypeNames.IntArray,custom=False).Block()
    materials={}
    for name,color in [('Wall',(.67,.65,.59)),('Roof',(.55,.56,.53))]:
        mat=UsdShade.Material.Define(stage,'/World/LandmarkMaterials/RetailBlock'+name);shader=UsdShade.Shader.Define(stage,str(mat.GetPath())+'/Surface');shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.92);mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');materials[name]=mat
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(materials['Wall']);roof_faces=[];offset=0
    for i,count in enumerate(geometry[1]):
        vertices=np.asarray([geometry[0][j] for j in geometry[2][offset:offset+count]]);offset+=count;normal=np.cross(vertices[1]-vertices[0],vertices[2]-vertices[0])
        if normal[2]>0:roof_faces.append(i)
    for name,indices in [('Roof',roof_faces),('Wall',[i for i in range(len(geometry[1])) if i not in set(roof_faces)])]:
        subset=UsdGeom.Subset.Define(stage,str(mesh.GetPath())+'/'+name+'Material');subset.CreateElementTypeAttr('face');subset.CreateFamilyNameAttr('materialBind');subset.CreateIndicesAttr(indices);UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(materials[name])
    UsdGeom.Subset.SetFamilyType(mesh,'materialBind',UsdGeom.Tokens.partition)
    camera=UsdGeom.Camera.Define(stage,'/World/Cameras/EdgewaterRetailBlockEvidence');local_center=outline.centroid
    target_view=Gf.Vec3d(local_center.x-origin[0],local_center.y-origin[1],1.8);eye=target_view+Gf.Vec3d(-60,-50,60);camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(eye,target_view,Gf.Vec3d(0,0,1)).GetInverse());camera.CreateFocalLengthAttr(32)
    per_parcel=[]
    t=Transformer.from_crs(4326,32617,always_xy=True)
    for feature in features:
        parcel=shapely.transform(shape(feature['geometry']),t.transform,interleaved=False);area=outline.intersection(parcel).area
        per_parcel.append({'parcel_id':feature['properties']['parcel_id'],'site_address':feature['properties']['site_address'],'observed_roof_overlap_m2':area,
            'reported_storeys':feature['properties']['stories'],'year_built':feature['properties']['year_built'],'not_independent_building_assertion':True})
    official=[];official_receipts=[]
    for cache in (ROOT/'data/cache/edgewater_audit').glob('*.json'):
        data=read(cache);data=data.get('data',data)
        for feature in data.get('features',[]):
            row=feature.get('attributes',{})
            if row.get('PARCEL') in PINS:
                official.append({k:row.get(k) for k in ['OBJECTID','PARCEL','SITUS','STYS','AYB','CONDO_FLAG','PARENT_ID','DOR_CODE']})
                official_receipts.append(cache)
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':evidence['source_snapshot'],'site_id':'edgewater_retail_1305_1319',
        'parcel_ids':PINS,'official_tax_records':official,'tax_record_count':6,'physical_building_count':None,
        'interpretation':'One connected observed roof complex across six tax parcels; party walls/legal physical building count unverified. Raw roof seed already one dominant connected component before closing.',
        'source_evidence':str(ROOT/'data/heights/retail_edgewater/acquisition.json'),'source_points_sha256':evidence['points_sha256'],
        'original_acquisition':'USGS OrangeCounty2018,2018-12-04 to2019-04-12; local flight day unknown','point_count':len(points),'classified_roof_support_points':len(q),
        'raw_dense_roof_cells':int(raw.sum()),'source_corrobated_infill_cells':confirmed_infill,'observed_components':raw_components,
        'roof_footprint_area_m2':outline.area,'tax_search_union_area_m2':target.area,'footprint_utm':mapping(outline),'per_parcel_coverage':per_parcel,
        'ground_reference_navd88_m':ground,'nearby_ground_p05_p95_m':np.percentile(near_ground[:,2],[5,95]).tolist(),
        'roof_plane_coefficients_model_xy':global_coef,'roof_support_p05_p50_p95_navd88_m':np.percentile(q[:,2],[5,50,95]).tolist(),
        'height_main_roof_m':float(np.median(A@coef)-ground),'maximum_rendered_height_m':max(p[2] for p in geometry[0])-.1,
        'roof_fit_residual_p50_p90_p95_max_m':np.percentile(residual,[50,90,95,100]).tolist(),
        'edge_simplification_bound_m':.65,'geometry_proof':proof,'closed_shell':gate,'float_proof':float_proof,
        'existing_visible_model_overlap_removed':overlap_records,'legacy_geometry_hidden':False,
        'aerial_reference':{'nominal_year':2025,'capture_day':'unknown','receipt':str(out/'aerial_receipt.json'),
            'qualitative_review':'Reviewed actual2025frame: abutting roof sections and rear extensions along the retail strip; no six-building interpretation from parcel lines.',
            'geometry_traced_from_image':False,'image_pixels_redistributed_or_embedded':False},
        'prim_path':path,'camera':str(camera.GetPath()),'status':'historical_source_supported_missing_form_proposal_pending_integration_and_visual_review',
        'limits':['Roof outline is observed; ground-level wall lines/overhangs and entrances are not independently located. Neutral display materials are proxies, not verified facades.',
            'One-meter source raster and0.65m simplification imply edge uncertainty; no sidewalk/ADA or precise party-wall claim.',
            'All six OCPA records report one storey/year1952 and empty condominium/parent fields; this does not establish legal building count or current tenants.',
            'Historical point cloud and nominal2025aerial cannot certify current as-built status. No logos, storefront names or floor-count extrapolation.'],
        'raw_official_footprint_records_for_target_pids':sum(f['properties'].get('PID') in PINS for f in read(ROOT/'data/buildings.geojson')['features']),
        'active_model_modified':False,'geometry_source':'classified USGS points, never tax-envelope extrusion'}
    active=read(ROOT/'data/processed/active.json')
    dependencies=[ROOT/'data/processed/active.json',ROOT/active['relative_path']/'parcels.json',ROOT/'data/buildings.geojson',ROOT/'data/footprint_manifest.json',
        out/'points.npz',out/'acquisition.json',out/'aerial_receipt.json',out/'aerial_2025_local_review.jpg',ROOT/'data/heights/vertical_unit_check.json',Path(__file__).resolve()]+official_receipts
    dependencies.extend(Path(l.realPath) for l in current.GetUsedLayers() if l.realPath and Path(l.realPath).resolve().is_relative_to(ROOT.resolve()))
    report['dependencies']={str(p.resolve().relative_to(ROOT.resolve())).replace('\\','/'):sha(p) for p in set(dependencies)}
    stage.GetRootLayer().customLayerData={'sourceSnapshot':evidence['source_snapshot'],'sourcePointsSha256':evidence['points_sha256'],
        'purpose':'Missing retail roof-derived block proposal, not current survey or six tax-extruded buildings'}
    layer=ROOT/'scene/retail_block_reconstruction_proposal.usda';temporary=layer.with_name(layer.stem+'.tmp.usda');stage.GetRootLayer().Export(str(temporary));os.replace(temporary,layer)
    report['layer']=str(layer);report['layer_sha256']=sha(layer);save(out/'verification.json',report)
    print(json.dumps({'layer':str(layer),'layer_sha256':report['layer_sha256'],'report':str(out/'verification.json'),'report_sha256':sha(out/'verification.json'),
        'source_roof_points':len(q),'roof_area_m2':outline.area,'main_height_m':report['height_main_roof_m'],'fit_residuals':report['roof_fit_residual_p50_p90_p95_max_m'],
        'closed_shell':gate,'per_parcel':per_parcel},indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args();reconstruct(args.live)
