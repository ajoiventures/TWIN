"""Screen cached OSM sidewalk coverage along the City Edgewater review spine."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely import transform
from shapely.geometry import LineString, shape
from shapely.strtree import STRtree


def review(corridor_path, osm_path):
    corridor_bytes = corridor_path.read_bytes()
    osm_bytes = osm_path.read_bytes()
    packet = json.loads(corridor_bytes)
    features = {feature['id']: shape(feature['geometry']) for feature in packet['features']}
    project = Transformer.from_crs(4326, 32617, always_xy=True).transform
    unproject = Transformer.from_crs(32617, 4326, always_xy=True).transform
    spine = transform(features['edgewater_focus_centerline'], project, interleaved=False)
    scope = transform(features['edgewater_focus_corridor'], project, interleaved=False)
    step, reach, minimum_parallel = 5, 25, math.cos(math.pi / 4)
    pedestrian = []
    crossings = []
    for way in json.loads(osm_bytes)['elements']:
        tags = way.get('tags', {})
        if way['type'] != 'way' or tags.get('highway') != 'footway':
            continue
        kind = tags.get('footway')
        coords = [(node['lon'], node['lat']) for node in way.get('geometry', ())]
        if kind not in ('sidewalk', 'crossing') or len(coords) < 2:
            continue
        line = transform(LineString(coords), project, interleaved=False)
        if not line.intersects(scope):
            continue
        if kind == 'crossing':
            point = line.intersection(spine)
            if not point.is_empty:
                crossings.append({'osm_way': way['id'], 'station_m': round(spine.project(point.centroid), 2)})
        else:
            pedestrian.append((way['id'], line))
    if not pedestrian:
        raise ValueError('No tagged sidewalk geometry intersects the review corridor')

    tree = STRtree([line for _, line in pedestrian])
    matched_ways = set()
    runs = {'west': [], 'east': []}
    for start in range(0, math.ceil(spine.length), step):
        end = min(start + step, spine.length)
        station = (start + end) / 2
        center = spine.interpolate(station)
        a, b = spine.interpolate(station - 1), spine.interpolate(station + 1)
        length = a.distance(b)
        dx, dy = (b.x - a.x) / length, (b.y - a.y) / length
        for side, sign in [('west', 1), ('east', -1)]:
            probe = LineString([center, (center.x - sign * dy * reach, center.y + sign * dx * reach)])
            candidates = []
            for index in tree.query(probe, predicate='intersects'):
                way, line = pedestrian[index]
                intersection = line.intersection(probe).intersection(scope)
                if intersection.is_empty:
                    continue
                for point in getattr(intersection, 'geoms', [intersection]):
                    if point.geom_type != 'Point':
                        continue
                    along = line.project(point)
                    p, q = line.interpolate(max(0, along - 1)), line.interpolate(along + 1)
                    delta = p.distance(q)
                    if delta and abs(dx * (q.x - p.x) + dy * (q.y - p.y)) / delta >= minimum_parallel:
                        candidates.append((center.distance(point), way))
            way = min(candidates)[1] if candidates else None
            if way is not None:
                matched_ways.add(way)
            if runs[side] and runs[side][-1]['osm_way'] == way:
                runs[side][-1]['end_m'] = end
            else:
                runs[side].append({'start_m': start, 'end_m': end, 'osm_way': way})

    summary = {}
    for side, rows in runs.items():
        missing = [r for r in rows if r['osm_way'] is None]
        for row in rows:
            row['start_lonlat'] = list(unproject(*spine.interpolate(row['start_m']).coords[0]))
            row['end_lonlat'] = list(unproject(*spine.interpolate(row['end_m']).coords[0]))
        summary[side] = {'unmapped_station_m': round(sum(r['end_m'] - r['start_m'] for r in missing), 2),
                         'unmapped_runs': len(missing)}
    return {'source_snapshot': packet['source_snapshot'], 'corridor_sha256': hashlib.sha256(corridor_bytes).hexdigest(),
            'osm_sha256': hashlib.sha256(osm_bytes).hexdigest(), 'spine_length_m': spine.length,
            'station_step_m': step, 'maximum_offset_m': reach, 'maximum_heading_difference_degrees': 45,
            'sidewalk_way_count_in_scope': len(pedestrian), 'matched_way_count': len(matched_ways),
            'osm_crossing_ways_intersecting_spine': sorted(crossings, key=lambda r: r['station_m']),
            'summary': summary, 'station_runs': runs,
            'interpretation': 'Missing station matches flag source review. Width, condition, crossings and physical continuity remain unverified.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corridor', required=True, type=Path)
    parser.add_argument('--osm', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = review(args.corridor, args.osm)
    with args.output.open('x', encoding='utf-8') as output:
        output.write(json.dumps(result, indent=2) + '\n')
