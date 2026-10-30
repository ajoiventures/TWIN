import unittest,sys,tempfile,json,io,urllib.error
from unittest import mock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import data_pipeline
from data_pipeline import clean_pin,normalize_parcels,Client,arcgis,socrata,building_joins

class DataContractTests(unittest.TestCase):
 def feature(self,**props):
  p={'OBJECTID':1,'PARCEL':'00123','STYS':2,'AYB':2002,'OWNER':'PRIVATE'};p.update(props)
  return {'type':'Feature','properties':p,'geometry':{'type':'Polygon','coordinates':[[[-81.39,28.57],[-81.389,28.57],[-81.389,28.571],[-81.39,28.57]]]}}
 def test_malformed_optional_attributes_are_unknown_without_row_loss(self):
  for stories,year in [('not a count','bad year'),(True,True),(float('inf'),float('nan'))]:
   rows,rejects=normalize_parcels({'features':[self.feature(STYS=stories,AYB=year,ACREAGE='bad')]})
   self.assertFalse(rejects);p=rows['features'][0]['properties'];self.assertIsNone(p['stories']);self.assertIsNone(p['year_built']);self.assertIsNone(p['area_acres']);self.assertNotIn('OWNER',p);self.assertTrue(p['attribute_quality_flags'])
 def test_missing_source_id_and_swapped_coordinates_quarantined(self):
  feature=self.feature();del feature['properties']['OBJECTID']
  swapped=self.feature();swapped['geometry']['coordinates']=[[[28.57,-81.39],[28.57,-81.389],[28.571,-81.389],[28.57,-81.39]]]
  rows,rejects=normalize_parcels({'features':[feature,swapped]});self.assertFalse(rows['features']);self.assertEqual(len(rejects),2)
 def test_cache_hash_mismatch_fails_closed(self):
  with tempfile.TemporaryDirectory() as folder:
   client=Client(folder,opener=lambda *a,**kw:io.StringIO('{"value":1}'));client.get('https://example.invalid')
   cache=next(p for p in Path(folder).glob('*.json') if not p.name.endswith('.provenance.json'));cache.write_text('{"value":2}')
   with self.assertRaisesRegex(ValueError,'checksum mismatch'):Client(folder,offline=True).get('https://example.invalid')
 def test_retry_timeout_backoff_and_original_retrieval_receipt(self):
  calls=[];waits=[]
  def opener(request,timeout):
   calls.append(timeout)
   if len(calls)<3:raise urllib.error.HTTPError(request.full_url,429,'retry',None,None)
   return io.StringIO('{"ok":true}')
  with tempfile.TemporaryDirectory() as folder:
   client=Client(folder,opener=opener,sleeper=waits.append);client.get('https://example.invalid');stamp=client.accesses[0]['retrieved_utc']
   offline=Client(folder,offline=True,opener=lambda *a,**k:self.fail('network'));offline.get('https://example.invalid')
   self.assertEqual(calls,[60,60,60]);self.assertEqual(waits,[1,2]);self.assertEqual(offline.accesses[0]['retrieved_utc'],stamp)
 def test_source_outage_preserves_active_snapshot(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);pointer=root/'data/processed/active.json';pointer.parent.mkdir(parents=True);pointer.write_text('{"snapshot":"previous","relative_path":"data/snapshots/previous"}');before=pointer.read_bytes()
   with mock.patch.object(data_pipeline,'ROOT',root),mock.patch('urllib.request.urlopen',side_effect=urllib.error.URLError('outage')),mock.patch('time.sleep'):
    with self.assertRaises(urllib.error.URLError):data_pipeline.refresh(force=True)
   self.assertEqual(pointer.read_bytes(),before)
 def join_fixture(self,folder):
  from pxr import Usd,UsdGeom
  from pyproj import Transformer
  path=Path(folder)/'base.usda';stage=Usd.Stage.CreateNew(str(path));mesh=UsdGeom.Mesh.Define(stage,'/World/Buildings/B1')
  mesh.CreatePointsAttr([(0,0,4),(10,0,4),(10,10,4),(0,10,4)]);mesh.CreateFaceVertexCountsAttr([3,3]);mesh.CreateFaceVertexIndicesAttr([0,1,2,0,2,3]);mesh.GetPrim().SetCustomData({'parcelId':'00123','buildingNumber':'01','sourceObjectIds':'11,12','heightMeters':4.2});stage.GetRootLayer().Save()
  t=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=t.transform(-81.389,28.572);inverse=Transformer.from_crs(32617,4326,always_xy=True)
  def parcel(feature,offset=0):return {'type':'Feature','properties':{'id':feature,'parcel_id':'00123','stories':2},'geometry':{'type':'Polygon','coordinates':[[inverse.transform(ox+x+offset,oy+y) for x,y in [(-1,-1),(11,-1),(11,11),(-1,11),(-1,-1)]]]}}
  return path,parcel
 def test_duplicate_exact_features_never_pick_first(self):
  with tempfile.TemporaryDirectory() as folder:
   path,parcel=self.join_fixture(folder);row=building_joins({'features':[parcel('ocpa:1'),parcel('ocpa:2')]},path)[0]
   self.assertEqual(row['join_state'],'ambiguous');self.assertIsNone(row['parcel_feature_id']);self.assertEqual(len(row['candidate_parcel_features']),2);self.assertEqual(row['candidate_parcels'],['00123'])
 def test_geometry_update_recomputes_join_without_changing_source_identity(self):
  with tempfile.TemporaryDirectory() as folder:
   path,parcel=self.join_fixture(folder);first=building_joins({'features':[parcel('ocpa:1')]},path)[0];second=building_joins({'features':[parcel('ocpa:1',100)]},path)[0]
   self.assertEqual(first['join_state'],'accepted');self.assertEqual(second['join_state'],'unmatched');self.assertEqual(first['source_building_key'],second['source_building_key']);self.assertEqual(first['source_building_number'],'01');self.assertEqual(first['source_object_ids'],['11','12'])
 def test_identifier_keeps_leading_zeroes(self):
  self.assertEqual(clean_pin('00-12 34'),'001234')
  self.assertEqual(clean_pin(None),'')
 def test_zero_stories_and_year_are_unknown(self):
  feature={'type':'Feature','geometry':{'type':'Polygon','coordinates':[[[-81.39,28.57],[-81.389,28.57],[-81.389,28.571],[-81.39,28.57]]]},'properties':{'OBJECTID':1,'PARCEL':'00123','STYS':0,'AYB':0}}
  result,rejects=normalize_parcels({'features':[feature]})
  p=result['features'][0]['properties'];self.assertIsNone(p['stories']);self.assertIsNone(p['year_built']);self.assertEqual(p['parcel_id'],'00123');self.assertFalse(rejects)
 def test_invalid_geometry_is_quarantined(self):
  result,rejects=normalize_parcels({'features':[{'properties':{'OBJECTID':1,'PARCEL':'123'},'geometry':None}]})
  self.assertEqual(len(result['features']),0);self.assertEqual(len(rejects),1)
 def test_offline_miss_does_not_contact_source(self):
  with tempfile.TemporaryDirectory() as folder:
   c=Client(folder,offline=True,opener=lambda *a,**k:self.fail('network called'))
   with self.assertRaisesRegex(RuntimeError,'Offline cache miss'):c.get('https://example.invalid')
 def test_arcgis_schema_change_fails(self):
  class Stub:
   def get(self,*a):return {'fields':[{'name':'OBJECTID'}]}
  with self.assertRaisesRegex(ValueError,'Schema change'):arcgis(Stub(),{'url':'https://example.invalid','fields':['OBJECTID','PARCEL'],'oid':'OBJECTID'})
 def test_arcgis_missing_batch_is_detected(self):
  class Stub:
   def get(self,url,params):
    if not url.endswith('/query'):return {'fields':[{'name':'OBJECTID'}]}
    if params.get('returnIdsOnly'):return {'objectIds':[1,2]}
    return {'features':[{'properties':{'OBJECTID':1}}]}
  with self.assertRaisesRegex(ValueError,'count mismatch'):arcgis(Stub(),{'url':'https://example.invalid','fields':['OBJECTID'],'oid':'OBJECTID'})
 def test_business_case_is_not_the_source_row_identifier(self):
  class Stub:
   def get(self,url,params=None):
    if '/api/views/' in url:return {'columns':[{'fieldName':'case_number'}]}
    return [{'case_number':'BUS1','source_row_id':'a'},{'case_number':'BUS1','source_row_id':'b'}]
  rows,_=socrata(Stub(),{'dataset':'test','url':'https://example.invalid','fields':['case_number']},'1=1')
  self.assertEqual(len(rows),2)
 def test_duplicate_source_row_is_detected(self):
  class Stub:
   def get(self,url,params=None):
    if '/api/views/' in url:return {'columns':[{'fieldName':'case_number'}]}
    return [{'case_number':'BUS1','source_row_id':'a'},{'case_number':'BUS1','source_row_id':'a'}]
  with self.assertRaisesRegex(ValueError,'duplicate source rows'):socrata(Stub(),{'dataset':'test','url':'https://example.invalid','fields':['case_number']},'1=1')

if __name__=='__main__':unittest.main()
