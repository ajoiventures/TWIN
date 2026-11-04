# Coordinated terrain candidate — November 2, 2026

**Inactive; not approved for adoption.** The first combined terrain, building and surface candidate has been built and reviewed in five actual matched views. It preserves source identities and building shapes, but visible frontage gaps, hardscape seams and unresolved grade/extent cases remain. These outputs advance #6, #11 and #13; they do not close those tickets or certify current conditions.

## What was built

The building helper replaces terrain only within the existing 5,270,060 m² Ground projection. Its 286,902 explicit triangles share one serialized height field with the surface helper. The full cached DEM remains the sampling source; the rendered extent does not expand to cover the tile mosaic. Ground retains its original 10 m texture scale. The overlapping inner flat Context is removed, while its outer 6,762,000 m² remains a clearly held schematic fallback with unresolved edge seams.

Building/roof components move rigidly, retaining measured roof shapes and source uncertainty. Historical roof assemblies use their recorded NAVD88 frame conversion once; towers, cornices, façades and storefronts inherit the correct family anchor. Disconnected source components receive separate anchors where source-face membership permits. The final building candidate F records 6,350 applied and 238 held path dispositions, not physical-building counts. Independent full-array checks cover 11,357 composed meshes: no XY or linear-transform changes; topology, normals, UVs, original custom data and material relationships preserved.

Surface candidate C clips original faces to the final ground triangles, retaining source outlines, holes, vertical offsets and affine UV mapping. It includes 1,727 road/shoulder/centerline meshes, 403 visible tree instances, 61 cars, 50 furniture families and eight park/parking/campus meshes. Point-instancer changes affect positions only; IDs, prototype indices, scales, orientations, visibility masks and prototype geometry remain unchanged. All 111 rigid asset transforms preserve original operation values, order and reset behavior. Independent checks of 23,184 surface centroids agree with the final ground field within 0.00001 m. These numerical contact checks do not establish road, sidewalk, parking or tree-location accuracy.

The combined audit accounts for 21,245 visible boundable entries, including instance geometry, with no unaccounted path, changed original identity or changed material binding. The 453 held disposition rows remain explicit. Accounting for geometry is not acceptance of its physical placement.

## Actual image review and blockers

Baseline: ignored `data/renders/20261102T192957Z/`. Candidate: ignored `data/renders/20261102T193840Z/`. Each contains five 1920×1080 captures and manifests:

1. DistrictOverview.
2. PrincetonEvidence.
3. TerrainEdgewaterNorth.
4. TerrainEdgewaterSouth.
5. ChurchSoutheastWingContinuousRoof.

Camera attributes and world transforms match between each pair. The two new road-oriented cameras are isolated review cameras, not saved changes to the user's working view. Every capture verifies its actual delivered camera matrix, rather than trusting its filename or requested camera path. Original scene, manual edits, active snapshot, running editor and original API remain unchanged.

[Independent source, composition and five-view review](evidence/terrain-coordinated-candidate-review.json) accepts bounded inactive progress and rejects activation. Roof shapes and object relationships remain coherent. Southbound frontage shows open black base gaps; church hardscape has stepped/cracked junctions. The Princeton roof corrugation appears before and after and remains a separate existing architectural defect.

Required corrections:

- Resolve 806 flagged building contact rows across 772 paths. The 0.3 m trigger is a project review threshold, not a survey or engineering standard. Estimated below-body closures must be distinguished from measured foundations and must preserve roof/body geometry.
- Align hardscape masks and paving tie edges deterministically. Matching a terrain interpolant does not guarantee an acceptable junction between differently offset surfaces.
- Resolve extent support for 129 held road meshes and 83 building/roof pairs. Cached DEM availability does not by itself extend the accepted rendered ground.
- Address 19 body/roof source-membership mismatch pairs without forcing incorrect joins.
- Inspect terrain coarsening: the initial every-23rd-centroid screen found 0.033 m median, 0.164 m P95 and 1.272 m maximum residual against the source DEM. A subsequent check of all 286,902 centroids found a 2.275 m maximum outside Main Street. The initial sampled maximum was not an all-surface bound. Refine where warranted before claiming equivalent source detail.
- Retain explicit bridge/tunnel/layer, water/shoreline, cartographic-overlay and outer-Context holds. A modelled wheel contact allowing up to 20 cm relief is also not final vehicle placement acceptance.

## Reproduction, safeguards and recovery

Builders: `tools/prepare_terrain_buildings.py` and `tools/prepare_terrain_surfaces.py`. Exact producers, manifests, ground arrays and dependency receipts are preserved in fresh ignored candidate folders. Building F and surface C use identical serialized ground geometry. Earlier surface A is rejected: its bare override replaced inherited transform-operation order. Fixed B/C preserves original operations and applies the world-Z anchor in the correct parent frame.

Combine the frozen local manifests without touching the active root:

```text
python tools/compose_terrain_review.py --manifest data/diagnostics/terrain_buildings_20261102_f/manifest.json --manifest data/diagnostics/terrain_surfaces_20261102_c/manifest.json --output data/diagnostics/NEW_FRESH_REVIEW
```

