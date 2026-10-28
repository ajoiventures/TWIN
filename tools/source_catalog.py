"""Bounded official-source probes; unknown coverage never becomes zero coverage.

Reads public allowlisted snapshot fields only. No BOOMS paths or source mutations.
"""
from pathlib import Path
import argparse, concurrent.futures, datetime, hashlib, html, json, os, re, struct, urllib.parse, urllib.request, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


class ProbeClient:
    def __init__(self, cache, offline=False, refresh=False, timeout=15, opener=None):
        self.cache = Path(cache)
        self.offline, self.refresh, self.timeout = offline, refresh, timeout
        self.opener = opener or urllib.request.urlopen

    def get(self, url, params=None):
        target = url + ('?' + urllib.parse.urlencode(params) if params else '')
        key = hashlib.sha256(target.encode()).hexdigest()
        path = self.cache / (key + '.json')
        if path.exists() and (self.offline or not self.refresh):
            cached = json.loads(path.read_text(encoding='utf-8'))
            return {**cached, 'read_mode': 'cached'}
        if self.offline:
            return {'url': target, 'status': 'unknown', 'error': 'offline cache miss', 'read_mode': 'offline', 'checked_utc': None}
        stamp = utcnow()
        try:
            request = urllib.request.Request(target, headers={'User-Agent': 'TWIN-source-catalog/1.0', 'Accept': 'application/json,text/html'})
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Response exceeded bounded metadata limit')
                text = raw.decode('utf-8', errors='replace')
                content_type = response.headers.get('Content-Type', '')
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
                result = {'url': target, 'status': 'reachable', 'http_status': response.status,
                          'content_type': content_type, 'checked_utc': stamp,
                          'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                          'final_url': response.geturl(), 'payload': payload}
                if payload is None and ('xml' in content_type or text.lstrip().startswith('<?xml')):
                    result['xml_text'] = text
                if isinstance(payload, dict) and payload.get('error'):
                    result.update(status='service_error', error=payload['error'])
        except Exception as exc:
            result = {'url': target, 'status': 'metadata_unreadable' if isinstance(exc, ValueError) else 'unreachable', 'checked_utc': stamp,
                      'error': type(exc).__name__ + ': ' + str(exc)}
        atomic_json(path, result)
        return {**result, 'read_mode': 'live'}

    def binary_range(self, url, start=0, length=1024):
        if not 0 < length <= 65536 or start < 0:
            raise ValueError('Invalid bounded byte range')
        key = hashlib.sha256((url + f'#range={start}:{length}').encode()).hexdigest()
        path = self.cache / (key + '.json')
        if path.exists() and (self.offline or not self.refresh):
            return {**json.loads(path.read_text(encoding='utf-8')), 'read_mode': 'cached'}
        if self.offline:
            return {'url': url, 'status': 'unknown', 'error': 'offline range cache miss'}
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'TWIN-source-catalog/1.0', 'Range': f'bytes={start}-{start + length - 1}'})
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(length)
                result = {'url': url, 'status': 'reachable', 'checked_utc': utcnow(), 'http_status': response.status,
                          'content_range': response.headers.get('Content-Range'), 'content_type': response.headers.get('Content-Type'),
                          'requested_start': start, 'range_honored': response.status == 206,
                          'bytes_read': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'data_hex': raw.hex()}
        except Exception as exc:
            result = {'url': url, 'status': 'unreachable', 'checked_utc': utcnow(), 'error': type(exc).__name__ + ': ' + str(exc)}
        atomic_json(path, result)
        return {**result, 'read_mode': 'live'}


def geo_bbox(geometry):
    def points(value):
        if value and isinstance(value[0], (int, float)):
            yield value
        else:
            for part in value:
                yield from points(part)
    values = list(points(geometry.get('coordinates', [])))
    if not values:
        return None
    return [min(p[0] for p in values), min(p[1] for p in values), max(p[0] for p in values), max(p[1] for p in values)]


def intersects(a, b):
    return bool(a and b and a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1])


