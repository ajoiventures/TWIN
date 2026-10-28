"""Run one isolated, bounded Kit probe of a fresh portable fictional sample.

Uses viewport frame-completion futures, not app-update counts. Never controls an
existing Kit process. Local SDK/cache only; no installation or acquisition.
"""
from pathlib import Path
import os,sys,json,time,argparse,datetime,tempfile,subprocess,ctypes,statistics,hashlib,shutil
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def percentile(values,q):
    values=sorted(values);position=(len(values)-1)*q;low=int(position);fraction=position-low
    return values[low]*(1-fraction)+values[min(low+1,len(values)-1)]*fraction


async def kit_probe():
    import asyncio,traceback,struct
    import omni.kit.app,omni.usd
    from omni.kit.viewport.utility import get_active_viewport,create_viewport_window,next_viewport_frame_async,capture_viewport_to_file
    config=json.loads(Path(os.environ['TWIN_SAMPLE_PROBE_CONFIG']).read_text());folder=Path(config['evidence']);app=omni.kit.app.get_app()
    started=float(config['launch_monotonic']);report={'status':'running','sample_directory':config['sample'],'resolution':[1280,720]}
    try:
        import runpy
        bootstrap=runpy.run_path(str(Path(config['sample'])/'open_sample.py'))
        await asyncio.wait_for(bootstrap['sample_startup_task'],timeout=90)
        context=omni.usd.get_context()
        if Path(context.get_stage().GetEditTarget().GetLayer().realPath)!=Path(config['sample'])/'manual.usda':raise RuntimeError('Generated bootstrap did not target manual edits')
        report['generated_bootstrap_used']=True;report['manual_edit_target_verified']=True
        report['launch_to_stage_open_seconds']=time.monotonic()-started
        viewport=get_active_viewport();window=None
        if not viewport:window=create_viewport_window('Portable sample probe',width=1280,height=720);viewport=window.viewport_api
        viewport.resolution=(1280,720);viewport.camera_path='/World/Cameras/Overview'
        for _ in range(5):await app.next_update_async()
        await asyncio.wait_for(next_viewport_frame_async(viewport),timeout=90)
        report['launch_to_first_viewport_frame_seconds']=time.monotonic()-started
        for _ in range(config['warmup_frames']):await asyncio.wait_for(next_viewport_frame_async(viewport),timeout=30)
        timings=[]
        for _ in range(config['frames']):
            start=time.perf_counter();await asyncio.wait_for(next_viewport_frame_async(viewport),timeout=30);timings.append(time.perf_counter()-start)
        report['frame_completion_intervals_ms']=[round(t*1000,6) for t in timings]
        report['timings']={'samples':len(timings),'warmup_viewport_frames':config['warmup_frames'],
            'median_ms':percentile(timings,.5)*1000,'p95_ms':percentile(timings,.95)*1000,'min_ms':min(timings)*1000,'max_ms':max(timings)*1000,
            'reciprocal_median_viewport_completions_per_second':1/percentile(timings,.5),
            'method':'Wall-clock wait intervals for actual next_viewport_frame_async futures; not app updates or GPU timestamp timings.'}
        image=folder/'sample.png';await asyncio.wait_for(capture_viewport_to_file(viewport,file_path=str(image)).wait_for_result(completion_frames=30),timeout=60)
        deadline=time.monotonic()+20;pixels=b''
        while time.monotonic()<deadline:
            if image.exists():
                pixels=image.read_bytes()
                if len(pixels)>32 and pixels[:8]==b'\x89PNG\r\n\x1a\n' and pixels[-8:-4]==b'IEND':break
            await app.next_update_async();await asyncio.sleep(.1)
        if len(pixels)<32 or pixels[-8:-4]!=b'IEND' or struct.unpack('>II',pixels[16:24])!=(1280,720):raise RuntimeError('No complete 1280x720 sample capture')
        report.update({'status':'complete','launch_to_capture_complete_seconds':time.monotonic()-started,'image':'sample.png','image_sha256':digest(image),'source_stage_saved':False})
    except Exception:report.update({'status':'failed','error':traceback.format_exc()})
    finally:
        (folder/'kit_result.json').write_text(json.dumps(report,indent=2))
        await omni.usd.get_context().close_stage_async();app.post_quit()


class DeviceMemory:
    def __init__(self):
        self.library=None;self.reason=None
        try:
            library=ctypes.WinDLL('nvml.dll');library.nvmlInit_v2.restype=ctypes.c_int
            if library.nvmlInit_v2()!=0:raise RuntimeError('NVML initialization failed')
            handle=ctypes.c_void_p()
            if library.nvmlDeviceGetHandleByIndex_v2(0,ctypes.byref(handle))!=0:raise RuntimeError('NVML device unavailable')
            self.library=library;self.handle=handle
        except Exception as error:self.reason=str(error)
    def sample(self):
        if not self.library:return None
        class Memory(ctypes.Structure):_fields_=[('total',ctypes.c_ulonglong),('free',ctypes.c_ulonglong),('used',ctypes.c_ulonglong)]
        memory=Memory()
        if self.library.nvmlDeviceGetMemoryInfo(self.handle,ctypes.byref(memory))!=0:return None
        return {'total_bytes':memory.total,'used_bytes':memory.used}
    def close(self):
        if self.library:self.library.nvmlShutdown()


def process_ram(process):
    if os.name!='nt':return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak_working_set','working_set','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    api=ctypes.WinDLL('psapi');api.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
    if not api.GetProcessMemoryInfo(wintypes.HANDLE(int(process._handle)),ctypes.byref(counters),counters.cb):return None
    return {'working_set_bytes':counters.working_set,'peak_working_set_bytes':counters.peak_working_set,'private_commit_bytes':counters.private}


