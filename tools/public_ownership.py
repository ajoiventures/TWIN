"""Full-neighborhood government assessment references; no owner-name access."""
from pathlib import Path
import os,sys,json,hashlib,collections,datetime,shutil,urllib.request
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import Client,SOURCES,arcgis,socrata,atomic_json,now,clean_pin
from city_adapter_contract import CheckedClient
from review_land import city_pin
import shapely
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from pyproj import Transformer
OUT='data/processed/public_ownership';API='https://ocpa-mainsite-afd-standard.azurefd.net/'
COUNTY_URL='https://services1.arcgis.com/0U8EQ1FrumPeIqDb/arcgis/rest/services/Orange_County_Owned_Buildings/FeatureServer/0'
GROUPS={
 'government_level_unspecified':['8000','8007','8100','8200','8238'],
 'water_management_district':['8010'],
 'county':['8060','8063','8064','8065','8066','8067','8068','8069','8286','8600','8610','8620'],
 'state':['8070','8073','8074','8075','8076','8077','8078','8079','8287','8700','8710','8798'],
 'federal':['8080','8288','8800'],
 'municipal':['8090','8093','8094','8095','8096','8097','8098','8099','8289','8900','8910','8920','8980','8981'],
 'school_district_reference':['8300'],'public_college_level_unspecified':['8400'],'public_hospital_level_unspecified':['8500'],
 'regional_expressway_authority':['8088'],'municipal_government_leasehold_reference':['9000','9011','9017','9048']}
RULES={code:group for group,codes in GROUPS.items() for code in codes}
EXPECTED_DEFINITIONS={'8000': 'Govt Vacant Land', '8007': 'Public Cemetery', '8010': 'Water Mgmt District Vac Land', '8060': 'County Vacant Land', '8063': 'County Conservation/Wetland', '8064': 'County Mitigation', '8065': 'County Stormwater/Retention', '8066': 'County Landscape/Wall Buffer', '8067': 'County Trails And Access', '8068': 'County Right-Of-Way', '8069': 'County Submerged', '8070': 'State Vacant Land', '8073': 'State Conservation/Wetland', '8074': 'State Mitigation', '8075': 'State Stormwater/Retention', '8076': 'State Landscape/Wall Buffer', '8077': 'State Trails And Access', '8078': 'State Right-Of-Way', '8079': 'State Submerged', '8080': 'Federal Vacant Land', '8088': 'Central Fl Expy Authority', '8090': 'Muni Vacant Land', '8093': 'Muni Conservation/Wetland', '8094': 'Muni Mitigation', '8095': 'Muni Stormwater/Retention', '8096': 'Muni Landscape/Wall Buffer', '8097': 'Muni Trails And Access', '8098': 'Muni Right-Of-Way', '8099': 'Muni Submerged', '8100': 'Military', '8200': 'Forest, Parks, Recreation', '8238': 'Public Golf Course', '8286': 'County Forest, Parks, Recreation', '8287': 'State Forest Park Recreation', '8288': 'Federal Forest Park Recreation', '8289': 'Municipal Forest Park Recreation', '8300': 'Public County School', '8400': 'Public College', '8500': 'Public Hospital', '8600': 'County (Other Bldg)', '8610': 'County Multi Use Facility', '8620': 'County Utility-Gas, Electric', '8700': 'State (Other Bldg)', '8710': 'State Muilti-Use Facility', '8798': 'State Commuter Rail', '8800': 'Federal (Other)', '8900': 'Municipal (Other)', '8910': 'Municipal Airport', '8920': 'Muni Utility, Gas, Electric', '8980': 'Municipal Multi-Use Fclty I', '8981': 'Municipal Multi-Use Fclty Ii', '9000': 'Municipal Lease - Other', '9011': 'Municipal Lease Retail', '9017': 'Municipal Lease Office', '9048': 'Municial Lease Warehouse'}

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transform(fn,g):return shapely.transform(g,fn,interleaved=False)

