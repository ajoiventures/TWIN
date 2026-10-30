# Princeton roof reconstruction: script contract and failed visual gate

Latest finding: the new connected roof regions still conflict with the retained roof at some interfaces, by up to 3.23 m. The dated aerial helps identify terraces and pitched caps but does not resolve their historical elevations. The diagnostic scripts and conflict evidence are preserved; no replacement roof has passed acceptance or been activated.

October29,2026. Scope: improve the eastern historical roof component of Princeton at College Park, parcel292214725701000,646 W Smith Street. This is bounded work toward tickets#6/#8. It does not complete those entire tickets or certify current as-built conditions. User Kit/Rhino sessions, the connected root and existing Wellesley/retail/Rugby corrections remain untouched.

## Actual result and adopted correction

The first source-fitted proposal passed independent numerical checks but **failed the actual matched visual gate**. Its28 individually valid planes were assigned through nearest-support cells; the resulting boundaries created artificial triangular spikes, microterraces and abrupt interfaces. Source residuals and closed topology did not establish architectural correctness. The active model was not replaced.

Rejected layerSHA: `65eb74f6ffcaee3d79272569e2ea06f06b98a30f26f00adc411cb5960ef64a47`. Actual matched baseline and proposal are `data/renders/20261029T010149Z/PrincetonCoherentRoofEvidence.png` and `data/renders/20261029T010301Z/PrincetonCoherentRoofEvidence.png`. Both used the same camera, inherited lighting and identical neutral material overrides. No blur or material change excuses the shape failure.

The complete rejected builder/layer/manifest/regions/support arrays/style/matched review scenes are preserved under ignored `data/heights/princeton/rejected_65eb74f6ffcaee3d/`, with a rejection receipt and file hashes. This is an evidence bundle, not a standalone checkout: replay requires matching project-relative paths in a separate workspace with the declared cached source dependencies. Do not execute its nested builder as if its computed project root were a complete repository, and do not overwrite render inputs while captures are live.

The correction adopted for the next candidate is **connected measured face regions with analytical shared boundaries**, rather than nearest-cell plane labels. A ridge/valley relation is accepted only when actual measured3D supports are adjacent and the local source inliers independently support opposite sides of the same plane-equality line. Ambiguous relations remain unresolved original-model context. Merely taking min/max of planes is not roof evidence.

## Current2D diagnostic contract

Purpose: assess source support, coherent regions and seam continuity before another expensive3D build/render. Run from any working directory:

```powershell
python C:/Projects/TWIN/tools/princeton_roof_regions.py
```

Inputs: frozen rejected-v1 source-plane support arrays and coefficients; the current cached original historical point cloud; current Princeton correction envelope/configuration; protected courtyard core; active snapshot identity. Support/cloud checksums are validated before processing. There are no network calls, private BOOMS inputs, restricted canopy reads, aerial traces, source-image textures, installs or editor operations.

Coordinates: EPSG32617 meters. Source heights are NAVD88 meters; source acquisition2018-12-04 through2019-04-12, exact local flight/construction phase unknown. Class6 source membership and plane-fit provenance are retained. West/middle class1-only source surfaces remain semantically uncertain and are not changed or called certified roofs. Six storeys is a property maximum, never a uniform extrusion instruction.

Algorithm: contiguous inlier support clusters are separated before constructing candidate face hulls. Small/disconnected support clusters remain unresolved. Co-planar merging is attempted only against actual fit thresholds; none was accepted in the current diagnostic. Confidence clipping uses0.5m occupied source neighborhoods with one8-neighbor expansion; source-to-cell-center plus neighboring-cell-center and output-corner distances are rigorously bounded by1.414214m. This mask bounds confidence only; it does not assign different plane labels per cell. Overlapping candidate regions receive analytical shared boundaries only where the measured adjacency/halfspace test passes. The courtyard is excluded explicitly. Original source geometry and flat ground are not changed.

