"""Run with Kit --no-window --exec to capture the actual composed scene.

Writes an original render and provenance under ignored data/renders; never saves
or modifies the source stage or a running user's editor session.
"""
from pathlib import Path
import asyncio,datetime,hashlib,json,os,time,traceback,struct
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import get_active_viewport,create_viewport_window,capture_viewport_to_file,next_viewport_frame_async

ROOT=Path(__file__).resolve().parents[1]
TOOL_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

async def capture():
    app=omni.kit.app.get_app();started=time.monotonic();folder=None
    try:
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        folder=ROOT/'data/renders'/stamp;folder.mkdir(parents=True)
        cameras=[v.strip() for v in os.environ.get('TWIN_REVIEW_CAMERAS',os.environ.get('TWIN_REVIEW_CAMERA','MainStreetOverview')).split(',')]
        if not 1<=len(cameras)<=5 or len(set(cameras))!=len(cameras) or any(not c.replace('_','').isalnum() for c in cameras):raise ValueError('Use one to five unique valid camera names')
        active_path=ROOT/'data/processed/active.json';active_bytes=active_path.read_bytes();active=json.loads(active_bytes)
        scene_name=os.environ.get('TWIN_REVIEW_SCENE','college_park_connected.usda')
        if Path(scene_name).name!=scene_name or not scene_name.endswith('.usda'):raise ValueError('Review scene must name one local USD layer')
        scene=ROOT/'scene'/scene_name
        ctx=omni.usd.get_context()
        proposal=os.environ.get('TWIN_REVIEW_PROPOSAL','')
        candidate=None
        if proposal:
            if Path(proposal).name!=proposal or not proposal.endswith('.usda'):raise ValueError('Proposal must name one local USD layer')
            candidate=ROOT/'scene'/proposal
            if not candidate.exists():raise ValueError('Proposal layer is missing')
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        from workspace_evidence import create_review_stage
        # Compose proposals and stage metadata before viewport attachment.
        stage=create_review_stage(scene,candidate)
        success,error=await ctx.attach_stage_async(stage)
        if not success:raise RuntimeError(error)
        paths={}
        from pxr import UsdGeom
        for camera in cameras:
            path='/World/Cameras/'+camera
            if not ctx.get_stage().GetPrimAtPath(path) and ctx.get_stage().GetPrimAtPath('/World/'+camera):path='/World/'+camera
            if not ctx.get_stage().GetPrimAtPath(path).IsA(UsdGeom.Camera):raise ValueError('Missing review camera: '+path)
            paths[camera]=path
        viewport=get_active_viewport();window=None
        if not viewport:
            window=create_viewport_window('Review capture',width=1920,height=1080)
            viewport=window.viewport_api
        layers={str(Path(layer.realPath).relative_to(ROOT)).replace('\\','/'):hashlib.sha256(Path(layer.realPath).read_bytes()).hexdigest() for layer in ctx.get_stage().GetUsedLayers() if layer.realPath and Path(layer.realPath).is_relative_to(ROOT)}
        reports=[]
        for camera,path in paths.items():
            viewport.resolution=(1920,1080);viewport.camera_path=path
            for _ in range(120):await app.next_update_async()
            await next_viewport_frame_async(viewport)
            image=folder/(camera+'.png')
            result=await asyncio.wait_for(capture_viewport_to_file(viewport,file_path=str(image)).wait_for_result(completion_frames=60),timeout=90)
            # Kit builds differ in their callback return value. Verify the actual
            # completed PNG rather than treating a None callback as missing output.
            pixels=b''
            file_deadline=time.monotonic()+20
            while time.monotonic()<file_deadline:
                if image.exists():
                    pixels=image.read_bytes()
                    if len(pixels)>32 and pixels[:8]==b'\x89PNG\r\n\x1a\n' and pixels[-8:-4]==b'IEND':break
                await app.next_update_async()
                await asyncio.sleep(.1)
            if len(pixels)<32 or pixels[:8]!=b'\x89PNG\r\n\x1a\n' or pixels[-8:-4]!=b'IEND':raise RuntimeError('Render capture did not produce a complete PNG')
            if struct.unpack('>II',pixels[16:24])!=(1920,1080):raise RuntimeError('Unexpected render dimensions')
            if any(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest for relative,digest in layers.items()):raise RuntimeError('Scene source changed during capture; image is not an accepted comparison')
            if active_path.read_bytes()!=active_bytes:raise RuntimeError('Active snapshot changed during capture')
            report={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'camera':path,'proposal_layer':proposal or None,'requested_resolution':[1920,1080],'scene':str(scene.relative_to(ROOT)),'scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),'layer_hashes':layers,'image':str(image.relative_to(ROOT)),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'elapsed_seconds':round(time.monotonic()-started,2),'quality':'Actual Kit render for visual inspection; not visual sign-off or a performance benchmark','source_stage_saved':False}
            from pxr import UsdGeom
            report['render_stage']={'up_axis':str(UsdGeom.GetStageUpAxis(ctx.get_stage())),
                'meters_per_unit':UsdGeom.GetStageMetersPerUnit(ctx.get_stage()),
                'root_mode':'transient_precomposed','capture_tool_sha256':TOOL_SHA256}
            (folder/('manifest.json' if len(cameras)==1 else camera+'.manifest.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
            reports.append(report)
            print('TWIN_RENDER_CAPTURE_READY',str(image),flush=True)
        if len(cameras)>1:
            (folder/'manifest.json').write_text(json.dumps({'schema':'twin.render-review-batch/1','captures':reports,'complete':len(reports)==len(cameras),'source_stage_saved':False},indent=2),encoding='utf-8')
            print('TWIN_RENDER_BATCH_READY',str(folder/'manifest.json'),flush=True)
    except Exception:
        error=traceback.format_exc();print('TWIN_RENDER_CAPTURE_FAILED',error,flush=True)
        if folder:(folder/'error.txt').write_text(error,encoding='utf-8')
    finally:
        await omni.usd.get_context().close_stage_async()
        app.post_quit()

asyncio.ensure_future(capture())
