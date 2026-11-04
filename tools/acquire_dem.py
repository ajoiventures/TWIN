"""Acquire and independently inspect original USGS DEM tiles; never activate terrain.

Original horizontal and elevation units remain US survey feet. EPT meters are a
different product. Only derived review metrics are converted to meters.
"""
from pathlib import Path
import argparse, concurrent.futures, datetime, hashlib, json, os, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
from PIL import Image
from pyproj import CRS, Transformer

US_FOOT_M = 1200 / 3937
OFFICIAL_HOSTS = {'rockyweb.usgs.gov', 'prd-tnm.s3.amazonaws.com'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def download(url, destination, maximum_bytes, offline=False, opener=None):
    destination = Path(destination)
    receipt_path = destination.with_suffix(destination.suffix + '.source.json')
    if destination.exists() and receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt['url'] != url or receipt['sha256'] != checksum(destination):
            raise ValueError('Cached source URL/checksum mismatch: ' + str(destination))
        if destination.stat().st_size > maximum_bytes:
            raise ValueError('Cached source exceeds configured bound')
        return {**receipt, 'read_mode': 'cached'}
    if offline:
        raise RuntimeError('Offline source cache miss: ' + str(destination))
    if urllib.parse.urlparse(url).scheme != 'https' or urllib.parse.urlparse(url).hostname not in OFFICIAL_HOSTS:
        raise ValueError('Download URL must use an allowlisted official HTTPS host')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.part')
    opener = opener or urllib.request.urlopen
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'TWIN-original-DEM-acquisition/1.0'})
        with opener(request, timeout=45) as response:
            if urllib.parse.urlparse(response.geturl()).hostname not in OFFICIAL_HOSTS:
                raise ValueError('Unexpected download redirect host')
            if response.status != 200:
                raise ValueError('Expected complete file response, not partial content')
            length = response.headers.get('Content-Length')
            if length and int(length) > maximum_bytes:
                raise ValueError('Advertised source exceeds configured bound')
            count = 0
            with temporary.open('wb') as stream:
                while True:
                    block = response.read(min(1024 * 1024, maximum_bytes - count + 1))
                    if not block:
                        break
                    count += len(block)
                    if count > maximum_bytes:
                        raise ValueError('Source exceeded configured byte bound')
                    stream.write(block)
            if length and count != int(length):
                raise ValueError('Incomplete file download')
            receipt = {'url': url, 'final_url': response.geturl(), 'fetched_utc': now(), 'bytes': count,
                       'source_last_modified': response.headers.get('Last-Modified'), 'source_etag': response.headers.get('ETag'),
                       'source_content_type': response.headers.get('Content-Type'), 'sha256': checksum(temporary)}
        os.replace(temporary, destination)
        atomic_json(receipt_path, receipt)
        return {**receipt, 'read_mode': 'live'}
    finally:
        if temporary.exists():
            temporary.unlink()


def geokeys(tags):
    directory = tuple(tags.get(34735, ()))
    if len(directory) < 4:
        raise ValueError('Missing GeoTIFF key directory')
    ascii_values = tags.get(34737, '')
    if isinstance(ascii_values, tuple):
        ascii_values = ''.join(map(str, ascii_values))
    doubles = tags.get(34736, ())
    result = {}
    for index in range(directory[3]):
        key, location, count, offset = directory[4 + index * 4:8 + index * 4]
        if location == 0:
            value = offset
        elif location == 34737:
            value = ascii_values[offset:offset + count].rstrip('|\x00')
        elif location == 34736:
            value = list(doubles[offset:offset + count])
        else:
            value = {'tag': location, 'count': count, 'offset': offset}
        result[str(key)] = value
    return result


def parse_metadata(path):
    root = ET.parse(path).getroot()
    def text(name):
        return root.findtext('.//' + name)
    return {'horizontal_crs': text('mapprojn'), 'vertical_datum': text('altdatum'), 'vertical_unit': text('altunits'),
            'acquisition_start': text('begdate'), 'acquisition_end': text('enddate'), 'publication_date': text('pubdate'),
            'access_constraints': text('accconst'), 'use_constraints': text('useconst'),
            'bbox_wgs84': [float(text(k)) for k in ['westbc', 'southbc', 'eastbc', 'northbc']]}