def kit_processes():
    result=subprocess.run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'kit.exe' } | Select-Object ProcessId,Name | ConvertTo-Json -Compress"],capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:value=json.loads(result.stdout);return value if isinstance(value,list) else [value]
    except ValueError:return []


def run(kit_root=None,frames=120,warmup=30,timeout=180,minimal=False):
    if not 10<=frames<=600 or not 1<=warmup<=120 or not 30<=timeout<=300:raise ValueError('Probe bounds exceeded')
    configured=kit_root or os.environ.get('OMNIVERSE_KIT_ROOT')
    if not configured and (ROOT/'config/local.json').is_file():configured=json.loads((ROOT/'config/local.json').read_text()).get('kit_root')
    if not configured:raise ValueError('Pass --kit-root <SDK release directory> or set OMNIVERSE_KIT_ROOT; a clean checkout has no local SDK configuration.')
    kit_root=Path(configured).resolve()
    exe=kit_root/'kit/kit.exe'
    if not exe.is_file():raise ValueError('Configured local Kit runtime unavailable')
    sys.path.insert(0,str(ROOT/'tools'));from build_sample import build
    sample=Path(tempfile.mkdtemp(prefix='twin-sample-runtime-'));manifest=build(sample)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');folder=ROOT/'data/sample_runtime'/stamp;folder.mkdir(parents=True)
    experience=sample/'sample.kit'
    if minimal:
        experience=folder/'minimal_renderer_probe.kit'
        text=(sample/'sample.kit').read_text()
        text='\n'.join(line for line in text.splitlines() if not line.startswith(('"omni.kit.menu.file"','"omni.kit.window.stage"')))
        experience.write_text(text)
    before=kit_processes();nvml=DeviceMemory();baseline=nvml.sample()
    config={'sample':str(sample),'evidence':str(folder),'frames':frames,'warmup_frames':warmup,'launch_monotonic':time.monotonic()}
    config_path=folder/'probe_config.json';config_path.write_text(json.dumps(config,indent=2))
    command=[str(exe),str(experience),'--ext-folder',str(kit_root/'exts'),'--ext-folder',str(kit_root/'extscache'),'--no-window','--/app/renderer/skipWhileMinimized=false','--/app/window/hideUi=true','--/renderer/multiGpu/enabled=false','--/app/extensions/registryEnabled=false','--exec','"'+str(Path(__file__).resolve())+'"']
    env=os.environ.copy();env['TWIN_SAMPLE_PROBE_CONFIG']=str(config_path);samples=[];timed_out=False
    with (folder/'kit.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        deadline=time.monotonic()+timeout
        while process.poll() is None:
            samples.append({'seconds':time.monotonic()-config['launch_monotonic'],'ram':process_ram(process),'device_vram':nvml.sample()})
            if time.monotonic()>deadline:
                timed_out=True;process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
                break
            time.sleep(.2)
    nvml.close();result_path=folder/'kit_result.json';result=json.loads(result_path.read_text()) if result_path.exists() else {'status':'failed','error':'Kit did not write probe result'}
    result.update({'probe_pid':process.pid,'exit_code':process.returncode,'timed_out':timed_out,'sample_manifest':manifest,'sample_sources_unchanged':all(digest(sample/name)==value for name,value in manifest['sha256'].items()),
        'other_kit_processes_before_launch':before,'other_kit_processes_after_exit':kit_processes(),'protected_user_pid':42464,'protected_pid_was_running':any(p['ProcessId']==42464 for p in before),
        'resource_samples':samples,'device_vram_baseline':baseline,'nvml_unavailable_reason':nvml.reason,'process_vram_bytes':None,
        'peak_sampled_process_working_set_bytes':max((s['ram']['working_set_bytes'] for s in samples if s['ram']),default=None),
        'peak_sampled_device_vram_used_bytes':max((s['device_vram']['used_bytes'] for s in samples if s['device_vram']),default=None),
        'command':command,'experience':str(experience),'minimal_renderer_experience':minimal,'experience_sha256':digest(experience),'numeric_worker_threads':1,'probe_tool_sha256':digest(__file__),
        'caveats':['Small fictional portable sample only; not the College Park district or a 30 FPS acceptance benchmark.',
            'Viewport completion timings include CPU scheduling/renderer waits; no GPU timestamp or displayed-monitor frame rate was measured.',
            'Device NVML VRAM includes all processes, driver and desktop allocations; per-process VRAM was not queried.',
            'Preinstalled SDK/cache used with extension registry disabled; network isolation was not externally enforced.',
            'Existing Kit processes were inventoried, never interrupted; this headless probe owns only its newly spawned PID.']})
    (folder/'report.json').write_text(json.dumps(result,indent=2));print(str(folder/'report.json'),flush=True);return result


if __name__=='__main__':
    if os.environ.get('TWIN_SAMPLE_PROBE_CONFIG') and 'omni.kit.app' in sys.modules:
        import asyncio;asyncio.ensure_future(kit_probe())
    else:
        parser=argparse.ArgumentParser();parser.add_argument('--kit-root');parser.add_argument('--frames',type=int,default=120);parser.add_argument('--warmup',type=int,default=30);parser.add_argument('--timeout',type=int,default=180);parser.add_argument('--minimal-experience',action='store_true');args=parser.parse_args()
        result=run(args.kit_root,args.frames,args.warmup,args.timeout,args.minimal_experience)
        print(json.dumps({key:result.get(key) for key in ('status','launch_to_stage_open_seconds','launch_to_first_viewport_frame_seconds','launch_to_capture_complete_seconds','timings','peak_sampled_process_working_set_bytes','peak_sampled_device_vram_used_bytes','error')},indent=2))
