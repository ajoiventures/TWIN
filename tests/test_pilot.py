import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from shapely.geometry import LineString,MultiLineString
from define_pilot import select_intersection

class PilotBoundaryTests(unittest.TestCase):
 def test_staggered_junction_choice_explicit(self):
  edge=LineString([(0,0),(0,10)]);cross=MultiLineString([[(-1,2),(1,2)],[(-1,3),(1,3)]])
  p,n=select_intersection(edge,cross,'south');self.assertEqual(n,2);self.assertEqual(p.y,2)
 def test_no_intersection_is_not_guessed(self):
  with self.assertRaises(ValueError):select_intersection(LineString([(0,0),(0,10)]),LineString([(1,2),(2,2)]),'south')

if __name__=='__main__':unittest.main()
