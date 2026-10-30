"""Offline, non-activating terrain proposal from receipt-verified original DEMs."""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
sys.path.insert(0, str(ROOT / 'tools'))
for _thread_variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_thread_variable]='1'  # This offline builder process only.
import numpy as np
from pyproj import Transformer
from pxr import Usd, UsdGeom, Vt, Gf
from acquire_dem import (checksum, parse_metadata, inspect_tile, study_grid,
                         paste_tile, US_FOOT_M, atomic_json, now)


def verify_source(path, url, previous):
    receipt_path=path.with_suffix(path.suffix+'.source.json')
    receipt=json.loads(receipt_path.read_text())
    digest=checksum(path)
    if receipt['url'] != url or receipt['sha256'] != digest or previous['sha256'] != digest:
        raise ValueError('Original source identity/hash mismatch: '+path.name)
    return receipt_path


def coarse_mesh(values, inside, grid, origin_wgs84, stride=8, z_origin_m=30.0):
    """Sample actual pixel centers; reject a quad if ANY covered source pixel is invalid.

    One common source grid avoids independent tile seam vertices. A conservative
    rectangular validity check also excludes even a single intervening NoData pixel.
    No interpolation, averaging or gap filling creates vertex elevations.
    """
    if not isinstance(stride, int) or not 1 <= stride <= 64:
        raise ValueError('stride must be an integer from 1 to 64')
    if values.shape != inside.shape or values.ndim != 2 or min(values.shape) < 2:
        raise ValueError('Invalid raster/mask shape')
    if not np.isfinite(z_origin_m):
        raise ValueError('Nonfinite vertical origin')
    rows = np.unique(np.r_[np.arange(0, values.shape[0], stride), values.shape[0]-1])
    cols = np.unique(np.r_[np.arange(0, values.shape[1], stride), values.shape[1]-1])
    invalid = ~(np.isfinite(values) & inside)
    sums = np.pad(invalid.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    r0, c0 = np.meshgrid(rows[:-1], cols[:-1], indexing='ij')
    r1, c1 = np.meshgrid(rows[1:], cols[1:], indexing='ij')
    bad = sums[r1+1,c1+1]-sums[r0,c1+1]-sums[r1+1,c0]+sums[r0,c0]
    good = bad == 0
    width = len(cols)
    rr, cc = np.nonzero(good)
    # Source rows advance south: this ordering produces upward normals.
    faces = np.column_stack((rr*width+cc, (rr+1)*width+cc,
                             (rr+1)*width+cc+1, rr*width+cc+1))
    used, inverse = np.unique(faces, return_inverse=True)
    sr, sc = rows[used//width], cols[used%width]
    transform = Transformer.from_crs(grid['horizontal_epsg'], 32617, always_xy=True)
    origin = Transformer.from_crs(4326,32617,always_xy=True).transform(*origin_wgs84)
    x = grid['left_ft']+(sc+.5)*grid['pixel_size_ft']
    y = grid['top_ft']-(sr+.5)*grid['pixel_size_ft']
    east,north = transform.transform(x,y)
    absolute = values[sr,sc].astype(np.float64)*US_FOOT_M
    points = np.column_stack((east-origin[0], north-origin[1], absolute-z_origin_m)).astype(np.float32)
    return points, inverse.reshape(-1,4), {'accepted_quads': int(good.sum()),
        'rejected_quads': int((~good).sum()), 'sampled_valid_vertices':len(used),
        'absolute_vertex_elevation_range_navd88_m': [float(absolute.min()),float(absolute.max())] if len(used) else None,
        'nominal_spacing_m':stride*grid['pixel_size_ft']*US_FOOT_M}


def build(root=ROOT, stride=8, z_origin_m=30.0):
    root=Path(root)
    config_path=root/'config/terrain_sources.json'
    configuration=json.loads(config_path.read_text())
    if (configuration.get('expected_vertical_datum') != 'North American Vertical Datum 1988'
            or configuration.get('expected_vertical_unit') != 'US survey foot'):
        raise ValueError('Unverified vertical datum/units: no terrain proposal may claim NAVD88 meters')
    study_path=root/'config/study_area.json'
    study=json.loads(study_path.read_text())
    folder=root/'data/heights/dem'
    manifest_path=folder/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest['configuration_sha256'] != checksum(config_path):
        raise ValueError('DEM manifest configuration changed')
    if configuration['study_bbox_wgs84'] != study['acquisition_bbox_wgs84']:
        raise ValueError('Extraction extent differs from current study configuration')
    if study['projected_crs'] != 'EPSG:32617' or study['units'] != 'meters':
        raise ValueError('Unsupported project frame')
    dependencies=[]
    grid=mosaic=covered=None
    rows_by_id={item['id']:item for item in manifest['tiles']}
    for source in configuration['tiles']:
        paths=[folder/(source['id']+suffix) for suffix in ('.tif','.xml')]
        previous=rows_by_id[source['id']]
        for path,url,key in zip(paths,[source['download_url'],source['metadata_url']],['source_receipt','metadata_receipt']):
            receipt_path=verify_source(path,url,previous[key])
            dependencies.extend({'path':p.relative_to(root).as_posix(),'sha256':checksum(p)} for p in (path,receipt_path))
        tile,values,valid=inspect_tile(paths[0],parse_metadata(paths[1]),configuration)
        if grid is None:
            grid=study_grid(configuration,tile)
            mosaic=np.full((grid['height'],grid['width']),np.nan,dtype=np.float32)
            covered=np.zeros(mosaic.shape,dtype=bool)
        if tile['horizontal_epsg'] != grid['horizontal_epsg']:
            raise ValueError('Mixed source CRS')
        overlap=paste_tile(mosaic,covered,grid,tile,values,valid)
        if (overlap['overlap_max_difference_m'] or 0) > 1e-6:
            raise ValueError('Conflicting overlapping source samples')
    mask_path=folder/'study_valid_pixels.npz'
    with np.load(mask_path,allow_pickle=False) as mask:
        if any(float(mask[k]) != grid[k] for k in ('left_ft','top_ft','pixel_size_ft','horizontal_epsg')):
            raise ValueError('Coverage mask grid differs from originals')
        if not np.array_equal(mask['valid'],np.isfinite(mosaic)) or not np.array_equal(mask['source_covered'],covered):
            raise ValueError('Coverage mask disagrees with decoded sources')
        inside=mask['inside_study'].copy()
    # Recompute geographic membership rather than trusting a cached inside mask.
    to_wgs=Transformer.from_crs(grid['horizontal_epsg'],4326,always_xy=True)
    xs=grid['left_ft']+(np.arange(grid['width'])+.5)*grid['pixel_size_ft']
    bbox=configuration['study_bbox_wgs84']
    for start in range(0,grid['height'],64):
        ys=grid['top_ft']-(np.arange(start,min(start+64,grid['height']))+.5)*grid['pixel_size_ft']
        xx,yy=np.meshgrid(xs,ys)
        lon,lat=to_wgs.transform(xx,yy)
        actual=(lon>=bbox[0])&(lon<=bbox[2])&(lat>=bbox[1])&(lat<=bbox[3])
        if not np.array_equal(inside[start:start+len(ys)],actual):
            raise ValueError('Cached extraction membership changed')
    points,faces,metrics=coarse_mesh(mosaic,inside,grid,study['local_origin_wgs84'],stride,z_origin_m)
    if not len(faces):
        raise ValueError('No valid terrain faces')
    layer_path=root/'scene/terrain_proposal.usda'
    layer_path.parent.mkdir(parents=True,exist_ok=True)
    stage=Usd.Stage.CreateInMemory()
    stage.GetRootLayer().customLayerData={'status':'historical_unanchored_proposal',
        'verticalDatum':'NAVD88','sceneZOriginNAVD88Meters':float(z_origin_m),
        'horizontalCRS':'EPSG:32617','sourceAcquisition':'2018-12-04/2019-04-12'}
    UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage,1)
    world=UsdGeom.Xform.Define(stage,'/World')
    stage.SetDefaultPrim(world.GetPrim())
    mesh=UsdGeom.Mesh.Define(stage,'/World/HistoricalTerrainProposal')
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
    mesh.CreateFaceVertexCountsAttr([4]*len(faces))
    mesh.CreateFaceVertexIndicesAttr(faces.flatten().tolist())
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.CreateDisplayColorAttr([Gf.Vec3f(.25,.32,.20)])
    mesh.GetPrim().SetCustomDataByKey('status','historical_unanchored_proposal_do_not_activate')
    mesh.GetPrim().SetCustomDataByKey('sceneZOriginNAVD88Meters',float(z_origin_m))
    mesh.CreateExtentAttr([Gf.Vec3f(*map(float,points.min(0))),Gf.Vec3f(*map(float,points.max(0)))])
    stage.GetRootLayer().Export(str(layer_path))
    for path in (config_path,study_path,manifest_path,mask_path,Path(__file__)):
        dependencies.append({'path':path.relative_to(root).as_posix(),'sha256':checksum(path)})
    report={'created_utc':now(),'status':'historical_unanchored_proposal','activated':False,
        'source_horizontal_epsg':grid['horizontal_epsg'],'output_horizontal_epsg':32617,
        'horizontal_transform':Transformer.from_crs(grid['horizontal_epsg'],32617,always_xy=True).description,
        'horizontal_transform_reported_accuracy_m':Transformer.from_crs(grid['horizontal_epsg'],32617,always_xy=True).accuracy,
        'local_origin_wgs84':study['local_origin_wgs84'],'vertical_datum':'NAVD88',
        'original_vertical_unit':'US survey foot','vertical_conversion_to_m':US_FOOT_M,
        'scene_z_origin_navd88_m':z_origin_m,'scene_z_rule':'scene_z = absolute_NAVD88_m - scene_z_origin_navd88_m',
        'source_acquisition_interval':configuration['expected_acquisition_interval'],
        'grid':grid,'stride_pixels':stride,**metrics,
        'scene_bounds_m':[points.min(0).astype(float).tolist(),points.max(0).astype(float).tolist()],
        'activation_gate':'Blocked pending independent review and explicit shared-origin ground anchoring; this tool has no apply mode.',
        'valid_source_pixels_inside_extraction':int((inside & np.isfinite(mosaic)).sum()),
        'absolute_source_elevation_range_navd88_m':[float(np.min(mosaic[inside & np.isfinite(mosaic)]))*US_FOOT_M,
                                                  float(np.max(mosaic[inside & np.isfinite(mosaic)]))*US_FOOT_M],
        'original_dem_seam_screening':manifest['adjacent_seams'],
        'runtime_dependencies':['Python standard library','numpy','Pillow TIFF decoder','pyproj EPSG database','usd-core pxr'],
        'dependencies':dependencies,'layer':layer_path.relative_to(root).as_posix(),'layer_sha256':checksum(layer_path),
        'anchoring_required':['Select and persist one shared NAVD88 scene origin before activation.',
            'Place existing building bases using sampled bare-earth ground minus that origin; preserve measured relative building heights.',
            'Drape roads/sidewalks with continuous grades and explicit clearance; validate bridge/water exceptions and existing detail offsets.',
            'Replace flat ground only after independent seam, geometry, and visual review of the anchored scene.'],
        'limits':['2018-2019 historical hydro-flattened bare earth, not current surveyed ground.',
            'Coarsened point samples omit sub-grid relief and curb detail; rejected cells remain holes, with no NoData bridging.',
            'Pixel centers do not cover the outer half-pixel boundary; conservative block rejection creates a further narrow edge margin.',
            'No vertical datum transformation was performed: source XML/GeoTIFF units were verified and converted only.',
            'Existing flat scene ground, roads and buildings have not been moved; overlay alone will intersect or float above them.']}
    atomic_json(folder/'terrain_proposal.json',report)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stride',type=int,default=8)
    parser.add_argument('--z-origin-m',type=float,default=30.0)
    args=parser.parse_args()
    result=build(stride=args.stride,z_origin_m=args.z_origin_m)
    print(json.dumps({k:result[k] for k in ('status','accepted_quads','sampled_valid_vertices','nominal_spacing_m','layer')},indent=2))
