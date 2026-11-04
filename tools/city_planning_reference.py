"""Full-neighborhood City zoning/FLU parcel context, never entitlement or scene data.

Run: python tools/city_planning_reference.py [--live]
Default offline; --live fills only missing bounded public requests. Outputs and
rollback bundles remain in data/processed/city_planning_reference. Original source
geometry is never repaired; invalid features enter an explicit exception queue.
Land-area denominators use EPSG:32617 unions, separate from overlapping tax rows.
"""
from pathlib import Path
import os,sys,json,hashlib,collections,shutil,urllib.parse,argparse
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
import shapely
from shapely.geometry import shape,mapping
from shapely.ops import unary_union,transform
from shapely.strtree import STRtree
from pyproj import Transformer
from data_pipeline import Client,SOURCES,arcgis,atomic_json,now,GIS
from city_adapter_contract import CheckedClient,EXTRA
OUT=Path('data/processed/city_planning_reference')
CACHES=('city_planning_reference','official','city_adapter_discovery','public_ownership','edgewater_audit')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def relative(p,root):return Path(p).relative_to(root).as_posix()

class CachedPublic:
    """Reuse known public caches without moving/replacing any source bytes."""
    def __init__(self,root,live=False):self.root,self.live,self.used,self.requests=root,live,{},[]
    def get(self,url,params=None):
        target=url+('?' + urllib.parse.urlencode(params) if params else '')
        key=hashlib.sha256(target.encode()).hexdigest()+'.json'
        folder=next((self.root/'data/cache'/n for n in CACHES if (self.root/'data/cache'/n/key).is_file()),self.root/'data/cache/city_planning_reference')
        c=Client(folder,offline=not self.live);value=c.get(url,params);p=folder/key
        self.requests.extend(c.accesses)
        self.used[relative(p,self.root)]=sha(p)
        provenance=p.with_suffix('.provenance.json')
        if provenance.exists():self.used[relative(provenance,self.root)]=sha(provenance)
        return value

def split_code(value):
    if value is None:return {'original':None,'base':None,'overlay_tokens':[]}
    if not isinstance(value,str):raise ValueError('Zoning code must retain source string')
    parts=value.split('/')
    return {'original':value,'base':parts[0],'overlay_tokens':parts[1:]}

def denominator(geometries,scope):
    clipped=[g.intersection(scope) for g in geometries if g.intersects(scope)]
    total=sum(g.area for g in clipped);union=unary_union(clipped) if clipped else shapely.GeometryCollection()
    return {'scope_area_m2':scope.area,'source_feature_area_sum_m2':total,
        'unique_covered_area_m2':union.area,'overlapping_source_area_excess_m2':max(0.,total-union.area),
        'unrepresented_area_m2':max(0.,scope.area-union.area),'coverage_fraction':union.area/scope.area}

def memberships(parcel,features,tree,kind,threshold=.01):
    rows=[]
    for i in tree.query(parcel,predicate='intersects'):
        f=features[int(i)];area=parcel.intersection(f['projected']).area
        if area<=threshold:continue
        p=f['properties'];r={'source_feature_id':f['source_feature_id'],'source_object_id':str(p['OBJECTID']),
            'intersection_m2':area,'parcel_clipped_area_fraction':area/parcel.area}
        if kind=='zoning':r.update({'zoning':split_code(p.get('Zoning')),'pd_name':p.get('PD_NAME'),'source_format_date':p.get('FormatDate')})
        else:r['future_land_use']=p.get('LanduseType')
        rows.append(r)
    return sorted(rows,key=lambda x:x['source_feature_id'])

def verify_previous(root):
    out=root/OUT;receipt=out/'receipt.json';expected={'packet.json','planning_features.geojson','coverage.svg'}
    if not receipt.exists():
        if any((out/n).exists() for n in expected):raise ValueError('Preserve unreceipted planning outputs')
        return
    rec=read(receipt)
    if set(rec.get('artifacts',{}))!=expected:raise ValueError('Planning receipt incomplete')
    if any(not (out/n).is_file() or sha(out/n)!=v for n,v in rec['artifacts'].items()):raise ValueError('Preserve manually modified planning outputs')

