import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'.dependencies'))
from shapely.geometry import box
from pxr import Gf
from study_boundaries import memberships
from constrain_scene import fits

class ScopeTests(unittest.TestCase):
 def test_main_street_membership_not_discarded_outside_neighborhood(self):
  result=memberships(box(9,9,10,10),box(8,8,12,12),box(0,0,5,5));self.assertTrue(result['main_street_member']);self.assertFalse(result['college_park_neighborhood_member'])
 def test_full_object_bounds_not_only_center_must_fit(self):
  ground=box(0,0,10,10);self.assertTrue(fits(Gf.Range3d(Gf.Vec3d(1,1,0),Gf.Vec3d(9,9,8)),ground))
  self.assertFalse(fits(Gf.Range3d(Gf.Vec3d(9,9,0),Gf.Vec3d(11,11,8)),ground))
 def test_slanted_actual_boundary_not_axis_aligned_envelope(self):
  from shapely.geometry import Polygon
  ground=Polygon([(0,1),(9,0),(10,9),(1,10)]);self.assertFalse(fits(Gf.Range3d(Gf.Vec3d(0,0,0),Gf.Vec3d(.2,.2,1)),ground))

if __name__=='__main__':unittest.main()
