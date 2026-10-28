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

The generated `sample.kit` targets the existing **Kit SDK 110.4.0+main.0.9cc43b76.local, Windows x86-64** configuration. Required preinstalled extensions are `omni.kit.uiapp`, `omni.hydra.rtx`, `omni.usd`, `omni.kit.viewport.window`, and `omni.kit.viewport.utility`, with their dependencies supplied by that SDK's local extension cache. A functioning NVIDIA RTX-capable Kit installation and compatible driver are required for this renderer. No extension versions are independently pinned by this sample; use the SDK's resolved local cache. Kit can attempt online extension resolution if the local cache is incomplete; provision the cache before an offline launch.

Use your SDK paths, for example:

```powershell
& 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/kit/kit.exe' 'C:/Temp/twin-offline-sample/sample.kit' --ext-folder 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/exts' --ext-folder 'C:/Omniverse/kit-app-template/_build/windows-x86_64/release/extscache' --exec 'C:/Temp/twin-offline-sample/open_sample.py'
```

The generated bootstrap supplies its own small edit panel for choosing manual/scenario edits, hiding or showing sample cars in that chosen layer, and saving only the selected edit layer. It opens `sample.usda`, selects `/World/Cameras/Overview`, sets a 1280 Ã— 720 viewport resolution, and targets `manual.usda` for editing. The 24 mm camera has explicit 36 Ã— 20.25 mm apertures (16:9). All corners of the world-aligned bounds of buildings, road, trees, cars, sidewalks and ground fit inside normalized device coordinates Â±0.9 in both frame axes, leaving a minimum 5% image-width/height border. Alternatively open `sample.usda` in an existing USD editor, select that camera and preserve its 16:9 gate. The isolated rendered frame below confirms useful framing and daylight for the small fictional scene; it does not establish full-project visual acceptance.

## Layer ownership and verification

`sample.usda` composes strongest-to-weakest: `manual.usda`, `scenario.usda`, `base.usda`. The generated base holds geometry, materials, lights and camera. Manual and scenario layers start empty with explicit purpose metadata. Author scenario edits separately; manual edits can override them without changing the base. A sample rebuild uses a new output directory and does not merge edits.

Run `python -m unittest discover -s C:/Projects/TWIN/tests -p test_sample_build.py -v`. Checks exercise a clean command-line build from an arbitrary directory, folder relocation, local-only dependency resolution, expected geometry, complete important-geometry framing with margin in an explicit 16:9 gate, daylight, units, deterministic hashes, overwrite protection and manual/scenario composition strength.

## Actual isolated runtime probe — October 28, 2026

`tools/probe_sample_runtime.py` builds a new temporary sample and launches its own no-window Kit process with the **unaltered generated `sample.kit` and `open_sample.py`**. It disables the extension registry, sets `skipWhileMinimized=false`, caps numerical worker threads to one, monitors only its spawned process, and captures the real 1280 × 720 viewport. It never stops or reuses an existing editor.

```powershell
python C:/Projects/TWIN/tools/probe_sample_runtime.py --frames 120 --warmup 30 --timeout 180
```

An earlier launch exposed unavailable optional `omni.kit.menu.file`/stage-window dependencies. The builder now omits those optional packages and provides its own edit panel using the available `omni.kit.uiapp` interface. The original failed receipt (`data/sample_runtime/20261028T222814Z`) and intermediate minimal-renderer receipt (`20261028T222907Z`) remain historical diagnostics. **The successful current result uses no alternate experience:** [report](../data/sample_runtime/20261028T223215Z/report.json), [rendered frame](../data/sample_runtime/20261028T223215Z/sample.png), and [Kit log](../data/sample_runtime/20261028T223215Z/kit.log).

| Measurement | Observed value |
| --- | --- |
| Launch to generated bootstrap ready / opened stage | 4.375 s |
| Launch to first viewport frame completion | 8.312 s |
| Launch to completed PNG capture | 10.656 s |
| Viewport timing sample | 120 completed frames after 30 completed warmup frames |
| Median / p95 viewport completion interval | 16.299 / 17.325 ms |
| Reciprocal median completion rate | 61.35 completions/s |
| Peak sampled probe working-set RAM | 5.132 GiB |
| Device-wide NVML VRAM baseline / peak | 0.368 / 2.446 GiB |
| Per-process VRAM | Unmeasured |

The generated bootstrap completed in Kit, its actual edit target was verified as `manual.usda`, the process exited normally, and every generated sample file retained its original hash. The captured image was visually checked for useful daylight, complete scene framing and visible road, buildings, cars and trees. Four focused tests cover portable dependency closure, framing, deterministic rebuilds, overwrite protection, manual/scenario composition strength and the supported generated experience/edit controls. The edit panel buttons have not been clicked in a live interactive acceptance pass.

Frame timings await actual `next_viewport_frame_async` completion futures, rather than counting app updates. They include CPU scheduling and renderer waits; they are not GPU timestamps, monitor presentation FPS, or a district-scene 30 FPS result. RAM and VRAM were sampled at approximately 0.2 s intervals. Device VRAM includes the desktop, driver and other applications; the difference from baseline is not a measured per-process allocation.

No other `kit.exe` process was found immediately before or after this run. Protected PID 42464 was absent at inventory time and was never controlled; the probe owned PID 18364. Other application contention was not excluded. The existing SDK and shader caches were retained, so this is not a clean-install or cold-cache benchmark. The extension registry was disabled, but network isolation was not independently enforced. No runtime packages were installed or downloaded.

This establishes a successful generated-config sample launch, bootstrap, rendering and bounded measurements on the declared SDK. Full ticket #1 acceptance still includes interactive edit/save/reopen verification; full district rendering and performance remain separate acceptance work.
