# Princeton–Edgewater showcase delivery plan

Created October 28, 2026. Parent roadmap: [#14](https://github.com/ajoiventures/TWIN/issues/14). Goal: finish a recognizable, evidence-backed Princeton–Edgewater scene that withstands close visual review and runs smoothly for a conference presentation, then expand the accepted approach along College Park Main Street.

The [consolidated execution overview](DELIVERY_PLAN.md) records the current reuse audit, critical path and efficiency rules. This document remains the detailed WQ acceptance breakdown; it does not compete with or replace the full ticket scope.

## Starting condition and scope

The current scene is a GIS prototype with illustrative details. Buildings include simplified masses, missing redevelopment forms and generic façades/roofs. Streets use approximate widths and sidewalks with incomplete intersection detail. Vegetation, parking and ground detail remain illustrative. Lighting and the tilt-shift camera have not passed a final rendered review. Source connections, authored settings and passing automated checks do not prove visual readiness.

Freeze a named showcase boundary containing all four Princeton–Edgewater corners, the approaches visible in the presentation cameras and one continuous adjoining Main Street block. Capture its exact polygon, date and five camera transforms before detailed production. Include nearby Princeton/Wellesley redevelopment components where visible; list any excluded skyline dependencies. Keep the full district available as context, but do not spread finishing effort across the district before the showcase passes.

## Work packages mapped to existing tickets

Local WQ IDs below are subtasks, not additional GitHub issue numbers. All are planned or in progress; none is marked complete by this document.

| Stage / priority | Ticket ownership | Concrete work and deliverables | Dependency / acceptance gate |
|---|---|---|---|
| WQ-01 · P0 · Freeze reference and baseline | #5/#8/#20/#25; GIS Analyst + Reference Artist | Showcase polygon, existing-condition reference date, per-property/reference register, five baseline captures, named visible defects and missing-source queue. Match overall, intersection, sidewalk, storefront and evening camera coverage. | First gate: sources are dated and eligible for intended use; current versus historical/proposed evidence is explicit. Missing measurements remain gaps. |
| WQ-02 · P0 · Correct building forms | #3/#6; Building Reconstruction Engineer | Replace obsolete redevelopment masses; verify apartment/condo grouping, stepped roofs, podium/garage, courtyards and heights. Prioritize Princeton and Wellesley where visible. Preserve stable identity, component confidence, provenance and rollback. | WQ-01. Plan-view and oblique comparison proves the correct forms; do not extrude tax parcels or assign unit-floor counts to whole buildings. |
| WQ-03 · P0 · Rebuild intersection and block | #15/#16/#17/#25; Transportation GIS + Civil/3D Engineer | Source-referenced road/sidewalk edges, lane/turn-pocket layout, markings, crossings/stop bars, curb returns, ramps, driveways, parking and signal positions. Deliver dimensional/source register and join/clearance exception report. | WQ-01; coordinate with WQ-02. Review all four corners and approaches against dated records. Generic buffers or a close centerline match do not pass this gate. |
| WQ-04 · P1 · Recognizable façades and roofs | #8/#18; Building/Environment Artist | Building-specific façade proportions, upper-floor windows, balconies where evidenced, doors, shopfront glazing, awnings, parapets and roof equipment. Use licensed/original textures and assets; distinguish verified tenant signs from unknown/generic signs. | Accepted WQ-02 forms and WQ-03 frontage alignment. Street and oblique captures must show recognizable, correctly scaled buildings without repeated generic shopfronts. |
| WQ-05 · P1 · Realistic streetscape and landscape | #9/#10/#18; Environment Artist | Materials for asphalt/concrete/joints/curbs/parking, species-appropriate trees and palms, supported planting areas, cars, furniture and ground transitions. Deliver asset/rights register and placement checks. | WQ-03/#16. No floating wheels, trunks through roofs, blocked crossings/ramps/doors or unsupported claims of surveyed placement. Illustrative details stay labeled. |
| WQ-06 · P1 · Lighting and camera finish | #18; Lighting Artist | Balanced daylight, dusk/night, correctly scaled streetlights, contact shadows/reflections, consistent texture scale and exposure. Main Street tilt-shift composition has readable focus and restrained depth of field; retain a sharp review camera. | WQ-04/WQ-05. Inspect actual renders at delivery resolution. Blur must not hide geometry defects; a saved preset does not pass. Existing/future lighting remains separate. |
| WQ-07 · P0 release gate · Independent visual review | #13; Independent QA + GIS/3D Leads | Same-camera before/after captures, dated-reference comparisons and defect register. Review building forms/façades, intersection/sidewalks, surface masks, tree/car/pole placement, lighting and framing. Fix blockers and major visible defects; document remaining limitations. | WQ-02 through WQ-06. Reviewer findings resolved and captures attached. Tests are supporting evidence, not a substitute for on-screen review. Human presentation sign-off remains required. |
| WQ-08 · P0 release gate · Conference package, then rollout | #13/#14; Technical Lead + PM | Fresh-launch/reload check; useful opening camera; readable controls; fixed presentation camera route; hardware/resolution, median and slow-frame measurements, RAM/VRAM and quality settings; versioned demonstrable scene and asset manifest. | WQ-07. Existing 1080p/30 FPS median target must be measured, with slow frames and memory reported; additional conference resolution needs its own run. Expand block by block only after showcase acceptance. |

## Delivery sequence and capacity

Milestone A: WQ-01 reference/baseline accepted. Milestone B: WQ-02 and WQ-03 form/road accuracy accepted. Milestone C: WQ-04–06 visual finish rendered. Milestone D: WQ-07–08 independent review and conference acceptance. Wider Main Street finishing starts after Milestone D; retain the full district context throughout.

Four agent slots are available: primary integration/coordination, up to two implementation workstreams, one independent reviewer. Suggested bounded parallel work is buildings versus transportation after reference freeze, then façades versus landscape after geometry acceptance. PM schedules 70–80% of assessed implementation capacity, retaining the rest for integration/review fixes; this is a planning allowance, not a claim of measured throughput. Role names are not continuously running agents. No delivery date or fixed effort estimate is promised before source access and a first finished sample establish actual capacity. Extra cosmetic variants are stretch work; required scope remains tracked.

## Defect and sign-off rules

- Blocker: missing/incorrect showcase building, wrong road topology, inaccessible scene, broken assets, or source/status misrepresentation. Must be resolved before a demo-readiness claim.
- Major: visibly generic/wrong façade, floating/intersecting object, incorrect crossing/corner, unreadable exposure or distracting rendering artifact in a fixed presentation view. Resolve before visual sign-off; unresolved findings stay open and prevent that gate from passing.
- Minor: small secondary visual defects outside the focal views. Record owner, proposed fix and reviewer disposition; do not silently delete them from scope.
- Every gate links the exact snapshot/scene version, sources, render captures, checks and reviewer findings. Keep a sharp plan/oblique view alongside the presentation view so artistic focus does not conceal inaccuracies.
- PM tracks progress and dependencies; Delivery Director reviews evidence and integration; VP/Sponsor reviews major scope/resource recommendations. Human owner decides presentation acceptance, spending and publication.

## Evidence already available and still pending

Existing references: `TRANSPORTATION_DOCUMENT_PLAN.md`, `PRINCETON_EDGEWATER_REVIEW.md`, `MULTIFAMILY_REVIEW.md`, `WELLESLEY_CORRECTION.md` and `EXECUTION_STATUS.md`. These support scoped work; they do not prove the showcase finished. Accurate road/as-built sheets, completed property-specific visual reconstruction, final rendered comparisons and conference performance acceptance remain open. The three added palms are illustrative and do not complete landscape accuracy.
