"""Scoped historical Wellesley correction: planar class-1 roof, not tax extrusion.

Writes an additive layer and only the resolved Wellesley height record. Source geometry,
old unmatched parcel lineage and every other height row are preserved.
"""
from pathlib import Path
import collections, datetime, hashlib, json, os, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
import shapely
from shapely.geometry import shape, box, Polygon, mapping
from shapely.ops import unary_union
from scipy import ndimage
from pyproj import Transformer
from PIL import Image
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def mesh_payload(mesh):
    return {'points': [[float(v) for v in p] for p in mesh.GetPointsAttr().Get()],
            'counts': list(mesh.GetFaceVertexCountsAttr().Get()), 'indices': list(mesh.GetFaceVertexIndicesAttr().Get())}


def resolve_target(config, source_stage, records):
    matches = []
    for prim in source_stage.GetPrimAtPath('/World/Buildings').GetChildren():
        data = prim.GetCustomData()
        if data.get('parcelId') == config['source_parcel_id'] and str(data.get('buildingNumber')) == config['source_building_number']:
            if sorted(data.get('sourceObjectIds', '').split(',')) == config['source_object_ids']:
                matches.append(prim)
    if len(matches) != 1:
        raise ValueError('Expected one exact source-identity/subarea match, independent of generated Building ID')
    prim = matches[0]
    records = [r for r in records if r['id'] == prim.GetName() and r['usd_path'] == str(prim.GetPath())]
    if len(records) != 1:
        raise ValueError('Resolved source mesh does not have one current snapshot building row')
    return records[0], prim


def validate_guard(config, active, record, source_prim, cloud_path):
    if not active.get('snapshot'):
        raise ValueError('No current source snapshot')
    data = source_prim.GetCustomData()
    if record['source_parcel_id'] != config['source_parcel_id'] or record['match_method'] != config['expected_match_method']:
        raise ValueError('Source building/parcel identity or match status changed')
    if data.get('parcelId') != config['source_parcel_id'] or str(data.get('buildingNumber')) != config['source_building_number']:
        raise ValueError('Original source parcel/building number changed')
    if sorted(data.get('sourceObjectIds', '').split(',')) != config['source_object_ids']:
        raise ValueError('Original footprint subarea membership changed')
    if digest(mesh_payload(UsdGeom.Mesh(source_prim))) != config['source_base_mesh_sha256']:
        raise ValueError('Original source mesh changed; correction cannot be silently reapplied')
    if hashlib.sha256(cloud_path.read_bytes()).hexdigest() != config['source_cloud_sha256']:
        raise ValueError('Source point cloud changed; roof extraction needs review')


