"""Offline public parcel/building QA. Reports exceptions; never changes match decisions."""
from pathlib import Path
import argparse, collections, datetime, hashlib, json, math, os, sys, urllib.parse

ROOT=Path(__file__).resolve().parents[1]
PARCEL_FIELDS=('id','parcel_id','source_parcel_id','source_object_id','site_address','stories','year_built','area_acres')
BUILDING_FIELDS=('id','usd_path','source_parcel_id','parcel_id','parcel_feature_id','site_address','match_method','overlap_ratio')
REQUIRED_PARCEL={'id','parcel_id','source_parcel_id','source_object_id','stories'}
REQUIRED_BUILDING={'id','usd_path','source_parcel_id','parcel_id','parcel_feature_id','match_method','candidate_parcels'}
EXACT='id_and_geometry'
PARCEL_URL='https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4'
FOOTPRINT_URL='https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28'

def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(temp,path)
def positive_integer(value):
    try:n=float(value)
    except (TypeError,ValueError):return None
    return int(n) if not isinstance(value,bool) and math.isfinite(n) and 0<n<=100 and n.is_integer() else None
def safe(row,fields):return {k:row.get(k) for k in fields}
def duplicates(rows,key):
    counts=collections.Counter(r.get(key) for r in rows if r.get(key) not in [None,''])
    return {k:n for k,n in counts.items() if n>1}
def source_key(parcel_id,building_number):
    # Generated USD Building_#### names are only stable inside a snapshot.
    if not isinstance(parcel_id,str) or not parcel_id or not building_number:return None
    return 'ocpa-building:'+parcel_id+':'+str(building_number)

def active_folder(root):
    pointer=read_json(root/'data/processed/active.json');folder=(root/pointer['relative_path']).resolve()
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Snapshot path escapes data/snapshots')
    return folder,pointer

def scene_evidence(root,parcels):
    sys.path.insert(0,str(root/'.dependencies'))
    from pxr import Usd,UsdGeom
    from shapely.geometry import Polygon,shape
    from shapely import transform
    from shapely.ops import unary_union
    from pyproj import Transformer
    projection=Transformer.from_crs(4326,32617,always_xy=True);ox,oy=projection.transform(-81.389,28.572)
    def xy(x,y,z=None):
        xx,yy=projection.transform(x,y);return xx-ox,yy-oy
    geoms={p['properties']['id']:transform(shape(p['geometry']),xy,interleaved=False) for p in parcels}
    stage=Usd.Stage.Open(str(root/'scene/college_park.usda'))
    if not stage:raise ValueError('Base scene could not be opened')
    records=[]
    for prim in stage.GetPrimAtPath('/World/Buildings').GetChildren():
        meta=prim.GetCustomData();mesh=UsdGeom.Mesh(prim);pts=mesh.GetPointsAttr().Get()
        indices=mesh.GetFaceVertexIndicesAttr().Get();sizes=mesh.GetFaceVertexCountsAttr().Get();offset=0;triangles=[]
        for count in sizes:
            if count==3:triangles.append(Polygon([(pts[j][0],pts[j][1]) for j in indices[offset:offset+count]]))
            offset+=count
        footprint=unary_union(triangles)
        records.append({'id':prim.GetName(),'usd_path':str(prim.GetPath()),'source_parcel_id':str(meta.get('parcelId','')),
           'building_number':str(meta.get('buildingNumber','')),
           'source_object_ids':[int(v) for v in str(meta.get('sourceObjectIds','')).split(',') if v],
           'footprint':footprint})
    return records,geoms

