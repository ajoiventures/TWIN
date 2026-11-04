"""Bounded historical Princeton roof-zone proposal; no global height/registry edits.

All geometry is derived from USGS points. Current OCPA aerial is local review
only; no traced pixels/textures are promoted. Parcel outline is a search mask.
"""
from pathlib import Path
import argparse, concurrent.futures, datetime, hashlib, io, json, os, sys, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
import shapely
from shapely.geometry import shape, box, mapping
from shapely.ops import unary_union
from scipy import ndimage
from pyproj import Transformer
from PIL import Image
import laspy
from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf
from correct_wellesley import write_mesh, source_footprint, mesh_payload, digest


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def node_intersects(key, bounds, roi):
    depth, x, y, _ = map(int, key.split('-'))
    size = (bounds[3] - bounds[0]) / 2 ** depth
    left, bottom = bounds[0] + x * size, bounds[1] + y * size
    return left <= roi[2] and left + size >= roi[0] and bottom <= roi[3] and bottom + size >= roi[1]


class EptReader:
    def __init__(self, root, live):
        self.root, self.live = root, live
        self.cache = root / 'data/cache/princeton_ept'
        self.cache.mkdir(parents=True, exist_ok=True)
        self.receipts = []

    def json(self, url):
        key = hashlib.sha256(url.encode()).hexdigest() + '.json'
        old = self.root / 'data/cache/ept' / key
        local = self.cache / key
        if local.exists():
            item = read(local); self.receipts.append({k: v for k, v in item.items() if k != 'data'}); return item['data']
        if old.exists():
            raw = old.read_bytes(); self.receipts.append({'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'cache': str(old), 'fetched_utc': None, 'note': 'Existing accepted project cache; original network fetch time unknown'})
            return json.loads(raw)
        if not self.live:
            raise RuntimeError('Offline hierarchy cache miss: ' + url)
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('Bounded EPT hierarchy response exceeded limit')
        data = json.loads(raw)
        receipt = {'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'fetched_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        atomic_json(local, {**receipt, 'data': data}); self.receipts.append(receipt)
        return data

    def node(self, key, base, limit):
        old = self.root / 'data/cache/ept' / (key + '.laz')
        path = old if old.exists() else self.cache / (key + '.laz')
        url = base + 'ept-data/' + key + '.laz'
        if not path.exists():
            if not self.live:
                raise RuntimeError('Offline EPT node cache miss: ' + key)
            with urllib.request.urlopen(url, timeout=45) as response:
                raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('EPT node exceeded bounded byte limit')
            temporary = path.with_suffix('.part'); temporary.write_bytes(raw); os.replace(temporary, path)
        if path.stat().st_size > limit:
            raise ValueError('Cached EPT node exceeded byte limit')
        las = laspy.read(path)
        return np.column_stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z), np.asarray(las.classification)]), {
            'key': key, 'url': url, 'cache': str(path), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_points(config, parcel_geometry, root, live):
    reader = EptReader(root, live)
    meta = reader.json(config['ept_url'] + 'ept.json')
    polygon = shapely.transform(parcel_geometry, Transformer.from_crs(4326, 3857, always_xy=True).transform, interleaved=False)
    roi = polygon.bounds; nodes, visited = {}, set()
    def hierarchy(key):
        if key in visited:
            return
        visited.add(key)
        for child, count in reader.json(config['ept_url'] + 'ept-hierarchy/' + key + '.json').items():
            if int(child.split('-')[0]) > config['ept_max_depth'] or not node_intersects(child, meta['bounds'], roi):
                continue
            if count == -1:
                hierarchy(child)
            elif count > 0:
                nodes[child] = count
    hierarchy('0-0-0-0')
    if not nodes or len(nodes) > config['maximum_ept_nodes']:
        raise ValueError('Unexpected bounded Princeton EPT node count')
    chunks, receipts = [], []
    def load(key):
        values, info = reader.node(key, config['ept_url'], config['maximum_node_bytes'])
        keep = (values[:, 0] >= roi[0]) & (values[:, 0] <= roi[2]) & (values[:, 1] >= roi[1]) & (values[:, 1] <= roi[3])
        values = values[keep]
        values = values[shapely.contains_xy(polygon, values[:, 0], values[:, 1])]
        return values, info
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for values, info in pool.map(load, sorted(nodes)):
            chunks.append(values); receipts.append(info)
    points = np.concatenate(chunks)
    points[:, 0], points[:, 1] = Transformer.from_crs(3857, 32617, always_xy=True).transform(points[:, 0], points[:, 1])
    return points, {'ept_url': config['ept_url'], 'max_depth': config['ept_max_depth'], 'required_nodes': len(nodes),
                    'node_receipts': receipts, 'hierarchy_receipts': reader.receipts, 'search_bbox_ept': list(roi),
                    'acquisition': '2018-12-04 to2019-04-12 project interval; local flight date/construction phase uncertain',
                    'coordinate_reference': 'EPSG:32617 XY after conversion; NAVD88 meters Z', 'global_pilot_unchanged': True}


def roof_zones(points, config):
    ground = points[points[:, 3] == 2, 2]
    if len(ground) < 100:
        raise ValueError('Insufficient local ground')
    ground_z = float(np.median(ground))
    values = points[np.isin(points[:, 3], [1, 6]) & (points[:, 2] > ground_z + 6) & (points[:, 2] < ground_z + 30)]
    size = config['grid_cell_m']; xmin, ymin = np.floor(values[:, :2].min(axis=0) / size) * size
    ix = np.floor((values[:, 0] - xmin) / size).astype(int); iy = np.floor((values[:, 1] - ymin) / size).astype(int)
    width, height = int(ix.max() + 1), int(iy.max() + 1)
    if width * height > 100000:
        raise ValueError('Roof-cell grid exceeded bound')
    codes = iy * width + ix; order = np.argsort(codes)
    ids, starts, counts = np.unique(codes[order], return_index=True, return_counts=True)
    elevations = np.full((height, width), np.nan)
    for code, start, count in zip(ids, starts, counts):
        z = values[order[start:start + count], 2]
        if count >= config['minimum_cell_points'] and np.percentile(z, 85) - np.percentile(z, 15) <= config['maximum_cell_spread_m']:
            elevations.flat[code] = np.median(z)
    zones, masks = [], []
    for band in config['zone_bands']:
        raw = (elevations >= band['min_z_m']) & (elevations < band['max_z_m'])
        mask = ndimage.binary_closing(raw, iterations=1)
        labels, _ = ndimage.label(mask); counts = np.bincount(labels.ravel())
        keep = [i for i, count in enumerate(counts) if i and count * size * size >= config['minimum_component_m2']]
        mask = np.isin(labels, keep)
        gaps = ndimage.binary_fill_holes(mask) & ~mask
        gl, _ = ndimage.label(gaps); gc = np.bincount(gl.ravel())
        fill = [i for i, count in enumerate(gc) if i and count * size * size <= config['gap_infill_m2']]
        mask |= np.isin(gl, fill)
        ys, xs = np.where(mask)
        geometry = unary_union([box(xmin + x * size, ymin + y * size, xmin + (x + 1) * size, ymin + (y + 1) * size) for y, x in zip(ys, xs)])
        geometry = geometry.simplify(config['simplify_m'], preserve_topology=True)
        supported = elevations[mask & raw]
        if geometry.is_empty or len(supported) < 30:
            continue
        z = float(np.median(supported))
        support_points = values[(mask & raw).ravel()[codes]]
        classes, class_counts = np.unique(support_points[:, 3].astype(int), return_counts=True)
        class_support = {str(int(k)): int(v) for k, v in zip(classes, class_counts)}
        zones.append({'class_support_points_in_supported_cells': class_support, 'classification_caveat': 'Class1 is unclassified, not certified roof; smooth canopy/equipment/construction remain possible.', 'id': band['id'], 'geometry': geometry, 'roof_z_m': z, 'ground_z_m': ground_z, 'height_m': round(z - ground_z, 2),
                      'supported_cells': len(supported), 'area_m2': geometry.area, 'planar_cell_z_p05_p95_m': np.percentile(supported, [5, 95]).tolist(),
                      'storeys': None, 'interpretation': band['local_review_interpretation'], 'quality': 'historical_point_derived_flat_zone_approximation; architectural pitch/details unresolved'})
        masks.append(mask)
    if len(zones) != len(config['zone_bands']):
        raise ValueError('Insufficient stepped roof-zone evidence; do not extrude parcel')
    return zones, elevations, masks, {'left_utm_m': float(xmin), 'bottom_utm_m': float(ymin), 'cell_m': size, 'ground_median_m': ground_z}


def validate_voids(geometry, config):
    """Fail closed if frozen point-derived courtyard seeds become roof faces."""
    checks = []
    for item in config.get('protected_voids_utm', []):
        void = box(*item['bounds'])
        overlap = geometry.intersection(void).area
        if overlap > 1e-7:
            raise ValueError('Protected courtyard void filled: ' + item['id'])
        checks.append({**item, 'roof_overlap_m2': overlap, 'status': 'preserved'})
    return checks


def disjoint_zones(zones, parcel):
    occupied = shapely.GeometryCollection()
    changes = []
    for zone in zones[:2]:
        clipped = zone['geometry'].intersection(parcel)
        trimmed = clipped.difference(occupied)
        changes.append({'id': zone['id'], 'removed_overlap_m2': clipped.area - trimmed.area})
        zone['geometry'] = trimmed
        zone['area_m2'] = trimmed.area
        occupied = occupied.union(trimmed)
    return occupied, changes


def legacy_overlap(footprint, parcel, match_method, source_pin, current_pin, minimum):
    ratio = footprint.intersection(parcel).area / footprint.area if footprint.area else 0
    approved = ratio >= minimum and match_method == 'spatial_review' and source_pin != current_pin
    return {'parcel_overlap_ratio': ratio, 'supersession_supported': approved,
            'action': 'hide_full' if approved and ratio >= 1 - 1e-6 else 'retain_only_outside_property_remainder' if approved else 'leave_unmodified',
            'reason': 'Current official redevelopment identity/year plus high-roof complex and local2025review show detached source groups obsolete; original source lineage retained' if approved else 'Insufficient verified overlap/identity; leave source geometry visible for review'}


def alternate_source_review(root, config, live):
    client = EptReader(root, live)
    urls = {'city_building_search': 'https://www.arcgis.com/sharing/rest/search?' + urllib.parse.urlencode({
        'f': 'json', 'q': 'orgid:mMuoPCaIYD4wEgDl AND (building OR footprint)', 'num': 50}),
        'ocpa_public_base': 'https://vgispublic.ocpafl.org/server/rest/services/OCPA/Base/MapServer?f=json',
        'current_project_property': 'https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4/query?' + urllib.parse.urlencode({
            'f': 'json', 'where': "PARCEL='" + config['parcel_id'] + "'", 'outFields': 'OBJECTID,PARCEL,SITUS,PROP_NAME,STYS,AYB', 'returnGeometry': 'false'})}
    output = {}
    for name, url in urls.items():
        try:
            data = client.json(url)
            if name == 'city_building_search':
                output[name] = {'url': url, 'total': data.get('total'), 'next_start': data.get('nextStart'),
                    'candidates': [{k: r.get(k) for k in ['id', 'title', 'type', 'url']} for r in data.get('results', [])],
                    'selection_status': 'No alternate current whole-building footprint source accepted from this bounded org query; results require feature/schema/currentness review.'}
            elif name == 'ocpa_public_base':
                output[name] = {'url': url, 'building_named_layers': [r for r in data.get('layers', []) if any(s in r.get('name', '').lower() for s in ['bldg', 'building', 'footprint'])],
                    'selection_status': 'Base-map layer-name inspection only; no alternate current footprint promoted.'}
            else:
                rows = [{k: r['attributes'].get(k) for k in ['OBJECTID', 'PARCEL', 'SITUS', 'PROP_NAME', 'STYS', 'AYB']} for r in data.get('features', [])]
                output[name] = {'url': url, 'safe_property_rows': rows}
        except Exception as exc:
            output[name] = {'url': url, 'status': 'unresolved_access', 'error': type(exc).__name__ + ': ' + str(exc)}
    output['request_receipts'] = client.receipts
    return output


def surface_geometry(mask, elevation_grid, grid_info, origin, ground, clip_geometry):
    """Piecewise-linear supported roof, shared corner heights, exterior walls only.

    Keeps eastern hipped roofs from becoming one flat 13m slab. Holes and the
    pool courtyard are not filled; unsupported interior gaps remain uncertainty.
    """
    source_valid = mask & np.isfinite(elevation_grid)
    if not source_valid.any():
        raise ValueError('No roof elevations for surface mesh')
    nearest = ndimage.distance_transform_edt(~source_valid, return_distances=False, return_indices=True)
    filled = elevation_grid[tuple(nearest)]
    height, width = mask.shape
    sums = np.zeros((height + 1, width + 1)); counts = np.zeros_like(sums)
    for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        sums[dy:dy + height, dx:dx + width] += np.where(mask, filled, 0)
        counts[dy:dy + height, dx:dx + width] += mask
    corners = sums / np.maximum(counts, 1)
    step = grid_info['cell_m']; xbase, ybase = grid_info['left_utm_m'], grid_info['bottom_utm_m']
    points, face_counts, indices = [], [], []
    def face(coords):
        start = len(points); points.extend(coords); face_counts.append(len(coords)); indices.extend(range(start, len(points)))
    for y, x in zip(*np.where(mask)):
        x0, y0 = xbase + x * step, ybase + y * step
        polygon = box(x0, y0, x0 + step, y0 + step).intersection(clip_geometry)
        if polygon.is_empty or polygon.area < 1e-8:
            continue
        def top(a, b):
            tx, ty = (a - x0) / step, (b - y0) / step
            z = (1 - tx) * (1 - ty) * corners[y, x] + tx * (1 - ty) * corners[y, x + 1] + tx * ty * corners[y + 1, x + 1] + (1 - tx) * ty * corners[y + 1, x]
            return (float(a - origin[0]), float(b - origin[1]), float(z - ground + .1))
        polygon = shapely.orient_polygons(polygon, exterior_cw=False)
        for triangle in shapely.constrained_delaunay_triangles(polygon).geoms:
            coords = list(triangle.exterior.coords)[:-1]
            if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(coords, coords[1:] + coords[:1])) < 0:
                coords.reverse()
            face([top(a, b) for a, b in coords]); face([(a - origin[0], b - origin[1], .1) for a, b in reversed(coords)])
        for ring in [polygon.exterior, *polygon.interiors]:
            coords = list(ring.coords)
            for a, b in zip(coords, coords[1:]):
                internal = ((abs(a[0] - x0) < 1e-7 and abs(b[0] - x0) < 1e-7 and x > 0 and mask[y, x - 1]) or
                            (abs(a[0] - x0 - step) < 1e-7 and abs(b[0] - x0 - step) < 1e-7 and x + 1 < width and mask[y, x + 1]) or
                            (abs(a[1] - y0) < 1e-7 and abs(b[1] - y0) < 1e-7 and y > 0 and mask[y - 1, x]) or
                            (abs(a[1] - y0 - step) < 1e-7 and abs(b[1] - y0 - step) < 1e-7 and y + 1 < height and mask[y + 1, x]))
                if not internal:
                    face([(a[0] - origin[0], a[1] - origin[1], .1), (b[0] - origin[0], b[1] - origin[1], .1), top(*b), top(*a)])
    if not points or max(indices) >= len(points) or sum(face_counts) != len(indices):
        raise ValueError('Invalid roof surface topology')
    return points, face_counts, indices