def planar_roof(points, parameters):
    ground = points[points[:, 3] == 2, 2]
    if len(ground) < 50:
        raise ValueError('Insufficient local classified ground support')
    ground_z = float(np.median(ground))
    source = points[(points[:, 3] == 1) & (points[:, 2] > ground_z + parameters['minimum_height_above_ground_m']) &
                    (points[:, 2] < ground_z + parameters['maximum_height_above_ground_m'])]
    if len(source) < 1000:
        raise ValueError('Insufficient unclassified high-surface support')
    histogram, bins = np.histogram(source[:, 2], bins=np.arange(ground_z + parameters['minimum_height_above_ground_m'],
                                                               ground_z + parameters['maximum_height_above_ground_m'], parameters['histogram_bin_m']))
    peak = int(histogram.argmax())
    plane = float((bins[peak] + bins[peak + 1]) / 2)
    size = parameters['cell_size_m']
    xmin, ymin = np.floor(source[:, :2].min(axis=0) / size) * size
    ix, iy = np.floor((source[:, 0] - xmin) / size).astype(int), np.floor((source[:, 1] - ymin) / size).astype(int)
    width, height = int(ix.max() + 1), int(iy.max() + 1)
    if width * height > 100000:
        raise ValueError('Roof raster exceeded bounded local grid')
    codes = iy * width + ix
    order = np.argsort(codes)
    ids, starts, counts = np.unique(codes[order], return_index=True, return_counts=True)
    accepted = np.zeros((height, width), dtype=bool)
    support_z = []
    for code, start, count in zip(ids, starts, counts):
        elevations = source[order[start:start + count], 2]
        if count < parameters['minimum_cell_points']:
            continue
        median = float(np.median(elevations))
        spread = float(np.percentile(elevations, 85) - np.percentile(elevations, 15))
        if abs(median - plane) <= parameters['maximum_cell_plane_deviation_m'] and spread <= parameters['maximum_cell_p85_p15_m']:
            accepted.flat[code] = True
            support_z.extend(elevations.tolist())
    raw_accepted = accepted.copy()
    if parameters['opening_iterations']:
        accepted = ndimage.binary_opening(accepted, iterations=parameters['opening_iterations'])
    if parameters['closing_iterations']:
        accepted = ndimage.binary_closing(accepted, iterations=parameters['closing_iterations'])
    labels, _ = ndimage.label(accepted)
    component_counts = np.bincount(labels.ravel())
    keep = [i for i, count in enumerate(component_counts) if i and count * size * size >= parameters['minimum_component_area_m2']]
    accepted = np.isin(labels, keep)
    # Small holes amid a supported plane are explicitly uncertain infills, not courtyard fill.
    gaps = ndimage.binary_fill_holes(accepted) & ~accepted
    gap_labels, _ = ndimage.label(gaps)
    gap_counts = np.bincount(gap_labels.ravel())
    infill = [i for i, count in enumerate(gap_counts) if i and count * size * size <= parameters['maximum_enclosed_gap_fill_m2']]
    accepted |= np.isin(gap_labels, infill)
    # Elevations come only from raw planar cells retained in the cleaned shape;
    # morphological infill never invents supporting points.
    support_z = source[raw_accepted.ravel()[codes] & accepted.ravel()[codes], 2].tolist()
    iy_cells, ix_cells = np.where(accepted)
    roof = unary_union([box(xmin + x * size, ymin + y * size, xmin + (x + 1) * size, ymin + (y + 1) * size) for y, x in zip(iy_cells, ix_cells)])
    roof = roof.simplify(parameters['simplification_tolerance_m'], preserve_topology=True)
    if roof.is_empty or not roof.is_valid or roof.area < parameters['minimum_total_upper_area_m2']:
        raise ValueError('No defendable contiguous upper-roof footprint')
    concavity = roof.convex_hull.difference(roof).area
    if concavity < parameters['minimum_concavity_void_area_m2']:
        raise ValueError('Courtyard/open C geometry was lost; do not extrude the property envelope')
    if not support_z:
        raise ValueError('No accepted roof elevations')
    roof_z = float(np.median(support_z))
    result = {'local_ground_median_m': ground_z, 'dominant_plane_mode_m': plane, 'roof_support_median_z_m': roof_z,
              'height_m': round(roof_z - ground_z, 2), 'ground_points': len(ground), 'high_class1_points': len(source),
              'accepted_planar_support_points': len(support_z), 'accepted_cells_before_cleanup': int(raw_accepted.sum()),
              'accepted_cells_after_cleanup': int(accepted.sum()), 'small_gap_infill_cells': int(np.isin(gap_labels, infill).sum()),
              'upper_footprint_area_m2': roof.area, 'concavity_and_hole_void_area_m2': concavity,
              'cell_size_m': size, 'grid_origin_utm_m': [float(xmin), float(ymin)], 'cleanup_parameters': parameters}
    return roof, result, raw_accepted, accepted


def source_footprint(mesh):
    payload = mesh_payload(mesh)
    polygons, offset = [], 0
    for count in payload['counts']:
        if count == 3:
            triangle = Polygon([(payload['points'][i][0], payload['points'][i][1]) for i in payload['indices'][offset:offset + count]])
            if triangle.area > 1e-8:
                polygons.append(triangle)
        offset += count
    return unary_union(polygons)


def polygon_parts(geometry):
    if geometry.is_empty:
        return []
    return list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]


def mesh_geometry(components, roofs_only=False):
    points, counts, indices = [], [], []
    def face(values):
        start = len(points)
        points.extend(values)
        counts.append(len(values))
        indices.extend(range(start, len(points)))
    for geometry, base, top in components:
        for polygon in polygon_parts(geometry):
            polygon = shapely.orient_polygons(polygon, exterior_cw=False)
            triangulation = shapely.constrained_delaunay_triangles(polygon)
            for triangle in triangulation.geoms:
                coords = list(triangle.exterior.coords)[:-1]
                if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(coords, coords[1:] + coords[:1])) < 0:
                    coords.reverse()
                face([(float(x), float(y), top) for x, y in coords])
                if not roofs_only:
                    face([(float(x), float(y), base) for x, y in reversed(coords)])
            if not roofs_only:
                for ring in [polygon.exterior, *polygon.interiors]:
                    coords = list(ring.coords)
                    for a, b in zip(coords, coords[1:]):
                        face([(a[0], a[1], base), (b[0], b[1], base), (b[0], b[1], top), (a[0], a[1], top)])
    return points, counts, indices


