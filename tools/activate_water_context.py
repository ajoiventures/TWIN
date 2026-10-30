"""Validated optional historical water context; no writes without --apply."""
from pathlib import Path
import sys,json,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.dependencies'),str(ROOT/'tools')]
from pxr import Usd,UsdGeom
from build_water_context import validate_water_context
from activate_flood_context import activate_optional
from activate_environment_assets import sha,local,relative


def validate(root=ROOT):
    root=Path(root);packet=validate_water_context(root);layer=root/'scene/water_landcover_context.usda';assembly=root/'scene/college_park_connected.usda'
    stage=Usd.Stage.Open(str(layer));prim=stage.GetPrimAtPath('/World/WaterLandcoverContext')
    if not prim or UsdGeom.Imageable(prim).ComputeVisibility()!='invisible':raise ValueError('Water context must remain default-off')
    if packet['ground_intersection'].get('display_z_is_water_elevation') is not False:raise ValueError('Reference display offset cannot be treated as water elevation')
    for p in stage.Traverse():
        if str(p.GetPath())!='/World' and not str(p.GetPath()).startswith('/World/WaterLandcoverContext'):raise ValueError('Unexpected water context prim namespace')
        if p.IsA(UsdGeom.Mesh) and UsdGeom.Mesh(p).GetSubdivisionSchemeAttr().Get()!='none':raise ValueError('Reference polygons require exact unsubdivided geometry')
    dependencies={relative(root,assembly):sha(assembly),relative(root,layer):sha(layer)}
    dependencies.update(packet['dependency_sha256'])
    for item in packet['cache_receipts']:
        if item.get('sha256'):dependencies['data/cache/water_context/'+hashlib.sha256(item['url'].encode()).hexdigest()+'.json']=item['sha256']
    for item in packet['binary_receipts'].values():dependencies[item['path']]=item['sha256']
    image=packet['shoreline_aerial_reference'];dependencies[image['image_path']]=image['image_sha256']
    for name in ('data/processed/active.json','data/transport/water_context.json','data/transport/water_context/layer_receipt.json','scene/manual_edits.usda'):
        if (root/name).exists():dependencies[name]=sha(root/name)
    return {'status':'validated_not_activated','source_snapshot':packet['source_snapshot'],'layer':relative(root,layer),'layer_sha256':sha(layer),
        'root_sha256':sha(assembly),'dependencies':dependencies,'default_visibility':'invisible','manual_edits_modified':False,'source_layers_modified':False,
        'quality':'Historical water and land-cover reference only; no current shoreline, terrain, water-level, depth or simulation acceptance'}


def validate_active_water(root=ROOT):
    root=Path(root);receipt=root/'data/transport/water_context/activation.json'
    if not receipt.exists():return None
    data=json.loads(receipt.read_text(encoding='utf-8'));packet=validate_water_context(root)
    if data.get('status')!='activated' or data.get('source_snapshot')!=packet['source_snapshot'] or sha(local(root,data['layer']))!=data['layer_sha256']:raise ValueError('Activated water context is stale; revalidate explicitly')
    return Path(data['layer']).name


def activate(root=ROOT,apply=False):
    report=validate(root)
    return activate_optional(report,root,'water') if apply else report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args();print(json.dumps(activate(apply=args.apply),indent=2))
