"""Prepare inactive CarConcept source-detail culling LODs, not decimation.

Inputs: reviewed converted_v3 package and its immutable hash manifest. Outputs:
fresh diagnostic package, explicit full/mid/far USD variants, all-angle cameras,
counts/removed source component IDs and preservation evidence. No downloads,
installs, GPU, active placement/editor/source mutation or automatic LOD switch.
Only opaque-glazing candidates are supported; occlusion requires actual review.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'PXR_WORK_THREAD_LIMIT'):
    os.environ.setdefault(key, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdUtils

SOURCE_SHA = '28737a869c9ee1ac0fd96abd9c847f385c842c71c78446ca95dd93005132cc7b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def attributes(prim):
    return {a.GetName(): (str(a.GetTypeName()), str(a.Get()), str(a.GetConnections())) for a in prim.GetAttributes()}


def category(prim):
    name = prim.GetParent().GetName()
    if 'Interior' in name:
        return 'cabin_or_under_hood_interior'
    if name.endswith('_Engine'):
        return 'engine_vent_visibility_unverified'
    if 'BrakePad' in name or 'BrakeDisc' in name:
        return 'brake_hardware_visible_through_rim_possible'
    if 'WindshieldWipers' in name:
        return 'small_exterior_wiper_detail_visible_at_close_range'
    return 'retained_exterior_or_uncategorized'


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('Choose a fresh output directory; existing candidates are preserved')
    manifest = json.loads((source / 'manifest.json').read_text())
    if manifest.get('glass_appearance_mode') != 'tinted-opaque' or sha(source / 'car.usda') != SOURCE_SHA:
        raise ValueError('Only reviewed pinned v3 opaque-tint source is supported')
    for name, digest in manifest['files'].items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or sha(path) != digest:
            raise ValueError('Source dependency mismatch: ' + name)
    protected = {str(p): sha(p) for p in source.rglob('*') if p.is_file()}
    original = Usd.Stage.Open(str(source / 'car.usda'))
    meshes = [p for p in original.Traverse() if p.IsA(UsdGeom.Mesh)]
    cache = UsdGeom.XformCache()
    records = {str(p.GetPath()): {'source_parent': p.GetParent().GetName(), 'category': category(p),
                'triangles': len(UsdGeom.Mesh(p).GetFaceVertexIndicesAttr().Get()) // 3,
                'vertices': len(UsdGeom.Mesh(p).GetPointsAttr().Get())} for p in meshes}
    output.mkdir(parents=True); shutil.copytree(source / 'textures', output / 'textures')
    for name in ('ATTRIBUTION.md', 'SOURCE_LICENSE.md'):
        shutil.copy2(source / name, output / name)
    with (output / 'ATTRIBUTION.md').open('a', encoding='utf-8') as handle:
        handle.write('\nAdditional TWIN modification: opt-in source-component culling LOD candidates; '
                     'no vertex simplification. See lod_manifest.json for exact removed components. '
                     'Occlusion, distant appearance and performance are not yet accepted.\n')
    variants = {}; source_bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render']).ComputeWorldBound(original.GetDefaultPrim()).ComputeAlignedRange()
    for level in ('full', 'mid', 'far'):
        path = output / (level + '.usda'); shutil.copy2(source / 'car.usda', path)
        stage = Usd.Stage.Open(str(path)); removed = []
        for prim in meshes:
            rec = records[str(prim.GetPath())]
            remove = level != 'full' and rec['category'] == 'cabin_or_under_hood_interior'
            remove |= level == 'far' and rec['category'] in ('engine_vent_visibility_unverified', 'brake_hardware_visible_through_rim_possible', 'small_exterior_wiper_detail_visible_at_close_range')
            if remove:
                removed.append({'path': str(prim.GetPath()), **rec})
                stage.RemovePrim(prim.GetPath())  # mesh only, never source ancestor/component transform
        stage.GetRootLayer().Save()
        reopened = Usd.Stage.Open(str(path)); remaining = [p for p in reopened.Traverse() if p.IsA(UsdGeom.Mesh)]
        for prim in remaining:
            src = original.GetPrimAtPath(prim.GetPath())
            if attributes(prim) != attributes(src) or str(prim.GetRelationships()) != str(src.GetRelationships()):
                raise ValueError('Retained primitive attributes/bindings changed: ' + str(prim.GetPath()))
            if cache.GetLocalToWorldTransform(src) != UsdGeom.XformCache().GetLocalToWorldTransform(prim):
                raise ValueError('Retained primitive world transform changed')
        # Materials and all retained authored transforms are exact, not regenerated.
        for prim in reopened.Traverse():
            if attributes(prim) != attributes(original.GetPrimAtPath(prim.GetPath())):
                raise ValueError('Retained source opinions changed: ' + str(prim.GetPath()))
        bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render']).ComputeWorldBound(reopened.GetDefaultPrim()).ComputeAlignedRange()
        variants[level] = {'mesh_count': len(remaining), 'triangles': sum(records[str(p.GetPath())]['triangles'] for p in remaining),
                           'vertices': sum(records[str(p.GetPath())]['vertices'] for p in remaining), 'removed_components': removed,
                           'bbox_equals_source': bounds == source_bounds, 'retained_attributes_world_transforms_materials_exact': True}
    stage = Usd.Stage.CreateNew(str(output / 'vehicle_lods.usda'))
    UsdGeom.SetStageUpAxis(stage, 'Z'); UsdGeom.SetStageMetersPerUnit(stage, 1)
    vehicle = UsdGeom.Xform.Define(stage, '/Vehicle'); stage.SetDefaultPrim(vehicle.GetPrim())
    vs = vehicle.GetPrim().GetVariantSets().AddVariantSet('lod')
    for level in variants:
        vs.AddVariant(level); vs.SetVariantSelection(level)
        with vs.GetVariantEditContext():
            vehicle.GetPrim().GetReferences().AddReference(level + '.usda', '/CarConcept')
    vs.SetVariantSelection('full')
    stage.GetRootLayer().customLayerData = {'candidateOnly': True, 'method': 'source detail culling, not decimation', 'automaticDistanceSelection': False}
    stage.GetRootLayer().Save()
    review = Usd.Stage.CreateNew(str(output / 'review.usda'))
    UsdGeom.SetStageUpAxis(review, 'Z'); UsdGeom.SetStageMetersPerUnit(review, 1)
    cameras = []
    for level, x in zip(variants, (-6, 0, 6)):
        xf = UsdGeom.Xform.Define(review, '/World/' + level)
        xf.GetPrim().GetReferences().AddReference('vehicle_lods.usda', '/Vehicle')
        xf.GetPrim().GetVariantSets().GetVariantSet('lod').SetVariantSelection(level)
        xf.AddTranslateOp().Set(Gf.Vec3d(x, 0, .00024107342268631093))
        for angle, offset, up in [('Front', (0, -8, 2.2), (0, 0, 1)), ('Rear', (0, 8, 2.2), (0, 0, 1)),
                                  ('Side', (8, 0, 2.2), (0, 0, 1)), ('Top', (0, 0, 16), (0, 1, 0))]:
            camera_path = '/World/Cameras/' + level + angle
            camera(review, camera_path, (x + offset[0], offset[1], offset[2]), (x, 0, .55), up)
            cameras.append(camera_path)
    for name, eye in [('LODComparisonFront', (12, -28, 14)), ('LODComparisonRear', (-12, 28, 14))]:
        path = '/World/Cameras/' + name; camera(review, path, eye, (0, 0, .55), (0, 0, 1)); cameras.append(path)
    ground = UsdGeom.Cube.Define(review, '/World/Ground'); ground.CreateSizeAttr(1)
    ground.AddTranslateOp().Set(Gf.Vec3d(0, 0, -.08)); ground.AddScaleOp().Set(Gf.Vec3f(25, 15, .1)); ground.CreateDisplayColorAttr([(.25, .27, .29)])
    UsdLux.DomeLight.Define(review, '/World/Dome').CreateIntensityAttr(700)
    sun = UsdLux.DistantLight.Define(review, '/World/Sun'); sun.CreateIntensityAttr(2200); sun.CreateAngleAttr(1)
    sun.AddRotateXYZOp().Set(Gf.Vec3f(-35, -25, 25)); review.GetRootLayer().Save()
    # Side views must not be occluded by the neighboring comparison vehicles.
    # Same camera/light/geometry opinions, with other candidates hidden only in
    # these diagnostic wrappers; no source visibility edits.
    for level in variants:
        isolated = Usd.Stage.CreateNew(str(output / (level + '_review.usda')))
        isolated.GetRootLayer().subLayerPaths = ['review.usda']
        UsdGeom.SetStageUpAxis(isolated, 'Z'); UsdGeom.SetStageMetersPerUnit(isolated, 1)
        for other in variants:
            if other != level:
                UsdGeom.Imageable(isolated.OverridePrim('/World/' + other)).CreateVisibilityAttr('invisible')
        isolated.GetRootLayer().Save()
    if UsdUtils.ComputeAllDependencies(str(output / 'review.usda'))[2]:
        raise ValueError('Unresolved package dependencies')
    if protected != {str(p): sha(p) for p in source.rglob('*') if p.is_file()}:
        raise ValueError('Source package changed')
    report = {'schema': 'twin.vehicle-detail-culling/1', 'method': 'source-component culling; no installed proper decimator found; no mesh decimation',
              'source_car_sha256': SOURCE_SHA, 'source_manifest_sha256': sha(source / 'manifest.json'), 'tool_sha256': sha(__file__),
              'variants': variants, 'default_variant': 'full', 'automatic_distance_selection': False, 'camera_paths': cameras,
              'source_preserved_file_count': len(protected), 'activation': False, 'actual_render_status': 'not_run',
              'acceptance': 'inactive geometry candidates only; occlusion, distant silhouette and performance require actual review',
              'limits': ['Opaque tint only, not physical glass', 'Interior visibility outside body or through openings unverified',
                         'Far brake/engine/wiper removal may be visibly wrong; explicit all-angle review needed',
                         'No FPS, memory, LOD-threshold, parking, vehicle-variety or district-readiness acceptance'],
              'files': {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()}}
    (output / 'lod_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def camera(stage, path, eye, target, up):
    cam = UsdGeom.Camera.Define(stage, path); cam.CreateFocalLengthAttr(45)
    cam.CreateHorizontalApertureAttr(36); cam.CreateVerticalApertureAttr(20.25); cam.CreateClippingRangeAttr(Gf.Vec2f(.05, 1000))
    cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(*up)).GetInverse())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/diagnostics/car_concept_20261030/converted_v3')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); report = build(args.source, args.output)
    print(json.dumps({level: {k: v[k] for k in ('mesh_count', 'triangles', 'vertices', 'bbox_equals_source')} for level, v in report['variants'].items()}))
