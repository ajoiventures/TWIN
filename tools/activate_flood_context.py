"""Optional default-off FEMA composition; validation-only unless --apply.

Preserves root opinions/manual edits, backs up the root, and refuses stale packet
or concurrent changes. This activates reference context, never a flood simulation.
"""
from pathlib import Path
import sys,json,datetime,os,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Sdf,Usd,UsdGeom
from build_flood_overlay import validate_packet
from activate_environment_assets import sha,guarded_replace,local,relative


def validate(root=ROOT):
    root=Path(root);packet=validate_packet(root);layer=root/'scene/fema_effective_hazards.usda';assembly=root/'scene/college_park_connected.usda'
    if packet.get('default_on') is not False or packet.get('source_product')!='effective_NFHL':raise ValueError('Expected default-off effective NFHL context only')
    key=relative(root,layer)
    if packet.get('artifacts',{}).get(key)!=sha(layer):raise ValueError('FEMA layer lacks matching artifact hash')
    stage=Usd.Stage.Open(str(layer));prim=stage.GetPrimAtPath('/World/Information/FemaEffectiveFloodHazards')
    if not prim or UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':raise ValueError('FEMA root must be explicitly default-off')
    for p in stage.Traverse():
        path=str(p.GetPath())
        if path not in ('/World','/World/Information') and not path.startswith(('/World/Information/FemaEffectiveFloodHazards','/World/FloodMaterials')):raise ValueError('Unexpected FEMA layer prim: '+path)
        if p.IsA(UsdGeom.Mesh) and UsdGeom.Mesh(p).GetSubdivisionSchemeAttr().Get()!='none':raise ValueError('FEMA reference mesh must preserve exact triangles without subdivision')
    assembly_layer=Sdf.Layer.FindOrOpen(str(assembly))
    if not assembly_layer:raise ValueError('Project assembly missing')
    dependencies={relative(root,assembly):sha(assembly),relative(root,root/'data/flood/effective_nfhl.json'):sha(root/'data/flood/effective_nfhl.json'),relative(root,root/'data/processed/active.json'):sha(root/'data/processed/active.json')}
    dependencies.update(packet['dependencies']);dependencies.update(packet['artifacts'])
    manual=root/'scene/manual_edits.usda'
    if manual.exists():dependencies[relative(root,manual)]=sha(manual)
    return {'status':'validated_not_activated','source_snapshot':packet['source_snapshot'],'layer':key,'layer_sha256':sha(layer),
        'dependencies':dependencies,'default_visibility':'invisible','quality':'FEMA effective reference polygons; no flood elevation/depth or parcel insurance determination',
        'root_sha256':sha(assembly),'manual_edits_modified':False,'source_layers_modified':False}


def validate_active_flood(root=ROOT):
    root=Path(root);receipt=root/'data/flood/activation.json'
    if not receipt.exists():return None
    data=json.loads(receipt.read_text(encoding='utf-8'));packet=validate_packet(root)
    if data.get('status')!='activated' or data.get('source_snapshot')!=packet['source_snapshot'] or sha(local(root,data['layer']))!=data['layer_sha256']:raise ValueError('Activated FEMA context is stale; validate/re-activate it explicitly')
    return Path(data['layer']).name


def activate(root=ROOT,apply=False):
    root=Path(root);report=validate(root)
    if not apply:return report
    return activate_optional(report,root,'flood')


def activate_optional(report,root,kind):
    """Shared local composition transaction for validated, default-off contexts."""
    root=Path(root)
    folder={'flood':root/'data/flood','water':root/'data/transport/water_context'}[kind]
    assembly=root/'scene/college_park_connected.usda';lock=root/'scene'/('.'+kind+'_activation.lock');descriptor=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        for key,digest in report['dependencies'].items():
            if sha(local(root,key))!=digest:raise ValueError('FEMA activation dependency changed: '+key)
        old=assembly.read_bytes();layer=Sdf.Layer.CreateAnonymous();layer.ImportFromString(old.decode('utf-8'));name=Path(report['layer']).name
        paths=[p for p in layer.subLayerPaths if p!=name];index=max((i for i,p in enumerate(paths) if p in ('map_extent_guard.usda','manual_edits.usda')),default=-1)+1;paths.insert(index,name);layer.subLayerPaths=paths
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup=folder/'activation_backups'/stamp;backup.mkdir(parents=True);(backup/assembly.name).write_bytes(old)
        receipt=folder/'activation.json'
        if receipt.exists():(backup/receipt.name).write_bytes(receipt.read_bytes())
        guarded_replace(assembly,layer.ExportToString().encode('utf-8'),report['root_sha256'])
        report.update({'status':'activated','activated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_after_sha256':sha(assembly),'backup':relative(root,backup)})
        temporary=receipt.with_suffix('.json.tmp')
        try:temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');os.replace(temporary,receipt)
        except Exception:
            guarded_replace(assembly,old,report['root_after_sha256'])
            if temporary.exists():temporary.unlink()
            raise
        return report
    finally:os.close(descriptor);lock.unlink()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();print(json.dumps(activate(apply=args.apply),indent=2))
