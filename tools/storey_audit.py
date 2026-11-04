"""Read-only multi-storey/condominium evidence audit; never changes scene heights.

Only public property/building fields are requested. Unit STYS/FLOOR_NO are kept
separate from whole-building storey counts and from raw footprint FLOOR_NUM.
"""
from pathlib import Path
import argparse, collections, datetime, hashlib, json, os, sys, urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
import shapely
from shapely.geometry import shape, box
from shapely.ops import unary_union
from pyproj import Transformer
from pxr import Usd, UsdGeom

PARCEL_URL = 'https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4/query'
SAFE_FIELDS = ['OBJECTID', 'PARCEL', 'SITUS', 'PROP_NAME', 'STYS', 'FLOOR_NO', 'CONDO_FLAG', 'PARENT_ID', 'AYB']


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def positive_integer(value):
    try:
        number = float(value)
        return int(number) if number.is_integer() and 1 <= number <= 80 else None
    except (TypeError, ValueError):
        return None


def evidence_client(params, root=ROOT, live=False):
    encoded = urllib.parse.urlencode(params).encode()
    key = hashlib.sha256(PARCEL_URL.encode() + encoded).hexdigest()
    path = root / 'data/cache/storey_audit' / (key + '.json')
    if path.exists():
        result = read(path)
        return result['payload'], {k: v for k, v in result.items() if k != 'payload'}
    if not live:
        return None, {'url': PARCEL_URL, 'status': 'unknown_offline_cache_miss'}
    request = urllib.request.Request(PARCEL_URL, data=encoded, headers={'User-Agent': 'TWIN-public-storey-audit/1.0'})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('Bounded property evidence response exceeded 8MiB')
    payload = json.loads(raw)
    if payload.get('error'):
        raise ValueError('Official property query failed: ' + str(payload['error']))
    result = {'url': PARCEL_URL, 'method': 'POST (read-only query)', 'parameters': params,
              'retrieved_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'response_sha256': hashlib.sha256(raw).hexdigest(),
              'status': 'observed_official_query', 'payload': payload}
    atomic_json(path, result)
    return payload, {k: v for k, v in result.items() if k != 'payload'}


def public_property_evidence(boundary, root=ROOT, live=False):
    geometry = shape(boundary['geometry'])
    polys = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    rings = [list(poly.exterior.coords) for poly in polys]
    spatial = {'geometry': json.dumps({'rings': rings, 'spatialReference': {'wkid': 4326}}), 'geometryType': 'esriGeometryPolygon',
               'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects'}
    predicate = "STYS >= 2 OR (CONDO_FLAG='C' AND FLOOR_NO NOT IN ('','0','1'))"
    ids_data, receipt = evidence_client({'f': 'json', 'where': predicate, 'returnIdsOnly': 'true', **spatial}, root, live)
    if ids_data is None:
        return [], [receipt]
    ids = sorted(set(ids_data.get('objectIds') or []))
    if len(ids) > 2000:
        raise ValueError('Unexpectedly large Main Street evidence query')
    rows, receipts = [], [receipt]
    for start in range(0, len(ids), 100):
        data, info = evidence_client({'f': 'json', 'objectIds': ','.join(map(str, ids[start:start + 100])),
                                     'outFields': ','.join(SAFE_FIELDS), 'returnGeometry': 'false'}, root, live)
        receipts.append(info)
        if data is None:
            continue
        rows.extend({k: f['attributes'].get(k) for k in SAFE_FIELDS} for f in data.get('features', []))
    observed = {r['OBJECTID'] for r in rows}
    if observed != set(ids):
        raise ValueError('Incomplete Main Street safe property evidence batches')
    return rows, receipts


