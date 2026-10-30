# Frozen-pilot dated aerial review

October29,2026 implementation for #20. This completes the observation ledger and discrepancy/review outputs for the frozen pilot; it does not accept imagery for measured modeling or complete downstream A-01–A-08 production gates.

The original January2022, January2024 and January2025 OCPA API-export JPEGs were actually viewed. Source acquisition months come from descriptive OCPA metadata, not service modification or model reference dates. Exact flight days, native GSD, positional accuracy and an affirmative redistribution/AI-use license remain unknown. Export access is observed; native/download reuse is not inferred. Original files remain in ignored local imagery storage; no source pixels are committed, copied to model textures or redistributed.

The frozen endpoints remain W Princeton Street and the southern W Smith Street intersection,85.44m of Edgewater. Reference date2026-10-28 is a model baseline, not aerial capture. A 60m review buffer is not right-of-way. The current pilot definition's actual geographic context matches the older imagery request; every sheet uses the actual returned EPSG2236 extent (US survey feet), not the narrower requested bbox. Export sampling is approximately0.178m/pixel, not a sensor accuracy claim.

## Review census and observations

All21 frozen parcel-linked candidate groups were assessed, and an independent intersection census of ALL source footprints found one additional physical-context group: Wellesley Building_2939, source key292214147406110:1. That group was omitted by the parcel-link queue; it is now reviewed without changing the frozen21IDs. All17 source groups physically intersecting the context are covered by the22-row ledger. Source groups are not automatically independent physical buildings.

Twelve source groups are entirely in the image frame, six are partial, and four lie wholly outside the cached frame. The four outside-frame linked groups are explicit source/frame exceptions with no visual roof/change conclusion. Partial-frame observations do not certify hidden edges. Original older-snapshot aliases remain in their historical queue; current rows are guarded by source parcel string, building number and exact footprint object-ID membership, not an assumed alias offset.

Eight adjacent review sectors cover both sides of the frozen85.44m centerline continuously. Their orange lines are20-US-foot centerline-offset review locators, not observed curbs. The ledger separately records visible crossings/frontages and parked-vehicle, tree, roof-shadow and corner occlusions. No curb width/grade, ramp, ADA, hidden driveway or public-access claim is made.

Several western roofs are weathered/darker in2022 and brighter in2024/2025. These are surface-appearance change candidates, not confirmed additions, construction dates, material specifications or measured height changes. No unambiguous new footprint extension was established from the three exports. Long eastern roof sections, rear parking, marked bays, planted corners and canopy were reviewed; varying parked cars are not evidence of parking capacity or changed legal access. Wellesley's courtyard remains distinguished from ground-level access, condo-unit geometry and the separately evidenced historical model correction.

## Delivered artifacts

Run `python tools/complete_pilot_aerial_review.py`; this uses only existing local evidence and performs no network requests.

- `config/pilot_aerial_observations.json`: explicit per-source-group observations and frontage findings.
- `data/imagery/pilot_complete/review.json`: source/date/schema/first-five-row packet, all22 building observations, eight frontage observations, frame coverage, original/active snapshot distinction, source-ID guards, A-01–A-08 dispositions and unresolved results.
- `review.geojson`: WGS84 review features linked to parcel/building/source IDs. Footprint geometry comes from OCPA source geometry; frontage geometry is an explicitly schematic review locator. Neither is promoted aerial tracing.
- `references.html`: dated local reference sheets with source-vector/record overlays. It links the original local JPEGs, not copied pixels.
- `coverage.html`: pixel-free map showing actual image frame, partial coverage and out-of-frame source groups.
- `scene/pilot_aerial_review.usda`: optional default-invisible review curves, no aerial pixels, no geometry or property-link promotion. It does not change the base, active root, manual layers or scenarios.
- `web/aerial-review.html`: date switching, source/observation inspector, all-building census, continuous frontage ledger and explicit remaining gates.
- [Committed safe review summary](evidence/pilot-aerial-review-summary.json): actual observations, provenance, source schemas, coverage and output checksums; no aerial imagery.

The normalized packet has a separate SHA256 receipt and source/output dependencies. `validate_review()` rejects stale snapshot, changed source images/metadata/source geometry, packet-only edits and modified outputs. Rebuilds reject manually changed generated files and keep a timestamped backup of the previous artifact bundle. The source images and original unreviewed queue are read-only. There are30 review-curve prims,22 unique guarded source keys and no unreviewed source group in the actual pilot context. Frontage sectors were checked for gaps/overlaps. JavaScript syntax and serialized default visibility were verified.

## Integration and remaining gates

Implemented local routes: `/api/v1/pilot_aerial_review` returns `complete_pilot_aerial_review.validate_review(ROOT)`; `/aerial-review` serves the page; `/aerial-review/coverage` serves the validated pixel-free coverage map; `/aerial-review/reference/2022`, `/2024`, `/2025` serve only the corresponding packet-listed, checksummed original local JPEG after validation. Restrict these images to the local review application. Optional scene composition must preserve its invisible default and existing root/manual opinions.

The existing [A-01–A-08 production breakdown](MAIN_STREET_GROUND_AND_CANOPY.md#aerial-driven-production-breakdown) is preserved. Independent surveyed ground controls, ground-registration residuals and a task-specific modeling tolerance are still unresolved: the review establishes frame arithmetic and qualitative discrepancies, not positional acceptance. Rear hardscape, roof/ground reconciliation, parking, canopy, street-facing architecture, matched model renders and full Main Street replication retain their separate gates. This review does not infer facades, current tenants or surveyed heights from overhead images, and never reads restricted canopy or private BOOMS data.

## Integrated local-review acceptance checkpoint

October29,2026. The integrator applied the guarded optional activation after independent PM review of the actual three dated images,22 source keys,17 intersecting source-context groups, frame fractions and eight frontage sectors. The activation backup is `data/imagery/pilot_complete/activation_backups/20261029T003259536743Z`. A separate read-only check confirmed that root opinions other than the added sublayer are identical, original sublayer order is preserved, the manual-layer checksum is unchanged, and aerial/FEMA/water contexts remain composed but invisible.

The integrator inspected the actual browser display using normal image elements with aligned SVG locators. Original2025 and2024 photographs are visible; date switching, Wellesley source selection, cyan footprint locators and orange frontage sectors work. No aerial source pixels are committed. The optional source layer contains full per-building source-key/parcel/object-ID/date/quality metadata for the native inspector; the integrator directly ran the inspector formatter on the composed Wellesley review prim and verified its source key, exact object IDs, three dated acquisitions, unknown assigned parcel, quality and observations. Interactive native control acceptance remains in open ticket #12.

[Acceptance evidence](evidence/pilot-aerial-review-acceptance.json) records independent preservation checks and distinguishes the PM's independent observation review from the author's implementation checks. Activation adds reference-locator curves only. It does not accept imagery for surveyed modeling, resolve occluded boundaries or complete the separately preserved A-01–A-08 production gates.