def validate(root=ROOT):
    root=Path(root).resolve();verify_previous(root);out=root/OUT;p=read(out/'packet.json')
    if p['schema']!='twin.city-planning-reference/1' or p['source_snapshot']!=read(root/'data/processed/active.json')['snapshot']:raise ValueError('Planning source snapshot/schema stale')
    if read(out/'receipt.json').get('source_snapshot')!=p['source_snapshot']:raise ValueError('Planning receipt snapshot stale')
    required={'tools/city_planning_reference.py','tools/data_pipeline.py','tools/city_adapter_contract.py',
        'data/processed/active.json','data/processed/study_boundaries.geojson'}
    if not isinstance(p.get('dependencies'),dict) or not required.issubset(p['dependencies']):raise ValueError('Planning dependencies missing')
    if set(p.get('tables',{}))!={'planning_parcel_context','planning_zoning_areas','planning_future_land_use_areas'}:raise ValueError('Planning table contract changed')
    for name,rows in p['tables'].items():
        dictionary=p.get('table_field_dictionaries',{}).get(name,{})
        if any(set(r)-set(dictionary) for r in rows):raise ValueError('Undocumented planning fields')
        if p.get('first_five_safe_rows',{}).get(name)!=rows[:5]:raise ValueError('Planning preview mismatch')
    for n,v in p['dependencies'].items():
        q=(root/n).resolve()
        if not q.is_relative_to(root) or not q.is_file() or sha(q)!=v:raise ValueError('Planning source dependency changed')
    return p

