import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import tomllib,ast

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
sys.path.insert(0,str(ROOT/'tools'))
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdUtils
from build_sample import build


class SampleBuildTests(unittest.TestCase):
    def test_clean_cli_arbitrary_cwd_and_portable_dependency_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); destination=root/'portable sample'
            result=subprocess.run([sys.executable,str(ROOT/'tools/build_sample.py'),'--output',str(destination)],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            manifest=json.loads(result.stdout)
            moved=root/'relocated'; destination.rename(moved)
            stage=Usd.Stage.Open(str(moved/'sample.usda'))
            layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(moved/'sample.usda'))
            self.assertFalse(assets);self.assertFalse(unresolved)
            self.assertEqual(len(layers),4)
            self.assertTrue(all(Path(layer.realPath).is_relative_to(moved) for layer in layers))
            self.assertEqual(stage.GetRootLayer().subLayerPaths,['manual.usda','scenario.usda','base.usda'])
            self.assertEqual(UsdGeom.GetStageMetersPerUnit(stage),1)
            self.assertEqual(UsdGeom.GetStageUpAxis(stage),'Z')
            self.assertTrue(stage.GetPrimAtPath(manifest['camera']).IsA(UsdGeom.Camera))
            self.assertGreater(UsdLux.DistantLight(stage.GetPrimAtPath('/World/Lighting/Sun')).GetIntensityAttr().Get(),0)
            bounds=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render']).ComputeWorldBound(stage.GetDefaultPrim()).ComputeAlignedBox()
            self.assertGreater(bounds.GetSize()[0],100)
            camera=UsdGeom.Camera(stage.GetPrimAtPath(manifest['camera'])).GetCamera()
            self.assertAlmostEqual(camera.horizontalAperture/camera.verticalAperture,16/9)
            self.assertEqual(manifest['render_resolution'],[1280,720])
            clip=camera.frustum.ComputeViewMatrix()*camera.frustum.ComputeProjectionMatrix()
            cache=UsdGeom.BBoxCache(Usd.TimeCode.Default(),['default','render'])
            for group in ('Buildings','Road','Trees','Cars','Sidewalks','Ground'):
                bound=cache.ComputeWorldBound(stage.GetPrimAtPath('/World/'+group)).ComputeAlignedBox()
                for index in range(8):
                    corner=bound.GetCorner(index)
                    projected=clip.Transform(corner)
                    self.assertLessEqual(abs(projected[0]),.9,(group,index,projected))
                    self.assertLessEqual(abs(projected[1]),.9,(group,index,projected))
                    self.assertGreater(projected[2],-1)
                    self.assertLess(projected[2],1)
            self.assertEqual(len(stage.GetPrimAtPath('/World/Buildings').GetChildren()),10)
            self.assertEqual(len(stage.GetPrimAtPath('/World/Trees').GetChildren()),12)
            self.assertEqual(len(stage.GetPrimAtPath('/World/Cars').GetChildren()),4)

    def test_deterministic_outputs_and_existing_files_protected(self):
        with tempfile.TemporaryDirectory() as temporary:
            a=Path(temporary)/'a'; b=Path(temporary)/'b'
            one=build(a);two=build(b)
            self.assertEqual(one,two)
            self.assertEqual((a/'sample_manifest.json').read_bytes(),(b/'sample_manifest.json').read_bytes())
            with self.assertRaises(FileExistsError):build(a)

    def test_manual_scenario_separation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);build(root)
            stage=Usd.Stage.Open(str(root/'sample.usda'))
            scenario=next(x for x in stage.GetLayerStack() if x.realPath.endswith('scenario.usda'))
            manual=next(x for x in stage.GetLayerStack() if x.realPath.endswith('manual.usda'))
            stage.SetEditTarget(scenario)
            UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cars')).MakeInvisible()
            self.assertEqual(UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cars')).ComputeVisibility(),'invisible')
            stage.SetEditTarget(manual)
            UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cars')).MakeVisible()
            self.assertEqual(UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cars')).ComputeVisibility(),'inherited')
            self.assertNotIn('visibility', (root/'base.usda').read_text())

    def test_generated_experience_uses_renderer_and_self_contained_edit_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);build(root)
            experience=tomllib.loads((root/'sample.kit').read_text())
            self.assertEqual(set(experience['dependencies']),{'omni.kit.uiapp','omni.hydra.rtx','omni.usd','omni.kit.viewport.window','omni.kit.viewport.utility'})
            bootstrap=(root/'open_sample.py').read_text();ast.parse(bootstrap)
            self.assertIn('sample_startup_task=',bootstrap)
            self.assertIn("layers['manual']",bootstrap)
            self.assertIn('Only manual/scenario edits may be saved',bootstrap)
            self.assertNotIn('stage.Save(',bootstrap)


if __name__=='__main__':unittest.main()
