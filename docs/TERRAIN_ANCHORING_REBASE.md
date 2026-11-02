# Terrain anchoring: current cached-data rebase

Read-only #6 analysis completed November 2, 2026. **Original DEM availability is not the remaining global anchoring blocker.** This work does not activate terrain, move an object, change an API/editor, or accept current/surveyed geometry. Source/analysis authorship is separate from the next independent review.

## Exact findings

The old proposal contains 4,781 building/road candidates and 307 skips, with five recorded dependencies now changed. A fresh analysis of the current composed scene, including the accepted historical church and southeast wing, reuses the six original receipt-verified TIFF/XML pairs. All 24,000,000 source pixels are valid in the cached 4,000 × 6,000 grid. Horizontal EPSG:6438 and vertical NAVD88 US survey feet are preserved; the existing GroundSampler converts source feet to meters once and subtracts its 30 m NAVD88 scene origin.

| Case | Actual current evidence | Meaning |
|---|---|---|
|3,203 visible legacy building groups; 1,873 road surfaces|All sampleable using the full cached source grid|Elevation availability, not approved anchoring/clearances|
|257 old NoData/outside-raster cases|Sampleable using original cached tiles beyond the masked extraction lookup|Deliberate lookup masking/grid extent caused the old support failure; no new source download needed|
|20 old water screens|2 buildings + 18 roads intersect conservative hulls; none intersects the actual current source-water polygon projection|Replace false hull screens with exact geometry review; **not permission to declare shoreline/wetland/clearance issues resolved**|
|18 explicit bridge/tunnel/layer cases|Grade-separation tags preserved|Need specific deck/clearance handling; do not force ground draping|
|1,855 other roads|No explicit bridge=no evidence|Grade remains unverified; not automatically accepted at grade|
|12 old whole categories|Never anchored by the original helper|Raster data alone cannot complete the scene|
|505 tree instance positions|All sampleable|Prototype pivot/trunk contact and arrays still require preservation checks|

There are 764 multipart source building groups. Sampled convex-hull vertex relief exceeds 0.5 m for 305 groups, 1 m for 36 and 2 m for 3. This is a diagnostic of the current rigid anchoring approach, not a full footprint/foundation survey. A representative hull point can lie in a courtyard or between separate structures. Large relief cannot be solved by quietly stretching a measured roof.

## Historical parts must inherit the correct frame

Eleven historical/appearance families are inventoried. Naively treating each mesh's lowest Z as ground would lower the church steeple about 14.15 m, its belfry 11.14 m, and office cornice detail 7.57 m. Those are concrete counterexamples to independent per-mesh base sampling. Facades, towers, cornices and roofs must follow the corresponding building anchor, retaining their relative geometry. The FinalOmissions container must be split into its separate Rugby sites rather than shifted as one building.

Where original reconstructions record source ground/origin, distinguish conversion from an absolute historical NAVD88 frame from relative-height/base anchoring. Do not apply both translations. Source ground can differ between project components, and display offsets remain display offsets. Original roofs/height values, uncertainty, raw parcel links and existing entity identity must survive any new anchor layer.

## Next concrete implementation

`handling_decisions.json` assigns each of the 307 old cases a disposition/action and records family-specific operations. The required output is one **inactive coordinated anchor overlay**, using existing helpers and source data:

1. Use full cached bilinear support while meshing only the accepted model extent. Replace old flat ground and reshape its material/hardscape masks together; do not simply place terrain over the flat source ground. Full tile lookup does not expand the accepted scene extent.
2. Define anchor units from actual connected building footprints, accepted corrections, retained source fragments and dependent appearance. Preserve relative roofs; handle relief/base intersections explicitly.
3. Reuse `tessellated_drape` for flat road polygons and their related markings/curb/sidewalk/driveway families with common interpolation and preserved outlines/holes. Keep bridge-specific deck handling and unknown grades explicit. Historical 0.762 m DEM sampling cannot certify curb/ADA profiles.
4. Anchor tree instancer positions while preserving IDs/prototypes/scales/orientations; validate prototype base and vehicle wheel/furniture contact. Do not translate shared prototypes or every component mesh separately.
5. Treat physical lake levels horizontally with datum/shore context. Drape cartographic boundaries/thematics with display offsets while preserving original source XY/default visibility and avoiding flood-depth claims. Refresh selection/highlight geometry against the anchored composition.
6. Extend source validation carefully: a terrain anchor changes world transforms and would correctly trip current original-source fingerprints. Only a strictly validated canonical anchor layer may be muted during ORIGINAL source checks; arbitrary layer muting or relaxed hashes is not an acceptable workaround.

Independent source/preservation review, actual contacts/seams and visual evidence remain prerequisites to activation. Existing sidewalk, road shape, shoreline and parking evidence gaps remain even after terrain sampling succeeds.

## Reproduce and inspect

New exclusive helper: `tools/analyze_terrain_anchoring.py`. It imports the existing source readers, GroundSampler, rigid sampling and bridge policy but never calls their USD/source writers. It only writes a fresh ignored diagnostic folder, refuses an existing/non-diagnostic destination, verifies source receipts and all recorded dependencies before/after computation, and uses no network.

```text
python tools/analyze_terrain_anchoring.py --output data/diagnostics/NEW_FRESH_FOLDER
```

Stable local evidence is `data/diagnostics/terrain_rebase_20261102_d/`: report.json (per-group/per-road diagnostics and full scope inventory), old_skip_rebase.csv, handling_decisions.json and README.md. Structural inventory includes hidden/prototype contents and is not a physical object census. Public [compact evidence](evidence/terrain-anchoring-rebase-summary.json) contains only aggregate metrics/hashes, not raw geometry/private coordinates. All quantities describe this source snapshot; no whole-ticket completion, surveyed accuracy or new current-condition claim is made.


Dependency follow-up: original report C remains unchanged. Fresh D additionally binds the consumed OSM grade-tag JSON and all twelve original TIFF/XML receipt files, rechecks every dependency after computation, and archives the exact helper bytes. Counts and source interpretations are unchanged. This repairs the reproducibility contract; it does not add an activation or accuracy claim.