FDOR_REVIEWED_SHA256='558abe7336d8c05638b4fa09046acfb2617deda31f5d0844f6f212f13c4271a3'
def ensure_fdor(root,offline):
 path=root/'data/cache/public_ownership/2026FINALCompSubmStd.pdf';receipt=path.with_suffix('.receipt.json');url='https://www.floridarevenue.com/property/Documents/2026FINALCompSubmStd.pdf'
 if path.exists()!=receipt.exists():raise ValueError('Partial FDOR document/receipt exists; preserve and review, never overwrite')
 if path.exists():
  proof=read(receipt)
  if sha(path)!=FDOR_REVIEWED_SHA256 or proof.get('sha256')!=FDOR_REVIEWED_SHA256 or proof.get('publication_date')!='2026-03-27' or proof.get('url')!=url:raise ValueError('FDOR bytes or receipt differ from reviewed source; preserve and review')
  return path,receipt
 if offline:raise ValueError('Offline original FDOR document/receipt missing')
 data=urllib.request.urlopen(url,timeout=30).read(8*1024*1024+1)
 if not data.startswith(b'%PDF') or len(data)>8*1024*1024 or hashlib.sha256(data).hexdigest()!=FDOR_REVIEWED_SHA256:raise ValueError('FDOR response differs from reviewed PDF; no file or dated receipt written')
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.pdf.tmp');temporary.write_bytes(data);temporary.replace(path)
 atomic_json(receipt,{'url':url,'retrieved_utc':now(),'sha256':FDOR_REVIEWED_SHA256,'publication_date':'2026-03-27','code_reference_pdf_page_1_based':65})
 return path,receipt

def classify(code,definitions):
 if code not in RULES:return {'assessment_government_reference':False,'assessment_classification':None,'government_level_reference':None,'classification_status':'ownership_unknown_not_classified_private','legal_owner_class':None}
 if code not in definitions:raise ValueError('Official exact use-code definition unavailable')
 return {'assessment_government_reference':True,'assessment_classification':RULES[code],'government_level_reference':RULES[code],'classification_status':'accepted_exact_official_assessment_code_reference_not_title','legal_owner_class':None}

