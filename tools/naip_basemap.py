"""Cache a dated NAIP review basemap in the parcel map's metre grid."""
import hashlib
import json
from math import isfinite
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from imagery_reference import ROOT, image_statistics, read_json, stamp

SERVICE = 'https://imagery.geoplatform.gov/iipp/rest/services/NAIP/NAIP2023_CONUS/ImageServer'
LICENSE = 'https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery'
FOLDER = 'data/imagery/naip_basemap'
BOUNDS = (460222.9248864, 3158511.6927512, 463519.2880506, 3162632.1467065)
SIZE = (1600, 2000)
ACQUISITION = '2023-01-12'
RASTERS = {
    9784: 'm_2808130_nw_17_030_20230112_20230530',
    9786: 'm_2808130_sw_17_030_20230112_20230511',
    9787: 'm_2808129_ne_17_030_20230112_20230511',
    9789: 'm_2808129_se_17_030_20230112_20230511',
}


def get(url, limit):
    target = urlsplit(url)
    if target.scheme != 'https' or target.hostname != 'imagery.geoplatform.gov':
        raise ValueError('Unexpected NAIP download host')
    request = Request(url, headers={'User-Agent': 'TWIN NAIP reference/1.0'})
    with urlopen(request, timeout=25) as response:
        target = urlsplit(response.geturl())
        if target.scheme != 'https' or target.hostname != 'imagery.geoplatform.gov':
            raise ValueError('Unexpected NAIP download host')
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('NAIP response exceeds the cache limit')
    return raw


def publish(path, raw):
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        pending = path.parent / stream.name
        try:
            stream.write(raw)
            stream.close()
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)


def verify_grid(bounds):
    if len(bounds) != 4 or any(not isfinite(a) or abs(a - b) > 0.01 for a, b in zip(bounds, BOUNDS)):
        raise ValueError('NAIP export changed the requested metre grid')


def build(root=ROOT):
    query = {
        'f': 'json', 'objectIds': ','.join(map(str, RASTERS)),
        'outFields': 'objectid,name,year,state,resolution,public', 'returnGeometry': 'false',
    }
    rows = json.loads(get(SERVICE + '/query?' + urlencode(query), 100_000))['features']
    sources = [row['attributes'] for row in rows]
    if ({row['objectid']: row['name'] for row in sources} != RASTERS or
            any((row['year'], row['state'], row['public']) != (2023, 'FL', 'yes') for row in sources)):
        raise ValueError('NAIP raster identity changed')
    params = {
        'f': 'json', 'bbox': ','.join(map(str, BOUNDS)),
        'bboxSR': 32617, 'imageSR': 32617, 'size': ','.join(map(str, SIZE)), 'format': 'jpg', 'bandIds': '0,1,2',
        'mosaicRule': json.dumps({'mosaicMethod': 'esriMosaicLockRaster', 'lockRasterIds': list(RASTERS)}),
    }
    export = json.loads(get(SERVICE + '/exportImage?' + urlencode(params), 100_000))
    extent = export['extent']
    bbox = [extent[key] for key in ('xmin', 'ymin', 'xmax', 'ymax')]
    if extent['spatialReference']['wkid'] != 32617:
        raise ValueError('Unexpected NAIP export CRS')
    verify_grid(bbox)
    raw = get(export['href'], 6 * 1024 * 1024)
    stats = image_statistics(raw)
    if (stats['width'], stats['height']) != SIZE or stats['format'] != 'JPEG':
        raise ValueError('Unexpected NAIP image dimensions or encoding')
    digest = hashlib.sha256(raw).hexdigest()
    folder = root / FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    image = folder / (digest + '.jpg')
    if not image.exists() or hashlib.sha256(image.read_bytes()).hexdigest() != digest:
        publish(image, raw)
    manifest = {
        'acquisition_date': ACQUISITION, 'retrieved_utc': stamp(), 'crs': 'EPSG:32617',
        'bounds': bbox, 'width': stats['width'], 'height': stats['height'], 'sha256': digest,
        'attribution': 'USDA NAIP, served by USFS GTAC / GeoPlatform IIPP',
        'source_url': SERVICE, 'license_url': LICENSE, 'raster_records': sources,
        'export_parameters': params,
    }
    publish(folder / 'manifest.json', json.dumps(manifest, indent=2).encode('utf-8'))
    return manifest


def read_basemap(root=ROOT):
    folder = root / FOLDER
    manifest = read_json(folder / 'manifest.json')
    verify_grid(manifest['bounds'])
    if (manifest['crs'], manifest['width'], manifest['height'], manifest['acquisition_date']) != ('EPSG:32617', *SIZE, ACQUISITION):
        raise ValueError('NAIP manifest grid or vintage changed')
    digest = manifest['sha256']
    if len(digest) != 64 or any(char not in '0123456789abcdef' for char in digest):
        raise ValueError('Invalid NAIP cache identity')
    raw = (folder / (digest + '.jpg')).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('NAIP image checksum mismatch')
    return manifest, raw


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
