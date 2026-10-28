"""Run with Kit --no-window --exec to capture the actual composed scene.

Writes an original render and provenance under ignored data/renders; never saves
or modifies the source stage or a running user's editor session.
"""
from pathlib import Path
import asyncio,datetime,hashlib,json,os,time,traceback
import omni.kit.app
import omni.usd
from omni.kit.viewport.utility import get_active_viewport,create_viewport_window,capture_viewport_to_file,next_viewport_frame_async

ROOT=Path(__file__).resolve().parents[1]

async def capture():
    app=omni.kit.app.get_app();started=time.monotonic();folder=None
    try:
        stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        folder=ROOT/'data/renders'/stamp;folder.mkdir(parents=True)
        camera=os.environ.get('TWIN_REVIEW_CAMERA','MainStreetOverview')
        if not camera.replace('_','').isalnum():raise ValueError('Invalid camera name')
        scene=ROOT/'scene/college_park_connected.usda'
        ctx=omni.usd.get_context();success,error=await ctx.open_stage_async(str(scene))
        if not success:raise RuntimeError(error)
        proposal=os.environ.get('TWIN_REVIEW_PROPOSAL','')
        if proposal:
            if Path(proposal).name!=proposal or not proposal.endswith('.usda'):raise ValueError('Proposal must name one local USD layer')
            candidate=ROOT/'scene'/proposal
            if not candidate.exists():raise ValueError('Proposal layer is missing')
            ctx.get_stage().GetSessionLayer().subLayerPaths=[str(candidate)]
        path='/World/Cameras/'+camera
        if not ctx.get_stage().GetPrimAtPath(path):raise ValueError('Missing review camera: '+path)
        viewport=get_active_viewport();window=None
        if not viewport:
            window=create_viewport_window('Review capture',width=1920,height=1080)
            viewport=window.viewport_api
        layers={str(Path(layer.realPath).relative_to(ROOT)).replace('\\','/'):hashlib.sha256(Path(layer.realPath).read_bytes()).hexdigest() for layer in ctx.get_stage().GetUsedLayers() if layer.realPath and Path(layer.realPath).is_relative_to(ROOT)}
        viewport.resolution=(1920,1080);viewport.camera_path=path
        for _ in range(120):await app.next_update_async()
        await next_viewport_frame_async(viewport)
        image=folder/(camera+'.png')
        result=await asyncio.wait_for(capture_viewport_to_file(viewport,file_path=str(image)).wait_for_result(completion_frames=60),timeout=90)
        if not result or not image.exists():raise RuntimeError('Render capture did not produce a file')
        if any(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest for relative,digest in layers.items()):raise RuntimeError('Scene source changed during capture; image is not an accepted comparison')
        active=json.loads((ROOT/'data/processed/active.json').read_text(encoding='utf-8'))
        report={'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':active['snapshot'],'camera':path,'proposal_layer':proposal or None,'requested_resolution':[1920,1080],'scene':str(scene.relative_to(ROOT)),'scene_sha256':hashlib.sha256(scene.read_bytes()).hexdigest(),'layer_hashes':layers,'image':str(image.relative_to(ROOT)),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'elapsed_seconds':round(time.monotonic()-started,2),'quality':'Actual Kit render for visual inspection; not visual sign-off or a performance benchmark','source_stage_saved':False}
        (folder/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('TWIN_RENDER_CAPTURE_READY',str(image),flush=True)
    except Exception:
        error=traceback.format_exc();print('TWIN_RENDER_CAPTURE_FAILED',error,flush=True)
        if folder:(folder/'error.txt').write_text(error,encoding='utf-8')
    finally:
        await omni.usd.get_context().close_stage_async()
        app.post_quit()

asyncio.ensure_future(capture())
