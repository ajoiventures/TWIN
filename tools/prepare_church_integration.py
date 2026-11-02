"""Prepare an inactive, local-only church assembly from the frozen reviewed C stack.

No activation, root rewrite, editor interaction, acquisition or public-image output.
See docs/CHURCH_INTEGRATION_CONTRACT.md. Requires a fresh output directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
from pxr import Sdf, Usd, UsdGeom

SNAPSHOT = '20261028T160543372334Z'
CAPTURE = 'data/renders/20261102T155708Z/manifest.json'
CAPTURE_SHA = 'd5fbe7d871994110b74b4efd3c4d5d218ee128b28dbbeb5e75a7f9f1aba962c3'
REVIEW_SCENE = 'scene/campus_church_combined_review_c_20261030.usda'
SOURCES = [
    'data/diagnostics/church_assembly_20261030_c/belfry.usda',
    'data/diagnostics/church_assembly_20261030_c/entrance/appearance.usda',
    'data/diagnostics/next_landmark_20261030/church_on_drive/steeple_study_v1/spire_candidate.usda',
    'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3/site.usda',
    'data/diagnostics/church_legacy_mask_20261030_c/legacy_mask.usda',
]
ROOTS = [
    '/World/Landmarks/ChurchOnDriveSanctuaryCandidateV3',
    '/World/Landmarks/ChurchOnDriveSteepleCandidate',
    '/World/ChurchFrontageAppearance',
    '/World/ChurchBelfryAppearance',
]
MASKS = ['/World/Buildings/Building_3065', '/World/Roofs/Roof_3065']
SUPPRESS = ['/World/Storefronts/Building_2919', '/World/Storefronts/Building_3065']
PHOTO = 'data/diagnostics/next_landmark_20261030/full_campus_references/drive_second_parcel_ocpa_front.jpg'
MANIFESTS = [
    'data/diagnostics/church_assembly_20261030_c/manifest.json',
    'data/diagnostics/church_assembly_20261030_c/entrance/manifest.json',
    'data/diagnostics/next_landmark_20261030/church_on_drive/sanctuary_candidate_v3/manifest.json',
    'data/diagnostics/next_landmark_20261030/church_on_drive/steeple_study_v1/evidence.json',
    'data/diagnostics/church_legacy_mask_20261030_c/manifest.json',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(output, root=ROOT):
    root = Path(root).resolve()
    output = Path(output).resolve()
    if not output.is_relative_to(root / 'data/diagnostics') or output.exists():
        raise ValueError('Require a fresh project data/diagnostics output directory')
    capture_path = root / CAPTURE
    if sha(capture_path) != CAPTURE_SHA:
        raise ValueError('Frozen reviewed capture identity changed')
    capture = json.loads(capture_path.read_text(encoding='utf-8'))
    active = json.loads((root / 'data/processed/active.json').read_text(encoding='utf-8'))
    protected = ['scene/college_park_connected.usda', 'scene/manual_edits.usda',
                 'scene/landmark_buildings.usda', 'scene/post_office_historical.usda',
                 'scene/campus_hardscape.usda', 'data/processed/active.json']
    protected_before = {p: sha(root / p) for p in protected}
    if active['snapshot'] != SNAPSHOT or capture['source_snapshot'] != SNAPSHOT:
        raise ValueError('Source snapshot changed')
    captured = {k.replace('\\', '/'): v for k, v in capture['layer_hashes'].items()}
    for relative in SOURCES:
        if not captured.get(relative) or sha(root / relative) != captured[relative]:
            raise ValueError('Reviewed source layer changed: ' + relative)
    if sha(root / REVIEW_SCENE) != capture['scene_sha256']:
        raise ValueError('Reviewed C wrapper changed')

    # Compose ONLY the five exact C contributors. Old A, full root, paving and
    # cameras never enter this stage. Flatten retains geometry-only mask overs.
    assembly = Usd.Stage.CreateInMemory()
    assembly.GetRootLayer().subLayerPaths = [str(root / x) for x in SOURCES]
    flat = assembly.Flatten()
    reviewed = Usd.Stage.Open(str(root / REVIEW_SCENE))
    reviewed_flat = reviewed.Flatten()
    candidate = Usd.Stage.CreateInMemory()
    layer = candidate.GetRootLayer()
    UsdGeom.SetStageUpAxis(candidate, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(candidate, 1)

    def copy(source, path):
        if not source.GetPrimAtPath(path):
            raise ValueError('Required source prim missing: ' + path)
        Sdf.CreatePrimInLayer(layer, Sdf.Path(path).GetParentPath())
        if not Sdf.CopySpec(source, path, layer, path):
            raise ValueError('Unable to copy source prim: ' + path)

    for path in ROOTS + MASKS:
        copy(flat, path)
    for path in SUPPRESS:
        candidate.OverridePrim(path).CreateAttribute('visibility', Sdf.ValueTypeNames.Token).Set('invisible')

    # Resolve all external relationship/connection targets from the actual C
    # composition. Copy only material subtrees, never an unrelated scene root.
    material_roots = set()
    for prim in list(candidate.TraverseAll()):
        for rel in prim.GetRelationships():
            for target in rel.GetTargets():
                if 'material:binding' not in rel.GetName():
                    continue
                target_prim = reviewed.GetPrimAtPath(target)
                if not target_prim or target_prim.GetTypeName() != 'Material':
                    raise ValueError('Unresolved bound material: ' + str(target))
                if not candidate.GetPrimAtPath(target):
                    material_roots.add(str(target))
    for path in sorted(material_roots):
        copy(reviewed_flat, path)

    # Absolute source texture references are local-only; no photograph is used
    # as a texture. Asset existence/hashes form part of the canonical recipe.
    assets = set()
    for prim in candidate.TraverseAll():
        for attr in prim.GetAttributes():
            value = attr.Get()
            if isinstance(value, Sdf.AssetPath):
                actual = Path(value.resolvedPath or value.path)
                if not actual.is_absolute() or not actual.is_file() or not actual.resolve().is_relative_to(root):
                    raise ValueError('Unresolved or external texture asset: ' + str(value))
                if actual.suffix.lower() in ('.jpg', '.jpeg') and actual.resolve() == (root / PHOTO).resolve():
                    raise ValueError('Source photograph cannot be a texture')
                attr.Set(Sdf.AssetPath(str(actual.resolve()).replace('\\', '/')))
                assets.add(actual.resolve().relative_to(root).as_posix())

    comparisons = []
    def comparable(value):
        if isinstance(value, Sdf.AssetPath):
            return str(Path(value.resolvedPath or value.path).resolve()).lower()
        return str(value)
    # Compare physical/render attributes in a temporary composition over the
    # original root, not in a flattened full-scene deliverable.
    check = Usd.Stage.CreateInMemory()
    check.GetRootLayer().subLayerPaths = [layer.identifier, str(root / 'scene/college_park_connected.usda')]
    original_xforms, candidate_xforms = UsdGeom.XformCache(), UsdGeom.XformCache()
    for path in ROOTS + MASKS + ['/World/Buildings/Building_2919', '/World/Roofs/Roof_2919']:
        before = reviewed.GetPrimAtPath(path)
        after = check.GetPrimAtPath(path)
        if not before or not after:
            raise ValueError('Comparison prim missing: ' + path)
        count = 0
        for prim in Usd.PrimRange(before):
            other = check.GetPrimAtPath(prim.GetPath())
            if not other:
                raise ValueError('Comparison descendant missing: ' + str(prim.GetPath()))
            if original_xforms.GetLocalToWorldTransform(prim) != candidate_xforms.GetLocalToWorldTransform(other):
                raise ValueError('World transform differs from C: ' + str(prim.GetPath()))
            for attr in prim.GetAttributes():
                if attr.GetName() == 'visibility':
                    continue
                equivalent = other.GetAttribute(attr.GetName())
                if comparable(attr.Get()) != comparable(equivalent.Get() if equivalent else None):
                    raise ValueError('Attribute differs from C: ' + str(attr.GetPath()))
                count += 1
            for rel in prim.GetRelationships():
                if rel.GetTargets() != other.GetRelationship(rel.GetName()).GetTargets():
                    raise ValueError('Relationship differs from C: ' + str(rel.GetPath()))
        comparisons.append({'prim_path': path, 'compared_attributes': count, 'equal_to_C': True})
    for path in SUPPRESS:
        if check.GetPrimAtPath(path).GetAttribute('visibility').Get() != 'invisible':
            raise ValueError('Storefront suppression missing')

    url = 'https://ocpaimages.ocpafl.org/api/Image/GetPIDImage?pid=292214146005190'
    for index, path in enumerate(ROOTS):
        prim = candidate.GetPrimAtPath(path)
        photo_interpreted = index >= 2
        data = dict(prim.GetCustomData())
        data.update({
            'sourceSnapshot': SNAPSHOT, 'sourceURL': url, 'publisher': 'Orange County Property Appraiser',
            'photoDate': '2021-11-08', 'acquisitionStart': '2018-12-04', 'acquisitionEnd': '2019-04-12',
            'acquisitionDateScope': 'USGS project range, not local flight date; photo date separate',
            'elevationPublisher': 'USGS 3DEP', 'verticalDatum': 'NAVD88', 'units': 'meters',
            'currentConditionsVerified': False, 'rawTaxLinksAccepted': False,
            'publicDerivativeReleaseAccepted': False,
            'appearanceId' if photo_interpreted else 'reconstructionId': 'church:1914-edgewater:' + path.split('/')[-1],
            'quality': 'illustrative_photo_interpreted_historical_appearance' if photo_interpreted else (
                'historical_lidar_derived' if index == 0 else 'historical_class1_photo_supported_nominal_spire_proxy'),
            'scopeLimit': 'Main sanctuary assembly only; not whole campus, surveyed wallline, current geometry or verified physical tip',
            'sourceParcelContext': ['292214146004210', '292214146005190'],
        })
        prim.SetCustomData(data)
    layer.customLayerData = {'schema': 'twin.church-integration-candidate/1', 'sourceSnapshot': SNAPSHOT,
        'localOnly': True, 'activated': False, 'publicDerivativeReleaseAccepted': False,
        'currentConditionsVerified': False, 'sourceCaptureManifestSha256': CAPTURE_SHA}
    dependencies = {CAPTURE: CAPTURE_SHA, REVIEW_SCENE: sha(root / REVIEW_SCENE),
                    'data/processed/active.json': sha(root / 'data/processed/active.json')}
    image = 'data/renders/20261102T155708Z/ChurchAssembly.png'
    dependencies[image] = sha(root / image)
    for relative in set(SOURCES + MANIFESTS + [PHOTO]) | assets:
        dependencies[relative] = sha(root / relative)
    # Complete source/review dependency closure from existing source manifests,
    # excluding changing full-root/manual opinions from the frozen recipe.
    for relative in MANIFESTS:
        packet = json.loads((root / relative).read_text(encoding='utf-8'))
        for key, expected in packet.get('dependencies', {}).items():
            key = key.replace('\\', '/')
            if key in ('scene/college_park_connected.usda', 'scene/manual_edits.usda'):
                continue
            path = (root / key).resolve()
            if not path.is_relative_to(root) or not path.is_file() or sha(path) != expected:
                raise ValueError('Canonical source dependency changed: ' + key)
            dependencies[key] = expected
    # Captured contributing legacy/material source layers are source evidence,
    # not the whole review stack (which also includes unrelated assets/paving).
    for prefix in ROOTS + MASKS:
        for prim in Usd.PrimRange(reviewed.GetPrimAtPath(prefix)):
            for prop in list(prim.GetAttributes()) + list(prim.GetRelationships()):
                for spec in prop.GetPropertyStack():
                    path = Path(spec.layer.realPath) if spec.layer.realPath else None
                    if path and path.is_file() and path.resolve().is_relative_to(root):
                        relative = path.resolve().relative_to(root).as_posix()
                        if relative not in ('scene/college_park_connected.usda', 'scene/manual_edits.usda') and relative not in SOURCES:
                            # Old A is superseded; only effective C-selected
                            # values are exported and compared, never A opinions.
                            if '/church_assembly_20261030/' not in relative:
                                dependencies[relative] = sha(path)
    output.mkdir(parents=True)
    archive = output / 'captured_helper.py'
    archive.write_bytes(Path(__file__).read_bytes())
    layer.Export(str(output / 'site.usda'))
    protected_after = {p: sha(root / p) for p in protected}
    if protected_before != protected_after:
        raise ValueError('Protected project files changed during preparation; do not adopt output')
    from accepted_scene_layers import manual_model_fingerprint
    manifest = {'schema': 'twin.church-integration-candidate/1', 'source_snapshot': SNAPSHOT,
        'prepared_utc': datetime.now(timezone.utc).isoformat(), 'activated': False,
        'current_geometry_verified': False, 'public_derivative_release_accepted': False,
        'scope': 'historical main sanctuary assembly, not whole church campus',
        'prim_roots': ROOTS, 'legacy_geometry_overrides': MASKS, 'suppressed_illustrative_storefronts': SUPPRESS,
        'material_roots': sorted(material_roots), 'comparisons_before_provenance_addition': comparisons,
        'protected_files_before': protected_before, 'protected_files_after': protected_after,
        'protected_files_unchanged': True, 'world_transforms_equal_to_C': True,
        'dependencies': dict(sorted(dependencies.items())),
        'producer_archive': archive.relative_to(root).as_posix(), 'producer_sha256': sha(archive),
        'manual_model_fingerprint': manual_model_fingerprint(root),
        'outputs': {'site.usda': sha(output / 'site.usda')},
        'limits': ['No activation or whole-building/current acceptance', 'Photo proportions and belfry enclosure estimated',
            'Nominal spire apex is highest observed return, not actual measured tip',
            'Legacy identity ambiguity preserved; source parcel context is not an accepted tax link',
            'Legacy remainder is an open-bottom source surface, not a watertight solid',
            'Local-only references; no photograph pixels embedded or redistributed'],
        'remaining_gates': ['Independent canonical packaging/preservation review', 'Final clean C visual decision bound to this package',
            'Church-specific activation validator and guarded additive integration; not performed here']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return {'output': output.relative_to(root).as_posix(), 'site_sha256': manifest['outputs']['site.usda'],
            'manifest_sha256': sha(output / 'manifest.json'), 'compared_attribute_count': sum(x['compared_attributes'] for x in comparisons)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT / args.output), indent=2))
