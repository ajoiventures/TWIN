"""Terrain proposal sampling, unit and source-boundary regressions."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile
import json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
sys.path.insert(0,str(ROOT/'tools'))
import numpy as np
from build_terrain_proposal import coarse_mesh, build, verify_source, US_FOOT_M
from acquire_dem import checksum


class TerrainProposalTests(unittest.TestCase):
    def setUp(self):
        self.grid={'left_ft':550000.,'top_ft':1500000.,'pixel_size_ft':2.5,'horizontal_epsg':6438}

    def test_original_feet_are_converted_once_and_origin_is_explicit(self):
        values=np.full((9,9),100.,dtype=np.float32)
        points,faces,stats=coarse_mesh(values,np.ones_like(values,dtype=bool),self.grid,[-81.389,28.572],4,30.)
        np.testing.assert_allclose(points[:,2],100*US_FOOT_M-30,atol=1e-6)
        self.assertEqual(len(faces),4)
        self.assertAlmostEqual(stats['absolute_vertex_elevation_range_navd88_m'][0],100*US_FOOT_M)
        cross=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
        self.assertTrue((cross[:,2]>0).all())

    def test_interior_nodata_is_never_bridged_even_when_corners_valid(self):
        values=np.full((17,17),100.,dtype=np.float32)
        inside=np.ones_like(values,dtype=bool)
        values[3,3]=np.nan
        inside[11,11]=False
        points,faces,stats=coarse_mesh(values,inside,self.grid,[-81.389,28.572],8)
        self.assertEqual(stats['accepted_quads'],2)
        self.assertEqual(stats['rejected_quads'],2)
        self.assertTrue(np.isfinite(points).all())

    def test_common_grid_crosses_tile_seam_without_duplicate_vertices(self):
        # Seam at column 8: global sampling shares its vertices on both sides.
        values=np.tile(np.arange(17,dtype=np.float32),(9,1))+100
        points,faces,stats=coarse_mesh(values,np.ones_like(values,dtype=bool),self.grid,[-81.389,28.572],8)
        self.assertEqual(len(points),6)
        self.assertEqual(len(set(faces[0]) & set(faces[1])),2)
        self.assertEqual(len(np.unique(points,axis=0)),6)
        self.assertAlmostEqual(stats['nominal_spacing_m'],20*US_FOOT_M)

    def test_invalid_frame_source_configuration_fails_before_scene_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config').mkdir()
            (root/'data/heights/dem').mkdir(parents=True)
            config={'study_bbox_wgs84':[0,0,1,1], 'expected_vertical_datum':'North American Vertical Datum 1988',
                    'expected_vertical_unit':'US survey foot'}
            path=root/'config/terrain_sources.json'
            path.write_text(json.dumps(config))
            (root/'config/study_area.json').write_text(json.dumps({'acquisition_bbox_wgs84':[0,0,1,1]}))
            (root/'data/heights/dem/manifest.json').write_text(json.dumps({'configuration_sha256':'wrong'}))
            with self.assertRaisesRegex(ValueError,'configuration changed'):
                build(root)
            self.assertFalse((root/'scene').exists())

    def test_tampered_source_or_wrong_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.tif'
            path.write_bytes(b'original raster fixture')
            receipt={'url':'https://example.test/source','sha256':checksum(path)}
            path.with_suffix('.tif.source.json').write_text(json.dumps(receipt))
            verify_source(path,receipt['url'],receipt)
            with self.assertRaisesRegex(ValueError,'identity/hash'):
                verify_source(path,'https://example.test/different',receipt)
            path.write_bytes(b'changed raster fixture')
            with self.assertRaisesRegex(ValueError,'identity/hash'):
                verify_source(path,receipt['url'],receipt)

    def test_unknown_vertical_datum_refuses_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'config').mkdir()
            (root/'config/terrain_sources.json').write_text(json.dumps({'expected_vertical_datum':'unknown'}))
            with self.assertRaisesRegex(ValueError,'Unverified vertical'):
                build(root)
            self.assertFalse((root/'scene').exists())


if __name__=='__main__':
    unittest.main()
