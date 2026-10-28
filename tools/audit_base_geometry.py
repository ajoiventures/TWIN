"""Offline isolated generator replay and canonical semantic diff; never repairs base."""
from pathlib import Path
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','PXR_WORK_THREAD_LIMIT'):os.environ[key]='1'
import datetime,hashlib,json,math,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,Sdf,Work
Work.SetConcurrencyLimit(1)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value):
    if value is None or isinstance(value,(str,bool,int)):return value
    if isinstance(value,float):return value if math.isfinite(value) else str(value)
    if isinstance(value,dict):return {str(k):canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,Sdf.AssetPath):return {'asset_path':value.path}
    try:return [canonical(v) for v in value]
    except TypeError:return str(value)

def prim_data(prim):
    attrs={}
    for attr in prim.GetAuthoredAttributes():
        attrs[attr.GetName()]={'type':str(attr.GetTypeName()),'value':canonical(attr.Get()),
            'metadata':canonical(attr.GetAllAuthoredMetadata()),'connections':[str(p) for p in attr.GetConnections()],
            'samples':{str(t):canonical(attr.Get(t)) for t in attr.GetTimeSamples()}}
    return {'type':prim.GetTypeName(),'metadata':canonical(prim.GetAllAuthoredMetadata()),'attributes':attrs,
            'relationships':{rel.GetName():[str(p) for p in rel.GetTargets()] for rel in prim.GetAuthoredRelationships()}}

