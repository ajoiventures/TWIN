"""Prepare dated City directory references for existing park identities only.

Default is offline. --live fetches missing bounded official HTML pages. No
imagery, contacts, source geometry, active snapshot, API or scene is published.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
import argparse, datetime, hashlib, json, os, re, shutil, sys, time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '.dependencies'), str(ROOT / 'tools')]
from inventory_neighborhood_parks import validate as validate_inventory

OUT = Path('data/processed/park_facility_references')
CACHE = Path('data/cache/park_facility_references')
BASE = 'https://www.orlando.gov/Parks-the-Environment/Directory/'
PAGES = {
    '62': ('Lake-Ivanhoe-Park', 'Lake Ivanhoe Park', 'Directory points to east-side Ivanhoe location; GIS address is south-side. Whole lake/shoreline amenity association is not accepted.'),
    '66': ('Albert-Park', 'Albert Park', 'Named directory context at matching Edgewater street number; no surveyed facility placement.'),
    '79': ('Dartmouth-Park', 'Dartmouth Park', 'GIS says Darmouth; directory says Dartmouth. Spelling discrepancy retained.'),
    '81': ('Don-Dudley-Park', 'Don Dudley Park', 'Named directory context; no surveyed facility placement.'),
    '91': ('Guernsey-Park', 'Guernsey Park', 'Named directory context; no surveyed facility placement.'),
    '94': ('Ivanhoe-Plaza-Park', 'Ivanhoe Plaza Park', 'Distinct from Lake Ivanhoe Park; do not transfer amenities between them.'),
    '113': ('Mathews-Park', 'Mathews Park', 'Named directory context; no surveyed facility placement.'),
    '121': ('Overbrook-Park', 'Overbrook Park', 'GIS has no street number; directory supplies a reference address, not a corrected source address.'),
    '125': ('Princeton-Park-and-College-Park-Pool', 'Princeton Park and College Park Pool', 'Combined park/pool directory page shares center address; park, pool and center hours/features must remain distinct. GIS2411 versus directory2393 address conflict.'),
    '145': ('Lake-Adair-Park', 'Lake Adair Park', 'GIS995 versus directory951 Lake Adair address conflict; location identity needs review.'),
    '239': ('College-Park-Neighborhood-Center', 'College Park Neighborhood Center', 'Center-specific page; do not apply its indoor amenities or operating hours to the adjacent park/pool polygon. GIS Street versus directory Avenue retained.'),
}


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def encode(value): return json.dumps(value, indent=2, ensure_ascii=True).encode()


class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []
    def text(self): return ' '.join(' '.join(c.text() if isinstance(c, Node) else c for c in self.children).split())
    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node): yield from child.nodes()
    def has_class(self, value): return value in self.attrs.get('class', '').split()


class PageParser(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    def __init__(self):
        super().__init__(convert_charrefs=True); self.root = Node(); self.current = self.root
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current); self.current.children.append(node)
        if tag not in self.VOID: self.current = node
    def handle_endtag(self, tag):
        cursor = self.current
        while cursor.parent is not None:
            if cursor.tag == tag: self.current = cursor.parent; return
            cursor = cursor.parent
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)
    def handle_data(self, data): self.current.children.append(data)


def parse_page(raw, url, expected_title):
    parser = PageParser(); parser.feed(raw.decode('utf-8-sig'))
    nodes = list(parser.root.nodes())
    titles = [n.text() for n in nodes if n.tag == 'h1' and n.has_class('oc-page-title')]
    if titles != [expected_title]: raise ValueError('Directory title changed: ' + url)
    canonical = [n.attrs.get('href') for n in nodes if n.tag == 'link' and n.attrs.get('rel') == 'canonical']
    if canonical != [url]: raise ValueError('Unexpected directory canonical URL')
    address = [n.text() for n in nodes if n.has_class('gmap-address')]
    location = [n.text() for n in nodes if n.has_class('gmap-latlong')]
    if len(address) != 1 or len(location) != 1: raise ValueError('Directory location schema changed')
    coordinates = [float(v) for v in location[0].split(',')]
    if len(coordinates) != 2 or not 24 <= coordinates[0] <= 32 or not -88 <= coordinates[1] <= -79:
        raise ValueError('Unexpected directory reference coordinates')
    features = [n for n in nodes if n.tag == 'ul' and n.has_class('park-feature-list')]
    if len(features) != 1: raise ValueError('Directory feature schema changed')
    amenities = [n.text() for n in features[0].children if isinstance(n, Node) and n.tag == 'li']
    if len(amenities) > 60 or len(set(amenities)) != len(amenities): raise ValueError('Unexpected feature list')
    days = [n for n in nodes if n.has_class('hours-day')]
    if days:
        hours = []
        for day in days:
            lists = [n for n in day.parent.children if isinstance(n, Node) and n.has_class('hours-time-list')]
            if len(lists) != 1: raise ValueError('Hours list schema changed')
            hours.append({'day': day.text(), 'published_time': lists[0].text()})
        if {h['day'] for h in hours} != {'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'} or len(hours) != 7:
            raise ValueError('Incomplete weekly hours')
        published_hours = {'kind': 'weekly_directory_schedule', 'weekly': hours}
    else:
        headings = [n for n in nodes if n.tag == 'h3' and n.text() == 'Hours']
        if len(headings) != 1: raise ValueError('Missing directory hours')
        children = headings[0].parent.children; start = children.index(headings[0]) + 1; parts = []
        for child in children[start:]:
            if isinstance(child, Node) and child.tag in ('h2', 'h3'): break
            text = child.text() if isinstance(child, Node) else child
            if text.strip(): parts.append(text.strip())
        value = ' '.join(' '.join(parts).split())
        if not value or len(value) > 200: raise ValueError('Unrecognized textual hours')
        published_hours = {'kind': 'textual_directory_schedule', 'text': value}
    maps = []
    for node in nodes:
        if node.tag == 'a' and re.search(r'amenit.*map', node.text(), re.I):
            target = urljoin(url, node.attrs.get('href', ''))
            if urlparse(target).hostname != 'www.orlando.gov': raise ValueError('Unexpected amenity-map host')
            maps.append({'label': node.text(), 'url': target, 'downloaded': False, 'georeferencing_verified': False})
    metadata = {n.attrs.get('property') or n.attrs.get('name'): n.attrs.get('content') for n in nodes if n.tag == 'meta'}
    descriptions = [n.text() for n in nodes if n.tag == 'p']
    claims = []
    if expected_title == 'Albert Park':
        for text in descriptions:
            if re.search(r'20-foot by 30-foot pavilion with a stage', text, re.I):
                claims.append({'kind': 'pavilion_with_stage', 'nominal_dimensions': [20, 30], 'dimension_unit': 'feet',
                               'orientation': None, 'geometry_accepted': False, 'source_locator': 'park description paragraph'})
    if expected_title == 'Dartmouth Park':
        for text in descriptions:
            if re.search(r'two small pavilions and a 20 x 30-foot shade structure', text, re.I):
                claims.append({'kind': 'shade_structure', 'nominal_dimensions': [20, 30], 'dimension_unit': 'feet',
                               'orientation': None, 'geometry_accepted': False, 'source_locator': 'park description paragraph'})
                claims.append({'kind': 'small_pavilions', 'published_quantity': 2, 'geometry_accepted': False,
                               'source_locator': 'same park description paragraph; quantity is a publisher assertion'})
    return {'directory_title': titles[0], 'directory_address': address[0],
            'directory_reference_point_lat_lon': coordinates, 'published_hours': published_hours,
            'published_features': amenities, 'description_claims': claims, 'amenity_map_references': maps,
            'publisher_page_date_modified': metadata.get('article:modified_time'),
            'publisher_page_date_published': metadata.get('article:published_time')}


def page_cache(root, url, live=False):
    if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'www.orlando.gov' or not url.startswith(BASE):
        raise ValueError('Only reviewed official directory URLs are allowed')
    folder = root / CACHE; key = hashlib.sha256(url.encode()).hexdigest()
    path = folder / (key + '.html'); proof = folder / (key + '.receipt.json')
    if path.exists() != proof.exists(): raise ValueError('Preserve incomplete page cache')
    if path.exists():
        receipt = read(proof)
        if receipt.get('sha256') != sha(path) or receipt.get('url') != url or receipt.get('final_url') != url:
            raise ValueError('Cached page identity or bytes changed')
        return path.read_bytes(), receipt, [path, proof]
    if not live: raise FileNotFoundError('Missing official page cache: ' + url + '; use --live to acquire')
    for attempt in range(3):
        try:
            request = Request(url, headers={'User-Agent': 'TWIN official park reference research'})
            with urlopen(request, timeout=30) as response:
                if response.url != url: raise ValueError('Unexpected directory redirect')
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type: raise ValueError('Expected official HTML')
                raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024: raise ValueError('Directory page exceeds bounded read')
                receipt = {'url': url, 'final_url': response.url, 'retrieved_utc': now(),
                           'sha256': hashlib.sha256(raw).hexdigest(), 'content_type': content_type,
                           'last_modified': response.headers.get('Last-Modified')}
            break
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2: raise
        except (URLError, TimeoutError):
            if attempt == 2: raise
        time.sleep(2 ** attempt)
    folder.mkdir(parents=True, exist_ok=True)
    if path.exists() or proof.exists(): raise ValueError('Page cache appeared during acquisition; preserve for review')
    temporary = path.with_suffix('.pending'); temporary.write_bytes(raw); os.replace(temporary, path)
    temporary = proof.with_suffix('.pending'); temporary.write_bytes(encode(receipt)); os.replace(temporary, proof)
    return raw, receipt, [path, proof]


FIELDS = {
    'id': 'Existing City park reference identity; never a new physical facility',
    'source_object_id': 'Unchanged original City GIS OBJECTID string',
    'source_name': 'Unchanged GIS source name', 'source_address': 'Unchanged GIS source address, including spelling',
    'source_type': 'Unchanged source facility type', 'source_class': 'Unchanged source classification',
    'in_main_street': 'Positive-area intersection in the separately validated inventory',
    'page_reference': 'Official named directory context, its URL/cache hash/check date and date/reuse limits',
    'association': 'Explicit candidate association and address/facility scope; not accepted amenity geometry',
    'published_hours': 'Publisher schedule for this directory page only; no effective-date or live-open claim',
    'published_features': 'Publisher feature labels for this page only; no positions, count, condition or ADA audit',
    'description_claims': 'Selected explicit description facts; nominal dimensions/quantities are undated publisher assertions, not accepted geometry',
    'amenity_map_references': 'Official links only; pixels not fetched and georeferencing not verified',
    'public_access_verified': 'False: no field or legal-access verification',
    'current_conditions_verified': 'False: retrieval date does not date field observation',
    'is_open_now': 'Unknown; no live operational inference',
    'physical_facility_geometry': 'Unknown; this product does not create or alter geometry',
    'legal_ownership': 'Unknown; directory/service membership does not prove title',
}


def previous(root):
    path = root / OUT / 'packet.json'; proof = root / OUT / 'receipt.json'
    if path.exists() != proof.exists(): raise ValueError('Preserve incomplete facility-reference publication')
    if not path.exists(): return None
    if read(proof).get('sha256') != sha(path): raise ValueError('Preserve manually modified facility references')
    return sha(path)


def build(root=ROOT, live=False):
    root = Path(root).resolve(); expected = previous(root); inventory = validate_inventory(root)
    if {r['source_object_id'] for r in inventory['rows']} != set(PAGES): raise ValueError('Park population changed; reconcile directory mapping')
    paths = [root / 'tools/enrich_park_facilities.py', root / 'data/land/full_neighborhood_parks/inventory.json', root / 'data/land/full_neighborhood_parks/receipt.json']
    dependencies = {p.relative_to(root).as_posix(): sha(p) for p in paths}; rows = []
    for source in inventory['rows']:
        slug, title, scope = PAGES[source['source_object_id']]; url = BASE + slug
        raw, receipt, paths = page_cache(root, url, live); parsed = parse_page(raw, url, title)
        dependencies.update({p.relative_to(root).as_posix(): sha(p) for p in paths})
        reference = {k: parsed[k] for k in ('directory_title', 'directory_address', 'directory_reference_point_lat_lon', 'publisher_page_date_modified', 'publisher_page_date_published')}
        reference.update({'publisher': 'City of Orlando', 'url': url, 'checked_utc': receipt['retrieved_utc'],
                          'html_sha256': receipt['sha256'], 'http_last_modified': receipt.get('last_modified'),
                          'observation_date': None, 'effective_date': None,
                          'reuse_conditions': 'Public reference access observed; no affirmative imagery/HTML redistribution or derivative-model license inferred.'})
        row = {'id': source['id'], 'source_object_id': source['source_object_id'], 'source_name': source['name'],
               'source_address': source['address'], 'source_type': source['type'], 'source_class': source['class'],
               'in_main_street': source['main_street_intersection_m2'] > 0, 'page_reference': reference,
               'association': {'status': 'named_directory_context_pending_site_reconciliation', 'scope_note': scope,
                               'source_geometry_changed': False, 'amenities_assigned_to_entire_polygon': False},
               'published_hours': parsed['published_hours'], 'published_features': parsed['published_features'], 'description_claims': parsed['description_claims'],
               'amenity_map_references': parsed['amenity_map_references'], 'public_access_verified': False,
               'current_conditions_verified': False, 'is_open_now': None, 'physical_facility_geometry': None, 'legal_ownership': None}
        if set(row) != set(FIELDS): raise ValueError('Incomplete facility reference dictionary')
        rows.append(row)
    packet = {'schema': 'twin.park-facility-references/1', 'source_snapshot': inventory['comparison_snapshot'],
              'built_utc': now(), 'counts': {'existing_park_references': len(rows), 'official_directory_contexts': len(rows),
                  'main_street_references': sum(r['in_main_street'] for r in rows), 'current_conditions_verified': 0,
                  'accepted_facility_geometries': 0, 'legal_titles_verified': 0},
              'rows': rows, 'field_dictionary': FIELDS, 'first_five_safe_rows': rows[:5], 'dependencies': dependencies,
              'limitations': ['Published hours and features are undated directory assertions, not live access or observed condition.',
                  'Park, pool and neighborhood-center scopes and conflicting source addresses remain distinct.',
                  'No amenity positions, accessible routes, parking capacity, ownership, vacancy or scene geometry inferred.',
                  'Raw HTML remains local; no page photographs, maps, contact information, keys or HTML are in this publication.'],
              'active_snapshot_changed': False, 'scene_changed': False, 'api_changed_by_builder': False}
    if any(sha(root / p) != h for p, h in dependencies.items()) or previous(root) != expected:
        raise ValueError('Source/output changed during preparation')
    out = root / OUT; out.mkdir(parents=True, exist_ok=True)
    if expected:
        backup = out / 'backups' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); backup.mkdir(parents=True)
        for name in ('packet.json', 'receipt.json'): shutil.copy2(out / name, backup / name)
    path = out / 'packet.json'; temporary = out / 'packet.pending'; temporary.write_bytes(encode(packet)); os.replace(temporary, path)
    temporary = out / 'receipt.pending'; temporary.write_bytes(encode({'sha256': sha(path), 'source_snapshot': packet['source_snapshot']})); os.replace(temporary, out / 'receipt.json')
    return packet


def validate(root=ROOT):
    root = Path(root).resolve()
    if not previous(root): raise ValueError('Park facility references are not built')
    packet = read(root / OUT / 'packet.json'); inventory = validate_inventory(root)
    if packet.get('schema') != 'twin.park-facility-references/1' or packet.get('source_snapshot') != inventory['comparison_snapshot']:
        raise ValueError('Facility source snapshot changed')
    expected_dependencies = {'tools/enrich_park_facilities.py', 'data/land/full_neighborhood_parks/inventory.json', 'data/land/full_neighborhood_parks/receipt.json'}
    for slug, _, _ in PAGES.values():
        key = hashlib.sha256((BASE + slug).encode()).hexdigest()
        expected_dependencies.update((str(CACHE / (key + '.html')).replace('\\', '/'), str(CACHE / (key + '.receipt.json')).replace('\\', '/')))
    if set(packet.get('dependencies', {})) != expected_dependencies or packet.get('field_dictionary') != FIELDS:
        raise ValueError('Facility dependency or field contract changed')
    for name, digest in packet.get('dependencies', {}).items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or sha(path) != digest: raise ValueError('Facility source dependencies changed')
    expected = {r['id']: r for r in inventory['rows']}
    if len(packet['rows']) != len(expected) or {r['id'] for r in packet['rows']} != set(expected) or packet.get('first_five_safe_rows') != packet['rows'][:5]:
        raise ValueError('Facility source membership or preview changed')
    for row in packet['rows']:
        source = expected[row['id']]
        identifiers = {'source_object_id': source['source_object_id'], 'source_name': source['name'], 'source_address': source['address'],
                       'source_type': source['type'], 'source_class': source['class'], 'in_main_street': source['main_street_intersection_m2'] > 0}
        if set(row) != set(FIELDS) or any(row[k] != value for k, value in identifiers.items()):
            raise ValueError('Facility original identity changed')
        if row['current_conditions_verified'] is not False or row['public_access_verified'] is not False or any(row[k] is not None for k in ('is_open_now', 'physical_facility_geometry', 'legal_ownership')):
            raise ValueError('Facility publication promotes unverified conditions')
        slug, title, scope = PAGES[row['source_object_id']]; ref = row['page_reference']
        if ref['url'] != BASE + slug or ref['directory_title'] != title or any(ref[k] is not None for k in ('observation_date', 'effective_date')):
            raise ValueError('Facility source context or date semantics changed')
        if row['association'] != {'status': 'named_directory_context_pending_site_reconciliation', 'scope_note': scope,
                                  'source_geometry_changed': False, 'amenities_assigned_to_entire_polygon': False} or any(c.get('geometry_accepted') is not False for c in row['description_claims']):
            raise ValueError('Facility scope promotes unverified geometry')
    return packet


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--live', action='store_true'); parser.add_argument('--validate', action='store_true'); args = parser.parse_args()
    result = validate() if args.validate else build(live=args.live)
    print(json.dumps({'counts': result['counts'], 'source_snapshot': result['source_snapshot'], 'packet': str(OUT / 'packet.json')}))
