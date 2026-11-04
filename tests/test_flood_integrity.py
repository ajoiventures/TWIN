import sys,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'.dependencies')]
from build_flood_overlay import validate_packet
from verify_retail_block import save,sha
class FloodPacketIntegrityTests(unittest.TestCase):
 def test_packet_only_mutation_and_empty_guards_fail(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);save(root/'data/processed/active.json',{'snapshot':'s1'});source=root/'source.json';source.write_text('source');artifact=root/'overlay.usda';artifact.write_text('overlay')
   path=root/'data/flood/effective_nfhl.json';receipt=root/'data/flood/effective_nfhl.receipt.json';packet={'source_snapshot':'s1','dependencies':{'source.json':sha(source)},'artifacts':{'overlay.usda':sha(artifact)},'tables':{'zone':'AE'}}
   def publish():
    save(path,packet);save(receipt,{'source_snapshot':'s1','packet_path':'data/flood/effective_nfhl.json','packet_sha256':sha(path)})
   publish();self.assertEqual(validate_packet(root)['tables']['zone'],'AE')
   packet['tables']['zone']='X';save(path,packet)
   with self.assertRaisesRegex(ValueError,'normalized packet'):validate_packet(root)
   publish();packet['dependencies']={};publish()
   with self.assertRaisesRegex(ValueError,'checksums required'):validate_packet(root)
   packet['dependencies']={'source.json':sha(source)};packet['artifacts']={};publish()
   with self.assertRaisesRegex(ValueError,'checksums required'):validate_packet(root)
if __name__=='__main__':unittest.main()
