# Historical campus paving delivery

October 30, 2026 · Existing #17/#18, parking P-02 and Main Street ground work.

Added a separate local model layer containing **1,873.414 m² of interpreted paving** behind College Park United Methodist and west of Church on the Drive. An additional **22.039 m²** represents eleven pale ground features visible in the dated reference. Their function is unknown; they are not labeled as planting, poles, curbs or accessible facilities.

The original January 2024/2025 aerials stay local. Pixel positions use each export's actual returned EPSG:2236 frame, then EPSG:32617 meters and the project origin. These are conservative visible surface interiors, with obscured edges retained as gaps. Image sampling resolution does not establish positional accuracy. No stalls, capacity, legal/public access or current-condition claim follows.

## What changed in the model

The additive `scene/campus_hardscape.usda` retains the reviewed C geometry, UVs and world transforms. One root sublayer was added; all other root opinions and manual, selection, snapshot, office and post-office files are unchanged. The existing editor was not reloaded or saved. Scene rebuild and native refresh retain the guarded layer.

The first proposal exposed green ground through pale-feature cutouts, falsely suggesting grass diamonds. C fills those features neutrally and reuses the project's paving texture. Its base UV divides meters by four; the inherited 4/3 transform yields an effective **3 m texture period**. Thin green collision-margin seams and larger obscured gaps remain unfinished display gaps, not observed planted strips or curbs. Whole-lot and conference realism remain unaccepted.

Independent review checked original source frames and dated images, serialized triangle area and world-space building/road/ground exclusions. Separate C delta and actual two-view inspection passed the bounded historical-surface gate. Local adoption preserves all three meshes exactly. The refreshed local scene profile checks 17,799 meshes without errors; terrain, collision, currentness and NVIDIA certification remain outside that result.

[Source review](evidence/campus-hardscape-source-review.json) · [C geometry/material/actual visual review](evidence/campus-hardscape-c-review.json) · [Adoption preservation](evidence/campus-hardscape-activation.json) · [Independent adoption audit](evidence/campus-hardscape-adoption-review.json).

## Reuse and recovery

```text
python tools/prepare_campus_hardscape.py --samples <local-json> --output data/diagnostics/<new-folder>
```

The local JSON supplies `samples`: each record has an ID, site ID matching the imagery manifest, an interpreted outer pixel ring, excluded pale-feature rings and limitations. The public producer contains no interpreted pixel-polygon list. It validates the retained image/frame/snapshot inputs, clips against world-transformed visible model geometry and flat ground, and writes a separate proposal into a new directory. Existing directories are refused. Original imagery, local interpretation inputs and generated geometry remain outside the public repository.

The accepted version is frozen in `data/diagnostics/campus_hardscape_20261030_c`; its original producer is archived by the canonical hash. New producer code does not retroactively change accepted geometry. `tools/accepted_scene_layers.py` verifies the fixed canonical recipe, reviewed source/output identity, snapshot, local-only scope, source files and manual model opinions before a rebuild. Camera-only edits under `/World/Cameras` remain compatible; other manual changes require review. Five focused guard tests pass.

Rollback removes only the campus sublayer and its local receipt/layer, preserving later user edits and the rest of the root. Do not overwrite a newer root with the archived pre-adoption file. No public derivative release is claimed; no aerial pixels or exact interpreted polygon input are published.

## Faster actual visual review

`tools/render_review.py` accepts optional `TWIN_REVIEW_CAMERAS` with one to five unique camera names. The default single-camera interface remains available. Each image has its own source/layer/snapshot/PNG proof; a batch manifest is complete only after every requested view succeeds. No source stage is saved.

The actual first two-camera batch took 151.02 seconds to the first capture and 6.59 additional seconds to the second, sharing one startup. [Independent implementation/runtime review](evidence/render-batch-review.json). This is workflow timing, not conference playback performance or a whole-ticket closure.
