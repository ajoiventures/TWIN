"""Reference-based material proposal over historical office geometry; no facade invention."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,Sdf,Gf

def build():
    manifest=json.loads((ROOT/'data/heights/landmarks/proposal_manifest.json').read_text())
    path=ROOT/'scene/landmark_building_proposal.usda'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['layer_sha256']:raise ValueError('Geometry proposal changed')
    source=Usd.Stage.Open(str(path));stage=Usd.Stage.CreateInMemory()
    brick=UsdShade.Material.Define(stage,'/World/LandmarkMaterials/OfficeBrick')
    brick_shader=UsdShade.Shader.Define(stage,brick.GetPath().AppendChild('Surface'));brick_shader.CreateIdAttr('UsdPreviewSurface')
    brick_shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.30,.095,.045));brick_shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.9);brick.CreateSurfaceOutput().ConnectToSource(brick_shader.ConnectableAPI(),'surface')
    material=UsdShade.Material.Define(stage,'/World/LandmarkMaterials/OfficeRoof')
    shader=UsdShade.Shader.Define(stage,material.GetPath().AppendChild('Surface'));shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.10,.115,.105));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.85);material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
    office=next(s for s in manifest['sites'] if s['site_id']=='andersen_office_1615');counts=[]
    for component in office['components']:
        original=UsdGeom.Mesh(source.GetPrimAtPath(component['prim_path']));points=original.GetPointsAttr().Get();indices=original.GetFaceVertexIndicesAttr().Get();faces=original.GetFaceVertexCountsAttr().Get();normals=original.GetNormalsAttr().Get()
        mesh=UsdGeom.Mesh.Define(stage,component['prim_path']);uv=[];roof=[];offset=0
        for i,n in enumerate(faces):
            normal=normals[i];is_roof=normal[2]>.3
            if is_roof:roof.append(i)
            for index in indices[offset:offset+n]:
                p=points[index]
                uv.append((p[0]/5,p[1]/5) if is_roof else ((p[1] if abs(normal[0])>abs(normal[1]) else p[0])/.8,p[2]/1.2))
            offset+=n
        if len(uv)!=len(indices) or not roof:raise ValueError('Invalid material assignment')
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying).Set(uv)
        binding=UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim());binding.Bind(brick)
        subset=binding.CreateMaterialBindSubset('RoofMaterial',roof)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material)
        wall=binding.CreateMaterialBindSubset('WallMaterial',[i for i in range(len(faces)) if i not in set(roof)])
        UsdShade.MaterialBindingAPI.Apply(wall.GetPrim()).Bind(brick)
        binding.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)
        mesh.GetPrim().SetCustomDataByKey('appearanceReference','Official broker brochure exterior pages3/9; photo date unknown; approximate original materials, no source pixels embedded')
        counts.append({'prim_path':component['prim_path'],'roof_faces':len(roof),'total_faces':len(faces),'uv_values':len(uv)})
    stage.GetRootLayer().subLayerPaths=[str(path)]
    stage.GetRootLayer().customLayerData={'purpose':'Office appearance proposal only; reference-based brick color and dark roof, not finished materials or facade','geometryModified':False,'sourceSnapshot':manifest['source_snapshot'],'geometryProposalSha256':manifest['layer_sha256']}
    output=ROOT/'scene/landmark_appearance_proposal.usda';stage.GetRootLayer().Export(str(output));print(json.dumps(counts,indent=2))

if __name__=='__main__':build()
