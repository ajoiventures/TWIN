# Ticket execution checkpoint — October 28, 2026

The full ticket plan remains active. This checkpoint reports implemented and reviewed evidence, not completion of the whole digital twin.

## Property search delivery — October 28, 2026

The local map now searches the current parcel snapshot by address or parcel number, ranks matches before pagination and selects the exact mapped parcel. The inspector includes an OCPA zoning reference and explicitly unsurveyed parcel reference coordinates. Browser checks verified address and formatted PIN searches, selection, no results and reset; [usage and captured evidence](PROPERTY_SEARCH.md). The integration suite passed 200 tests at this checkpoint. This feature does not close its broader property-data or scene-quality tickets. GitHub status remains 30 open issues and one completed issue (#19), pending the next acceptance review.

## Latest Main Street extraction — October 28, 2026, 16:15 UTC

Expanded the shared extraction to fully contain the official City College Park Main Street polygon. Active snapshot `20261028T160543372334Z`: 13,999 OCPA footprint subareas, 3,216 building groups, 3,916 parcel features and 1,310 OSM road segments. Actual 3D ground covers 100% of Main Street (0 m² uncovered); wider neighborhood context remains partial at 60.77%. Full district coverage does not imply current, individually verified building geometry.

Recomposed the scene, preserved the seven-storey Wellesley correction (23.35 m historical LiDAR height), and regenerated the map guard: zero visible object/tree spillovers. Validation checked 17,608 meshes, including 3,480 instance proxies, across 16 layers with zero errors. All 137 tests pass, including rejection of stale quality reports when their parent data is current. The refreshed 0.4 editor reported WORKSPACE_READY with 3,216 building meshes. Live map/API now serves the expanded snapshot. See [scope evidence](STUDY_SCOPE.md).

Broker evidence and accepted property context are available through the map/scene; current market statuses remain unknown where freshness cannot be established. Ticket #32 tracks remaining verification. Older checkpoints below retain their original counts and are superseded by this extraction for current coverage.

## Accepted delivery

GitHub #19 is closed as completed after independent review. The implementation is published for review in [draft PR #31](https://github.com/ajoiventures/TWIN/pull/31). Remaining implementation tickets stay open; the overall goal is active.

**#19 government-source catalog/discovery:** 17 source records, three bounded searches, six original elevation-tile candidates, acquisition deduplication, ranked decisions, safe previews and geographic metadata-coverage diagram. Actual API/coverage routes and checkbox controls were verified; 20 focused tests and independent review passed. Restricted canopy data is excluded from AI use. Dataset activation/terrain QA, exact imagery eligibility and transportation semantics remain downstream tasks.

## Implemented and still in progress

| Tickets | Current evidence | Remaining acceptance |
|---|---|---|
| #1 | Migrated source generators, configured independent Kit editor, project-relative paths, preserved manual layer | Clean-checkout redistributable sample and startup/performance acceptance |
| #3/#4 | Cached official adapters, atomic active snapshot, read-only API/map, source-schema tests; parcel audit recomputes 3,053 assigned overlaps | Full property/sketch, exception, refresh/recovery and entity-lineage review |
| #5/#17 | Princeton-to-southern-Smith pilot frozen from City centerline geometry; 85.44 m, 21 contextual building groups, one spatial review link | Official district boundary reconciliation, accepted curb/sidewalk/parking geometry and dimensional review |
| #6 | 976 changed heights; 90 historical LiDAR and 3,000 estimates; actual unit validation retained | Expanded roofs, original DEM integration, terrain/ground anchoring and current-condition review |
| #9/#10/#18 | Original detailed trees/cars and illustrative scene assets | Verified locations/parking/clearances, fixed-camera visual and target-resolution performance acceptance |
| #12/#26 | Stable source-based registry; additive semantic layer; stale API guards; instance-aware scene validation; cache provenance corrected | NVIDIA-library preflight, task-specific physical checks/repair loop and full release review |
| #16 | Four overlapping draft crosswalk versions queried; latest 166 review-only polylines and 28-field dictionary; no draft promoted | Actual sidewalks/ramps, authoritative status/unit meanings, dated geometry and pilot acceptance |
| #29/#30 | Read-only runtime feasibility assessment against actual hardware and current vendor requirements | Selected authorized inputs, compatible execution environment and real held-out evaluation; no full-stack deployment assumed |

Parcel evidence: 3,783 features / 3,782 PINs; 2,857 exact ID+geometry links, 196 spatial review, 3 ambiguous and 34 unmatched. Ninety-seven accepted one-to-many parcels contain 210 groups. Five large floor conflicts and 550 one-floor disagreements are queued; no link/height is silently changed by the audit.

## Verification

- Current active snapshot: `20261028T145054204280Z`; offline refresh preserved counts and retained unknown original legacy fetch times.
- 74 automated tests passed across source adapters, API stale-data guards, heights, parcel/pedestrian discovery, pilot selection, semantic contracts and scene-validator failure cases.
- Composed local visualization profile: 3,090 entities, 17,485 meshes including 4,000 instance proxies, 12 USD layers, 16 external assets, zero validation errors. This does not certify survey accuracy, physics or NVIDIA SimReady readiness.
- Live loopback API checks passed for assets, quality, validation, pilot, source catalog, pedestrian access and five-row crosswalk pagination. No agency calls are made per map request.
- Five sequential local API samples per route: median health 15.49 ms, five-asset page 106.93 ms, five-parcel page 197.90 ms, full 7.35 MB map 1,601.37 ms. These are a small loopback sample, not concurrent load or rendering benchmarks.
- Independent reviewers found cache/hash, instance coverage, copied-parcel-story and nonfinite-overlap weaknesses; corrections and regression fixtures were applied. Fresh-directory and generator-order fixes are documented.

## Next delivery

Integrate accepted original DEM data with explicit US-survey-foot to meter conversion and terrain anchoring, review pilot parcel/floor conflicts, then reconcile current aerial/pedestrian evidence before constructing accepted streetscape geometry. #20/#25 supply the remaining reference evidence. #27 reconstruction and #28 planning/replay build on that baseline; #21 remains a separate proposed-design layer. No global blocker or completion claim is made.

## Main Street presentation work in progress

Added a reversible close oblique camera, optical depth of field, warm sun/sky, greener landscape and brighter leaf texture scaling. Official boundary graphics are hidden for presentation. All 137 tests and the 17-layer scene profile pass. Final rendered acceptance is still pending; UI interaction was interrupted by active user input/minimization. These settings do not establish photorealism or fix unresolved source geometry.


## October 28 integration checkpoint — snapshot 20261028T160543372334Z

Supersedes numeric baselines above: 3,216 building entities; 20 composed layers; 17,611 meshes and 3,480 instance-proxy meshes; 19 external assets; zero local-profile validation errors. All 166 tests passed. Reviewed Princeton historical reconstruction is composed and registered. Wellesley roof revision 2 is applied: false equipment voids filled, courtyard preserved, 23.35 m main roof and separate 28.393 m maximum roof/equipment surface. Full Main Street ground coverage is retained.

Road material quality tiers and the local aerial/texture gallery are implemented; HTTP checks returned 200 for all four allowlisted images and 404 for unknown names. Actual 1080p render inspection still shows generic façades and approximate road/sidewalk geometry. These remain open, along with terrain integration, corridor-wide detail, scenario/operations acceptance and conference playback validation. The heavy-blur presentation setting is being revised; no finished visual quality claim is made.

## Latest integrated/proposal checkpoint — October 28, 2026

The 1615 office is composed as a historical, photo-interpreted display draft with coherent roof sections, four approximate dormers, two point-supported chimneys, public-front details and original physical-scale brick textures. Current/as-built and conference acceptance remain open. The local scene profile passes with 3,216 original building entities, 17,623 meshes, 3,480 instance-proxy meshes, 22 layers and 22 external assets. Full suite: 232 tests passed; the five additional district asset checks also pass.

Other delivered code remains at its stated stage: original-DEM terrain and anchoring proposals (3,101 rigid building groups plus paired roofs; 1,680 draped road surfaces; exclusions and unanchored assets retained); district tree/car revision proposal preserving 505 tree arrays and 87 vehicle transforms; corridor sidewalk/rear-asphalt proposal with 40 unresolved sampled side-stations. These three proposals are not activated or accepted current geometry. The updated workspace has startup retry, inherited evidence, temporary display switches and manual-only saving; live Kit UI proof remains pending. Exact-feature map/3D selection passes contract tests and browser-to-API checks; the running older editor has not acknowledged the new bridge.

The owner requires highest quality, parallel execution and consolidated review after each five completed tickets. The district-wide missing-building process is explicit in the linked delivery plan and existing #3/#6/#14. No full-ticket closure is inferred from these partial deliveries. Source records, historical corrections and draft visuals remain distinct.

## Latest building-review and visual checkpoint — October 28, 2026, 22:14 UTC

The repeatable all-use audit now classifies 3,849 parcel-feature records (3,848 parcel IDs) inside the official boundaries or prior corridor context, from 3,916 extracted records. It checks 3,205 visible model entities and recognizes both the office and Princeton reconstructions. The old 17-record commercial queue resolves to seven land/parking records, one already reconstructed office and nine unverified records—not nine confirmed missing buildings. Across the wider extract, 384 records remain potential physical omissions and 322 parcel-story/component comparisons need review. All 13,999 official subareas were checked; no FLOOR_NUM 2/3 record was omitted from the source-floor calculation. These findings do not establish accurate occupied floors or current geometry.

The local `/building-review` page and API expose exact-feature identities, address/state/scope filtering, pagination and coverage gaps. Main Street ground extent is 100%; neighborhood extent is 60.768%, with building counts in the remaining 3,285,546 square meters unknown. Report snapshot and dependency hashes must match before display. Live HTTP page/API checks passed, including five returned rows; interactive browser acceptance remains pending. The workspace also has reversible evidence-category filters and freshness labels; live Kit acceptance remains open. Full automated suite: 248 tests passed.

Actual 1080p renders compared current and revised assets fairly. Revised oaks remove block-like leaf cards; palms gained denser leaflets and upright crown fronds. The original procedural asset proposal preserves 505 tree placements and 87 vehicle transforms. The comparison and capture manifest are saved under `docs/evidence/environment-assets-comparison*`. These assets and the combined corridor ground workview remain inactive drafts, not a realism sign-off.

The Princeton–Edgewater workview exposed jagged building silhouettes. All examined building/roof meshes already disable subdivision, and Princeton/Wellesley face normals match their geometry. An isolated flat-normal comparison did not materially resolve the appearance, so it remains a diagnostic proposal. Coherent source-supported roof planes and architectural wall outlines are still required; this problem is not marked fixed. Existing office/parking layers missing from the current root composition were restored additively, preserving root camera/render opinions. A running older editor can still overwrite its stale root; its manual-only save update is implemented but not loaded into that existing session.

Next source-verification block: shared retail records at 1305–1319 Edgewater, then 720/738 Rugby and 3457 Edgewater. Do not assume six retail tax records mean six separate buildings. The post office has a ready historical form but remains uncomposed with a frontage-reference gap. No full ticket was closed by this checkpoint; consolidated acceptance remains after five completed tickets.

## Latest activated geometry and runtime checkpoint — October 28, 2026, 22:39 UTC

Environment revision 2 is now activated with guarded source/asset hashes, rollback backups and preserved 505 tree placements / 87 vehicle transforms. It remains illustrative placement, not accepted parking or pedestrian clearance. Wellesley's coherent architectural interpretation is also composed: seven documentary storeys, 23.35 m main roof, 28.393 m equipment maximum, protected courtyard retained. Same-camera actual rendering confirms removal of the jagged silhouette. The fitted outline has a 3 m Hausdorff departure and 10.30% symmetric area difference from the historical roof outline; current/as-built geometry and blank facades remain unaccepted. These explicit limitations are carried in active metadata. Both activations are reproducible and retained during normal recomposition.

Source verification for 1305/1311/1313/1315/1317/1319 Edgewater produced one 1,071 m² roof-derived historical form supported by 9,812 classified roof points. Six tax records are associated with that form without asserting six physical buildings. The 300-face closed-shell proposal and actual rendered evidence are saved; it is not activated. Ground wall lines, overhangs, entrances, facade detail and current conditions remain unresolved. Roof residual p95 is 0.289 m; this is not footprint positional accuracy.

The new building-review page passed actual browser lookup of exact feature `ocpa:99613`, returning only 1615 Edgewater and correctly showing its historical reconstruction. Screenshot: `docs/evidence/building-review.png`. The portable sample's missing optional extension dependency was fixed. Its original generated configuration now opens and renders through the documented SDK: first viewport frame 8.312 s; median completion interval 16.299 ms across 120 samples, peak sampled RAM 5.132 GiB and device-wide VRAM 2.446 GiB. These are small-sample measurements, not full-district FPS or per-process VRAM. Generated sample hashes stayed unchanged; edit-panel button interaction remains unverified. See SAMPLE_BUILD.md and portable-sample-runtime evidence.

A strict scene check detected a changed base-file hash. An offline isolated replay reproduced the original registered hash exactly and compared all 8,366 prims: geometry, topology, UVs, materials and transforms were unchanged. Only two camera exposure API metadata lists differed. The current base was preserved, then the semantic registry was normally regenerated. The resulting scene profile passes with 3,216 original entities, 17,711 meshes, 3,480 instance proxies, 28 layers and 23 external assets. Full automated suite: 259 tests passed. No full-ticket completion is claimed from these individual implementation steps; remaining acceptance and the five-ticket consolidated review still apply.

## Latest retail activation and batch readiness — October 28, 2026, 22:57 UTC

The 1305–1319 Edgewater historical roof-derived form is now activated. One reconstruction entity retains all six parcel IDs; all six live API lookups return that same entity once. It adds a missing modeled form without asserting physical subdivision, current storefront identity or accepted tax-to-building links. The original 17-record commercial queue now has seven historical-reconstruction parcel contexts (office plus six retail records), six land/parking records, one land/geometry conflict and three unverified omission candidates. Across the wider in-scope review, omission candidates declined from 384 to 378 parcel records; these remain records, not a census of physical buildings. Current visible modeled entities checked: 3,206.

After activation, the composed scene passes its local profile: 17,712 meshes, 3,480 instance proxies, 29 layers and 23 external assets; all 267 automated tests pass. A transformed-geometry audit checked 403 visible trees and 70 visible cars while preserving 102 tree and 17 car masks. No additional unequivocal low-trunk/body collisions warranted hiding or relocation. Ten canopy-bounds cases and all 70 cars' roadside/parking status remain review-only; this does not establish verified parking or pedestrian clearance. The empty clearance proposal is not activated as a cosmetic change.

Ticket #1 is implementation-ready for the five-ticket consolidated review batch (one ready ticket in this batch, not a newly closed issue). A clean committed archive built the sample, actual UI scenario/manual save controls worked, and a separate Kit process reopened it with the manual override preserved. Source/base hashes stayed unchanged. Evidence is in `docs/evidence/portable-sample-clean-checkout-report.json` and `portable-sample-manual-saved.jpg`. Final portable path/grid patches and remaining ticket-wide review still apply. The preview utility's last workstation-specific paths were replaced with explicit arguments and an ignored local default output. No additional whole tickets are marked complete here.
