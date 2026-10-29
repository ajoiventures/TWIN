from pathlib import Path
import sys,tempfile,unittest,json
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Sdf
import activate_flood_context as activation


class FloodActivationTests(unittest.TestCase):
    def test_optional_activation_preserves_root_and_manual_and_backs_up(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scene').mkdir();(root/'data/flood').mkdir(parents=True)
            path=root/'scene/college_park_connected.usda';layer=Sdf.Layer.CreateNew(str(path));layer.subLayerPaths=['map_extent_guard.usda','manual_edits.usda','base.usda'];layer.customLayerData={'cameraSettings':{'boundCamera':'keep'},'renderSettings':{'samples':42}};layer.Save()
            manual=root/'scene/manual_edits.usda';manual.write_text('# manual bytes preserved')
            flood=root/'scene/fema_effective_hazards.usda';Sdf.Layer.CreateNew(str(flood)).Save();before=path.read_bytes()
            report={'status':'validated_not_activated','source_snapshot':'s1','layer':'scene/fema_effective_hazards.usda','layer_sha256':activation.sha(flood),'root_sha256':activation.sha(path),'dependencies':{'scene/manual_edits.usda':activation.sha(manual),'scene/college_park_connected.usda':activation.sha(path)}}
            with patch.object(activation,'validate',return_value=report):
                self.assertEqual(activation.activate(root)['status'],'validated_not_activated');self.assertEqual(path.read_bytes(),before)
                result=activation.activate(root,apply=True)
            layer.Reload(True);self.assertEqual(layer.customLayerData,{'cameraSettings':{'boundCamera':'keep'},'renderSettings':{'samples':42}})
            self.assertEqual(list(layer.subLayerPaths),['map_extent_guard.usda','manual_edits.usda','fema_effective_hazards.usda','base.usda'])
            self.assertEqual(manual.read_text(),'# manual bytes preserved');self.assertEqual((root/result['backup']/path.name).read_bytes(),before)
            self.assertFalse((root/'scene/.flood_activation.lock').exists())


if __name__=='__main__':unittest.main()