def normalize_use_restrictions(item, evidence_url):
    exact = ' '.join(html.unescape(re.sub('<[^>]+>', ' ', item.get('licenseInfo') or '')).split())
    restricted = all(term in exact.lower() for term in ['machine learning', 'five years', 'ecopia', 'written consent'])
    return {'ml_use_allowed': False if restricted else None,
            'status': 'exclude_from_ai_use_unless_permission_or_expiry_established' if restricted else 'terms_not_established',
            'restriction_text': exact or None, 'restriction_evidence_url': evidence_url,
            'restricted_purposes': ['creating', 'training', 'improving', 'modifying', 'validating', 'testing', 'evaluating machine learning algorithms'] if restricted else [],
            'duration_years': 5 if restricted else None,
            'original_product_creation_date': None, 'restriction_expiry_date': None,
            'arcgis_item_created_epoch_ms': item.get('created'),
            'item_creation_is_not_product_creation': True,
            'written_consent_evidence': None,
            'note': 'Imagery title years, item creation and modification timestamps do not establish the license period start or expiry. No consent has been supplied; no consent request is sent.'}


def iso_summary(xml_text):
    ns = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco'}
    root = ET.fromstring(xml_text)
    def value(path):
        e = root.find(path, ns)
        return ''.join(e.itertext()).strip() if e is not None else None
    bbox = [value('.//gmd:' + name + '/gco:Decimal') for name in ['westBoundLongitude', 'southBoundLatitude', 'eastBoundLongitude', 'northBoundLatitude']]
    return {'bbox_wgs84': [float(v) for v in bbox] if all(v is not None for v in bbox) else None,
            'constraints': [' '.join(' '.join(e.itertext()).split()) for e in root.findall('.//gmd:MD_LegalConstraints', ns)],
            'source_resolution': value('.//gmd:MD_Resolution'),
            'metadata_date': value('.//gmd:dateStamp'),
            'online_resources': [''.join(e.itertext()).strip() for e in root.findall('.//gmd:URL', ns)]}


def fgdc_summary(xml_text):
    root = ET.fromstring(xml_text)
    def text(name):
        return root.findtext('.//' + name)
    values = [text(n) for n in ['westbc', 'southbc', 'eastbc', 'northbc']]
    return {'bbox_wgs84': [float(v) for v in values] if all(v for v in values) else None,
            'acquisition_start': text('begdate'), 'acquisition_end': text('enddate'), 'publication_date': text('pubdate'),
            'horizontal_crs': text('mapprojn'), 'horizontal_unit': 'US survey foot' if '(ftUS)' in (text('mapprojn') or '') else None,
            'vertical_datum': text('altdatum'), 'vertical_unit': text('altunits'),
            'access_constraints': text('accconst'), 'use_constraints': text('useconst'),
            'raster_columns': text('colcount'), 'raster_rows': text('rowcount')}


def tiff_pixel_scale(url, client):
    header = client.binary_range(url, 0, 1024)
    raw = bytes.fromhex(header.get('data_hex', ''))
    if len(raw) < 8 or raw[:2] not in [b'II', b'MM']:
        return {'status': 'unknown', 'note': 'No readable TIFF header', 'access_probe': {k: v for k, v in header.items() if k != 'data_hex'}}
    order = '<' if raw[:2] == b'II' else '>'
    version = struct.unpack(order + 'H', raw[2:4])[0]
    if version != 42:
        return {'status': 'header_only', 'tiff_version': version, 'note': 'BigTIFF binary access verified; pixel resolution remains metadata-derived', 'access_probe': {k: v for k, v in header.items() if k != 'data_hex'}}
    offset = struct.unpack(order + 'I', raw[4:8])[0]
    if offset + 2 <= len(raw):
        block, base = raw, 0
    else:
        response = client.binary_range(url, offset, 4096)
        if not response.get('range_honored'):
            return {'status': 'unknown', 'note': 'Server did not honor TIFF metadata range'}
        block, base = bytes.fromhex(response.get('data_hex', '')), offset
    position = offset - base
    if position + 2 > len(block):
        return {'status': 'unknown', 'note': 'Truncated TIFF directory'}
    count = struct.unpack(order + 'H', block[position:position + 2])[0]
    for index in range(min(count, 200)):
        start = position + 2 + index * 12
        if start + 12 > len(block):
            break
        tag, kind, amount, value = struct.unpack(order + 'HHII', block[start:start + 12])
        if tag == 33550 and kind == 12 and amount == 3:
            if value >= base and value + 24 <= base + len(block):
                sample = block[value - base:value - base + 24]
            else:
                response = client.binary_range(url, value, 24)
                sample = bytes.fromhex(response.get('data_hex', '')) if response.get('range_honored') else b''
            if len(sample) == 24:
                return {'status': 'observed_geotiff_tag', 'pixel_scale_source_units': list(struct.unpack(order + 'ddd', sample)),
                        'access_probe': {k: v for k, v in header.items() if k != 'data_hex'}}
    return {'status': 'unknown', 'note': 'Pixel scale not found in bounded TIFF metadata read'}


