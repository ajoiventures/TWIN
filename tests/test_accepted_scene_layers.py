"""Portable accepted-layer guard regressions; synthetic local files only."""
from pathlib import Path
import tempfile,json,hashlib,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from accepted_scene_layers import CONFIG,validated_layer,manual_model_fingerprint

class AcceptedSceneLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.config=CONFIG['campus_hardscape']
        self.write('data/processed/active.json',{'snapshot':'fixture-S'})
        self.write('scene/manual_edits.usda','#usda 1.0\nover "World"\n{\n    over "Cameras"\n    {\n    }\n}\n')
        self.write(self.config['layer'],'#usda 1.0\ndef Xform "FixturePaving" {}\n')
        self.write('tools/prepare_campus_hardscape.py','original fixture recipe')
        self.write(self.config['recipe_helper_archive'],'original fixture recipe')
        self.write('data/cache/fixture_source.json',{'source':'original public fixture'})
        for path in self.config['reviews']:self.write(path,{'decision':'fixture reviewed'})
        recipe={name:self.hash(name) for name in ['tools/prepare_campus_hardscape.py','data/processed/active.json','data/cache/fixture_source.json']}
        self.write(self.config['source_manifest'],{'schema':'twin.campus-hardscape-candidate/1','source_snapshot':'fixture-S','dependencies':recipe,'outputs':{'site.usda':'fixture-candidate'}})
        dependencies={**recipe,**{name:self.hash(name) for name in self.config['reviews']|{self.config['source_manifest']}}}
        dependencies[self.config['recipe_helper_archive']]=dependencies.pop('tools/prepare_campus_hardscape.py')
        self.packet={'schema':'twin.accepted-scene-layer/1','kind':'campus_hardscape','layer':self.config['layer'],'quality':self.config['quality'],
            'current_geometry_verified':False,'public_derivative_release_accepted':False,'source_snapshot':'fixture-S','layer_sha256':self.hash(self.config['layer']),
            'dependencies':dependencies,'source_candidate_sha256':'fixture-candidate','manual_model_fingerprint':manual_model_fingerprint(self.root)}
        self.save_packet()
    def tearDown(self):self.temp.cleanup()
    def write(self,name,value):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value) if isinstance(value,dict) else value,encoding='utf-8')
    def hash(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
    def save_packet(self):self.write(self.config['receipt'],self.packet)
    def test_layer_edit_and_missing_canonical_source_rejected(self):
        self.assertEqual(validated_layer('campus_hardscape',self.root),'campus_hardscape.usda')
        layer=self.root/self.config['layer'];before=layer.read_bytes();layer.write_bytes(before+b'\n# changed\n')
        with self.assertRaisesRegex(ValueError,'layer changed'):validated_layer('campus_hardscape',self.root)
        layer.write_bytes(before);del self.packet['dependencies']['data/cache/fixture_source.json'];self.save_packet()
        with self.assertRaisesRegex(ValueError,'required evidence missing'):validated_layer('campus_hardscape',self.root)
    def test_stale_snapshot_rejected(self):
        self.write('data/processed/active.json',{'snapshot':'fixture-new'})
        with self.assertRaisesRegex(ValueError,'snapshot stale'):validated_layer('campus_hardscape',self.root)
    def test_frozen_producer_required_but_working_code_can_evolve(self):
        self.write('tools/prepare_campus_hardscape.py','new working version with local samples input')
        self.assertEqual(validated_layer('campus_hardscape',self.root),'campus_hardscape.usda')
        archive=self.root/self.config['recipe_helper_archive'];before=archive.read_bytes();archive.write_bytes(before+b' changed')
        with self.assertRaisesRegex(ValueError,'dependency changed'):validated_layer('campus_hardscape',self.root)
        archive.write_bytes(before);del self.packet['dependencies'][self.config['recipe_helper_archive']];self.save_packet()
        with self.assertRaisesRegex(ValueError,'required evidence missing'):validated_layer('campus_hardscape',self.root)
    def test_camera_save_compatible_but_model_change_rejected(self):
        self.write('scene/manual_edits.usda','#usda 1.0\nover "World"\n{\n    over "Cameras"\n    {\n        def Camera "SavedUserView"\n        {\n            float focalLength = 75\n        }\n    }\n}\n')
        self.assertEqual(validated_layer('campus_hardscape',self.root),'campus_hardscape.usda')
        self.write('scene/manual_edits.usda','#usda 1.0\nover "World"\n{\n    over "Buildings"\n    {\n        over "Building_1"\n        {\n            token visibility = "invisible"\n        }\n    }\n}\n')
        with self.assertRaisesRegex(ValueError,'Manual model opinions changed'):validated_layer('campus_hardscape',self.root)
    def test_local_release_and_candidate_identity_guards(self):
        self.packet['public_derivative_release_accepted']=True;self.save_packet()
        with self.assertRaisesRegex(ValueError,'public release'):validated_layer('campus_hardscape',self.root)
        self.packet['public_derivative_release_accepted']=False;self.packet['source_candidate_sha256']='different';self.save_packet()
        with self.assertRaisesRegex(ValueError,'candidate identity changed'):validated_layer('campus_hardscape',self.root)

if __name__=='__main__':unittest.main()