def validate_metadata(meta, configuration):
    if meta['horizontal_crs'] != configuration['expected_horizontal_crs']:
        raise ValueError('Unexpected source horizontal CRS')
    if meta['vertical_unit'] != configuration['expected_vertical_unit'] or meta['vertical_datum'] != configuration['expected_vertical_datum']:
        raise ValueError('Unexpected source vertical datum/unit; EPT meter assumptions cannot be applied')
    if [meta['acquisition_start'], meta['acquisition_end']] != configuration['expected_acquisition_interval']:
        raise ValueError('Source acquisition interval changed; review before reuse')


def valid_pixels(values, nodata):
    valid = np.isfinite(values)
    if nodata is not None:
        valid &= values != np.asarray(nodata, dtype=values.dtype)
    return valid


def inspect_tile(path, metadata, configuration):
    validate_metadata(metadata, configuration)
    with Image.open(path) as image:
        tags = dict(image.tag_v2)
        keys = geokeys(tags)
        scale = tuple(float(v) for v in tags.get(33550, ()))
        tie = tuple(float(v) for v in tags.get(33922, ()))
        if len(scale) != 3 or len(tie) != 6 or tags.get(274, 1) != 1:
            raise ValueError('Unsupported/missing GeoTIFF scale/tiepoint/orientation')
        if abs(scale[0] - configuration['expected_pixel_scale_ft']) > 1e-9 or abs(scale[1] - scale[0]) > 1e-9:
            raise ValueError('Unexpected GeoTIFF pixel scale')
        if keys.get('1025') != 1:
            raise ValueError('Expected PixelIsArea raster; point interpretation needs explicit support')
        source_crs = CRS.from_user_input(metadata['horizontal_crs'])
        epsg = keys.get('3072')
        if isinstance(epsg, int) and epsg != 32767 and not CRS.from_epsg(epsg).equals(source_crs):
            raise ValueError('GeoTIFF projected CRS conflicts with source XML')
        if keys.get('3076') not in [9003]:
            raise ValueError('GeoTIFF projected linear units are not US survey feet')
        if abs(source_crs.axis_info[0].unit_conversion_factor - US_FOOT_M) > 1e-12:
            raise ValueError('Named CRS horizontal unit conversion mismatch')
        vertical = keys.get('4099')
        if vertical is not None and vertical != 9003:
            raise ValueError('GeoTIFF vertical units conflict with XML US survey foot')
        vertical_epsg = keys.get('4096')
        if isinstance(vertical_epsg, int) and vertical_epsg != 32767:
            vertical_crs = CRS.from_epsg(vertical_epsg)
            if not vertical_crs.is_vertical or vertical_crs.datum.name != configuration['expected_vertical_datum']:
                raise ValueError('GeoTIFF vertical CRS conflicts with source XML datum')
            if abs(vertical_crs.axis_info[0].unit_conversion_factor - US_FOOT_M) > 1e-12:
                raise ValueError('GeoTIFF vertical CRS unit conversion mismatch')
        nodata_text = tags.get(42113)
        if isinstance(nodata_text, tuple):
            nodata_text = nodata_text[0]
        nodata = float(nodata_text.rstrip('\x00')) if isinstance(nodata_text, str) else float(nodata_text) if nodata_text is not None else None
        values = np.array(image, dtype=np.float32)
        if values.ndim != 2:
            raise ValueError('Expected single-band height raster')
        valid = valid_pixels(values, nodata)
        x0, y0 = tie[3] - tie[0] * scale[0], tie[4] + tie[1] * scale[1]
        width, height = image.size
        bounds = [x0, y0 - height * scale[1], x0 + width * scale[0], y0]
        return {'width': width, 'height': height, 'pixel_scale_source_ft': list(scale), 'pixel_size_m': scale[0] * US_FOOT_M,
                'source_bounds_ft': bounds, 'geokeys': keys, 'horizontal_epsg': source_crs.to_epsg(),
                'nodata': nodata, 'valid_pixels': int(valid.sum()), 'total_pixels': int(values.size),
                'valid_fraction': float(valid.mean()), 'elevation_range_source_ft': [float(values[valid].min()), float(values[valid].max())] if valid.any() else None,
                'vertical_reference': {'datum': metadata['vertical_datum'], 'unit': metadata['vertical_unit'], 'geotiff_vertical_epsg': vertical_epsg,
                    'evidence': 'source XML plus GeoTIFF vertical unit key when present', 'geotiff_vertical_unit_key': vertical},
                'source_origin_top_left_ft': [x0, y0], 'metadata': metadata}, values, valid


