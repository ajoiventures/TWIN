"""Expose a composed historical reconstruction separately from legacy tax links."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom
from data_pipeline import atomic_json,now

def build():
    active=json.loads((ROOT/'data/processed/active.json').read_text())
    assembly=ROOT/'scene/college_park_connected.usda';stage=Usd.Stage.Open(str(assembly))
    layer=ROOT/'scene/princeton_correction.usda';manifest_path=ROOT/'data/heights/princeton/manifest.json'
    used={Path(x.realPath).resolve() for x in stage.GetUsedLayers() if x.realPath}
    if layer.resolve() not in used:raise ValueError('Princeton correction must be reviewed and composed before registration')
    evidence=json.loads(manifest_path.read_text())
    if evidence['source_snapshot']!=active['snapshot']:raise ValueError('Reconstruction snapshot is stale')
    project=stage.GetPrimAtPath('/World/Landmarks/PrincetonAtCollegePark')
    if not project or UsdGeom.Imageable(project).ComputeVisibility()=='invisible':raise ValueError('Reconstruction is not visible in the disk composition')
    old=evidence['legacy_supersession']
    for row in old:
        if row.get('action')=='hide_full' and UsdGeom.Imageable(stage.GetPrimAtPath(row['usd_path'])).ComputeVisibility()!='invisible':raise ValueError('Superseded source building is still visible')
    record={'id':evidence['project_id'],'parcel_id':evidence['official_parcel']['parcel_id'],'site_address':evidence['official_parcel']['site_address'],'usd_path':str(project.GetPath()),'quality':'historical_component_reconstruction_current_conditions_unverified','reported_project_maximum_storeys':evidence['reported_project_maximum_storeys'],'components':evidence['components'],'superseded_legacy_groups':sum(r.get('action')=='hide_full' for r in old),'partially_retained_legacy_groups':sum(r.get('action')=='retain_only_outside_property_remainder' for r in old),'raw_property_links_promoted':False,'limitations':evidence['limitations']}
    dependencies=[assembly,layer,manifest_path,ROOT/'scene/college_park.usda']
    records=[record];activation_path=ROOT/'data/heights/landmarks/activation.json'
    if activation_path.exists():
        packet=json.loads(activation_path.read_text());landmark_layer=ROOT/packet['layer']
        if packet['source_snapshot']!=active['snapshot'] or landmark_layer.resolve() not in used or hashlib.sha256(landmark_layer.read_bytes()).hexdigest()!=packet['layer_sha256']:raise ValueError('Landmark activation is stale or not composed')
        dependencies.extend([activation_path,landmark_layer])
        for relative,digest in packet['dependencies'].items():
            dependency=(ROOT/relative).resolve()
            if not dependency.is_relative_to(ROOT.resolve()) or hashlib.sha256(dependency.read_bytes()).hexdigest()!=digest:raise ValueError('Landmark source dependency changed')
            dependencies.append(dependency)
        for site in packet['sites']:
            prim=stage.GetPrimAtPath(site['prim_path'])
            if not prim or UsdGeom.Imageable(prim).ComputeVisibility()=='invisible':raise ValueError('Landmark reconstruction not visible')
            records.append({'id':site['site_id'],'parcel_id':site['parcel_id'],'site_address':site['site_address'],'usd_path':site['prim_path'],'quality':'historical_component_reconstruction_current_conditions_unverified','components':site['components'],'main_roof_height_m':site['main_roof_height_m'],'maximum_rendered_height_m':site['maximum_rendered_height_m'],'main_roof_height_ground_reference_range_m':site['main_roof_height_ground_reference_range_m'],'superseded_legacy_groups':0,'raw_property_links_promoted':False,'limitations':packet['limitations']})
    report={'source_snapshot':active['snapshot'],'registered_utc':now(),'dependencies':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},'records':records}
    atomic_json(ROOT/'data/processed/reconstructions.json',report)
    print('Registered historical reconstruction:',record['id']);return report

if __name__=='__main__':build()