def audit_records(parcels,buildings,heights,snapshot,scene_rows=None,parcel_geometries=None,footprints=None):
    pby={p.get('id'):p for p in parcels};bby={b.get('id'):b for b in buildings}
    queues={k:[] for k in ['duplicate_parcel_ids','non_exact_links','link_integrity','multiple_buildings_per_parcel',
       'floor_conflicts','stale_height_evidence','scene_source_exceptions','identifier_issues','schema_issues']}
    for name,rows,required in [('parcels',parcels,REQUIRED_PARCEL),('buildings',buildings,REQUIRED_BUILDING)]:
        for i,row in enumerate(rows):
            missing=sorted(required-set(row))
            if missing:queues['schema_issues'].append({'table':name,'row':i,'missing_fields':missing})
    for pin,count in duplicates(parcels,'parcel_id').items():
        queues['duplicate_parcel_ids'].append({'parcel_id':pin,'feature_count':count,
           'features':[safe(p,PARCEL_FIELDS) for p in parcels if p.get('parcel_id')==pin],
           'decision':'Preserve distinct source features; duplicate parcel ID does not establish duplicate geometry.'})
    for table,rows,keys in [('parcels',parcels,['id','source_object_id']),('buildings',buildings,['id','usd_path'])]:
        for key in keys:
            for value,count in duplicates(rows,key).items():queues['identifier_issues'].append({'table':table,'field':key,'value':value,'count':count})
    for p in parcels:
        if not isinstance(p.get('parcel_id'),str) or not p.get('parcel_id'):
            queues['identifier_issues'].append({'table':'parcels','id':p.get('id'),'reason':'Parcel ID must be a nonempty string'})
        if p.get('source_parcel_id')!=p.get('parcel_id'):
            queues['identifier_issues'].append({'table':'parcels','id':p.get('id'),'reason':'Normalized/source parcel IDs differ; review normalization'})
        if p.get('id')!='ocpa:'+str(p.get('source_object_id')):
            queues['identifier_issues'].append({'table':'parcels','id':p.get('id'),'reason':'Feature ID does not match recorded source object ID'})
    accepted=collections.defaultdict(list);all_links=collections.defaultdict(list)
    for b in buildings:
        row=safe(b,BUILDING_FIELDS);p=pby.get(b.get('parcel_feature_id'));errors=[]
        if b.get('match_method')!=EXACT:queues['non_exact_links'].append({**row,'candidate_parcels':b.get('candidate_parcels',[]),'accepted':False})
        if b.get('parcel_id'):all_links[b['parcel_id']].append(b['id'])
        if b.get('match_method')==EXACT:
            accepted[b.get('parcel_id')].append(b['id'])
            if not p:errors.append('Assigned parcel feature missing')
            if b.get('source_parcel_id')!=b.get('parcel_id'):errors.append('Source parcel ID differs from assigned exact parcel ID')
            if p and p.get('parcel_id')!=b.get('parcel_id'):errors.append('Assigned feature parcel ID mismatch')
            ratio=b.get('overlap_ratio')
            if isinstance(ratio,bool) or not isinstance(ratio,(float,int)) or not math.isfinite(ratio) or not 0<=ratio<=1:errors.append('Stored overlap is not a finite ratio in [0,1]')
            elif ratio<.8:errors.append('Stored exact overlap below threshold')
        if errors:queues['link_integrity'].append({**row,'reasons':errors})
    for pin,ids in accepted.items():
        if len(ids)>1:queues['multiple_buildings_per_parcel'].append({'parcel_id':pin,'accepted_building_count':len(ids),'building_ids':sorted(ids),
            'decision':'Preserve one-to-many; do not copy parcel story counts to every group.'})
    current_heights={};duplicate_heights=duplicates(heights,'building_id')
    for h in heights:
        if h.get('source_snapshot')!=snapshot:
            queues['stale_height_evidence'].append({'building_id':h.get('building_id'),'height_snapshot':h.get('source_snapshot'),'active_snapshot':snapshot})
        else:current_heights[h.get('building_id')]=h
    for bid,count in duplicate_heights.items():queues['identifier_issues'].append({'table':'heights','field':'building_id','value':bid,'count':count})
    for h in current_heights.values():
        b=bby.get(h.get('building_id'),{});p=pby.get(b.get('parcel_feature_id'),{})
        first=positive_integer(h.get('source_building_floor'));second=positive_integer(p.get('stories')) if b.get('match_method')==EXACT else None
        copied=positive_integer(h.get('source_parcel_stories'))
        if copied!=second:queues['stale_height_evidence'].append({'building_id':h.get('building_id'),'reason':'Copied parcel stories differ from current assigned parcel attributes','copied_parcel_stories':copied,'current_assigned_parcel_stories':second})
        if first and second and first!=second:
            queues['floor_conflicts'].append({**safe(b,BUILDING_FIELDS),'source_building_floor':first,'source_parcel_stories':second,
              'difference':abs(first-second),'height_method':h.get('method'),'height_quality':h.get('quality'),
              'floors_used':h.get('floors_used'),'accepted_buildings_on_parcel':len(accepted.get(b.get('parcel_id'),[])),
              'severity':'large_conflict' if abs(first-second)>1 else 'one_floor_disagreement',
              'decision':'Review source definitions and current evidence; no change made by audit.'})
    source_index={str(f['properties'].get('OBJECTID')):f['properties'] for f in (footprints or [])}
    stable_rows=[];geometry_checked=0
    for scene in scene_rows or []:
        b=bby.get(scene['id']);errors=[]
        if not b:errors.append('Base scene group missing snapshot building record')
        if b and scene['source_parcel_id']!=b.get('source_parcel_id'):errors.append('Base scene source parcel ID differs from snapshot')
        for oid in scene['source_object_ids']:
            raw=source_index.get(str(oid))
            if raw is None:errors.append('Missing footprint source object '+str(oid))
            elif str(raw.get('PID'))!=scene['source_parcel_id']:errors.append('Footprint PID differs for source object '+str(oid))
            elif str(raw.get('BLDG_NUM'))!=scene['building_number']:errors.append('Footprint BLDG_NUM differs for source object '+str(oid))
        raw_floors=[positive_integer(source_index.get(str(oid),{}).get('FLOOR_NUM')) for oid in scene['source_object_ids']]
        raw_floor=max([f for f in raw_floors if f],default=None)
        h=current_heights.get(scene['id'])
        if h and raw_floor!=positive_integer(h.get('source_building_floor')):errors.append('Height evidence building floor differs from current footprint attributes')
        recomputed=None
        if b and b.get('parcel_feature_id') and parcel_geometries is not None:
            assigned=parcel_geometries.get(b['parcel_feature_id']);fp=scene.get('footprint')
            if assigned is not None and fp is not None and fp.area>0:
                recomputed=fp.intersection(assigned).area/fp.area;geometry_checked+=1
                stored=b.get('overlap_ratio')
                if isinstance(stored,bool) or not isinstance(stored,(int,float)) or not math.isfinite(stored) or not 0<=stored<=1:errors.append('Stored overlap is not a finite ratio in [0,1]')
                elif abs(recomputed-stored)>.00011:errors.append('Stored overlap differs from independent recomputation')
                if b.get('match_method')==EXACT and recomputed<.8:errors.append('Independent exact overlap below threshold')
        stable_rows.append({'building_id':scene['id'],'usd_path':scene['usd_path'],
           'source_building_key':source_key(scene['source_parcel_id'],scene['building_number']),
           'source_parcel_id':scene['source_parcel_id'],'source_building_number':scene['building_number'],
           'footprint_source_object_ids':sorted(scene['source_object_ids']),
           'footprint_max_positive_integer_floor_num':raw_floor,
           'assigned_parcel_feature_id':b.get('parcel_feature_id') if b else None,
           'independent_assigned_overlap_ratio':round(recomputed,6) if recomputed is not None else None,
           'webmap_url':'https://webmap.ocpafl.org/search','webmap_search_token':scene['source_parcel_id'],
           'map_link_status':'Generic official search page; no verified parcel-specific deep link',
           'footprint_query_url':FOOTPRINT_URL+'/query?'+urllib.parse.urlencode({'f':'geojson','objectIds':','.join(map(str,scene['source_object_ids'])),'outFields':'OBJECTID,PID,BLDG_NUM,FLOOR_NUM','outSR':4326}),
           'snapshot':snapshot})
        if errors:queues['scene_source_exceptions'].append({'building_id':scene['id'],'reasons':errors})
    for key,count in duplicates(stable_rows,'source_building_key').items():queues['identifier_issues'].append({'table':'scene','field':'source_building_key','value':key,'count':count})
    scene_ids={s['id'] for s in scene_rows or []}
    if scene_rows is not None:
        for missing in sorted(set(bby)-scene_ids):queues['scene_source_exceptions'].append({'building_id':missing,'reasons':['Snapshot building absent from base scene']})
    ambiguous=[b for b in buildings if b.get('match_method')=='ambiguous_or_unmatched']
    summary={'snapshot':snapshot,'parcel_features':len(parcels),'unique_parcel_ids':len({p.get('parcel_id') for p in parcels}),
       'duplicate_parcel_id_groups':len(queues['duplicate_parcel_ids']),'buildings':len(buildings),
       'match_methods':dict(collections.Counter(b.get('match_method') for b in buildings)),
       'exact_match_percent':round(100*sum(b.get('match_method')==EXACT for b in buildings)/len(buildings),2) if buildings else None,
       'ambiguous_with_candidates':sum(bool(b.get('candidate_parcels')) for b in ambiguous),
       'unmatched_without_candidates':sum(not b.get('candidate_parcels') for b in ambiguous),
       'accepted_linked_parcels':len(accepted),'all_assigned_parcels_including_review':len(all_links),
       'accepted_one_to_many_parcels':len(queues['multiple_buildings_per_parcel']),
       'building_groups_on_accepted_one_to_many_parcels':sum(x['accepted_building_count'] for x in queues['multiple_buildings_per_parcel']),
       'current_snapshot_height_rows':len(current_heights),'height_rows_missing_for_buildings':len(set(bby)-set(current_heights)),
       'independently_recomputed_assigned_overlaps':geometry_checked,
       'exception_counts':{key:len(value) for key,value in queues.items()},'audit_changes_match_decisions':False}
    summary['floor_conflict_severity']=dict(collections.Counter(r['severity'] for r in queues['floor_conflicts']))
    summary['source_schema']={'parcel_fields':sorted(set().union(*(set(p) for p in parcels))),
      'building_fields':sorted(set().union(*(set(b) for b in buildings))),
      'required_parcel_fields':sorted(REQUIRED_PARCEL),'required_building_fields':sorted(REQUIRED_BUILDING)}
    return summary,queues,stable_rows