def write_mesh(stage, path, components, roofs_only=False):
    points, counts, indices = mesh_geometry(components, roofs_only)
    if not points or sum(counts) != len(indices) or max(indices) >= len(points):
        raise ValueError('Invalid correction mesh topology')
    mesh = UsdGeom.Mesh(stage.OverridePrim(path))
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(indices)
    mesh.CreateSubdivisionSchemeAttr('none')
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateExtentAttr([Gf.Vec3f(*(min(p[i] for p in points) for i in range(3))), Gf.Vec3f(*(max(p[i] for p in points) for i in range(3)))])
    normals, offset = [], 0
    for count in counts:
        face = [np.asarray(points[i]) for i in indices[offset:offset + count]]
        normal = np.cross(face[1] - face[0], face[2] - face[0])
        length = float(np.linalg.norm(normal))
        normals.append(tuple(normal / length) if length else (0, 0, 1))
        offset += count
    mesh.CreateNormalsAttr(normals)
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
    uv = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    uv.Set([(float(points[i][0] / 5), float((points[i][1] if roofs_only else points[i][2]) / 5)) for i in indices])
    mesh.GetPrim().CreateAttribute('primvars:st:indices', Sdf.ValueTypeNames.IntArray, custom=False).Block()
    return mesh


def corrected_height_rows(rows, identifier, values):
    if sum(r['building_id'] == identifier for r in rows) != 1:
        raise ValueError('Expected exactly one Wellesley height row')
    before_others = digest([r for r in rows if r['building_id'] != identifier])
    result = [{**r, **values} if r['building_id'] == identifier else r for r in rows]
    if digest([r for r in result if r['building_id'] != identifier]) != before_others:
        raise ValueError('Unrelated height rows changed')
    return result