def parcel_representation(stories, buildings):
    """Do not force a parcel-level story count onto multiple accessories."""
    accepted = [b for b in buildings if b.get('match_method') == 'id_and_geometry']
    if not accepted:
        return 'no_accepted_building_link'
    maximum = max((positive_integer(b.get('floors_used')) or 0) for b in accepted)
    if maximum >= stories:
        return 'represented_by_at_least_one_building'
    if len(accepted) > 1:
        return 'multi_building_parcel_no_matching_storey_evidence'
    if stories - maximum > 1:
        return 'parcel_story_outlier_or_building_floor_conflict'
    return 'single_building_height_record_below_parcel_stories'


def condo_floor_evidence(rows):
    positions = [positive_integer(r.get('FLOOR_NO')) for r in rows]
    return {'property_names': sorted({r['PROP_NAME'] for r in rows if r.get('PROP_NAME')}),
            'record_count': len(rows), 'reported_unit_floor_distribution': dict(collections.Counter(str(r.get('FLOOR_NO')) for r in rows)),
            'highest_reported_unit_floor': max((v for v in positions if v), default=None),
            'parcel_stys_distribution': dict(collections.Counter(str(r.get('STYS')) for r in rows)),
            'whole_building_storey_count': None,
            'interpretation': 'FLOOR_NO is a reported unit floor position, not verified whole-building storey count. Unit STYS must not flatten the condominium.'}


def height_contradictions(row):
    issues = []
    raw_floor = positive_integer(row.get('source_building_floor'))
    used = positive_integer(row.get('floors_used'))
    if raw_floor and used and raw_floor > used:
        issues.append('raw_building_floor_exceeds_floors_used')
    if used and used >= 2 and row.get('height_m', 0) / used < 2.4:
        issues.append('low_height_per_reported_floor_needs_review')
    if row.get('roof_elevation_m') is not None and row.get('nearby_ground_elevation_m') is not None:
        candidate = row['roof_elevation_m'] - row['nearby_ground_elevation_m']
        if candidate > max(row.get('height_m', 0) * 1.8, row.get('height_m', 0) + 4):
            issues.append('rejected_lidar_candidate_much_taller_than_applied_mass')
    return issues


