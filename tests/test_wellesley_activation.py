from pathlib import Path
import hashlib,json,os,sys,tempfile,unittest
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'));sys.path.insert(0,str(ROOT/'tools'))
from pxr import Usd,UsdGeom,Sdf
from build_wellesley_architecture import activate,validate_activation,validate_active_wellesley,sha

class WellesleyActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for folder in ('scene','data/processed','data/heights/wellesley_architecture','data/renders/review'):(self.root/folder).mkdir(parents=True)
        self.write('data/processed/active.json',{'snapshot':'s1'})
        source=self.root/'scene/landmark_corrections.usda';s=Usd.Stage.CreateNew(str(source));UsdGeom.Cube.Define(s,'/World/Buildings/Building_2939');s.GetRootLayer().Save()
        for name in ('manual_edits.usda','map_extent_guard.usda'):
            layer=Sdf.Layer.CreateNew(str(self.root/'scene'/name));layer.Save()
        assembly=Usd.Stage.CreateNew(str(self.root/'scene/college_park_connected.usda'))
        assembly.GetRootLayer().subLayerPaths=['map_extent_guard.usda','manual_edits.usda','landmark_corrections.usda']
        assembly.GetRootLayer().customLayerData={'userCamera':'keep this root setting'}
        assembly.OverridePrim('/World/UserEdits').CreateAttribute('userNote',Sdf.ValueTypeNames.String).Set('preserve this opinion')
        assembly.GetRootLayer().Save()
        report={'source_snapshot':'s1','resolved_building_id':'Building_2939','documentary_storeys':7,'main_roof_height_m':23.35,'maximum_equipment_height_m':28.393,
                'deviation':{'hausdorff_m':3.,'symmetric_difference_fraction':.103},'dependencies':{'scene/landmark_corrections.usda':sha(source)}}
        proposal=self.root/'scene/wellesley_architectural_proposal.usda';s=Usd.Stage.CreateNew(str(proposal))
        p=s.OverridePrim('/World/Buildings/Building_2939');p.SetCustomDataByKey('architecturalInterpretation',{'status':'inactive'})
        s.GetRootLayer().customLayerData={'reportJson':json.dumps(report)};s.GetRootLayer().Save()
        report['proposal_sha256']=sha(proposal);self.write('data/heights/wellesley_architecture/report.json',report)
        image=self.root/'data/renders/review/test.png';image.write_bytes(b'\x89PNG\r\n\x1a\n'+b'x'*1100)
        self.proof=Path('data/renders/review/manifest.json')
        self.write(self.proof,{'source_snapshot':'s1','proposal_layer':proposal.name,'camera':'/World/Cameras/CivilPrincetonEdgewater','image':str(image.relative_to(self.root)),'image_sha256':sha(image),'layer_hashes':{'scene/'+proposal.name:sha(proposal)}})
    def tearDown(self):self.temp.cleanup()
    def write(self,path,data):(self.root/path).write_text(json.dumps(data),encoding='utf-8')

    def test_guarded_temp_activation_preserves_root_and_order(self):
        assembly=self.root/'scene/college_park_connected.usda';before=assembly.read_bytes()
        checked=validate_activation(self.root,self.proof);self.assertTrue(checked)
        record=activate(self.root,self.proof)
        stage=Usd.Stage.Open(str(assembly));self.assertEqual(stage.GetRootLayer().customLayerData,{'userCamera':'keep this root setting'})
        self.assertEqual(stage.GetPrimAtPath('/World/UserEdits').GetAttribute('userNote').Get(),'preserve this opinion')
        names=list(stage.GetRootLayer().subLayerPaths);self.assertLess(names.index('manual_edits.usda'),names.index('wellesley_architecture.usda'))
        self.assertLess(names.index('map_extent_guard.usda'),names.index('wellesley_architecture.usda'))
        self.assertLess(names.index('wellesley_architecture.usda'),names.index('landmark_corrections.usda'))
        self.assertEqual((self.root/record['root_backup']).read_bytes(),before)
        self.assertTrue(validate_active_wellesley(self.root))
        self.assertEqual(record['deviation']['hausdorff_m'],3)

    def test_stale_render_proposal_source_and_report_fail_closed(self):
        self.assertFalse(validate_active_wellesley(self.root))
        before=(self.root/'scene/college_park_connected.usda').read_bytes()
        proof=json.loads((self.root/self.proof).read_text());proof['layer_hashes']['scene/wellesley_architectural_proposal.usda']='wrong';self.write(self.proof,proof)
        with self.assertRaises(ValueError):activate(self.root,self.proof)
        self.assertEqual((self.root/'scene/college_park_connected.usda').read_bytes(),before)
        self.assertFalse((self.root/'scene/wellesley_architecture.usda').exists())
        with self.assertRaises(ValueError):validate_activation(self.root,None)

    def test_modified_review_metrics_rejected(self):
        path=self.root/'data/heights/wellesley_architecture/report.json';data=json.loads(path.read_text());data['deviation']['hausdorff_m']=0;path.write_text(json.dumps(data))
        with self.assertRaises(ValueError):validate_activation(self.root,self.proof)

    def test_changed_source_and_image_rejected(self):
        path=self.root/'scene/landmark_corrections.usda';original=path.read_bytes();path.write_bytes(original+b'\n# changed source\n')
        with self.assertRaises(ValueError):validate_activation(self.root,self.proof)
        path.write_bytes(original)
        image=self.root/'data/renders/review/test.png';image.write_bytes(image.read_bytes()+b'changed')
        with self.assertRaises(ValueError):validate_activation(self.root,self.proof)

if __name__=='__main__':unittest.main()