def acquisition_groups(sources):
    groups = {}
    for source in sources:
        # Never merge unknown acquisitions merely because publishers or dates match.
        identity = source.get('acquisition_id')
        if identity and source.get('acquisition_evidence'):
            groups.setdefault(identity, []).append(source['id'])
    return [{'acquisition_id': key, 'source_ids': ids,
             'independent_measurement_count': 1,
             'note': 'Explicit shared acquisition identity; portal copies are not independent evidence'}
            for key, ids in sorted(groups.items())]


def snapshot_evidence(source, root):
    table = source.get('snapshot_table')
    if not table:
        return None
    pointer = root / 'data/processed/active.json'
    if not pointer.exists():
        return None
    active = json.loads(pointer.read_text(encoding='utf-8'))
    folder = (root / active['relative_path']).resolve()
    if not folder.is_relative_to((root / 'data/snapshots').resolve()):
        raise ValueError('Snapshot path escaped data/snapshots')
    table_path = folder / (table + '.json')
    if not table_path.exists():
        return None
    data = json.loads(table_path.read_text(encoding='utf-8'))
    rows = [f['properties'] for f in data['features']] if isinstance(data, dict) and data.get('type') == 'FeatureCollection' else data
    if not isinstance(rows, list):
        raise ValueError('Snapshot table must contain rows')
    safe = source.get('safe_fields', [])
    manifest_path = folder / 'sources.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
    metadata = next((s for s in manifest if s['id'] == source.get('snapshot_source_id')), {})
    return {'state': 'observed_local_snapshot', 'snapshot': active['snapshot'],
            'row_count': len(rows), 'scope': metadata.get('scope'),
            'geometry_crs': metadata.get('geometry_crs'),
            'source_updated': metadata.get('source_updated'),
            'snapshot_reported_retrieved_utc': metadata.get('retrieved_utc'),
            'retrieval_caveat': 'Legacy snapshot timestamp can be build time for cached responses; original network fetch time is not established.',
            'sha256': hashlib.sha256(table_path.read_bytes()).hexdigest(),
            'safe_fields': safe, 'first_five_rows': [{k: row[k] for k in safe if k in row} for row in rows[:5]],
            'note': 'Rows observed in prior clipped snapshot; not a claim of current complete source coverage'}


