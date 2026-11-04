"""Measure 2021 classified canopy within the saved College Park study boundaries."""
import hashlib
import json
import math
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
import shapely
from pyproj import Transformer

DIRECTORY = ROOT / 'data/diagnostics/orlando_canopy_2021'
ARCHIVE_MD5 = 'e8bba02b4c8556311ecf3673e6e4e735'
SOURCE_URL = 'https://zenodo.org/records/15084614'
CLASSES = ('no_data', 'grass', 'non_vegetation', 'tree')


def profile(archive_path, boundaries_path):
    with archive_path.open('rb') as source:
        if hashlib.file_digest(source, 'md5').hexdigest() != ARCHIVE_MD5:
            raise ValueError('Canopy archive does not match the publisher checksum')
    project = Transformer.from_crs(4326, 26917, always_xy=True)
    boundaries = json.loads(boundaries_path.read_text(encoding='utf-8'))
    scopes = {
        feature['id']: shapely.transform(
            shapely.geometry.shape(feature['geometry']), project.transform, interleaved=False
        )
        for feature in boundaries['features'] if feature['id'] in ('main_street', 'neighborhood')
    }
    if set(scopes) != {'main_street', 'neighborhood'}:
        raise ValueError('Both official study boundaries are required')
    with zipfile.ZipFile(archive_path) as archive:
        header = archive.read('2021.HDR').decode()
        # These metadata values identify the verified one-band uint8 ENVI grid.
        columns, rows, left, top, spacing = 144118, 117000, 407784., 3194797.2, .6
        if archive.getinfo('2021').file_size != rows * columns:
            raise ValueError('Unexpected canopy raster dimensions')
        bounds = shapely.union_all(list(scopes.values())).bounds
        x0, y0, x1, y1 = bounds
        start_x, end_x = math.floor((x0-left)/spacing), math.ceil((x1-left)/spacing)
        start_y, end_y = math.floor((top-y1)/spacing), math.ceil((top-y0)/spacing)
        if not (0 <= start_x < end_x <= columns and 0 <= start_y < end_y <= rows):
            raise ValueError('Study boundaries extend beyond the canopy grid')
        xs = left + (np.arange(start_x, end_x) + .5) * spacing
        ys = top - (np.arange(start_y, end_y) + .5) * spacing
        pixels = np.empty((len(ys), len(xs)), dtype=np.uint8)
        with archive.open('2021') as raster:
            raster.seek(start_y * columns)
            for index in range(len(ys)):
                line = raster.read(columns)
                if len(line) != columns:
                    raise ValueError('Canopy raster ended inside the study window')
                pixels[index] = np.frombuffer(line, dtype=np.uint8)[start_x:end_x]
    result = {}
    for name, scope in scopes.items():
        mask = shapely.contains_xy(scope, xs[None, :], ys[:, None])
        counts = np.bincount(pixels[mask], minlength=len(CLASSES))
        if len(counts) != len(CLASSES) or counts[1:].sum() == 0:
            raise ValueError('Unexpected canopy class values or no classified area')
        result[name] = {
            'class_pixels': dict(zip(CLASSES, map(int, counts))),
            'classified_canopy_percent': float(100 * counts[3] / counts[1:].sum()),
            'tree_area_m2': float(counts[3] * spacing**2),
        }
    return {
        'source': SOURCE_URL, 'archive_md5': ARCHIVE_MD5, 'license': 'CC BY 4.0',
        'observation_year': 2021, 'crs': 'EPSG:26917', 'spacing_m': spacing,
        'boundary_sha256': hashlib.sha256(boundaries_path.read_bytes()).hexdigest(),
        'envi_header_sha256': hashlib.sha256(header.encode()).hexdigest(),
        'window_shape': list(pixels.shape), 'study_areas': result,
        'limits': 'Historical classified canopy by pixel centers. Trunks, species, tree counts and current condition are unverified.',
    }


if __name__ == '__main__':
    report = profile(DIRECTORY / '2021_withinboundary.zip', ROOT / 'data/processed/study_boundaries.geojson')
    (DIRECTORY / 'coverage.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
