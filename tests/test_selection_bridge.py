from pathlib import Path
import concurrent.futures,http.client,json,os,sys,tempfile,threading,unittest
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'.dependencies'))
from selection_bridge import read_state,publish,load_context,resolve_selection,SelectionError,valid_origin,validate_payload,acknowledge,counterpart_paths,selection_identity

class SelectionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.processed=self.root/'data/processed';self.processed.mkdir(parents=True)
        folder=self.root/'data/snapshots/s1';folder.mkdir(parents=True)
        self.write(self.processed/'active.json',{'snapshot':'s1','relative_path':'data/snapshots/s1'})
        features=[{'id':'ocpa:'+letter,'properties':{'id':'ocpa:'+letter,'parcel_id':'SAME-PIN'},'geometry':None} for letter in ('a','b','condo')]
        self.write(folder/'parcels.json',{'type':'FeatureCollection','features':features})
        self.records=[{'entity_id':'e1','local_building_id':'B1','source_snapshot':'s1','parcel_feature_id':'ocpa:a','parcel_link_accepted':True,'usd_path':'/World/Buildings/B1'},
                      {'entity_id':'e2','local_building_id':'B2','source_snapshot':'s1','parcel_feature_id':'ocpa:b','parcel_link_accepted':False,'usd_path':'/World/Buildings/B2'},
                      {'entity_id':'e3','local_building_id':'B3','source_snapshot':'s1','parcel_feature_id':'ocpa:a','parcel_link_accepted':True,'usd_path':'/World/Buildings/B3'}]
        self.write(self.processed/'asset_registry.json',{'source_snapshot':'s1','records':self.records})
    def tearDown(self):self.temp.cleanup()
    def write(self,path,data):path.write_text(json.dumps(data),encoding='utf-8')
    def payload(self,packet=None,**change):
        packet=packet or read_state(self.root)
        payload={'epoch':packet['epoch'],'snapshot':packet['snapshot'],'expected_revision':packet['revision'],'sender':'map','feature_id':'ocpa:a'};payload.update(change);return payload

    def test_exact_feature_preserves_duplicate_pin_and_condos(self):
        context=load_context(self.root)
        self.assertEqual(resolve_selection(context,'ocpa:a')['paths'],['/World/Buildings/B1','/World/Buildings/B3'])
        self.assertEqual(resolve_selection(context,'ocpa:b')['status'],'unmatched')
        self.assertEqual(resolve_selection(context,'ocpa:condo')['status'],'unmatched')
        self.assertEqual(resolve_selection(context,entity_id='e2')['feature_id'],None)
        self.assertEqual(resolve_selection(context,entity_id='e1')['feature_id'],'ocpa:a')
        with self.assertRaises(SelectionError):resolve_selection(context,'SAME-PIN')

    def test_stale_epoch_revision_snapshot_and_ack_rejected(self):
        packet=read_state(self.root);first=publish(self.payload(packet),self.root)
        self.assertEqual(first['revision'],1)
        for change in ({},{'epoch':'stale'},{'snapshot':'old'}):
            with self.assertRaises(SelectionError) as error:publish(self.payload(packet,**change),self.root)
            self.assertEqual(error.exception.status,409)
        with self.assertRaises(SelectionError):acknowledge(packet,'selected-in-editor','old',self.root)
        reset=read_state(self.root,reset=True);self.assertNotEqual(reset['epoch'],packet['epoch'])
        self.assertEqual(reset['revision'],0)

    def test_racing_writes_are_atomic_and_compare_revision(self):
        packet=read_state(self.root);payload=self.payload(packet)
        def worker(_):
            try:return publish(payload,self.root)['revision']
            except SelectionError:return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(4) as pool:results=list(pool.map(worker,range(4)))
        self.assertEqual(results.count(1),1);self.assertEqual(results.count('conflict'),3)
        current=json.loads((self.processed/'selection_bridge.json').read_text());self.assertEqual(current['revision'],1)
        self.assertEqual(list(self.processed.glob('selection-*.tmp')),[])

    def test_small_strict_payload_and_origin(self):
        for bad in ([],{},self.payload(expected_revision=True),self.payload(feature_id=[]),self.payload(path='/evil'),self.payload(feature_id='x'*257),self.payload(sender='external')):
            with self.assertRaises(SelectionError):validate_payload(bad)
        self.assertTrue(valid_origin('http://127.0.0.1:8768','127.0.0.1:8768',8768,'127.0.0.1'))
        for origin,host,client in [('https://127.0.0.1:8768','127.0.0.1:8768','127.0.0.1'),('http://evil.test:8768','evil.test:8768','127.0.0.1'),('null','127.0.0.1:8768','127.0.0.1'),('http://127.0.0.1:8768','127.0.0.1:8768','192.0.2.1')]:self.assertFalse(valid_origin(origin,host,8768,client))

    def test_stale_registry_fails_closed(self):
        self.write(self.processed/'asset_registry.json',{'source_snapshot':'old','records':self.records})
        with self.assertRaises(SelectionError):read_state(self.root)

    def test_editor_counterparts_validate_actual_entity_and_snapshot(self):
        from pxr import Usd,UsdGeom
        stage=Usd.Stage.CreateInMemory();prim=UsdGeom.Xform.Define(stage,'/World/Buildings/B1').GetPrim()
        prim.SetCustomDataByKey('twin',{'entityId':'e1','sourceSnapshot':'s1'})
        child=UsdGeom.Cube.Define(stage,'/World/Buildings/B1/Window').GetPrim()
        packet=publish(self.payload(),self.root);context=load_context(self.root)
        self.assertEqual(selection_identity(child,context),{'entity_id':'e1'})
        roof_body=UsdGeom.Xform.Define(stage,'/World/Buildings/Building_0001').GetPrim()
        roof_body.SetCustomDataByKey('twin',{'entityId':'e1','sourceSnapshot':'s1'})
        roof=UsdGeom.Mesh.Define(stage,'/World/Roofs/Roof_0001').GetPrim()
        self.assertEqual(selection_identity(roof,context),{'entity_id':'e1'})
        from workspace_evidence import inspector_text
        self.assertIn('Entity: e1',inspector_text(roof))
        self.assertIn('Selected: /World/Roofs/Roof_0001',inspector_text(roof))
        roof_body.SetCustomDataByKey('twin',{'entityId':'e1','sourceSnapshot':'old'})
        self.assertEqual(selection_identity(roof,context),{'entity_id':'unregistered-selection'})
        self.assertEqual(counterpart_paths(stage,packet,context),['/World/Buildings/B1'])
        prim.SetCustomDataByKey('twin',{'entityId':'e1','sourceSnapshot':'old'})
        self.assertEqual(counterpart_paths(stage,packet,context),[])
        unrelated=UsdGeom.Cube.Define(stage,'/World/Storefronts/Guess').GetPrim()
        unrelated.SetCustomDataByKey('parcelId','SAME-PIN')
        self.assertEqual(selection_identity(unrelated,context),{'entity_id':'unregistered-selection'})

    def test_http_selection_only_origin_and_payload_guards(self):
        import serve
        from http.server import ThreadingHTTPServer
        previous=serve.ROOT;serve.ROOT=self.root
        server=ThreadingHTTPServer(('127.0.0.1',0),serve.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        port=server.server_address[1]
        def request(path,body,headers):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            try:conn.request('POST',path,body,headers);response=conn.getresponse();response.read();return response.status
            finally:conn.close()
        try:
            body=json.dumps(self.payload());headers={'Origin':f'http://127.0.0.1:{port}','Content-Type':'application/json'}
            self.assertEqual(request('/api/v1/selection',body,headers),200)
            self.assertEqual(request('/api/v1/parcels',body,headers),405)
            self.assertEqual(request('/api/v1/selection',body,{'Content-Type':'application/json'}),403)
            self.assertEqual(request('/api/v1/selection','x'*2049,headers),413)
            self.assertEqual(request('/api/v1/selection','[]',headers),400)
            self.assertEqual(request('/api/v1/selection','{bad',headers),400)
        finally:server.shutdown();server.server_close();thread.join();serve.ROOT=previous

if __name__=='__main__':unittest.main()
