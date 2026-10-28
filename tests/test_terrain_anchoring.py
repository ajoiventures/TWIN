from pathlib import Path
import sys,unittest,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
from anchor_terrain_proposal import GroundSampler,rigid_delta,drape_points,tessellated_drape,bridge_policy,verify_dependencies,US_FOOT_M,checksum
from shapely.geometry import box


class FakeGround:
    def sample(self,xy):
        xy=np.asarray(xy);return xy[:,0]*.1+2


class AnchoringTests(unittest.TestCase):
    def test_rigid_building_preserves_every_relative_coordinate(self):
        points=np.array([[0,0,.1],[10,0,.1],[10,10,8],[0,10,8.]])
        delta,detail=rigid_delta(points,FakeGround())
        moved=points+[0,0,delta]
        np.testing.assert_allclose(moved-moved[0],points-points[0])
        self.assertAlmostEqual(moved[:,2].min(),2.6)
        self.assertEqual(detail['sampled_ground_relief_m'],1.)

    def test_bilinear_requires_all_four_support_samples(self):
        grid={'left_ft':0.,'top_ft':10.,'pixel_size_ft':1.,'horizontal_epsg':32617}
        values=np.array([[100.,102.],[104.,106.]])
        sample=GroundSampler(values,grid,[-81.389,28.572])
        sample.origin=(0.,0.)
        self.assertAlmostEqual(sample.sample([[1.,9.]])[0],103*US_FOOT_M-30)
        values[1,1]=np.nan
        with self.assertRaisesRegex(ValueError,'nodata'):sample.sample([[1.,9.]])
        with self.assertRaisesRegex(ValueError,'outside'):sample.sample([[0,0]])

    def test_drape_keeps_offset_and_rejects_long_triangles(self):
        points=np.array([[0,0,.065],[2,0,.065],[0,2,.065]])
        moved=drape_points(points,FakeGround(),faces=[[0,1,2]])
        np.testing.assert_allclose(moved[:,:2],points[:,:2])
        np.testing.assert_allclose(moved[:,2],[2.065,2.265,2.065])
        points[1,0]=20
        with self.assertRaisesRegex(ValueError,'tessellation'):drape_points(points,FakeGround(),faces=[[0,1,2]])

    def test_unknown_bridges_do_not_get_draped(self):
        self.assertIsNone(bridge_policy({'highway':'residential'}))
        self.assertIsNone(bridge_policy({'bridge':'no','highway':'residential'}))
        self.assertIsNotNone(bridge_policy({'bridge':'yes'}))
        self.assertIsNotNone(bridge_policy({'bridge':'no','layer':'1'}))

    def test_grid_tessellation_preserves_surface_area_and_ground_offset(self):
        points=np.array([[0,0,.065],[30,0,.065],[30,4,.065],[0,4,.065]])
        out,faces=tessellated_drape(points,[[0,1,2,3]],FakeGround())
        np.testing.assert_allclose(out[:,2],out[:,0]*.1+2.065)
        def area_of(f):
            a=out[f[1],:2]-out[f[0],:2];b=out[f[2],:2]-out[f[0],:2]
            return abs(a[0]*b[1]-a[1]*b[0])/2
        area=sum(area_of(f) for f in faces)
        self.assertAlmostEqual(area,120,places=5)
        self.assertGreater(len(faces),2)

    def test_stale_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'assembly.usda';path.write_text('original')
            deps=[{'path':path.name,'sha256':checksum(path)}]
            verify_dependencies(directory,deps)
            path.write_text('changed')
            with self.assertRaisesRegex(ValueError,'Stale source'):verify_dependencies(directory,deps)

    def test_interior_nodata_surface_support_rejected(self):
        grid={'left_ft':0.,'top_ft':10.,'pixel_size_ft':1.,'horizontal_epsg':32617}
        values=np.full((10,10),100.)
        sampler=GroundSampler(values,grid,[-81.389,28.572]);sampler.origin=(0.,0.)
        sampler.validate_geometry(box(1,2,8,9))
        values[4,4]=np.nan
        with self.assertRaisesRegex(ValueError,'nodata_surface'):sampler.validate_geometry(box(1,2,8,9))


if __name__=='__main__':unittest.main()
