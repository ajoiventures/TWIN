"""Isolated city-visualization asset inspection; never activates or repairs sources.

Contract: select one registered entity, copy its composed geometry/materials into
an ignored experiment directory, add task metadata in a separate layer, and
report source hashes, material/reference/scale/origin checks. No physics claim.
"""
from pathlib import Path
import argparse,datetime,hashlib,json,math,sys
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,UsdPhysics,UsdSemantics,UsdLux,Gf,Sdf,UsdUtils

PROFILE='college-park-source-inspection/1.0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def date_provenance(root,row):
    """Link exact footprint requests where retained; never reuse build time."""
    path=Path(root)/'data/footprint_manifest.json';wanted=set(row.get('source_feature_ids',[]));receipts=[];covered=set()
    if path.exists():
        for request in json.loads(path.read_text()).get('requests',[]):
            query=parse_qs(urlparse(request.get('url','')).query)
            ids=set(query.get('objectIds',[''])[0].split(','))&wanted
            if ids:
                covered|=ids;receipts.append({'source_feature_ids':sorted(ids),'url':request['url'],'retrieved_utc':request.get('retrieved_utc'),'retrieval_quality':request.get('retrieval_quality','unknown'),'response_sha256':request.get('sha256')})
    return {'receipt_ref':'data/footprint_manifest.json#requests' if path.exists() else None,'receipt_sha256':sha(path) if path.exists() else None,'requests':receipts,'source_ids_without_retained_request':sorted(wanted-covered),'unknown_reason':'Reused legacy rows may lack retained original retrieval receipts; build/read times are not substitutions.','acquisition_interval':row.get('acquisition_interval'),'valid_time':row.get('valid_time'),'evidence_refs':row.get('evidence_refs',[])}
def preflight_stage(output,bounds,pilot_relative):
    """CPU-only camera/light setup, separate from the validator's exact asset."""
    path=Path(output)/'preflight.usda'
    if path.exists():raise ValueError('Preflight already exists')
    layer=Sdf.Layer.CreateNew(str(path));layer.subLayerPaths=[Path(pilot_relative).as_posix()]
    stage=Usd.Stage.Open(layer);UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,'Z')
    center=Gf.Vec3d(*[(bounds[0][i]+bounds[1][i])*.5 for i in range(3)])
    size=max(bounds[1][i]-bounds[0][i] for i in range(3));camera=UsdGeom.Camera.Define(stage,'/World/Cameras/AssetContractEvidence')
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(center+Gf.Vec3d(size*1.3,-size*1.5,size),center,Gf.Vec3d(0,0,1)).GetInverse())
    camera.CreateFocalLengthAttr(25);camera.CreateClippingRangeAttr((.05,max(100.,size*20)))
    dome=UsdLux.DomeLight.Define(stage,'/ReviewLighting/Dome');dome.CreateIntensityAttr(700)
    sun=UsdLux.DistantLight.Define(stage,'/ReviewLighting/Sun');sun.CreateIntensityAttr(2000);sun.AddRotateXYZOp().Set((-35,-25,-30))
    layer.Save();return path