def build(root=ROOT):
    folder,pointer=active_folder(root);parcel_data=read_json(folder/'parcels.json');parcels=[f['properties'] for f in parcel_data['features']]
    buildings=read_json(folder/'buildings.json');heights=read_json(root/'data/heights/building_heights.json') if (root/'data/heights/building_heights.json').exists() else []
    raw=read_json(root/'data/buildings.geojson')['features'];scene,geoms=scene_evidence(root,parcel_data['features'])
    summary,queues,stable=audit_records(parcels,buildings,heights,pointer['snapshot'],scene,geoms,raw)
    sources=read_json(folder/'sources.json');parcel_source=next(s for s in sources if s['id']=='parcels')
    inputs=[folder/'parcels.json',folder/'buildings.json',folder/'sources.json',root/'scene/college_park.usda',root/'data/buildings.geojson']
    if (root/'data/heights/building_heights.json').exists():inputs.append(root/'data/heights/building_heights.json')
    hashes={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    summary.update(audit_created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mode='offline_local_snapshot_no_network',
       source_sha256=hashes,parcel_source={k:parcel_source.get(k) for k in ['api_url','source_updated','retrieved_utc','snapshot_built_utc','retrieval_quality','request_retrieval_range_utc']},
       limitations=['Stored matching decisions are audited, never promoted or rewritten.',
          'Feature object IDs identify this source version; generated USD names may change on rebuild. Preserve the source parcel + BLDG_NUM key and source-object provenance.',
          'Same parcel ID can identify distinct source geometry; duplicate IDs are not silently merged.',
          'Legacy cached responses may lack original retrieval time. Build time does not establish source freshness.',
          'Floor disagreement is a review flag, not proof either source is wrong; all floor-derived heights remain estimates.',
          'This rectangle is not an official district boundary; overlap validation is against source reference geometry, not a survey.'])
    preview={'parcels':{'fields':list(PARCEL_FIELDS),'first_five_rows':[safe(p,PARCEL_FIELDS) for p in parcels[:5]]},
      'buildings':{'fields':list(BUILDING_FIELDS),'first_five_rows':[safe(b,BUILDING_FIELDS) for b in buildings[:5]]},
      'exception_samples':{k:rows[:5] for k,rows in queues.items()}}
    for filename,data in [('parcel_audit_quality.json',summary),('parcel_audit_exceptions.json',queues),('parcel_audit_identifiers.json',stable),('parcel_audit_preview.json',preview)]:write_json(root/'data/processed'/filename,data)
    print(json.dumps(summary,indent=2));return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true',help='Audit is always offline; flag is explicit documentation.')
    parser.parse_args();build()
