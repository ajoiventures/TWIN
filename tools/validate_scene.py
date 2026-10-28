"""Read-only scene/profile inspection. Does not repair or change source USD."""
from pathlib import Path
import sys,json,math,datetime,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdUtils
from data_pipeline import atomic_json
from semantic_registry import validate_records,PROFILE,sha

def inspect_mesh(mesh):
    errors=[];pts=mesh.GetPointsAttr().Get() or [];counts=mesh.GetFaceVertexCountsAttr().Get() or [];indices=mesh.GetFaceVertexIndicesAttr().Get() or []
    if sum(counts)!=len(indices):errors.append('face_index_count_mismatch')
    if any(i<0 or i>=len(pts) for i in indices):errors.append('face_index_out_of_range')
    if any(c<3 for c in counts):errors.append('degenerate_face')
    if any(not math.isfinite(float(v)) for p in pts for v in p):errors.append('nonfinite_point')
    return errors

def validate(root=ROOT,verbose=True):
    root=Path(root);path=root/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(path))
    registry=json.loads((root/'data/processed/asset_registry.json').read_text(encoding='utf-8'));rows=registry['records'];errors=validate_records(rows);warnings=[]
    active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
    if registry['source_snapshot']!=active['snapshot']:errors.append({'code':'registry_snapshot_stale'})
    if registry['base_geometry_sha256']!=sha(root/'scene/college_park.usda'):errors.append({'code':'base_geometry_hash_stale'})
    if registry['height_evidence_sha256']!=sha(root/'data/heights/building_heights.json'):errors.append({'code':'height_evidence_hash_stale'})
    expected=json.loads((root/active['relative_path']/'buildings.json').read_text(encoding='utf-8'))
    if {(r['local_building_id'],r['usd_path']) for r in rows}!={(r['id'],r['usd_path']) for r in expected}:errors.append({'code':'registry_coverage_mismatch'})
    if any(r['source_snapshot']!=active['snapshot'] for r in rows):errors.append({'code':'record_snapshot_stale'})
    if UsdGeom.GetStageMetersPerUnit(stage)!=1:errors.append({'code':'scene_units_not_meters'})
    if UsdGeom.GetStageUpAxis(stage)!='Z':errors.append({'code':'scene_up_axis_not_z'})
    meshes=0
    instance_meshes=0
    for prim in Usd.PrimRange.Stage(stage,Usd.TraverseInstanceProxies()):
        if prim.IsA(UsdGeom.Mesh):
            meshes+=1
            if prim.IsInstanceProxy():instance_meshes+=1
            for error in inspect_mesh(UsdGeom.Mesh(prim)):errors.append({'path':str(prim.GetPath()),'code':error})
    for r in rows:
        prim=stage.GetPrimAtPath(r['usd_path'])
        if not prim:errors.append({'entity_id':r['entity_id'],'code':'missing_scene_entity'});continue
        if prim.GetCustomDataByKey('twin:entityId')!=r['entity_id']:errors.append({'entity_id':r['entity_id'],'code':'semantic_identity_mismatch'})
        if prim.GetCustomDataByKey('twin:validationProfile')!=PROFILE:errors.append({'entity_id':r['entity_id'],'code':'semantic_profile_mismatch'})
        mesh=UsdGeom.Mesh(prim);pts=mesh.GetPointsAttr().Get() or []
        if not pts or abs(max(p[2] for p in pts)-(.1+r.get('maximum_rendered_height_m',r['height_m'])))>.02:errors.append({'entity_id':r['entity_id'],'code':'height_geometry_mismatch'})
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(path))
    for name in unresolved:errors.append({'path':str(name),'code':'unresolved_asset'})
    warnings.extend(['Ground remains flat; terrain/ground anchoring is not survey-validated.','Collision, pedestrian clearances and sensor material response are not validated by this visualization profile.','Historical LiDAR and estimated heights do not prove current conditions.'])
    report={'profile':PROFILE,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'building_entities':len(rows),'meshes_checked':meshes,'instance_proxy_meshes_checked':instance_meshes,'layers':len(layers),'external_assets':len(assets),'errors':errors,'warnings':warnings,'passed_local_profile':not errors,'nvidia_certified':False}
    atomic_json(root/'data/processed/scene_validation.json',report)
    if verbose:print(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    result=validate();sys.exit(0 if result['passed_local_profile'] else 1)