def inspect(stage,prim):
    errors=[];warnings=[];meshes=0;materials=set();collision=0
    cache=UsdGeom.XformCache();world_points=[]
    for item in Usd.PrimRange(prim,Usd.TraverseInstanceProxies()):
        if item.HasAPI(UsdPhysics.CollisionAPI):collision+=1
        if not item.IsA(UsdGeom.Mesh):continue
        meshes+=1;mesh=UsdGeom.Mesh(item);points=mesh.GetPointsAttr().Get() or []
        transform=cache.GetLocalToWorldTransform(item)
        for point in points:
            p=transform.Transform(point)
            if not all(math.isfinite(float(v)) for v in p):errors.append('nonfinite_world_point')
            else:world_points.append(tuple(p))
        material,_=UsdShade.MaterialBindingAPI(item).ComputeBoundMaterial()
        if material:
            materials.add(str(material.GetPath()))
            if not material.ComputeSurfaceSource()[0]:errors.append('unresolved_material_surface:'+str(material.GetPath()))
        elif not mesh.GetDisplayColorAttr().Get():warnings.append('no_material_or_display_color:'+str(item.GetPath()))
    if not world_points:errors.append('empty_geometry')
    bounds=[[min(p[i] for p in world_points) for i in range(3)],[max(p[i] for p in world_points) for i in range(3)]] if world_points else None
    if UsdGeom.GetStageMetersPerUnit(stage)!=1:errors.append('units_not_meters')
    if UsdGeom.GetStageUpAxis(stage)!='Z':errors.append('up_axis_not_z')
    if bounds and (max(bounds[1][i]-bounds[0][i] for i in range(3))>1000 or min(bounds[1][i]-bounds[0][i] for i in range(3))<=0):errors.append('implausible_building_extent')
    return {'errors':sorted(set(errors)),'warnings':sorted(set(warnings)),'meshes':meshes,'bound_materials':sorted(materials),'world_bounds_m':bounds,'authored_collision_prims':collision,'collision_requirement':'not applicable to source-inspection visualization; NOT approved for navigation/physics','traversability_requirement':'not applicable to this task; pedestrian routes/clearances remain unverified'}