def seam_metrics(edge_a, inner_a, edge_b, inner_b):
    valid = np.isfinite(edge_a) & np.isfinite(inner_a) & np.isfinite(edge_b) & np.isfinite(inner_b)
    if not valid.any():
        return {'valid_pairs': 0, 'status': 'unknown_no_valid_pairs'}
    jump = (edge_b[valid].astype(np.float64) - edge_a[valid]) * US_FOOT_M
    expected = ((edge_a[valid] - inner_a[valid]) + (inner_b[valid] - edge_b[valid])) * .5 * US_FOOT_M
    residual = jump - expected
    return {'valid_pairs': int(valid.sum()), 'median_signed_step_m': float(np.median(jump)),
            'p95_absolute_step_m': float(np.percentile(np.abs(jump), 95)),
            'median_signed_residual_m': float(np.median(residual)),
            'p95_absolute_residual_m': float(np.percentile(np.abs(residual), 95)),
            'max_absolute_residual_m': float(np.max(np.abs(residual))),
            'note': 'Adjacent pixel-center differences include real terrain slope; residual subtracts mean neighboring interior slope. This is discontinuity screening, not survey accuracy.'}


def analyze_seams(tiles, edges, thresholds):
    output = []
    for i, a in enumerate(tiles):
        ax0, ay0, ax1, ay1 = a['source_bounds_ft']
        for b in tiles[i + 1:]:
            bx0, by0, bx1, by1 = b['source_bounds_ft']
            side = None
            if abs(ax1 - bx0) < .001 and abs(ay0 - by0) < .001 and abs(ay1 - by1) < .001:
                side, first, second, opposite = 'east_west', a, b, ('east', 'west')
            elif abs(bx1 - ax0) < .001 and abs(ay0 - by0) < .001 and abs(ay1 - by1) < .001:
                side, first, second, opposite = 'east_west', b, a, ('east', 'west')
            elif abs(ay0 - by1) < .001 and abs(ax0 - bx0) < .001 and abs(ax1 - bx1) < .001:
                side, first, second, opposite = 'north_south', a, b, ('south', 'north')
            elif abs(by0 - ay1) < .001 and abs(ax0 - bx0) < .001 and abs(ax1 - bx1) < .001:
                side, first, second, opposite = 'north_south', b, a, ('south', 'north')
            if side:
                e1, e2 = edges[first['id']][opposite[0]], edges[second['id']][opposite[1]]
                metrics = seam_metrics(e1[0], e1[1], e2[0], e2[1])
                status = 'review' if metrics.get('valid_pairs', 0) and (abs(metrics['median_signed_residual_m']) > thresholds['absolute_median_residual'] or metrics['p95_absolute_residual_m'] > thresholds['p95_absolute_residual']) else 'screen_pass' if metrics.get('valid_pairs', 0) else 'unknown'
                output.append({'tile_a': first['id'], 'tile_b': second['id'], 'orientation': side, 'status': status, **metrics})
    return output


def study_grid(configuration, first_tile):
    projection = Transformer.from_crs(4326, first_tile['horizontal_epsg'], always_xy=True)
    bounds = projection.transform_bounds(*configuration['study_bbox_wgs84'], densify_pts=21)
    step = first_tile['pixel_scale_source_ft'][0]
    ox, oy = first_tile['source_origin_top_left_ft']
    left = ox + np.floor((bounds[0] - ox) / step) * step
    top = oy + np.ceil((bounds[3] - oy) / step) * step
    width, height = int(np.ceil((bounds[2] - left) / step)), int(np.ceil((top - bounds[1]) / step))
    if not 0 < width * height <= 30000000:
        raise ValueError('Study grid exceeded bounded 30-million-pixel limit')
    return {'left_ft': float(left), 'top_ft': float(top), 'pixel_size_ft': step, 'width': width, 'height': height,
            'horizontal_epsg': first_tile['horizontal_epsg']}


