"""Prepare an isolated, static CarConcept geometry benchmark; never edit placements.

Contract: exact pinned Khronos GLB + receipt -> fresh local USD package/review.
Existing USD/NumPy/Pillow only; no network, installs, activation, or source writes.
Supports this asset's dense FLOAT/USHORT accessors and static matrix/TRS nodes.
Default Carmine materials only. PreviewSurface is NOT native glTF fidelity:
transmission uses approximate opacity, AO/tangent normals/iridescence omitted.
Logo atlas and branded tire textures/plate geometry are excluded in derivative.
Run: python tools/convert_car_concept.py --source <source-dir> --output <new-dir>
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import struct
import sys

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'PXR_WORK_THREAD_LIMIT'):
    os.environ.setdefault(_key, '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdUtils, Vt

COMMIT = '8f492390ddc7a2ae221a1369ef560589cf8c70fb'
GLB_SHA = 'c272098089d78c5cd9fd9f24ff50ee8acf8d932c55f2d55fc10adb6c8998966b'
EXCLUDED_IMAGES = {3, 10, 11}  # observed logo atlas/tire branding + conservative tire normal exclusion


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_glb(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != GLB_SHA:
        raise ValueError('Unreviewed GLB; expected pinned CarConcept bytes')
    if struct.unpack_from('<III', data) != (0x46546C67, 2, len(data)):
        raise ValueError('Invalid GLB header')
    chunks = {}; pos = 12
    while pos < len(data):
        size, kind = struct.unpack_from('<II', data, pos); pos += 8
        if pos + size > len(data) or kind in chunks:
            raise ValueError('Invalid GLB chunks')
        chunks[kind] = data[pos:pos + size]; pos += size
    g = json.loads(chunks[0x4E4F534A]); binary = chunks[0x004E4942]
    if g.get('animations') or g.get('skins') or len(g['buffers']) != 1 or 'uri' in g['buffers'][0]:
        raise ValueError('Only this static, embedded-buffer source is supported')
    return g, binary


def accessor(g, binary, index):
    a = g['accessors'][index]; b = g['bufferViews'][a['bufferView']]
    if a.get('sparse') or a.get('normalized') or b['buffer'] != 0:
        raise ValueError('Unsupported accessor encoding')
    dtype = {5123: np.dtype('<u2'), 5126: np.dtype('<f4')}[a['componentType']]
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    offset = a.get('byteOffset', 0); stride = b.get('byteStride', dtype.itemsize * width)
    if stride < width * dtype.itemsize or stride % dtype.itemsize or a['count'] < 1:
        raise ValueError('Invalid accessor stride/count')
    end = offset + stride * (a['count'] - 1) + dtype.itemsize * width
    if end > b['byteLength'] or b.get('byteOffset', 0) + b['byteLength'] > len(binary):
        raise ValueError('Accessor overruns buffer view')
    result = np.ndarray((a['count'], width), dtype=dtype, buffer=binary,
                        offset=b.get('byteOffset', 0) + offset,
                        strides=(stride, dtype.itemsize)).copy()
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite accessor')
    return result


def node_matrix(node):
    # glTF column-major flattening is the equivalent Gf row-vector matrix.
    if 'matrix' in node:
        return Gf.Matrix4d(*node['matrix'])
    t = Gf.Matrix4d().SetTranslate(Gf.Vec3d(*node.get('translation', [0, 0, 0])))
    q = node.get('rotation', [0, 0, 0, 1])
    r = Gf.Matrix4d().SetRotate(Gf.Quatd(q[3], Gf.Vec3d(*q[:3])))
    s = Gf.Matrix4d().SetScale(Gf.Vec3d(*node.get('scale', [1, 1, 1])))
    return s * r * t


def transformed_uv(uv, info):
    tr = info.get('extensions', {}).get('KHR_texture_transform', {})
    angle = tr.get('rotation', 0); c, s = math.cos(angle), math.sin(angle)
    v = uv.astype(np.float64) * tr.get('scale', [1, 1])
    return v @ np.array([[c, s], [-s, c]]) + tr.get('offset', [0, 0])


def build(source, output, glass_mode='source-opacity'):
    source, output = Path(source).resolve(), Path(output).resolve()
    if glass_mode not in ('source-opacity', 'tinted-opaque'):
        raise ValueError('Unknown glass approximation')
    if output.exists():
        raise FileExistsError('Choose a fresh output directory')
    receipt = json.loads((source / 'acquisition.json').read_text())
    if receipt['commit'] != COMMIT:
        raise ValueError('Wrong acquisition commit')
    for f in receipt['files']:
        if sha(source / f['file']) != f['sha256']:
            raise ValueError('Source receipt mismatch: ' + f['file'])
    g, binary = read_glb(source / 'CarConcept.glb')
    output.mkdir(parents=True); (output / 'textures').mkdir()
    # Flip derivative image rows, not source bytes: glTF UV origin is upper-left.
    texture_paths = {}
    for i, im in enumerate(g['images']):
        if i in EXCLUDED_IMAGES:
            continue
        b = g['bufferViews'][im['bufferView']]; start = b.get('byteOffset', 0)
        from io import BytesIO
        image = Image.open(BytesIO(binary[start:start + b['byteLength']]))
        path = output / 'textures' / f'image_{i:02}.png'
        image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(path)
        texture_paths[i] = 'textures/' + path.name
    stage = Usd.Stage.CreateNew(str(output / 'car.usda'))
    UsdGeom.SetStageUpAxis(stage, 'Z'); UsdGeom.SetStageMetersPerUnit(stage, 1)
    asset = UsdGeom.Xform.Define(stage, '/CarConcept'); stage.SetDefaultPrim(asset.GetPrim())
    asset.GetPrim().SetCustomDataByKey('quality', 'Licensed concept-car benchmark; placements unverified; partial PreviewSurface conversion')
    source_root = UsdGeom.Xform.Define(stage, '/CarConcept/Source')
    axis = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), 90))
    source_root.AddTransformOp().Set(axis)
    mats = {}; material_uvs = {}; omitted = []
    for mi, mat in enumerate(g['materials']):
        m = UsdShade.Material.Define(stage, f'/CarConcept/Materials/M{mi}')
        shader = UsdShade.Shader.Define(stage, m.GetPath().AppendChild('Surface'))
        shader.CreateIdAttr('UsdPreviewSurface')
        m.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        pbr = mat.get('pbrMetallicRoughness', {}); base = pbr.get('baseColorFactor', [1, 1, 1, 1])
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*base[:3]))
        if mi == 18:  # logo-bearing tire albedo removed, retain unbranded rubber appearance
            shader.GetInput('diffuseColor').Set(Gf.Vec3f(.012, .012, .012))
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(pbr.get('metallicFactor', 1))
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(pbr.get('roughnessFactor', 1))
        extensions = mat.get('extensions', {}); coat = extensions.get('KHR_materials_clearcoat', {})
        shader.CreateInput('clearcoat', Sdf.ValueTypeNames.Float).Set(coat.get('clearcoatFactor', 0))
        shader.CreateInput('clearcoatRoughness', Sdf.ValueTypeNames.Float).Set(coat.get('clearcoatRoughnessFactor', 0))
        emission = np.array(mat.get('emissiveFactor', [0, 0, 0])) * extensions.get('KHR_materials_emissive_strength', {}).get('emissiveStrength', 1)
        if mat.get('emissiveTexture', {}).get('index') == 3:
            emission[:] = 0
        shader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, emission)))
        if extensions.get('KHR_materials_transmission', {}).get('transmissionFactor', 0):
            shader.CreateInput('opacity', Sdf.ValueTypeNames.Float).Set(.18 if glass_mode == 'source-opacity' else 1.)
            shader.CreateInput('ior', Sdf.ValueTypeNames.Float).Set(1.5)
            if glass_mode == 'tinted-opaque':
                # Explicit appearance fallback after actual v2 RTX proof showed
                # milky triangle-patterned opacity. This is a reflective tint,
                # NOT transmitted/refracted glass or preserved native fidelity.
                shader.GetInput('diffuseColor').Set(Gf.Vec3f(.006, .012, .018))
                shader.GetInput('roughness').Set(.08)
                shader.CreateInput('useSpecularWorkflow', Sdf.ValueTypeNames.Int).Set(1)
                shader.CreateInput('specularColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.10, .13, .16))
                shader.GetInput('clearcoat').Set(1.)
                shader.GetInput('clearcoatRoughness').Set(.045)
                shader.GetPrim().SetCustomDataByKey('appearanceApproximation', 'Opaque dark reflective tint; no glass transmission/refraction; v2 opacity visual failure')
        material_uvs[mi] = []

        def texture(info, role, color, scale):
            image_index = g['textures'][info['index']]['source']
            if image_index in EXCLUDED_IMAGES:
                omitted.append({'material': mi, 'role': role, 'image': image_index}); return None
            tr = info.get('extensions', {}).get('KHR_texture_transform', {})
            uvset = tr.get('texCoord', info.get('texCoord', 0))
            pv = f'uv_m{mi}_{role}'; material_uvs[mi].append((pv, uvset, info))
            reader = UsdShade.Shader.Define(stage, m.GetPath().AppendChild(role + 'UV'))
            reader.CreateIdAttr('UsdPrimvarReader_float2'); reader.CreateInput('varname', Sdf.ValueTypeNames.Token).Set(pv)
            tex = UsdShade.Shader.Define(stage, m.GetPath().AppendChild(role + 'Texture'))
            tex.CreateIdAttr('UsdUVTexture')
            tex.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture_paths[image_index]))
            tex.CreateInput('sourceColorSpace', Sdf.ValueTypeNames.Token).Set('sRGB' if color else 'raw')
            tex.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), 'result')
            tex.CreateInput('scale', Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*scale))
            sampler = g.get('samplers', [{}])[g['textures'][info['index']].get('sampler', 0)]
            for dim in ('S', 'T'):
                tex.CreateInput('wrap' + dim, Sdf.ValueTypeNames.Token).Set({10497: 'repeat', 33071: 'clamp', 33648: 'mirror'}[sampler.get('wrap' + dim, 10497)])
            return tex

        if 'baseColorTexture' in pbr:
            tex = texture(pbr['baseColorTexture'], 'base', True, base)
            if tex:
                shader.GetInput('diffuseColor').ConnectToSource(tex.ConnectableAPI(), 'rgb')
        if 'metallicRoughnessTexture' in pbr:
            tex = texture(pbr['metallicRoughnessTexture'], 'metalRough', False,
                          [1, pbr.get('roughnessFactor', 1), pbr.get('metallicFactor', 1), 1])
            if tex:
                shader.GetInput('roughness').ConnectToSource(tex.ConnectableAPI(), 'g')
                shader.GetInput('metallic').ConnectToSource(tex.ConnectableAPI(), 'b')
        if 'emissiveTexture' in mat:
            tex = texture(mat['emissiveTexture'], 'emission', True, [*map(float, emission), 1])
            if tex:
                shader.GetInput('emissiveColor').ConnectToSource(tex.ConnectableAPI(), 'rgb')
        mats[mi] = m
    records = []; expected_world = []; paths = set()

    def visit(index, parent, parent_matrix):
        if index in paths:
            raise ValueError('Repeated/cyclic source node unsupported')
        paths.add(index); n = g['nodes'][index]
        if index == 32:
            if n.get('name') != 'License Plate' or n.get('children'):
                raise ValueError('Logo exclusion source identity changed')
            return
        path = parent + f'/N{index}_{TfValid(n.get("name", "Node"))}'
        x = UsdGeom.Xform.Define(stage, path); matrix = node_matrix(n)
        x.AddTransformOp().Set(matrix); world = matrix * parent_matrix
        if 'mesh' in n:
            for pi, primitive in enumerate(g['meshes'][n['mesh']]['primitives']):
                if primitive.get('mode', 4) != 4 or primitive.get('targets'):
                    raise ValueError('Unsupported primitive mode/morph')
                arrays = {k: accessor(g, binary, v) for k, v in primitive['attributes'].items()}
                points = arrays['POSITION']; indices = accessor(g, binary, primitive['indices']).reshape(-1)
                if any(len(v) != len(points) for v in arrays.values()):
                    raise ValueError('Attribute cardinality mismatch')
                if len(indices) % 3 or indices.max() >= len(points):
                    raise ValueError('Invalid triangle indices')
                mesh = UsdGeom.Mesh.Define(stage, path + f'/Primitive{pi}')
                mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
                mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * (len(indices) // 3)))
                mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(indices.astype(np.int32)))
                mesh.CreateSubdivisionSchemeAttr('none'); mesh.CreateOrientationAttr('rightHanded')
                mi = primitive.get('material', 0)
                mesh.CreateDoubleSidedAttr(g['materials'][mi].get('doubleSided', False))
                if 'NORMAL' in arrays:
                    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(arrays['NORMAL'])); mesh.SetNormalsInterpolation('vertex')
                api = UsdGeom.PrimvarsAPI(mesh)
                for key in ('TEXCOORD_0', 'TEXCOORD_1'):
                    if key in arrays:
                        api.CreatePrimvar('st' if key.endswith('0') else 'st1', Sdf.ValueTypeNames.TexCoord2fArray, 'vertex').Set(Vt.Vec2fArray.FromNumpy(arrays[key]))
                if 'TANGENT' in arrays:
                    api.CreatePrimvar('sourceTangent', Sdf.ValueTypeNames.Float4Array, 'vertex').Set(Vt.Vec4fArray.FromNumpy(arrays['TANGENT']))
                for name, uvset, info in material_uvs[mi]:
                    uv = transformed_uv(arrays[f'TEXCOORD_{uvset}'], info).astype(np.float32)
                    api.CreatePrimvar(name, Sdf.ValueTypeNames.TexCoord2fArray, 'vertex').Set(Vt.Vec2fArray.FromNumpy(uv))
                UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(mats[mi])
                observed = np.array(mesh.GetPointsAttr().Get())
                if not np.array_equal(observed, points):
                    raise ValueError('Source point preservation failed')
                if 'NORMAL' in arrays and not np.array_equal(np.array(mesh.GetNormalsAttr().Get()), arrays['NORMAL']):
                    raise ValueError('Source normal preservation failed')
                if not np.array_equal(np.array(mesh.GetFaceVertexIndicesAttr().Get()), indices):
                    raise ValueError('Source topology preservation failed')
                coords = np.array([world.Transform(Gf.Vec3d(*map(float, p))) for p in points])
                expected_world.append(coords)
                records.append({'path': str(mesh.GetPath()), 'node': index, 'source_mesh': n['mesh'], 'primitive': pi,
                                'vertices': len(points), 'triangles': len(indices) // 3})
        for child in n.get('children', []):
            visit(child, path, world)

    for node in g['scenes'][g.get('scene', 0)]['nodes']:
        visit(node, '/CarConcept/Source', axis)
    stage.GetRootLayer().Save()
    reopened = Usd.Stage.Open(str(output / 'car.usda')); cache = UsdGeom.XformCache()
    max_transform_delta = 0.; actual = []
    for record, expected in zip(records, expected_world):
        mesh = UsdGeom.Mesh(reopened.GetPrimAtPath(record['path'])); matrix = cache.GetLocalToWorldTransform(mesh.GetPrim())
        coords = np.array([matrix.Transform(Gf.Vec3d(*map(float, p))) for p in mesh.GetPointsAttr().Get()])
        max_transform_delta = max(max_transform_delta, float(np.abs(coords - expected).max())); actual.append(coords)
    allpoints = np.vstack(actual); bounds = [allpoints.min(0).tolist(), allpoints.max(0).tolist()]
    if max_transform_delta > 1e-9:
        raise ValueError('Composed transform preservation failed')
    review = Usd.Stage.CreateNew(str(output / 'review.usda'))
    review.GetRootLayer().subLayerPaths = ['car.usda']; UsdGeom.SetStageUpAxis(review, 'Z'); UsdGeom.SetStageMetersPerUnit(review, 1)
    lower, upper = map(np.array, bounds); center = (lower + upper) / 2; radius = float(np.linalg.norm(upper - lower)) / 2
    ground = UsdGeom.Cube.Define(review, '/Review/Ground'); ground.CreateSizeAttr(1)
    ground.AddTranslateOp().Set(Gf.Vec3d(float(center[0]), float(center[1]), float(lower[2] - .06)))
    ground.AddScaleOp().Set(Gf.Vec3f(float(radius * 5), float(radius * 5), .1)); ground.CreateDisplayColorAttr([( .25, .27, .29)])
    camera = UsdGeom.Camera.Define(review, '/Review/Camera'); camera.CreateFocalLengthAttr(45)
    camera.CreateHorizontalApertureAttr(36); camera.CreateVerticalApertureAttr(20.25)
    eye = center + np.array([1.1, -1.5, .85]) * radius * 2.6
    view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*center), Gf.Vec3d(0, 0, 1))
    camera.AddTransformOp().Set(view.GetInverse()); camera.CreateClippingRangeAttr(Gf.Vec2f(.05, 1000))
    dome = UsdLux.DomeLight.Define(review, '/Review/Dome'); dome.CreateIntensityAttr(700)
    sun = UsdLux.DistantLight.Define(review, '/Review/Sun'); sun.CreateIntensityAttr(2200)
    sun.CreateAngleAttr(1); sun.AddRotateXYZOp().Set(Gf.Vec3f(-35, -25, 25))
    review.GetRootLayer().Save()
    # Honest comparison references the actual composed active prototype, not raw
    # procedural source missing material overrides. Reset placement only here.
    project = ROOT / 'scene/college_park_connected.usda'
    composed = Usd.Stage.Open(str(project))
    car_path = '/World/ParkedVehicles/Car_000/DetailedSedan'
    if not composed.GetPrimAtPath(car_path):
        raise ValueError('Current composed car prototype unavailable')
    comparison = Usd.Stage.CreateNew(str(output / 'compare.usda'))
    UsdGeom.SetStageUpAxis(comparison, 'Z'); UsdGeom.SetStageMetersPerUnit(comparison, 1)
    current = UsdGeom.Xform.Define(comparison, '/Comparison/Current')
    current.GetPrim().GetReferences().AddReference(os.path.relpath(project, output).replace('\\', '/'), car_path)
    current.GetPrim().SetInstanceable(False); current.SetXformOpOrder([], resetXformStack=True)
    current.AddTranslateOp(opSuffix='comparison').Set(Gf.Vec3d(-3.5, 0, 0))
    candidate = UsdGeom.Xform.Define(comparison, '/Comparison/Candidate')
    candidate.GetPrim().GetReferences().AddReference('car.usda', '/CarConcept')
    candidate.AddTranslateOp(opSuffix='comparison').Set(Gf.Vec3d(3.5, 0, -float(lower[2])))
    candidate.AddRotateZOp(opSuffix='comparison').Set(90)  # align length with current +X; not a placement claim
    floor = UsdGeom.Cube.Define(comparison, '/Comparison/Ground'); floor.CreateSizeAttr(1)
    floor.AddTranslateOp().Set(Gf.Vec3d(0, 0, -.08)); floor.AddScaleOp().Set(Gf.Vec3f(18, 12, .1))
    floor.CreateDisplayColorAttr([(.25, .27, .29)])
    for name, eye, target in [('CompareCamera', (11, -17, 10), (0, 0, .6)),
                              ('CandidateDetail', (7, -6, 3.6), (3.5, 0, .6))]:
        cam = UsdGeom.Camera.Define(comparison, '/Comparison/' + name)
        cam.CreateFocalLengthAttr(45); cam.CreateHorizontalApertureAttr(36); cam.CreateVerticalApertureAttr(20.25)
        cam.CreateClippingRangeAttr(Gf.Vec2f(.05, 1000))
        cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye), Gf.Vec3d(*target), Gf.Vec3d(0, 0, 1)).GetInverse())
    UsdLux.DomeLight.Define(comparison, '/Comparison/Dome').CreateIntensityAttr(700)
    distant = UsdLux.DistantLight.Define(comparison, '/Comparison/Sun'); distant.CreateIntensityAttr(2200)
    distant.CreateAngleAttr(1); distant.AddRotateXYZOp().Set(Gf.Vec3f(-35, -25, 25))
    comparison.GetRootLayer().Save()
    deps = UsdUtils.ComputeAllDependencies(str(output / 'review.usda'))
    if deps[2]:
        raise ValueError('Unresolved asset dependencies: ' + str(deps[2]))
    (output / 'ATTRIBUTION.md').write_text(
        '# CarConcept derivative benchmark\n\n© 2024 Darmstadt Graphics Group GmbH. Model/textures by Eric Chadwick.\n'
        'License: CC BY 4.0 https://creativecommons.org/licenses/by/4.0/\n'
        f'Source: https://github.com/KhronosGroup/glTF-Sample-Assets/tree/{COMMIT}/Models/CarConcept\n\n'
        'Modifications: static USD conversion, Y-up to Z-up, image vertical orientation, omitted license plate, '
        'Khronos logo atlas and branded tire base/normal textures. Default Carmine only. No endorsement.\n'
        f'Glass appearance mode: {glass_mode}. Source-opacity approximates transmission with opacity; tinted-opaque '
        'uses an opaque dark reflective surface with NO transmission/refraction. Tangent normal maps, AO and iridescence are omitted. '
        'This is not full native glTF PBR fidelity, a real vehicle survey, or accepted district placement.\n', encoding='utf-8')
    (output / 'SOURCE_LICENSE.md').write_bytes((source / 'LICENSE.md').read_bytes())
    report = {'schema': 'twin.car-concept-benchmark/1', 'commit': COMMIT, 'source_glb_sha256': GLB_SHA,
              'source_receipt_sha256': sha(source / 'acquisition.json'), 'tool_sha256': sha(__file__),
              'excluded_node': 32, 'excluded_image_indices': sorted(EXCLUDED_IMAGES), 'omitted_bindings': omitted,
              'mesh_records': records, 'mesh_count': len(records), 'triangle_count': sum(r['triangles'] for r in records),
              'vertex_count': sum(r['vertices'] for r in records), 'bbox_z_up_m': bounds,
              'max_world_transform_delta_m': max_transform_delta, 'unresolved_dependencies': [],
              'geometry_arrays_preserved': True, 'render_status': 'not_run', 'activation': False,
              'glass_appearance_mode': glass_mode,
              'comparison_current_prim': car_path, 'comparison_current_root_sha256': sha(project),
              'comparison_cameras': ['/Comparison/CompareCamera', '/Comparison/CandidateDetail'],
              'limits': ['Default Carmine only; no material variants authored', f'Glass {glass_mode} approximation, not native refraction/transmission',
                         'Tangent normal maps, AO and iridescence omitted', 'No observed placement/parking accuracy', 'No visual acceptance yet'],
              'files': {str(p.relative_to(output)): sha(p) for p in output.rglob('*') if p.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def TfValid(value):
    from pxr import Tf
    return Tf.MakeValidIdentifier(value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path); parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--glass-mode', choices=('source-opacity', 'tinted-opaque'), default='source-opacity')
    args = parser.parse_args(); result = build(args.source, args.output, args.glass_mode)
    print(json.dumps({k: result[k] for k in ('mesh_count', 'triangle_count', 'vertex_count', 'bbox_z_up_m', 'max_world_transform_delta_m')}))
