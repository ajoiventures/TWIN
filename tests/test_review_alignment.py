from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.dependencies')]
from review_alignment import utm17,distributed,native_grid_checks
from pyproj import Transformer
import numpy as np
from pxr import Gf,Usd,UsdGeom

class AlignmentArithmeticTests(unittest.TestCase):
    def test_independent_series_matches_reference_across_project(self):
        reference=Transformer.from_crs(4326,32617,always_xy=True)
        for lon in (-81.398,-81.389,-81.379):
            for lat in (28.5602,28.572,28.5858):
                self.assertLess(max(abs(a-b) for a,b in zip(utm17(lon,lat),reference.transform(lon,lat))),.001)
        x,y=utm17(-81.389,28.572)
        self.assertGreater(utm17(-81.388,28.572)[0],x);self.assertGreater(utm17(-81.389,28.573)[1],y)

    def test_distributed_points_cover_extremes_and_reject_duplicates(self):
        points=[(x,y) for x in range(4) for y in range(4)];chosen=[points[i] for i in distributed(points)]
        self.assertEqual(len(set(chosen)),10)
        for corner in ((0,0),(0,3),(3,0),(3,3)):self.assertIn(corner,chosen)
        with self.assertRaises(ValueError):distributed([(0,0)]*10)

    def test_native_order_detects_whole_pixel_shift_and_uses_parent_transform(self):
        origin=(-81.389,28.572);grid={'left_ft':528405.,'top_ft':1545900.,'pixel_size_ft':2.5,'horizontal_epsg':6438}
        transform=Transformer.from_crs(6438,32617,always_xy=True);o=Transformer.from_crs(4326,32617,always_xy=True).transform(*origin)
        values=[]
        for row in range(4):
            for col in range(4):
                x,y=transform.transform(grid['left_ft']+(col+.5)*2.5,grid['top_ft']-(row+.5)*2.5);values.append((x-o[0],y-o[1],0))
        values=np.asarray(values);valid=np.ones((4,4),bool)
        result=native_grid_checks(values,Gf.Matrix4d(1),grid,valid,valid,1,origin)
        self.assertLess(max(r['residual_m'] for r in result),.001)
        shifted=values+(values[1]-values[0])
        self.assertGreater(min(r['residual_m'] for r in native_grid_checks(shifted,Gf.Matrix4d(1),grid,valid,valid,1,origin)),.7)
        stage=Usd.Stage.CreateInMemory();parent=UsdGeom.Xform.Define(stage,'/World');parent.AddTranslateOp().Set((5,7,0))
        child=UsdGeom.Mesh.Define(stage,'/World/Terrain');matrix=UsdGeom.XformCache().GetLocalToWorldTransform(child.GetPrim())
        self.assertGreater(min(r['residual_m'] for r in native_grid_checks(values,matrix,grid,valid,valid,1,origin)),8)
        result=native_grid_checks(values-(5,7,0),matrix,grid,valid,valid,1,origin)
        self.assertLess(max(r['residual_m'] for r in result),.001)
        with self.assertRaisesRegex(ValueError,'vertex count'):native_grid_checks(values[:-1],Gf.Matrix4d(1),grid,valid,valid,1,origin)

if __name__=='__main__':unittest.main()
