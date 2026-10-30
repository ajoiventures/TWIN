# Ticket execution checkpoint — October 28, 2026

The full ticket plan remains active. This checkpoint reports implemented and reviewed evidence, not completion of the whole digital twin.

## LYNX published schedule integration — October 29, 2026 UTC

Connected the actual official static GTFS feed, including service calendars and exceptions, 15 study stops and routes 106/125. The transit page now checks a selected date, labels expired/not-yet-effective periods and exposes source fields/sample records. Actual API/browser checks distinguish 100 scheduled local-stop trips on October 28 from unknown availability outside the feed period. Older GIS route 89 stays separate. [Contract and actual UI](LYNX_GTFS_REFERENCE.md). Live positions, FDOT/civil geometry and expanded transportation requirements remain open.

## Interpreted Princeton roof visual review — October 29, 2026 UTC

Built and rendered a second separate roof proposal using broad architectural caps and terraces. It removes many pits but still has implausible compound joins; integrator and independent reviewer reject architectural acceptance and activation. Composed normals and face planarity were checked, so the next correction must address component geometry rather than a shading workaround. [Actual matched images and evidence](PRINCETON_ROOF_REFERENCES.md). No active geometry changed.

## Property inspector government references — October 29, 2026 UTC

Connected the accepted government-reference register to selected parcels using exact active feature and parcel identities. Actual browser review verified federal classification, a retained County/municipal conflict, unknown ownership for an unclassified office parcel, and clearing. Added readable inspector styling and preserved map-only review. [Usage and evidence](PROPERTY_SEARCH.md). Wider property/scene requirements remain open.

## Government property reference integration — October 29, 2026 UTC

Screened 5,732 OCPA parcel features against exact published use-code definitions and official inventories across the full neighborhood. Identified 93 government-related references, including five City vacant-lot inventory matches and one conflicting County/municipal reference. Independent source/geometry review passed; actual API/browser fields, first five rows and coverage are available on local port8773. All legal title/public-access/current-vacancy fields remain unverified. [Delivery and remaining scope](PUBLIC_OWNERSHIP.md). This does not close the broader land/planning tickets or expand the active 3D ground.

## Native control round trips — October 29, 2026 UTC

Added broad clickable labels and verified independent tree, car and storefront hide/restore in the actual editor. Illustrative filtering removes those details and master-off restores them; corrected no-change refresh wording is now verified natively. Review session closed normally and all four protected file hashes remained unchanged. Remaining switches, filter responsiveness and changed-layer native recovery keep #12 open. [Evidence](NATIVE_CONTROL_REVIEW.md).

## Distributed coordinate checks — October 29, 2026 UTC

Ten City Main Street references spanning 2.8 km agree numerically with the composed scene's boundary; ten independent native DEM grid ties agree with the inactive terrain proposal. Origin, east/north axes, metre scale and Z-up are consistent. The reviewer identified a potential whole-pixel-shift blind spot; source-derived vertex ordering and world-transform checks now address it. These checks do not establish field/survey accuracy, which has no accepted control network or tolerance yet. [Report and remaining #5 gates](ALIGNMENT_REVIEW.md). No geometry activation or ticket closure.

## Roof interface findings — October 29, 2026 UTC

The revised connected-region analysis improved source fit but exposed unresolved interfaces with the retained roof: 4,421 sampled boundaries, 0.715 m p95 and 3.230 m maximum height disagreement. Nearby historical returns support different interpretations at different locations. A fresh look at the dated aerial distinguishes roof forms without resolving historical elevations. Saved reproducible diagnostics and conflict evidence; no forced seam walls, replacement roof or active geometry change. [Roof method and remaining work](PRINCETON_ROOF_PLANES.md). #6/#8 remain open.

## County reference integration — October 29, 2026 UTC

