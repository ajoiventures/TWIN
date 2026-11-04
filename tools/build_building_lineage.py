"""Publish guarded source lineage for an immutable active building snapshot."""
from pathlib import Path
import sys, os, json, hashlib, collections, shutil
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):
    os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from data_pipeline import building_joins, atomic_json, now
from semantic_registry import building_identity
from pxr import Usd, UsdGeom, Sdf
_GEOMETRY_CACHE={}

OUTPUT='data/processed/building_lineage.json'
SOURCE_FIELDS=('source_building_key','source_building_number','source_object_ids',
        'candidate_parcel_features','match_confidence_basis','join_state')
FIELDS=SOURCE_FIELDS+('entity_id',)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('utf-8')
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def local(root,name):
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Lineage path outside project')
    return path

def reconcile(original,recomputed):
    old={r['id']:r for r in original};new={r['id']:r for r in recomputed}
    if len(old)!=len(original) or len(new)!=len(recomputed) or set(old)!=set(new):raise ValueError('Building census changed; explicit snapshot migration required')
    records=[];keys=set()
    for ident,row in new.items():
        if any(k not in row or row[k]!=v for k,v in old[ident].items()):raise ValueError('Building relationship changed: '+ident+'; explicit review required')
        key=row['source_building_key'];objects=row['source_object_ids']
        if not row['source_building_number'] or not objects or key in keys or len(objects)!=len(set(objects)):raise ValueError('Missing or duplicate source building identity: '+ident)
        keys.add(key)
        records.append({'id':ident,'usd_path':row['usd_path'],'entity_id':building_identity(objects),**{k:row[k] for k in SOURCE_FIELDS}})
    return sorted(records,key=lambda r:r['entity_id'])

def source_geometry_fingerprint(root):
    source=root/'scene/college_park.usda';cache_key=(str(root),sha(source))
    if cache_key in _GEOMETRY_CACHE:return _GEOMETRY_CACHE[cache_key]
    stage=Usd.Stage.Open(Sdf.Layer.OpenAsAnonymous(str(source)));rows=[]
    for prim in stage.GetPrimAtPath('/World/Buildings').GetChildren():
        mesh=UsdGeom.Mesh(prim);raw=prim.GetCustomData()
        rows.append({'path':str(prim.GetPath()),'source':{k:raw.get(k) for k in ('parcelId','buildingNumber','sourceObjectIds','heightMeters')},'points':[list(v) for v in mesh.GetPointsAttr().Get()], 'counts':list(mesh.GetFaceVertexCountsAttr().Get()),'indices':list(mesh.GetFaceVertexIndicesAttr().Get()),'world_transform':[list(v) for v in UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())]})
    value=digest(sorted(rows,key=lambda r:r['path']));_GEOMETRY_CACHE.clear();_GEOMETRY_CACHE[cache_key]=value;return value

def registry_identity_fingerprint(root):
    rows=read(root/'data/processed/asset_registry.json')['records']
    return digest(sorted([{'id':r['local_building_id'],'entity_id':r['entity_id'],'objects':sorted(r['source_feature_ids'])} for r in rows],key=lambda r:r['id']))

def verify_membership(records,raw,registry):
    indexed={str(f['properties']['OBJECTID']):f['properties'] for f in raw['features']}
    if len(indexed)!=len(raw['features']):raise ValueError('Duplicate raw source object IDs')
    by_id={r['local_building_id']:r for r in registry['records']}
    if len(by_id)!=len(registry['records']) or set(by_id)!={r['id'] for r in records}:raise ValueError('Registry census differs; reconcile identities first')
    used=set();entities=set()
    for row in records:
        objects=row['source_object_ids'];registered=by_id[row['id']]
        if row['entity_id'] in entities or row['entity_id']!=registered['entity_id'] or set(objects)!=set(registered['source_feature_ids']):raise ValueError('Source membership changed; split/merge/republication review required: '+row['id'])
        entities.add(row['entity_id'])
        for obj in objects:
            if obj in used or obj not in indexed:raise ValueError('Missing or multiply assigned raw subarea')
            used.add(obj);p=indexed[obj]
            if 'ocpa-building:'+str(p['PID'])+':'+str(p['BLDG_NUM'])!=row['source_building_key']:raise ValueError('Raw PID/building grouping disagrees')
    orphans=[{'source_object_id':obj,'source_parcel_id':str(p['PID']),'source_building_number':str(p['BLDG_NUM']),'source_building_key':'ocpa-building:'+str(p['PID'])+':'+str(p['BLDG_NUM']),'state':'unrepresented_raw_subarea_review','reason':'Raw source row is not a member of any active modeled group; exclusion reason not established here','physical_omission_confirmed':False} for obj,p in sorted(indexed.items()) if obj not in used]
    modeled_keys={row['source_building_key'] for row in records}
    for row in orphans:row['source_group_has_modeled_members']=row['source_building_key'] in modeled_keys
    orphan_keys={x['source_building_key'] for x in orphans}
    return {'partially_represented_source_groups':len(orphan_keys & modeled_keys),'wholly_unrepresented_source_groups':len(orphan_keys-modeled_keys),'raw_subareas':len(indexed),'modeled_subareas':len(used),'orphan_subareas':len(orphans),'orphan_source_groups':len({x['source_building_key'] for x in orphans}),'orphan_queue':orphans,'registry_membership_conflicts':0}

