"""Attributed parking/mobility references; no capacity survey or active writes.

Default offline; --live populates bounded public source caches. Contract:
docs/MOBILITY_INVENTORY.md. Original documents stay local and ignored.
"""
from pathlib import Path
import sys,os,json,re,html,unicodedata,datetime,hashlib,urllib.request,urllib.parse,shutil
from html.parser import HTMLParser
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapely
from shapely.geometry import shape,mapping,Point
from shapely.ops import unary_union
from pyproj import Transformer
from pypdf import PdfReader
from data_pipeline import Client,atomic_json
from fdot_context import read,sha,now,rel,transform,validate as validate_fdot
from city_adapter_contract import validate as validate_city

OUT=Path('data/processed/mobility_inventory')
REVIEWED_REPORT_SHA256='3a81831860dd55f195809463fbde0d4ac01a4d37c89a8f1c7275cea74188914a'  # Actual pages6/90 visually reviewed; re-review a changed revision.
URLS={
 'city_parking_directory':'https://www.orlando.gov/Parking-Transportation/Parking/Parking-Garages-and-Lots/City-of-Orlando-Garages',
 'city_bike_study':'https://www.orlando.gov/Building-Development/City-Projects/Bike-and-Micromobility-Parking-Study',
 'college_park_ev':'https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/CAO/Sustainability-Resilience/Green-Works-Focus-Areas/Alternative-Transportation/Expanding-Public-Electric-Vehicle-EV-Charging-Infrastructure/College-Park-Neighborhood-Center-Station',
 'district_parking':'https://www.thedrivecollegepark.com/plan-your-day/',
 'albert_park':'https://www.orlando.gov/Parks-the-Environment/Directory/Albert-Park',
 'bike_final_report':'https://www.orlando.gov/files/sharedassets/public/v/1/departments/transportation/bike-and-micromobility-parking-study-final-report-8.26.pdf',
 'bike_final_recommendations':'https://www.orlando.gov/files/sharedassets/public/v/1/departments/transportation/bike-parking-study-final-recommendations-8.26.pdf',
}

def source(root,name,offline):
 folder=root/OUT/'sources';folder.mkdir(parents=True,exist_ok=True);suffix='.pdf' if name.startswith('bike_final') else '.html';path=folder/(name+suffix);rp=folder/(name+'.receipt.json');url=URLS[name]
 if path.exists():
  receipt=read(rp)
  if receipt['url']!=url or receipt['sha256']!=sha(path):raise ValueError('Original mobility source changed: '+name)
  return path,receipt
 if offline:raise ValueError('Offline source miss: '+name)
 cap=20000000 if suffix=='.pdf' else 5000000
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'text/html,application/pdf'}),timeout=45) as r:data=r.read(cap+1);headers=dict(r.headers);final=r.url
 if len(data)>cap or suffix=='.pdf' and not data.startswith(b'%PDF'):raise ValueError('Unexpected bounded source size/type')
 path.write_bytes(data);receipt={'url':url,'final_url':final,'retrieved_utc':now(),'sha256':sha(path),'bytes':len(data),'headers':headers};atomic_json(rp,receipt);return path,receipt

class Text(HTMLParser):
 def __init__(self):super().__init__();self.output=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style'):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.skip=max(0,self.skip-1)
 def handle_data(self,data):
  if not self.skip:self.output.append(data)

def plain(path,main=True):
 raw=path.read_text(encoding='utf8');start=raw.find('normalTemplateStart');end=raw.find('normalTemplateEnd',start)
 if main and start>=0:raw=raw[start:end]
 p=Text();p.feed(raw);return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',' '.join(p.output))).strip()