def prepare(root=ROOT,output=None,local_id='Building_0665'):
    root=Path(root).resolve();output=Path(output or root/'data/diagnostics/asset_contract_pilot').resolve()
    # No arbitrary overwrite of existing work, source tree or active composition.
    allowed=(root/'data/diagnostics').resolve()
    if not output.is_relative_to(allowed) or output==allowed:raise ValueError('Output must be a new experiment below data/diagnostics')
    if output.exists():raise ValueError('Output already exists; preserve prior experiment')
    active=json.loads((root/'data/processed/active.json').read_text());registry=json.loads((root/'data/processed/asset_registry.json').read_text())
    if registry['source_snapshot']!=active['snapshot']:raise ValueError('Registry snapshot stale')
    if registry.get('base_geometry_sha256')!=sha(root/'scene/college_park.usda') or registry.get('height_evidence_sha256')!=sha(root/'data/heights/building_heights.json'):raise ValueError('Registry source hashes stale')
    matches=[r for r in registry['records'] if r['local_building_id']==local_id]
    if len(matches)!=1:raise ValueError('Expected exactly one registered entity')
    row=matches[0];source=root/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(source));prim=stage.GetPrimAtPath(row['usd_path'])
    dates=date_provenance(root,row)
    if not prim or prim.GetCustomDataByKey('twin:entityId')!=row['entity_id'] or prim.GetCustomDataByKey('twin:sourceSnapshot')!=active['snapshot']:raise ValueError('Scene identity or snapshot mismatch')
    layers,assets,unresolved=UsdUtils.ComputeAllDependencies(str(source))
    if unresolved:raise ValueError('Source has unresolved references')
    paths={Path(l.realPath).resolve() for l in layers if l.realPath}|{Path(a).resolve() for a in assets}
    paths|={root/'data/processed/asset_registry.json',root/'data/processed/active.json',root/'data/heights/building_heights.json'}
    if dates['receipt_ref']:paths.add(root/'data/footprint_manifest.json')
    before={str(p):sha(p) for p in sorted(paths)}
    original=inspect(stage,prim);flat=stage.Flatten();output.mkdir(parents=True)
    copy=Usd.Stage.CreateNew(str(output/'source_copy.usda'));UsdGeom.SetStageMetersPerUnit(copy,1);UsdGeom.SetStageUpAxis(copy,'Z')
    world=UsdGeom.Xform.Define(copy,'/World').GetPrim();copy.SetDefaultPrim(world)
    Sdf.CreatePrimInLayer(copy.GetRootLayer(),prim.GetPath().GetParentPath());Sdf.CopySpec(flat,prim.GetPath(),copy.GetRootLayer(),prim.GetPath())
    # Preserve any ancestor world transforms rather than silently relocating.
    ancestor=prim.GetParent()
    while ancestor and not ancestor.IsPseudoRoot():
        target=copy.DefinePrim(ancestor.GetPath(),ancestor.GetTypeName() or 'Xform')
        for prop in ancestor.GetProperties():
            if prop.GetName().startswith('xformOp:') or prop.GetName()=='xformOpOrder':
                if flat.GetPropertyAtPath(prop.GetPath()):Sdf.CopySpec(flat,prop.GetPath(),copy.GetRootLayer(),prop.GetPath())
        ancestor=ancestor.GetParent()
    for material in original['bound_materials']:
        Sdf.CreatePrimInLayer(copy.GetRootLayer(),Sdf.Path(material).GetParentPath());Sdf.CopySpec(flat,material,copy.GetRootLayer(),material)
    copy.GetRootLayer().Save()
    additive=Usd.Stage.CreateNew(str(output/'contract.usda'));over=additive.OverridePrim(row['usd_path'])
    over.SetCustomDataByKey('cityTask',{'profile':PROFILE,'task':'source-inspection visualization','scenarioStatus':'existing_conditions_prototype','validTime':json.dumps(dates['valid_time']),'acquisitionInterval':json.dumps(dates['acquisition_interval']),'dateProvenance':json.dumps(dates),'quality':row['observation_kind'],'entityId':row['entity_id'],'collision':'not authorized for physics','traversability':'unverified'})
    UsdSemantics.LabelsAPI.Apply(over,'cityscapes').CreateLabelsAttr(['building'])
    additive.GetRootLayer().Save()
    package=output/'city_building'/'usd';package.mkdir(parents=True)
    pilot=package/'city_building.usda';assembly=Sdf.Layer.CreateNew(str(pilot));assembly.subLayerPaths=['../../contract.usda','../../source_copy.usda']
    assembly.customLayerData={'asset_name':'city_building','asset_type':'static_visual_building','source_file':'../../source_copy.usda','usd_date_generated':datetime.datetime.now(datetime.timezone.utc).isoformat(),'SimReady_Metadata':{'purpose':'isolated validation experiment; not certification'}}
    composed=Usd.Stage.Open(assembly);UsdGeom.SetStageMetersPerUnit(composed,1);UsdGeom.SetStageUpAxis(composed,'Z');composed.SetDefaultPrim(composed.GetPrimAtPath('/World'));assembly.Save()
    isolated=Usd.Stage.Open(assembly);result=inspect(isolated,isolated.GetPrimAtPath(row['usd_path']))
    if any(original[key]!=result[key] for key in ('world_bounds_m','meshes','bound_materials')):raise ValueError('Isolated geometry/material inventory differs from composed source')
    preflight_stage(output,result['world_bounds_m'],pilot.relative_to(output))
    _,_,missing=UsdUtils.ComputeAllDependencies(str(pilot))
    result['missing_references']=[str(v) for v in missing]
    if missing:result['errors'].append('missing_isolated_reference')
    changed=[str(p) for p in paths if sha(p)!=before[str(p)]]
    if changed:raise ValueError('Sources changed during preparation; candidate is not accepted: '+str(changed))
    report={'schema':'twin.asset-contract-pilot/1','profile':PROFILE,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'entity_id':row['entity_id'],'local_building_id':local_id,'usd_path':row['usd_path'],'pilot_path':str(pilot.relative_to(output)),'valid_time':row.get('valid_time'),'acquisition_interval':row.get('acquisition_interval'),'horizontal_reference':row.get('horizontal_reference'),'origin_verification':'declared frame copied from current registry; not independent survey control','inspection':result,'source_dependencies_sha256':before,'source_files_unchanged':True,'artifacts_sha256':{str(p.relative_to(output)):sha(p) for p in output.rglob('*.usda')},'rollback':'Delete or retain isolated experiment; no active scene or source mutation occurred.','visual_preflight':'not run; requires actual same-candidate render before acceptance','nvidia_certified':False,'accepted':False}
    report['date_provenance']=dates
    (output/'inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);parser.add_argument('--building',default='Building_0665');args=parser.parse_args()
    report=prepare(output=args.output,local_id=args.building);print(json.dumps({k:report[k] for k in ('profile','entity_id','inspection','accepted')},indent=2));sys.exit(bool(report['inspection']['errors']))

