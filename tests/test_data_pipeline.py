import unittest,sys,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from data_pipeline import clean_pin,normalize_parcels,Client,arcgis,socrata

class DataContractTests(unittest.TestCase):
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
