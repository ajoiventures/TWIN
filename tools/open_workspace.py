"""Runs inside Omniverse Kit, leaving all scene geometry editable."""
import asyncio, json
from pathlib import Path
import omni.kit.app
import omni.usd
import omni.ui as ui
import carb.settings
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from pxr import Gf

ROOT=Path(__file__).resolve().parents[1]

async def open_workspace():
    app=omni.kit.app.get_app()
    for _ in range(10):await app.next_update_async()
    while not (ROOT/'data'/'manifest.json').exists():
        await asyncio.sleep(1)
    ctx=omni.usd.get_context()
    detailed=(ROOT/'scene'/'college_park_realistic.usda').exists()
    scene_name='college_park_realistic.usda' if detailed else 'college_park.usda'
    success,error=await ctx.open_stage_async(str(ROOT/'scene'/scene_name))
    if not success:raise RuntimeError(error)
    ctx.get_selection().set_selected_prim_paths([],False)
    for _ in range(10):await app.next_update_async()
    viewport=get_active_viewport()
    if viewport:
        viewport.camera_path='/World/Cameras/TreeLinedEdgewater' if detailed else '/World/Cameras/EdgewaterCorridor'
        carb.settings.get_settings().set_bool(f'/persistent/app/viewport/{viewport.id}/guide/grid/visible',False)
    manifest=json.loads((ROOT/'data'/'manifest.json').read_text())
    counts=manifest['counts']
    detail_counts=json.loads((ROOT/'data'/'detail_manifest.json').read_text())['counts'] if detailed else {}
    def view(name):
        viewport=get_active_viewport()
        if viewport:viewport.camera_path='/World/Cameras/'+name
    def toggle(path,visible):
        from pxr import UsdGeom
        prim=ctx.get_stage().GetPrimAtPath(path)
        if prim:UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if visible else 'invisible')
    def save():
        ctx.get_stage().GetRootLayer().Save()
        status.text='Scene saved.'
    window=ui.Window('College Park | Project',width=330,height=620)
    # Retain references for the lifetime of this Kit session.
    global project_window, selection_subscription
    project_window=window
    with window.frame, ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
        with ui.VStack(spacing=8,height=0):
            ui.Label('COLLEGE PARK',height=30,style={'font_size':25,'color':0xffe2d1a1})
            ui.Label('Orlando, Florida | Edgewater corridor',height=22)
            ui.Label('Prototype 02 - Edgewater streetscape' if detailed else 'Prototype 01 - geographic base',height=22)
            ui.Separator(height=4)
            ui.Label(f"{counts['buildingMeshes']:,} buildings | {counts['roadSegments']:,} street segments",height=24)
            if detailed:ui.Label(f"{detail_counts['trees']} trees | {detail_counts['storefrontBuildings']} detailed storefront buildings",height=24)
            ui.Label('Saved views',height=23,style={'font_size':18})
            ui.Button('District overview',height=34,clicked_fn=lambda:view('DistrictOverview'))
            ui.Button('Edgewater corridor',height=34,clicked_fn=lambda:view('EdgewaterCorridor'))
            ui.Button('Close aerial view',height=34,clicked_fn=lambda:view('StreetScale'))
            if detailed:
                ui.Button('Tree-lined Edgewater',height=34,clicked_fn=lambda:view('TreeLinedEdgewater'))
                ui.Button('Storefront walk',height=34,clicked_fn=lambda:view('StorefrontWalk'))
            ui.Label('Layers',height=22,style={'font_size':18})
            layers=[('Buildings','/World/Buildings'),('Roofs','/World/Roofs'),('Streets','/World/Streets'),('Parks','/World/Parks'),('Water','/World/Water')]
            if detailed:layers += [('Trees','/World/Trees'),('Storefronts','/World/Storefronts'),('Street furniture','/World/StreetFurniture'),('Parked vehicles','/World/ParkedVehicles')]
            for label,path in layers:
                with ui.HStack(height=23):
                    model=ui.SimpleBoolModel(True)
                    ui.CheckBox(model=model,width=24)
                    ui.Label(label)
                    model.add_value_changed_fn(lambda m,p=path:toggle(p,m.as_bool))
            ui.Button('Save scene',height=34,clicked_fn=save)
            status=ui.Label('Ready. Select a building to inspect it.',height=42,word_wrap=True)
            ui.Label('Heights are estimates. Ground is flat.\nNo live traffic or sensor feeds.',height=48,word_wrap=True,style={'color':0xffa9b8cf})
            if detailed:ui.Label('Trees and storefront designs are illustrative.\nShop signs show generic categories.',height=48,word_wrap=True)
            ui.Label('Buildings: Orange County Property Appraiser\nMap: OpenStreetMap contributors (ODbL)',height=48,word_wrap=True)
            ui.Spacer(height=0)
    def selection_changed(event):
        if event.type!=int(omni.usd.StageEventType.SELECTION_CHANGED):return
        paths=ctx.get_selection().get_selected_prim_paths()
        if not paths:return
        prim=ctx.get_stage().GetPrimAtPath(paths[0])
        if not prim:return
        data=prim.GetCustomData()
        if data.get('parcelId'):
            status.text=f"{data.get('classification','Building')} | parcel {data['parcelId']}\nEstimated height: {data['heightMeters']} m"
        elif data.get('roadName'):status.text=data['roadName']
        else:status.text=prim.GetName()
    selection_subscription=ctx.get_stage_event_stream().create_subscription_to_pop(selection_changed)
    for _ in range(10):await app.next_update_async()
    stage_window=ui.Workspace.get_window('Stage')
    if stage_window:window.dock_in(stage_window,ui.DockPosition.SAME)
    print('COLLEGE_PARK_WORKSPACE_READY',counts)

asyncio.ensure_future(open_workspace())
