"""Runs inside Omniverse Kit, leaving all scene geometry editable."""
import asyncio, json, sys
from pathlib import Path
import omni.kit.app
import omni.usd
import omni.ui as ui
import carb.settings
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from pxr import Gf

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from workspace_evidence import inspector_text, inherited_evidence, set_session_visibility, visible, save_manual_only, available_display_groups, should_open_project, is_project_stage, registry_index, SessionConfidenceFilter, CONFIDENCE_CATEGORIES
from selection_bridge import read_state as bridge_state, publish as bridge_publish, load_context as bridge_context, selection_identity, counterpart_paths, acknowledge, SelectionError
project_window=None
startup_task=None

async def open_workspace():
    global project_window, selection_subscription, confidence_controller
    if 'confidence_controller' in globals():confidence_controller.reset()
    if project_window is None:
        project_window=ui.Window('College Park | Project',width=360,height=700)
    window=project_window
    with window.frame, ui.VStack(spacing=10):
        ui.Label('COLLEGE PARK',height=30,style={'font_size':25})
        startup_status=ui.Label('Loading project status…',height=150,word_wrap=True)
        ui.Button('Retry project startup',height=34,clicked_fn=retry_startup)
    app=omni.kit.app.get_app()
    await app.next_update_async()
    try:
        manifest_path=ROOT/'data'/'manifest.json'
        if not manifest_path.is_file():
            raise FileNotFoundError('Project dataset is missing: data/manifest.json. Build or restore the local dataset, then Retry. Your open stage is preserved.')
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        counts=manifest.get('counts',{})
    except Exception as error:
        startup_status.text='Project not ready. '+str(error)
        return
    ctx=omni.usd.get_context()
    detailed=(ROOT/'scene'/'edgewater_details.usdc').exists()
    scene_name='college_park_connected.usda' if (ROOT/'scene'/'college_park_connected.usda').exists() else 'college_park_realistic.usda' if (ROOT/'scene'/'college_park_realistic.usda').exists() else 'college_park.usda'
    try:
        current=ctx.get_stage()
        opened_new=False
        # Retain an already open editor stage, including unsaved user work.
        if should_open_project(current):
            success,error=await ctx.open_stage_async(str(ROOT/'scene'/scene_name))
            if not success:raise RuntimeError(error)
            opened_new=True
        if ctx.get_stage() is None:raise RuntimeError('No editable stage is available')
        project_stage=is_project_stage(ctx.get_stage(),[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')])
    except Exception as error:
        startup_status.text='Scene could not open. '+str(error)+'\nUse Retry after restoring the local scene. Existing work is preserved.'
        return
    from pxr import Sdf,Usd
    manual=ROOT/'scene'/'manual_edits.usda'
    if opened_new and manual.exists():
        manual_layer=next((layer for layer in ctx.get_stage().GetLayerStack() if layer.realPath and Path(layer.realPath).resolve()==manual.resolve()),None)
        if manual_layer:ctx.get_stage().SetEditTarget(Usd.EditTarget(manual_layer))
    if opened_new:ctx.get_selection().set_selected_prim_paths([],False)
    for _ in range(10):await app.next_update_async()
    viewport=get_active_viewport()
    if viewport and opened_new:
        for candidate in ['MainStreetOverview','WellesleyEvidence','WellesleyReview','TreeLinedEdgewater','EdgewaterCorridor']:
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/'+candidate):
                viewport.camera_path='/World/Cameras/'+candidate
                break
        carb.settings.get_settings().set_bool(f'/persistent/app/viewport/{viewport.id}/guide/grid/visible',False)
    try:
        detail_counts=json.loads((ROOT/'data'/'detail_manifest.json').read_text(encoding='utf-8')).get('counts',{}) if detailed else {}
    except (OSError,ValueError):detail_counts={}
    try:
        active_packet=json.loads((ROOT/'data/processed/active.json').read_text())
        project_refresh=active_packet.get('activated_utc');active_snapshot=active_packet.get('snapshot')
    except (OSError,ValueError):project_refresh=active_snapshot=None
    try:
        evidence_registry=registry_index(json.loads((ROOT/'data/processed/asset_registry.json').read_text(encoding='utf-8')))
    except (OSError,ValueError,TypeError):evidence_registry={}
    confidence_controller=SessionConfidenceFilter(ctx.get_stage(),active_snapshot if project_stage else None)
    confidence_counts=confidence_controller.counts()
    registry_stamp=None
    confidence_enabled={key for key,label in CONFIDENCE_CATEGORIES};confidence_mode={'enabled':False}
    def refresh_confidence():
        nonlocal project_refresh,active_snapshot,evidence_registry,registry_stamp
        try:
            packet=json.loads((ROOT/'data/processed/active.json').read_text())
            project_refresh=packet.get('activated_utc');active_snapshot=packet.get('snapshot')
        except (OSError,ValueError):project_refresh=active_snapshot=None
        confidence_controller.active_snapshot=active_snapshot if project_stage else None
        try:
            registry_path=ROOT/'data/processed/asset_registry.json';stamp=registry_path.stat().st_mtime_ns
            if stamp!=registry_stamp:
                evidence_registry=registry_index(json.loads(registry_path.read_text(encoding='utf-8')));registry_stamp=stamp
        except (OSError,ValueError,TypeError):evidence_registry={};registry_stamp=None
    def filter_confidence(key=None,enabled=None):
        try:
            if ctx.get_stage()!=confidence_controller.stage:raise ValueError('The open stage changed. Retry project startup to attach display controls.')
            refresh_confidence()
            if key:
                if enabled:confidence_enabled.add(key)
                else:confidence_enabled.discard(key)
            result=confidence_controller.apply(confidence_enabled) if confidence_mode['enabled'] else confidence_controller.reset()
            confidence_summary.text='Evidence display groups (paired roofs counted separately):\n'+'\n'.join(f'{label}: {result["counts"][key]}' for key,label in CONFIDENCE_CATEGORIES)
            status.text=f'Evidence filter: {result["hidden_groups"]} groups hidden temporarily. Source accuracy is not certified.'
        except Exception as error:status.text='Evidence display change failed: '+str(error)
    def confidence_master(model):
        confidence_mode['enabled']=model.as_bool;filter_confidence()
    def view(name):
        viewport=get_active_viewport()
        stage=ctx.get_stage()
        if viewport and stage and stage.GetPrimAtPath('/World/Cameras/'+name):viewport.camera_path='/World/Cameras/'+name
    def toggle(path,shown):
        try:
            if not set_session_visibility(ctx.get_stage(),path,shown):status.text='Display group is unavailable: '+path
        except Exception as error:status.text='Display change failed: '+str(error)
    def save():
        try:
            save_manual_only(ctx.get_stage(),manual)
            status.text='Manual edits saved. Display switches remain temporary.'
        except Exception as error:status.text='Manual edits were not saved: '+str(error)
    with window.frame, ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
        with ui.VStack(spacing=8,height=0):
            ui.Label('COLLEGE PARK',height=30,style={'font_size':25,'color':0xffe2d1a1})
            ui.Label('Orlando, Florida | Edgewater corridor',height=22)
            ui.Label(('Prototype 02 - Edgewater streetscape' if detailed else 'Prototype 01 - geographic base') if project_stage else 'Existing editor stage preserved',height=22)
            ui.Separator(height=4)
            if project_stage:
                ui.Label(f"{counts.get('buildingMeshes',0):,} buildings | {counts.get('roadSegments',0):,} street segments",height=24)
                if detailed:ui.Label(f"{detail_counts.get('trees','unknown')} trees | {detail_counts.get('storefrontBuildings','unknown')} detailed storefront buildings",height=24)
            else:ui.Label('TWIN dataset counts are not applied to this stage. Your existing scene has not been replaced.',height=60,word_wrap=True)
            ui.Label('Saved views',height=23,style={'font_size':18})
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/MainStreetOverview'):ui.Button('College Park Main Street',height=34,clicked_fn=lambda:view('MainStreetOverview'))
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/WellesleyReview'):ui.Button('Wellesley — seven-story evidence',height=34,clicked_fn=lambda:view('WellesleyReview'))
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/WellesleyEvidence'):ui.Button('Wellesley — seven-story evidence',height=34,clicked_fn=lambda:view('WellesleyEvidence'))
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/PrincetonEvidence'):ui.Button('Princeton — historical roof components',height=34,clicked_fn=lambda:view('PrincetonEvidence'))
            ui.Button('District overview',height=34,clicked_fn=lambda:view('DistrictOverview'))
            ui.Button('Edgewater corridor',height=34,clicked_fn=lambda:view('EdgewaterCorridor'))
            ui.Button('Close aerial view',height=34,clicked_fn=lambda:view('StreetScale'))
            if detailed:
                ui.Button('Tree-lined Edgewater',height=34,clicked_fn=lambda:view('TreeLinedEdgewater'))
                ui.Button('Storefront walk',height=34,clicked_fn=lambda:view('StorefrontWalk'))
            ui.Label('Layers',height=22,style={'font_size':18})
            layers=available_display_groups(ctx.get_stage())
            for label,path in layers:
                with ui.HStack(height=23):
                    from pxr import UsdGeom
                    model=ui.SimpleBoolModel(visible(ctx.get_stage(),path))
                    ui.CheckBox(model=model,width=24)
                    ui.Label(label)
                    model.add_value_changed_fn(lambda m,p=path:toggle(p,m.as_bool))
            ui.Button('Save manual edits',height=34,clicked_fn=save)
            ui.Label('Display switches are temporary; source layers are preserved.',height=38,word_wrap=True)
            ui.Label('Source confidence',height=23,style={'font_size':18})
            ui.Label('Labels describe evidence, not certified accuracy. Historical heights do not establish current conditions.',height=48,word_wrap=True)
            with ui.HStack(height=24):
                model=ui.SimpleBoolModel(False);ui.CheckBox(model=model,width=24);ui.Label('Filter scene by evidence category')
                model.add_value_changed_fn(confidence_master)
            for key,label in CONFIDENCE_CATEGORIES:
                with ui.HStack(height=23):
                    model=ui.SimpleBoolModel(True);ui.CheckBox(model=model,width=24);ui.Label(label)
                    model.add_value_changed_fn(lambda m,k=key:filter_confidence(k,m.as_bool))
            confidence_summary=ui.Label('Evidence display groups (paired roofs counted separately):\n'+'\n'.join(f'{label}: {confidence_counts[key]}' for key,label in CONFIDENCE_CATEGORIES),height=170,word_wrap=True)
            ui.Button('Refresh evidence labels',height=30,clicked_fn=filter_confidence)
            status=ui.Label('Ready. Select any building part to inspect its evidence.',height=340,word_wrap=True)
            ui.Label('Heights: historical LiDAR or floor estimates. Ground is flat.\nNo live traffic or sensor feeds.',height=48,word_wrap=True,style={'color':0xffa9b8cf})
            if detailed:ui.Label('Trees and storefront designs are illustrative.\nShop signs show generic categories.',height=48,word_wrap=True)
            ui.Label('Buildings: Orange County Property Appraiser\nMap: OpenStreetMap contributors (ODbL)',height=48,word_wrap=True)
            ui.Spacer(height=0)
    bridge_runtime={'remote_paths':None,'last_seen':None}
    def selection_changed(event):
        if event.type!=int(omni.usd.StageEventType.SELECTION_CHANGED):return
        stage=ctx.get_stage()
        if not stage:return
        paths=ctx.get_selection().get_selected_prim_paths()
        prim=stage.GetPrimAtPath(paths[0]) if paths else None
        refresh_confidence()
        status.text=inspector_text(prim,project_refresh if project_stage else None,evidence_registry if project_stage else None,active_snapshot if project_stage else None)
        if not project_stage or not is_project_stage(stage,[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')]):return
        if tuple(paths)==bridge_runtime['remote_paths']:return
        bridge_runtime['remote_paths']=None
        try:
            packet=bridge_state(ROOT);context=bridge_context(ROOT)
            identity=selection_identity(prim,context) if prim else {'feature_id':''}
            # A stale rendered entity must not publish against a newer snapshot.
            evidence=inherited_evidence(prim)['data'] if prim else {}
            snapshot=evidence.get('twin',{}).get('sourceSnapshot',evidence.get('official',{}).get('snapshot'))
            if prim and snapshot and snapshot!=packet['snapshot']:raise SelectionError('Selected editor evidence is stale',409)
            published=bridge_publish({'epoch':packet['epoch'],'snapshot':packet['snapshot'],'expected_revision':packet['revision'],'sender':'kit',**identity},ROOT)
            bridge_runtime['last_seen']=(published['epoch'],published['revision'])
        except (OSError,ValueError) as error:status.text+='\nSelection link: '+str(error)
    selection_subscription=ctx.get_stage_event_stream().create_subscription_to_pop(selection_changed)
    async def sync_map_selection():
        while True:
            await asyncio.sleep(1)
            if not project_stage or not is_project_stage(ctx.get_stage(),[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')]):continue
            try:
                packet=bridge_state(ROOT);key=(packet['epoch'],packet['revision'])
                if key==bridge_runtime['last_seen']:continue
                bridge_runtime['last_seen']=key
                if packet['sender']!='map':continue
                paths=counterpart_paths(ctx.get_stage(),packet,bridge_context(ROOT))
                bridge_runtime['remote_paths']=tuple(paths)
                ctx.get_selection().set_selected_prim_paths(paths,False)
                selection=packet['selection']
                if selection['status']=='matched' and not paths:
                    notice='Accepted counterparts are not loaded with matching snapshot evidence in this editor.'
                    acknowledge(packet,'unmatched-editor',notice,ROOT)
                else:
                    notice=selection['reason']
                    acknowledge(packet,'selected-in-editor' if paths else 'unmatched-editor',notice,ROOT)
                status.text='Map selection: '+notice+'\nCamera preserved.'
            except (OSError,ValueError) as error:status.text='Selection link: '+str(error)
    global selection_sync_task
    if 'selection_sync_task' in globals() and not selection_sync_task.done():selection_sync_task.cancel()
    selection_sync_task=asyncio.ensure_future(sync_map_selection())
    for _ in range(10):await app.next_update_async()
    stage_window=ui.Workspace.get_window('Stage')
    if stage_window:window.dock_in(stage_window,ui.DockPosition.SAME)
    print('COLLEGE_PARK_WORKSPACE_READY',counts)
    # Generated layers may be rebuilt outside Kit. Refresh clean generated
    # layers only; never reload the user's manual edit layer.
    watched=['retail_block.usda','wellesley_architecture.usda','landmark_buildings.usda','rear_parking_samples.usda','road_materials.usda','main_street_palms.usda','main_street_presentation.usda','college_park.usda','edgewater_details.usdc','asset_upgrade.usda','asset_upgrade_environment_v2.usda','building_heights.usda','semantic_assets.usda','official_context.usda','study_scope.usda','commercial_context.usda','landmark_corrections.usda','princeton_correction.usda','map_extent_guard.usda','college_park_connected.usda']
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
    if 'refresh_task' in globals() and not refresh_task.done():refresh_task.cancel()
    refresh_task=asyncio.ensure_future(refresh_generated())

def retry_startup():
    global startup_task
    if startup_task and not startup_task.done():return
    startup_task=asyncio.ensure_future(startup_guard())

async def startup_guard():
    try:await open_workspace()
    except Exception as error:
        global project_window
        if project_window is None:project_window=ui.Window('College Park | Project',width=360,height=300)
        with project_window.frame, ui.VStack(spacing=10):
            ui.Label('Project startup needs attention: '+str(error),height=150,word_wrap=True)
            ui.Button('Retry project startup',clicked_fn=retry_startup)
        print('COLLEGE_PARK_WORKSPACE_ERROR',str(error))

retry_startup()
