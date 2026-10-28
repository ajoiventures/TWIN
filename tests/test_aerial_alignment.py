import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from review_aerial_alignment import pixel

class ImageRegistrationTests(unittest.TestCase):
    def test_returned_extent_and_image_y_direction(self):
        e=dict(xmin=10,ymin=20,xmax=110,ymax=220)
        self.assertEqual(pixel(10,220,e,500,1000),(0,0))
        self.assertEqual(pixel(110,20,e,500,1000),(500,1000))
        self.assertEqual(pixel(60,120,e,500,1000),(250,500))
    def test_invalid_frame_rejected(self):
        with self.assertRaises(ValueError):pixel(0,0,dict(xmin=1,xmax=1,ymin=0,ymax=1),100,100)
