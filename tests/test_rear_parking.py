import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_rear_parking import pixel_ground

class IdentityProjection:
    def transform(self,x,y):return x,y

class RearParkingRegistrationTests(unittest.TestCase):
    extent=dict(xmin=100,ymin=200,xmax=200,ymax=400)
    def test_image_y_and_local_origin_and_area(self):
        p=pixel_ground([[0,0],[100,0],[100,200],[0,200]],self.extent,100,200,IdentityProjection(),(100,200))
        self.assertEqual(p.bounds,(0,0,100,200));self.assertEqual(p.area,20000)
        self.assertEqual(list(p.exterior.coords)[0],(0,200))
    def test_outside_or_self_crossing_trace_rejected(self):
        for pts in [[[-1,0],[10,0],[10,10]],[[0,0],[100,200],[0,200],[100,0]]]:
            with self.subTest(pts=pts),self.assertRaises(ValueError):pixel_ground(pts,self.extent,100,200,IdentityProjection(),(0,0))
