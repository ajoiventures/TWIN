"""Validate explicitly reviewed additive scene layers before a scene rebuild."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
CONFIG={'campus_hardscape':{'layer':'scene/campus_hardscape.usda','receipt':'data/processed/campus_hardscape_activation.json',
    'quality':'historical_aerial_visual_interpretation_not_surveyed',
    'source_manifest':'data/diagnostics/campus_hardscape_20261030_c/manifest.json',
    'recipe_helper_archive':'data/diagnostics/campus_hardscape_20261030_c/captured_helper.py',
    'reviews':{'docs/evidence/campus-hardscape-source-review.json','docs/evidence/campus-hardscape-c-review.json'}}}

def manual_model_fingerprint(root=ROOT):
    """Camera saves do not invalidate paving; other manual opinions still do."""
    from pxr import Sdf
    layer=Sdf.Layer.OpenAsAnonymous(str(Path(root)/'scene/manual_edits.usda'))
    if not layer:raise ValueError('Manual source unavailable')
    if layer.GetPrimAtPath('/World/Cameras'):
        edit=Sdf.BatchNamespaceEdit();edit.Add('/World/Cameras',Sdf.Path.emptyPath)
        if not layer.Apply(edit):raise ValueError('Unable to isolate manual model opinions')
    prims=[]
    def collect(prim):
        prims.append(prim)
        for child in prim.nameChildren:collect(child)
    for prim in layer.rootPrims:collect(prim)
    for prim in sorted(prims,key=lambda p:str(p.path).count('/'),reverse=True):
        if not prim.nameChildren and not prim.properties and set(prim.ListInfoKeys())<={'specifier'}:
            edit=Sdf.BatchNamespaceEdit();edit.Add(prim.path,Sdf.Path.emptyPath);layer.Apply(edit)
    return hashlib.sha256(layer.ExportToString().encode()).hexdigest()

def validated_layer(name,root=ROOT):
    root=Path(root).resolve();config=CONFIG[name];layer=root/config['layer'];receipt=root/config['receipt']
    if not layer.exists() and not receipt.exists():return None
    if not layer.is_file() or not receipt.is_file():raise ValueError('Accepted scene layer/receipt incomplete: '+name)
    p=json.loads(receipt.read_text(encoding='utf-8'))
    if p.get('schema')!='twin.accepted-scene-layer/1' or p.get('kind')!=name or p.get('layer')!=config['layer']:
        raise ValueError('Accepted scene layer identity changed')
    if p.get('quality')!=config['quality'] or p.get('current_geometry_verified') is not False:
        raise ValueError('Historical layer cannot promote current geometry')
    if p.get('public_derivative_release_accepted') is not False:raise ValueError('Local-only source cannot be promoted to public release')
    active=json.loads((root/'data/processed/active.json').read_text(encoding='utf-8'))
    if p.get('source_snapshot')!=active['snapshot']:raise ValueError('Accepted scene layer snapshot stale')
    if hashlib.sha256(layer.read_bytes()).hexdigest()!=p.get('layer_sha256'):raise ValueError('Accepted scene layer changed; review required')
    dependencies=p.get('dependencies')
    source=json.loads((root/config['source_manifest']).read_text(encoding='utf-8'))
    if source.get('schema')!='twin.campus-hardscape-candidate/1' or source.get('source_snapshot')!=active['snapshot']:
        raise ValueError('Canonical paving source identity/snapshot changed')
    recipe=source.get('dependencies')
    if not isinstance(recipe,dict) or not recipe:raise ValueError('Canonical source recipe missing')
    helper_hash=recipe.get('tools/prepare_campus_hardscape.py')
    if not helper_hash:raise ValueError('Canonical producer version missing')
    recipe={k:v for k,v in recipe.items() if k not in ('scene/college_park_connected.usda','scene/manual_edits.usda')}
    recipe.pop('tools/prepare_campus_hardscape.py')
    recipe[config['recipe_helper_archive']]=helper_hash
    required=config['reviews']|{'data/processed/active.json',config['source_manifest']}|set(recipe)
    if not isinstance(dependencies,dict) or not required.issubset(dependencies):raise ValueError('Accepted layer required evidence missing')
    if any(dependencies[k]!=digest for k,digest in recipe.items()):raise ValueError('Accepted source recipe differs from canonical source')
    if p.get('source_candidate_sha256')!=source.get('outputs',{}).get('site.usda'):raise ValueError('Accepted source candidate identity changed')
    if 'scene/college_park_connected.usda' in dependencies:raise ValueError('Additive assembly cannot be its own frozen source dependency')
    if 'scene/manual_edits.usda' in dependencies:raise ValueError('Use manual model fingerprint, not camera-sensitive raw bytes')
    if p.get('manual_model_fingerprint')!=manual_model_fingerprint(root):raise ValueError('Manual model opinions changed; review required')
    for relative,digest in dependencies.items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Accepted scene layer dependency changed: '+relative)
    return Path(config['layer']).name
