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
    report={'source_snapshot':active['snapshot'],'registered_utc':now(),'dependencies':{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies},'records':[record]}
    atomic_json(ROOT/'data/processed/reconstructions.json',report)
    print('Registered historical reconstruction:',record['id']);return report

if __name__=='__main__':build()
