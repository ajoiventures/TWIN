import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.dependencies')]
import verify_retail_block as retail
from register_reconstructions import retail_registration_record
from review_corridor_buildings import reconstruction_context_index
from serve import page_table,matches_parcel_id
from pxr import Usd,UsdGeom
from PIL import Image

class RetailActivationTests(unittest.TestCase):
 def fixture(self,folder):
  root=Path(folder)
  for p in ['data/processed','data/heights/retail_edgewater','scene','data/renders/proof']:(root/p).mkdir(parents=True,exist_ok=True)
  retail.save(root/'data/processed/active.json',{'snapshot':'s1','relative_path':'data/snapshots/s1'})
  proposal=root/'scene/retail_block_reconstruction_proposal.usda';stage=Usd.Stage.CreateNew(str(proposal));stage.GetRootLayer().customLayerData={'sourceSnapshot':'s1'}
  prim=UsdGeom.Xform.Define(stage,retail.RETAIL_PRIM).GetPrim();prim.SetCustomDataByKey('parcelIds',','.join(retail.PINS))
  from correct_wellesley import mesh_geometry
  from shapely.geometry import box
  points,counts,indices=mesh_geometry([(box(0,0,2,2),0,3)])
  mesh=UsdGeom.Mesh.Define(stage,retail.RETAIL_PRIM+'/RoofDerivedBlock');mesh.CreatePointsAttr(points);mesh.CreateFaceVertexCountsAttr(counts);mesh.CreateFaceVertexIndicesAttr(indices);stage.GetRootLayer().Save()
  source=root/'data/source.json';source.write_text('source');manual=root/'scene/manual.usda';manual.write_text('manual camera opinion')
  report={'source_snapshot':'s1','parcel_ids':retail.PINS,'layer':'scene/'+proposal.name,'layer_sha256':retail.sha(proposal),'dependencies':{'data/source.json':retail.sha(source),'scene/manual.usda':retail.sha(manual)},'camera':'/World/Cameras/Test','height_main_roof_m':3,'maximum_rendered_height_m':3,'roof_footprint_area_m2':4,'per_parcel_coverage':[],'original_acquisition':{'year':2019},'source_points_sha256':'a'*64,'limits':['historical draft']}
  retail.save(root/'data/heights/retail_edgewater/verification.json',report)
  image=root/'data/renders/proof/image.png';Image.new('RGB',(8,8)).save(image)
  render={'source_snapshot':'s1','proposal_layer':proposal.name,'camera':report['camera'],'layer_hashes':{'scene/'+proposal.name:retail.sha(proposal),'scene/manual.usda':retail.sha(manual)},'image':'data/renders/proof/image.png','image_sha256':retail.sha(image),'requested_resolution':[8,8]}
  path=root/'data/renders/proof/manifest.json';retail.save(path,render)
  return root,'data/renders/proof/manifest.json',retail.sha(path)
 def test_prepare_no_writes_then_activation_preserves_manual(self):
  with tempfile.TemporaryDirectory() as d:
   root,render,digest=self.fixture(d);before=(root/'scene/manual.usda').read_bytes();packet=retail.prepare_activation(root,render,digest)
   self.assertTrue(packet['prepared_only']);self.assertFalse((root/'scene/retail_block.usda').exists())
   packet=retail.activate(root,render,digest);self.assertEqual(retail.validate_active_retail(root)['rendered_entity_count'],1);self.assertEqual((root/'scene/manual.usda').read_bytes(),before)
   record=retail_registration_record(packet);self.assertFalse(record['raw_property_links_promoted']);self.assertEqual(len(reconstruction_context_index([record])),6)
   retail.save(root/'data/processed/reconstructions.json',{'source_snapshot':'s1','dependencies':{},'records':[record]})
   for pid in retail.PINS:self.assertEqual(page_table('reconstructions',{'parcel_id':[pid]},root)['rows'][0]['id'],record['id'])
   self.assertEqual(page_table('reconstructions',{},root)['total'],1)
   (root/'scene/retail_block.usda').write_text('manual active edit')
   with self.assertRaisesRegex(ValueError,'manual changes'):retail.activate(root,render,digest)
 def test_changed_evidence_proof_and_escape_fail_closed(self):
  for target in ['data/source.json','scene/retail_block_reconstruction_proposal.usda','data/renders/proof/image.png','data/renders/proof/manifest.json']:
   with self.subTest(target=target),tempfile.TemporaryDirectory() as d:
    root,render,digest=self.fixture(d);(root/target).write_bytes(b'changed')
    with self.assertRaises(ValueError):retail.prepare_activation(root,render,digest)
    self.assertFalse((root/'scene/retail_block.usda').exists())
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):retail.inside(Path(d),'../escape')
 def test_open_shell_rejected_even_with_matching_review_hashes(self):
  with tempfile.TemporaryDirectory() as d:
   root,render,digest=self.fixture(d);proposal=root/'scene/retail_block_reconstruction_proposal.usda'
   stage=Usd.Stage.Open(str(proposal));mesh=UsdGeom.Mesh(stage.GetPrimAtPath(retail.RETAIL_PRIM+'/RoofDerivedBlock'))
   counts=list(mesh.GetFaceVertexCountsAttr().Get());indices=list(mesh.GetFaceVertexIndicesAttr().Get());mesh.GetFaceVertexCountsAttr().Set(counts[1:]);mesh.GetFaceVertexIndicesAttr().Set(indices[counts[0]:]);stage.GetRootLayer().Save()
   path=root/'data/heights/retail_edgewater/verification.json';report=retail.read(path);report['layer_sha256']=retail.sha(proposal);retail.save(path,report)
   path=root/render;proof=retail.read(path);proof['layer_hashes']['scene/'+proposal.name]=retail.sha(proposal);retail.save(path,proof)
   with self.assertRaisesRegex(ValueError,'open shell'):retail.prepare_activation(root,render,retail.sha(path))
   self.assertFalse((root/'scene/retail_block.usda').exists())
 def test_exact_context_matching(self):
  self.assertTrue(matches_parcel_id({'parcel_ids':['001','002']},'001'));self.assertFalse(matches_parcel_id({'parcel_ids':['001','002']},'1'))
  with self.assertRaises(ValueError):reconstruction_context_index([{'id':'a','parcel_id':'001'},{'id':'b','parcel_id':'001'}])

if __name__=='__main__':unittest.main()

