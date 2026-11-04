import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pxr import Usd,UsdGeom
from semantic_registry import building_identity,sha,SCHEMA,PROFILE
from validate_scene import validate

class SceneValidationIntegrationTests(unittest.TestCase):
 def fixture(self,folder,corrupt_instance=False):
  r=Path(folder);(r/'scene').mkdir();(r/'data/processed').mkdir(parents=True);(r/'data/snapshots/s1').mkdir(parents=True);(r/'data/heights').mkdir()
  p=r/'scene/college_park.usda';s=Usd.Stage.CreateNew(str(p));UsdGeom.SetStageMetersPerUnit(s,1);UsdGeom.SetStageUpAxis(s,'Z')
  m=UsdGeom.Mesh.Define(s,'/World/B1');m.CreatePointsAttr([(0,0,4.3),(1,0,4.3),(0,1,4.3)]);m.CreateFaceVertexCountsAttr([3]);m.CreateFaceVertexIndicesAttr([0,1,2])
  key=building_identity(['01']);m.GetPrim().SetCustomDataByKey('twin',{'entityId':key,'validationProfile':PROFILE})
  if corrupt_instance:
   a=Usd.Stage.CreateNew(str(r/'scene/asset.usda'));x=UsdGeom.Xform.Define(a,'/Asset');q=UsdGeom.Mesh.Define(a,'/Asset/BadMesh');q.CreatePointsAttr([(0,0,0),(1,0,0),(0,1,0)]);q.CreateFaceVertexCountsAttr([3]);q.CreateFaceVertexIndicesAttr([0,1,99]);a.GetRootLayer().Save()
   i=UsdGeom.Xform.Define(s,'/World/Instance').GetPrim();i.GetReferences().AddReference('asset.usda','/Asset');i.SetInstanceable(True)
  s.GetRootLayer().Save();a=Usd.Stage.CreateNew(str(r/'scene/college_park_connected.usda'));a.GetRootLayer().subLayerPaths=['college_park.usda'];UsdGeom.SetStageMetersPerUnit(a,1);UsdGeom.SetStageUpAxis(a,'Z');a.GetRootLayer().Save()
  active={'snapshot':'s1','relative_path':'data/snapshots/s1'};(r/'data/processed/active.json').write_text(json.dumps(active))
  (r/'data/snapshots/s1/buildings.json').write_text(json.dumps([{'id':'B1','usd_path':'/World/B1'}]));(r/'data/heights/building_heights.json').write_text('[]')
  row={'schema':SCHEMA,'entity_id':key,'local_building_id':'B1','usd_path':'/World/B1','height_m':4.2,'source_snapshot':'s1','source_feature_ids':['01'],'observation_kind':'estimated'}
  registry={'source_snapshot':'s1','base_geometry_sha256':sha(p),'height_evidence_sha256':sha(r/'data/heights/building_heights.json'),'records':[row]};(r/'data/processed/asset_registry.json').write_text(json.dumps(registry));return r,registry
 def write_registry(self,r,d):(r/'data/processed/asset_registry.json').write_text(json.dumps(d))
 def test_current_scene_passes(self):
  with tempfile.TemporaryDirectory() as d:
   r,_=self.fixture(d);self.assertTrue(validate(r,verbose=False)['passed_local_profile'])
 def test_stale_geometry_and_height_hashes_fail(self):
  with tempfile.TemporaryDirectory() as d:
   r,data=self.fixture(d);data.update(base_geometry_sha256='wrong',height_evidence_sha256='wrong');self.write_registry(r,data)
   codes={e['code'] for e in validate(r,verbose=False)['errors']};self.assertTrue({'base_geometry_hash_stale','height_evidence_hash_stale'}<=codes)
 def test_missing_registry_coverage_fails(self):
  with tempfile.TemporaryDirectory() as d:
   r,data=self.fixture(d);data['records']=[];self.write_registry(r,data);self.assertIn('registry_coverage_mismatch',{e['code'] for e in validate(r,verbose=False)['errors']})
 def test_changed_profile_fails(self):
  with tempfile.TemporaryDirectory() as d:
   r,data=self.fixture(d);s=Usd.Stage.Open(str(r/'scene/college_park.usda'));s.GetPrimAtPath('/World/B1').SetCustomDataByKey('twin:validationProfile','different');s.GetRootLayer().Save();data['base_geometry_sha256']=sha(r/'scene/college_park.usda');self.write_registry(r,data)
   self.assertIn('semantic_profile_mismatch',{e['code'] for e in validate(r,verbose=False)['errors']})
 def test_invalid_instanced_mesh_is_checked(self):
  with tempfile.TemporaryDirectory() as d:
   r,_=self.fixture(d,True);report=validate(r,verbose=False);self.assertEqual(report['instance_proxy_meshes_checked'],1);self.assertIn('face_index_out_of_range',{e['code'] for e in report['errors']})

if __name__=='__main__':unittest.main()