def build(root=ROOT,offline=False):
 root=Path(root).resolve();out=root/OUT;receipt_path=out/'receipt.json';expected_files={'register.json','government_references.geojson','coverage.svg'}
 if receipt_path.exists():
  receipt=read(receipt_path)
  if set(receipt.get('artifacts',{}))!=expected_files:raise ValueError('Ownership output proof incomplete')
  for n,h in receipt['artifacts'].items():
   if sha(out/n)!=h:raise ValueError('Preserve manually modified ownership output')
 elif any((out/n).exists() for n in expected_files):raise ValueError('Unreceipted ownership output exists')
 fdor_path,fdor_receipt=ensure_fdor(root,offline)
 active=read(root/'data/processed/active.json');bound_path=root/'data/processed/study_boundaries.geojson';scopes={f['properties']['scope']:shape(f['geometry']) for f in read(bound_path)['features']};scope=scopes['neighborhood'];folder=(root/active['relative_path']).resolve()
 if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Active snapshot escapes')
 old=read(folder/'parcels.json')['features'];oldbyid={f['properties']['id']:f for f in old};client=Client(root/'data/cache/public_ownership',offline=offline)
 use=client.get(API+'api/RP/GetUseCodes');exemption=client.get(API+'api/RP/GetExemptionCodes');definitions={r['code']:r['description'] for r in use}
 if len(definitions)!=len(use) or not all(isinstance(r['code'],str) for r in use):raise ValueError('Official code schema changed')
 # Bind exact local definitions, not another county's suffixes or keyword guesses.
 for code,description in EXPECTED_DEFINITIONS.items():
  if definitions.get(code)!=description:raise ValueError('OCPA use-code definition changed; review classification: '+code)
 source={**SOURCES['parcels'],'fields':['OBJECTID','PARCEL','DOR_CODE','EXEMPT_CODE']};raw,metadata=arcgis(CheckedClient(client),source,bbox=scope.bounds)
 project=Transformer.from_crs(4326,32617,always_xy=True).transform;rows=[];gov_features=[];excluded=[];by_pin=collections.defaultdict(list);all_scope_geoms=[]
 for f in raw['features']:
  props=f['properties'];oid=str(props['OBJECTID']);pin=props['PARCEL'];code=props.get('DOR_CODE');g=shape(f['geometry'])
  if not isinstance(pin,str):raise ValueError('Parcel identity is not original string')
  if not g.is_valid or g.is_empty:raise ValueError('Invalid source parcel geometry; preserve prior register')
  clip=g.intersection(scope)
  if clip.area<=0:excluded.append({'source_object_id':oid,'reason':'envelope_candidate_without_positive_area_in_official_neighborhood'});continue
  classification=classify(code,definitions);feature_id='ocpa:'+oid;oldrow=oldbyid.get(feature_id);method='outside_active_extraction_or_new_source_feature';active_id=None;geometry_delta=None
  if oldrow and oldrow['properties']['parcel_id']==pin:
   geometry_delta=transform(project,g.symmetric_difference(shape(oldrow['geometry']))).area
   if geometry_delta<.01:method='exact_source_OBJECTID_PARCEL_and_geometry';active_id=feature_id
   else:method='same_source_OBJECTID_PARCEL_geometry_changed_review'
  row={'source_feature_id':feature_id,'source_object_id':oid,'parcel_id':pin,'original_use_code':code,'official_use_description':definitions.get(code),**classification,'public_entity_type':'utility' if code in ('8620','8920') else 'school_district' if code=='8300' else 'assessment_reference_only','municipality_identity':None,'legal_title_verified':False,'public_access_verified':False,'current_vacancy_verified':False,'source_tax_year':None,'source_status':'published_assessment_reference; acquisition/effective date unknown','active_feature_match':method,'active_parcel_feature_id':active_id,'source_vs_active_geometry_difference_m2':geometry_delta,'neighborhood_intersection_m2':transform(project,clip).area,'main_street_intersection_m2':transform(project,g.intersection(scopes['main_street'])).area,'official_inventory_corroboration':[]}
  rows.append(row);by_pin[pin].append(row);all_scope_geoms.append(transform(project,clip))
  if row['assessment_government_reference']:gov_features.append({'type':'Feature','id':feature_id,'geometry':mapping(clip),'properties':row})
 # Independent official registers corroborate only exact original parcel identifiers.
 city_source={'dataset':'bkpt-5h2w','url':'https://data.cityoforlando.net/resource/bkpt-5h2w.json','fields':['property_id','parcel']};city,city_meta=socrata(CheckedClient(client),city_source,'1=1');city_matches=[];city_unmatched=0;city_unusable=0
 for record in city:
  pin=city_pin(record.get('parcel'))
  if not pin:city_unusable+=1;continue
  matches=by_pin.get(pin,[])
  if not matches:city_unmatched+=1;continue
  evidence={'source':'City Owned Vacant Lots','dataset_id':'bkpt-5h2w','source_row_id':record['source_row_id'],'property_id':record.get('property_id'),'original_parcel_string':record.get('parcel'),'normalized_parcel_id':pin,'match_method':'exact_publisher_parcel_number_with_documented_City_STR_to_OCPA_RTS_order','matched_feature_ids':[r['source_feature_id'] for r in matches],'ownership_statement':'City inventory reports City-owned; not independent current deed verification','current_vacancy_verified':False};city_matches.append(evidence)
  for row in matches:row['official_inventory_corroboration'].append(evidence)
 county_item=client.get('https://www.arcgis.com/sharing/rest/content/items/a4bdbefbfd914033a1f8e839165d57f6',{'f':'json'})
 if county_item.get('orgId')!='0U8EQ1FrumPeIqDb' or county_item.get('access')!='public' or str(county_item.get('url','')).rstrip('/')!=COUNTY_URL.rsplit('/',1)[0]:raise ValueError('County-owned building item association changed')
 county_source={'url':COUNTY_URL,'fields':['OBJECTID','ENTERPRISE_ADDRESS_ID','OFFICIAL_PARCEL_ID','DOR_USE_CODE','DT_LAST_MOD'],'oid':'OBJECTID'};county,county_meta=arcgis(CheckedClient(client),county_source,bbox=scope.bounds);county_matches=[];county_unmatched=[]
 for f in county['features']:
  props=f['properties'];pin=clean_pin(props.get('OFFICIAL_PARCEL_ID'));matches=by_pin.get(pin,[]);inside=shape(f['geometry']).intersects(scope)
  evidence={'source':'Orange County Owned Buildings','item_id':'a4bdbefbfd914033a1f8e839165d57f6','source_object_id':str(props['OBJECTID']),'enterprise_address_id':props.get('ENTERPRISE_ADDRESS_ID'),'original_parcel_id':props.get('OFFICIAL_PARCEL_ID'),'source_use_code':props.get('DOR_USE_CODE'),'source_last_modified':props.get('DT_LAST_MOD'),'point_in_official_neighborhood':inside,'matched_feature_ids':[r['source_feature_id'] for r in matches],'match_method':'exact_publisher_OFFICIAL_PARCEL_ID_no_spatial_promotion','ownership_statement':'County building inventory reports County-owned; building record is not a complete County land/title register'}
  if matches:
   county_matches.append(evidence)
   for row in matches:row['official_inventory_corroboration'].append(evidence)
  else:county_unmatched.append(evidence)
 # Government reference observations remain separate from current title and each other.
 reference_conflicts=[]
 for row in rows:
  evidence=row['official_inventory_corroboration'];levels=set()
  if row['assessment_classification'] in ('municipal','county','state','federal'):levels.add(row['assessment_classification'])
  for entry in evidence:levels.add('municipal' if entry['source']=='City Owned Vacant Lots' else 'county')
  row['government_reference_present']=bool(row['assessment_government_reference'] or evidence)
  row['government_reference_status']='agency_reference_conflict_review' if len(levels)>1 else 'official_inventory_and_or_assessment_reference_not_title' if row['government_reference_present'] else 'ownership_unknown_not_classified_private'
  row['reported_government_level_candidates']=sorted(levels)
  row['municipality_identity_reference']='City of Orlando, as reported by City inventory' if any(e['source']=='City Owned Vacant Lots' for e in evidence) else None
  if len(levels)>1:reference_conflicts.append({'source_feature_id':row['source_feature_id'],'parcel_id':row['parcel_id'],'assessment_classification':row['assessment_classification'],'inventory_reported_candidates':sorted(levels),'reason':'Published government reference classifications disagree; no selected owner/title promoted'})
 gov_features=[{'type':'Feature','id':row['source_feature_id'],'geometry':mapping(shape(next(f['geometry'] for f in raw['features'] if str(f['properties']['OBJECTID'])==row['source_object_id'])).intersection(scope)),'properties':row} for row in rows if row['government_reference_present']]
 fdor_path=root/'data/cache/public_ownership/2026FINALCompSubmStd.pdf';fdor_receipt=root/'data/cache/public_ownership/2026FINALCompSubmStd.receipt.json';fdor=read(fdor_receipt)
 if fdor.get('publication_date')!='2026-03-27' or sha(fdor_path)!=fdor['sha256']:raise ValueError('2026 final FDOR source receipt mismatch')
 dependencies={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in [bound_path,root/'data/processed/active.json',folder/'parcels.json',root/'tools/public_ownership.py',root/'tools/data_pipeline.py',root/'tools/review_land.py',fdor_path,fdor_receipt]}
 for a in client.accesses:
  p=root/'data/cache/public_ownership'/(hashlib.sha256(a['url'].encode()).hexdigest()+'.json');dependencies[str(p.relative_to(root)).replace('\\','/')]=sha(p)
 totals=collections.Counter(r['assessment_classification'] or 'unknown_not_classified_private' for r in rows);unknown_codes=sorted({r['original_use_code'] for r in rows if r['official_use_description'] is None},key=str);counts={'envelope_source_features':len(raw['features']),'official_neighborhood_features':len(rows),'unique_parcel_ids':len(by_pin),'government_assessment_reference_features':sum(r['assessment_government_reference'] for r in rows),'combined_government_reference_features':sum(r['government_reference_present'] for r in rows),'official_inventory_matched_features':sum(bool(r['official_inventory_corroboration']) for r in rows),'agency_reference_conflicts':len(reference_conflicts),'assessment_without_government_label_features':sum(not r['assessment_government_reference'] for r in rows),'no_government_reference_features':sum(not r['government_reference_present'] for r in rows),'legal_owner_class_unknown_features':len(rows),'legal_titles_verified':0,'source_envelope_exclusions':len(excluded),'class_counts':dict(totals),'exact_active_feature_matches':sum(r['active_parcel_feature_id'] is not None for r in rows)}
 gap=transform(project,scope).difference(unary_union(all_scope_geoms)).area
 packet={'schema':'twin.public-ownership-reference/1','source_snapshot':active['snapshot'],'built_utc':now(),'counts':counts,'coverage':{'boundary':'Full official College Park neighborhood polygon, not current partial extraction','query_bbox_wgs84':list(scope.bounds),'neighborhood_area_m2':transform(project,scope).area,'uncovered_by_any_parcel_polygon_m2':gap,'gap_meaning':'Parcel geometry gaps can include roads/water and unregistered land; not proof of private/public ownership','main_street_government_reference_features':sum(r['government_reference_present'] and r['main_street_intersection_m2']>0 for r in rows)},'classification_rules':{code:{'assessment_classification':RULES[code],'official_OCPA_description':definitions[code]} for code in sorted(RULES)},'exemption_namespace_result':{'OCPA_numeric_exemption_dictionary_rows':len(exemption),'GIS_field_name':'EXEMPT_CODE','accepted_crosswalk':False,'reason':'GIS field namespace is not established as the numeric public code-table namespace; no exemption values published or used for government classification'},'source_register':[{'publisher':'Orange County Property Appraiser','api_url':source['url'],'fields_requested':source['fields'],'fields_published':['OBJECTID','PARCEL','DOR_CODE'],'source_native_crs':metadata.get('extent',{}).get('spatialReference'),'output_crs':'EPSG4326','area_crs':'EPSG32617 metres','vertical_datum':'not used','acquisition_date':None,'effective_date':None,'tax_roll_year':None,'source_updated_epoch_ms':metadata.get('editingInfo',{}).get('lastEditDate'),'rights':'Public reference API access observed; appraisal geometry is not a title/boundary survey'},{'publisher':'OCPA public Code Tables','api_url':API+'api/RP/GetUseCodes','date_published':None,'date_effective':None,'dictionary_version':'Current returned lookup; original version date not supplied','official_UI_trace':'https://ocpaweb.ocpafl.org/ codetables lazy module212; no authentication or security endpoints accessed'},{'publisher':'Florida Department of Revenue','url':fdor['url'],'publication_date':'2026-03-27','retrieved_utc':fdor.get('retrieved_utc'),'reference':'2026 FINAL standards, Addendum E PDFpage65; general government categories only. Exact OCPA local suffix definitions control classification.'},{'publisher':'City of Orlando Real Estate Management Division','dataset_id':'bkpt-5h2w','title':city_meta.get('name'),'rows_updated_epoch_seconds':city_meta.get('rowsUpdatedAt'),'requested_fields':['property_id','parcel',':id as source_row_id'],'citywide_source_rows':len(city),'exact_neighborhood_matches':len(city_matches),'not_matched_in_neighborhood':city_unmatched,'unusable_parcel_strings':city_unusable,'scope':'Only City-owned vacant-lot inventory, not comprehensive City-owned parcels; current vacancy/title unverified'},{'publisher':'Orange County Government GIS','item_id':'a4bdbefbfd914033a1f8e839165d57f6','api_url':COUNTY_URL,'item_modified_epoch_ms':county_item.get('modified'),'license_info':county_item.get('licenseInfo'),'source_geometry_crs':county_meta.get('extent',{}).get('spatialReference'),'requested_fields':county_source['fields'],'query_envelope_candidates':len(county['features']),'exact_neighborhood_parcel_matches':len(county_matches),'scope':'County-owned building POINT inventory, not all County land or title records'}],'rows':rows,'government_reference_geojson_count':len(gov_features),'first_five_safe_rows':rows[:5],'first_five_government_reference_rows':[r for r in rows if r['government_reference_present']][:5],'field_dictionary':{'source_feature_id':'OCPA source OBJECTID namespace; repeated tax PINs retain distinct geometry rows','parcel_id':'Original OCPA PARCEL string, no leading-zero loss','original_use_code':'Exact original four-character OCPA DOR_CODE; no foreign-county suffix translation','assessment_government_reference':'Exact official published assessment-use classification only, never legal title','assessment_classification':'Explicit reviewed code rule; no keyword/owner-name classification','legal_owner_class':'Unknown; no title/deed/owner-name evidence imported','official_inventory_corroboration':'Exact original parcel-ID context from official City/County register; no spatial-only ownership promotion','active_feature_match':'Original source OBJECTID + exact PID + geometry comparison, no active snapshot mutation'},'exact_inventory_corroborations':{'city':city_matches,'county':county_matches,'county_unmatched':county_unmatched,'agency_reference_conflicts':reference_conflicts},'excluded':excluded,'unresolved':reference_conflicts+[{'reason':'Full legal government ownership is not established; use codes can omit government property in other use/lease/utility categories, and assessed labels are not a current deed search.'},{'reason':'Government-level-unspecified and public institution categories retain unknown exact agency; municipal code alone does not identify which municipality.'},{'reason':'Zoning P, park function, exemption, public access, physical vacancy, surplus/development availability and legal ownership remain distinct.'},{'reason':'GIS exemption namespace is unresolved; no numeric-code crosswalk applied.'},{'unknown_use_codes':unknown_codes}],'requests':client.accesses,'dependencies':dependencies,'active_snapshot_changed':False,'scene_changed':False,'owner_names_requested':False,'owner_contacts_requested':False,'private_booms_read':False,'comprehensive_legal_ownership_claimed':False}
 if any(sha(root/p)!=h for p,h in dependencies.items()):raise ValueError('Ownership input changed while building')
 for source_entry in packet['source_register']:
  api=source_entry.get('api_url');matches=[a for a in client.accesses if api and a['url'].split('?')[0] in (api,api+'/query')]
  if source_entry.get('dataset_id')=='bkpt-5h2w':matches=[a for a in client.accesses if a['url'].split('?')[0] in ('https://data.cityoforlando.net/resource/bkpt-5h2w.json','https://data.cityoforlando.net/api/views/bkpt-5h2w.json')]
  known=sorted(a['retrieved_utc'] for a in matches if a.get('retrieved_utc'));source_entry['retrieved_utc']=(known[-1] if known and len(known)==len(matches) else None) if matches else source_entry.get('retrieved_utc');source_entry['request_retrieval_range_utc']=[known[0],known[-1]] if known else None
 # Pixel-free full-neighborhood map; assessment and official register references only.
 whole=transform(project,scope);xmin,ymin,xmax,ymax=whole.bounds;scale=min(850/(xmax-xmin),850/(ymax-ymin))
 def path(g):
  parts=[]
  for poly in getattr(g,'geoms',[g]):
   if poly.geom_type!='Polygon':continue
   d=' '.join('M '+' L '.join(f'{(x-xmin)*scale+15:.2f},{(ymax-y)*scale+15:.2f}' for x,y in ring.coords)+' Z' for ring in [poly.exterior,*poly.interiors]);parts.append('<path fill-rule="evenodd" d="'+d+'"/>')
  return ''.join(parts)
 svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 930"><rect width="900" height="930" fill="#f7f7f1"/><g fill="#e3e7e1" stroke="#777">'+path(whole)+'</g><g fill="#438c78" stroke="#254c40">'+''.join(path(transform(project,shape(f['geometry']))) for f in gov_features)+'</g><text x="15" y="905" font-size="15">Full College Park: government assessment/register references, not legal ownership</text><text x="15" y="925" font-size="13">Other parcels remain ownership unknown; no private/public-access or vacancy inference.</text></svg>'
 payloads={'register.json':json.dumps(packet,indent=2).encode(),'government_references.geojson':json.dumps({'type':'FeatureCollection','features':gov_features},indent=2).encode(),'coverage.svg':svg.encode()}
 if receipt_path.exists():
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for name in [*expected_files,'receipt.json']:shutil.copy2(out/name,backup/name)
 out.mkdir(parents=True,exist_ok=True)
 for name,body in payloads.items():temp=out/(name+'.tmp');temp.write_bytes(body);temp.replace(out/name)
 atomic_json(receipt_path,{'source_snapshot':active['snapshot'],'artifacts':{n:sha(out/n) for n in expected_files}});return packet

def validate(root=ROOT):
 root=Path(root).resolve();out=root/OUT;p=read(out/'register.json');receipt=read(out/'receipt.json')
 if p.get('schema')!='twin.public-ownership-reference/1' or not p.get('dependencies') or set(receipt.get('artifacts',{}))!={'register.json','government_references.geojson','coverage.svg'}:raise ValueError('Ownership proof incomplete')
 if p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or receipt['source_snapshot']!=p['source_snapshot']:raise ValueError('Ownership snapshot stale')
 for name,h in receipt['artifacts'].items():
  if sha(out/name)!=h:raise ValueError('Ownership output changed')
 for name,h in p['dependencies'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or sha(path)!=h:raise ValueError('Ownership source changed')
 return p

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args();p=build(offline=args.offline);print(json.dumps({'counts':p['counts'],'coverage':p['coverage'],'inventory_matches':{k:len(v) for k,v in p['exact_inventory_corroborations'].items()}}))