def probe_source(source, bbox, client, root=ROOT):
    kind = source['kind']
    params = {'f': 'json'} if kind in ['arcgis', 'arcgis_index', 'image_service'] else None
    if kind == 'tnm_catalog':
        params = {'datasets': 'Lidar Point Cloud (LPC)', 'bbox': ','.join(map(str, bbox)), 'outputFormat': 'JSON', 'max': 20}
    if kind == 'download_probe':
        fetched = client.binary_range(source['url'])
        data = bytes.fromhex(fetched.pop('data_hex', ''))
        payload = None
    else:
        fetched = client.get(source['url'], params)
        payload = fetched.pop('payload', None)
    xml_text = fetched.pop('xml_text', None)
    result = {**source, 'probe': fetched, 'coverage': {'state': 'unknown', 'feature_count': None},
              'dates': {'acquisition_interval': source.get('acquisition_interval'), 'source_updated': None, 'source_updated_unit': None},
              'spatial_reference': {'horizontal_crs': source.get('horizontal_crs'), 'horizontal_unit': source.get('horizontal_unit'),
                                    'vertical_datum': source.get('vertical_datum'), 'vertical_unit': source.get('vertical_unit')},
              'access_note': 'Reachable HTML/metadata does not establish downloadable geometry, permission, or College Park coverage'}
    if kind == 'download_probe':
        result['binary_signature'] = 'ZIP' if data[:4] in [b'PK\x03\x04', b'PK\x05\x06'] else 'unknown'
        result['disposition'] = 'pending corridor coverage, fields, units and source-date validation in #15; bounded access probe only'
    if isinstance(payload, dict) and fetched['status'] == 'reachable':
        if kind in ['arcgis', 'arcgis_index'] and 'fields' in payload and 'type' in payload:
            result['fields'] = [{k: f.get(k) for k in ['name', 'type', 'alias']} for f in payload['fields']]
            result['spatial_reference']['source_spatial_reference'] = payload.get('extent', {}).get('spatialReference')
            result['dates']['source_updated'] = payload.get('editingInfo', {}).get('lastEditDate')
            result['dates']['source_updated_unit'] = 'unix_epoch_milliseconds'
            result['source_copyright_text'] = payload.get('copyrightText')
            count = client.get(source['url'] + '/query', {'f': 'json', 'where': '1=1', 'geometry': ','.join(map(str, bbox)),
                'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects', 'returnCountOnly': 'true'})
            count_data = count.pop('payload', None)
            result['coverage_probe'] = count
            if isinstance(count_data, dict) and isinstance(count_data.get('count'), int) and count['status'] == 'reachable':
                result['coverage'] = {'state': 'observed_bbox_query', 'feature_count': count_data['count'], 'bbox_wgs84': bbox,
                                      'note': 'Intersects bounding rectangle; not official district membership'}
            if kind == 'arcgis_index':
                sample = client.get(source['url'] + '/query', {'f': 'geojson', 'where': '1=1', 'geometry': ','.join(map(str, bbox)),
                    'geometryType': 'esriGeometryEnvelope', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects',
                    'outSR': 4326, 'outFields': ','.join(source['safe_fields']), 'returnGeometry': 'true', 'resultRecordCount': 200})
                sample_data = sample.pop('payload', None)
                result['tile_query_probe'] = sample
                if sample['status'] == 'reachable' and isinstance(sample_data, dict) and isinstance(sample_data.get('features'), list):
                    features = sample_data['features']
                    result['tile_records'] = [{'id': f.get('id'), 'bbox_wgs84': geo_bbox(f.get('geometry', {})),
                                              'attributes': {k: v for k, v in f.get('properties', {}).items() if k in source['safe_fields']}} for f in features]
                    result['tile_query_complete'] = not sample_data.get('exceededTransferLimit', False) and len(features) == result['coverage'].get('feature_count')
                    result['first_five_rows'] = [f['attributes'] for f in result['tile_records'][:5]]
                    if features:
                        props = result['tile_records'][0]['attributes']
                        metadata = client.get(props['DEM_Metadata'])
                        metadata.pop('payload', None)
                        text = metadata.pop('xml_text', None)
                        result['tile_dem_metadata_probe'] = metadata
                        if text:
                            result['representative_dem_metadata'] = fgdc_summary(text)
                        result['representative_dem_resolution'] = tiff_pixel_scale(props['DownloadDEM'], client)
        elif kind == 'tnm_catalog' and isinstance(payload.get('items'), list):
            result['coverage'] = {'state': 'catalog_intersection_candidates', 'feature_count': None, 'product_total': payload.get('total'),
                                  'returned_products': len(payload['items']), 'bbox_wgs84': bbox,
                                  'note': 'Catalog candidates, not verified complete point/ground coverage; pagination may remain'}
            result['products'] = [{k: row.get(k) for k in ['sourceId', 'title', 'publicationDate', 'lastUpdated', 'metaUrl', 'downloadURL']} for row in payload['items']]
        elif kind == 'ept' and 'bounds' in payload:
            result['metadata_summary'] = {k: payload.get(k) for k in ['bounds', 'boundsConforming', 'points', 'srs', 'dataType', 'span']}
        elif kind == 'socrata_metadata' and 'columns' in payload:
            result['fields'] = [{k: c.get(k) for k in ['fieldName', 'name', 'dataTypeName']} for c in payload['columns']]
            result['dates']['source_updated'] = payload.get('rowsUpdatedAt')
            result['dates']['source_updated_unit'] = 'unix_epoch_seconds'
            result['source_license_id'] = payload.get('licenseId')
        elif kind == 'image_service' and payload.get('extent'):
            result['metadata_summary'] = {k: payload.get(k) for k in ['extent', 'pixelSizeX', 'pixelSizeY', 'copyrightText', 'serviceDataType']}
            sample = client.get(source['url'] + '/getSamples', {'f': 'json', 'geometry': json.dumps({'x': -81.389, 'y': 28.572, 'spatialReference': {'wkid': 4326}}),
                'geometryType': 'esriGeometryPoint', 'returnFirstValueOnly': 'true'})
            samples = sample.pop('payload', None)
            result['pixel_sample_probe'] = sample
            result['pilot_pixel_samples'] = samples.get('samples', []) if isinstance(samples, dict) else []
    if xml_text:
        try:
            result['metadata_summary'] = iso_summary(xml_text)
        except (ET.ParseError, ValueError) as exc:
            result['metadata_error'] = str(exc)
        if source.get('download_url'):
            result['binary_access'] = tiff_pixel_scale(source['download_url'], client)
    if source.get('item_metadata_url'):
        item = client.get(source['item_metadata_url'])
        item_data = item.pop('payload', None)
        result['item_metadata_probe'] = item
        if isinstance(item_data, dict) and item['status'] == 'reachable':
            result['item_metadata'] = {k: item_data.get(k) for k in ['id', 'owner', 'orgId', 'title', 'licenseInfo', 'accessInformation', 'created', 'modified']}
            result['use_restrictions'] = normalize_use_restrictions(item_data, source['item_metadata_url'])
    try:
        evidence = snapshot_evidence(source, root)
        if evidence:
            result['local_snapshot'] = evidence
    except (ValueError, KeyError, OSError) as exc:
        result['local_snapshot_error'] = type(exc).__name__ + ': ' + str(exc)
    if source.get('local_ept_sample'):
        path = root / source['local_ept_sample']
        if path.exists():
            try:
                evidence = json.loads(path.read_text(encoding='utf-8'))
                result['local_sample'] = {k: evidence.get(k) for k in ['pilot_bbox_wgs84', 'clipped_points', 'classifications', 'max_depth']}
                result['local_sample']['note'] = 'Historical sampled pilot; not full study coverage'
            except (ValueError, OSError) as exc:
                result['local_sample_error'] = str(exc)
    return result


