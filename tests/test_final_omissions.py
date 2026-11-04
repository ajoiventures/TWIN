import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.dependencies')]
import numpy as np
from shapely.geometry import box
from verify_final_omissions import roof_support
class FinalOmissionTests(unittest.TestCase):
 def test_ground_and_unclassified_do_not_create_roof(self):
  points=np.array([[x+.2,y+.2,30,c] for x in range(4) for y in range(4) for c in [1,2,2]])
  g,components=roof_support(points,box(0,0,4,4));self.assertIsNone(g);self.assertEqual(components,[])
 def test_source_grid_not_parcel_extrusion_and_slope_diagnostic(self):
  points=np.array([[x+dx,y+dy,35+.3*x,6] for x in range(4) for y in range(4) for dx,dy in [(.1,.1),(.2,.2),(.3,.3),(.4,.4),(.5,.5),(.6,.6),(.7,.7)]])
  g,components=roof_support(points,box(-5,-5,10,10));self.assertEqual(g.area,16);self.assertEqual(len(components),1);self.assertGreater(components[0]['z_p05_p50_p95_navd88_m'][2],35.5)
 def test_no_closing_fills_unsupported_hole(self):
  points=np.array([[x+dx,y+dy,35,6] for x in range(5) for y in range(5) if (x,y)!=(2,2) for dx,dy in [(.1,.1),(.2,.2),(.3,.3),(.4,.4),(.5,.5)]])
  g,_=roof_support(points,box(0,0,5,5));self.assertEqual(g.area,24);self.assertEqual(g.intersection(box(2,2,3,3)).area,0)
if __name__=='__main__':unittest.main()