For the same fixed cameras over the unchanged baseline, use `--baseline` without candidate manifests. The composer requires fresh ignored output, matching snapshots and dependencies, standalone Z-up/metre layers, no candidate presentation edits or composition arcs, no conflicting property/prim opinions, and no nested newly authored family anchors. It checks USD composition, source identity/material bindings and visible-path coverage. An audit failure remains a failed acceptance result. The output is a review stage, not an activation receipt.

`tools/render_review.py` renders these stages through an isolated owned Kit process. Recovery consists of preserving the failed candidate and generating a new folder after fixing its cause. No active-state rollback is needed because these candidates were never adopted. Source/imagery rights, historical dates and current-condition limits continue to apply; original restricted references and derived scene geometry remain local.

## Bounded contact correction study — November 3, 2026

`tools/prepare_terrain_contacts.py` reuses the frozen F ground sampler, coordinated review stage and actual connected base edges. Run `python tools/prepare_terrain_contacts.py --output data/diagnostics/NEW_FRESH_CONTACTS` to prepare a separate, inactive addition under `/World/TerrainContactClosures`. The default 0.75 m whole-edge cap holds larger gaps rather than truncating them into floating strips. This is estimated rendering geometry below unchanged bodies/slabs, not surveyed foundations, basements, doors, stairs, new floors or new buildings. Source roof/body points, identity, visibility and material definitions remain unchanged; existing resolved materials are bound through subsets.

Preserved candidate B is `data/diagnostics/terrain_contacts_20261102_b/`. Independent CPU/source review checks all 80 dependencies, five protected files and 3,441 added meshes/111,909 faces. No invalid/degenerate faces, unresolved material targets or source-property opinions were found. Maximum height above the ground field is 0.744791 m; lower contact error is at most 2.384e-7 m. [Independent evidence](evidence/terrain-contact-candidate-review.json).

771 of the 772 flagged source paths receive **some** closure geometry. This does not resolve 806 contact rows: 125 large-gap edges, four unsupported edges, 1,445 unresolved-material edges and other holds remain. Full-centroid coarsening analysis leaves F's original ground untouched. Compose its manifest as a third input alongside F/C into a fresh review directory; inspect actual matched views and seams before any adoption. Actual visual acceptance remains pending. The active scene is unchanged.

The combined F+C+B review stage was actually composed at `data/diagnostics/terrain_contact_combined_20261103_a/review.usda` (SHA256 `23138ef74c45bdec58c37d3e04cf9b864a011fdab92b01e800c5e9b0fa5b5979`). The composition audit accounts for all 21,245 original visible boundables with zero missing paths, changed original identities or material bindings. It remains inactive. Before capture, a resource check found only 1.12 GB free physical RAM while the owner's open editor used 10.80 GB working set; no competing renderer was started. This is an execution resource observation, not a performance benchmark or visual acceptance.

## Matched contact renders and seam attribution

The isolated Kit capture completed on November 4 UTC after available memory recovered. The three 1920 × 1080 images and frame manifests are in `data/renders/20261104T000458Z/`. North, South and Church use the same camera poses and projection matrices as the previous F+C views. South shows the largest visible improvement at the left storefront base, where the long dark opening is largely filled. A short transverse opening and raised gray edge remain. North shows smaller improvements and visible step joins. The church connector bases read more continuously and a dark strip appears along part of the foreground brick base.

CPU rays from the saved Church camera provide specific leads for the upper gray seams. The upper-middle sample at pixel (900, 269) first hits `Building_3076` at about 5.15 m in the scene frame. Samples at (900, 280) and (900, 290) first hit `Roof_2919` at about 5.08 m. The right-hand samples (1522, 394) and (1522, 410) first hit `Roof_3065` at about 5.31 m. The upper-left sample (600, 135) hits `Roof_2928`, and the left trim sample (220, 580) hits a `Building_3076` storefront parapet. These samples point to legacy building and roof interfaces. Actual ground-level paving and sidewalk joins need separate picks. The probe tested visible meshes from the composed USD using the captured camera matrices and fan-triangulated faces. It gives sampled mesh attribution and approximate local elevations.

The visual review supports bounded base-gap improvement. Raised edges, roof interfaces, held contacts, road and sidewalk joins, and source-supported grade still prevent activation. Review evidence records the three pairs and remaining findings. [Independent matched-view review](evidence/terrain-contact-render-review.json)

### Southbound street-level seam trace

At the left storefront, samples on the black transverse strip first intersect the contact closure below Building_2897's `Front_0/EntryPaving`. At common XY the illustrative paving is at about 2.130 m in the scene frame and the overlapping shoulder at about 1.852 m. The resulting 0.278 m step has a vertical face, so the appearance cannot be corrected by filling a hole. A source-supported threshold and accessible-route grade are needed for physical regrading.

On the right, the Vassar Street road and shoulder overlap with a modeled 30 mm difference. The shoulder is 35 mm above the ground. Some dark pixels hit the shoulder top beyond the road edge, and several other samples hit only ground. These represent separate overlap and coverage cases. Extending the paved footprint requires a corresponding source edge. [Sample rays and source paths](evidence/edgewater-ground-seam-trace.json)
