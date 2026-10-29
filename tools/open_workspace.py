"""Runs inside Omniverse Kit, leaving all scene geometry editable."""
import asyncio, json, sys, os
from pathlib import Path
import omni.kit.app
import omni.usd
import omni.ui as ui
import carb.settings
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from pxr import Gf

ROOT=Path(__file__).resolve().parents[1]
REVIEW_ONLY=os.environ.get('TWIN_REVIEW_ONLY')=='1'
sys.path.insert(0,str(ROOT/'tools'))
from workspace_evidence import inspector_text, inherited_evidence, set_session_visibility, visible, save_manual_only, available_display_groups, should_open_project, is_project_stage, registry_index, SessionConfidenceFilter, CONFIDENCE_CATEGORIES, set_session_camera, create_workspace_stage, SceneRefresh, government_preview, normalize_boundary_switches
from selection_bridge import read_state as bridge_state, publish as bridge_publish, load_context as bridge_context, selection_identity, counterpart_paths, acknowledge, SelectionError
project_window=None
startup_task=None

def checkbox_label(text,model):
    """Let the readable label toggle the same model as its small checkbox."""
    return ui.Button(text,clicked_fn=lambda: model.set_value(not model.as_bool),
                     style={'background_color':0x00000000,'border_width':0})
REFRESH_LAYERS=['final_omission_roofs.usda','retail_block.usda','wellesley_architecture.usda','landmark_buildings.usda','rear_parking_samples.usda','road_materials.usda','main_street_palms.usda','main_street_presentation.usda','college_park.usda','edgewater_details.usdc','asset_upgrade.usda','asset_upgrade_environment_v2.usda','building_heights.usda','semantic_assets.usda','official_context.usda','study_scope.usda','commercial_context.usda','landmark_corrections.usda','princeton_correction.usda','map_extent_guard.usda','college_park_connected.usda','fema_effective_hazards.usda','water_landcover_context.usda','pilot_aerial_review.usda']

