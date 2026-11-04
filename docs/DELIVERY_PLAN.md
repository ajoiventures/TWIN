# Consolidated delivery plan: accuracy, realism and efficient reuse

## Project scope clarification

The project is the **College Park digital twin**, with **all of College Park Main Street / the Edgewater Drive corridor** as the primary detailed area and the wider College Park neighborhood as context. **Princeton–Edgewater is one component and priority work area within that project.** It is not a replacement for the full project, and completing its showcase cannot complete the overall goal.

All district-wide building, multifamily, street/sidewalk, landscape, lighting, source/API, scenario and release requirements remain in scope. A phased showcase is a way to validate a repeatable method; PM must retain corridor-wide work and coverage/acceptance tracking, including the parts not visible from Princeton–Edgewater.

Reviewed October 28, 2026 against the working tree, active snapshot `20261028T160543372334Z`, composed layer list and local source/validation reports. Parent ticket: [#14](https://github.com/ajoiventures/TWIN/issues/14). This is the execution overview; [the detailed showcase packages](PRINCETON_EDGEWATER_SHOWCASE_PLAN.md) retain their acceptance requirements. Full original project scope remains in [TICKET_PLAN.md](../TICKET_PLAN.md).

## Accepted ticket checkpoint — October 29, 2026 UTC

**7 completed existing tickets / 24 open:** #1, #2, #12, #19, #20, #23 and #24. Ticket #12 closed after pushed `4ac7210`; its [independent criterion matrix](evidence/native-ticket12-review.json) accepts native provenance/visibility controls, changed-layer apply/undo/restart recovery and explicit unavailable-input errors with successful Retry. All 62 protected physical files remained unchanged. This accepts workspace controls, not physical-model accuracy or completion of dependent tickets.

**Next consolidated review: 10 completed existing tickets**, three further completions. Keep the five-ticket cadence; partial source packets, building proposals and small edits do not advance the completed-ticket counter. Existing full-corridor and neighborhood requirements remain active. Pending mobility source/browser work is separate from the accepted native-controls batch.

## Outcome and production rule

Run district-wide building completeness and block correction in parallel with the Princeton–Edgewater showcase. Use it to establish finished-detail standards without making one building a prerequisite for correcting the rest of Main Street. Accurate forms, building-specific detail, credible materials/assets and finished lighting must work together. A finished showcase does not mean the wider twin is complete. The [repeatable missing-building process](EDGEWATER_PROPERTY_AUDIT.md#repeatable-missing-building-process--full-project) covers all building types, missing upper floors and areas outside the extraction.

Five required outcomes map directly to the existing work packages: physical accuracy (WQ-01–03), recognizable buildings (WQ-04), materials/assets (WQ-05), presentation (WQ-06), actual rendered review and conference playback (WQ-07–08). All still require gate evidence; planning does not complete them.

## Reuse audit: retain, finish or replace

| Previous work inspected | Reuse decision | Required next work / limitation |
|---|---|---|
| Official snapshot/API, source-based identity and parcel review | Retain the shared data foundation; avoid a new app/data stack | Use targeted exception resolution and freshness checks. Exact identity does not establish current geometry. |
| Full City Main Street boundary and expanded extraction | Retain the existing full coverage and context | Freeze a precise showcase polygon/camera baseline; do not mistake area coverage for feature accuracy. |
| Wellesley correction and historical height evidence | Retain reviewed component work and source guards | Check actual rendered appearance, podium/roof details and source dates; do not restart the massing from generic boxes. |
| Princeton historical reconstruction | Reviewed and integrated as `princeton_correction.usda`; retain bounded evidence and component register | Actual rendered review confirms composition, but façades/materials and current-condition verification remain incomplete. Preserve courtyard and partial legacy fragment guards. |
| Multifamily inventory and 624/520 W Princeton identity investigation | Reuse bounded records, dated photos and upper-story/source-index findings | Evidence tools and API review are committed. Resolve physical location/components before geometry promotion; do not count unit parcels as buildings. |
| Transportation research and centerline comparison | Reuse project IDs, exact document pages and quantified alignment findings | Obtain accepted existing/as-built Princeton sheets; replace only unsupported road/sidewalk geometry. Centerline agreement does not prove road width. |
| Six original DEM tiles, full valid-pixel coverage | Reuse cached original rasters/receipts/unit QA | Terrain mesh, vertical origin and object anchoring remain open; downloaded terrain is not integrated terrain. |
| Original tree/palm/car assets, material generators and instancing | Audit quality in fixed views and reuse acceptable assets | Improve or replace only visibly inadequate components; validate scale, rights and placement. Three palms are illustrative, not an inventory or landscape sign-off. |
| Additive layers, manual-edit separation and display guard | Retain reversible composition and recovery | Refresh dependent guards/registries after geometry changes; do not overwrite manual work. |
| Camera/light presets and validation tools | Reuse as starting settings and numerical checks | Actual tilt-shift/day/evening rendering and performance acceptance remain pending. Latest inspected scene report has 3,216 source groups, 18 layers and zero profile errors, not visual acceptance. |

## Ordered production batches and exit evidence

| Batch | Work, existing tickets and owner | Exit evidence before proceeding |
|---|---|---|
| A · Reference and baseline (P0) | GIS/Reference Analyst; #5/#8/#20/#25. Freeze all four corners, visible approaches and an adjoining block; record reference date, source status/rights, five camera transforms and a visible-defect list. | Exact showcase polygon, property/frontage list, source register and five actual baseline captures. Missing engineering records have explicit acquisition actions. |
| B · Physical correction (P0) | Building Reconstruction Engineer and Civil/3D Engineer; #3/#6/#15/#16/#17. Finish Princeton integration and nearby multifamily identity/component problems; correct road edges, turn pockets, crossings, sidewalks and corners from accepted evidence. | Plan and sharp oblique comparisons, source-linked dimensions and unresolved areas, correct courtyards/components, no obsolete duplicate masses. Existing and future scenarios remain separate. |
| C · Recognizable frontage (P1) | Environment/Building Artist; #8/#18. Finish one representative building façade/roof completely using actual proportions, window patterns, evidenced balconies, entrances, shopfronts and materials. Apply the proven method to other showcase buildings. | Close and aerial renders compared with eligible dated references; no repeated generic façade pretending to be a real property. Unknown signs/details remain explicit. |
| D · Surfaces and assets (P1) | Environment Artist; #9/#10/#18. Finish pavement, curb/joint and ground transitions; reuse or upgrade trees, palms, cars, furniture and lights to a consistent scale. | Placement/overlap checks and actual captures: no blocked crossings, ramps or doors, floating wheels, trees through roofs or inappropriate surface masks. Unverified locations remain illustrative. |
| E · Lighting and camera (P1) | Lighting Artist; #18. Tune daylight and evening exposure, contact shadows/reflections, fixture distributions where evidenced and restrained depth of field. | Actual delivery-resolution renders from presentation and sharp review cameras; focal areas readable, no blur concealing defects. Clearly separate measured fixture data from artistic settings. |
| F · Visual review and conference delivery (release gate) | Independent QA with GIS/3D Leads; #13/#14. Compare the same views against references, fix blockers/major defects, verify fresh launch/reload and benchmark the presentation route. | Scene/snapshot version, five comparisons, defect disposition, source/asset manifest and measured resolution/frame-time/RAM/VRAM report. Existing 1080p/30 FPS median target is measured, not assumed; include slow-frame behavior. Human presentation sign-off required. |
| G · Main Street rollout | PM + technical leads; existing corridor tickets. Repeat accepted building/block production units along the full district. | Each block has its own date/evidence and visual acceptance. Retain the full extraction and unresolved queue; do not extrapolate showcase accuracy across the district. |

## Efficiency rules that preserve quality

- Use existing tickets as the work ledger; WQ/batch IDs are subtasks, not duplicate GitHub issues. One PM overview links specialist evidence. Do not append competing master plans or call a checklist a completed delivery.
- Current owner instruction: prioritize completion through parallel ticket work, then consolidate review after each five completed tickets. Use four slots for integration and bounded builders during construction; assign a separate reviewer at the batch boundary. A builder cannot independently approve its own output. Necessary local source/geometry checks continue. Partial features do not count as completed tickets, and one reference building must not delay corridor-wide correction.
- Separate data refresh, geometry correction, material/asset changes and camera changes. Camera/material work should not reacquire government data or regenerate every building. Change only affected layers and dependent reports; rebuild the broader chain only when dependencies actually change.
- Reuse cached public data with checksums and known fetch dates. Use the newest applicable official approved/adopted revision after checking publisher amendments. Preserve older measurements as historical; newer proposed designs never overwrite existing conditions. Current TIP context is the September 2026 amendment; TIP pages are not roadway geometry.
- Keep source-based identities stable even when generated Building_N aliases change. Source corrections require explicit lineage and supersession; do not silently promote spatial links, move sketches or copy parcel story counts to every component.
- Use a small deterministic preview for each change, compare the same camera and resolve the next visible defect. Run appropriate source/geometry checks when relevant. Full-scene validation and conference-resolution performance remain mandatory at integration/release gates.
- Reuse instancing, local detail levels and material libraries; spend geometry/texture budgets where fixed presentation views reveal them. Optimization may reduce hidden/remote detail, but must not remove required visible accuracy or substitute blur for reconstruction.
- Commit and review each coherent accepted batch. Keep pending/uncommitted specialist work explicitly separate until checked; preserve ignored raw/private/imagery data, source rights, rollback and manual layers. No automatic merge, external outreach or spending is implied.

## Critical path and immediate dispatch

A → B → C/D → E → F → G. Source acquisition #25 is a prerequisite for accepting road dimensions; it does not prevent independent building evidence work or baseline capture. If a source is unavailable, retain the specific gap and continue an independent ready package. Do not mark the whole project blocked while useful work is available.

Current dispatch: run the all-building exception process across Main Street and the neighborhood coverage ledger; correct ready building forms by block; progress continuous sidewalks, roads/rear paving and district asset quality in parallel. Retain Princeton, Wellesley and 1615 office work as reusable methods and historical corrections. Obtain applicable engineering/as-built evidence without holding unrelated ready work. Consolidate independent review after five completed tickets; unresolved properties retain specific evidence gaps and do not stop the corridor. Use observed throughput for delivery estimates.

## Remaining original scope

This sequence prioritizes the showcase without cancelling the wider ticket plan: corridor transportation/ADA and terrain, OCPA/property lineage, business/reference verification, proposed Complete Street scenarios, water/flood/context layers, source/semantic validation, and the scoped NVIDIA reconstruction/query/video/simulation feasibility tracks remain tracked in their original issues (#1–#30 and #32 as applicable). Advanced features must not consume the geometry/visual critical path or be represented as deployed merely because a vendor blueprint exists.

## Management and reporting

Use the [full-project team and four-slot execution model](AI_TEAM_MANAGEMENT.md#full-project-delivery-team--current-operating-model): primary integrator, two independent builders and one independent reviewer. PM/Director/VP remain separate authority levels with decisions at batch/milestone boundaries, not mandatory per-change handoffs. Shared evidence, incremental rebuilds, exclusive file ownership and one backlog reduce duplicate effort. Track accepted coverage and observed cycle/rework time; preserve all original accuracy, visual and release gates.

PM records each package's owner, readiness/dependency, current artifact, open findings and next action. Delivery Director resolves sequencing/integration; technical leads accept domain evidence; independent QA reviews actual results; VP/Sponsor handles major scope/resource recommendations. Human owner retains presentation/publication/spending decisions. Update the living index, ticket evidence and execution checkpoint at each batch boundary. Report implemented, integrated, visually reviewed and accepted as separate states. No unattended monitoring or perpetual agent staffing is claimed.


## Next execution batch - October 29, 2026

Starting from 7 accepted tickets and 24 open. Next consolidated review is at 10 completed existing tickets; partial source or visual work does not advance that count.

| Track | Existing tickets | Next concrete delivery | Acceptance gate |
|---|---|---|---|
| Pedestrian evidence | #16, #25 | Acquire/reconcile available official sidewalk, ramp, crossing and existing-condition engineering records; retain exact missing artifacts | Source dates, coverage, coordinates and current/proposed distinction verified |
| Street geometry | #17, #18 | Correct supported road edges, sidewalk continuity, crossings and parking interruptions, beginning at Princeton-Edgewater and extending along Main Street | Reference comparison and actual plan/street renders; no generic buffer represented as measured sidewalk |
| Realistic buildings | #6, #8, #11, #32 | Reuse property-linked roof and frontage work; finish recognizable roofs, stepped forms, windows, storefronts, balconies, entrances and materials across Main Street | Compare fixed sharp views with address-verified dated references; resolve missing upper floors, identity conflicts and visible mesh defects before activation |
| Trees and cars | #9, #10 | Reuse existing detailed assets in a separate improved proposal; resolve scale, variety, materials and placement | Same-camera before/after review, walking-path clearance, asset rights and performance |
| Transportation integration | #15 | Finish pending parking/mobility map, source fields and first-five previews | Actual browser check and refreshed independent packet/integration review; unknown capacity/access/demand remain explicit |

Root integrates and coordinates renders; GIS analyst owns pedestrian-source acquisition; the asset builder owns separate tree/car proposals. Independent review follows implementation with no self-approval. No new tickets are created. Full College Park/Main Street scope remains intact; Princeton-Edgewater is one component. Preserve the active user editor and all pending work.


### Building realism included in this batch

Owner explicitly added realistic buildings on October 29. Building work proceeds alongside streets and assets. Prioritize recognizable Main Street landmarks and verified missing upper floors, then repeat the method by frontage/block across the district. Wellesley, Princeton, the 1615 office, churches and post office stay in the shared full-project queue; no single unresolved landmark blocks ready buildings elsewhere.

Reuse the existing Wellesley architecture, office frontage/brick/roof, retail block, landmark reconstruction and property-lineage tools. First inspect the actual composed result and the latest rejection records. Office frontage is photo-interpreted; post-office frontage still lacks an accepted address-specific exterior reference; Princeton's failed roof proposal stays rejected. Do not re-run or activate these scripts simply because they exist.

For each ready building: establish physical identity and reference date; correct supported mass/roof and floor count; add actual opening/storefront/balcony/entrance patterns and suitable materials; inspect sharp same-camera before/after images and source fit; integrate the accepted layer with provenance and rollback. Record unsupported dimensions as estimates. Generic window grids or attractive materials alone do not establish architectural accuracy. Whole-ticket closure still requires the original coverage, source and visual acceptance scope.