def paste_tile(mosaic, covered, grid, tile, values, valid):
    step = grid['pixel_size_ft']
    xfloat = (tile['source_origin_top_left_ft'][0] - grid['left_ft']) / step
    yfloat = (grid['top_ft'] - tile['source_origin_top_left_ft'][1]) / step
    if abs(xfloat - round(xfloat)) > 1e-5 or abs(yfloat - round(yfloat)) > 1e-5:
        raise ValueError('Tile pixels are not on the common source grid')
    x, y = round(xfloat), round(yfloat)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(grid['width'], x + tile['width']), min(grid['height'], y + tile['height'])
    if x0 >= x1 or y0 >= y1:
        return {'overlap_valid_pixels': 0, 'overlap_max_difference_m': None}
    local = values[y0 - y:y1 - y, x0 - x:x1 - x]
    local_valid = valid[y0 - y:y1 - y, x0 - x:x1 - x]
    target = mosaic[y0:y1, x0:x1]
    overlap = np.isfinite(target) & local_valid
    difference = float(np.max(np.abs(target[overlap].astype(np.float64) - local[overlap])) * US_FOOT_M) if overlap.any() else None
    target[~np.isfinite(target) & local_valid] = local[~np.isfinite(target) & local_valid]
    covered[y0:y1, x0:x1] = True
    return {'overlap_valid_pixels': int(overlap.sum()), 'overlap_max_difference_m': difference}


def coverage_evidence(mosaic, covered, grid, bbox, folder):
    to_wgs = Transformer.from_crs(grid['horizontal_epsg'], 4326, always_xy=True)
    inside = np.zeros(mosaic.shape, dtype=bool)
    xs = grid['left_ft'] + (np.arange(grid['width']) + .5) * grid['pixel_size_ft']
    for row in range(0, grid['height'], 64):
        ys = grid['top_ft'] - (np.arange(row, min(row + 64, grid['height'])) + .5) * grid['pixel_size_ft']
        xx, yy = np.meshgrid(xs, ys)
        lon, lat = to_wgs.transform(xx, yy)
        inside[row:row + len(ys)] = (lon >= bbox[0]) & (lon <= bbox[2]) & (lat >= bbox[1]) & (lat <= bbox[3])
    valid = np.isfinite(mosaic)
    count = int(inside.sum())
    valid_count = int((inside & valid).sum())
    nodata_count = int((inside & covered & ~valid).sum())
    uncovered_count = int((inside & ~covered).sum())
    if valid_count + nodata_count + uncovered_count != count:
        raise ValueError('Coverage denominator mismatch')
    np.savez_compressed(folder / 'study_valid_pixels.npz', valid=valid, source_covered=covered, inside_study=inside,
                        left_ft=grid['left_ft'], top_ft=grid['top_ft'], pixel_size_ft=grid['pixel_size_ft'], horizontal_epsg=grid['horizontal_epsg'])
    colors = np.full((*mosaic.shape, 3), 255, dtype=np.uint8)
    colors[inside & ~covered] = [155, 155, 155]
    colors[inside & covered & ~valid] = [213, 72, 60]
    colors[inside & valid] = [40, 142, 85]
    Image.fromarray(colors).save(folder / 'study_valid_pixels.png')
    return {'grid': grid, 'study_bbox_wgs84': bbox, 'study_pixel_centers': count, 'valid_elevation_pixels': valid_count,
            'nodata_pixels_within_source_tiles': nodata_count, 'uncovered_pixels': uncovered_count,
            'valid_pixel_fraction': valid_count / count if count else None,
            'method': 'Every source-grid pixel center inside the WGS84 extraction rectangle is checked against decoded raster validity; not metadata-envelope coverage.',
            'mask_file': str(folder / 'study_valid_pixels.npz'), 'image_file': str(folder / 'study_valid_pixels.png'),
            'colors': {'green': 'decoded valid elevation', 'red': 'source tile NoData', 'gray': 'no source tile', 'white': 'outside extraction rectangle'},
            'limitations': 'Pixel validity does not establish surveyed accuracy, current conditions, curb detail or continuous coverage between pixel centers.'}