def previous(root):
    path=root/OUTPUT;receipt=root/(OUTPUT+'.receipt')
    if path.exists()!=receipt.exists():raise ValueError('Incomplete lineage publication; preserve and review')
    if not path.exists():return None
    pointer=read(path);proof=read(receipt)
    if proof.get('sha256')!=sha(path):raise ValueError('Preserve manually modified lineage manifest')
    if pointer.get('schema')=='twin.building-lineage-manifest/1':
        target=local(root,pointer['packet_path'])
        if target.name!=pointer['packet_sha256']+'.json' or sha(target)!=pointer['packet_sha256']:raise ValueError('Preserve changed immutable lineage packet')
    return {'manifest_sha256':sha(path),'receipt_sha256':sha(receipt)}

def publish(root,report):
    expected=previous(root);content=canonical(report);hashvalue=hashlib.sha256(content).hexdigest();relative='data/derived/ocpa-lineage/'+hashvalue+'.json';target=local(root,relative)
    if target.exists() and target.read_bytes()!=content:raise ValueError('Immutable lineage content-address conflict')
    manifest={'schema':'twin.building-lineage-manifest/1','source_snapshot':report['source_snapshot'],'packet_path':relative,'packet_sha256':hashvalue}
    path=root/OUTPUT;receipt=root/(OUTPUT+'.receipt')
    if expected and read(path)==manifest:return report
    if expected:
        if previous(root)!=expected:raise ValueError('Lineage publication changed while building')
        backup=root/'data/derived/ocpa-lineage/backups'/now().replace(':','_');backup.mkdir(parents=True)
        shutil.copy2(path,backup/path.name);shutil.copy2(receipt,backup/receipt.name)
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        temporary=target.with_suffix('.tmp');temporary.write_bytes(content);os.replace(temporary,target)
    atomic_json(path,manifest);atomic_json(receipt,{'source_snapshot':report['source_snapshot'],'sha256':sha(path)})
    return report

def build(root=ROOT):
    root=Path(root).resolve();expected=previous(root);active=read(root/'data/processed/active.json');folder=local(root,active['relative_path'])
    if not folder.is_relative_to((root/'data/snapshots').resolve()):raise ValueError('Active snapshot outside snapshot directory')
    inputs=[root/'data/processed/active.json',folder/'buildings.json',folder/'parcels.json',root/'data/buildings.geojson',root/'tools/data_pipeline.py',root/'tools/build_building_lineage.py']
    dependencies={str(p.relative_to(root)).replace('\\','/'):sha(p) for p in inputs}
    fingerprints={'base_building_geometry':source_geometry_fingerprint(root),'registry_identities':registry_identity_fingerprint(root)}
    original=read(folder/'buildings.json');records=reconcile(original,building_joins(read(folder/'parcels.json'),root/'scene/college_park.usda'))
    membership=verify_membership(records,read(root/'data/buildings.geojson'),read(root/'data/processed/asset_registry.json'))
    if any(sha(local(root,k))!=v for k,v in dependencies.items()) or fingerprints!={'base_building_geometry':source_geometry_fingerprint(root),'registry_identities':registry_identity_fingerprint(root)} or previous(root)!=expected:raise ValueError('Source/publication changed while deriving lineage')
    report={'schema':'twin.building-lineage/2','source_snapshot':active['snapshot'],
        'purpose':'Immutable additive source lineage; no snapshot, accepted link, geometry or manual changes',
        'source_geometry_promoted':False,'stored_relationships_changed':False,'all_original_fields_preserved':True,'dependencies':dependencies,'fingerprints':fingerprints,
        'source_key_scope':'OCPA source parcel + building number; not permanent physical identity. Entity ID reuses the existing source-object-membership registry hash.',
        'fields':{'entity_id':'Existing registry identity derived from sorted original source object IDs; source membership change requires lineage review','source_building_key':'ocpa-building:original source PID:original BLDG_NUM','source_building_number':'Original source string','source_object_ids':'Original subarea IDs as strings','candidate_parcel_features':'Distinct active parcel feature identities, ratio and source-PIN agreement','match_confidence_basis':'Overlap fraction, not statistical probability','join_state':'accepted source ID/geometry, spatial_review, ambiguous or unmatched; no current physical-form acceptance'},
        'counts':dict(collections.Counter(r['join_state'] for r in records)),'membership':membership,
        'limitations':['Frozen full3916-feature active parcel membership retained; separate ten-row quarantine policy is not published here.','Source keys and original registry identities are snapshot/source-version traceability, not automatic cross-republication continuity.','Orphan source rows are an explicit review queue, not confirmed missing buildings. No geometry or historical reconstruction promoted.','Source retrieval/acquisition remains governed by unchanged snapshot source manifests; publication does not refresh agency data.'],
        'records':records}
    return publish(root,report)

def validate(root=ROOT):
    root=Path(root).resolve();proof=previous(root)
    if not proof:raise ValueError('Building lineage not published')
    manifest=read(root/OUTPUT)
    if manifest.get('schema')!='twin.building-lineage-manifest/1':raise ValueError('Legacy lineage publication needs migration')
    report=read(local(root,manifest['packet_path']))
    if report['schema']!='twin.building-lineage/2' or report['source_snapshot']!=read(root/'data/processed/active.json')['snapshot'] or report['source_snapshot']!=manifest['source_snapshot']:raise ValueError('Building lineage snapshot stale')
    if not report.get('dependencies'):raise ValueError('Missing lineage dependency evidence')
    for name,value in report['dependencies'].items():
        if sha(local(root,name))!=value:raise ValueError('Building lineage source changed: '+name)
    if report['fingerprints']!={'base_building_geometry':source_geometry_fingerprint(root),'registry_identities':registry_identity_fingerprint(root)}:raise ValueError('Building geometry/membership changed; explicit lineage review required')
    return report

if __name__=='__main__':
    report=build();print(json.dumps({'source_snapshot':report['source_snapshot'],'counts':report['counts'],'records':len(report['records']),'membership':{k:v for k,v in report['membership'].items() if k!='orphan_queue'}}))
