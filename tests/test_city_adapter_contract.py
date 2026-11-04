from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from city_adapter_contract import CheckedClient,fetch_arcgis,normalize

class Fake:
 def __init__(self,responses):self.responses=iter(responses)
 def get(self,*args):
  value=next(self.responses)
  if isinstance(value,Exception):raise value
  return value

class CityContractTests(unittest.TestCase):
 def test_schema_failure_malformed_empty_and_service_errors(self):
  source={'url':'https://example.invalid/0','fields':['OBJECTID'],'oid':'OBJECTID'}
  for value in ({'fields':[]},TimeoutError('outage')):
   with self.assertRaises((ValueError,TimeoutError)):fetch_arcgis(Fake([value]),source,[-82,28,-81,29])
  for response in ({},{'error':{'message':'unavailable'}}):
   with self.assertRaises(ValueError):CheckedClient(Fake([response])).get('url',{'returnIdsOnly':'true'})
  rows,_=fetch_arcgis(Fake([{'fields':[{'name':'OBJECTID'}]},{'objectIds':[]}]),source,[-82,28,-81,29]);self.assertEqual(rows['features'],[])
 def test_safe_fields_geometry_and_string_ids(self):
  source={'fields':['OBJECTID','optional'],'oid':'OBJECTID'}
  rows=[]
  for ident,geometry in [('0001',{'type':'Point','coordinates':[28.5,-81.3]}),('0002',{'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}),('0003',None)]:rows.append({'properties':{'OBJECTID':ident,'unsafe_notes':'SECRET'},'geometry':geometry})
  normalized,q=normalize('addresses',{'features':rows},source,[-82,28,-81,29]);self.assertEqual(normalized[0]['source_id'],'0001');self.assertEqual(len(q['issues']),3);self.assertNotIn('SECRET',str(normalized));self.assertIsNone(normalized[1]['geometry']);self.assertEqual(normalized[0]['missing_optional_fields'],['optional'])
  rows.append(rows[0])
  with self.assertRaises(ValueError):normalize('addresses',{'features':rows},source,[-82,28,-81,29])
 def test_license_case_does_not_replace_original_row_identity(self):
  source={'fields':['case_number']};rows=[{'case_number':'SAME','source_row_id':key} for key in ('001','002')];out,q=normalize('businesses',rows,source,[-82,28,-81,29]);self.assertEqual(len({r['entity_id'] for r in out}),2);self.assertFalse(q['empty_response']);self.assertTrue(normalize('businesses',[],source,[-82,28,-81,29])[1]['empty_response'])

if __name__=='__main__':unittest.main()