def cloud_property_mask_summary(mask_wgs84, root=ROOT):
    path = root / 'data/heights/pilot_points.npz'
    if mask_wgs84 is None or not path.exists():
        return {'status': 'unknown_no_local_points_or_property_mask'}
    projection = Transformer.from_crs(4326, 3857, always_xy=True)
    mask = shapely.transform(mask_wgs84, projection.transform, interleaved=False)
    points = np.load(path)['points']
    bounds = mask.bounds
    clipped = points[(points[:, 0] >= bounds[0]) & (points[:, 0] <= bounds[2]) & (points[:, 1] >= bounds[1]) & (points[:, 1] <= bounds[3])]
    del points
    clipped = clipped[shapely.contains_xy(mask, clipped[:, 0], clipped[:, 1])]
    ground = clipped[clipped[:, 3] == 2, 2]
    local_ground = float(np.median(ground)) if len(ground) else None
    classes = {}
    for code in sorted(set(clipped[:, 3])):
        values = clipped[clipped[:, 3] == code, 2]
        classes[str(int(code))] = {'count': len(values), 'elevation_percentiles_m': dict(zip(['p0', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99', 'p100'], map(float, np.percentile(values, [0, 10, 25, 50, 75, 90, 95, 99, 100])))),
                                  'above_ground_plus_20m': int((values > local_ground + 20).sum()) if local_ground is not None else None}
    return {'status': 'observed_historical_point_cloud', 'mask_type': 'union of current public parcel geometries, not a verified roof mask',
            'point_count': len(clipped), 'local_class2_ground_median_m': local_ground, 'classes': classes,
            'point_crs': 'EPSG:3857 XY; NAVD88 meters Z',
            'interpretation': 'Class1 is unclassified, not automatically roof. Dense high surfaces can be missed by class6-only roof extraction; spatial roof/vegetation/stepped-component review is required.'}


def audit(root=ROOT, live=False):
    active = read(root / 'data/processed/active.json')
    folder = (root / active['relative_path']).resolve()
    if not folder.is_relative_to((root / 'data/snapshots').resolve()):
        raise ValueError('Invalid snapshot folder')
    parcels = read(folder / 'parcels.json')['features']
    records = read(folder / 'buildings.json')
    heights = {r['building_id']: r for r in read(root / 'data/heights/building_heights.json')}
    raw = read(root / 'data/buildings.geojson')['features']
    raw_by_id = {str(f['properties']['OBJECTID']): f for f in raw}
    boundaries = read(root / 'data/processed/study_boundaries.geojson')['features']
    main = next(f for f in boundaries if f['properties']['scope'] == 'main_street')
    neighborhood = next(f for f in boundaries if f['properties']['scope'] == 'neighborhood')
    main_geom, neighborhood_geom = shape(main['geometry']), shape(neighborhood['geometry'])
    to_meters = Transformer.from_crs(4326, 32617, always_xy=True)
    origin_x, origin_y = to_meters.transform(-81.389, 28.572)
    source = Usd.Stage.Open(str(root / 'scene/college_park.usda'))
    composed = Usd.Stage.Open(str(root / 'scene/college_park_connected.usda'))
    rows, geometry_by_id, queue = [], {}, []
    by_parcel = collections.defaultdict(list)
    for record in records:
        identifier = record['id']
        height = heights.get(identifier, {})
        prim = source.GetPrimAtPath(record['usd_path'])
        if not prim:
            queue.append({'priority': 'P0', 'building_id': identifier, 'reason': 'snapshot_building_missing_from_base_stage'})
            continue
        attributes = prim.GetCustomData()
        parts = [raw_by_id[key] for key in attributes.get('sourceObjectIds', '').split(',') if key in raw_by_id]
        geometry = unary_union([shape(f['geometry']) for f in parts]) if parts else None
        geometry_by_id[identifier] = geometry
        center = geometry.representative_point() if geometry else None
        scope = {'main_street_center': bool(center and main_geom.covers(center)), 'main_street_intersects': bool(geometry and main_geom.intersects(geometry)),
                 'neighborhood_center': bool(center and neighborhood_geom.covers(center))}
        stage_prim = composed.GetPrimAtPath(record['usd_path'])
        points = UsdGeom.Mesh(stage_prim).GetPointsAttr().Get() if stage_prim else None
        span = float(max(p[2] for p in points) - min(p[2] for p in points)) if points else None
        row = {'building_id': identifier, 'usd_path': record['usd_path'], 'parcel_id': record.get('parcel_id'),
               'source_parcel_id': record.get('source_parcel_id'), 'site_address': record.get('site_address'),
               'match_method': record.get('match_method'), 'source_building_number': attributes.get('buildingNumber'),
               'raw_subarea_count': len(parts), 'raw_floor_values': sorted({str(f['properties'].get('FLOOR_NUM')) for f in parts}),
               'raw_subarea_descriptions': sorted({str(f['properties'].get('SUB_DESC')) for f in parts}),
               'floors_used': height.get('floors_used'), 'source_building_floor': height.get('source_building_floor'),
               'source_parcel_stories': height.get('source_parcel_stories'), 'height_m': height.get('height_m'),
               'height_method': height.get('method'), 'height_quality': height.get('quality'), 'height_source_snapshot': height.get('source_snapshot'),
               'composed_mesh_span_m': span, 'scope': scope, 'review_notes': height.get('review_notes'),
               'historical_lidar_candidate_m': height['roof_elevation_m'] - height['nearby_ground_elevation_m'] if height.get('roof_elevation_m') is not None and height.get('nearby_ground_elevation_m') is not None else None}
        row['upper_story_subarea_description_present'] = any('UP' in d.upper() and ('STORY' in d.upper() or 'STRY' in d.upper()) for d in row['raw_subarea_descriptions'])
        rows.append(row)
        if record.get('parcel_id'):
            by_parcel[record['parcel_id']].append(row)
        reasons = height_contradictions(height)
        if row['upper_story_subarea_description_present'] and (positive_integer(row['floors_used']) or 0) < 2:
            reasons.append('upper_story_subarea_label_but_model_uses_one_floor')
        if span is None or height.get('height_m') is None or abs(span - height['height_m']) > .03:
            reasons.append('composed_mesh_height_missing_or_disagrees_with_height_record')
        if height.get('source_snapshot') != active['snapshot']:
            reasons.append('height_snapshot_mismatch')
        if reasons:
            queue.append({'priority': 'P0' if scope['main_street_intersects'] else 'P1', 'building_id': identifier, 'parcel_id': record.get('parcel_id'),
                          'site_address': record.get('site_address'), 'reasons': reasons, 'scope': scope,
                          'height_m': row['height_m'], 'floors_used': row['floors_used'], 'historical_lidar_candidate_m': row['historical_lidar_candidate_m'],
                          'automatic_height_change_allowed': False})
    parcel_reviews = []
    for feature in parcels:
        prop = feature['properties']
        stories = positive_integer(prop.get('stories'))
        if not stories or stories < 2:
            continue
        geom = shape(feature['geometry'])
        if not main_geom.intersects(geom):
            continue
        buildings = by_parcel.get(prop['parcel_id'], [])
        status = parcel_representation(stories, buildings)
        review = {'parcel_id': prop['parcel_id'], 'parcel_feature_id': prop['id'], 'site_address': prop.get('site_address'),
                  'parcel_stories': stories, 'building_ids': [b['building_id'] for b in buildings], 'status': status,
                  'automatic_height_change_allowed': False}
        parcel_reviews.append(review)
        if status != 'represented_by_at_least_one_building':
            queue.append({'priority': 'P0', 'reason': status, **review})
    # Specific named user case: official safe property fields identify the condominium.
    wellesley_data, wellesley_receipt = evidence_client({'f': 'json', 'where': "SITUS LIKE '2305 EDGEWATER DR%'",
        'outFields': ','.join(SAFE_FIELDS), 'returnGeometry': 'false'}, root, live)
    wellesley_rows = [{k: f['attributes'].get(k) for k in SAFE_FIELDS} for f in (wellesley_data or {}).get('features', [])]
    wellesley = condo_floor_evidence(wellesley_rows)
    parcel_candidates = [f for f in parcels if (f['properties'].get('site_address') or '').startswith('2305 EDGEWATER DR')]
    wellesley_geometry = unary_union([shape(f['geometry']) for f in parcel_candidates]) if parcel_candidates else None
    affected = [r for r in rows if geometry_by_id[r['building_id']] is not None and wellesley_geometry is not None and geometry_by_id[r['building_id']].intersection(wellesley_geometry).area > 1e-10]
    wellesley.update({'address_query': '2305 EDGEWATER DR', 'official_query': wellesley_receipt, 'safe_property_rows': wellesley_rows,
                     'intersecting_building_ids': [r['building_id'] for r in affected],
                     'building_records': affected, 'promotion_status': 'review_only_no_links_or_floors_changed'})
    wellesley['historical_cloud_summary'] = cloud_property_mask_summary(wellesley_geometry, root)
    if wellesley['highest_reported_unit_floor'] and affected:
        for b in affected:
            if (b.get('floors_used') or 0) < wellesley['highest_reported_unit_floor']:
                queue.insert(0, {'priority': 'P0', 'reason': 'user_reported_wellesley_condo_whole_building_underrepresentation',
                    'building_id': b['building_id'], 'site_address': '2305 EDGEWATER DR',
                    'source_parcel_id': b['source_parcel_id'], 'current_floors_used': b['floors_used'],
                    'highest_reported_unit_floor': wellesley['highest_reported_unit_floor'], 'current_height_m': b['height_m'],
                    'historical_lidar_candidate_m': b['historical_lidar_candidate_m'],
                    'automatic_height_change_allowed': False, 'note': 'Reported unit floor positions establish a serious missing-storey conflict, not a verified whole-building height or stepped roof model.'})
    live_main_rows, main_receipts = public_property_evidence(main, root, live)
    snapshot_oids = {f['properties']['source_object_id'] for f in parcels}
    unrepresented_live = [r for r in live_main_rows if r['OBJECTID'] not in snapshot_oids]
    for r in unrepresented_live:
        queue.append({'priority': 'P0', 'reason': 'official_main_street_multistorey_property_not_in_current_parcel_snapshot',
                      'parcel_id': r['PARCEL'], 'site_address': r['SITUS'], 'reported_parcel_stories': r['STYS'],
                      'reported_unit_floor': r['FLOOR_NO'], 'automatic_height_change_allowed': False,
                      'note': 'Official boundary intersects source record, but no current extraction row. Scope/acquisition gap needs review before any building-height attribution.'})
    queue.sort(key=lambda r: (r['priority'] != 'P0', -max(r.get('highest_reported_unit_floor', 0), r.get('parcel_stories', 0), r.get('reported_parcel_stories', 0)), r.get('site_address') or '', r.get('building_id') or ''))
    scopes = {}
    for label, predicate in [('all_extracted', lambda r: True), ('main_street_center', lambda r: r['scope']['main_street_center']),
                             ('main_street_intersects', lambda r: r['scope']['main_street_intersects']), ('neighborhood_center', lambda r: r['scope']['neighborhood_center'])]:
        selected = [r for r in rows if predicate(r)]
        scopes[label] = {'building_groups': len(selected), 'floors_used_distribution': dict(collections.Counter(str(r['floors_used']) for r in selected)),
                         'raw_building_floor_2plus': sum((positive_integer(r['source_building_floor']) or 0) >= 2 for r in selected),
                         'upper_story_subarea_label_but_floors_used_lt2': sum(r['upper_story_subarea_description_present'] and (positive_integer(r['floors_used']) or 0) < 2 for r in selected),
                         'modeled_floors_2plus': sum((positive_integer(r['floors_used']) or 0) >= 2 for r in selected)}
    parcel_source = next(source for source in read(folder / 'sources.json') if source['id'] == 'parcels')
    extraction = box(*parcel_source['scope'])
    projected_main = shapely.transform(main_geom, to_meters.transform, interleaved=False)
    projected_inside = shapely.transform(main_geom.intersection(extraction), to_meters.transform, interleaved=False)
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'source_snapshot': active['snapshot'],
              'scopes': scopes, 'official_main_street_boundary': main['properties'],
              'main_street_area_inside_extraction_fraction': projected_inside.area / projected_main.area,
              'main_street_parcel_story_reviews': parcel_reviews,
              'main_street_property_evidence': {'rows': live_main_rows, 'receipts': main_receipts, 'outside_current_snapshot_rows': unrepresented_live},
              'wellesley': wellesley, 'buildings': rows, 'exception_count': len(queue),
              'scene_sublayers_on_disk': list(composed.GetRootLayer().subLayerPaths),
              'runtime_status': 'Disk composition checked. Running Omniverse stage/UI reload state cannot be established by this audit.',
              'limits': ['No spatial-only or condominium link is promoted.', 'FLOOR_NUM, parcel STYS and unit FLOOR_NO have different scopes.',
                         'Generic ground-level facade detail does not show upper-floor windows even where mass height is correct.',
                         'Historical LiDAR aggregation can follow podium roofs and does not automatically establish tallest stepped-roof height.',
                         'No floors, source snapshot, USD layers or public API are modified.']}
    atomic_json(root / 'data/heights/storey_audit.json', report)
    atomic_json(root / 'data/heights/storey_exception_queue.json', queue)
    print(json.dumps({'scopes': scopes, 'parcel_review_statuses': dict(collections.Counter(r['status'] for r in parcel_reviews)),
                      'exceptions': len(queue), 'wellesley_highest_unit_floor': wellesley['highest_reported_unit_floor'],
                      'wellesley_buildings': wellesley['intersecting_building_ids'], 'main_street_source_rows_outside_snapshot': len(unrepresented_live)}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    audit(live=args.live)
