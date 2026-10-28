"""Build an original, offline USD demonstration; no GIS or external assets."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dependencies'))
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdUtils


def material(stage, name, color):
    mat = UsdShade.Material.Define(stage, '/World/Materials/' + name)
    shader = UsdShade.Shader.Define(stage, mat.GetPath().AppendChild('Surface'))
    shader.CreateIdAttr('UsdPreviewSurface')
    shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.75)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
    return mat


def box(stage, path, center, size, mat):
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1)
    cube.AddTranslateOp().Set(Gf.Vec3d(*center))
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(mat)
    return cube


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    names = ['sample.usda', 'base.usda', 'manual.usda', 'scenario.usda',
             'sample.kit', 'open_sample.py', 'sample_manifest.json']
    if any((output / name).exists() for name in names):
        raise FileExistsError('Sample output already contains generated files; choose a new directory.')
    stage = Usd.Stage.CreateNew(str(output / 'base.usda'))
    world = UsdGeom.Xform.Define(stage, '/World')
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.GetRootLayer().customLayerData = {
        'provenance': 'Original procedural demonstration; fictional layout, no surveyed GIS.',
        'license': 'CC0-1.0: generated geometry and materials dedicated to the public domain.',
    }
    palette = {'Grass': (.20,.32,.17), 'Asphalt': (.12,.13,.14),
               'Concrete': (.66,.65,.60), 'Paint': (.92,.82,.28),
               'Facade': (.72,.55,.37), 'Glass': (.12,.29,.36),
               'Trunk': (.27,.15,.08), 'Leaves': (.12,.36,.16),
               'Car': (.22,.39,.67), 'Tire': (.025,.025,.025)}
    mats = {name: material(stage, name, color) for name, color in palette.items()}
    for group in ('Sidewalks','Markings','Buildings','Trees','Cars','Lighting','Cameras'):
        UsdGeom.Xform.Define(stage, '/World/'+group)
    box(stage, '/World/Ground', (0,0,-.25), (110,130,.5), mats['Grass'])
    box(stage, '/World/Road', (0,0,.025), (12,120,.05), mats['Asphalt'])
    for side in (-1,1):
        box(stage, f'/World/Sidewalks/Side{side+1}', (side*8,0,.12), (4,120,.24), mats['Concrete'])
    for index, y in enumerate(range(-54,55,9)):
        box(stage, f'/World/Markings/Dash{index}', (0,y,.065), (.14,4,.02), mats['Paint'])
    for index, y in enumerate(range(-42,43,21)):
        for side in (-1,1):
            path = f'/World/Buildings/B{index}_{side+1}'
            height = 6 + (index % 3)*3
            box(stage, path+'/Shell', (side*20,y,height/2), (18,16,height), mats['Facade'])
            # Storefront panels face the road; original schematic detail.
            for window in range(3):
                box(stage, path+f'/Storefront{window}', (side*10.95,y-5+window*5,1.6), (.12,3.5,2.5), mats['Glass'])
            box(stage, path+'/Awning', (side*10.4,y,3.2), (1.4,15,.18), mats['Concrete'])
    for index, y in enumerate(range(-50,51,20)):
        for side in (-1,1):
            path = f'/World/Trees/T{index}_{side+1}'
            trunk = UsdGeom.Cylinder.Define(stage, path+'/Trunk')
            trunk.CreateRadiusAttr(.22); trunk.CreateHeightAttr(3.5)
            trunk.AddTranslateOp().Set(Gf.Vec3d(side*8,y,1.75))
            UsdShade.MaterialBindingAPI.Apply(trunk.GetPrim()).Bind(mats['Trunk'])
            canopy = UsdGeom.Sphere.Define(stage, path+'/Canopy')
            canopy.CreateRadiusAttr(2.1)
            canopy.AddTranslateOp().Set(Gf.Vec3d(side*8,y,4.2))
            canopy.AddScaleOp().Set(Gf.Vec3f(1,1,1.15))
            UsdShade.MaterialBindingAPI.Apply(canopy.GetPrim()).Bind(mats['Leaves'])
    for index, y in enumerate((-35,-8,24,44)):
        path = f'/World/Cars/C{index}'
        box(stage, path+'/Body', (3.8,y,.75), (1.85,4.3,.8), mats['Car'])
        box(stage, path+'/Cabin', (3.8,y,1.35), (1.6,2.2,.65), mats['Glass'])
        for side in (-1,1):
            for axle in (-1,1):
                wheel=UsdGeom.Cylinder.Define(stage,path+f'/Wheel{side+1}_{axle+1}')
                wheel.CreateAxisAttr('X'); wheel.CreateRadiusAttr(.34); wheel.CreateHeightAttr(.2)
                wheel.AddTranslateOp().Set(Gf.Vec3d(3.8+side*.94,y+axle*1.35,.43))
                UsdShade.MaterialBindingAPI.Apply(wheel.GetPrim()).Bind(mats['Tire'])
    sun = UsdLux.DistantLight.Define(stage, '/World/Lighting/Sun')
    sun.CreateIntensityAttr(2500); sun.CreateAngleAttr(1)
    sun.AddRotateXYZOp().Set(Gf.Vec3f(-35,-25,-25))
    sky = UsdLux.DomeLight.Define(stage, '/World/Lighting/Sky')
    sky.CreateIntensityAttr(450); sky.CreateColorAttr(Gf.Vec3f(.78,.86,1))
    camera = UsdGeom.Camera.Define(stage, '/World/Cameras/Overview')
    view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(105,-135,105), Gf.Vec3d(0,0,0), Gf.Vec3d(0,0,1))
    camera.AddTransformOp().Set(view.GetInverse())
    camera.CreateHorizontalApertureAttr(36)
    camera.CreateVerticalApertureAttr(20.25)  # Explicit 16:9 capture gate.
    camera.CreateFocalLengthAttr(24); camera.CreateClippingRangeAttr(Gf.Vec2f(.1,1000))
    stage.GetRootLayer().Save()
    for name, purpose in [('manual','User edits; stronger than scenario and base.'),
                          ('scenario','Scenario edits; separate from existing fictional sample base.')]:
        layer = Sdf.Layer.CreateNew(str(output / (name+'.usda')))
        layer.customLayerData = {'purpose': purpose}
        layer.Save()
    composed = Usd.Stage.CreateNew(str(output / 'sample.usda'))
    composed.GetRootLayer().subLayerPaths = ['manual.usda','scenario.usda','base.usda']
    composed.SetDefaultPrim(composed.GetPrimAtPath('/World'))
    UsdGeom.SetStageMetersPerUnit(composed,1); UsdGeom.SetStageUpAxis(composed,'Z')
    composed.GetRootLayer().Save()
    kit = '''[package]
title="TWIN Offline Sample"
version="1.0.0"
[dependencies]
"omni.kit.uiapp"={}
"omni.hydra.rtx"={}
"omni.usd"={}
"omni.kit.viewport.window"={}
"omni.kit.viewport.utility"={}
[settings.app]
name="twin_offline_sample"
[settings.app.window]
title="TWIN | Original Offline Sample"
width=1280
height=720
[settings]
renderer.enabled="rtx"
renderer.multiGpu.enabled=false
'''
    (output/'sample.kit').write_text(kit,encoding='utf-8')
    (output/'open_sample.py').write_text('''import asyncio
from pathlib import Path
import omni.kit.app
import omni.usd
import omni.ui as ui
from omni.kit.viewport.utility import get_active_viewport
from pxr import Sdf, Usd
async def open_sample():
    global sample_window
    root=Path(__file__).resolve().parent
    context=omni.usd.get_context()
    success,error=await context.open_stage_async(str(root/'sample.usda'))
    if not success: raise RuntimeError(error)
    for _ in range(10): await omni.kit.app.get_app().next_update_async()
    viewport=get_active_viewport()
    if viewport:
        viewport.camera_path='/World/Cameras/Overview'
        viewport.resolution=(1280,720)
    stage=context.get_stage()
    layers={name:Sdf.Layer.FindOrOpen(str(root/(name+'.usda'))) for name in ('manual','scenario')}
    stage.SetEditTarget(Usd.EditTarget(layers['manual']))
    sample_window=ui.Window('Offline sample edits',width=330,height=290)
    with sample_window.frame,ui.VStack(spacing=8):
        ui.Label('Fictional offline demonstration',height=24)
        status=ui.Label('Editing manual.usda; base is preserved.',height=45,word_wrap=True)
        def target(name):
            stage.SetEditTarget(Usd.EditTarget(layers[name]));status.text='Editing '+name+'.usda; base is preserved.'
        def cars(shown):
            from pxr import UsdGeom
            image=UsdGeom.Imageable(stage.GetPrimAtPath('/World/Cars'))
            if shown:image.MakeVisible()
            else:image.MakeInvisible()
            status.text='Car visibility changed in '+stage.GetEditTarget().GetLayer().GetDisplayName()+'. Manual overrides scenario.'
        def save():
            layer=stage.GetEditTarget().GetLayer()
            if layer not in layers.values():raise RuntimeError('Only manual/scenario edits may be saved')
            layer.Save();status.text='Saved '+layer.GetDisplayName()+' only.'
        ui.Button('Edit manual layer',clicked_fn=lambda:target('manual'))
        ui.Button('Edit scenario layer',clicked_fn=lambda:target('scenario'))
        ui.Button('Hide cars in selected edit layer',clicked_fn=lambda:cars(False))
        ui.Button('Show cars in selected edit layer',clicked_fn=lambda:cars(True))
        ui.Button('Save selected edits',clicked_fn=save)
sample_startup_task=asyncio.ensure_future(open_sample())
''',encoding='utf-8')
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(output/'sample.usda'))
    if unresolved or assets or any(not Path(layer.realPath).is_relative_to(output) for layer in layers):
        raise RuntimeError('Sample contains unresolved or external dependencies')
    manifest = {'format_version':1, 'scene':'sample.usda', 'fictional':True,
                'license':'CC0-1.0', 'counts':{'buildings':10,'trees':12,'cars':4},
                'camera':'/World/Cameras/Overview', 'render_resolution':[1280,720],
                'camera_aperture_mm':[36,20.25], 'meters_per_unit':1,'up_axis':'Z',
                'layers':['manual.usda','scenario.usda','base.usda'],
                'external_assets':[], 'unresolved_assets':[],
                'sha256':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in names if name!='sample_manifest.json'}}
    (output/'sample_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path,help='New output directory; relative paths use the current working directory.')
    args=parser.parse_args()
    print(json.dumps(build(args.output),indent=2))
