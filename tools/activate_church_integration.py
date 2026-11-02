"""Prepare/apply a guarded, local-only historical church layer; no editor reload.

Preparation publishes only an ignored plan/archive. Application is explicit and
adds one root sublayer after manual, with rollback backups and preserved opinions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
from pxr import Sdf, Usd, UsdGeom
from accepted_scene_layers import manual_model_fingerprint

BASE = 'data/diagnostics/church_integration_20261102_b/'
LAYER = 'scene/church_historical.usda'
RECEIPT = 'data/processed/church_historical_activation.json'
SNAPSHOT = '20261028T160543372334Z'
FIXED = {
    BASE + 'manifest.json': '14e13bfce1f39555a9768c47d66bff4514be237cf44ab290a9089acce2ba8af4',
    BASE + 'site.usda': '55388928a2750ed22e739ef9fad2c5137835a60335a3abe45ab08cc1c50e3fbc',
    BASE + 'captured_helper.py': 'b32b031c1156ad9632476558bd6423999f488ff42073185384379c96e30bbbcf',
    'docs/evidence/church-integration-package-review.json': 'a3657cbb5dc905add1653f2ce0409daadfdbf5b4cb354a7fa3fc88871c892957',
    'docs/evidence/church-frame-gate-review.json': '857dab326beaaf92ddfa4d80f4fe6bfde908e8e9678e688ebe52067d7fb1867d',
    'docs/evidence/church-assembly-visual-review.json': '8805e3c4ee4ee591b1e868c0f95377de5dfc6c537bc969855d33c7f0dc32f426',
    'docs/evidence/church-sanctuary-v3-review.json': '4e1b4950072d2536d4840430867f69211caca8f786a94f3a73d320a8854b31b1',
    'docs/evidence/church-frontage-appearance-review.json': 'f2198864bb1b177a99458057428a088d90fbca9faf5b11280a1c99bf2ecb57ec',
    'docs/evidence/church-steeple-source-review.json': 'c30666c1a892c1bb27031d88a912392486917d48d62e4fc833f0fac46718e033',
    'docs/evidence/church-legacy-mask-review.json': '2a10edd9a4767eb03819c153be6dbf6db010c4ab34f013fe8044074a42db825f',
    'data/renders/20261102T155708Z/ChurchAssembly.png': 'f5c85995a744d73e0fe221d1efb2f9de52d73728c596ab457e05a6e74229fb5f',
    'data/renders/20261102T155708Z/manifest.json': 'd5fbe7d871994110b74b4efd3c4d5d218ee128b28dbbeb5e75a7f9f1aba962c3',
}
ARCHIVES = BASE + 'activation_source_versions/'
COMPONENTS = ['/World/Landmarks/ChurchOnDriveSanctuaryCandidateV3',
    '/World/Landmarks/ChurchOnDriveSteepleCandidate', '/World/ChurchFrontageAppearance', '/World/ChurchBelfryAppearance']
LEGACY = ['/World/Buildings/Building_2919', '/World/Roofs/Roof_2919',
          '/World/Buildings/Building_3065', '/World/Roofs/Roof_3065',
          '/World/Storefronts/Building_2919', '/World/Storefronts/Building_3065']
# Semantic source guard is fixed after independently reviewed legacy geometry;
# unrelated cameras/trees/roads/materials do not participate.
LEGACY_SHA = '0862fe207f519338f72a4353eaff956e928878339538c8961eb93b9512eaeae6'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(root, relative, digest):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file() or sha(path) != digest:
        raise ValueError('Church required source changed/missing: ' + relative)
    return path


def legacy_fingerprint(root=ROOT, paths=None):
    root = Path(root).resolve()
    stage = Usd.Stage.Open(str(root / 'scene/college_park_connected.usda'))
    if not stage:
        raise ValueError('Church legacy source stage unavailable')
    if (root / LAYER).exists():
        # Nonrecursive canonical identity check before muting the accepted
        # sanctuary correction. Never hide an arbitrary replacement file.
        receipt_path=root/RECEIPT
        if not receipt_path.is_file():raise ValueError('Church layer lacks canonical receipt')
        own=json.loads(receipt_path.read_text(encoding='utf-8'))
        if own.get('schema')!='twin.church-historical-activation/1' or own.get('layer')!=LAYER or own.get('site')!=canonical_site():
            raise ValueError('Church canonical identity changed before source fingerprint')
        if own.get('dependencies')!=recipe(root)[1] or own.get('source_snapshot')!=SNAPSHOT:
            raise ValueError('Church source recipe changed before source fingerprint')
        if own.get('layer_sha256')!=FIXED[BASE+'site.usda']:
            raise ValueError('Church receipt layer hash changed before source fingerprint')
        if any(own.get(flag) is not False for flag in ('current_geometry_verified','raw_tax_links_accepted','public_derivative_release_accepted')):
            raise ValueError('Church identity promotion forbidden')
        checked(root,LAYER,FIXED[BASE+'site.usda'])
        stage.MuteLayer(str(root / LAYER))
    elif (root/RECEIPT).exists():
        raise ValueError('Church receipt lacks layer')
    # Identity validation deliberately excludes a legacy fingerprint call, so
    # main/wing source checks cannot recurse through one another.
    from activate_church_wing import validate_wing_identity
    wing=validate_wing_identity(root)
    if wing:stage.MuteLayer(str(root/wing['layer']))
    cache = UsdGeom.XformCache()
    rows = []
    materials = set()
    for prefix in (LEGACY if paths is None else paths):
        parent = stage.GetPrimAtPath(prefix)
        if not parent:
            raise ValueError('Church required legacy group absent: ' + prefix)
        for prim in Usd.PrimRange(parent):
            for relationship in prim.GetRelationships():
                if 'material:binding' in relationship.GetName():
                    materials.update(str(target) for target in relationship.GetTargets())
            rows.append({'path': str(prim.GetPath()), 'type': prim.GetTypeName(),
                'customData': prim.GetCustomData(), 'world': str(cache.GetLocalToWorldTransform(prim)),
                'attributes': {a.GetName(): str(a.Get()) for a in prim.GetAttributes()},
                'relationships': {r.GetName(): [str(p) for p in r.GetTargets()] for r in prim.GetRelationships()}})
    for path in sorted(materials):
        material = stage.GetPrimAtPath(path)
        if not material:
            raise ValueError('Church legacy material missing: ' + path)
        for prim in Usd.PrimRange(material):
            rows.append({'path': str(prim.GetPath()), 'attributes': {a.GetName(): str(a.Get()) for a in prim.GetAttributes()},
                         'connections': {a.GetName(): [str(p) for p in a.GetConnections()] for a in prim.GetAttributes()}})
    return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()


def recipe(root=ROOT, archive=False):
    root = Path(root).resolve()
    for path, digest in FIXED.items():
        checked(root, path, digest)
    packet = json.loads((root / BASE / 'manifest.json').read_text(encoding='utf-8'))
    if packet.get('schema') != 'twin.church-integration-candidate/1' or packet.get('source_snapshot') != SNAPSHOT:
        raise ValueError('Church canonical package identity changed')
    dependencies = dict(FIXED)
    context = {}
    # Local diagnostic/source records and copied textures are critical. Broad
    # captured context layers are provenance only; exact affected legacy groups
    # are guarded semantically instead of pinning whole district files.
    for path, digest in packet['dependencies'].items():
        critical = path.startswith(('data/diagnostics/', 'assets/generated/office_brick/')) or path == 'data/buildings.geojson'
        if path.endswith('.py'):
            critical = True
            archived = ARCHIVES + digest + '_' + Path(path).name
            if archive and not (root / archived).exists():
                source = checked(root, path, digest)
                (root / archived).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, root / archived)
            checked(root, archived, digest)
            dependencies[archived] = digest
        elif critical and not path.endswith('/review.usda'):
            checked(root, path, digest)
            dependencies[path] = digest
        else:
            context[path] = digest
    dependencies['data/processed/active.json'] = packet['dependencies']['data/processed/active.json']
    for path, digest in dependencies.items():
        checked(root, path, digest)
    return packet, dependencies, context


def canonical_site():
    return {'id': 'church_on_drive_sanctuary', 'prim_path': COMPONENTS[0],
        'parcel_id': '292214146005190', 'parcel_ids': ['292214146005190'],
        'source_parcel_context': ['292214146004210', '292214146005190'], 'site_address': '1914 Edgewater Drive',
        'components': [{'id': name, 'prim_path': path} for name, path in zip(
            ['sanctuary', 'spire_proxy', 'entrance_appearance', 'belfry_appearance'], COMPONENTS)],
        'physical_building_count': None, 'rendered_entity_count': 1,
        'raw_tax_links_accepted': False, 'current_geometry_verified': False,
        'quality': 'historical_component_with_photo_interpreted_appearance',
        'limits': ['Main sanctuary assembly only, not whole campus', 'Parcel IDs are source context, not accepted tax links',
            'Historical source, current condition unknown', 'Belfry/facade dimensions photo-estimated',
            'Spire apex is highest observed return, actual tip unknown', 'Local-only; public derivative release not accepted']}


def verify_receipt(packet, root=ROOT, require_layer=True):
    root = Path(root).resolve()
    canonical, dependencies, context = recipe(root)
    if packet.get('schema') != 'twin.church-historical-activation/1' or packet.get('layer') != LAYER:
        raise ValueError('Church receipt schema/layer identity changed')
    for flag in ('current_geometry_verified', 'raw_tax_links_accepted', 'public_derivative_release_accepted'):
        if packet.get(flag) is not False:
            raise ValueError('Church cannot promote current geometry, tax identity or publication')
    if packet.get('source_snapshot') != SNAPSHOT or json.loads((root / 'data/processed/active.json').read_text())['snapshot'] != SNAPSHOT:
        raise ValueError('Church source snapshot stale')
    if packet.get('dependencies') != dependencies or packet.get('site') != canonical_site():
        raise ValueError('Church canonical source/site contract differs')
    if packet.get('layer_sha256') != FIXED[BASE + 'site.usda']:
        raise ValueError('Church layer differs from reviewed source')
    if require_layer:
        checked(root, LAYER, packet['layer_sha256'])
    if packet.get('manual_model_fingerprint') != manual_model_fingerprint(root):
        raise ValueError('Church manual model opinions changed')
    if packet.get('legacy_semantic_sha256') != LEGACY_SHA or legacy_fingerprint(root) != LEGACY_SHA:
        raise ValueError('Church legacy source identity/geometry/material/heights changed')
    return packet


def validated_church(root=ROOT):
    root = Path(root).resolve()
    layer, receipt = root / LAYER, root / RECEIPT
    if not layer.exists() and not receipt.exists():
        return None
    if not layer.is_file() or not receipt.is_file():
        raise ValueError('Church accepted layer/receipt incomplete')
    return verify_receipt(json.loads(receipt.read_text(encoding='utf-8')), root)


def prepare(root=ROOT):
    root = Path(root).resolve()
    canonical, dependencies, context = recipe(root, archive=True)
    packet = {'schema': 'twin.church-historical-activation/1', 'layer': LAYER,
        'layer_sha256': FIXED[BASE + 'site.usda'], 'source_snapshot': SNAPSHOT,
        'current_geometry_verified': False, 'raw_tax_links_accepted': False,
        'public_derivative_release_accepted': False, 'site': canonical_site(),
        'dependencies': dependencies, 'captured_comparison_context_not_live_dependencies': context,
        'legacy_semantic_sha256': LEGACY_SHA, 'manual_model_fingerprint': manual_model_fingerprint(root)}
    verify_receipt(packet, root, require_layer=False)
    target = root / BASE / 'activation_plan.json'
    if target.exists() and target.read_text(encoding='utf-8') != json.dumps(packet, indent=2):
        raise ValueError('Existing activation plan differs; preserve it for review')
    target.write_text(json.dumps(packet, indent=2), encoding='utf-8')
    return target


def apply(root=ROOT):
    root = Path(root).resolve()
    plan = root / BASE / 'activation_plan.json'
    packet = verify_receipt(json.loads(plan.read_text(encoding='utf-8')), root, require_layer=False)
    if (root / LAYER).exists() or (root / RECEIPT).exists():
        raise ValueError('Church destination already exists; do not overwrite')
    assembly = root / 'scene/college_park_connected.usda'
    original = assembly.read_bytes()
    source = Sdf.Layer.OpenAsAnonymous(str(assembly))
    layers = list(source.subLayerPaths)
    if 'manual_edits.usda' not in layers or Path(LAYER).name in layers:
        raise ValueError('Church root ordering/manual precondition failed')
    source.subLayerPaths.insert(layers.index('manual_edits.usda') + 1, Path(LAYER).name)
    # Verify only the sublayer list changed in the in-memory copy.
    new_layers = list(source.subLayerPaths)
    source.subLayerPaths = layers
    before = source.ExportToString()
    source.subLayerPaths = new_layers
    edited = source.ExportToString()
    source.subLayerPaths = layers
    if source.ExportToString() != before:
        raise ValueError('Church root opinions failed preservation check')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = root / 'data/backups' / ('church_integration_' + stamp)
    backup.mkdir(parents=True)
    (backup / assembly.name).write_bytes(original)
    (backup / 'activation_plan.json').write_bytes(plan.read_bytes())
    # Multiple-file publication cannot be globally atomic: stage layer+receipt
    # first, atomically replace root last; rollback all on any ordinary failure.
    staged = root / (LAYER + '.pending')
    pending_receipt = root / (RECEIPT + '.pending')
    pending_root = assembly.with_suffix('.church_pending.usda')
    try:
        shutil.copyfile(root / BASE / 'site.usda', staged)
        pending_receipt.write_text(json.dumps(packet, indent=2), encoding='utf-8')
        pending_root.write_text(edited, encoding='utf-8')
        verify_receipt(packet, root, require_layer=False)
        if assembly.read_bytes() != original:
            raise ValueError('Root changed during church activation; refusing overwrite')
        os.replace(staged, root / LAYER)
        os.replace(pending_receipt, root / RECEIPT)
        validated_church(root)
        if assembly.read_bytes() != original:
            raise ValueError('Root changed before publication; refusing overwrite')
        os.replace(pending_root, assembly)
    except Exception:
        for target in (root / LAYER, root / RECEIPT, staged, pending_receipt, pending_root):
            if target.exists():
                target.unlink()
        raise
    return {'backup': backup.relative_to(root).as_posix(), 'layer': LAYER, 'receipt': RECEIPT,
            'root_before_sha256': hashlib.sha256(original).hexdigest(), 'root_after_sha256': sha(assembly)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Explicit local adoption; default prepares only')
    args = parser.parse_args()
    print(json.dumps(apply() if args.apply else {'prepared_plan': str(prepare())}, indent=2))