def correct(root=ROOT):
    config_path = root / 'config/building_corrections.json'
    config = read(config_path)
    active = read(root / 'data/processed/active.json')
    snapshot = root / active['relative_path']
    records = read(snapshot / 'buildings.json')
    stage = Usd.Stage.Open(str(root / 'scene/college_park.usda'))
    record, source = resolve_target(config, stage, records)
    identifier = record['id']
    cloud_path = root / 'data/heights/pilot_points.npz'
    validate_guard(config, active, record, source, cloud_path)
    unit_check = read(root / 'data/heights/vertical_unit_check.json')
    if not unit_check.get('accepted') or unit_check.get('ept_z_unit') != 'meters':
        raise ValueError('EPT vertical-meter unit validation is not accepted')
    parcels = read(snapshot / 'parcels.json')['features']
    properties = [f for f in parcels if (f['properties'].get('site_address') or '').startswith(config['source_address_prefix'])]
    if len(properties) != 114:
        raise ValueError('Wellesley property group changed; verify whole-entity attribution')
    mask_wgs = unary_union([shape(f['geometry']) for f in properties])
    to_ept = Transformer.from_crs(4326, 3857, always_xy=True)
    mask_ept = shapely.transform(mask_wgs, to_ept.transform, interleaved=False)
    points = np.load(cloud_path)['points']
    b = mask_ept.bounds
    points = points[(points[:, 0] >= b[0]) & (points[:, 0] <= b[2]) & (points[:, 1] >= b[1]) & (points[:, 1] <= b[3])]
    points = points[shapely.contains_xy(mask_ept, points[:, 0], points[:, 1])]
    to_utm = Transformer.from_crs(3857, 32617, always_xy=True)
    points[:, 0], points[:, 1] = to_utm.transform(points[:, 0], points[:, 1])
    roof_utm, evidence, raw_mask, cleaned_mask = planar_roof(points, config['roof_extraction'])
    to_utm_wgs = Transformer.from_crs(4326, 32617, always_xy=True)
    mask_utm = shapely.transform(mask_wgs, to_utm_wgs.transform, interleaved=False)
    evidence['upper_area_before_property_clip_m2'] = roof_utm.area
    roof_utm = roof_utm.intersection(mask_utm)
    evidence['upper_footprint_area_m2'] = roof_utm.area
    evidence['property_mask_clip_applied'] = True
    if roof_utm.is_empty or not roof_utm.is_valid or roof_utm.area < config['roof_extraction']['minimum_total_upper_area_m2']:
        raise ValueError('Property-clipped roof is not defendable')
    if roof_utm.area / mask_utm.area > config['roof_extraction']['maximum_tax_envelope_area_fraction']:
        raise ValueError('Roof would fill too much tax envelope/courtyard')
    if abs(evidence['height_m'] - config['reported_height_m']) > config['roof_extraction']['maximum_reported_height_difference_m']:
        raise ValueError('Derived roof height conflicts with independently reported historical height')
    origin = to_utm_wgs.transform(*config['origin_wgs84'])
    roof_local = shapely.transform(roof_utm, lambda x, y: (x - origin[0], y - origin[1]), interleaved=False)
    old_footprint = source_footprint(UsdGeom.Mesh(source))
    lower_footprint = old_footprint.difference(roof_local)
    heights_path = root / 'data/heights/building_heights.json'
    rows = read(heights_path)
    previous = next(r for r in rows if r['building_id'] == identifier)
    if previous.get('correction_id') != config['correction_id'] and abs(previous['height_m'] - config['expected_previous_height_m']) > .01:
        raise ValueError('Wellesley prior height changed; do not overwrite an unreviewed correction')
    backup_path = root / 'data/heights/wellesley_prior_height_record.json'
    if not backup_path.exists():
        atomic_json(backup_path, previous)
    prior = read(backup_path)
    if prior['building_id'] not in [identifier, config['original_building_id']]:
        raise ValueError('Prior-height backup does not belong to this correction lineage')
    components = [(roof_local, .1, .1 + evidence['height_m'])]
    if not lower_footprint.is_empty:
        components.append((lower_footprint, .1, .1 + prior['height_m']))
    layer_path = root / 'scene/landmark_corrections.usda'
    layer = Usd.Stage.CreateNew(str(layer_path))
    UsdGeom.SetStageMetersPerUnit(layer, 1)
    UsdGeom.SetStageUpAxis(layer, 'Z')
    building = write_mesh(layer, record['usd_path'], components)
    write_mesh(layer, '/World/Roofs/Roof_' + identifier.split('_')[-1], [(g, base, top + .02) for g, base, top in components], roofs_only=True)
    # Height/shape metadata is stronger; official parcel-link data is deliberately untouched.
    building.GetPrim().SetCustomDataByKey('heightMeters', evidence['height_m'])
    building.GetPrim().SetCustomDataByKey('heightQuality', 'historical_lidar_derived')
    building.GetPrim().SetCustomDataByKey('height', {'height_m': evidence['height_m'], 'floors_used': config['reported_stories'],
        'method': 'historical_planar_class1_roof_minus_local_ground_with_documentary_storeys', 'quality': 'historical_lidar_derived',
        'source_snapshot': active['snapshot'], 'source_building_floor': int(previous.get('source_building_floor') or 0),
        'source_parcel_stories': int(previous.get('source_parcel_stories') or 0), 'lidar_roof_points': evidence['accepted_planar_support_points'],
        'roof_elevation_m': evidence['roof_support_median_z_m'], 'nearby_ground_elevation_m': evidence['local_ground_median_m'],
        'review_notes': 'Historical planar upper-roof zone; original unmatched parcel lineage retained; lower components remain unresolved.'})
    building.GetPrim().SetCustomDataByKey('landmarkCorrection', {'id': config['correction_id'], 'name': 'The Wellesley at College Park',
        'reportedStories': config['reported_stories'], 'reportedNominalHeightMeters': config['reported_height_m'],
        'roofHeightMeters': evidence['height_m'], 'roofAreaMeters2': roof_local.area,
        'shapeQuality': 'historical dense planar class1 roof; roof/vegetation separation and stepped shape uncertain',
        'parcelLinkStatus': 'original ambiguous/unmatched lineage preserved', 'sourceSnapshot': active['snapshot']})
    eye = Gf.Vec3d(-110, -95, 85)
    target = Gf.Vec3d(float(roof_local.centroid.x), float(roof_local.centroid.y), evidence['height_m'] * .5)
    camera = UsdGeom.Camera.Define(layer, '/World/Cameras/WellesleyEvidence')
    camera.AddTransformOp().Set(Gf.Matrix4d(1).SetLookAt(eye, target, Gf.Vec3d(0, 0, 1)).GetInverse())
    camera.CreateFocalLengthAttr(32)
    camera.CreateClippingRangeAttr(Gf.Vec2f(.1, 10000))
    layer.GetRootLayer().customLayerData = {'purpose': 'Scoped historical Wellesley upper-roof mass; not tax-polygon extrusion or current survey',
        'correctionId': config['correction_id'], 'sourceSnapshot': active['snapshot'], 'source': config['documentary_reference']['url'],
        'method': 'Dense planar unclassified high surfaces plus classified local ground; source mass retained only outside upper footprint',
        'lowerComponents': 'Original low masses unresolved; not assigned seven storeys'}
    layer.GetRootLayer().Save()
    values = {'height_m': evidence['height_m'], 'floors_used': config['reported_stories'], 'source_snapshot': active['snapshot'], 'method': 'historical_planar_class1_roof_minus_local_ground_with_documentary_storeys',
              'quality': 'historical_lidar_derived', 'correction_id': config['correction_id'],
              'reported_documentary_height_m': config['reported_height_m'], 'documentary_stories': config['reported_stories'],
              'roof_elevation_m': evidence['roof_support_median_z_m'], 'nearby_ground_elevation_m': evidence['local_ground_median_m'],
              'lidar_roof_points': evidence['accepted_planar_support_points'],
              'review_notes': 'Historical class1 planar upper-roof zone, documentary seven-storey/75ft cross-check; shape and lower components need current review. Original parcel link remains ambiguous/unmatched; not a current roof survey.',
              'shape_quality': 'historical_planar_upper_zone_with_unresolved_lower_components'}
    updated = corrected_height_rows(rows, identifier, values)
    atomic_json(heights_path, updated)
    quality_path = root / 'data/heights/height_quality.json'
    quality = read(quality_path)
    quality.update({'source_snapshot':active['snapshot'], 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'height_quality': dict(collections.Counter(r['quality'] for r in updated)),
                    'changed_heights': sum(abs(r['height_m'] - r['previous_height_m']) > .01 for r in updated),
                    'height_range_m': [min(r['height_m'] for r in updated), max(r['height_m'] for r in updated)]})
    quality['landmark_corrections'] = [r for r in quality.get('landmark_corrections', []) if r.get('building_id') != identifier] + [
        {'building_id': identifier, 'correction_id': config['correction_id'], 'quality': values['shape_quality']}]
    atomic_json(quality_path, quality)
    out = root / 'data/heights/wellesley_correction'
    out.mkdir(parents=True, exist_ok=True)
    image = np.full((*raw_mask.shape, 3), 255, dtype=np.uint8)
    image[raw_mask] = [166, 194, 214]
    image[cleaned_mask] = [37, 139, 83]
    Image.fromarray(image[::-1]).resize((raw_mask.shape[1] * 6, raw_mask.shape[0] * 6)).save(out / 'roof_support_mask.png')
    to_wgs = Transformer.from_crs(32617, 4326, always_xy=True)
    atomic_json(out / 'upper_roof.geojson', {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': mapping(shapely.transform(roof_utm, to_wgs.transform, interleaved=False)),
        'properties': {'building_id': identifier, 'quality': values['shape_quality'], 'acquisition': '2018-2019', 'accepted_current_roof': False}}]})
    manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'correction_id': config['correction_id'],
                'configuration_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(), 'source_snapshot': active['snapshot'],
                'documentary_reference': config['documentary_reference'], 'reported_stories': config['reported_stories'],
                'reported_height_m': config['reported_height_m'], 'extraction': evidence, 'old_footprint_area_m2': old_footprint.area,
                'retained_lower_footprint_area_m2': lower_footprint.area, 'tax_envelope_area_m2': mask_utm.area,
                'resolved_building_id': identifier, 'original_building_id': config['original_building_id'],
                'upper_footprint_local_m': mapping(roof_local), 'prior_height_record': prior, 'updated_height_record': next(r for r in updated if r['building_id'] == identifier),
                'unrelated_height_rows_unchanged': True, 'original_base_mesh_unchanged': True, 'original_unmatched_parcel_status_preserved': True,
                'layer': str(layer_path), 'camera': '/World/Cameras/WellesleyEvidence',
                'composition_status': 'Parent must compose landmark layer stronger than building_heights/semantic source layers; this tool does not edit connected assembly.'}
    atomic_json(out / 'manifest.json', manifest)
    print(json.dumps({'building_id': identifier, 'height_m': evidence['height_m'], 'reported_stories': config['reported_stories'],
                      'upper_footprint_area_m2': roof_local.area, 'retained_lower_footprint_area_m2': lower_footprint.area,
                      'tax_envelope_area_m2': mask_utm.area, 'layer': str(layer_path), 'composition_status': manifest['composition_status']}, indent=2))
    return manifest


if __name__ == '__main__':
    correct()