async def open_workspace():
    global project_window, selection_subscription, confidence_controller, scene_refresh_controller
    if 'confidence_controller' in globals():confidence_controller.reset()
    if project_window is None:
        project_window=ui.Window('College Park | Review' if REVIEW_ONLY else 'College Park | Project',width=360,height=700)
    window=project_window
    with window.frame, ui.VStack(spacing=10):
        ui.Label('COLLEGE PARK',height=30,style={'font_size':25})
        startup_status=ui.Label('Loading project status…',height=150,word_wrap=True)
        ui.Button('Retry project startup',height=34,clicked_fn=retry_startup)
    app=omni.kit.app.get_app()
    # Kit's viewport save callback otherwise authors implicit camera metadata
    # directly on the root layer, independently of the selected edit target.
    carb.settings.get_settings().set_bool('/app/omni.usd/storeCameraSettingsToUsdStage',False)
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
            success,error=await ctx.attach_stage_async(create_workspace_stage(ROOT/'scene'/scene_name))
            if not success:raise RuntimeError(error)
            opened_new=True
        if ctx.get_stage() is None:raise RuntimeError('No editable stage is available')
        project_stage=is_project_stage(ctx.get_stage(),[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')])
    except Exception as error:
        startup_status.text='Scene could not open. '+str(error)+'\nUse Retry after restoring the local scene. Existing work is preserved.'
        return
    from pxr import Sdf,Usd
    manual=ROOT/'scene'/'manual_edits.usda'
    if REVIEW_ONLY:
        ctx.get_stage().SetEditTarget(Usd.EditTarget(ctx.get_stage().GetSessionLayer()))
    elif opened_new and manual.exists():
        manual_layer=next((layer for layer in ctx.get_stage().GetLayerStack() if layer.realPath and Path(layer.realPath).resolve()==manual.resolve()),None)
        if manual_layer:ctx.get_stage().SetEditTarget(Usd.EditTarget(manual_layer))
    if opened_new:ctx.get_selection().set_selected_prim_paths([],False)
    for _ in range(10):await app.next_update_async()
    viewport=get_active_viewport()
    if viewport and opened_new:
        for candidate in ['MainStreetOverview','WellesleyEvidence','WellesleyReview','TreeLinedEdgewater','EdgewaterCorridor']:
            if ctx.get_stage().GetPrimAtPath('/World/Cameras/'+candidate):
                set_session_camera(ctx.get_stage(),viewport,'/World/Cameras/'+candidate)
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
    previous_refresh=globals().get('scene_refresh_controller')
    scene_refresh=previous_refresh if previous_refresh and previous_refresh.stage==ctx.get_stage() else SceneRefresh(ctx.get_stage(),ROOT,REFRESH_LAYERS) if project_stage else None
    scene_refresh_controller=scene_refresh
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
        if viewport and stage:set_session_camera(stage,viewport,'/World/Cameras/'+name)
    def toggle(path,shown):
        try:
            if not set_session_visibility(ctx.get_stage(),path,shown):status.text='Display group is unavailable: '+path
        except Exception as error:status.text='Display change failed: '+str(error)
    def save():
        if REVIEW_ONLY:
            status.text='Review window: project Save is disabled. Source and manual layers are preserved.'
            return
        try:
            save_manual_only(ctx.get_stage(),manual)
            status.text='Manual edits saved. Display switches remain temporary.'
        except Exception as error:status.text='Manual edits were not saved: '+str(error)
    def refresh_scene(action):
        try:
            if not scene_refresh or ctx.get_stage()!=scene_refresh.stage:raise ValueError('Attach these controls to the current project using Retry startup')
            report=getattr(scene_refresh,action)()
            lines=[report.get('status',action),str(report.get('before_snapshot',''))+' → '+str(report.get('candidate_snapshot',''))]
            lines.extend(Path(row['path']).name+' · '+str(row['bytes'])+' bytes' for row in report.get('layers',[]))
            if report.get('recovery_receipt'):lines.append('Recovery: '+report['recovery_receipt'])
            refresh_summary.text='\n'.join(lines);refresh_summary.height=ui.Pixel(max(100,22*len(lines)))
            refresh_confidence()
            status.text=('No local scene changes to apply. Current view is unchanged.' if report.get('status')=='no_local_changes' else {'review':'Local changes reviewed. Apply replaces generated layers in memory; manual/scenario edits are retained.','apply':'Scene update applied. Rebuild layer controls to show newly added optional switches.','undo':'Previous scene view restored in memory; saved sources and API snapshot remain unchanged.','recover_latest':'Previous saved scene view recovered in memory; sources and API snapshot remain unchanged.'}[action])
        except Exception as error:status.text='Scene update not applied: '+str(error)
    def preview_government():
        global government_window
        refresh_confidence();government_window=ui.Window('Government source evidence',width=740,height=700)
        requested_window=government_window;requested_snapshot=active_snapshot
        with government_window.frame,ui.VStack():ui.Label('Checking adapter receipts and source dependencies…',word_wrap=True)
        async def populate():
            text=await asyncio.to_thread(government_preview,ROOT,requested_snapshot)
            refresh_confidence()
            if active_snapshot!=requested_snapshot:text='Snapshot changed while checking sources. Reopen this evidence preview.'
            height=20*sum(max(1,(len(line)+69)//70) for line in text.splitlines())+40
            with requested_window.frame,ui.ScrollingFrame(),ui.VStack(height=0):ui.Label(text,word_wrap=True,height=height)
        asyncio.ensure_future(populate())
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
            ui.Button('Rebuild layer controls',height=28,clicked_fn=retry_startup)
            normalize_boundary_switches(ctx.get_stage())
            layers=available_display_groups(ctx.get_stage())
            for label,path in layers:
                with ui.HStack(height=23):
                    from pxr import UsdGeom
                    model=ui.SimpleBoolModel(visible(ctx.get_stage(),path))
                    ui.CheckBox(model=model,width=24)
                    checkbox_label(label,model)
                    model.add_value_changed_fn(lambda m,p=path:toggle(p,m.as_bool))
            if not any(path in ('/World/Scenario','/World/Scenarios') for label,path in layers):
                ui.Label('Future scenarios: unavailable in this scene. Existing conditions remain visible.',height=44,word_wrap=True)
            ui.Button('Save manual edits',height=34,clicked_fn=save,enabled=not REVIEW_ONLY)
            if REVIEW_ONLY:ui.Label('Review window: session edit target; map link and project Save are disabled.',height=50,word_wrap=True)
            ui.Label('Display switches are temporary; source layers are preserved.',height=38,word_wrap=True)
            ui.Label('Source confidence',height=23,style={'font_size':18})
            ui.Label('Labels describe evidence, not certified accuracy. Historical heights do not establish current conditions.',height=48,word_wrap=True)
            with ui.HStack(height=24):
                model=ui.SimpleBoolModel(False);ui.CheckBox(model=model,width=24);checkbox_label('Filter scene by evidence category',model)
                model.add_value_changed_fn(confidence_master)
            for key,label in CONFIDENCE_CATEGORIES:
                with ui.HStack(height=23):
                    model=ui.SimpleBoolModel(True);ui.CheckBox(model=model,width=24);checkbox_label(label,model)
                    model.add_value_changed_fn(lambda m,k=key:filter_confidence(k,m.as_bool))
            confidence_summary=ui.Label('Evidence display groups (paired roofs counted separately):\n'+'\n'.join(f'{label}: {confidence_counts[key]}' for key,label in CONFIDENCE_CATEGORIES),height=170,word_wrap=True)
            ui.Button('Refresh evidence labels',height=30,clicked_fn=filter_confidence)
            ui.Button('Government schemas / first five safe rows',height=32,clicked_fn=preview_government)
            ui.Label('Local scene updates',height=23,style={'font_size':18})
            ui.Label('The data pipeline stages source snapshots. These controls adopt completed local layers without downloading or saving source geometry.',height=58,word_wrap=True)
            ui.Button('Review local scene updates',height=30,clicked_fn=lambda:refresh_scene('review'))
            ui.Button('Apply reviewed scene update',height=30,clicked_fn=lambda:refresh_scene('apply'))
            ui.Button('Undo last scene refresh',height=30,clicked_fn=lambda:refresh_scene('undo'))
            ui.Button('Recover previous saved scene view',height=30,clicked_fn=lambda:refresh_scene('recover_latest'))
            refresh_summary=ui.Label('No scene refresh reviewed. Manual and scenario layers are excluded.',height=140,word_wrap=True)
            status=ui.Label('Ready. Select any building part to inspect its evidence.',height=80,word_wrap=True)
            inspector=ui.Label('Select a building part to inspect source, dates and evidence quality.',height=660,word_wrap=True)
            ui.Label('Heights: historical LiDAR or floor estimates. Ground is flat.\nNo live traffic or sensor feeds.',height=48,word_wrap=True,style={'color':0xffa9b8cf})
            if detailed:ui.Label('Trees and storefront designs are illustrative.\nShop signs show generic categories.',height=48,word_wrap=True)
            ui.Label('Buildings: Orange County Property Appraiser\nMap: OpenStreetMap contributors (ODbL)',height=48,word_wrap=True)
            ui.Spacer(height=0)
    bridge_runtime={'remote_paths':None,'last_seen':None}
    def update_inspector(prim):
        text=inspector_text(prim,project_refresh if project_stage else None,evidence_registry if project_stage else None,active_snapshot if project_stage else None)
        inspector.text=text;inspector.height=ui.Pixel(20*sum(max(1,(len(line)+39)//40) for line in text.splitlines())+30)
    def selection_changed(event):
        if event.type!=int(omni.usd.StageEventType.SELECTION_CHANGED):return
        stage=ctx.get_stage()
        if not stage:return
        paths=ctx.get_selection().get_selected_prim_paths()
        prim=stage.GetPrimAtPath(paths[0]) if paths else None
        refresh_confidence()
        update_inspector(prim)
        if REVIEW_ONLY or not project_stage or not is_project_stage(stage,[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')]):return
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
            if REVIEW_ONLY or not project_stage or not is_project_stage(ctx.get_stage(),[ROOT/'scene'/name for name in ('college_park_connected.usda','college_park_realistic.usda','college_park.usda')]):continue
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
                refresh_confidence()
                update_inspector(ctx.get_stage().GetPrimAtPath(paths[0]) if paths else None)
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
    watched=REFRESH_LAYERS
    stamps={name:(ROOT/'scene'/name).stat().st_mtime_ns for name in watched if (ROOT/'scene'/name).exists()}
    async def refresh_generated():
        while True:
            await asyncio.sleep(2)
            for name in watched:
                path=ROOT/'scene'/name
                if not path.exists():continue
                stamp=path.stat().st_mtime_ns
                if stamps.get(name)==stamp:continue
                stamps[name]=stamp
                status.text='Completed local scene files changed. Review local scene updates before applying; current view and manual edits are preserved.'
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
