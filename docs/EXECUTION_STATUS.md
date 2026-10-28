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