def build(root=ROOT,live=False):
    root=Path(root).resolve();verify_previous(root);active_path=root/'data/processed/active.json';active=read(active_path)
    boundary_path=root/'data/processed/study_boundaries.geojson';scopes_wgs={f['properties']['scope']:shape(f['geometry']) for f in read(boundary_path)['features']}
    project=Transformer.from_crs(4326,32617,always_xy=True).transform
    scopes={k:transform(project,v) for k,v in scopes_wgs.items()};scope=scopes['neighborhood']
    c=CachedPublic(root,live);sources={'zoning':SOURCES['zoning'],'future_land_use':EXTRA['future_land_use'],
        'parcels':{**SOURCES['parcels'],'fields':['OBJECTID','PARCEL','DOR_CODE','EXEMPT_CODE']}}
    layers={};register=[];exceptions=[];excluded=[];geo=[]
    for kind,source in sources.items():
        fc,meta=arcgis(CheckedClient(c),source,scopes_wgs['neighborhood'].bounds);features=[]
        for f in fc['features']:
            p=f['properties'];identifier=str(p['OBJECTID']);g=shape(f['geometry']) if f.get('geometry') else None
            if g is None or g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon'):
                exceptions.append({'source':kind,'source_object_id':identifier,'reason':'invalid_or_missing_source_polygon_not_repaired'});continue
            local=transform(project,g).intersection(scope)
            if local.area<=.01:
                excluded.append({'source':kind,'source_object_id':identifier,'intersection_m2':local.area,
                    'reason':'outside_neighborhood_or_at_most_0.01m2_numerical_sliver'})
                continue
            features.append({'source_feature_id':('ocpa:' if kind=='parcels' else 'city:'+kind+':')+identifier,'properties':p,'projected':local})
            if kind!='parcels':geo.append({'type':'Feature','geometry':mapping(g.intersection(scopes_wgs['neighborhood'])),
                'properties':{'entity_type':'planning_reference_polygon','source':kind,'source_object_id':identifier,
                    **{n:p.get(n) for n in source['fields']},'governing_conditions_verified':False}})
        layers[kind]=features
        register.append({'source':kind,'publisher':source.get('publisher','City of Orlando'),'api_url':source['url'],
            'metadata_url':source['url']+'?f=json','native_spatial_reference':meta.get('extent',{}).get('spatialReference'),
            'normalized_crs':'EPSG:4326 geometry; EPSG:32617 square-meter area calculations',
            'source_last_edit_unix_ms':meta.get('editingInfo',{}).get('lastEditDate'),
            'inventory_acquisition_date':None,'effective_ordinance_date':None,'update_frequency':None,
            'reuse_original':meta.get('copyrightText'),'pagination':'bounded object-ID discovery +50-ID batches',
            'auth':'public read, no credentials','rate_limit':None,'timeout_seconds':60,'maximum_attempts':3,
            'backoff_seconds':[1,2],'incremental_refresh':'No verified change/deletion token; bounded complete query only',
            'bbox_source_rows':len(fc['features']),
            'valid_positive_neighborhood_rows':len(features),
            'fields_original':[f for f in meta.get('fields',[]) if f['name'] in source['fields'] and f['name']!='EXEMPT_CODE']})
    trees={k:STRtree([f['projected'] for f in layers[k]]) for k in ('zoning','future_land_use')};rows=[]
    for f in layers['parcels']:
        p=f['properties'];pin=p.get('PARCEL')
        if not isinstance(pin,str) or not pin:raise ValueError('Original parcel ID must remain nonempty string')
        g=f['projected'];z=memberships(g,layers['zoning'],trees['zoning'],'zoning');flu=memberships(g,layers['future_land_use'],trees['future_land_use'],'future_land_use')
        rows.append({'source_feature_id':f['source_feature_id'],'source_object_id':str(p['OBJECTID']),'parcel_id':pin,
            'neighborhood_clipped_area_m2':g.area,'main_street_intersection_m2':g.intersection(scopes['main_street']).area,
            'zoning_memberships':z,'future_land_use_memberships':flu,
            'multiple_zoning_code_context':len({x['zoning']['original'] for x in z})>1,
            'pd_condition_review_required':any(x['zoning']['base']=='PD' or x['pd_name'] for x in z),
            'link_method':'positive_polygon_intersection_over_0.01m2_reference_only',
            'governing_conditions_verified':False,'current_use_verified':False,'legal_ownership_verified':False})
    areas={k:{name:denominator([f['projected'] for f in layer],s) for name,s in scopes.items()} for k,layer in layers.items()}
    category_areas={}
    for kind,field in [('zoning','Zoning'),('future_land_use','LanduseType')]:
        groups=collections.defaultdict(list)
        for f in layers[kind]:groups[str(f['properties'].get(field))].append(f['projected'])
        category_areas[kind]=[{'exact_source_code':code,'unique_neighborhood_area_m2':unary_union(gs).area,
            'source_polygon_count':len(gs),'percent_of_whole_neighborhood':100*unary_union(gs).area/scope.area} for code,gs in sorted(groups.items())]
    dependencies={relative(p,root):sha(p) for p in [Path(__file__),root/'tools/data_pipeline.py',root/'tools/city_adapter_contract.py',active_path,boundary_path]};dependencies.update(c.used)
    packet={'schema':'twin.city-planning-reference/1','source_snapshot':active['snapshot'],'built_utc':now(),
        'source_register':register,'rows':rows,'first_five_safe_rows':rows[:5],
        'counts':{'source_parcel_features':len(rows),'distinct_parcel_id_strings':len({r['parcel_id'] for r in rows}),
            'multiple_zoning_code_context_features':sum(r['multiple_zoning_code_context'] for r in rows),
            'pd_condition_review_required_features':sum(r['pd_condition_review_required'] for r in rows)},
        'denominators':areas,'exact_code_area_breakdown':category_areas,'exceptions':exceptions,'excluded':excluded,
        'field_dictionary':{'source_feature_id':'Publisher source-feature identity, not physical site count',
            'source_object_id':'Original OBJECTID as string','parcel_id':'Original OCPA PARCEL string; no reversal/coercion',
            'neighborhood_clipped_area_m2':'Source-feature polygon intersected with official neighborhood, EPSG32617 area',
            'main_street_intersection_m2':'Separate official Main Street polygon intersection, square meters',
            'zoning_memberships':'All intersecting City polygons; original exact zoning, lexical base/suffix tokens, PD name/date and source IDs preserved',
            'future_land_use_memberships':'Intersecting City FLU polygons; original LanduseType and source IDs',
            'multiple_zoning_code_context':'More than one exact zoning string with intersection >0.01m2; not legal split-zoning determination',
            'pd_condition_review_required':'Source PD base code or nonempty PD name; governing ordinance/plan still required',
            'link_method':'Geometric reference correspondence only; numerical area floor explicitly0.01m2',
            'governing_conditions_verified':'Alwaysfalse; no ordinance/overlay/PD entitlements established',
            'current_use_verified':'Alwaysfalse; planning designation is not observed physical use',
            'legal_ownership_verified':'Alwaysfalse; zoning/FLU is not legal title'},
        'limits':['Original code strings retained; slash split is lexical only, not ordinance interpretation.',
            'C/T/PD or other tokens do not infer commercial/townhouse/developable status or approval.',
            'Unique union land area is distinct from overlapping source-feature area sums and tax-row counts.',
            'Source parcel features/condominium records are not a count of physical properties/buildings.',
            'Invalid planning polygons are quarantined without repair; coverage gaps and overlap excess remain explicit.',
            'Threshold0.01m2 excludes numerical slivers; source positional accuracy unknown; no survey tolerance.',
            'Current legal zoning/effective ordinances, PD amendments, vacancy and park-site acceptance remain unresolved.'],
        'requests':c.requests,'dependencies':dependencies,'active_snapshot_changed':False,'scene_changed':False,'private_data_read':False}
    packet['tables']={'planning_parcel_context':rows,
        'planning_zoning_areas':category_areas['zoning'],
        'planning_future_land_use_areas':category_areas['future_land_use']}
    area_dictionary={'exact_source_code':'Original zoning combination or LanduseType, no entitlement inference',
        'unique_neighborhood_area_m2':'Union of same-code polygons clipped to neighborhood, EPSG32617 square meters',
        'source_polygon_count':'Distinct source polygon rows; not parcels or physical sites',
        'percent_of_whole_neighborhood':'100 times unique same-code area divided by full official neighborhood; overlapping codes need not sum to100'}
    parcel_dictionary=dict(packet['field_dictionary'])
    parcel_dictionary.update({'zoning_memberships[].source_feature_id':'City zoning source polygon identity',
        'zoning_memberships[].source_object_id':'Original City OBJECTID as string',
        'zoning_memberships[].intersection_m2':'Clipped source parcel/zoning polygon area in EPSG32617 square meters',
        'zoning_memberships[].parcel_clipped_area_fraction':'Intersection divided by clipped source-feature parcel area; not unique land denominator',
        'zoning_memberships[].zoning.original':'Original exact source zoning string, null preserved',
        'zoning_memberships[].zoning.base':'Lexical token before first slash; no legal definition inferred',
        'zoning_memberships[].zoning.overlay_tokens':'Ordered lexical suffix strings; not independently verified governing overlay conditions',
        'zoning_memberships[].pd_name':'Original PD_NAME; null remains unknown',
        'zoning_memberships[].source_format_date':'Original FormatDate; not assumed adoption/effective date',
        'future_land_use_memberships[].source_feature_id':'City future land use source polygon identity',
        'future_land_use_memberships[].source_object_id':'Original City OBJECTID as string',
        'future_land_use_memberships[].intersection_m2':'Clipped parcel/FLU intersection in EPSG32617 square meters',
        'future_land_use_memberships[].parcel_clipped_area_fraction':'Intersection divided by clipped source-feature parcel area',
        'future_land_use_memberships[].future_land_use':'Original LanduseType; planning reference, not current use/approval'})
    packet['table_field_dictionaries']={'planning_parcel_context':parcel_dictionary,
        'planning_zoning_areas':area_dictionary,'planning_future_land_use_areas':area_dictionary}
    packet['first_five_safe_rows']={k:v[:5] for k,v in packet['tables'].items()}
    verify_previous(root);out=root/OUT
    if (out/'receipt.json').exists():
        backup=out/'backups'/now().replace(':','_');backup.mkdir(parents=True)
        for n in ['packet.json','planning_features.geojson','coverage.svg','receipt.json']:shutil.copy2(out/n,backup/n)
    atomic_json(out/'packet.json',packet);atomic_json(out/'planning_features.geojson',{'type':'FeatureCollection','features':geo})
    left,bottom,right,top=scope.bounds;scale=800/(right-left);height=(top-bottom)*scale
    paths=[]
    for f in layers['zoning']:
        geom=f['projected'];code=str(f['properties'].get('Zoning'));color='#'+hashlib.sha256(code.encode()).hexdigest()[:6]
        for poly in shapely.get_parts(geom):
            if poly.geom_type!='Polygon':continue
            d=' '.join('M '+' L '.join(f'{(x-left)*scale:.2f},{(top-y)*scale:.2f}' for x,y in ring.coords)+' Z' for ring in [poly.exterior,*poly.interiors])
            paths.append(f'<path d="{d}" fill="{color}" fill-rule="evenodd" stroke="#333" stroke-width="0.3"/>')
    (out/'coverage.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height:.2f}" role="img" aria-label="Clipped City zoning references; white gaps are unresolved"><rect width="800" height="{height}" fill="white"/>'+''.join(paths)+'</svg>',encoding='utf-8')
    atomic_json(out/'receipt.json',{'schema':packet['schema'],'source_snapshot':active['snapshot'],
        'artifacts':{n:sha(out/n) for n in ['packet.json','planning_features.geojson','coverage.svg']}})
    return packet

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--live',action='store_true');a=ap.parse_args()
    p=build(live=a.live);print(json.dumps({'counts':p['counts'],'exceptions':len(p['exceptions']),
        'denominators':p['denominators'],'packet_sha256':sha(ROOT/OUT/'packet.json')}))