def run_discoveries(configuration, client):
    output = []
    for discovery in configuration.get('discovery_queries', []):
        params = {'f': 'json', 'num': discovery.get('limit', 30), 'q': discovery['query'],
                  'bbox': ','.join(map(str, configuration['study_bbox_wgs84']))}
        response = client.get('https://www.arcgis.com/sharing/rest/search', params)
        data = response.pop('payload', None)
        result = {**discovery, 'probe': response, 'bbox_wgs84': configuration['study_bbox_wgs84'],
                  'total': None, 'results': [], 'bounded_search_complete': False,
                  'interpretation': 'This publisher/query/bbox search does not establish absence across other publishers, aliases or unpublished datasets.'}
        if response.get('status') == 'reachable' and isinstance(data, dict) and isinstance(data.get('results'), list):
            result['total'] = data.get('total')
            result['next_start'] = data.get('nextStart')
            result['bounded_search_complete'] = data.get('nextStart') == -1 and len(data['results']) == data.get('total')
            for item in data['results']:
                candidate = {k: item.get(k) for k in ['id', 'title', 'owner', 'type', 'url', 'extent', 'created', 'modified']}
                candidate['disposition'] = 'not selected; product access, local pixels, acquisition and terms unverified; review imagery in #20' if discovery['domain'] == 'imagery' else 'pending dataset/corridor validation in #15'
                if item['id'] == '5288fc04c2ed4c3ba86bb2469b3d1acf':
                    candidate['disposition'] = 'excluded from AI candidate use: explicit five-year Ecopia ML restriction; product creation/expiry not established; pilot pixel NoData'
                result['results'].append(candidate)
            if not data['results']:
                result['outcome'] = 'no suitable result in this exact bounded search; no general no-data claim'
            else:
                result['outcome'] = 'specific candidates cataloged; no new imagery/transport source activated'
        else:
            result['outcome'] = 'search access unresolved; coverage remains unknown'
        output.append(result)
    return output


