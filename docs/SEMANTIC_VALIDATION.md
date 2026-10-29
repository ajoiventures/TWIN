# Semantic registry and scene inspection

The local `college-park-evidence-visualization/1.0` profile supports #26 without claiming NVIDIA certification or physical/survey accuracy.

`tools/semantic_registry.py` derives building-group identity from sorted original OCPA footprint object IDs, independent of list order and local mesh numbering. A membership change creates a new group identity. Parcels remain separate one-to-many relationships; spatial-only associations stay unaccepted. Records retain snapshot, source-file hash, height method, current-validity unknowns, historical acquisition interval where applicable and evidence references. Existing tree/car assets remain illustrative and are not given false official identity.

`tools/connect_scene.py` composes the additive semantic layer under manual edits. `tools/validate_scene.py` reads the final assembly, checks exact registry coverage, source/evidence hashes, active snapshot, identity/profile metadata, meter/Z-up conventions, finite mesh points, topology indices, building-height agreement and unresolved references. Instance proxies are included. It does not author repairs into sources.

Generated outputs stay local in `data/processed/asset_registry.json`, `asset_registry_quality.json`, `scene_validation.json` and `scene/semantic_assets.usda`. API routes `/api/v1/assets`, `/api/v1/asset_quality`, `/api/v1/scene_validation` expose these artifacts. Asset and height routes reject a mismatched active snapshot with HTTP 409. Building responses include entity/evidence IDs when current registry evidence exists.

Run `python tools/semantic_registry.py`, `python tools/connect_scene.py`, `python tools/validate_scene.py`. Re-run after snapshot or height changes. Source files and manual edits remain separate; a validator pass does not imply they are all correct or reviewed.

At the original checkpoint, #26 still needed NVIDIA library evaluation, runtime/profile pinning, actual visual preflight and independent acceptance. The isolated evaluation below advances those requirements; it does not update the working SDK or close the remaining acceptance gates.

## Isolated NVIDIA library evaluation — October 29, 2026

`tools/inspect_asset_contract.py` now prepares a single registered building in a new directory below `data/diagnostics`, preserving composed world transforms, stable entity identity and material binding. It checks active snapshot and registry source hashes, finite world geometry, meter/Z-up scale, building extent, material surface resolution and missing references. Source hashes are checked again after preparation. The copied source is separate from `contract.usda`, which adds `SemanticsLabelsAPI:cityscapes = building` and task evidence without changing the registry or active scene. Publication/overwrite into source paths is refused. Rollback is retaining/removing the isolated experiment; nothing is activated.

The selected city task is **source-inspection visualization**, with NVIDIA's `Open-Taxonomy-Cityscapes` profile `0.1.0` used as a bounded interoperability experiment. Collision and traversability are explicitly inapplicable to that viewing task, and remain **unverified for navigation, vehicles, pedestrians and physics**. The coordinate origin is copied from the current EPSG:32617 registry frame and world bounds are preserved; this is not independent survey control. Whole-city simulation cannot inherit this pilot's result.

The actual evaluation used a separate Python 3.12.14 Windows venv, `simready-validate==2026.8.0` and `simready-foundation-tier-core==2026.8.0` (both wheel metadata declare Apache-2.0). Their transitive packages and SHA256 wheel hashes are pinned in [requirements-simready-validation.lock](../tools/requirements-simready-validation.lock). No working editor, Kit extension, `.dependencies` package or GPU setting changed. The [official installation guide](https://nvidia.github.io/simready-foundation/2026.08.0/guides/foundation_pypi.html) and [validation workflow](https://nvidia.github.io/simready-foundation/2026.08.0/guides/validate_workflow.html) explain tier discovery and isolation. No downloaded sample assets are used, and third-party dependency licenses remain their own.

The unadapted pilot first failed missing NVIDIA semantic labels and packaging metadata. After adding those only in the isolated contract/package, Building_0665 passed all three selected features: Core, Semantic Labels and Cityscapes Labels. [Actual validator output](evidence/simready-cityscapes-pilot-result.json) and [environment, hash and preservation receipt](evidence/simready-library-pilot.json) record the result. One final CPU validation invocation took approximately 1.178 seconds including process launch. RAM/VRAM were not measured; this is not a rendering, physics or district performance benchmark. USD flattening warned about unsupported Kit UI-only metadata; geometry/material/transform preservation is checked, not every editor-only field.

Reproduce with a new experiment path (the existing one is intentionally not overwritten):

```powershell
python -m venv data/diagnostics/simready_2026_8_0/venv
data/diagnostics/simready_2026_8_0/venv/Scripts/python.exe -m pip install --require-hashes -r tools/requirements-simready-validation.lock
python tools/inspect_asset_contract.py --output data/diagnostics/my_asset_contract
data/diagnostics/simready_2026_8_0/venv/Scripts/simready-validate.exe --profile Open-Taxonomy-Cityscapes --version 0.1.0 --output data/diagnostics/my_asset_contract/nvidia_validation.json data/diagnostics/my_asset_contract/city_building/usd/city_building.usda
```

Use the repository's configured Python for preparation (it needs existing `.dependencies`). Do not pass `--stamp-asset-validation` against original assets. A profile pass is a machine-check result, **not NVIDIA certification**. No blanket physics profile was selected to manufacture a pass.

### Actual exact-candidate preflight and remaining scope

The exact validated `26e` asset was rendered through a separate review wrapper. The first image clipped its lower edge; only the external camera focal length changed from 35 to 25 mm. The final [actual PNG](evidence/simready-pilot-preflight.png) and [capture manifest](evidence/simready-pilot-preflight.json) fully frame the asset. The integrator independently inspected this image and confirmed all three candidate file hashes still match the earlier NVIDIA validation. No obvious tearing, missing face or material fallback is visible in this view. This accepts a **plain source-mass preflight only**, not façade detail, architectural realism, current physical form or district readiness. The headless capture process terminated normally; the editor and source stage were not saved.

The current helper additionally resolves retained footprint request receipts by exact source object IDs, with their actual original retrieval times, receipt hash and evidence references. Uncovered legacy source IDs remain explicit unknowns; neither snapshot build time nor manifest creation time substitutes for retrieval or acquisition. The curated handoff records the actual registry `valid_time` and `acquisition_interval` fields. **The immutable validated/rendered26e contract still has its original placeholder retrieval text**; the improved helper does not retroactively alter it, and a future candidate needs its own validation/render evidence.

#26 stays open: the demonstrated task is one source-inspection building, not full district planning/operations. Whole-project semantics/material/scale/origin coverage, required collision/traversability, downstream API/scene cross-checks, broader independent acceptance and open #3/#6/#12 dependencies remain. RAM/VRAM and installed-disk footprint were not measured; the receipt explicitly retains those technology-gate gaps. No runtime/library upgrade was applied to the working editor.
