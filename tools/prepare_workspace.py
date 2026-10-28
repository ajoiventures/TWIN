from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
base=Path('C:/Omniverse/kit-app-template/_build/windows-x86_64/release')
text=(base/'apps'/'college_park_twin.kit').read_text()
text=text.replace('"college_park_twin_extension" = { order = 1000 }','''"omni.kit.menu.file" = {}
"omni.kit.menu.edit" = {}
"omni.kit.menu.create" = {}
"omni.kit.window.stage" = {}
"omni.kit.property.bundle" = {}
"omni.kit.window.property" = {}
"omni.kit.manipulator.prim" = {}
"omni.kit.window.toolbar" = {}
"omni.kit.viewport.menubar.camera" = {}
"omni.kit.viewport.menubar.display" = {}
"omni.kit.viewport.menubar.lighting" = {}''')
text=text.replace('"${app}/../exts"','"'+str(base/'exts').replace('\\','/')+'"').replace('"${app}/../extscache/"','"'+str(base/'extscache').replace('\\','/')+'"')
text=text.replace('name = "college_park_twin"','name = "college_park_workspace"')
text=text.replace('title = "college_park_twin"','title = "College Park Digital Twin | Orlando"')
if (root/'scene'/'college_park_realistic.usda').exists():text=text.replace('title = "College Park Digital Twin | Orlando"','title = "College Park Digital Twin | Edgewater 02"')
text=text.replace('ignoreUnsavedOnExit = true','ignoreUnsavedOnExit = false')
text=text.replace('renderer.resolution.width = 1920','renderer.resolution.width = 0').replace('renderer.resolution.height = 1080','renderer.resolution.height = 0')
text=text.replace('renderer.multiGpu.enabled = true','renderer.multiGpu.enabled = false')
text=text.replace('fillViewport = true','fillViewport = true')
(root/'college_park_workspace.kit').write_text(text)
# A path without spaces also avoids Kit's --exec argument splitting on Windows.
boot=Path('C:/Omniverse/college_park_boot.py')
boot.write_text("import runpy\nrunpy.run_path("+repr(str(root/'tools'/'open_workspace.py'))+")\n")
launcher=f'''@echo off
"{base / 'kit' / 'kit.exe'}" "%~dp0college_park_workspace.kit" --exec "{boot}"
'''
(root/'Open College Park.bat').write_text(launcher)
print('Prepared workspace and launcher')
