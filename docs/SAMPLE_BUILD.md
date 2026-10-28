# Portable offline demonstration

This small fictional street scene contains original generated geometry and solid-color USD Preview Surface materials: ten storefront buildings, twelve schematic trees, four cars, sidewalks, lane markings, ground, daylight and an overview camera. It demonstrates the build and layer workflow; it does not represent surveyed College Park conditions. Generated sample content is dedicated under CC0-1.0. It includes no government imagery, GIS data, third-party models or downloaded textures.

## Build requirements

Verified environment: **64-bit CPython 3.12.14, usd-core 26.11 (OpenUSD 0.26.11), Windows**. The only nonstandard build dependency is `usd-core==26.11`. The repository's existing `.dependencies` is supported; otherwise install this exact package into the Python environment before going offline. Dependency installation requires a previously obtained compatible wheel or package access; the sample builder itself never downloads anything. No Kit installation is required to generate or compose the USD.

From any working directory, run:

```powershell
python C:/Projects/TWIN/tools/build_sample.py --output C:/Temp/twin-offline-sample
```

Choose a clean directory. Existing generated filenames are protected rather than overwritten. Relative output paths are relative to the caller's current directory. Copy the entire output folder to relocate it; there are no absolute authored asset dependencies. `sample_manifest.json` records deterministic file hashes, counts, units and dependency closure.

## Open in Kit

The generated `sample.kit` targets the existing **Kit SDK 110.4.0+main.0.9cc43b76.local, Windows x86-64** configuration. Required preinstalled extensions are `omni.kit.uiapp`, `omni.hydra.rtx`, `omni.usd`, `omni.kit.viewport.window`, `omni.kit.viewport.utility`, `omni.kit.menu.file`, and `omni.kit.window.stage`, with their dependencies supplied by that SDK's local extension cache. A functioning NVIDIA RTX-capable Kit installation and compatible driver are required for this renderer. No extension versions are independently pinned by this sample; use the SDK's resolved local cache. Kit can attempt online extension resolution if the local cache is incomplete; provision the cache before an offline launch.

Use your SDK paths, for example:

```powershell
& 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/kit/kit.exe' 'C:/Temp/twin-offline-sample/sample.kit' --ext-folder 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/exts' --ext-folder 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/extscache' --exec 'C:/Temp/twin-offline-sample/open_sample.py'
```

The generated bootstrap opens `sample.usda`, selects `/World/Cameras/Overview`, sets a 1280 × 720 viewport resolution, and targets `manual.usda` for editing. The 24 mm camera has explicit 36 × 20.25 mm apertures (16:9). All corners of the world-aligned bounds of buildings, road, trees, cars, sidewalks and ground fit inside normalized device coordinates ±0.9 in both frame axes, leaving a minimum 5% image-width/height border. Alternatively open `sample.usda` in an existing USD editor, select that camera and preserve its 16:9 gate. Camera framing and positive daylight are verified from USD; an actual rendered frame has not been accepted for this sample.

## Layer ownership and verification

`sample.usda` composes strongest-to-weakest: `manual.usda`, `scenario.usda`, `base.usda`. The generated base holds geometry, materials, lights and camera. Manual and scenario layers start empty with explicit purpose metadata. Author scenario edits separately; manual edits can override them without changing the base. A sample rebuild uses a new output directory and does not merge edits.

Run `python -m unittest discover -s C:/Projects/TWIN/tests -p test_sample_build.py -v`. Checks exercise a clean command-line build from an arbitrary directory, folder relocation, local-only dependency resolution, expected geometry, complete important-geometry framing with margin in an explicit 16:9 gate, daylight, units, deterministic hashes, overwrite protection and manual/scenario composition strength.

This verifies a small portable composition, not full ticket #1 acceptance. Kit launch time, rendered image quality, RAM, VRAM and frame rate remain unmeasured. The active renderer was not interrupted or reused for benchmarking. No claim of offline first-launch success is made until the SDK cache and an actual isolated Kit launch are verified.

