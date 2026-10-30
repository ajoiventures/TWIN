from pathlib import Path
import json,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.dependencies')]
from pxr import Usd,UsdGeom,UsdShade,Gf
from inspect_asset_contract import inspect,prepare,sha,date_provenance

class AssetContractTests(unittest.TestCase):
    def test_retrieval_is_exact_request_not_build_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            (root/'data/footprint_manifest.json').write_text(json.dumps({'created_utc':'new-build-time','requests':[{'url':'https://example.gov/query?objectIds=17,19','retrieved_utc':'original-time','retrieval_quality':'network_response'}]}))
            result=date_provenance(root,{'source_feature_ids':['17','18'],'valid_time':{'start':None,'quality':'unknown'}})
            self.assertEqual(result['requests'][0]['retrieved_utc'],'original-time')
            self.assertEqual(result['requests'][0]['source_feature_ids'],['17'])
            self.assertEqual(result['source_ids_without_retained_request'],['18'])
    def test_world_scale_material_and_invalid_geometry(self):
        stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
        parent=UsdGeom.Xform.Define(stage,'/World');parent.AddTranslateOp().Set((7,8,9))
        mesh=UsdGeom.Mesh.Define(stage,'/World/Building');mesh.CreatePointsAttr([(0,0,0),(1,0,1),(0,1,0)])
        report=inspect(stage,mesh.GetPrim());self.assertEqual(report['world_bounds_m'],[[7,8,9],[8,9,10]])
        self.assertIn('no_material_or_display_color:/World/Building',report['warnings'])
        material=UsdShade.Material.Define(stage,'/World/Material');UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)
        self.assertIn('unresolved_material_surface:/World/Material',inspect(stage,mesh.GetPrim())['errors'])
        mesh.GetPointsAttr().Set([(float('nan'),0,0)])
        self.assertIn('nonfinite_world_point',inspect(stage,mesh.GetPrim())['errors'])

    def test_isolated_copy_preserves_identity_transforms_and_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'scene').mkdir();(root/'data/processed').mkdir(parents=True);(root/'data/heights').mkdir()
            source=root/'scene/college_park_connected.usda';stage=Usd.Stage.CreateNew(str(source));UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
            world=UsdGeom.Xform.Define(stage,'/World');world.AddTranslateOp().Set((7,8,9))
            group=UsdGeom.Xform.Define(stage,'/World/Buildings')
            mesh=UsdGeom.Mesh.Define(stage,'/World/Buildings/Building_0665');mesh.CreatePointsAttr([(0,0,0),(1,0,1),(0,1,0)]);mesh.CreateDisplayColorAttr([(1,1,1)])
            mesh.GetPrim().SetCustomDataByKey('twin',{'entityId':'entity1','sourceSnapshot':'s1'});stage.GetRootLayer().Save()
            (root/'scene/college_park.usda').write_bytes(source.read_bytes());(root/'data/heights/building_heights.json').write_text('[]')
            row={'local_building_id':'Building_0665','entity_id':'entity1','usd_path':str(mesh.GetPath()),'observation_kind':'estimated'}
            for path,data in [(root/'data/processed/active.json',{'snapshot':'s1'}),(root/'data/processed/asset_registry.json',{'source_snapshot':'s1','base_geometry_sha256':sha(root/'scene/college_park.usda'),'height_evidence_sha256':sha(root/'data/heights/building_heights.json'),'records':[row]})]:path.write_text(json.dumps(data))
            before=sha(source);out=root/'data/diagnostics/pilot';report=prepare(root,out)
            self.assertEqual(sha(source),before);self.assertFalse(report['accepted']);self.assertEqual(report['inspection']['errors'],[])
            self.assertEqual(report['inspection']['world_bounds_m'],[[7,8,9],[8,9,10]])
            copy=Usd.Stage.Open(str(out/report['pilot_path']));self.assertEqual(copy.GetPrimAtPath(row['usd_path']).GetCustomDataByKey('twin:entityId'),'entity1')
            self.assertEqual(copy.GetPrimAtPath(row['usd_path']).GetAttribute('semantics:labels:cityscapes').Get(),['building'])
            with self.assertRaisesRegex(ValueError,'already exists'):prepare(root,out)
            with self.assertRaisesRegex(ValueError,'below data/diagnostics'):prepare(root,root/'scene/forbidden')

if __name__=='__main__':unittest.main()
