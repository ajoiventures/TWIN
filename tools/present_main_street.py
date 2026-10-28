"""Reversible Main Street presentation; no geographic or height edits."""
from pathlib import Path
import sys,json,math
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.dependencies'))
from pxr import Usd,UsdGeom,UsdShade,UsdLux,Gf,Sdf
from pyproj import Transformer

def build():
    pilot=json.loads((ROOT/'data/processed/pilot.json').read_text())
    project=Transformer.from_crs(4326,32617,always_xy=True)
    origin=project.transform(*json.loads((ROOT/'config/study_area.json').read_text())['local_origin_wgs84'])
    xy=[project.transform(*e['coordinates']) for e in pilot['endpoints']]
    target=Gf.Vec3d(sum(p[0] for p in xy)/len(xy)-origin[0],sum(p[1] for p in xy)/len(xy)-origin[1]+45,5)
    eye=target+Gf.Vec3d(175,-230,205)
    stage=Usd.Stage.CreateInMemory()
    camera=UsdGeom.Camera.Define(stage,'/World/Cameras/MainStreetOverview')
    camera.CreateFocalLengthAttr(55)
    camera.CreateHorizontalApertureAttr(36)
    camera.CreateVerticalApertureAttr(20.25)
    camera.CreateClippingRangeAttr(Gf.Vec2f(.5,10000))
    camera.CreateFocusDistanceAttr((eye-target).GetLength())
    # Strong miniature-style focus, adjustable in the editor; USD uses tenths
    # of scene units for focal length/aperture, scene units for focus distance.
    camera.CreateFStopAttr(.7)
    UsdGeom.Xformable(camera).AddTransformOp().Set(Gf.Matrix4d().SetLookAt(eye,target,Gf.Vec3d(0,0,1)).GetInverse())
    camera.GetPrim().SetCustomDataByKey('presentation','Main Street tilt-shift aerial; optical effect only, no geometry changes')
    for path in ['/World/StudyBoundaries']:
        UsdGeom.Imageable(stage.OverridePrim(path)).CreateVisibilityAttr('invisible')
    # Planning overlay requested by the user: faint lot lines, independent of
    # the source parcel geometry and stronger district-boundary graphics.
    UsdGeom.Imageable(stage.OverridePrim('/World/ParcelBoundaries')).CreateVisibilityAttr('inherited')
    source=Usd.Stage.Open(str(ROOT/'scene/college_park_connected.usda'))
    for prim in source.GetPrimAtPath('/World/ParcelBoundaries').GetChildren():
        curve=UsdGeom.BasisCurves.Define(stage,prim.GetPath())
        curve.CreateWidthsAttr([.04]);curve.SetWidthsInterpolation('constant')
        curve.CreateDisplayColorAttr([Gf.Vec3f(.35,.39,.36)])
        curve.CreateDisplayOpacityAttr([.18]);curve.SetDisplayOpacityInterpolation('constant')
    sun=UsdLux.DistantLight.Define(stage,'/World/Lighting/Sun')
    sun.CreateIntensityAttr(2200);sun.CreateColorAttr(Gf.Vec3f(1,.91,.77));sun.CreateAngleAttr(2)
    sun.AddRotateXYZOp().Set(Gf.Vec3f(35,-25,-35))
    sky=UsdLux.DomeLight.Define(stage,'/World/Lighting/Sky')
    sky.CreateIntensityAttr(650);sky.CreateColorAttr(Gf.Vec3f(.77,.86,1))
    # Readable natural palettes retain the existing textured street assets.
    for name,color in [('Ground',(.22,.31,.16)),('Park',(.17,.29,.12)),('Water',(.045,.16,.20))]:
        shader=UsdShade.Shader.Define(stage,'/World/Materials/'+name+'/Surface')
        shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    # Replace only the ground's texture color with a subdued landscape tone;
    # the street and facade textures remain authored by the detail generator.
    ground=UsdShade.Shader.Define(stage,'/World/DetailMaterials/Grass/Surface')
    ground.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).DisconnectSource()
    ground.GetInput('diffuseColor').Set(Gf.Vec3f(.20,.29,.13))
    for i in range(7):
        leaf=UsdShade.Shader.Define(stage,f'/World/Trees/Detailed/Tree_{i}/Materials/Leaves/Texture')
        leaf.CreateInput('scale',Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2.1,2.0,1.7,1))
    stage.GetRootLayer().customLayerData={'purpose':'Main Street tilt-shift presentation','geographic_changes':False,'source_snapshot':pilot['source_snapshot'],'focusDistanceMeters':float((eye-target).GetLength())}
    stage.GetRootLayer().Export(str(ROOT/'scene/main_street_presentation.usda'))
    print('Main Street tilt-shift camera',tuple(eye),'focus distance',round((eye-target).GetLength(),2),'m')

if __name__=='__main__':build()