def point_from_page(text):
 matches=[(float(a),float(b)) for a,b in re.findall(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)',text) if 25<float(a)<32 and -85<float(b)<-79]
 if len(set(matches))!=1:raise ValueError('Unique official facility reference point unavailable')
 lat,lon=matches[0];return {'type':'Point','coordinates':[lon,lat]}

def hour(value,ampm):return f'{int(value)%12+(12 if ampm.lower()=="pm" else 0):02d}:00'

def recommendations(reader):
 if len(reader.pages)!=2:raise ValueError('Recommendations source pagination changed')
 text=reader.pages[1].extract_text() or '';rows=[];unparsed=[]
 pattern=r'^(\d+)\s+(.+?)\s+([A-Z]{2}\d+)\s+(City District|Study District|Parramore Zone [12]|Ivanhoe Village|Thornton Park|Creative Village)\s*(.*?)\s+(Bike Parking|Electrified Parking|On-Street Corral|Designated Staging)\s+(yes|no)\s*$'
 for line in text.splitlines():
  if not re.match(r'^\d+\s+\S',line):continue
  m=re.match(pattern,line)
  if not m:unparsed.append(line);continue
  oid,name,key,district,location,kind,priority=m.groups();rows.append({'id':'city:bike-study-2026:recommendation:'+oid,'source_fields':{'OBJECTID':int(oid),'NAME':name,'ID':key,'DISTRICT':district,'LOCATION':location or None,'TYPE':kind,'PRIORITY':priority},'source_document':'bike_final_recommendations','physical_page':2,'status':'proposed_recommendation_not_existing_inventory','geometry':None,'geometry_status':'no_published_GIS_geometry_in_retrieved_table','accepted_as_local_existing_facility':False,'capacity_spaces':None,'geographic_status':'not_accepted_as_CollegePark_without_source_location_geometry','source_text_incomplete':bool(location and location.count('(')!=location.count(')'))})
 if unparsed or len(rows)!=70 or len({r['source_fields']['OBJECTID'] for r in rows})!=70:raise ValueError('Recommendations table/schema/count changed: '+str(unparsed))
 return rows

def study_counts(pages):
 text=re.sub(r'\s+',' ',pages[38]);districts=['Creative Village','Parramore Zone 1','Parramore Zone 2','City District','Ivanhoe Village','Thornton Park','Outside Main Street Districts','TOTAL'];rows=[];totals={};table_values={};conflicts=[]
 for label in ['Bicycle Parking','Formal Staging','Informal Staging']:
  m=re.search(re.escape(label)+r'\s+((?:\d+\s+){7}\d+)',text)
  if not m:raise ValueError('Published Table9 schema changed: '+label)
  values=[int(v) for v in m.group(1).split()];totals[label]=values[-1];table_values[label]=values
  if sum(values[:-1])!=values[-1]:conflicts.append({'source_document':'bike_final_report','physical_page':39,'table':9,'category':label,'reported_total':values[-1],'sum_of_published_district_cells':sum(values[:-1]),'resolution':'unresolved; original values preserved'})
  for district,value in zip(districts,values):rows.append({'id':'city:bike-study-2026:table9:'+label.replace(' ','_')+':'+district.replace(' ','_'),'district':district,'category':label,'reported_count':value,'unit':'facility_records_not_parking_spaces','source_document':'bike_final_report','physical_page':39,'table':9,'college_park_applicability':'not_established; no accepted local extrapolation','observation_date':None})
 prose=re.search(r'including\s+(\d+)\s+bike parking facilities',re.sub(r'\s+',' ',pages[37]));prose=int(prose.group(1)) if prose else None
 if prose!=totals['Bicycle Parking']:conflicts.append({'source_document':'bike_final_report','physical_pages':[38,39],'category':'Bicycle Parking','prose_count':prose,'table9_count':totals['Bicycle Parking'],'resolution':'unresolved; no correction or capacity inference'})
 # Table11's formal-staging City District cell differs from Table9. Retain this
 # documented mismatch rather than selecting whichever supports a conclusion.
 table11=re.sub(r'\s+',' ',pages[39]).split('TABLE 11:',1)[1];m=re.search(r'\bTOTAL\s+((?:\d+\s+){7}\d+)',table11)
 if not m:raise ValueError('Table11 source structure changed')
 table11_values=[int(v) for v in m.group(1).split()]
 if table11_values[3]!=table_values['Formal Staging'][3]:conflicts.append({'source_document':'bike_final_report','physical_pages':[39,40],'category':'City District formal staging','table9_value':table_values['Formal Staging'][3],'table11_value':table11_values[3],'resolution':'unresolved; no CollegePark attribution'})
 return rows,conflicts

def table_dictionaries(tables):
 """Every exported table field has a reviewed meaning; new fields fail closed."""
 json_types={str:'string',int:'integer',float:'number',bool:'boolean',dict:'object',list:'array',type(None):'null'}
 shared={
  'id':'Project namespaced document/context row key, not a verified physical facility/space or agency GIS identifier.',
  'geometry':'GeoJSON source-reference context in EPSG4326 display coordinates; never a surveyed parking bay or entrance. Null means no accepted location.',
  'physical_page':'One-based physical source PDF page, distinct from a printed page label.',
  'source_document':'Key of the original PDF in source_register; binds the row to its source bytes and receipt.',
 }
 local={
  'ADA_compliance_verified':'False means compliance was not verified; it does not mean noncompliant.',
  'address_source_entity_ids':'Exact City address adapter entity IDs used as location references, not accepted garage identities.',
  'blockface_geometry_verified':'False means the parking-regulated blockface was not established from signs or an authoritative inventory.',
  'candidate_city_street_feature_ids':'City centerline feature IDs providing corridor context only; no parking-rule or FDOT identity promotion.',
  'capacity_status':'Qualification of capacity evidence; operator_reported_unverified is an attributable claim, not accepted capacity.',
  'charger_count_is_not_parking_space_count':'True explicitly prevents treating the static charger quantity as vehicle-space capacity.',
  'contextual_park_hours':'Object holding actual City park-opening text and its limited scope; not a parking-access schedule.',
  'current_occupancy':'Number of occupied spaces from an actual dated observation; null because no observation was obtained.',
  'current_public_access_legally_verified':'False means no current legal-access agreement/title verification was performed, not that access is prohibited.',
  'demand':'Parking demand with observation methodology/interval; null because no usable observations were acquired.',
  'facility_entrance_geometry':'Surveyed or otherwise accepted entrance geometry; null because only reference locations are available.',
  'fees':'Attributed current parking charge/rate schedule; null when not established. A time limit does not establish a fee.',
  'garage_parcel_id':'Accepted whole-garage parcel association; null because a City address PID may identify a condo/unit.',
  'geometry_basis':'Exact source and interpretation used for the reference point/line; excludes bay/entrance/survey accuracy claims.',
  'hours':'Accepted parking-access/operation schedule; null when not supplied or verified.',
  'inventory_observation_date':'Date of actual facility/space inventory observation; null is unknown, not the download date.',
  'kind':'Reference-context category, separating amenity, corridor rule, garage claim and charger count.',
  'legally_usable_capacity':'Accepted legally available vehicle-space quantity after restrictions/access review; null because not established.',
  'live_charger_availability':'Real-time available charger count; null because a static web quantity is not a live feed.',
  'name':'Human-readable source-context name; not a certified legal facility identity.',
  'occupancy_observation_interval':'Actual start/end and sampling interval for occupancy; null because no observations were obtained.',
  'operator_reports_no_restriction_after_18_or_sunday':'Whether the retrieved district guidance contains that explicit statement; not independent City legal verification.',
  'outside_limit_window_status':'Parking status outside the stated time-limit window; null when the source does not establish it.',
  'parking_limit_days':'Weekdays to which the district operator attributes the parking time limit; not a field-sign/legal verification.',
  'parking_limit_wall_time':'Two local wall-clock HH:MM strings for the attributed restriction window; no effective-date or UTC assumption.',
  'parking_max_stay_minutes':'Operator-reported maximum stay, converted from hours to minutes; not a verified current sign rule.',
  'reported_accessible_spaces':'Operator-reported accessible-space quantity; not ADA compliance, dimensional or legal verification.',
  'reported_address':'Address explicitly printed by the source; not an accepted entrance or whole-parcel association.',
  'reported_charger_count':'Static City web charger quantity, not vehicle spaces, usable parking capacity or current availability.',
  'reported_parking_level':'Operator-reported parking floor/level number; not building story count or elevation.',
  'reported_public_access_statement':'Attributed public-parking claim with its unverified legal/currentness limitation.',
  'reported_standard_spaces':'Operator-reported standard vehicle-space quantity; not an independently counted inventory.',
  'reported_total_basis':'Original claim/arithmetic and its limits; standard plus accessible claims are not legally usable capacity.',
  'reported_total_spaces':'Arithmetic total of the operator standard/accessible claims when present; null otherwise, never a district supply total.',
  'reported_total_vehicle_spaces':'Vehicle-space capacity distinct from charger count; null when the source only reports chargers.',
  'scene_geometry_promoted':'False confirms these source contexts were not applied as active parking/scene geometry.',
  'scope':'Object recording actual intersection of the reference geometry with official neighborhood/MainStreet boundaries.',
  'source_address_parcel_references':'Original City address PID strings; condo/unit possibilities remain unresolved and are not promoted to garage ownership.',
  'source_ids':'Source-register keys supporting the claim and its contextual geometry; provider roles remain separate.',
  'source_parcel_limit':'Explanation of unit/address-versus-whole-garage parcel ambiguity.',
  'sources':'Copies of referenced source_register objects, including imported City/FDOT adapter provenance; not extra independent observations.',
  'static_web_label':'Original source label for a static quantity; the word available does not imply a live availability feed.',
  'time_limit_is_not_a_fee_rule':'True preserves the distinction between a parking duration rule and payment/price.',
  'time_zone_basis':'Local wall-clock interpretation and the publishers unspecified timezone/effective-date limitation.',
  'turnover':'Space-use turnover from dated observations with intervals; null because none were acquired.',
 }
 counts={
  'category':'Original Table9 facility category; counts describe facility records, not parking-space capacity.',
  'college_park_applicability':'Explicit lack of accepted local extrapolation from the source study districts.',
  'district':'Original published district/category column, including TOTAL; no CollegePark boundary is invented.',
  'observation_date':'Actual underlying facility inventory date; null because not supplied by the reviewed source.',
  'reported_count':'Exact integer in the published table cell, retained even when row arithmetic conflicts.',
  'table':'Printed source table number, here9; source conflicts refer separately to prose/Table11.',
  'unit':'facility_records_not_parking_spaces; a rack, staging area or record is not a fixed space count.',
 }
 proposed={
  'accepted_as_local_existing_facility':'False: a proposed, unlocated report row is not an accepted existing CollegePark facility.',
  'capacity_spaces':'Parking-space capacity; null because the recommendation table does not provide it.',
  'geographic_status':'Why the recommendation has no accepted CollegePark location; not proof of zero physical facilities.',
  'geometry_status':'No published GIS geometry in the retrieved recommendation table; no inferred/geocoded point.',
  'source_fields':'Object containing original PDF columns unchanged in their own document namespace; definitions supplied below.',
  'source_text_incomplete':'True when the source location text contains unmatched parentheses; no missing address text is invented.',
  'status':'proposed_recommendation_not_existing_inventory, regardless of its priority flag.',
 }
 definitions={'local_facility_references':local,'published_study_existing_facility_counts':counts,'study_proposed_recommendations':proposed};result={}
 for name,rows in tables.items():
  fields=sorted({k for row in rows for k in row});known={**shared,**definitions[name]}
  if set(fields)-set(known):raise ValueError('Undocumented exported mobility fields: '+str(set(fields)-set(known)))
  result[name]={k:{'definition':known[k],'observed_json_types':sorted({json_types[type(r[k])] for r in rows if k in r}),'presence':'optional by reference kind' if any(k not in r for r in rows) else 'present in every table row','null_semantics':'Unknown/unestablished when null; an absent optional field is not applicable to that reference kind.'} for k in fields}
 result['local_facility_references'].update({
  'scope.in_neighborhood':{'definition':'Exact intersection of reference geometry with official CollegePark neighborhood; null if no accepted geometry.'},
  'scope.intersects_main_street':{'definition':'Exact intersection of reference geometry with the separate official MainStreet polygon; not parking coverage/completeness.'},
  'contextual_park_hours.source_text':{'definition':'Original City park-opening text extracted from Hours; null if unavailable. Not parking-access hours.'},
  'contextual_park_hours.scope':{'definition':'Explicit park-opening-only limitation preventing promotion to parking rules.'},
 })
 originals={'OBJECTID':'Original integer OBJECTID column in the PDF recommendation edition; not a live GIS object identifier.','NAME':'Original published recommendation/site name, without correcting identity/address discrepancies.','ID':'Original document recommendation code such as CD22; distinct from project row ID and agency GIS identifiers.','DISTRICT':'Original study-district label; does not establish CollegePark coverage.','LOCATION':'Original location description, null if blank; incomplete text is preserved and no point is inferred.','TYPE':'Original proposed parking-facility type; not an existing installation or space quantity.','PRIORITY':'Original yes/no prioritization string; not approval, construction or existing status.'}
 actual={k for row in tables['study_proposed_recommendations'] for k in row['source_fields']}
 if actual!=set(originals):raise ValueError('Original recommendation field dictionary changed')
 for k,v in originals.items():result['study_proposed_recommendations']['source_fields.'+k]={'definition':v,'observed_json_types':sorted({json_types[type(r['source_fields'][k])] for r in tables['study_proposed_recommendations']}),'null_semantics':'Blank original LOCATION becomes null; no value is invented.' if k=='LOCATION' else 'Original source value preserved.'}
 return result

def map_html(scopes,facilities,project):
 boundary=transform(project,scopes['neighborhood']);xmin,ymin,xmax,ymax=boundary.bounds;scale=min(780/(xmax-xmin),780/(ymax-ymin))
 def point(x,y):return ((x-xmin)*scale+10,(ymax-y)*scale+10)
 def path(g):
  parts=[]
  for p in getattr(g,'geoms',[g]):
   if p.geom_type=='Polygon':parts.append(' '.join('M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in [point(*q[:2]) for q in r.coords])+' Z' for r in [p.exterior,*p.interiors]))
   elif p.geom_type=='LineString':parts.append('M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in [point(*q[:2]) for q in p.coords]))
  return ' '.join(parts)
 svg='<svg viewBox="0 0 820 820" xmlns="http://www.w3.org/2000/svg"><path d="'+path(boundary)+'" fill="#edf2e9" fill-rule="evenodd" stroke="#60806c"/><path d="'+path(transform(project,scopes['main_street']))+'" fill="none" stroke="#d3a044" stroke-width="2"/>'
 for i,row in enumerate(facilities):
  if not row['geometry']:continue
  g=transform(project,shape(row['geometry']))
  if g.geom_type=='Point':
   x,y=point(g.x,g.y);svg+=f'<g data-row="{i}"><circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#286c91"/><text x="{x+7:.2f}" y="{y:.2f}" font-size="11">{html.escape(row["name"])}</text></g>'
  else:svg+=f'<path data-row="{i}" d="{path(g)}" fill="none" stroke="#ab743d" stroke-width="3"/>'
 svg+='</svg>';data=json.dumps(facilities).replace('<','\\u003c');buttons=''.join(f'<button data-select="{i}">{html.escape(r["name"])}</button>' for i,r in enumerate(facilities))
 return ("""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>College Park parking references</title>
<style>body{font:16px/1.5 system-ui;margin:24px;color:#25392e;background:#f4f6f1}h1{margin-bottom:8px}main{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(320px,1fr);gap:22px}svg{width:100%;max-height:78vh;background:white;border-radius:10px}aside{background:white;padding:22px;border-radius:10px;align-self:start}button{padding:10px 14px;margin:5px;border:1px solid #a8baad;border-radius:6px;background:white;cursor:pointer}button[aria-pressed=true]{background:#d9e9df;border-color:#38634c}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #bc8b32;outline-offset:3px}.selected{stroke:#b73722;stroke-width:5}h2{margin:4px 0 8px}h3{font-size:16px;margin-bottom:8px}.type{color:#5c7162;margin:0}.note{font-size:14px;color:#56685b}.facts{display:grid;grid-template-columns:110px 1fr;gap:10px 16px;margin:20px 0}.facts dt{font-weight:650}.facts dd{margin:0}.unknowns{padding:12px;background:#f6f1e4;border-radius:6px}.sources{padding-left:20px}.sources li{margin-bottom:12px}.sources small{display:block;color:#5c7162}a{color:#26583e}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:450px;overflow:auto}details{margin-top:20px;border-top:1px solid #dce4dd;padding-top:12px}summary{cursor:pointer}nav{margin:18px 0}@media(max-width:850px){body{margin:16px}main{grid-template-columns:1fr}svg{max-height:52vh}}</style>
<a href="/">Back to district map</a><h1>College Park parking and mobility</h1><p>Explore four source references. Reported counts and parking guidance still need on-site and access checks.</p><nav aria-label="Choose a parking reference">"""+buttons+"""</nav><main>"""+svg+"""<aside aria-live="polite"><p id="facilityType" class="type">Choose a reference</p><h2 id="facilityName">Parking information</h2><p id="selectionHint">Select a name or map marker to see reported spaces, time limits and sources.</p><dl id="facts" class="facts"></dl><p id="locationBasis" class="note"></p><p id="unknowns" class="unknowns" hidden></p><div id="sourceSection" hidden><h3>Sources and dates</h3><ul id="sourceLinks" class="sources"></ul></div><details id="rawDetails" hidden><summary>Source records and technical details</summary><pre id="rawRecord"></pre></details></aside></main><p class="note">Gold outline: Main Street. Green area: College Park neighborhood. Markers locate facilities or addresses; lines provide street context. This is not a complete parking inventory or a live availability map.</p><script>const rows="""+data+""";
const $=id=>document.getElementById(id);
const labels={park_parking_amenity_with_operator_capacity_claim:'Park parking',corridor_rule_reference_not_space_inventory:'Street parking guidance',district_reported_public_parking_context:'Garage parking guidance',official_charger_count_reference_not_vehicle_capacity:'EV charging reference'};
const names={park_parking_amenity_with_operator_capacity_claim:'Albert Park',corridor_rule_reference_not_space_inventory:'Edgewater Drive',district_reported_public_parking_context:'Wellesley parking',official_charger_count_reference_not_vehicle_capacity:'College Park Neighborhood Center'};
function clock(value){const [hour,minute]=value.split(':').map(Number);return (hour%12||12)+(minute?':'+String(minute).padStart(2,'0'):'')+(hour>=12?'pm':'am')}
function date(value){if(!value)return 'unknown';const parsed=new Date(value);return Number.isNaN(parsed.valueOf())?'unknown':parsed.toLocaleDateString('en-US',{timeZone:'UTC',month:'short',day:'numeric',year:'numeric'})}
function fact(label,value){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('facts').append(dt,dd)}
function select(i){
 const r=rows[Number(i)];if(!r)return;
 document.querySelectorAll('.selected').forEach(x=>x.classList.remove('selected'));
 document.querySelectorAll('[data-row]').forEach(x=>{if(Number(x.dataset.row)===Number(i))x.classList.add('selected')});
 document.querySelectorAll('[data-select]').forEach(x=>x.setAttribute('aria-pressed',String(Number(x.dataset.select)===Number(i))));
 $('facilityType').textContent=labels[r.kind]||'Source reference';$('facilityName').textContent=names[r.kind]||r.name;$('selectionHint').textContent='';$('facts').replaceChildren();
 if(r.reported_total_spaces!=null)fact('Reported spaces',r.reported_total_spaces+' ('+r.reported_standard_spaces+' standard + '+r.reported_accessible_spaces+' accessible), from district guidance');
 else if(r.reported_charger_count!=null){fact('Reported chargers',r.reported_charger_count+' on the City facility page');fact('Vehicle spaces','Unknown; charger count is separate')}
 else fact('Space count','Unknown');
 if(r.reported_parking_level!=null)fact('Parking level','Second floor, reported by district guidance');
 if(r.parking_max_stay_minutes!=null){
  fact('Time limit',r.parking_max_stay_minutes%60?r.parking_max_stay_minutes+' minutes':r.parking_max_stay_minutes/60+' hours');
  const days=r.parking_limit_days.length===7?'Every day':r.parking_limit_days.length===6?'Monday-Saturday':r.parking_limit_days.join(', ');
  fact('Limit applies',days+', '+r.parking_limit_wall_time.map(clock).join(' - '));
  if(r.operator_reports_no_restriction_after_18_or_sunday)fact('Outside that window','District guidance reports no time restriction after 6pm or on Sundays');
 }else fact('Parking hours','Unknown');
 if(r.reported_address)fact('Address',r.reported_address);
 const location={park_parking_amenity_with_operator_capacity_claim:'The map marks the park, not individual parking spaces.',corridor_rule_reference_not_space_inventory:'The line follows the street for context. Exact regulated block faces are unverified.',district_reported_public_parking_context:'The map uses a City address point. The garage entrance is unverified.',official_charger_count_reference_not_vehicle_capacity:'The map marks the neighborhood center, not individual charging bays.'};
 $('locationBasis').textContent=location[r.kind]||'Location accuracy remains unverified.';
 $('unknowns').hidden=false;$('unknowns').textContent='Still unverified: current usable capacity, legal public access, occupancy and demand. No live availability is provided.';
 $('sourceLinks').replaceChildren();$('sourceSection').hidden=false;
 for(const source of r.sources){
  const li=document.createElement('li'),url=source.url||source.api_url||source.endpoint;let anchor;
  try{const target=new URL(url,window.location.href);if(!['https:','http:'].includes(target.protocol))continue;anchor=document.createElement('a');anchor.href=target.href;anchor.target='_blank';anchor.rel='noopener noreferrer'}catch{continue}
  anchor.textContent=source.publisher+(source.provider_role==='district_operator_guidance_not_agency'?' - visitor guidance':source.id==='city_address_context'?' - address reference':source.id==='city_street_context'?' - street reference':' - facility page');
  const dates=document.createElement('small'),range=source.request_retrieval_range_utc||source.retrieval_range_utc,retrieved=source.retrieved_utc||(range&&range[range.length-1]);
  dates.textContent='Retrieved '+date(retrieved)+'. Observation/effective date: unknown.';li.append(anchor,dates);$('sourceLinks').append(li);
 }
 $('rawDetails').hidden=false;$('rawDetails').open=false;$('rawRecord').textContent=JSON.stringify(r,null,2);
}
document.querySelectorAll('[data-row]').forEach(x=>x.onclick=()=>select(x.dataset.row));
document.querySelectorAll('[data-select]').forEach((x,i)=>{x.textContent=names[rows[i].kind]||rows[i].name;x.setAttribute('aria-pressed','false');x.onclick=()=>select(x.dataset.select)});
</script></html>""")


def build(root=ROOT,offline=True):
 root=Path(root).resolve();out=root/OUT;rp=out/'receipt.json';expected={'packet.json','coverage.html'}
 if rp.exists():
  prior=read(rp)
  if set(prior.get('artifacts',{}))!=expected or any(sha(out/n)!=h for n,h in prior['artifacts'].items()):raise ValueError('Preserve modified mobility output')
 elif any((out/n).exists() for n in expected):raise ValueError('Unreceipted mobility output')
 active=read(root/'data/processed/active.json');boundary=root/'data/processed/study_boundaries.geojson';scopes={f['properties']['scope']:shape(f['geometry']) for f in read(boundary)['features']};project=Transformer.from_crs(4326,32617,always_xy=True).transform
 files={};register=[];deps=[root/'tools/mobility_inventory.py',root/'tools/data_pipeline.py',root/'tools/fdot_context.py',root/'tools/city_adapter_contract.py',root/'data/processed/active.json',boundary]
 for name in URLS:
  path,receipt=source(root,name,offline);files[name]=path;deps.extend([path,path.with_name(name+'.receipt.json')]);register.append({'id':name,'publisher':'College Park Main Street / The Drive' if name=='district_parking' else 'City of Orlando','provider_role':'district_operator_guidance_not_agency' if name=='district_parking' else 'official_municipal_publication','url':URLS[name],'retrieved_utc':receipt['retrieved_utc'],'bytes_sha256':receipt['sha256'],'document_date':'2026-07-31' if name=='bike_final_report' else None,'publication_date':None,'observation_date':None,'effective_date':None,'original_coordinates':'Published web latitude/longitude treated as EPSG4326 display reference; datum/accuracy not supplied. City address/street context retains adapter CRS evidence.','positional_accuracy':None,'rights':'Publicly accessible; no explicit redistribution license established. Original HTML/PDF/image pixels stay local.','authentication_observed':'public access without account/token','published_rate_limit':None,'refresh_cadence':None})
 raw_study=files['city_bike_study'].read_text(encoding='utf8')
 if any(urllib.parse.urlparse(URLS[n]).path not in raw_study for n in ['bike_final_report','bike_final_recommendations']):raise ValueError('Current City page no longer links selected final documents')
 if sha(files['bike_final_report'])!=REVIEWED_REPORT_SHA256:raise ValueError('Report revision changed; independently review actual study map/AppendixD before retaining geographic/inventory claims')
 report=PdfReader(files['bike_final_report']);pages=[p.extract_text() or '' for p in report.pages]
 if len(pages)!=93 or 'July 31, 2026' not in pages[0] or 'Appendix D:' not in pages[89] or 'Inventory' not in pages[89]:raise ValueError('Final report identity/structure changed')
 if len(pages[89].split())>25 or report.pages[89].get('/Annots'):raise ValueError('AppendixD now has content; review new inventory instead of retaining previous missing-data claim')
 proposed=recommendations(PdfReader(files['bike_final_recommendations']));summaries,conflicts=study_counts(pages)
 district=plain(files['district_parking']);i=district.find('Parking in College Park');j=district.find('Lynx',i);section=district[i:j]
 edge=re.search(r'(\d+)-hour parking along Edgewater Drive is available Monday-Saturday (\d+)(am|pm)-(\d+)(am|pm)',section);albert=re.search(r'Albert Park (\d+) spots \+ (\d+) handicap spot (\d+)-hour parking from (\d+)(am|pm)-(\d+)(am|pm) \(Monday-Sundays\)',section)
 if not edge or not albert or 'Public parking spaces available on the second floor of The Wellesley condominium' not in section:raise ValueError('District parking reference schema changed; do not reuse stale rules')
 atext=plain(files['albert_park']);evtext=plain(files['college_park_ev']);ev=re.search(r'Number of available electric chargers:\s*(\d+)',evtext)
 if not ev or 'Parking Lot' not in atext or 'On Street Parking' not in atext:raise ValueError('City facility statements changed')
 fdot=validate_fdot(root);city=validate_city(root);deps.extend([root/'data/processed/fdot_context/packet.json',root/'data/processed/fdot_context/receipt.json',root/'data/processed/city_adapter_contract/packet.json',root/'data/processed/city_adapter_contract/receipt.json']);deps.extend(root/p for p in {*fdot['dependencies'],*city['dependencies']})
 register.append({**next(r for r in city['source_register'] if r['id']=='addresses'),'id':'city_address_context','provider_role':'official_address_reference_not_parking_entrance','source_packet':'data/processed/city_adapter_contract/packet.json'})
 register.append({**next(r for r in fdot['source_register'] if r['table']=='city_streets'),'id':'city_street_context','provider_role':'official_street_reference_not_parking_bay','source_packet':'data/processed/fdot_context/packet.json'})
 street_rows=[r for r in fdot['tables']['city_streets']['rows'] if 'EDGEWATER' in str(r['original_fields'].get('FullStreetName','')).upper()];streets=[shape(r['clipped_geometry_wgs84']).intersection(scopes['main_street']) for r in street_rows];edgegeo=unary_union([g for g in streets if not g.is_empty and transform(project,g).length>.01]);addresses=[r for r in city['tables']['addresses'] if r['source_fields'].get('SitusAddress')=='2305 EDGEWATER DR'];locations={json.dumps(r['geometry'],sort_keys=True) for r in addresses};wgeo=json.loads(next(iter(locations))) if len(locations)==1 else None
 common={'legally_usable_capacity':None,'current_occupancy':None,'occupancy_observation_interval':None,'turnover':None,'demand':None,'current_public_access_legally_verified':False,'ADA_compliance_verified':False,'facility_entrance_geometry':None,'fees':None,'inventory_observation_date':None,'scene_geometry_promoted':False}
 facilities=[
  {**common,'id':'mobility:albert-park-reference','name':'Albert Park parking reference','kind':'park_parking_amenity_with_operator_capacity_claim','geometry':point_from_page(atext),'geometry_basis':'City park reference point, not parking lot/space/entrance geometry','source_ids':['albert_park','district_parking'],'reported_standard_spaces':int(albert[1]),'reported_accessible_spaces':int(albert[2]),'reported_total_spaces':int(albert[1])+int(albert[2]),'reported_total_basis':'Arithmetic of district operator standard+accessible claims; not surveyed or legally usable capacity','capacity_status':'operator_reported_unverified','parking_max_stay_minutes':int(albert[3])*60,'parking_limit_days':['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],'parking_limit_wall_time':[hour(albert[4],albert[5]),hour(albert[6],albert[7])],'outside_limit_window_status':None,'contextual_park_hours':{'source_text':re.search(r'Hours (.+?) Contact',atext).group(1) if re.search(r'Hours (.+?) Contact',atext) else None,'scope':'Park opening hours only, not a parking-access agreement'}},
  {**common,'id':'mobility:edgewater-curb-reference','name':'Edgewater time-limit reference','kind':'corridor_rule_reference_not_space_inventory','geometry':mapping(edgegeo),'geometry_basis':'City centerline context clipped to MainStreet; source does not identify every regulated blockface','source_ids':['district_parking','city_street_context'],'reported_total_spaces':None,'parking_max_stay_minutes':int(edge[1])*60,'parking_limit_days':['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],'parking_limit_wall_time':[hour(edge[2],edge[3]),hour(edge[4],edge[5])],'operator_reports_no_restriction_after_18_or_sunday':'There are no restrictions after 6pm or on Sundays' in section,'time_limit_is_not_a_fee_rule':True,'candidate_city_street_feature_ids':[r['id'] for r in street_rows if r['main_street_intersection']],'blockface_geometry_verified':False},
  {**common,'id':'mobility:wellesley-parking-reference','name':'Wellesley second-floor parking reference','kind':'district_reported_public_parking_context','geometry':wgeo,'geometry_basis':'Exact City address-reference point; not garage entrance, bay or whole-building parcel acceptance','source_ids':['district_parking','city_address_context'],'reported_total_spaces':None,'reported_parking_level':2,'reported_public_access_statement':'District operator reports public parking spaces on second floor; legal/current access unverified','hours':None,'address_source_entity_ids':[r['entity_id'] for r in addresses],'source_address_parcel_references':[r['source_fields'].get('PID') for r in addresses],'garage_parcel_id':None,'source_parcel_limit':'A source address PID may be a condo/unit record; not promoted to garage ownership/wholebuilding identity'},
  {**common,'id':'mobility:college-park-center-ev-reference','name':'College Park Neighborhood Center EV reference','kind':'official_charger_count_reference_not_vehicle_capacity','geometry':point_from_page(evtext),'geometry_basis':'Official City facility reference point, not stall or charger/entrance survey','source_ids':['college_park_ev'],'reported_charger_count':int(ev[1]),'reported_total_vehicle_spaces':None,'reported_address':'2393 Elizabeth Avenue','static_web_label':'Number of available electric chargers','live_charger_availability':None,'charger_count_is_not_parking_space_count':True},
 ]
 source_by_id={r['id']:r for r in register}
 for row in facilities:
  row['sources']=[source_by_id[k] for k in row['source_ids']];row['time_zone_basis']='Orlando local wall-clock reference; source does not specify timezone/effective dates';row['scope']={'in_neighborhood':shape(row['geometry']).intersects(scopes['neighborhood']) if row['geometry'] else None,'intersects_main_street':shape(row['geometry']).intersects(scopes['main_street']) if row['geometry'] else None}
  if row['geometry'] and not row['scope']['in_neighborhood']:raise ValueError('Named local reference is outside actual official neighborhood')
 client=Client(root/'data/cache/mobility_inventory',offline=offline);discovery=[]
 for term in ['parking','bike','scooter']:
  data=client.get('https://api.us.socrata.com/api/catalog/v1',{'domains':'data.cityoforlando.net','q':term,'limit':100});discovery.append({'source':'City Socrata catalog','query':term,'returned':[{'id':r['resource'].get('id'),'title':r['resource'].get('name'),'type':r['resource'].get('type')} for r in data.get('results',[])],'qualification':'No selected capacity/restriction/occupancy inventory; keyword search is not proof no unpublished inventory exists'})
 query='orgid:mMuoPCaIYD4wEgDl AND (parking OR bicycle OR scooter OR micromobility OR rack)';ag=client.get('https://www.arcgis.com/sharing/rest/search',{'f':'json','q':query,'num':100});discovery.append({'source':'City official ArcGIS organization catalog','query':query,'returned':[{'id':r['id'],'title':r['title'],'type':r['type'],'url':r.get('url')} for r in ag.get('results',[])],'qualification':'BikeFacilities is lane/trail planning, not rack/parking-space inventory; no selected public capacity layer'})
 for access in client.accesses:
  path=client.cache/(hashlib.sha256(access['url'].encode()).hexdigest()+'.json');deps.extend([path,path.with_suffix('.provenance.json')])
 packet={'schema':'twin.mobility-inventory-reference/1','source_snapshot':active['snapshot'],'built_utc':now(),'coverage_scope':'Four bounded CollegePark source contexts; NOT comprehensive parking/rack/corral census','source_register':register,'tables':{'local_facility_references':facilities,'published_study_existing_facility_counts':summaries,'study_proposed_recommendations':proposed},'field_dictionary':{'id':'Namespaced document/context reference, not a verified physical space/garage/rack ID','geometry':'Official facility/address/centerline context only; never space outlines or surveyed entrances','reported_total_spaces':'Attributed operator text/arithmetic; legally usable capacity remains unknown','reported_charger_count':'Static City page charger count, not spaces or live availability','parking_max_stay_minutes':'Operator reported time limit; current legal signs/effective date not verified','reported_parking_level':'Operator floor statement; not story count or elevation','source_address_parcel_references':'Exact original City address PID reference; unit/whole-garage identity unresolved','observation_date':'Actual inventory measurement date, unknown when not supplied; not retrieval or document date','study_recommendations':'Proposed source PDFtable rows; not existing, capacity or accepted CollegePark location'},'first_five_safe_rows':{n:rows[:5] for n,rows in {'local_facility_references':facilities,'published_study_existing_facility_counts':summaries,'study_proposed_recommendations':proposed}.items()},'study_review':{'report_document_date':'2026-07-31','pdf_metadata_creation_date':report.metadata.get('/CreationDate'),'inventory_observation_date':None,'actual_report_physical_pages':len(pages),'study_map_physical_page':6,'named_scope':['City District','Creative Village','Ivanhoe Village','Parramore','Thornton Park','major venues'],'CollegePark_named_in_scope':False,'exact_area_intersection_with_CollegePark':None,'geographic_limit':'Actual study map and legend inspected; no GIS boundary delivered, so no exact zero-overlap claim','appendix_D_physical_page':90,'appendix_D_is_divider_only':True,'appendix_D_annotation_count':len(report.pages[89].get('/Annots',[])),'embedded_attachment_names':list(report.attachments),'embedded_GIS_inventory_found':False,'source_recommendation_rows':len(proposed),'accepted_existing_local_bike_or_scooter_sites_from_report':0,'zero_is_not_physical_absence':True},'source_conflicts':conflicts,'discovery':discovery,'requests':client.accesses,'unresolved':[{'artifact':'Original GIS/FieldMaps existing and proposed micromobility facility inventory, capacity attributes, geometry, inventory dates and study boundary','evidence':'Final report references GIS and AppendixD, but retrieved PDF has divider only and no GIS attachment','action':'Obtain an existing public download or authorized records copy; no outreach performed'},{'artifact':'CollegePark space/blockface/garage/rack/corral inventory with stableIDs, signs, hours, loading/accessible/reserved categories and access agreements','known_subset':'Attributed local facility/rule references only'},{'artifact':'Weekday/weekend/event occupancy and turnover observations with actual intervals/weather/context','status':'Not acquired; no decorative-car/charger/trip-data substitution'}],'dependencies':{rel(p,root):sha(p) for p in set(deps)},'limits':['A document date, website retrieval or proposed recommendation is not a local inventory observation.','Operator guidance is not City law, a public-access agreement, a title record or ADA certification.','No district-wide supply, demand, deficit, utilization or current availability is established.','Original source HTML/PDFs/rendered pages stay ignored/local; coverage page contains no source pixels.'],'private_booms_read':False,'agency_contacted':False,'decorative_scene_cars_counted':False,'private_access_inferred':False,'active_snapshot_changed':False,'scene_changed':False}
 packet['table_field_dictionaries']=table_dictionaries(packet['tables'])
 bodies={'packet.json':json.dumps(packet,indent=2,allow_nan=False).encode('utf8'),'coverage.html':map_html(scopes,facilities,project).encode('utf8')}
 if rp.exists():
  if any(sha(out/n)!=h for n,h in prior['artifacts'].items()):raise ValueError('Mobility output changed during build')
  backup=out/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
  for name in [*expected,'receipt.json']:shutil.copy2(out/name,backup/name)
 out.mkdir(parents=True,exist_ok=True)
 for name,body in bodies.items():path=out/(name+'.tmp');path.write_bytes(body);path.replace(out/name)
 atomic_json(rp,{'source_snapshot':active['snapshot'],'artifacts':{n:sha(out/n) for n in expected}});return packet

def validate(root=ROOT):
 root=Path(root).resolve();out=root/OUT;rp=read(out/'receipt.json');p=read(out/'packet.json')
 if p.get('schema')!='twin.mobility-inventory-reference/1' or not p.get('dependencies') or set(rp.get('artifacts',{}))!={'packet.json','coverage.html'}:raise ValueError('Incomplete mobility integrity proof')
 if p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or rp['source_snapshot']!=p['source_snapshot']:raise ValueError('Mobility snapshot stale')
 for name,h in rp['artifacts'].items():
  if sha(out/name)!=h:raise ValueError('Mobility artifact modified')
 for name,h in p['dependencies'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root) or sha(path)!=h:raise ValueError('Mobility source/dependency changed')
 for name,rows in p['tables'].items():
  dictionary=p.get('table_field_dictionaries',{}).get(name,{})
  if {k for r in rows for k in r}-set(dictionary):raise ValueError('Incomplete mobility table field dictionary: '+name)
  if name=='study_proposed_recommendations' and any('source_fields.'+k not in dictionary for r in rows for k in r['source_fields']):raise ValueError('Incomplete original recommendation field dictionary')
 return p

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args();build(offline=not args.live);p=validate();print(json.dumps({'snapshot':p['source_snapshot'],'tables':{n:len(r) for n,r in p['tables'].items()},'study_review':p['study_review'],'source_conflicts':p['source_conflicts']},indent=2))
