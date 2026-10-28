"""Small architectural work view; full-district integration remains a separate check."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Gf,Sdf,Usd,UsdGeom,UsdLux,UsdShade

def build(root=ROOT):
    folder=root/'scene';layers=['office_frontage_proposal.usda','landmark_appearance_proposal.usda']
    manifest=json.loads((root/'data/heights/landmarks/proposal_manifest.json').read_text())
    if hashlib.sha256((folder/'landmark_building_proposal.usda').read_bytes()).hexdigest()!=manifest['layer_sha256']:raise ValueError('Landmark geometry changed')
    extra=folder/'office_architectural_roof_proposal.usda'
    if extra.exists():layers.insert(1,extra.name)
    for name in layers:
        if not (folder/name).exists():raise ValueError('Missing proposal '+name)
        evidence=Sdf.Layer.FindOrOpen(str(folder/name)).customLayerData
        if evidence.get('geometryProposalSha256')!=manifest['layer_sha256']:raise ValueError('Rebuild stale derived proposal '+name)
    stage=Usd.Stage.CreateInMemory();UsdGeom.SetStageUpAxis(stage,'Z');UsdGeom.SetStageMetersPerUnit(stage,1)
    stage.GetRootLayer().subLayerPaths=[str(folder/name) for name in layers]
    UsdGeom.Xform.Define(stage,'/World')
    ground=UsdGeom.Cube.Define(stage,'/World/ReviewGround');ground.CreateSizeAttr(1)
    ground.AddTranslateOp().Set(Gf.Vec3d(-18,-624,-.11));ground.AddScaleOp().Set(Gf.Vec3f(180,180,.2))
    mat=UsdShade.Material.Define(stage,'/World/ReviewMaterial');shader=UsdShade.Shader.Define(stage,'/World/ReviewMaterial/Surface')
    shader.CreateIdAttr('UsdPreviewSurface');shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(.34,.34,.32));shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.9)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface');UsdShade.MaterialBindingAPI.Apply(ground.GetPrim()).Bind(mat)
    sun=UsdLux.DistantLight.Define(stage,'/World/ReviewLighting/Sun');sun.CreateIntensityAttr(1800);sun.CreateAngleAttr(1.2);sun.AddRotateXYZOp().Set(Gf.Vec3f(-35,-35,-25))
    sky=UsdLux.DomeLight.Define(stage,'/World/ReviewLighting/Sky');sky.CreateIntensityAttr(350);sky.CreateColorAttr(Gf.Vec3f(.8,.88,1))
    camera=UsdGeom.Camera.Define(stage,'/World/Cameras/OfficeFrontage')
    camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(-95,-684,28),Gf.Vec3d(-16,-624,5),Gf.Vec3d(0,0,1)).GetInverse())
    camera.CreateFocalLengthAttr(32);camera.CreateHorizontalApertureAttr(36);camera.CreateVerticalApertureAttr(20.25);camera.CreateClippingRangeAttr(Gf.Vec2f(.1,1000))
    stage.GetRootLayer().customLayerData={'purpose':'Isolated architectural draft, neutral context; not full-district/site/lighting acceptance','proposalHashesJson':json.dumps({name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in layers},sort_keys=True)}
    output=folder/'office_frontage_review.usda';stage.GetRootLayer().Export(str(output));return output

if __name__=='__main__':print(build())