Outputs under ignored `data/heights/princeton/architectural_regions/`:

- `diagnostics.json`: source inputs, units/fit origin, accepted joins, ambiguous relations, source residuals, support bounds and remaining uncertainty.
- `regions.geojson` and `unresolved.geojson`: WGS84 review regions, not promoted current building footprints.
- `regions.svg` and `regions.png`: standalone2D diagnostic diagram; grey means retained unresolved original approximation. No aerial pixels.

Current result:2404.50m² of source-supported candidate regions;619.11m² unresolved original approximation;28 plane regions;10 analytically partitioned shared relations with zero analytical height jump;28 ambiguous relations. Actual assigned class6 residual median/p95 are0.0389/0.1591m; boundary-sampled support distance max1.3367m; protected-courtyard overlap0. The3.489m maximum residual remains an explicit outlier/structure disagreement, not discarded or asserted to be a particular roof detail. This is a2D diagnostic result, **not a new3D visual acceptance**.

Verification uses real frozen source supports, explicit checksums and a reviewable plane/region diagram. Remaining work is to judge these coherent-region/unknown-interface results, author a new jointly closed proposal with exact per-face provenance, and inspect another matched actual render. No further full render should precede that source/seam review.

Recovery: rerunning replaces only generated diagnostic outputs; preserve separately any manual annotations. No active composition was modified, so the failed proposal requires no active-model rollback. The frozen rejected bundle preserves the exact previous comparison. Any later geometry promotion needs its own dependency-checked activation, backup and independent actual visual approval.

[Safe diagnostic summary and rejected-gate evidence](evidence/princeton-roof-region-diagnostics.json) contains numerical provenance and hashes without raw point arrays or source imagery. The reusable lesson is limited and verified: **good individual plane fits plus closed topology do not validate a fragmented architectural partition; actual matched renders must judge the assembled roof.** The new region method is a candidate under2D review, not an already accepted solution.

## Attempted shared-shell interface gate: actual constraint

The CPU-only interface analysis did not justify another closed candidate. Run `python tools/princeton_roof_seams.py` to reproduce `architectural_regions/seams.json` and `seam_conflicts.geojson`. It compares known-to-uncertain interior boundaries only, excluding original outer/courtyard boundaries and the analytically reconciled known-known joins. It uses the old source mesh's actual triangles and the new measured planes, not a nearest-cell seam wall.

Across4421 samples the median/p95/max height disagreement is0.171/0.715/3.230m.1815 samples exceed the0.2m diagnostic trigger. Comparison against actual class6 neighbors within0.5m, evaluating both models at those measured point coordinates, classifies545 conflict samples as supporting the fitted surface,585 as preferring the original/possible true step and685 as unresolved. These are sample counts, not independent roof-feature counts or survey tolerances. The comparison uses the same historical acquisition, not an independent current survey.

The existing January2025 OCPA reference was actually viewed again. It visibly distinguishes flat white terraces, pitched grey/red caps and the courtyard pavilion. It does not supply precise historical ridge/eave coordinates or elevations and cannot by itself reconcile2018–2019 construction-phase geometry with completed2025 conditions. The local `architectural_regions/seam_reference.html` links that original local image with representative conflict markers; no imagery pixels are committed or used as a texture.

Accordingly, **no new shared-shell3D candidate was authored or activated at this gate**. Filling these interfaces mechanically would recreate the rejected fins or add unsupported transition slopes. The remaining engineering task is to interpret the measured roof breaklines/level changes at the flagged interfaces, using raw-return evidence and suitable roof-plan references where needed, then retain uncertainty explicitly. This does not prove the historical point cloud can never support a better interpretation; it records that the current connected-region interpretation does not yet resolve the interfaces safely.

[Safe interface-constraint report](evidence/princeton-roof-interface-constraints.json) records the actual numerical findings. Existing Wellesley, retail, Rugby, root/manual and user editor sessions remain unchanged. No new GPU render was launched.
