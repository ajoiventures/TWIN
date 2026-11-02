"""Read-only rebased terrain/anchoring diagnosis from original cached DEMs.

Writes only a fresh ignored diagnostic folder; never invokes proposal writers,
downloads sources, edits USD or activates terrain. Reuses the existing sampler.
"""
from pathlib import Path
import os,sys,json,argparse,hashlib,collections,csv
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
import shapely
from shapely.geometry import Polygon,MultiPoint
from shapely.ops import unary_union
from pxr import Usd,UsdGeom
from acquire_dem import inspect_tile,parse_metadata,paste_tile,study_grid
from anchor_terrain_proposal import GroundSampler,rigid_delta,bridge_policy

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def analyze(output,root=ROOT):
    root,output=Path(root).resolve(),Path(output).resolve()
    if output.exists() or not output.is_relative_to(root/'data/diagnostics'):raise ValueError('Fresh ignored output required')
    folder=root/'data/heights/dem';config=json.loads((root/'config/terrain_sources.json').read_text())
    terrain=json.loads((folder/'terrain_proposal.json').read_text());old=json.loads((folder/'anchoring_proposal.json').read_text())
    rootpath=root/'scene/college_park_connected.usda';root_sha=sha(rootpath)
    deps={p:sha(root/p) for p in ['scene/college_park_connected.usda','scene/manual_edits.usda','data/processed/active.json','config/terrain_sources.json','data/heights/dem/terrain_proposal.json','data/heights/dem/anchoring_proposal.json']}
    for p in ['tools/analyze_terrain_anchoring.py','tools/anchor_terrain_proposal.py','tools/acquire_dem.py','data/heights/dem/study_valid_pixels.npz','data/openstreetmap.json']:
        deps[p]=sha(root/p)
    tiles=[]
    for row in config['tiles']:
        tile=folder/(row['id']+'.tif');xml=folder/(row['id']+'.xml')
        for path in [tile,xml]:
            receipt_path=Path(str(path)+'.source.json')
            deps[receipt_path.relative_to(root).as_posix()]=sha(receipt_path)
            receipt=json.loads(receipt_path.read_text())
            expected=receipt.get('sha256') or receipt.get('checksum_sha256')
            if sha(path)!=expected:raise ValueError('Original DEM receipt mismatch: '+str(path))
            deps[path.relative_to(root).as_posix()]=expected
        info,values,valid=inspect_tile(tile,parse_metadata(xml),config);tiles.append((info,values,valid))
    step=tiles[0][0]['pixel_scale_source_ft'][0]
    left=min(x[0]['source_bounds_ft'][0] for x in tiles);bottom=min(x[0]['source_bounds_ft'][1] for x in tiles)
    right=max(x[0]['source_bounds_ft'][2] for x in tiles);top=max(x[0]['source_bounds_ft'][3] for x in tiles)
    fullgrid={'left_ft':left,'top_ft':top,'pixel_size_ft':step,'width':round((right-left)/step),'height':round((top-bottom)/step),'horizontal_epsg':tiles[0][0]['horizontal_epsg']}
    if fullgrid['width']*fullgrid['height']>30000000:raise ValueError('Cached mosaic bound exceeded')
    full=np.full((fullgrid['height'],fullgrid['width']),np.nan,np.float32);covered=np.zeros(full.shape,bool)
    oldgrid=terrain['grid'];masked=np.full((oldgrid['height'],oldgrid['width']),np.nan,np.float32);oldcovered=np.zeros(masked.shape,bool)
    for info,values,valid in tiles:
        paste_tile(full,covered,fullgrid,info,values,valid);paste_tile(masked,oldcovered,oldgrid,info,values,valid)
    del tiles
    with np.load(folder/'study_valid_pixels.npz',allow_pickle=False) as source_mask:
        masked[~source_mask['inside_study']]=np.nan
    oldsampler=GroundSampler(masked,oldgrid,terrain['local_origin_wgs84'])
    sampler=GroundSampler(full,fullgrid,terrain['local_origin_wgs84'])
    stage=Usd.Stage.Open(str(rootpath));xc=UsdGeom.XformCache();bc=UsdGeom.BBoxCache(0,['default','render'],useExtentsHint=True)
    for layer in stage.GetUsedLayers():
        if layer.realPath:
            p=Path(layer.realPath).resolve()
            if p.is_relative_to(root):deps[p.relative_to(root).as_posix()]=sha(p)
    stale=[]
    for row in old['dependencies']:
        p=root/row['path'];actual=sha(p) if p.is_file() else None
        if actual!=row['sha256']:stale.append({'path':row['path'],'old_sha256':row['sha256'],'current_sha256':actual})
    def points(prim):
        m=UsdGeom.Mesh(prim);v=m.GetPointsAttr().Get()
        if v is None:return None
        matrix=xc.GetLocalToWorldTransform(prim)
        return np.array([matrix.Transform(p) for p in v],float)
    def footprint(prim,v):
        m=UsdGeom.Mesh(prim);counts=m.GetFaceVertexCountsAttr().Get();indices=m.GetFaceVertexIndicesAttr().Get();polys=[];off=0
        if counts is None or indices is None:return MultiPoint(v[:,:2]).convex_hull
        for n in counts:
            q=Polygon(v[np.array(indices[off:off+n]),:2]);off+=n
            if q.is_valid and q.area>1e-6:polys.append(q)
        return unary_union(polys) if polys else MultiPoint(v[:,:2]).convex_hull
    water=[];water_hulls=[]
    wp=stage.GetPrimAtPath('/World/Water')
    if wp:
        for p in Usd.PrimRange(wp):
            if p.GetTypeName()=='Mesh' and UsdGeom.Imageable(p).ComputeVisibility()!='invisible':
                v=points(p)
                if v is not None:
                    water.append(footprint(p,v));water_hulls.append(MultiPoint(v[:,:2]).convex_hull)
    water=unary_union(water)
    water_hulls=unary_union(water_hulls)
    rows=[]
    def ground_check(prim,kind):
        v=points(prim)
        if v is None or len(v)==0:return {'path':str(prim.GetPath()),'kind':kind,'full_cached_result':'no_mesh_points'}
        geometry=footprint(prim,v);row={'path':str(prim.GetPath()),'kind':kind,'world_base_z_m':float(v[:,2].min()),
            'source_transform_ops':len(UsdGeom.Xformable(prim).GetOrderedXformOps()),'footprint_area_m2':geometry.area,
            'footprint_connected_parts':len(geometry.geoms) if hasattr(geometry,'geoms') else 1,
            'actual_water_projection_intersects':bool(geometry.intersects(water)) if not water.is_empty else False,
            'legacy_convex_hull_water_screen_intersects':bool(MultiPoint(v[:,:2]).convex_hull.intersects(water_hulls)) if not water_hulls.is_empty else False,
            'water_projected_intersection_m2':float(geometry.intersection(water).area) if not water.is_empty else 0}
        try:
            oldsampler.validate_geometry(geometry);old_delta,_=rigid_delta(v,oldsampler);row['masked_grid_result']='sampleable';row['masked_delta_z_m']=old_delta
        except ValueError as error:row['masked_grid_result']=str(error)
        try:
            sampler.validate_geometry(geometry);delta,detail=rigid_delta(v,sampler);row.update(full_cached_result='sampleable',rigid_candidate_delta_z_m=delta,**detail)
        except ValueError as error:row['full_cached_result']=str(error)
        return row
    buildings=stage.GetPrimAtPath('/World/Buildings')
    for prim in buildings.GetChildren():
        if prim.GetTypeName()=='Mesh' and UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':rows.append(ground_check(prim,'legacy_building_group'))
    osm=json.loads((root/'data/openstreetmap.json').read_text());tags={str(e['id']):e.get('tags',{}) for e in osm['elements']}
    roads=[]
    for prim in stage.GetPrimAtPath('/World/Streets').GetChildren():
        if prim.GetTypeName()!='Mesh' or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':continue
        r=ground_check(prim,'road_surface');t=tags.get(prim.GetName().rsplit('_',1)[-1]);r['grade_exclusion']=bridge_policy(t);r['explicit_bridge_no']=bool(t and t.get('bridge')=='no')
        r['flat_source_surface']=bool(np.ptp(points(prim)[:,2])<=.001);roads.append(r)
    bypath={r['path']:r for r in rows+roads};oldskips=[]
    for item in old['skip_queue']:
        current=bypath.get(item['path']);oldskips.append({**item,'current_status':current['full_cached_result'] if current else 'category_or_hidden_or_no_longer_in_legacy_loop',
            'old_masked_status_now':current['masked_grid_result'] if current else None,'data_available_from_cached_tiles':bool(current and current['full_cached_result']=='sampleable')})
    # All inherited landmark meshes are inventoried as atomic component families,
    # not silently anchored by the legacy-building loop.
    historical=[]
    for prefix in ['/World/Landmarks','/World/OfficeFrontageDetail','/World/ChurchFrontageAppearance','/World/ChurchBelfryAppearance']:
        parent=stage.GetPrimAtPath(prefix)
        if not parent:continue
        groups=list(parent.GetChildren()) if prefix=='/World/Landmarks' else [parent]
        for group in groups:
            meshes=[p for p in Usd.PrimRange(group,Usd.TraverseInstanceProxies()) if p.GetTypeName()=='Mesh' and UsdGeom.Imageable(p).ComputeVisibility()!='invisible']
            if not meshes:continue
            bound=bc.ComputeWorldBound(group).ComputeAlignedRange();lo,hi=bound.GetMin(),bound.GetMax();center=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2]
            try:sample=float(sampler.sample([center])[0]);status='cached_ground_sampleable';delta=sample-float(lo[2])+.1
            except ValueError as error:sample=delta=None;status=str(error)
            historical.append({'path':str(group.GetPath()),'mesh_count':len(meshes),'bounds_world_m':[list(lo),list(hi)],'ground_center_scene_m':sample,
                'nominal_rigid_bbox_delta_m_not_approved':delta,'status':status,'source_custom_data':group.GetCustomData(),
                'policy':'Resolve sourceabsoluteNAVD88 frame vs relativeheight first; move geometry+appearance/tower/materialcontext atomically; never drape roof vertices'})
    inventory=[]
    for prefix in [str(p.GetPath()) for p in stage.GetPrimAtPath('/World').GetChildren() if str(p.GetPath()) not in ['/World/Buildings','/World/Roofs','/World/Streets','/World/Landmarks']]:
        parent=stage.GetPrimAtPath(prefix)
        if not parent:continue
        types=collections.Counter();instancers=[]
        for prim in Usd.PrimRange(parent,Usd.TraverseInstanceProxies()):
            types[prim.GetTypeName()]+=1
            if prim.IsA(UsdGeom.PointInstancer):
                pos=UsdGeom.PointInstancer(prim).GetPositionsAttr().Get()
                record={'path':str(prim.GetPath()),'positions':len(pos) if pos is not None else 0}
                if pos is not None and len(pos):
                    world=np.array([xc.GetLocalToWorldTransform(prim).Transform(p) for p in pos]);sampleable=0;errors=collections.Counter();deltas=[]
                    for point in world:
                        try:deltas.append(float(sampler.sample([point[:2]])[0]-point[2]));sampleable+=1
                        except ValueError as error:errors[str(error)]+=1
                    record.update(full_cached_sampleable_positions=sampleable,exceptions=dict(errors),
                        nominal_pivot_ground_delta_range_m=[min(deltas),max(deltas)] if deltas else None,
                        policy='Pivot-only diagnostic, not approved treebase; preserveprotoIndices/scales/orientations/IDs and verifyprototypecontact')
                instancers.append(record)
        inventory.append({'path':prefix,'types':dict(types),'point_instancers':instancers,'policy':'NOT anchored by original helper; requires family/base/pivot or surface-specific treatment'})
    report={'schema':'twin.terrain-anchoring-rebase-analysis/1','source_snapshot':json.loads((root/'data/processed/active.json').read_text())['snapshot'],
        'active_scene_changed':False,'new_acquisition':False,'source_z_origin_navd88_m':30.,'old_candidates':old['candidate_count'],
        'old_skip_count':old['skip_count'],'old_skip_reasons':dict(collections.Counter(x['reason'] for x in old['skip_queue'])),
        'old_dependency_changes':stale,'full_cached_grid':fullgrid,'full_source_valid_pixels':int(np.isfinite(full).sum()),
        'full_source_total_pixels':full.size,'current_buildings':rows,'current_roads':roads,'old_skip_rebase':oldskips,
        'historical_component_families':historical,'unanchored_category_inventory':inventory,
        'summaries':{'buildings_full_result':dict(collections.Counter(r['full_cached_result'] for r in rows)),
            'roads_full_result':dict(collections.Counter(r['full_cached_result'] for r in roads)),
            'old_skips_with_current_cached_data':sum(x['data_available_from_cached_tiles'] for x in oldskips),
            'old_data_extent_skips_now_sampleable':sum(x['reason'] in ('nodata_interpolation_support','nodata_surface_support','outside_valid_raster') and x['data_available_from_cached_tiles'] for x in oldskips),
            'old_water_and_grade_exceptions_still_semantic_review':sum(x['reason'] in ('water_intersection','bridge_tunnel_or_nonzero_layer') for x in oldskips),
            'roads_grade_exclusions':dict(collections.Counter(str(r['grade_exclusion']) for r in roads)),
            'buildings_multi_part_footprints':sum(r.get('footprint_connected_parts',0)>1 for r in rows)},
        'dependencies':deps,'limits':['Read-only sampler/geography rebase, no generated USD or terrain activation',
            'Fullcachedcoverage beyond extraction only diagnoses availability; does not expand accepted scene extent',
            'Convexhull-center rigid_delta retained as diagnostic, not accepted foundation/atomic object policy',
            'Historical bare-earth cannot establish road bridge clearance, curbs, ADA grades, current ground or lake surfaces',
            'No all-object completion: appearance, vegetation, vehicles, masks and ground replacement require coordinated anchored composition']}
    if sha(rootpath)!=root_sha:raise ValueError('Root changed during read-only analysis; rerun fresh')
    changed=[p for p,h in deps.items() if not (root/p).is_file() or sha(root/p)!=h]
    if changed:raise ValueError('Source changed during terrain analysis: '+', '.join(changed))
    output.mkdir(parents=True);(output/'report.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    with (output/'old_skip_rebase.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(oldskips[0]));writer.writeheader();writer.writerows(oldskips)
    return {'output':str(output),'summaries':report['summaries'],'old_dependency_changes':len(stale),'historical_families':len(historical),'report_sha256':sha(output/'report.json')}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True);args=parser.parse_args()
    print(json.dumps(analyze(ROOT/args.output),indent=2))