def build(root=ROOT):
    root=Path(root).resolve();current=root/'scene/college_park.usda';start_hash=sha(current)
    registry=json.loads((root/'data/processed/asset_registry.json').read_text())
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=root/'data/diagnostics/base_geometry_audit'/stamp;replay=output/'isolated_replay'
    for name in ('tools','config','data','scene'):(replay/name).mkdir(parents=True,exist_ok=True)
    inputs=['tools/build_scene.py','config/study_area.json','data/buildings.geojson','data/footprint_manifest.json','data/openstreetmap.json','data/osm_extent.json']
    hashes={name:sha(root/name) for name in inputs}
    for name in inputs:shutil.copy2(root/name,replay/name)
    entry="import sys,urllib.request,runpy;sys.path.insert(0,"+repr(str(root/'.dependencies'))+");from pxr import Work;Work.SetConcurrencyLimit(1)\ndef denied(*args,**kwargs):raise RuntimeError('Network access forbidden in offline geometry audit')\nurllib.request.urlopen=denied\nrunpy.run_path("+repr(str(replay/'tools/build_scene.py'))+",run_name='__main__')"
    result=subprocess.run([sys.executable,'-c',entry],cwd=replay,env=os.environ.copy(),capture_output=True,text=True,timeout=180)
    (output/'replay_stdout.txt').write_text(result.stdout,encoding='utf-8');(output/'replay_stderr.txt').write_text(result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Isolated offline replay failed; inspect '+str(output/'replay_stderr.txt'))
    rebuilt=replay/'scene/college_park.usda';a=Usd.Stage.Open(str(current));b=Usd.Stage.Open(str(rebuilt))
    paths_a={str(p.GetPath()) for p in a.TraverseAll()};paths_b={str(p.GetPath()) for p in b.TraverseAll()}
    differences=[];categories={};point_topology_changes=[];material_changes=[];transform_changes=[]
    geometry_names={'points','faceVertexCounts','faceVertexIndices','extent','subdivisionScheme','normals','holeIndices','creaseIndices','creaseLengths','creaseSharpnesses','cornerIndices','cornerSharpnesses'}
    def note(category,path,name,old,new):
        categories[category]=categories.get(category,0)+1
        differences.append({'category':category,'path':path,'field':name,'current':old,'rebuilt':new})
    for path in sorted(paths_a&paths_b):
        current_prim=prim_data(a.GetPrimAtPath(path));rebuilt_prim=prim_data(b.GetPrimAtPath(path))
        if current_prim==rebuilt_prim:continue
        for section in ('type','metadata','relationships'):
            if current_prim[section]!=rebuilt_prim[section]:
                category='material_binding' if section=='relationships' and ('material' in str(current_prim[section]).lower() or 'material' in str(rebuilt_prim[section]).lower()) else section
                note(category,path,section,current_prim[section],rebuilt_prim[section])
                if category=='material_binding':material_changes.append(path)
        ca=current_prim['attributes'];cb=rebuilt_prim['attributes']
        for name in sorted(set(ca)|set(cb)):
            if ca.get(name)==cb.get(name):continue
            category='geometry' if name in geometry_names else 'transform' if name.startswith('xformOp') else 'material' if '/Materials/' in path or name.startswith(('inputs:','outputs:')) else 'primvar' if name.startswith('primvars:') else 'attribute'
            old=ca.get(name);new=cb.get(name)
            # Full large arrays remain available in preserved current/replay USD.
            def abbreviated(value):
                text=json.dumps(value,sort_keys=True)
                return value if len(text)<2000 else {'canonical_sha256':hashlib.sha256(text.encode()).hexdigest(),'serialized_length':len(text),'summary':'Full authored values retained in source/replay files'}
            note(category,path,name,abbreviated(old),abbreviated(new))
            if category=='geometry':point_topology_changes.append({'path':path,'attribute':name})
            if category=='transform':transform_changes.append({'path':path,'attribute':name})
            if category=='material':material_changes.append(path)
    root_a=canonical(a.GetPseudoRoot().GetAllAuthoredMetadata());root_b=canonical(b.GetPseudoRoot().GetAllAuthoredMetadata())
    known_api='SdfTokenListOp(Explicit Items: [OmniRtxCameraAutoExposureAPI_1, OmniRtxCameraExposureAPI_1])'
    camera_api_only=bool(differences) and all(
        diff['category']=='metadata' and diff['path'].startswith('/World/Cameras/')
        and diff['current'].get('apiSchemas')==known_api
        and {k:v for k,v in diff['current'].items() if k!='apiSchemas'}==diff['rebuilt'] for diff in differences)
    report={'created_utc':stamp,'current_base_sha256':start_hash,'expected_registry_sha256':registry['base_geometry_sha256'],'isolated_rebuild_sha256':sha(rebuilt),
            'rebuild_matches_expected_original_bytes':sha(rebuilt)==registry['base_geometry_sha256'],'current_file_preserved':sha(current)==start_hash,
            'input_hashes':hashes,'offline_network_forbidden':True,'numeric_threads':1,'current_prims':len(paths_a),'rebuilt_prims':len(paths_b),
            'current_only_paths':sorted(paths_a-paths_b),'rebuilt_only_paths':sorted(paths_b-paths_a),'difference_categories':categories,
            'geometry_attribute_changes':point_topology_changes,'transform_changes':transform_changes,'material_changed_paths':sorted(set(material_changes)),
            'root_metadata_equal':root_a==root_b,'root_metadata_current':root_a,'root_metadata_rebuilt':root_b,
            'canonical_equal':not differences and paths_a==paths_b and root_a==root_b,'differences':differences,
            'known_camera_exposure_metadata_only':camera_api_only,
            'geometry_and_appearance_semantically_equal':not point_topology_changes and not transform_changes and not material_changes and not any(d['category'] not in ('metadata',) for d in differences) and paths_a==paths_b,
            'recommended_action':'Preserve current base; record exact original-byte replay and camera-only metadata equivalence, regenerate semantic registry through its normal tool, then rerun validation. Regenerate other full-bytehash-derived products as required; do not patch hashes manually.' if camera_api_only and sha(rebuilt)==registry['base_geometry_sha256'] else 'Investigate semantic differences before refreshing registry or replacing any base file.',
            'preserved_current_file':str(current),'isolated_rebuilt_file':str(rebuilt),'replay_directory':str(replay)}
    if any(sha(root/name)!=digest for name,digest in hashes.items()) or sha(current)!=start_hash:raise ValueError('Active source changed during audit; repeat before taking action')
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    latest=root/'data/diagnostics/base_geometry_audit/latest.json';latest.write_text(json.dumps({'report':str(output/'report.json')},indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('differences','root_metadata_current','root_metadata_rebuilt','input_hashes')},indent=2));return report

if __name__=='__main__':build()