Connected 137 County address references, seven roads and two drainage basins for the existing Edgewater pilot context. Independent review reconciled all 146 features against cached originals and verified safe IDs/fields. Fixed transitive City freshness and source-item URL findings before integration. Actual API/browser checks show fields, sample rows, sources, gaps and coverage on port8772. Address-location differences remain flagged, not snapped; inaccessible ROW remains unknown and empty County pipe/structure queries do not establish no City drainage. [Delivery and remaining #22 scope](COUNTY_CONTEXT.md). Active scene and dataset are unchanged; **6 closed / 25 open**.

## Native roof inspector and review isolation — October 29, 2026 UTC

Verified roof picking and actual property/source evidence in a separate native editor; checked no-change refresh and unavailable Undo. Added session-targeted review mode with map bridge/project Save disabled and fixed the misleading applied message on no-op refresh. The owned review process closed normally; connected scene, manual edits, active pointer and selection state hashes are unchanged. Checkbox round trips and changed-layer native recovery remain unaccepted. [Evidence and limits](NATIVE_CONTROL_REVIEW.md). #12 stays open; totals remain **6 closed / 25 open**.

## NVIDIA isolated asset pilot — October 29, 2026 UTC

Pinned NVIDIA SimReady validation 2026.8.0 in a separate environment. One copied registered building passes Core, Semantic Labels and Cityscapes profile checks. The exact candidate was rendered at 1920×1080; independent integrator inspection accepts the fully framed plain source mass only. Source assets, registry and user editor remain unchanged. [Actual image, validator evidence and remaining gates](SEMANTIC_VALIDATION.md) distinguish this interoperability pilot from district simulation, architectural realism and NVIDIA certification. #26 remains open for broader scope, metadata/resource gates and dependencies; ticket totals remain **6 closed / 25 open**.

## City sources and full-neighborhood parks — October 29, 2026 UTC

Integrated supplemental City address points (4,621) and future-land-use polygons (46), plus 11 park reference footprints across the full official neighborhood. Mathews, Overbrook and Don Dudley parks supplement the prior eight. Independent park review reconciled all 14 source candidates and clipped memberships; the three outside candidates are excluded. The local source browser on port8771 exposes fields, first five rows, source dates, quality and coverage. Existing snapshot, 3D ground and user sessions remain unchanged. See [City contract](CITY_ADAPTER_CONTRACT.md) and [park inventory](FULL_NEIGHBORHOOD_PARKS.md). Ownership, vacancy, governing planning conditions and park-site acceptance remain open; totals remain **6 closed / 25 open**.

## Princeton matched-render decision — October 29, 2026 UTC

Rendered baseline and proposed roofs at 1920×1080 with matched camera, lighting and material. Independent geometry checks passed, but both integrator and separate visual reviewer rejected activation: the candidate adds triangular pits/fins and fragmented roof steps. Saved original renders and an explicit failed visual gate in [Princeton roof review](PRINCETON_ROOF_REVIEW.md). The existing scene and user sessions were not changed. A connected-region/analytical-boundary revision is in progress; full ticket totals remain **6 closed / 25 open**.

## Boundary exception disposition — October 29, 2026 UTC

Independently replayed the actual generator boundary exclusion for all 73 raw subareas absent from modeled membership. All 73 are outside the extraction: empty intersection and zero inside area. This resolves their exclusion reason without inventing missing buildings or changing source IDs, snapshots or geometry. The wider neighborhood coverage gap remains open. [Bounded evidence](evidence/orphan-boundary-review.json) and [lineage follow-up](BUILDING_LINEAGE.md#follow-up-orphan-boundary-disposition). Ticket totals remain **6 closed / 25 open**. Princeton roof proposal refinement is still under independent review; no roof activation is claimed.

## Learning and script protocol adopted — October 29, 2026 UTC

Delivered the owner-requested reusable protocol plus College Park profile, script-contract and lesson-record templates, and seven evidence-backed seed lessons. Repository `AGENTS.md`, the project index and team operating plan link the workflow so future project work can retrieve it. Independent VP protocol review passed; owner/adoption details and batch-review wording were clarified from its findings. This is repository documentation and reusable templates, not model retraining, global installation or a scheduled automation. Existing ticket scope and count remain unchanged: **6 closed / 25 open**. [Start here](protocols/LEARNING_AND_SCRIPT_CREATION.md).

## Latest implementation — October 28, 2026 local time (October 29 UTC)

Added immutable source lineage for all 3,216 building groups, reusing existing entity IDs and preserving every frozen building field and all 3,916 parcel features. Actual replay leaves snapshot, connected scene and manual bytes unchanged. The API and expandable property inspector expose original subarea IDs and distinct parcel-feature candidates; browser review at 2204 Edgewater confirms two separate source building groups. [Lineage contract](BUILDING_LINEAGE.md) and [integration evidence](evidence/building-lineage-acceptance.json).

The raw-membership review explicitly retains 73 unrepresented subareas across 46 source groups (35 partially represented and 11 wholly unrepresented). These are review candidates, not confirmed missing physical buildings. #3 remains open for full property/sketch/coverage work. Total remains **6 closed / 25 open**.

The updated review app is available on local port8770. Port8768's API was preserved after automatic review blocked its restart; no denial reason beyond policy was supplied. Map inspection can be unlinked from 3D selection, and a preserving restart option retains valid selection state. [Native editor evidence](evidence/workspace-native-controls.json) records remaining #12 controls and preservation of the user's unsaved camera work. Rhino was also left untouched.

## Latest accepted ticket — October 28, 2026 local time (October 29 UTC)

**6 closed / 25 open.** #20 is now accepted after independent PM/Director source/image/census review and actual integrated API/browser/scene-provenance verification. Its 22 dated building reviews and eight frontage sectors are available from the map's dated aerial review link; the optional 3D review layer is composed off by default. Root opinions, prior layer order and manual edits were independently confirmed unchanged. [Acceptance and limits](PILOT_AERIAL_REVIEW.md). This is the first closure after the five-ticket consolidated review below; the next consolidated review is due at ten completed tickets.

Refreshed reconstruction and corridor ledgers against the new composition. Fixed native inspector sizing and roof-to-building identity, added aerial source details and explicit unavailable-scenario text; focused recovery/selection checks pass. #12 remains open for actual roof/checkbox/refresh control acceptance. Foreground testing stopped on user activity; the older unresponsive user session was preserved. A-01 surveyed alignment and A-02–A-08 detailed geometry/visual production remain open.

## Current consolidated acceptance — October 28, 2026 local time

**Qualified five-ticket pass: #1, #2, #19, #23 and #24 are closed; 5 closed / 26 open.** This supersedes the historical issue counts and awaiting-review statements below. Five actual existing tickets passed their relevant independent acceptance gates; it is not a full-district visual, survey, performance or live-operations sign-off.

| Closed ticket | Accepted delivery and evidence | Practical limit |
|---|---|---|
| #1 | Portable original sample; clean committed archive build, actual Kit capture and manual/scenario save/reopen; separate final GIS acceptance. [Sample evidence](SAMPLE_BUILD.md) | Fictional offline baseline; district geometry/currentness and district performance remain open. |
| #2 | Six-source read-only audit, schema/freshness/reconciliation exceptions and publication allowlist; independent root privacy/source-contract review; delivery commit `e44ca09`. [Audit contract](SOURCE_ADAPTER_CONTRACT.md) | Private records remain held; missing original receipts/terms are recorded unknowns and authorize no release. |
| #19 | Official-source search, ranked/deduplicated decisions, schema/sample/coverage outputs and working local API/UI; independent review. [Catalog evidence](SOURCE_CATALOG.md) | Candidate catalog acceptance does not activate every dataset or accept terrain/transport semantics. |
| #23 | Historical water/landcover packet, safeguards and independent geometry review; actual Lake Adair render accepted; optional composition off by default. [Water evidence](WATER_LANDCOVER_CONTEXT.md) | Historical contextual polygons, unknown current shoreline/water elevation; clipped study boundary retained. |
| #24 | Effective FEMA source/coverage review and actual enabled-view visual acceptance; source-preserving optional composition off by default. [Hazard evidence](FLOOD_HAZARDS.md) | Mapped effective hazard information, not live flooding, modeled depth or insurance determination. |

#3 remains open despite its working adapter/search/selection: the current snapshot's review queues, component/sketch conflicts and full-project completeness still need disposition. The latest source audit verifies 3,916 parcel features / 3,915 PINs and 3,216 source building groups, with 2,976 exact links, 202 spatial-review, 3 ambiguous and 35 unmatched; 561 floor disagreements include six larger conflicts. Main Street extent is covered, while neighborhood extraction remains 60.768%; neither metric certifies physical-building completeness. #12 native controls and #20 dated pilot observations are undergoing their own delivery/acceptance work. Their state is not inferred from the five closed tickets.

## Property search delivery — October 28, 2026

The local map now searches the current parcel snapshot by address or parcel number, ranks matches before pagination and selects the exact mapped parcel. The inspector includes an OCPA zoning reference and explicitly unsurveyed parcel reference coordinates. Browser checks verified address and formatted PIN searches, selection, no results and reset; [usage and captured evidence](PROPERTY_SEARCH.md). The integration suite passed 200 tests at this checkpoint. This feature does not close its broader property-data or scene-quality tickets. At this historical checkpoint there were 30 open issues and one completed issue (#19); the current five-ticket acceptance above supersedes that count.

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

## Latest delivery and independent acceptance — October 28, 2026

Ticket #1 passed final independent acceptance by the GIS agent, who did not implement the sample. All four original criteria were checked against committed archive, runtime, edit/save/reopen, dependency/configuration and source-preservation evidence. A remaining main-launcher spaced-path bug was fixed with a project-directory launch and relative bootstrap; independent generation in a temporary checkout containing spaces passed. Evidence links now resolve to committed artifacts. This final closure check follows the owner's renewed instruction to start completing tickets; the broader five-ticket consolidated review cadence remains in place.

720 and 738 Rugby are now active historical pitched-roof drafts, with separate reconstruction identities. Their actual renders were inspected before activation. 3457 Edgewater remains an inactive high-residual proposal; current walls and facades are not accepted. The original commercial 17-record queue now has one unverified modeled omission candidate, one land/geometry conflict, six land/parking records and nine historical-reconstruction parcel contexts. Wider neighborhood completion remains open.

Workspace runtime checks proved exact-feature map-to-Kit and Kit-to-map selection, unmatched states and clearing. Separate inspector/status panels prevent evidence being overwritten. An anonymous workspace root contains Kit's camera/render opinions while source/manual file hashes remain unchanged. Native final checkbox/pixel-selection review remains outstanding. LYNX static GIS now supplies 15 stop records and three route features through `/transit` and its cached API; actual browser selection of the Princeton–Edgewater stop worked. Calendars/live vehicles remain unavailable, and source-coded pedestrian attributes are not surveyed sidewalk geometry.

The OCPA adapter now rejects modified cache contents, quarantines invalid optional/source geometry values and preserves ambiguous exact-ID candidates. A previous regression expected modified cache data to be consumed with a downgraded timestamp; it was corrected to require rejection, matching the stronger ingestion contract. Integration checks pass. These adapter/source-audit changes do not close full-project verification or private release requirements in #2/#3.

## Latest government overlay integration — October 28, 2026, 23:48 UTC

The local API and district navigation now connect `/flood`, `/api/v1/flood`, `/flood/coverage`, `/water-context`, `/api/v1/water_context` and the bounded Lake Adair aerial reference. Every data/reference request validates the active snapshot and source/artifact checksums. An actual builder edit caused the FEMA API and coverage route to reject stale evidence; offline regeneration restored successful responses. The initial FEMA text-encoding defect was corrected and browser-checked.

Actual browser checks loaded seven FEMA effective zones, preserved the 2009-09-25 panel date and original zone codes, exercised the off-by-default map toggle and inspected Main Street zone `12095C_3779`. The water page loaded 56 land-cover polygons, 12 water-class polygons and 11 older waterbody records. The Lake Adair comparison displayed January 2025 aerial imagery alongside explicitly dated 2012 shoreline and 2020–2021 land-cover references. This is historical context, not a current shoreline survey or flood simulation. Independent source/scene review and optional scene composition are still pending; #23/#24 remain open.

The updated user-facing 3D model is open at MainStreetOverview. A fresh-launch guard initially preserved an empty SDK stage and produced a black viewport. A dedicated explicit project launch loaded the current scene through a transient root without saving source layers. The standard startup guard has a narrow corrective patch under review; no broad permission to replace user scenes was added. Editor refresh/recovery acceptance remains in progress under #12.

## Overlay review corrections — October 28, 2026, 23:54 UTC

FEMA normalized-packet integrity now has a separate byte-checksum receipt; packet-only changes are rejected. The optional layer was composed on disk with its invisible default, root backup and manual-edit preservation. An actual Kit capture (`data/renders/20261028T235035Z/DistrictOverview.png`) revealed that its broad X-zone fill washes out the scene when enabled. This capture is a failed presentation review, not acceptance. Display correction and another render remain required; GitHub #24 records the outstanding defect.

Water rebuilding now protects edited generated outputs, keeps rollback backups, checks the relevant composed ground/water geometry and labels August 2012 as a source update rather than an effective date. The API was restarted with these changes and returned the current water packet successfully. The editor's government preview now invokes each adapter's full validator and exposes its actual date/schema fields. Both adapter previews pass current validation. Independent water re-review and editor runtime acceptance remain open.

## Accepted FEMA presentation and water composition — October 29, 2026, 00:02 UTC

The corrected FEMA enabled view passed parent inspection and independent VP visual review: six mapped SFHA polygons are readable in blue, X retains its source identity without a broad scene fill, and building/road context remains visible. The actual render and source-preservation manifest are committed as `docs/evidence/fema-mapped-hazard-render.png` and `.json`. Independent PM review verified source coverage, effective status, dates and labels. The seven original records remain in the packet/inspector. The overlay stays off by default, with recoverable disk composition and validated persistence through future scene rebuilds. These checks satisfy #24's bounded information-overlay requirements; they do not certify flood levels or insurance decisions.

Water context has also been composed off by default with a recoverable root backup. Independent data review passed, and the actual Lake Adair optional-layer render is pending. #23 remains open until that render is inspected. Editor control work is implemented but #12 remains open for native runtime acceptance; the broader full-project tickets are not closed by these adapter deliveries.

## Water delivery accepted — October 29, 2026, 00:05 UTC

Ticket #23 passed independent source/geometry/safeguard review and actual Kit visual review. Both water and FEMA activation preserved root opinions and manual-file hashes; both layers remain invisible by default. The actual Lake Adair capture shows historical water/land-cover context on the clipped ground, without floating sheets; its straight lake termination remains an explicitly documented study cut. Render, provenance and acceptance records are committed under `docs/evidence/water-context-*`. #24 was closed after delivery commit `5ed1a1a`; #23 is ready for closure with this evidence. Native editor interaction acceptance remains in #12, and the full project goal remains active.


## FDOT reference integration - October 29, 2026 UTC

Independent review passed all 11 source tables, 767 City coverage comparisons and 16 exact traffic-site joins. The validated packet now serves /fdot-context and eleven paginated API tables; government source records expose field dictionaries and first-five samples. Actual API/browser checks confirmed sidewalk records and selected the Princeton-Edgewater annual traffic site. Source/native IDs, unknown dates and inventory-gap limitations remain visible. See FDOT_CONTEXT.md and evidence/fdot-context-review.json. No road/sidewalk geometry was promoted, and full transportation ticket 15 remains open.


## Native boundary and durable recovery review - October 29, 2026 UTC

Fixed hidden-parent boundary controls and roughly halved full-scene confidence-helper time. Actual isolated native Apply/Undo and fresh-process Recover passed with a visibly changed copied boundary. Native filtering preserved independently hidden vegetation. All 62 protected physical files unchanged (duplicate path spellings removed); owned reviewers closed normally, owner editor preserved. Independent PM review found startup missing-asset preflight still needed for full ticket12 acceptance. See NATIVE_CONTROL_REVIEW.md and native-refresh-recovery.json.


## Native startup recovery - October 29, 2026 UTC

Startup preflight now rejects missing dependencies and empty geometry before attachment. Actual native missing-asset and missing-manifest messages plus restored-input Retry passed. The isolated review closed normally without saving; all 62 protected physical files remain unchanged and the original editor remains running. Eighteen focused checks passed; complete ticket 12 independent acceptance is pending its final matrix.


## Ticket 12 closed - October 29, 2026 UTC

Pushed 4ac7210 and closed ticket 12 after the independent eight-criterion acceptance matrix passed. Fresh GitHub state: 7 closed / 24 open; next consolidated review at 10 completed existing tickets. The full project remains active.


## Parking/mobility integration and pedestrian evidence - October 29, 2026

Integrated four attributed local parking/charger references, 24 published study count cells and 70 proposed unlocated recommendations. Complete field dictionaries, first-five previews and readable facility cards passed independent source/HTTP review and actual browser inspection. Missing legal capacity, access, entrances and demand remain explicit. New pedestrian acquisition found 67 MetroPlan references (18 synthetic nonphysical duplicates) plus 263 draft recommendations, retained separately. Independent review passed bounded source/geometry findings; actual sidewalk/ramp layers and engineering/as-built geometry remain missing. Tickets 15/16/25 remain open.


## Office appearance integration and asset review - October 30, 2026

Integrated independently reviewed cornice, small front pediments and darker roofing for 1615 Edgewater as a separate appearance layer. All 177 existing office geometry/transform records match the reviewed base; only one root sublayer was added, preserving other root/manual/snapshot/selection opinions and recoverable backups. Scene rebuild/refresh retain the guarded layer; reconstruction/corridor reports and the local scene profile were refreshed. Actual integrated detail placement passes, while overall presentation fails due to facade striping and black road/sidewalk polygons. Those defects remain under diagnosis. Revised trees/cars remain inactive after actual visual rejection; permissive production-asset source research is documented. No whole ticket closed; 7 completed / 24 open remains the latest verified count.


## Corrected render setup and appearance provenance - October 30, 2026

Independent review traced an invalid temporary render setup: implicit Y-up/centimeter units instead of project Z-up/meters. Exact old wrapper bytes were archived by capture hashes. Corrected actual full-scene render retains camera/material/geometry/light layers and has no earlier facade striping or black road bands. The previous material-defect diagnosis is superseded; no material/geometry change was necessary. Render helper now requires explicit physical metadata and precomposes candidates, with 20 focused checks passing. Appearance detail provenance/filtering now exposes a stable appearance ID, broker reference, unknown dates and illustrative quality. Local API at8768 was restored after authoritative absence and serves current mobility/reconstruction/corridor records. Original user editor remains untouched. No whole ticket closure; full realism/accuracy work continues.


## Separate post-office historical form - October 30, 2026

Added the reviewed historical four-component post-office form in a separate layer, preserving office/manual/root opinions apart from one additive sublayer. Source/geometry/preservation and isolated actual rendering passed independent review. Current operation/facade/geometry remain unverified; no raw tax links or physical-building count promoted. Reconstruction API exposes the separate historical site; derived corridor/reconstruction reports refreshed. Hardened identity/dependency validator after two independent findings; focused regression and nine independent cases passed. Integrated render command was blocked by automatic approval review (blocked by policy; no specific reason), created no process/wrapper and was not retried through an equivalent route. In-scene visual acceptance remains pending. Corrected-unit tree/car review still falls short of realism; no district replacement activated. No whole ticket closure.


## Full-neighborhood parcel planning integration - October 30, 2026

Connected 5,723 parcel-feature contexts, 74 exact zoning-code area groups and 19 FLU categories to the checked API/source browser, including fields and first five rows. Multiple intersecting codes and PD-review flags remain explicit; unique land-area unions are separate from overlapping tax-row sums. Independent original-source/area review and separate HTTP/UI integration review passed. Three invalid City polygons are quarantined, and nine numerical parcel slivers explain the ownership-inventory count difference. Governing ordinance/overlay/PD conditions, current use, vacancy and legal ownership remain unverified; full #4 stays open. [Contract and evidence](CITY_PLANNING_REFERENCE.md). No scene or active snapshot changes; completed-ticket count remains 7, with consolidated review due at 10.


## Church source acquisition and central roof study - October 30, 2026

Acquired full-campus 2024/2025 dated aerial references for both church sites and completed the Church on the Drive public LiDAR cache. A separate connected two-plane sanctuary study passed independent source/CPU and actual1920x1080 central-roof visual review. Full-building adoption is rejected: east-end articulation, wall/overhang positions, lower wings and exact legacy supersession remain unresolved. The owned isolated render exited normally; no active scene/editor changes. [Actual image, review and remaining construction work](LANDMARK_RECONSTRUCTION.md#latest-bounded-building-work--october-30-2026). This advances existing building tickets without claiming facade or whole-ticket completion.
