import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
sys.path.insert(0, str(ROOT / 'tools'))
import numpy as np
from PIL import Image, TiffImagePlugin
from acquire_dem import US_FOOT_M, analyze_seams, download, inspect_tile, paste_tile, seam_metrics, valid_pixels, validate_metadata


CONFIG = {'expected_horizontal_crs': 'NAD83(2011) / Florida East (ftUS)', 'expected_vertical_datum': 'North American Vertical Datum 1988',
          'expected_vertical_unit': 'US survey foot', 'expected_acquisition_interval': ['20181204', '20190412'], 'expected_pixel_scale_ft': 2.5}
META = {'horizontal_crs': CONFIG['expected_horizontal_crs'], 'vertical_datum': CONFIG['expected_vertical_datum'],
        'vertical_unit': CONFIG['expected_vertical_unit'], 'acquisition_start': '20181204', 'acquisition_end': '20190412'}


class Response(io.BytesIO):
    status = 200
    headers = {}
    def geturl(self):
        return 'https://rockyweb.usgs.gov/test.tif'


class DemTests(unittest.TestCase):
    def test_vertical_meter_metadata_is_not_treated_as_original_feet(self):
        with self.assertRaisesRegex(ValueError, 'vertical'):
            validate_metadata({**META, 'vertical_unit': 'meter'}, CONFIG)

    def test_acquisition_change_requires_review(self):
        with self.assertRaisesRegex(ValueError, 'acquisition'):
            validate_metadata({**META, 'acquisition_end': '20250101'}, CONFIG)

    def test_cached_receipt_preserves_original_fetch_and_checks_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'tile.tif'
            first = download('https://rockyweb.usgs.gov/test.tif', target, 100, opener=lambda *a, **k: Response(b'TIFF'))
            second = download('https://rockyweb.usgs.gov/test.tif', target, 100, offline=True)
            self.assertEqual(first['fetched_utc'], second['fetched_utc'])
            self.assertEqual(first['sha256'], second['sha256'])
            target.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                download('https://rockyweb.usgs.gov/test.tif', target, 100, offline=True)

    def test_stream_byte_bound_removes_partial_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'tile.tif'
            with self.assertRaisesRegex(ValueError, 'byte bound'):
                download('https://rockyweb.usgs.gov/test.tif', target, 3, opener=lambda *a, **k: Response(b'toolarge'))
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.tif.part').exists())

    def test_download_host_is_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'official'):
                download('https://unrelated.example/tile', Path(tmp) / 'tile.tif', 100)

    def test_offline_miss_does_not_connect(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, 'Offline'):
                download('https://rockyweb.usgs.gov/test.tif', Path(tmp) / 'tile.tif', 100, offline=True,
                         opener=lambda *a, **k: self.fail('network called'))

    def test_geotiff_pixels_units_and_nodata_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.tif'
            directory = TiffImagePlugin.ImageFileDirectory_v2()
            directory[33550] = (2.5, 2.5, 1.)
            directory[33922] = (0., 0., 0., 525000., 1550000., 0.)
            keys = [(1024, 0, 1, 1), (1025, 0, 1, 1), (3072, 0, 1, 6438), (3076, 0, 1, 9003),
                    (4096, 0, 1, 6360), (4099, 0, 1, 9003)]
            directory[34735] = (1, 1, 0, len(keys), *(v for entry in keys for v in entry))
            directory[42113] = '-999999'
            values = np.array([[100, -999999], [101, 102]], dtype=np.float32)
            Image.fromarray(values).save(path, tiffinfo=directory)
            result, read, mask = inspect_tile(path, META, CONFIG)
            self.assertEqual(result['horizontal_epsg'], 6438)
            self.assertEqual(result['vertical_reference']['geotiff_vertical_epsg'], 6360)
            self.assertEqual(result['valid_pixels'], 3)
            self.assertAlmostEqual(result['pixel_size_m'], .762001524003048)
            self.assertEqual(result['source_bounds_ft'], [525000., 1549995., 525005., 1550000.])

    def test_real_terrain_slope_does_not_create_false_seam_offset(self):
        result = seam_metrics(np.array([10., 20.]), np.array([9., 19.]), np.array([11., 21.]), np.array([12., 22.]))
        self.assertAlmostEqual(result['median_signed_step_m'], US_FOOT_M)
        self.assertAlmostEqual(result['median_signed_residual_m'], 0.)

    def test_artificial_vertical_step_is_detected(self):
        result = seam_metrics(np.array([10., 20.]), np.array([9., 19.]), np.array([16., 26.]), np.array([17., 27.]))
        self.assertAlmostEqual(result['median_signed_residual_m'], 5 * US_FOOT_M)

    def test_missing_seam_pixels_stay_unknown(self):
        bad = np.array([np.nan])
        self.assertEqual(seam_metrics(bad, bad, bad, bad)['status'], 'unknown_no_valid_pairs')

    def test_nodata_and_nonfinite_are_invalid_but_negative_elevation_is_valid(self):
        values = np.array([-999999, np.nan, np.inf, -3., 0., 90.], dtype=np.float32)
        self.assertEqual(valid_pixels(values, -999999).tolist(), [False, False, False, True, True, True])

    def test_overlapping_valid_pixels_report_conflict(self):
        grid = {'left_ft': 0, 'top_ft': 5, 'pixel_size_ft': 2.5, 'width': 2, 'height': 2}
        tile = {'source_origin_top_left_ft': [0, 5], 'width': 2, 'height': 2}
        mosaic = np.full((2, 2), np.nan, dtype=np.float32)
        covered = np.zeros((2, 2), dtype=bool)
        valid = np.ones((2, 2), dtype=bool)
        paste_tile(mosaic, covered, grid, tile, np.full((2, 2), 100, dtype=np.float32), valid)
        result = paste_tile(mosaic, covered, grid, tile, np.full((2, 2), 105, dtype=np.float32), valid)
        self.assertEqual(result['overlap_valid_pixels'], 4)
        self.assertAlmostEqual(result['overlap_max_difference_m'], 5 * US_FOOT_M)
        self.assertTrue(np.all(mosaic == 100))

    def test_subpixel_grid_misalignment_is_rejected(self):
        grid = {'left_ft': 0, 'top_ft': 5, 'pixel_size_ft': 2.5, 'width': 2, 'height': 2}
        tile = {'source_origin_top_left_ft': [.5, 5], 'width': 2, 'height': 2}
        with self.assertRaisesRegex(ValueError, 'common source grid'):
            paste_tile(np.zeros((2, 2)), np.ones((2, 2), dtype=bool), grid, tile, np.zeros((2, 2)), np.ones((2, 2), dtype=bool))


if __name__ == '__main__':
    unittest.main()
