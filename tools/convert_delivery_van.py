"""Convert the pinned CC0 Innerscene van or SUV into a static USD asset."""
import argparse
import json
import struct
from io import BytesIO
from pathlib import Path
from PIL import Image

from convert_car_concept import ROOT, Gf, Sdf, Usd, UsdGeom, UsdShade, Vt, accessor, node_matrix, sha

SOURCE = 'https://www.innerscene.com/tools/library/3d-parts/delivery-van-131990b3'
SOURCE_SHA = '9bf34cceaa3f25088d37e6e0a737effc2e5d7a47b892514782fb7a90543808d4'
SUV_SOURCE = 'https://www.innerscene.com/tools/library/3d-parts/generic-compact-suv-9f157ee5'
SUV_SHA = 'fd08e2f12559e0c49b65a79e8c9fb3d3811b2109475c219af48a9be466612d3b'
DIRECTORY = ROOT / 'data/diagnostics/vehicle_body_style_sources'


def build(source: Path, output: Path, suv=False):
    if output.exists():
        raise FileExistsError(output)
    if sha(source) != (SUV_SHA if suv else SOURCE_SHA):
        raise ValueError('Expected the pinned Innerscene vehicle')
    data = source.read_bytes()
    if struct.unpack_from('<III', data) != (0x46546C67, 2, len(data)):
        raise ValueError('Invalid GLB header')
    length, kind = struct.unpack_from('<II', data, 12)
    binary_length, binary_kind = struct.unpack_from('<II', data, 20 + length)
    binary = data[28 + length:]
    if (kind, binary_kind, len(binary)) != (0x4E4F534A, 0x004E4942, binary_length):
        raise ValueError('Unexpected GLB chunks')
    model = json.loads(data[20:20 + length])
    if model.get('skins') or model.get('animations'):
        raise ValueError('Expected a static vehicle')

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    root = '/CompactSUV' if suv else '/DeliveryVan'
    van = UsdGeom.Xform.Define(stage, root)
    stage.SetDefaultPrim(van.GetPrim())
    van.GetPrim().SetCustomData({'publisher': 'Innerscene', 'license': 'CC0', 'source': SUV_SOURCE if suv else SOURCE})
    if suv:
        van.GetPrim().SetCustomDataByKey('glassConversion', 'Opaque PreviewSurface; transmission and refraction omitted')
    axes = UsdGeom.Xform.Define(stage, root + '/Source')
    axes.AddRotateXOp().Set(90)
    materials = []
    for index, record in enumerate(model['materials']):
        path = f'{root}/Materials/M{index}'
        material = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + '/Surface')
        shader.CreateIdAttr('UsdPreviewSurface')
        pbr = record['pbrMetallicRoughness']
        color = shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f)
        color.Set(Gf.Vec3f(*pbr.get('baseColorFactor', [1, 1, 1])[:3]))
        if 'baseColorTexture' in pbr:
            texture = model['textures'][pbr['baseColorTexture']['index']]
            image = model['images'][texture['source']]
            view = model['bufferViews'][image['bufferView']]
            start = view.get('byteOffset', 0)
            texture_dir = output.parent / 'suv_textures'
            texture_dir.mkdir(exist_ok=True)
            filename = f'color_{index}.png'
            with Image.open(BytesIO(binary[start:start + view['byteLength']])) as pixels:
                pixels.transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(texture_dir / filename)
            reader = UsdShade.Shader.Define(stage, path + '/ST')
            reader.CreateIdAttr('UsdPrimvarReader_float2')
            reader.CreateInput('varname', Sdf.ValueTypeNames.Token).Set('st')
            sampler = UsdShade.Shader.Define(stage, path + '/Color')
            sampler.CreateIdAttr('UsdUVTexture')
            sampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath('./suv_textures/' + filename))
            sampler.CreateInput('sourceColorSpace', Sdf.ValueTypeNames.Token).Set('sRGB')
            sampler.CreateInput('st', Sdf.ValueTypeNames.Float2).ConnectToSource(reader.CreateOutput('result', Sdf.ValueTypeNames.Float2))
            color.ConnectToSource(sampler.CreateOutput('rgb', Sdf.ValueTypeNames.Float3))
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(pbr['metallicFactor'])
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(pbr['roughnessFactor'])
        coat = record.get('extensions', {}).get('KHR_materials_clearcoat', {})
        if coat:
            shader.CreateInput('clearcoat', Sdf.ValueTypeNames.Float).Set(coat.get('clearcoatFactor', 0))
            shader.CreateInput('clearcoatRoughness', Sdf.ValueTypeNames.Float).Set(coat['clearcoatRoughnessFactor'])
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        materials.append(material)

    def add_node(index, parent):
        node = model['nodes'][index]
        xform = UsdGeom.Xform.Define(stage, f'{parent}/Node_{index}')
        xform.AddTransformOp().Set(node_matrix(node))
        primitives = model['meshes'][node['mesh']]['primitives'] if 'mesh' in node else []
        for mesh_index, primitive in enumerate(primitives):
            if primitive.get('mode', 4) != 4:
                raise ValueError('Expected triangle primitives')
            attributes = primitive['attributes']
            points = accessor(model, binary, attributes['POSITION'])
            normals = accessor(model, binary, attributes['NORMAL'])
            indices = accessor(model, binary, primitive['indices']).ravel()
            if len(indices) % 3 or len(points) != len(normals) or indices.max() >= len(points):
                raise ValueError('Invalid mesh indexing')
            mesh = UsdGeom.Mesh.Define(stage, f'{xform.GetPath()}/Mesh_{mesh_index}')
            mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
            mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(normals))
            mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
            mesh.CreateFaceVertexIndicesAttr(indices.astype('int32').tolist())
            mesh.CreateFaceVertexCountsAttr([3] * (len(indices) // 3))
            mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            if suv:
                uv = accessor(model, binary, attributes['TEXCOORD_0'])
                UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st', Sdf.ValueTypeNames.TexCoord2fArray, 'vertex').Set(Vt.Vec2fArray.FromNumpy(uv))
            material_index = primitive['material']
            mesh.CreateDoubleSidedAttr(model['materials'][material_index].get('doubleSided', False))
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(materials[material_index])
        for child in node.get('children', []):
            add_node(child, xform.GetPath())

    for index in model['scenes'][model.get('scene', 0)]['nodes']:
        add_node(index, axes.GetPath())
    if not stage.GetRootLayer().Export(str(output)):
        raise ValueError('Failed to export delivery van')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suv', action='store_true')
    args = parser.parse_args()
    if args.suv:
        build(DIRECTORY / 'suv.glb', DIRECTORY / 'compact_suv.usda', suv=True)
    else:
        build(DIRECTORY / 'van.glb', DIRECTORY / 'delivery_van.usda')