def acquire(root=ROOT, offline=False):
    config_path = root / 'config/terrain_sources.json'
    configuration = json.loads(config_path.read_text(encoding='utf-8'))
    sources = configuration['tiles']
    if len(sources) != 6 or configuration['maximum_tile_count'] != 6 or len({t['id'] for t in sources}) != len(sources):
        raise ValueError('Expected exactly the configured six distinct DEM tiles')
    if any(not re_id(t['id']) for t in sources):
        raise ValueError('Unsafe tile identifier')
    folder = root / 'data/heights/dem'
    folder.mkdir(parents=True, exist_ok=True)
    def fetch(tile):
        path = folder / (tile['id'] + '.tif')
        meta_path = folder / (tile['id'] + '.xml')
        dem_receipt = download(tile['download_url'], path, configuration['maximum_tile_bytes'], offline)
        meta_receipt = download(tile['metadata_url'], meta_path, configuration['maximum_metadata_bytes'], offline)
        return tile, path, meta_path, dem_receipt, meta_receipt
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        downloads = list(pool.map(fetch, sources))
    rows, edges, overlaps = [], {}, []
    mosaic = covered = grid = None
    for source, path, meta_path, receipt, meta_receipt in downloads:
        row, values, valid = inspect_tile(path, parse_metadata(meta_path), configuration)
        row.update({'id': source['id'], 'file': str(path), 'source_receipt': receipt, 'metadata_receipt': meta_receipt,
                    'index_object_id': source['index_object_id']})
        values[~valid] = np.nan
        edges[source['id']] = {'north': [values[0].copy(), values[1].copy()], 'south': [values[-1].copy(), values[-2].copy()],
                               'west': [values[:, 0].copy(), values[:, 1].copy()], 'east': [values[:, -1].copy(), values[:, -2].copy()]}
        if grid is None:
            grid = study_grid(configuration, row)
            mosaic = np.full((grid['height'], grid['width']), np.nan, dtype=np.float32)
            covered = np.zeros(mosaic.shape, dtype=bool)
        if row['horizontal_epsg'] != grid['horizontal_epsg']:
            raise ValueError('Tiles have mixed horizontal CRS')
        overlaps.append({'tile_id': source['id'], **paste_tile(mosaic, covered, grid, row, values, valid)})
        rows.append(row)
        print('Validated', source['id'], row['width'], 'x', row['height'], 'valid', row['valid_pixels'], flush=True)
    coverage = coverage_evidence(mosaic, covered, grid, configuration['study_bbox_wgs84'], folder)
    seams = analyze_seams(rows, edges, configuration['seam_review_thresholds_m'])
    manifest = {'schema_version': 1, 'created_utc': now(), 'configuration_sha256': checksum(config_path),
                'source_acquisition_id': configuration['source_acquisition_id'], 'source_catalog_sha256': configuration['source_catalog_sha256'],
                'original_bytes_preserved': True, 'scene_or_snapshot_activated': False,
                'tiles': rows, 'study_coverage': coverage, 'overlap_checks': overlaps, 'adjacent_seams': seams,
                'seam_review_thresholds_m': configuration['seam_review_thresholds_m'],
                'unit_rule': 'Original TIFF horizontal and vertical values are US survey feet; EPT meter elevations are a separate transformed product.',
                'limits': ['2018-2019 historical acquisition, not current survey.', 'Hydro-flattened bare-earth raster does not resolve all curb or sidewalk geometry.',
                           'Seam screening thresholds are review triggers, not a survey-accuracy standard.', 'No terrain layer or application snapshot is activated.']}
    atomic_json(folder / 'manifest.json', manifest)
    print(json.dumps({'tiles': len(rows), 'bytes': sum(t['source_receipt']['bytes'] for t in rows),
                      'valid_pixel_fraction': coverage['valid_pixel_fraction'], 'nodata_pixels': coverage['nodata_pixels_within_source_tiles'],
                      'uncovered_pixels': coverage['uncovered_pixels'], 'seams': len(seams),
                      'seam_review_cases': sum(s['status'] == 'review' for s in seams), 'manifest': str(folder / 'manifest.json')}, indent=2))
    return manifest


def re_id(value):
    return isinstance(value, str) and value.isalnum()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    acquire(offline=args.offline)