def select_candidates(rows, bbox):
    lookup = {r['id']: r for r in rows}
    candidates = []
    index = lookup.get('florida_lidar_tile_index', {})
    tiles = index.get('tile_records', [])
    resolution = index.get('representative_dem_resolution', {})
    observed_scale = resolution.get('pixel_scale_source_units')
    ready = bool(tiles and index.get('tile_query_complete') and observed_scale and index.get('representative_dem_metadata', {}).get('horizontal_unit') == 'US survey foot')
    candidates.append({'id': 'florida_original_dem', 'rank': 1, 'source_id': 'florida_lidar_tile_index',
        'decision': 'accept_for_historical_terrain_preparation' if ready else 'pending',
        'reason': 'Specific intersecting original DEM tiles; representative TIFF metadata and pixel-scale access checked. No newer acquisition or production terrain accuracy is implied.' if ready else 'Tile coverage, original metadata or binary resolution check incomplete.',
        'resolution_source_units': observed_scale, 'resolution_unit': index.get('representative_dem_metadata', {}).get('horizontal_unit') if observed_scale else None,
        'resolution_m': observed_scale[0] * 1200 / 3937 if observed_scale and index.get('representative_dem_metadata', {}).get('horizontal_unit') == 'US survey foot' else None,
        'acquisition_id': 'FL_Peninsular_FDEM_Orange_2018',
        'download_urls': [t['attributes']['DownloadDEM'] for t in tiles],
        'coverage_boxes_wgs84': [t['bbox_wgs84'] for t in tiles if t.get('bbox_wgs84')],
        'coverage_basis': 'Actual query-returned tile footprint envelopes; valid raster cells not exhaustively sampled',
        'production_gate': 'Transform source horizontal/vertical US survey feet correctly; inspect all tile metadata, nodata/seams and terrain alignment before activation.'})
    ept = lookup.get('usgs_orange_ept', {})
    candidates.append({'id': 'noaa_usgs_orange_ept', 'rank': 2, 'source_id': 'usgs_orange_ept',
        'decision': 'accept_for_historical_point_sampling' if ept.get('probe', {}).get('status') == 'reachable' and ept.get('local_sample') else 'pending',
        'reason': 'NOAA specifically references the existing USGS Orange EPT. Historical classified roof/ground sampling can expand; this is not a second independent flight.',
        'resolution_m': None, 'resolution_note': 'Nominal project pulse spacing about 0.35m; point density is not a raster cell resolution or local accuracy guarantee.',
        'acquisition_id': 'FL_Peninsular_FDEM_Orange_2018', 'download_urls': [ept.get('url')],
        'coverage_boxes_wgs84': [ept['local_sample']['pilot_bbox_wgs84']] if ept.get('local_sample') else [],
        'coverage_basis': 'Previously sampled pilot bbox only; full EPT project envelope is not complete local sampling',
        'production_gate': 'Validate acquisition age, roof class coverage, density and current building changes per footprint.'})
    noaa = lookup.get('noaa_florida_east1_dem', {})
    extent = noaa.get('metadata_summary', {}).get('bbox_wgs84')
    candidates.append({'id': 'noaa_east1_regional_dem', 'rank': 3, 'source_id': 'noaa_florida_east1_dem',
        'decision': 'reject_for_precise_streetscape',
        'reason': 'Approximately 3m regional composite is too coarse for curb/sidewalk geometry and partly derives from the same Orange acquisition. Retain only as a potential broad-context fallback.',
        'resolution_m': noaa.get('resolution_m'), 'derived_from_acquisition_ids': ['FL_Peninsular_FDEM_Orange_2018'],
        'download_urls': [noaa.get('download_url')], 'metadata_bbox_intersects_study': intersects(extent, bbox),
        'binary_access_status': noaa.get('binary_access', {}).get('status'),
        'coverage_boxes_wgs84': [extent] if extent else [], 'coverage_basis': 'Regional ISO metadata envelope, not valid-pixel coverage',
        'context_fallback_status': 'pending pixel/nodata check and metadata conflict review; catalog accessLevel disagrees with working public binary',
        'production_gate': 'Not approved for pedestrian dimensions, surveyed elevations or live flood simulation.'})
    canopy = lookup.get('florida_noaa_canopy_2020_2021', {})
    samples = canopy.get('pilot_pixel_samples', [])
    nodata = bool(samples and all(s.get('value') in [None, '', 'NoData'] for s in samples))
    restricted = canopy.get('use_restrictions', {}).get('ml_use_allowed') is False
    candidates.append({'id': 'florida_noaa_canopy', 'rank': 4, 'source_id': 'florida_noaa_canopy_2020_2021',
        'decision': 'exclude_from_ai_candidate_use' if restricted else 'pending',
        'reason': 'Ecopia written-consent exception/five-year ML restriction applies; original product creation and expiry are unestablished, so exclude from AI workflows. Pilot pixel is also NoData.' if restricted else 'Pilot-center query returned no valid canopy value; broad service extent does not establish local raster coverage.' if nodata else 'Valid local canopy pixels, source acquisition and terms still require verification.',
        'resolution_m': canopy.get('metadata_summary', {}).get('pixelSizeX'), 'download_urls': [],
        'coverage_boxes_wgs84': [], 'coverage_basis': 'Unknown valid-pixel coverage; not drawn as covered',
        'pilot_sample_nodata': nodata, 'ai_use_allowed': False if restricted else None,
        'production_gate': 'No AI training/improvement/validation/testing/evaluation use without established eligibility. No tree positions/species from unverified local coverage.'})
    return candidates


