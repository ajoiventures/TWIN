"""Derive a separate Edgewater review scope from cached City GIS inputs."""

import hashlib
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))

from pyproj import Transformer
from shapely import line_merge, transform, union_all
from shapely.geometry import Point, box, mapping, shape

OUT = 'data/processed/edgewater_focus_corridor.json'
SCHEMA = 'twin.edgewater-focus-corridor/1'
STREET_NAME = 'EDGEWATER DR'


def derive(root):
    dependencies = {}

    def read(relative_path):
        content = (root / relative_path).read_bytes()
        dependencies[relative_path] = hashlib.sha256(content).hexdigest()
        return json.loads(content)

    active = read('data/processed/active.json')
    folder = (root / active['relative_path']).resolve()
    if folder.parent != (root / 'data/snapshots').resolve() or folder.name != active['snapshot']:
        raise ValueError('Invalid active snapshot directory')
    prefix = folder.relative_to(root).as_posix()
    streets = read(f'{prefix}/streets.json')
    source = next(row for row in read(f'{prefix}/sources.json') if row['id'] == 'streets')
    metadata = read(f'{prefix}/streets_metadata.json')
    registry = read('data/processed/study_boundaries.geojson')
    pilot = read('data/processed/pilot.json')
    if {registry['provenance']['source_snapshot'], pilot['source_snapshot']} != {active['snapshot']}:
        raise ValueError('Boundary or pilot context belongs to a different snapshot')
    if source['geometry_crs'] != 'EPSG:4326' or source['publisher'] != 'City of Orlando':
        raise ValueError('Unexpected street source or CRS')
    main_feature = next(feature for feature in registry['features'] if feature['id'] == 'main_street')
    main_wgs84 = shape(main_feature['geometry'])
    if not main_wgs84.is_valid or main_wgs84.is_empty or not box(*source['scope']).covers(main_wgs84):
        raise ValueError('Street extraction must cover the entire valid Main Street boundary')

    to_m = Transformer.from_crs(4326, 32617, always_xy=True).transform
    to_wgs84 = Transformer.from_crs(32617, 4326, always_xy=True).transform
    main = transform(main_wgs84, to_m, interleaved=False)
    members = []
    segments = []
    for feature in streets['features']:
        properties = feature['properties']
        if properties['FullStreetName'] != STREET_NAME:
            continue
        segment = transform(shape(feature['geometry']), to_m, interleaved=False).intersection(main)
        if segment.length <= 0:
            continue
        if segment.geom_type not in ('LineString', 'MultiLineString'):
            raise ValueError('Unexpected clipped centerline geometry')
        segments.append(segment)
        members.append({key: properties[key] for key in ('OBJECTID', 'GlobalID', 'CenterlineID')})

    if len({member['OBJECTID'] for member in members}) != len(members):
        raise ValueError('Duplicate street source identity')
    if len({member['CenterlineID'] for member in members}) != 1:
        raise ValueError('Review disconnected or ambiguous Edgewater source identities')
    centerline = line_merge(union_all(segments))
    if centerline.geom_type != 'LineString' or centerline.is_empty or not centerline.is_simple:
        raise ValueError('Edgewater must form one unbranched centerline')
    if any(Point(endpoint).distance(main.boundary) > 0.000001 for endpoint in (centerline.coords[0], centerline.coords[-1])):
        raise ValueError('Both Edgewater endpoints must reach the Main Street boundary')
    if centerline.coords[0][1] > centerline.coords[-1][1]:
        centerline = centerline.reverse()

    radius = pilot['context_buffer_m']
    if radius != 60:
        raise ValueError('Review a change to the frozen 60 m project context rule')
    corridor = centerline.buffer(radius, cap_style='flat').intersection(main)
    if not corridor.is_valid or corridor.is_empty or corridor.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Invalid Edgewater focus corridor')

    shared = {
        'status': 'project_review_scope',
        'source_snapshot': active['snapshot'],
        'snapshot_built_utc': source['snapshot_built_utc'],
        'source_observation_date': None,
        'effective_date': None,
        'publisher': source['publisher'],
        'source_url': source['api_url'],
        'source_item_id': metadata['serviceItemId'],
        'source_layer_last_edit_unix_ms': source['source_updated'],
        'source_request_retrieval_range_utc': source['request_retrieval_range_utc'],
        'main_street_source_url': main_feature['properties']['source_url'],
        'main_street_source_item_id': main_feature['properties']['source_item_id'],
        'main_street_source_feature_ids': main_feature['properties']['source_feature_ids'],
        'main_street_layer_last_edit_unix_ms': main_feature['properties']['layer_last_edit_unix_ms'],
        'main_street_effective_date': main_feature['properties']['effective_date'],
        'source_terms': source['license_note'],
    }
    features = [
        {'type': 'Feature', 'id': 'edgewater_focus_corridor',
         'properties': {**shared, 'name': 'Edgewater Drive focus corridor', 'context_buffer_m': radius,
                        'rule_reference': pilot['pilot_id'], 'rule_reference_date': pilot['reference_date'],
                        'role': 'project review area'},
         'geometry': mapping(transform(corridor, to_wgs84, interleaved=False))},
        {'type': 'Feature', 'id': 'edgewater_focus_centerline',
         'properties': {**shared, 'name': 'Edgewater Drive centerline within Main Street',
                        'role': 'City centerline clipped to Main Street'},
         'geometry': mapping(transform(centerline, to_wgs84, interleaved=False))},
    ]
    packet = {
        'type': 'FeatureCollection', 'schema': SCHEMA, 'source_snapshot': active['snapshot'],
        'geometry_crs': 'EPSG:4326', 'measurement_crs': 'EPSG:32617',
        'features': features, 'dependencies': dependencies,
        'city_centerline_members': sorted(members, key=lambda member: member['OBJECTID']),
        'metrics': {'centerline_length_m': round(centerline.length, 3),
                    'corridor_area_m2': round(corridor.area, 3),
                    'city_segment_count': len(members), 'context_buffer_m': radius},
    }
    for relative_path, digest in dependencies.items():
        if hashlib.sha256((root / relative_path).read_bytes()).hexdigest() != digest:
            raise ValueError('Focus corridor input changed during derivation')
    return json.loads(json.dumps(packet, allow_nan=False))


def validate(root=ROOT):
    root = Path(root).resolve()
    packet = json.loads((root / OUT).read_text(encoding='utf-8'))
    if packet != derive(root):
        raise ValueError('Focus corridor differs from its current cached inputs')
    return packet


def build(root=ROOT):
    root = Path(root).resolve()
    packet = derive(root)
    destination = root / OUT
    stream = NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent, delete=False)
    candidate = Path(stream.name)
    try:
        with stream:
            json.dump(packet, stream, ensure_ascii=False, indent=2)
        candidate.replace(destination)
    finally:
        candidate.unlink(missing_ok=True)
    return validate(root)


if __name__ == '__main__':
    print(json.dumps(build()['metrics'], indent=2))
