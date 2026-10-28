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
    detailed=(ROOT/'scene'/'edgewater_details.usdc').exists()
    scene_name='college_park_connected.usda' if (ROOT/'scene'/'college_park_connected.usda').exists() else 'college_park_realistic.usda' if (ROOT/'scene'/'college_park_realistic.usda').exists() else 'college_park.usda'
    success,error=await ctx.open_stage_async(str(ROOT/'scene'/scene_name))
    if not success:raise RuntimeError(error)
    from pxr import Sdf,Usd
    manual=ROOT/'scene'/'manual_edits.usda'
    if manual.exists():ctx.get_stage().SetEditTarget(Usd.EditTarget(Sdf.Layer.FindOrOpen(str(manual))))
    ctx.get_selection().set_selected_prim_paths([],False)
    for _ in range(10):await app.next_update_async()
    viewport=get_active_viewport()
    if viewport:
        for candidate in ['MainStreetOverview','WellesleyEvidence','WellesleyReview','TreeLinedEdgewater','EdgewaterCorridor']:
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/'+candidate):
                viewport.camera_path='/World/Cameras/'+candidate
                break
        carb.settings.get_settings().set_bool(f'/persistent/app/viewport/{viewport.id}/guide/grid/visible',False)
    manifest=json.loads((ROOT/'data'/'manifest.json').read_text(encoding='utf-8'))
    counts=manifest['counts']
    detail_counts=json.loads((ROOT/'data'/'detail_manifest.json').read_text(encoding='utf-8'))['counts'] if detailed else {}
    def view(name):
        viewport=get_active_viewport()
        if viewport:viewport.camera_path='/World/Cameras/'+name
    def toggle(path,visible):
        from pxr import UsdGeom
        prim=ctx.get_stage().GetPrimAtPath(path)
        if prim:UsdGeom.Imageable(prim).GetVisibilityAttr().Set('inherited' if visible else 'invisible')
    def save():
        ctx.get_stage().Save()
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
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/MainStreetOverview'):ui.Button('College Park Main Street',height=34,clicked_fn=lambda:view('MainStreetOverview'))
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/WellesleyReview'):ui.Button('Wellesley — seven-story evidence',height=34,clicked_fn=lambda:view('WellesleyReview'))
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/WellesleyEvidence'):ui.Button('Wellesley — seven-story evidence',height=34,clicked_fn=lambda:view('WellesleyEvidence'))
            ui.Button('District overview',height=34,clicked_fn=lambda:view('DistrictOverview'))
            ui.Button('Edgewater corridor',height=34,clicked_fn=lambda:view('EdgewaterCorridor'))
            ui.Button('Close aerial view',height=34,clicked_fn=lambda:view('StreetScale'))
            if detailed:
                ui.Button('Tree-lined Edgewater',height=34,clicked_fn=lambda:view('TreeLinedEdgewater'))
                ui.Button('Storefront walk',height=34,clicked_fn=lambda:view('StorefrontWalk'))
            ui.Label('Layers',height=22,style={'font_size':18})
            layers=[('Buildings','/World/Buildings'),('Roofs','/World/Roofs'),('Streets','/World/Streets'),('Parks','/World/Parks'),('Water','/World/Water')]
            if ctx.get_stage().GetPrimAtPath('/World/ParcelBoundaries'):layers.append(('Official parcel outlines','/World/ParcelBoundaries'))
            if ctx.get_stage().GetPrimAtPath('/World/StudyBoundaries/MainStreet'):layers.append(('City Main Street boundary','/World/StudyBoundaries/MainStreet'))
            if ctx.get_stage().GetPrimAtPath('/World/StudyBoundaries/Neighborhood'):layers.append(('City neighborhood boundary','/World/StudyBoundaries/Neighborhood'))
            if detailed:layers += [('Trees','/World/Trees'),('Storefronts','/World/Storefronts'),('Street furniture','/World/StreetFurniture'),('Parked vehicles','/World/ParkedVehicles')]
            for label,path in layers:
                with ui.HStack(height=23):
                    from pxr import UsdGeom
                    model=ui.SimpleBoolModel(UsdGeom.Imageable(ctx.get_stage().GetPrimAtPath(path)).ComputeVisibility()!='invisible')
                    ui.CheckBox(model=model,width=24)
                    ui.Label(label)
                    model.add_value_changed_fn(lambda m,p=path:toggle(p,m.as_bool))
            ui.Button('Save scene',height=34,clicked_fn=save)
            status=ui.Label('Ready. Select a building to inspect it.',height=90,word_wrap=True)
            ui.Label('Heights: historical LiDAR or floor estimates. Ground is flat.\nNo live traffic or sensor feeds.',height=48,word_wrap=True,style={'color':0xffa9b8cf})
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
        official=data.get('official',{})
        if official:
            h=data.get('height',{})
            status.text=f"{official.get('site_address','Unknown address')}\nParcel: {official.get('parcel_id','unmatched')} | {official.get('match_method','source outline')}\nHeight: {h.get('height_m','unknown')} m | {h.get('quality','not verified')}\nRecent permits: {official.get('recent_permit_count','unknown')}"
            if data.get('commercialEvidence'):status.text+='\nBroker context linked; current market status: unknown.'
            return
        if data.get('parcelId'):
            status.text=f"{data.get('classification','Building')} | parcel {data['parcelId']}\nEstimated height: {data['heightMeters']} m"
        elif data.get('roadName'):status.text=data['roadName']
        else:status.text=prim.GetName()
    selection_subscription=ctx.get_stage_event_stream().create_subscription_to_pop(selection_changed)
    for _ in range(10):await app.next_update_async()
    stage_window=ui.Workspace.get_window('Stage')
    if stage_window:window.dock_in(stage_window,ui.DockPosition.SAME)
    print('COLLEGE_PARK_WORKSPACE_READY',counts)
    # Generated layers may be rebuilt outside Kit. Refresh clean generated
    # layers only; never reload the user's manual edit layer.
    watched=['main_street_palms.usda','main_street_presentation.usda','college_park.usda','edgewater_details.usdc','asset_upgrade.usda','building_heights.usda','semantic_assets.usda','official_context.usda','study_scope.usda','commercial_context.usda','landmark_corrections.usda','map_extent_guard.usda','college_park_connected.usda']
    stamps={name:(ROOT/'scene'/name).stat().st_mtime_ns for name in watched if (ROOT/'scene'/name).exists()}
    async def refresh_generated():
        while True:
            await asyncio.sleep(2)
            for name in watched:
                path=ROOT/'scene'/name
                if not path.exists():continue
                stamp=path.stat().st_mtime_ns
                if stamps.get(name)==stamp:continue
                layer=Sdf.Layer.Find(str(path).replace('\\','/'))
                if layer and layer.dirty:
                    status.text='Generated layer has unsaved edits; refresh deferred: '+name
                    continue
                if layer:layer.Reload()
                stamps[name]=stamp
                status.text='Updated model evidence loaded; manual edits preserved.'
    global refresh_task
    refresh_task=asyncio.ensure_future(refresh_generated())

asyncio.ensure_future(open_workspace())