def coverage_html(catalog):
    bbox = catalog['study_bbox_wgs84']
    padding_x, padding_y = (bbox[2] - bbox[0]) * .65, (bbox[3] - bbox[1]) * .65
    view = [bbox[0] - padding_x, bbox[1] - padding_y, bbox[2] + padding_x, bbox[3] + padding_y]
    width, height = 900, 620
    def rectangle(box, fill, stroke, label, dashed=False):
        if not intersects(box, view):
            return ''
        clipped = [max(box[0], view[0]), max(box[1], view[1]), min(box[2], view[2]), min(box[3], view[3])]
        x = (clipped[0] - view[0]) / (view[2] - view[0]) * width
        y = (view[3] - clipped[3]) / (view[3] - view[1]) * height
        w = (clipped[2] - clipped[0]) / (view[2] - view[0]) * width
        h = (clipped[3] - clipped[1]) / (view[3] - view[1]) * height
        dash = ' stroke-dasharray="8 5"' if dashed else ''
        return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}><title>{html.escape(label)}</title></rect>'
    shapes, legend = [], []
    colors = ['#376fb2', '#25864f', '#9b7a30', '#777777']
    for candidate, color in zip(reversed(catalog['candidate_selections']), reversed(colors)):
        boxes = candidate['coverage_boxes_wgs84']
        identifier = candidate['id']
        fill = 'url(#envelope)' if 'regional' in identifier else color + '22'
        shapes.append(f'<g id="{identifier}">' + ''.join(rectangle(box, fill, color, candidate['coverage_basis']) for box in boxes) + '</g>')
        legend.append(f'<p><label><input type="checkbox" checked data-layer="{identifier}"> <strong>{html.escape(identifier)}</strong></label> — {html.escape(candidate["decision"])}. {html.escape(candidate["coverage_basis"])}</p>')
    shapes.append(rectangle(bbox, 'none', '#d32e2e', 'Study extraction rectangle; not official district boundary', True))
    records = ''.join(f'<tr><td>{c["rank"]}</td><td>{html.escape(c["id"])}</td><td>{html.escape(c["decision"])}</td><td>{html.escape(c["reason"])}</td></tr>' for c in catalog['candidate_selections'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>TWIN source coverage evidence</title>
<style>body{{font:16px system-ui;max-width:1150px;margin:30px auto;padding:0 20px;color:#17362d}}svg{{width:100%;border:1px solid #bbb;background:#f7f7f1}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #ddd}}.note{{background:#fff3ce;padding:14px}}</style>
<h1>College Park source coverage evidence</h1><p>Generated {html.escape(catalog['created_utc'])}. Red dashed rectangle: extraction extent. North is up; geographic coordinate diagram, not a surveyed basemap.</p>
<p class="note">Boxes show actual source metadata/tile envelopes, not guaranteed valid pixels, complete measurements or official district boundaries. Hatched regional metadata envelope is clipped to this view. Unknown coverage is not drawn. Hover over boxes for their evidence basis.</p>
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Source tile envelopes and sampled pilot over the College Park extraction rectangle"><defs><pattern id="envelope" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 0L12 12" stroke="#cbb88b" stroke-width="1"/></pattern></defs>{''.join(shapes)}</svg>
<p>View longitude {view[0]:.5f} to {view[2]:.5f}; latitude {view[1]:.5f} to {view[3]:.5f}.</p>{''.join(legend)}
<table><thead><tr><th>Rank</th><th>Candidate</th><th>Decision</th><th>Reason</th></tr></thead><tbody>{records}</tbody></table>
<p>Machine-readable evidence: source_catalog.json in this directory. Candidate acceptance is for bounded preparation/sampling, not production geometry release.</p>
<script>document.querySelectorAll('[data-layer]').forEach(e=>e.onchange=()=>document.getElementById(e.dataset.layer).style.display=e.checked?'':'none');</script></html>'''


def build(root=ROOT, offline=False, refresh=False, timeout=15):
    config_path = root / 'config/government_sources.json'
    configuration = json.loads(config_path.read_text(encoding='utf-8'))
    sources = configuration['sources']
    if len({s['id'] for s in sources}) != len(sources):
        raise ValueError('Duplicate source IDs')
    client = ProbeClient(root / 'data/cache/source_catalog', offline, refresh, timeout)
    def safe_probe(source):
        try:
            return probe_source(source, configuration['study_bbox_wgs84'], client, root)
        except (ValueError, KeyError, OSError, ET.ParseError) as exc:
            return {**source, 'probe': {'status': 'metadata_unreadable', 'error': str(exc)},
                    'coverage': {'state': 'unknown', 'feature_count': None}}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(safe_probe, sources))
    groups = acquisition_groups(sources)
    for group in groups:
        products = []
        for row in rows:
            for product in row.get('products', []):
                # Exact project directory identifies known copies/tiles, not title similarity.
                path = urllib.parse.urlparse(product.get('downloadURL') or '').path
                if '/' + group['acquisition_id'] + '/' in path:
                    products.append(product['sourceId'])
        group['catalog_product_ids'] = sorted(set(products))
        group['tile_index_members'] = [{'source_id': row['id'], 'tile_ids': [t['attributes'].get('LidarName') for t in row.get('tile_records', []) if t['attributes'].get('WU_Name') == group['acquisition_id']]}
                                      for row in rows if row.get('tile_records')]
    snapshots = sorted({r['local_snapshot']['snapshot'] for r in rows if r.get('local_snapshot')})
    output = {'schema_version': 1, 'created_utc': utcnow(), 'study_bbox_wgs84': configuration['study_bbox_wgs84'],
              'scope_note': configuration['scope_note'], 'configuration_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
              'sources': rows, 'acquisition_groups': groups, 'local_snapshots': snapshots, 'local_snapshot_consistent': len(snapshots) <= 1,
              'candidate_selections': select_candidates(rows, configuration['study_bbox_wgs84']),
              'discovery_outcomes': run_discoveries(configuration, client)}
    atomic_json(root / 'data/processed/source_catalog.json', output)
    (root / 'data/processed/source_coverage.html').write_text(coverage_html(output), encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    output = build(offline=args.offline, refresh=args.refresh, timeout=args.timeout)
    print(json.dumps({'sources': len(output['sources']), 'acquisition_groups': output['acquisition_groups'],
                      'probes': [{'id': s['id'], 'access': s['probe']['status'], 'coverage': s['coverage']['state']} for s in output['sources']],
                      'candidate_selections': [{k: c.get(k) for k in ['id', 'decision', 'resolution_m']} for c in output['candidate_selections']],
                      'local_snapshots': output['local_snapshots'],
                      'output': str(ROOT / 'data/processed/source_catalog.json')}, indent=2))