def write_surface(stage, path, geometry):
    points, counts, indices = geometry
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(points); mesh.CreateFaceVertexCountsAttr(counts); mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateSubdivisionSchemeAttr('none'); mesh.CreateDoubleSidedAttr(True)
    mesh.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in points) for i in range(3))), Gf.Vec3f(*(max(p[i] for p in points) for i in range(3)))])
    normals, offset = [], 0
    for count in counts:
        a, b, c = [np.asarray(points[i]) for i in indices[offset:offset + 3]]
        n = np.cross(b - a, c - a); length = np.linalg.norm(n)
        normals.append(tuple(n / length) if length else (0, 0, 1)); offset += count
    mesh.CreateNormalsAttr(normals); mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
    uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    uv.Set([(points[i][0] / 5, points[i][1] / 5) for i in indices])
    return mesh


def build(root=ROOT, live=False):
    config_path = root / 'config/princeton_sources.json'; config = read(config_path)
    active = read(root / 'data/processed/active.json'); folder = (root / active['relative_path']).resolve()
    if not folder.is_relative_to((root / 'data/snapshots').resolve()):
        raise ValueError('Invalid snapshot path')
    parcels = read(folder / 'parcels.json')['features']; matches = [f for f in parcels if f['properties']['parcel_id'] == config['parcel_id']]
    if len(matches) != 1:
        raise ValueError('Expected one current Princeton project parcel')
    prop = matches[0]['properties']; parcel = shape(matches[0]['geometry'])
    if prop['stories'] != config['reported_project_maximum_storeys'] or prop['year_built'] != config['year_built']:
        raise ValueError('Official project story/year evidence changed')
    units = read(root / 'data/heights/vertical_unit_check.json')
    if not units.get('accepted') or units.get('ept_z_unit') != 'meters':
        raise ValueError('EPT vertical units not accepted')
    points, cloud_evidence = read_points(config, parcel, root, live)
    zones, grid, masks, grid_info = roof_zones(points, config)
    to_utm = Transformer.from_crs(4326, 32617, always_xy=True)
    parcel_utm = shapely.transform(parcel, to_utm.transform, interleaved=False)
    origin = to_utm.transform(*config['origin_wgs84'])
    flat_footprint, overlap_resolution = disjoint_zones(zones, parcel_utm)
    east_clip = parcel_utm.difference(flat_footprint)
    eastern_mask = masks[2] | masks[3]
    ys, xs = np.where(eastern_mask)
    step = grid_info['cell_m']; left = grid_info['left_utm_m']; bottom = grid_info['bottom_utm_m']
    east_footprint = unary_union([box(left+x*step, bottom+y*step, left+(x+1)*step, bottom+(y+1)*step) for y,x in zip(ys,xs)]).intersection(east_clip)
    combined = flat_footprint.union(east_footprint)
    void_checks = validate_voids(combined, config)
    if combined.area > parcel_utm.area * .85:
        raise ValueError('Roof proposal filled too much project parcel; courtyard/parking mask must be reviewed')
    source = Usd.Stage.Open(str(root / 'scene/college_park.usda'))
    records = read(folder / 'buildings.json'); by_id = {r['id']: r for r in records}
    guarded, supersession, outside_fragments = [], [], {}
    height_rows = {r['building_id']: r for r in read(root / 'data/heights/building_heights.json')}
    for guard in config['legacy_groups']:
        found = []
        for prim in source.GetPrimAtPath('/World/Buildings').GetChildren():
            data = prim.GetCustomData()
            if data.get('parcelId') == guard['source_parcel_id'] and str(data.get('buildingNumber')) == guard['source_building_number'] and sorted(data.get('sourceObjectIds', '').split(',')) == guard['source_object_ids']:
                found.append(prim)
        if len(found) != 1:
            raise ValueError('Legacy group identity changed')
        prim = found[0]; row = by_id[prim.GetName()]
        if row.get('parcel_id') != config['parcel_id'] or row['match_method'] != guard['expected_match_method']:
            raise ValueError('Legacy group current assignment changed')
        if digest(mesh_payload(UsdGeom.Mesh(prim))) != guard['source_mesh_sha256']:
            raise ValueError('Legacy source mesh changed; supersession needs fresh review')
        footprint = source_footprint(UsdGeom.Mesh(prim))
        absolute = shapely.transform(footprint, lambda x, y: (x + origin[0], y + origin[1]), interleaved=False)
        review = legacy_overlap(absolute, parcel_utm, row['match_method'], row['source_parcel_id'], config['parcel_id'], config['minimum_supersession_parcel_overlap'])
        if review['action'] == 'retain_only_outside_property_remainder':
            outside = absolute.difference(parcel_utm)
            outside_fragments[row['id']] = shapely.transform(outside, lambda x, y: (x - origin[0], y - origin[1]), interleaved=False)
            review['retained_outside_area_m2'] = outside.area
        supersession.append({'building_id': row['id'], 'usd_path': row['usd_path'], 'source_parcel_id': row['source_parcel_id'], **review})
        guarded.append(row['id'])
    out = root / 'data/heights/princeton'; out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'points.npz', points=points)
    image = np.full((*grid.shape, 3), 255, np.uint8)
    palette = [(154, 72, 185), (40, 160, 90), (60, 125, 190), (210, 160, 55)]
    for mask, color in zip(masks, palette):
        image[mask] = color
    Image.fromarray(image[::-1]).resize((grid.shape[1] * 6, grid.shape[0] * 6)).save(out / 'roof_zones.png')
    layer_path = root / 'scene/princeton_correction.usda'; layer = Usd.Stage.CreateNew(str(layer_path))
    UsdGeom.SetStageMetersPerUnit(layer, 1); UsdGeom.SetStageUpAxis(layer, 'Z')
    project = UsdGeom.Xform.Define(layer, '/World/Landmarks/PrincetonAtCollegePark')
    project.GetPrim().SetCustomData({'projectId': config['project_id'], 'parcelId': config['parcel_id'], 'siteAddress': config['site_address'],
        'reportedMaximumStories': config['reported_project_maximum_storeys'], 'yearBuilt': config['year_built'], 'sourceSnapshot': active['snapshot'],
        'quality': 'historical USGS point-derived stepped roof-zone proposal, not current survey or as-built footprint',
        'imageryUse': 'local qualitative review only; geometry derived from USGS points, no image textures/tracing',
        'originalParcelLinks': 'Legacy spatial-review links are not promoted'})
    for i, zone in enumerate(zones[:2]):
        geometry = zone['geometry'].intersection(parcel_utm)
        local = shapely.transform(geometry, lambda x, y: (x - origin[0], y - origin[1]), interleaved=False)
        path = str(project.GetPath()) + '/' + zone['id']
        UsdGeom.Mesh.Define(layer, path)
        mesh = write_mesh(layer, path, [(local, .1, .1 + zone['height_m'])])
        mesh.CreateDisplayColorAttr([Gf.Vec3f(.66 + .025 * i, .69 + .015 * i, .66)])
        mesh.GetPrim().SetCustomData({'roofElevationMetersNAVD88': zone['roof_z_m'], 'heightAboveLocalGroundMeters': zone['height_m'],
                                    'quality': zone['quality'], 'storeyCount': 'unknown per component; project maximum6 is separate'})
    eastern_mask = masks[2] | masks[3]
    eastern_grid = np.where((grid >= config['zone_bands'][2]['min_z_m']) & (grid < config['zone_bands'][3]['max_z_m']), grid, np.nan)
    surface = surface_geometry(eastern_mask, eastern_grid, grid_info, origin, grid_info['ground_median_m'], east_clip)
    east = write_surface(layer, str(project.GetPath()) + '/EasternVariableRoof', surface)
    east.CreateDisplayColorAttr([Gf.Vec3f(.73, .74, .72)])
    east.GetPrim().SetCustomData({'quality': 'historical cell-supported piecewise-linear hipped/flat roof approximation; no uniform project-storey extrusion',
                                'storeyCount': 'unknown per wing; project maximum6 separate', 'gridCellMeters': config['grid_cell_m']})
    for item in supersession:
        if item['action'] == 'hide_full':
            for path in [item['usd_path'], '/World/Roofs/Roof_' + item['building_id'].split('_')[-1], '/World/Storefronts/' + item['building_id']]:
                UsdGeom.Imageable(layer.OverridePrim(path)).CreateVisibilityAttr('invisible')
        elif item['action'] == 'retain_only_outside_property_remainder':
            height = height_rows[item['building_id']]['height_m']
            geometry = outside_fragments[item['building_id']]
            write_mesh(layer, item['usd_path'], [(geometry, .1, .1 + height)])
            write_mesh(layer, '/World/Roofs/Roof_' + item['building_id'].split('_')[-1], [(geometry, .1, .12 + height)], roofs_only=True)
            UsdGeom.Imageable(layer.OverridePrim('/World/Storefronts/' + item['building_id'])).CreateVisibilityAttr('invisible')
    camera = UsdGeom.Camera.Define(layer, '/World/Cameras/PrincetonEvidence')
    centroid = shapely.transform(combined, lambda x, y: (x - origin[0], y - origin[1]), interleaved=False).centroid
    eye = Gf.Vec3d(float(centroid.x) - 130, float(centroid.y) - 130, 100)
    target = Gf.Vec3d(float(centroid.x), float(centroid.y), 9)
    camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse())
    camera.CreateFocalLengthAttr(27); camera.CreateClippingRangeAttr(Gf.Vec2f(.1, 10000))
    layer.GetRootLayer().customLayerData = {'purpose': 'Princeton historical stepped component proposal; no uniform six-floor parcel extrusion', 'sourceSnapshot': active['snapshot'], 'activation': 'Parent review/composition required'}
    layer.GetRootLayer().Save()
    to_wgs = Transformer.from_crs(32617, 4326, always_xy=True)
    geojson = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': mapping(shapely.transform(z['geometry'], to_wgs.transform, interleaved=False)),
        'properties': {k: v for k, v in z.items() if k != 'geometry'}} for z in zones]}
    atomic_json(out / 'roof_zones.geojson', geojson)
    manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_snapshot': active['snapshot'],
                'configuration_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(), 'project_id': config['project_id'],
                'official_parcel': prop, 'reported_project_maximum_storeys': config['reported_project_maximum_storeys'],
                'cloud': cloud_evidence, 'point_count': len(points), 'grid': grid_info,
                'components': [{k: v for k, v in z.items() if k != 'geometry'} for z in zones],
                'rendered_component_names': ['highest_west_zone', 'middle_height_zone', 'EasternVariableRoof'],
                'eastern_variable_roof': {'grid_cell_m': config['grid_cell_m'], 'faces': len(surface[1]), 'vertices': len(surface[0]),
                    'height_range_above_ground_m': [min(p[2] for p in surface[0] if p[2] > .10001) - .1, max(p[2] for p in surface[0]) - .1],
                    'method': 'Nearest supported roof cells fill only accepted morphology cells; adjacent-cell corner averaging yields continuous piecewise-linear roof with preserved courtyard holes',
                    'quality': 'historical roof-surface approximation; source pixel size/planarity/phase uncertainty retained'},
                'protected_void_checks': void_checks, 'overlap_resolution': overlap_resolution,
                'action': 'proposal_ready_for_parent_review_not_composed',
                'acceptance': 'historical_component_reconstruction_only_current_as_built_validation_pending',
                'derived_roof_union_area_m2': combined.area, 'parcel_area_m2': parcel_utm.area, 'legacy_supersession': supersession,
                'global_height_rows_modified': 0, 'global_registry_modified': False, 'root_assembly_modified': False,
                'aerial_review': config['aerial_review'], 'documentary_sources': config['documentary_sources'],
                'alternate_current_source_review': alternate_source_review(root, config, live),
                'layer': str(layer_path), 'camera': '/World/Cameras/PrincetonEvidence',
                'limitations': ['Planarity and density do not certify roof classification; class1 smooth canopy/equipment may survive; per-zone class support is explicit.',
                               'Historical cloud may overlap construction phase; current component footprint/architectural pitch not surveyed.',
                               'Representative flat west/middle bands and variable eastern roof approximate stepped levels; no component is automatically assigned six storeys.',
                               'Parking-deck ramps, vehicles, equipment and interior gaps may require separate geometry review.',
                               'No traced imagery or source imagery redistribution; official parcel boundary used only as search/clip mask.']}
    atomic_json(out / 'manifest.json', manifest)
    print(json.dumps({'point_count': len(points), 'required_nodes': cloud_evidence['required_nodes'], 'components': manifest['components'],
                      'roof_union_m2': combined.area, 'parcel_m2': parcel_utm.area,
                      'obsolete_groups_superseded_inside_project': sum(x['supersession_supported'] for x in supersession),
                      'fully_hidden_groups': sum(x['action'] == 'hide_full' for x in supersession),
                      'outside_fragments_retained': sum(x['action'] == 'retain_only_outside_property_remainder' for x in supersession), 'layer': str(layer_path)}, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--live', action='store_true'); args = parser.parse_args()
    build(live=args.live)
