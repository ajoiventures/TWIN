from pathlib import Path
import sys,tempfile,json,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Sdf,Usd,UsdGeom,Gf
import activate_environment_assets as activation


class EnvironmentActivationTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);(root/'scene').mkdir();(root/'data/processed').mkdir(parents=True)
        layer=Sdf.Layer.CreateNew(str(root/'scene/college_park_connected.usda'))
        layer.customLayerData={'cameraSettings':{'boundCamera':'/World/Cameras/Test'},'renderSettings':{'samples':32}}
        layer.subLayerPaths=['map_extent_guard.usda','manual_edits.usda','asset_upgrade.usda']
        for name in layer.subLayerPaths:Sdf.Layer.CreateNew(str(root/'scene'/name)).Save()
        layer.Save();proposal=root/'scene/asset_upgrade_proposal.usda';Sdf.Layer.CreateNew(str(proposal)).Save()
        report={'status':'validated_not_activated','source_snapshot':'s1','root_sha256':activation.sha(root/'scene/college_park_connected.usda'),
            'proposal_sha256':activation.sha(proposal),'asset_hashes':{},'texture_hashes':{},
            'preserved_source_hashes':{str(p.relative_to(root)).replace('\\','/'):activation.sha(p) for p in (root/'scene').glob('*.usda') if p!=proposal}}
        return root,report

    def test_default_is_validation_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report=self.fixture(folder);before=(root/'scene/college_park_connected.usda').read_bytes()
            with patch.object(activation,'validate',return_value=report):self.assertEqual(activation.activate(root)['status'],'validated_not_activated')
            self.assertEqual((root/'scene/college_park_connected.usda').read_bytes(),before)
            self.assertFalse((root/'data/processed/environment_activation.json').exists())

    def test_apply_preserves_root_metadata_manual_and_creates_recoverable_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report=self.fixture(folder);assembly=root/'scene/college_park_connected.usda';before=assembly.read_bytes()
            metadata=dict(Sdf.Layer.FindOrOpen(str(assembly)).customLayerData)
            manual=(root/'scene/manual_edits.usda').read_bytes()
            with patch.object(activation,'validate',return_value=report):result=activation.activate(root,apply=True)
            layer=Sdf.Layer.FindOrOpen(str(assembly));layer.Reload()
            self.assertEqual(dict(layer.customLayerData),metadata)
            self.assertEqual(list(layer.subLayerPaths),['map_extent_guard.usda','manual_edits.usda','asset_upgrade_environment_v2.usda','asset_upgrade.usda'])
            self.assertEqual((root/'scene/manual_edits.usda').read_bytes(),manual)
            self.assertEqual((root/result['backup']/'college_park_connected.usda').read_bytes(),before)
            self.assertEqual(activation.validated_environment_layer(root),'asset_upgrade_environment_v2.usda')
            self.assertFalse((root/'scene/.environment_activation.lock').exists())
            (root/'scene/asset_upgrade_environment_v2.usda').write_text('# changed')
            with self.assertRaisesRegex(ValueError,'dependency changed'):activation.validated_environment_layer(root)

    def test_concurrent_root_edit_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'root.usda';path.write_text('original');expected=activation.sha(path)
            path.write_text('user edit')
            with self.assertRaisesRegex(ValueError,'concurrently'):activation.guarded_replace(path,b'candidate',expected)
            self.assertEqual(path.read_text(),'user edit');self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_source_change_between_validation_and_apply_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report=self.fixture(folder);before=(root/'scene/college_park_connected.usda').read_bytes()
            def changed(_):
                (root/'scene/manual_edits.usda').write_text('# user edit')
                return report
            with patch.object(activation,'validate',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'Source changed'):activation.activate(root,apply=True)
            self.assertEqual((root/'scene/college_park_connected.usda').read_bytes(),before)
            self.assertFalse((root/'scene/asset_upgrade_environment_v2.usda').exists())

    def test_tree_arrays_and_car_transforms_rejected_if_changed(self):
        a=Usd.Stage.CreateInMemory();trees=UsdGeom.PointInstancer.Define(a,'/World/Trees');trees.CreatePositionsAttr([(1,2,0)]);trees.CreateProtoIndicesAttr([0])
        UsdGeom.Xform.Define(a,'/World/ParkedVehicles/Car_000/DetailedSedan').AddTranslateOp().Set(Gf.Vec3d(1,2,0))
        b=Usd.Stage.CreateInMemory();b.GetRootLayer().ImportFromString(a.GetRootLayer().ExportToString())
        self.assertEqual(activation.compare_placements(a,b),{'tree_instances':1,'cars':1})
        UsdGeom.PointInstancer(b.GetPrimAtPath('/World/Trees')).GetPositionsAttr().Set([(4,2,0)])
        with self.assertRaisesRegex(ValueError,'Tree instance'):activation.compare_placements(a,b)
        UsdGeom.PointInstancer(b.GetPrimAtPath('/World/Trees')).GetPositionsAttr().Set([(1,2,0)])
        b.GetPrimAtPath('/World/ParkedVehicles/Car_000/DetailedSedan').GetAttribute('xformOp:translate').Set(Gf.Vec3d(2,2,0))
        with self.assertRaisesRegex(ValueError,'Vehicle transform'):activation.compare_placements(a,b)

    def test_receipt_write_failure_rolls_back_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root,report=self.fixture(folder);before=(root/'scene/college_park_connected.usda').read_bytes();replace=activation.os.replace
            def fail_receipt(src,dst):
                if Path(dst).name=='environment_activation.json':raise OSError('simulated receipt failure')
                return replace(src,dst)
            with patch.object(activation,'validate',return_value=report),patch.object(activation.os,'replace',side_effect=fail_receipt):
                with self.assertRaisesRegex(OSError,'receipt failure'):activation.activate(root,apply=True)
            self.assertEqual((root/'scene/college_park_connected.usda').read_bytes(),before)


if __name__=='__main__':unittest.main()
