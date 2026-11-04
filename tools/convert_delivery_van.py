"""Convert the pinned CC0 Innerscene delivery van into a static USD asset."""
import json
import struct
from pathlib import Path

from convert_car_concept import ROOT, Gf, Sdf, Usd, UsdGeom, UsdShade, Vt, accessor, node_matrix, sha

SOURCE = 'https://www.innerscene.com/tools/library/3d-parts/delivery-van-131990b3'
SOURCE_SHA = '9bf34cceaa3f25088d37e6e0a737effc2e5d7a47b892514782fb7a90543808d4'
DIRECTORY = ROOT / 'data/diagnostics/vehicle_body_style_sources'


def build(source: Path, output: Path):
    if output.exists():
        raise FileExistsError(output)
    if sha(source) != SOURCE_SHA:
        raise ValueError('Expected the pinned Innerscene delivery van')
    data = source.read_bytes()
    if struct.unpack_from('<III', data) != (0x46546C67, 2, len(data)):
        raise ValueError('Invalid GLB header')
    length, kind = struct.unpack_from('<II', data, 12)
    binary_length, binary_kind = struct.unpack_from('<II', data, 20 + length)
    binary = data[28 + length:]
    if (kind, binary_kind, len(binary)) != (0x4E4F534A, 0x004E4942, binary_length):
        raise ValueError('Unexpected GLB chunks')
    model = json.loads(data[20:20 + length])
    if model.get('images') or model.get('extensionsUsed') or model.get('skins') or model.get('animations'):
        raise ValueError('This converter only handles the pinned static material-factor source')

    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    van = UsdGeom.Xform.Define(stage, '/DeliveryVan')
    stage.SetDefaultPrim(van.GetPrim())
    van.GetPrim().SetCustomData({'publisher': 'Innerscene', 'license': 'CC0', 'source': SOURCE})
    axes = UsdGeom.Xform.Define(stage, '/DeliveryVan/Source')
    axes.AddRotateXOp().Set(90)
    materials = []
    for index, record in enumerate(model['materials']):
        path = f'/DeliveryVan/Materials/M{index}'
        material = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + '/Surface')
        shader.CreateIdAttr('UsdPreviewSurface')
        pbr = record['pbrMetallicRoughness']
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*pbr['baseColorFactor'][:3]))
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(pbr['metallicFactor'])
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(pbr['roughnessFactor'])
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        materials.append(material)

    def add_node(index, parent):
        node = model['nodes'][index]
        xform = UsdGeom.Xform.Define(stage, f'{parent}/Node_{index}')
        xform.AddTransformOp().Set(node_matrix(node))
        for mesh_index, primitive in enumerate(model['meshes'][node['mesh']]['primitives']):
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
    build(DIRECTORY / 'van.glb', DIRECTORY / 'delivery_van.usda')
