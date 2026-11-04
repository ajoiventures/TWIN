"""Offline alignment evidence: independent UTM arithmetic versus authored XY.

This is coordinate/serialization verification, never external survey accuracy.
Source caches, scene, active pointer and user layers are read only.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,math,os,sys
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
from pxr import Usd,UsdGeom

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def utm17(lon,lat):
    """Independent WGS84 Snyder TM series through A^6; zone17, northern hemisphere.

    GRS80/native datum changes are not approximated here; those use PROJ only
    before this independent WGS84 geographic-to-UTM calculation.
    """
    a=6378137.;f=1/298.257223563;e2=f*(2-f);ep2=e2/(1-e2);phi=math.radians(lat);dl=math.radians(lon+81)
    n=a/math.sqrt(1-e2*math.sin(phi)**2);t=math.tan(phi)**2;c=ep2*math.cos(phi)**2;A=math.cos(phi)*dl
    m=a*((1-e2/4-3*e2**2/64-5*e2**3/256)*phi-(3*e2/8+3*e2**2/32+45*e2**3/1024)*math.sin(2*phi)+(15*e2**2/256+45*e2**3/1024)*math.sin(4*phi)-35*e2**3/3072*math.sin(6*phi))
    return (500000+.9996*n*(A+(1-t+c)*A**3/6+(5-18*t+t*t+72*c-58*ep2)*A**5/120),.9996*(m+n*math.tan(phi)*(A*A/2+(5-t+9*c+4*c*c)*A**4/24+(61-58*t+t*t+600*c-330*ep2)*A**6/720)))

def distributed(points,count=10):
    """Deterministic farthest-point sample; starts at the southernmost point."""
    values=np.asarray(points,float)
    if len(values)<count:raise ValueError('Fewer than ten distinct reference points')
    selected=[int(np.lexsort((values[:,0],values[:,1]))[0])];distance=np.sum((values-values[selected[0]])**2,axis=1)
    for _ in range(count-1):
        index=int(np.argmax(distance))
        if distance[index]<=0:raise ValueError('Reference points are not distinct')
        selected.append(index);distance=np.minimum(distance,np.sum((values-values[index])**2,axis=1))
    return selected

def summary(rows):
    values=np.array([r['residual_m'] for r in rows]);xy=np.array([r['reference_local_xy_m'] for r in rows])
    return {'count':len(rows),'rms_m':float(np.sqrt(np.mean(values**2))),'p95_m':float(np.percentile(values,95)),'maximum_m':float(values.max()),'reference_local_bounds_m':[xy.min(0).tolist(),xy.max(0).tolist()],'span_east_m':float(np.ptp(xy[:,0])),'span_north_m':float(np.ptp(xy[:,1]))}

def source_vertex_pixels(valid,inside,stride):
    """Reconstruct canonical mesh vertex ORDER from source validity, never mesh XY.

    Every pixel in an inclusive source block must be valid/inside. Vertices are
    the sorted row-major coarse-grid IDs used by accepted quads.
    """
    if valid.shape!=inside.shape or valid.ndim!=2 or not isinstance(stride,int) or stride<1:raise ValueError('Invalid source grid/mask/stride')
    rows=np.unique(np.r_[np.arange(0,valid.shape[0],stride),valid.shape[0]-1]);cols=np.unique(np.r_[np.arange(0,valid.shape[1],stride),valid.shape[1]-1])
    invalid=(~valid|~inside).astype(np.int32);sums=np.pad(invalid,((1,0),(1,0))).cumsum(0).cumsum(1)
    lowr,lowc=np.meshgrid(rows[:-1],cols[:-1],indexing='ij');highr,highc=np.meshgrid(rows[1:],cols[1:],indexing='ij')
    bad=sums[highr+1,highc+1]-sums[lowr,highc+1]-sums[highr+1,lowc]+sums[lowr,lowc]
    rr,cc=np.where(bad==0);width=len(cols)
    ids=np.unique(np.concatenate((rr*width+cc,(rr+1)*width+cc,(rr+1)*width+cc+1,rr*width+cc+1)))
    return rows[ids//width],cols[ids%width]

def native_grid_checks(values,matrix,grid,valid,inside,stride,origin_wgs84):
    row_indices,col_indices=source_vertex_pixels(valid,inside,stride)
    if len(values)!=len(row_indices):raise ValueError('Proposal vertex count differs from independently reconstructed source ordering')
    world=np.c_[values,np.ones(len(values))]@np.asarray(matrix,dtype=float)
    if not np.isfinite(world).all() or not np.allclose(world[:,3],1,atol=1e-12):raise ValueError('Nonfinite/non-affine proposal world transform')
    geographic=Transformer.from_crs(grid['horizontal_epsg'],4326,always_xy=True);origin=utm17(*origin_wgs84);result=[]
    for index in distributed(world[:,:2]):
        row=int(row_indices[index]);col=int(col_indices[index]);nx=grid['left_ft']+(col+.5)*grid['pixel_size_ft'];ny=grid['top_ft']-(row+.5)*grid['pixel_size_ft']
        lon,lat=geographic.transform(nx,ny);reference=np.subtract(utm17(lon,lat),origin);point=world[index]
        result.append({'id':'dem-pixel-'+str(row)+'-'+str(col),'source_vertex_index':int(index),'source_native_xy_ftUS':[nx,ny],'source_epsg':grid['horizontal_epsg'],'source_pixel_valid':bool(valid[row,col] and inside[row,col]),'source_wgs84_via_declared_datum_operation':[lon,lat],'reference_local_xy_m':reference.tolist(),'proposal_world_xy_m':point[:2].tolist(),'residual_m':float(np.linalg.norm(reference-point[:2])),'comparison':'source-mask/stride vertex ordering to full world-transformed inactive proposal; no inverse snapping, no active-ground or independent survey control'})
    return result

def review(root=ROOT):
    root=Path(root);config=root/'config/study_area.json';study=json.loads(config.read_text());origin=utm17(*study['local_origin_wgs84'])
    active_path=root/'data/processed/active.json';active=json.loads(active_path.read_text())
    if study['projected_crs']!='EPSG:32617' or study['units']!='meters':raise ValueError('Unexpected declared scene frame')
    boundary=root/'data/processed/study_boundaries.geojson';collection=json.loads(boundary.read_text());main=next(f for f in collection['features'] if f['id']=='main_street')
    if collection['provenance']['source_snapshot']!=active['snapshot']:raise ValueError('Boundary snapshot stale')
    from study_boundaries import SOURCES,Client
    official=SOURCES['main_street'];client=Client(root/'data/cache/boundaries',offline=True)
    original=client.get(official['url']+'/query',{'f':'geojson','where':official['where'],'outFields':','.join(official['fields']),'outSR':4326,'returnGeometry':'true'})
    if len(original.get('features',[]))!=1 or not shape(original['features'][0]['geometry']).equals_exact(shape(main['geometry']),1e-12):raise ValueError('Derived boundary differs from frozen official response')
    source=shape(main['geometry']);coords=np.unique(np.array(source.exterior.coords if source.geom_type=='Polygon' else [p for g in source.geoms for p in g.exterior.coords]),axis=0)
    expected=np.array([np.subtract(utm17(*p),origin) for p in coords]);scene=root/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(scene));prim=stage.GetPrimAtPath('/World/StudyBoundaries/MainStreet')
    if not prim:raise ValueError('Official MainStreet curve missing')
    curve=UsdGeom.BasisCurves(prim);matrix=UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0);points=[matrix.Transform(p) for p in curve.GetPointsAttr().Get()];lines=[];offset=0
    for count in curve.GetCurveVertexCountsAttr().Get():
        lines.append(LineString([(p[0],p[1]) for p in points[offset:offset+count]]));offset+=count
    rendered=unary_union(lines);rows=[]
    for index in distributed(expected):
        xy=expected[index];p=Point(xy)
        # Nearest curve distance also catches clipping without inventing a closing edge.
        from shapely.ops import nearest_points
        observed=nearest_points(p,rendered)[1]
        rows.append({'id':'city-mainstreet-vertex-'+str(index),'source_feature':main['properties']['source_feature_ids'],'source_wgs84':coords[index].tolist(),'reference_local_xy_m':xy.tolist(),'scene_nearest_xy_m':[observed.x,observed.y],'residual_m':p.distance(rendered),'comparison':'official cached WGS84 vertex versus composed USD boundary; analytic UTM independent of composer PROJ call'})
    paths={config,boundary,scene,active_path};paths.update(Path(l.realPath) for l in stage.GetUsedLayers() if l.realPath)
    paths.update((root/'data/cache/boundaries').glob('*.json'))
    native=[];native_info={'status':'unavailable'};terrain_report=root/'data/heights/dem/terrain_proposal.json'
    if terrain_report.exists():
        info=json.loads(terrain_report.read_text());terrain=root/info['layer']
        if sha(terrain)!=info['layer_sha256']:raise ValueError('Terrain proposal hash stale')
        if info['local_origin_wgs84']!=study['local_origin_wgs84']:raise ValueError('Terrain origin differs from declared scene frame')
        from PIL import Image
        from acquire_dem import geokeys
        source_manifest=json.loads((root/'data/heights/dem/manifest.json').read_text());headers=[]
        for tile in source_manifest['tiles']:
            tif=root/'data/heights/dem'/Path(tile['file']).name
            if sha(tif)!=tile['source_receipt']['sha256']:raise ValueError('Original DEM source hash changed')
            with Image.open(tif) as image:tags=dict(image.tag_v2);keys=geokeys(tags);tie=list(tags[33922]);scale=list(tags[33550])
            if keys.get('3072')!=info['source_horizontal_epsg'] or keys.get('3076')!=9003:raise ValueError('Original GeoTIFF CRS/unit mismatch')
            for value in ((info['grid']['left_ft']-tie[3])/scale[0],(tie[4]-info['grid']['top_ft'])/scale[1]):
                if abs(value-round(value))>1e-6:raise ValueError('Mosaic is not aligned to original pixel grid')
            headers.append({'tile':tile['id'],'original_tiepoint':tie,'original_pixel_scale':scale,'projected_epsg':keys['3072'],'linear_unit_code':keys['3076'],'source_url':tile['source_receipt']['url'],'original_retrieval_utc':tile['source_receipt'].get('fetched_utc'),'acquisition_interval':['2018-12-04','2019-04-12']})
            paths.add(tif)
        native_stage=Usd.Stage.Open(str(terrain));native_prim=native_stage.GetPrimAtPath('/World/HistoricalTerrainProposal');values=np.asarray(UsdGeom.Mesh(native_prim).GetPointsAttr().Get(),float)
        native_matrix=UsdGeom.XformCache().GetLocalToWorldTransform(native_prim)
        grid=info['grid'];mask_path=root/'data/heights/dem/study_valid_pixels.npz'
        with np.load(mask_path) as mask:
            native=native_grid_checks(values,native_matrix,grid,mask['valid'],mask['inside_study'],info['stride_pixels'],study['local_origin_wgs84'])
        paths.update([terrain_report,terrain,mask_path,root/'data/heights/dem/manifest.json'])
        native_info={'status':'ten_native_grid_ties_checked_on_inactive_proposal','summary':summary(native),'verified_original_geotiff_headers':headers,'source_horizontal_epsg':grid['horizontal_epsg'],'source_units':'US survey foot','transform_operation':info['horizontal_transform'],'operation_reported_accuracy_m':info['horizontal_transform_reported_accuracy_m'],'accuracy_meaning':'EPSG operation metadata only, not source positional accuracy or project acceptance tolerance','points':native}
    hashes={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in sorted(paths)}
    stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if json.loads(active_path.read_text())!=active:raise ValueError('Snapshot changed during review')
    report={'schema':'twin.alignment-review/1','created_utc':stamp,'source_snapshot':active['snapshot'],'frame':study,'origin_utm_reference_m':origin,'axis_checks':{'east_is_positive_x':utm17(study['local_origin_wgs84'][0]+.001,study['local_origin_wgs84'][1])[0]>origin[0],'north_is_positive_y':utm17(study['local_origin_wgs84'][0],study['local_origin_wgs84'][1]+.001)[1]>origin[1],'stage_meters_per_unit':UsdGeom.GetStageMetersPerUnit(stage),'stage_up_axis':str(UsdGeom.GetStageUpAxis(stage))},'city_boundary_source':main['properties'],'city_boundary_native_coordinate_limit':'Cached City query explicitly requested outSR4326; no independent native-coordinate point attributes were retained. Native DEM comparison is a separate source/proposal check.','city_boundary_summary':summary(rows),'city_boundary_points':rows,'native_dem_crosscheck':native_info,'numerical_screen_m':.001,'numerical_screen_meaning':'software consistency screen for float32 local serialization and analytic series; not survey tolerance','numerical_consistency_pass':max(r['residual_m'] for r in rows+native)<.001 and all(r['source_pixel_valid'] for r in native) and UsdGeom.GetStageMetersPerUnit(stage)==1 and UsdGeom.GetStageUpAxis(stage)=='Z','external_positional_accuracy':{'status':'not_established','independent_survey_controls':0,'source_supported_project_tolerance_m':None,'reason':'No retained independently surveyed ten-point controls or authoritative positional acceptance tolerance. City service WGS84 coordinates and official DEM grid ties test transforms, not independent field truth.'},'source_dependencies_sha256':hashes,'ticket5_complete':False}
    folder=root/'data/processed';(folder/'alignment_review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    features=[{'type':'Feature','id':r['id'],'properties':{'role':'city_source_transform_reference','residual_m':r['residual_m']},'geometry':{'type':'Point','coordinates':r['source_wgs84']}} for r in rows]
    (folder/'alignment_reference_points.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}),encoding='utf-8');return report

if __name__=='__main__':
    result=review();print(json.dumps({k:result[k] for k in ('city_boundary_summary','axis_checks','external_positional_accuracy','numerical_consistency_pass')},indent=2));sys.exit(not result['numerical_consistency_pass'])
