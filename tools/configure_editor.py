"""Generate an independent editor using a configured Kit SDK release directory."""
from pathlib import Path
import os,argparse,json
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--kit-root',default=os.getenv('OMNIVERSE_KIT_ROOT'));a=p.parse_args();local=root/'config/local.json';config=json.loads(local.read_text(encoding='utf-8')) if local.exists() else {};value=a.kit_root or config.get('kit_root')
if not value:raise SystemExit('Set OMNIVERSE_KIT_ROOT or pass --kit-root with the Kit SDK release folder.')
base=Path(value).resolve();exe=base/'kit/kit.exe'
if not exe.exists():raise SystemExit('Kit executable not found: '+str(exe))
deps=['omni.kit.uiapp','omni.hydra.rtx','omni.kit.viewport.window','omni.kit.viewport.utility','omni.kit.manipulator.camera','omni.kit.manipulator.selection','omni.kit.manipulator.prim','omni.kit.menu.file','omni.kit.menu.edit','omni.kit.menu.create','omni.kit.window.stage','omni.kit.window.property','omni.kit.property.bundle','omni.kit.window.toolbar','omni.kit.viewport.menubar.camera','omni.kit.viewport.menubar.display','omni.kit.viewport.menubar.lighting']
text='[package]\ntitle="TWIN College Park"\nversion="0.4.0"\n[dependencies]\n'+'\n'.join('"'+d+'"={}' for d in deps)
text+='\n[settings.app]\nname="twin_college_park"\ncontent.emptyStageOnStart=true\nfastShutdown=true\n[settings.app.window]\ntitle="TWIN | College Park | Main Street verified model"\nwidth=1600\nheight=1000\n[settings.app.exts]\nfolders.\'++\'='+json.dumps([str(base/'exts').replace('\\','/'),str(base/'extscache').replace('\\','/')])+'\n[settings]\nrenderer.enabled="rtx"\nrenderer.multiGpu.enabled=false\n[settings.app.file]\nignoreUnsavedOnExit=false\n'
(root/'college_park_workspace.kit').write_text(text);boot=root/'tools/kit_bootstrap.py';boot.write_text('import runpy\nrunpy.run_path('+repr(str(root/'tools/open_workspace.py'))+')\n');(root/'Open College Park.bat').write_text('@echo off\npushd "%~dp0"\n"'+str(exe)+'" college_park_workspace.kit --exec tools/kit_bootstrap.py\npopd\n');local.parent.mkdir(exist_ok=True);local.write_text(json.dumps({'kit_root':str(base)},indent=2));print('Configured independent editor in',root)
