"""Original environment prototype safety and geometry contracts."""
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import numpy as np
from pxr import Usd,UsdGeom,UsdShade
from PIL import Image
import build_detailed_assets as assets


class DetailedAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name);(cls.out/'textures').mkdir()
        cls.previous=assets.OUT;assets.OUT=cls.out
        assets.leaf_texture();assets.revised_tree('oak_a',110);assets.revised_tree('palm',310);assets.car()

    @classmethod
    def tearDownClass(cls):
        assets.OUT=cls.previous;cls.temp.cleanup()

    def test_cutout_texture_and_leaf_shader_are_connected(self):
        alpha=np.asarray(Image.open(self.out/'textures/leaf_cluster.png'))[:,:,3]
        self.assertGreater((alpha==0).mean(),.2);self.assertGreater((alpha==255).mean(),.1)
        stage=Usd.Stage.Open(str(self.out/'oak_a.usdc'))
        shader=UsdShade.Shader(stage.GetPrimAtPath('/Asset/Materials/LeafTone0/Surface'))
        self.assertTrue(shader.GetInput('opacity').HasConnectedSource())
        self.assertGreater(shader.GetInput('opacityThreshold').Get(),0)
        foliage=UsdGeom.Mesh(stage.GetPrimAtPath('/Asset/Geometry/FoliageTone0'))
        self.assertTrue(foliage.GetDoubleSidedAttr().Get())
        self.assertEqual(len(UsdGeom.PrimvarsAPI(foliage).GetPrimvar('st').Get()),len(foliage.GetFaceVertexIndicesAttr().Get()))

    def test_geometry_finite_valid_and_bounded_prototype_budget(self):
        for name in ('oak_a','palm','sedan'):
            stage=Usd.Stage.Open(str(self.out/(name+'.usdc')));count=0
            for prim in stage.Traverse():
                if not prim.IsA(UsdGeom.Mesh):continue
                m=UsdGeom.Mesh(prim);p=np.asarray(m.GetPointsAttr().Get());indices=np.asarray(m.GetFaceVertexIndicesAttr().Get())
                self.assertTrue(np.isfinite(p).all());self.assertGreaterEqual(indices.min(),0);self.assertLess(indices.max(),len(p))
                count+=len(p)
                normals=m.GetNormalsAttr().Get()
                if normals:self.assertTrue(np.isfinite(np.asarray(normals)).all())
            self.assertLess(count,10000)

    def test_car_scale_reflective_glass_and_paint_variants(self):
        stage=Usd.Stage.Open(str(self.out/'sedan.usdc'))
        box=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default']).ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedRange()
        extent=box.GetSize();self.assertAlmostEqual(extent[0],4.5,places=2)
        self.assertLess(extent[1],2.4);self.assertGreater(extent[2],1.4)
        shader=UsdShade.Shader(stage.GetPrimAtPath('/Asset/Materials/Glass/Surface'))
        self.assertEqual(shader.GetInput('metallic').Get(),0)
        self.assertLess(shader.GetInput('roughness').Get(),.15)
        self.assertEqual(len(stage.GetDefaultPrim().GetVariantSet('paintColor').GetVariantNames()),4)

    def test_active_output_refused(self):
        with self.assertRaisesRegex(ValueError,'non-active'):assets.build(proposal=False)
        with self.assertRaisesRegex(ValueError,'original assets'):assets.build(output=ROOT/'assets/generated')

    def test_existing_instance_arrays_and_vehicle_transforms_preserved(self):
        work=ROOT/'scene/environment_workview_proposal.usda'
        if not work.exists():self.skipTest('Optional district proposal has not been generated')
        source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'));proposal=Usd.Stage.Open(str(work))
        for name in ('positions','orientations','scales','protoIndices','invisibleIds'):
            a=source.GetPrimAtPath('/World/Trees').GetAttribute(name).Get();b=proposal.GetPrimAtPath('/World/Trees').GetAttribute(name).Get()
            self.assertEqual(str(a),str(b),name)
        for car in source.GetPrimAtPath('/World/ParkedVehicles').GetChildren():
            path=car.GetPath().AppendChild('DetailedSedan')
            a=UsdGeom.Xformable(source.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            b=UsdGeom.Xformable(proposal.GetPrimAtPath(path)).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            self.assertEqual(a,b)


if __name__=='__main__':unittest.main()
