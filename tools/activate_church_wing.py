"""Guarded local adoption of reviewed existing-group2892 roof correction.

Default prepares an ignored canonical package/plan only. No editor/API/GPU use.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,Sdf
from accepted_scene_layers import manual_model_fingerprint

BASE='data/diagnostics/church_se_wing_continuous_20261102_b/'
PACKAGE='data/diagnostics/church_wing_integration_20261102/'
LAYER='scene/church_southeast_wing.usda'
RECEIPT='data/processed/church_wing_activation.json'
SNAPSHOT='20261028T160543372334Z'
PACKAGED_SHA='2fdb4e7fb8f3e6170486a3f82ee06bfd8194323455d0a175bed1ad054fbd9303'
RAW_SHA='6089acbbd7b8d41bc6b708876b329c9668c1eb414ef1dd2211e0fcdb197c1131'
FIXED={
 BASE+'site.usda':'a229152f5add5aeec0879f6905261ce6acabe2f3e6ef5692f2c0dbf99af2ddd0',
 BASE+'legacy_mask_proposal.usda':'43a08b4e9adf07a73c3c8920b88479039de5b13cdd5e5f0d8785aa9fb00bfe00',
 BASE+'manifest.json':'9dfb489daa704397fa960a54c8ece6d04fa1994d4b609bc91a1a8d0465d43427',
 BASE+'captured_helper.py':'cc55d593178c4fa03fab8d19fb7ad7b6bcfe70743891e8e55bb1ecef451e84b9',
 'docs/evidence/church-wing-continuous-review.json':'5ace7d48a29eb9273158b103a369b290fe3b01421b407f0d847ab0f9fb9f5070',
 'docs/evidence/church-wing-census-replay.json':'7ebd6afd62533e908bf2cca6e58e9dadef49757ed1548e159566722a8bcb7672',
 'docs/evidence/church-wing-source-replay.json':'0901ffe0c721c9376e03e81f452184ca2fb0520f99d06f7baf8df513afffe6a8',
 'data/renders/20261102T174414Z/manifest.json':'0b2f5523607e3d1ad83d1574281706dc6381f5ba55db3029368a4b7732c1f695',
 'data/renders/20261102T174414Z/ChurchSoutheastWingContinuousRoof.png':'de4df939810bef4860bf02fd9f5082148eae56f207260af412c4c76c2b6bd41a',
 'assets/generated/office_brick/color.png':'b54c92c89d16609ffa0a2bb7b29967b28d8810280e89ec9e618b00d9468a2397',
 'assets/generated/office_brick/normal.png':'6b387482eda5265dfd40bdf2d7e06649b11c7ef40dcdd3bf27a1c0e806f5cd9d',
 'assets/generated/office_brick/roughness.png':'c8dc664b025e391f89c6f853c597c03b5ae4c5395aad1b9cbf7d124dc86fb162',
}
RAW_PATHS=[f'/World/{kind}/{prefix}{number}' for number in (2892,2919,2928,3065,3074,3076)
           for kind,prefix in [('Buildings','Building_'),('Roofs','Roof_')]]+['/World/Storefronts/Building_2892']
PRIM='/World/Landmarks/ChurchSoutheastWingContinuousRoof'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def checked(root,path,digest):
    resolved=(root/path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file() or sha(resolved)!=digest:
        raise ValueError('Wing canonical evidence missing/changed: '+path)
    return resolved

def site():
    return {'id':'church_southeast_wing_existing_2892_correction','prim_path':PRIM,
        'kind':'historical_form_correction','source_model_alias':'Building_2892',
        'existing_entity_id':'ocpa:building-group:69f7107de66f455f9cb153eb','source_usd_path':'/World/Buildings/Building_2892',
        'source_building_group':'Building_2892','source_entity_id':'ocpa:building-group:69f7107de66f455f9cb153eb',
        'source_building_number':'4','source_object_ids':['1158142','1160052','1170575'],
        'source_parcel_id':'292214146004210','parcel_id':'292214146005190','parcel_ids':['292214146005190'],
        'source_parcel_context':['292214146004210','292214146005190'],
        'site_address':'1914 Edgewater Drive','adds_physical_entity':False,'physical_building_count':None,
        'raw_tax_links_accepted':False,'current_geometry_verified':False,
        'quality':'historical_measured_roof_planes_with_estimated_continuation_and_enclosure',
        'components':[{'id':'roof_north','prim_path':PRIM+'/RoofPatch_1'},
            {'id':'roof_south','prim_path':PRIM+'/RoofPatch_2'},
            {'id':'estimated_enclosure','prim_path':PRIM+'/EstimatedRoofEnvelopeClosure'}],
        'limits':['Existing2892 underheight correction, not new physical building',
            'Assigned5190/source4210 ambiguity retained; context not accepted tax identity',
            'Roofcover edge continuation and zero-overhang wallclosure estimated; current condition unknown',
            'Lowerreturns unmodeled; no upperroofholes inferred','Openbottom render enclosure, not watertight surveyed solid',
            'Sourcefloors1 retained; no new storey count promoted','Local-only; public derivative release false']}

def recipe(root=ROOT,archive=False):
    root=Path(root).resolve()
    for p,h in FIXED.items():checked(root,p,h)
    manifest=json.loads((root/BASE/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema')!='twin.church-se-continuous-envelope-candidate/1' or manifest.get('source_snapshot')!=SNAPSHOT:
        raise ValueError('Wing source schema/snapshot changed')
    deps=dict(FIXED);context={}
    for p,h in manifest['dependencies'].items():
        if p=='tools/prepare_church_wing.py':continue # exact reviewed captured helper already pinned
        if p.endswith('.py'):
            target=PACKAGE+'producer_versions/'+h+'_'+Path(p).name
            if archive and not (root/target).exists():
                source=checked(root,p,h);(root/target).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,root/target)
            checked(root,target,h);deps[target]=h
        elif p.startswith('data/diagnostics/') or p=='data/processed/active.json':
            checked(root,p,h);deps[p]=h
        else:context[p]=h
    census=json.loads((root/'data/diagnostics/church_wings_20261102/all_source_census_v1.json').read_text())
    if census['raw_feature_count']!=18 or len(census['all_model_groups'])!=6 or census['raw_ids_not_in_model_groups']:
        raise ValueError('Wing full source-census contract changed')
    return deps,context

def verify_identity(packet,root=ROOT,require_layer=True):
    """Nonrecursive identity/recipe guard; NEVER calls legacy_fingerprint."""
    root=Path(root).resolve();deps,_=recipe(root)
    if packet.get('schema')!='twin.church-wing-activation/1' or packet.get('layer')!=LAYER or packet.get('site')!=site():
        raise ValueError('Wing schema/layer/site identity changed')
    if any(packet.get(k) is not False for k in ['current_geometry_verified','raw_tax_links_accepted','public_derivative_release_accepted','adds_physical_entity']):
        raise ValueError('Wing current/tax/public/newentity promotion forbidden')
    if packet.get('source_snapshot')!=SNAPSHOT or json.loads((root/'data/processed/active.json').read_text())['snapshot']!=SNAPSHOT:
        raise ValueError('Wing snapshot stale')
    if packet.get('dependencies')!=deps or not deps:
        raise ValueError('Wing critical recipe incomplete/changed')
    if packet.get('layer_sha256')!=PACKAGED_SHA:
        raise ValueError('Wing canonical layer identity changed')
    if packet.get('manual_model_fingerprint')!=manual_model_fingerprint(root):
        raise ValueError('Wing manual model opinions changed')
    checked(root,PACKAGE+'site.usda',PACKAGED_SHA)
    if require_layer:checked(root,LAYER,PACKAGED_SHA)
    return packet

def validate_wing_identity(root=ROOT):
    root=Path(root).resolve();layer,receipt=root/LAYER,root/RECEIPT
    if not layer.exists() and not receipt.exists():return None
    if not layer.is_file() or not receipt.is_file():raise ValueError('Wing layer/receipt incomplete')
    return verify_identity(json.loads(receipt.read_text(encoding='utf-8')),root)

def verify_full(packet,root=ROOT,require_layer=True):
    root=Path(root).resolve();verify_identity(packet,root,require_layer)
    if packet.get('manual_model_fingerprint')!=manual_model_fingerprint(root):raise ValueError('Wing manual model opinions changed')
    from activate_church_integration import legacy_fingerprint
    if packet.get('raw_source_fingerprint')!=RAW_SHA or legacy_fingerprint(root,paths=RAW_PATHS)!=RAW_SHA:
        raise ValueError('Wing originalsource geometry/identity/material changed')
    return packet

def validated_wing(root=ROOT):
    packet=validate_wing_identity(root)
    return verify_full(packet,root) if packet else None

def make_package(root=ROOT):
    root=Path(root).resolve();recipe(root,archive=True)
    target=root/PACKAGE/'site.usda'
    assembly=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(assembly,'Z');UsdGeom.SetStageMetersPerUnit(assembly,1.)
    assembly.GetRootLayer().subLayerPaths=[str(root/BASE/'site.usda'),str(root/BASE/'legacy_mask_proposal.usda')]
    flat=assembly.Flatten();flat.customLayerData={'schema':'twin.church-wing-local-package/1',
        'sourceSnapshot':SNAPSHOT,'currentConditionsVerified':False,'rawTaxLinksAccepted':False,
        'publicDerivativeReleaseAccepted':False,'addsPhysicalEntity':False,'purpose':'Existing2892 historical roof/estimatedenclosure correction plus boundedsource-surface remainders'}
    text=flat.ExportToString()
    if target.exists() and target.read_text(encoding='utf-8')!=text:raise ValueError('Frozen canonical wing package differs')
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
    return sha(target)

def prepare(root=ROOT):
    root=Path(root).resolve()
    protected=['scene/college_park_connected.usda','scene/manual_edits.usda','scene/church_historical.usda',
        'scene/landmark_buildings.usda','scene/post_office_historical.usda','scene/campus_hardscape.usda','data/processed/active.json']
    before={p:sha(root/p) for p in protected}
    digest=make_package(root)
    if digest!=PACKAGED_SHA:raise ValueError('Canonical package SHA requires reviewed code binding: '+digest)
    deps,context=recipe(root)
    packet={'schema':'twin.church-wing-activation/1','layer':LAYER,'layer_sha256':digest,'source_snapshot':SNAPSHOT,
        'current_geometry_verified':False,'raw_tax_links_accepted':False,'public_derivative_release_accepted':False,'adds_physical_entity':False,
        'site':site(),'dependencies':deps,'comparison_context_not_live_dependencies':context,
        'manual_model_fingerprint':manual_model_fingerprint(root),'raw_source_fingerprint':RAW_SHA,
        'preparation_protected_before':before,'preparation_protected_after':{p:sha(root/p) for p in protected}}
    if packet['preparation_protected_before']!=packet['preparation_protected_after']:
        raise ValueError('Protected files changed during wing preparation; preserve candidate for review')
    verify_full(packet,root,require_layer=False)
    plan=root/PACKAGE/'activation_plan.json';text=json.dumps(packet,indent=2)
    if plan.exists() and plan.read_text(encoding='utf-8')!=text:raise ValueError('Prepared plan differs; preserve previous for review')
    plan.write_text(text,encoding='utf-8');return plan

def apply(root=ROOT):
    root=Path(root).resolve();plan=root/PACKAGE/'activation_plan.json';packet=verify_full(json.loads(plan.read_text()),root,False)
    if (root/LAYER).exists() or (root/RECEIPT).exists():raise ValueError('Wing destination exists; do not overwrite')
    assembly=root/'scene/college_park_connected.usda';original=assembly.read_bytes();layer=Sdf.Layer.OpenAsAnonymous(str(assembly));old=list(layer.subLayerPaths)
    if 'manual_edits.usda' not in old or Path(LAYER).name in old:raise ValueError('Wing root ordering precondition failed')
    new=old.copy();new.insert(new.index('manual_edits.usda')+1,Path(LAYER).name);layer.subLayerPaths=new
    edited=layer.ExportToString();layer.subLayerPaths=old
    reference=Sdf.Layer.OpenAsAnonymous(str(assembly))
    if layer.ExportToString()!=reference.ExportToString():raise ValueError('Wing root non-sublayer opinions changed')
    backup=root/'data/backups'/('church_wing_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));backup.mkdir(parents=True)
    (backup/assembly.name).write_bytes(original);(backup/'activation_plan.json').write_bytes(plan.read_bytes())
    pending=root/(LAYER+'.pending');pr=root/(RECEIPT+'.pending');pa=assembly.with_suffix('.wing_pending.usda')
    try:
        shutil.copyfile(root/PACKAGE/'site.usda',pending);pr.write_text(json.dumps(packet,indent=2),encoding='utf-8');pa.write_text(edited,encoding='utf-8')
        verify_full(packet,root,False)
        if assembly.read_bytes()!=original:raise ValueError('Root changed during wing staging')
        os.replace(pending,root/LAYER);os.replace(pr,root/RECEIPT);validated_wing(root)
        if assembly.read_bytes()!=original:raise ValueError('Root changed before wing publication')
        os.replace(pa,assembly)
    except Exception:
        for p in (pending,pr,pa,root/LAYER,root/RECEIPT):
            if p.exists():p.unlink()
        raise
    return {'backup':backup.relative_to(root).as_posix(),'layer':LAYER,'receipt':RECEIPT,'root_before_sha256':hashlib.sha256(original).hexdigest(),'root_after_sha256':sha(assembly)}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    print(json.dumps(apply() if args.apply else {'plan':str(prepare())},indent=2))
