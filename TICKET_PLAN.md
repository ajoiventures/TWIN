# College Park digital twin — ticket plan

## Project scope clarification

The project is the **College Park digital twin**, with **all of College Park Main Street / the Edgewater Drive corridor** as the primary detailed area and the wider College Park neighborhood as context. **Princeton–Edgewater is one component and priority work area within that project.** It is not a replacement for the full project, and completing its showcase cannot complete the overall goal.

All district-wide building, multifamily, street/sidewalk, landscape, lighting, source/API, scenario and release requirements remain in scope. A phased showcase is a way to validate a repeatable method; PM must retain corridor-wide work and coverage/acceptance tracking, including the parts not visible from Princeton–Edgewater.

Created October 27, 2026 (America/New_York).

Latest GitHub check: October 30, 2026 — **7 completed / 24 open**. Completed existing tickets: #1, #2, #12, #19, #20, #23 and #24. The next consolidated review is at 10 completed tickets. The detailed specifications below retain their original scope; partial source packets and building corrections do not count as completed tickets. See [current execution evidence](docs/EXECUTION_STATUS.md).

Build an accurate, navigable digital twin of College Park, Orlando, beginning with Edgewater Drive. The current prototype has public footprint/street geometry and illustrative storefront, tree and vehicle detail. This roadmap replaces assumptions with traceable evidence and upgrades the visual assets.

## Delivery sequence

Expanded source-by-source work packages and delivery gates are in [Government Data Improvement Plan](docs/GOVERNMENT_DATA_PLAN.md), including USGS, Florida GIO, OCPA, City GIS/ADA, FDOT, NOAA, LYNX, County GIS and optional environmental context.

### 1. Establish clean data foundations

- [x] https://github.com/ajoiventures/TWIN/issues/1 — Create a portable, versioned Omniverse project baseline
- [x] https://github.com/ajoiventures/TWIN/issues/2 — Audit local BOOMS, parcel and map sources before integration
- [ ] https://github.com/ajoiventures/TWIN/issues/3 — Add cached OCPA parcel API ingestion and stable parcel-building links
- [ ] https://github.com/ajoiventures/TWIN/issues/4 — Build clean, documented City of Orlando Open Data and GIS adapters
- [ ] https://github.com/ajoiventures/TWIN/issues/5 — Align official district boundaries and a linked 2D parcel map with the 3D twin

### 2. Improve accuracy and visual assets

- [ ] https://github.com/ajoiventures/TWIN/issues/6 — Replace uniform heights and flat ground with evidence-based geometry
- [ ] https://github.com/ajoiventures/TWIN/issues/7 — Connect approved BOOMS property, vacancy and business context to scene objects
- [ ] https://github.com/ajoiventures/TWIN/issues/8 — Build a verified Edgewater storefront reference and asset register
- [ ] https://github.com/ajoiventures/TWIN/issues/9 — Replace simplified trees with detailed oak and palm assets
- [ ] https://github.com/ajoiventures/TWIN/issues/10 — Replace box vehicles with realistic parked car models and valid parking

### 3. Deliver and verify a realistic pilot block

- [ ] https://github.com/ajoiventures/TWIN/issues/11 — Model a verified pilot block of storefronts and pedestrian streetscape
- [x] https://github.com/ajoiventures/TWIN/issues/12 — Add provenance, accuracy filters and dependable scene refresh controls
- [ ] https://github.com/ajoiventures/TWIN/issues/13 — Verify geographic accuracy, visual realism and laptop performance before release

## Definition of done

Commercial verification now includes [#32 — broker/listing evidence and affected model status](https://github.com/ajoiventures/TWIN/issues/32). Start with the Wellesley missing-story case and other multi-story/mixed-use Main Street properties. Record source/date and sale/lease scope separately from occupancy; never apply a retail-component listing to an entire condo tower. See [official focus-area evidence](docs/STUDY_SCOPE.md) and [Wellesley reference](docs/WELLESLEY_REFERENCE.md).

- Official Orlando Open Data, city GIS and OCPA integrations have documented schemas, stable identifiers, dated local snapshots and quality checks.
- Approved BOOMS context links to the correct parcels/buildings; unknown, stale, estimated and illustrative content remains distinguishable.
- One reviewed Edgewater pilot block has referenced storefronts, detailed vegetation and vehicles, plausible parking and pedestrian space.
- Source/asset rights and data-release status are recorded; manual edits survive refresh.
- Geographic, visual and performance acceptance evidence is attached to the verification ticket.

## Primary references

- [City of Orlando Open Data](https://data.cityoforlando.net/en/)
- [Orlando GIS downloads](https://www.orlando.gov/Our-Government/Records-and-Documents/Map-Library/GIS-Data-Download)
- [Orlando Permit Applications dataset](https://data.cityoforlando.net/Permitting/Permit-Applications/ryhf-m453/data)
- [Official OCPA parcel service](https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4)
- [BOOMS overview from Main Street America](https://mainstreet.org/resources/knowledge-hub/topics/real-estate-and-property-development)

This is a sequenced ticket plan. Open tickets do not imply those improvements are implemented or verified.

## Ticket specifications

The transportation and sidewalk workstream is detailed in [TRANSPORTATION_PLAN.md](docs/TRANSPORTATION_PLAN.md): [transportation sources #15](https://github.com/ajoiventures/TWIN/issues/15), [pedestrian GIS #16](https://github.com/ajoiventures/TWIN/issues/16), [accurate block geometry #17](https://github.com/ajoiventures/TWIN/issues/17), and [street visuals and placement #18](https://github.com/ajoiventures/TWIN/issues/18). Final tree/vehicle placement and pilot-block sign-off now depend on these geometry checks.

### [TWIN-01: Create a portable, versioned Omniverse project baseline](https://github.com/ajoiventures/TWIN/issues/1)

Priority: P0. Dependencies: None.

Bring the existing College Park prototype and its generators into this repository with portable paths and reproducible setup.

- [ ] Separate source code, generated scenes, licensed assets, and private/local data. Do not commit machine runtimes, logs, secrets, or raw BOOMS/BTR exports.
- [ ] Replace hard-coded workstation paths with configuration or project-relative paths; document supported Kit and Python dependencies.
- [ ] Preserve the original base scene and keep source geometry, illustrative details, manual edits, and scenarios in separate USD layers.
- [ ] A clean checkout can run a documented small sample build and open it in the supported Kit installation; record baseline startup time, frame rate, RAM and VRAM.

Deliverables: Project structure, setup guide, dependency manifest, configuration, .gitignore, small redistributable sample.

### [TWIN-02: Audit local BOOMS, parcel and map sources before integration](https://github.com/ajoiventures/TWIN/issues/2)

Priority: P0. Dependencies: TWIN-01.

Inventory the existing local BOOMS program export, completion tracker, parcel spine, polygon snapshots and map outputs. Reuse existing refresh logic after review. Include the City of Orlando Open Data portal and city GIS catalog as first-class authoritative source candidates.

- [ ] Record schema, coverage, source URL, retrieval date, CRS, license/redistribution terms and release tier for each source.
- [ ] Reconcile differing raw export, normalized parcel and polygon counts, duplicate parcel IDs and invalid geometry; deliver an exception report.
- [ ] Document the BOOMS-to-parcel field mapping, including parcel_pin, cp_uid, num_floors, vacancy/use, last_edit_date and completion/release fields.
- [ ] Keep the source BTR project read-only. Preserve its held-2026-data and public-release gates; no raw private records or owner/contact notes enter this public repository.
- [ ] Distinguish the BOOMS inventory from its completion tracker and from live appraiser snapshots; do not assume a BOOMS API is available.

Deliverables: Source register, schema map, freshness report, reconciliation queue and publication field allowlist.

### [TWIN-03: Add cached OCPA parcel API ingestion and stable parcel-building links](https://github.com/ajoiventures/TWIN/issues/3)

Priority: P0. Dependencies: TWIN-02.

Use the official OCPA parcel service and existing building footprint geometry to build stable, traceable parcel/building relationships.

- [ ] Inspect the official parcel service schema and use bounded, paginated or object-ID-batched queries with retry, timeout and local cache behavior.
- [ ] Normalize parcel IDs as strings without dropping leading zeros; preserve source identifiers and retrieval timestamps.
- [ ] Model parcel-to-building relationships explicitly, including multiple buildings per parcel and condo/overlapping parcel cases; do not equate a parcel with a storefront.
- [ ] Produce matched, ambiguous and unmatched queues. Use address/spatial fallback only with recorded match method and confidence.
- [ ] Build and refresh from snapshots; the interactive/static map must not query public agency APIs on every render. Test missing fields, source outages and geometry updates.
- [ ] Document the OCPA adapter's interface so it can share identifiers, CRS, cache manifests and quality reports with the Orlando portal/GIS adapters.

Deliverables: OCPA adapter, snapshot manifest, normalized parcel/building tables and join QA report.

### [TWIN-13: Build clean, documented City of Orlando Open Data and GIS adapters](https://github.com/ajoiventures/TWIN/issues/4)

Priority: P0. Dependencies: TWIN-02.

Create a consistent ingestion interface for the official City of Orlando data portal and GIS catalog, aligned with the OCPA parcel adapter.

- [ ] Inventory relevant official portal/GIS datasets for addresses, parcels/buildings, boundaries, zoning, permits, business records, streets, tree inventory and elevation; verify actual availability rather than assuming every dataset exists.
- [ ] For each selected dataset record publisher, stable dataset/service ID, API URL, metadata URL, pagination, auth/rate limits, update frequency, CRS, units, license and retrieval date.
- [ ] Normalize source IDs and preserve original IDs, source dates and geometry quality. Keep distinct address, parcel, building, business and permit entities.
- [ ] Provide a documented read-only ingestion API/adapter contract with bounded queries, pagination, retries/backoff, timeouts, schema checks, cached snapshots and incremental refresh where supported.
- [ ] Add offline fixtures and tests for schema changes, missing fields, duplicate features, swapped coordinates, invalid geometry, empty responses and service failure; produce a quality report rather than silently replacing good data.
- [ ] Expose only approved normalized fields to map/scene clients. Public/static views use snapshots, not agency calls per render; no keys or internal exports enter the public repo.

Deliverables: Official dataset catalog, Orlando portal and ArcGIS adapters, common data contract, fixture tests, cache manifests and API documentation.

### [TWIN-04: Align official district boundaries and a linked 2D parcel map with the 3D twin](https://github.com/ajoiventures/TWIN/issues/5)

Priority: P0. Dependencies: TWIN-03, TWIN-13.

Replace the rectangular study-area assumption with named, traceable boundary layers and a 2D/3D inspection map.

- [ ] Represent the College Park neighborhood, Main Street program boundary and Edgewater focus corridor as distinct geometries, each with source/date/status.
- [ ] Verify the local UTM origin, axis direction, horizontal CRS and units against at least ten distributed reference points; report residuals and the source-supported tolerance.
- [ ] Show parcel outlines, building footprints, streets and an appropriately licensed dated reference basemap; preserve attribution.
- [ ] Selecting a parcel or building highlights its counterpart in 2D and 3D, with stable IDs and a visible unmatched state.
- [ ] Keep proposed redesign geometry separate from existing-condition mapping; mark digitized/unapproved boundaries accordingly.

Deliverables: Boundary registry, reference-point alignment report and linked parcel map.

### [TWIN-05: Replace uniform heights and flat ground with evidence-based geometry](https://github.com/ajoiventures/TWIN/issues/6)

Priority: P1. Dependencies: TWIN-03, TWIN-04, TWIN-13.

Assess public elevation/LiDAR coverage and verified floor data, then improve building and terrain geometry without inventing precision.

- [ ] Inventory available elevation/LiDAR/height products, acquisition dates, resolution, licenses, coverage and vertical datums before selecting a source.
- [ ] Use bare-earth terrain for the ground and separate roof/building measurements; screen vegetation and outliers from roof height estimates.
- [ ] Assess OCPA STYS and BOOMS num_floors definitions and completeness before using them. A floor-derived height remains an estimate, not a measured elevation.
- [ ] Every height records its value, units, method, date, source and confidence; missing/conflicting records retain labeled fallbacks.
- [ ] Verify representative small shops, larger buildings and residential structures against reference evidence; document error and remaining gaps.

Deliverables: Elevation-source assessment, terrain/height pipeline, per-building confidence attributes and validation sample.

### [TWIN-06: Connect approved BOOMS property, vacancy and business context to scene objects](https://github.com/ajoiventures/TWIN/issues/7)

Priority: P1. Dependencies: TWIN-02, TWIN-03, TWIN-04.

Expose appropriate inventory context when users select a parcel or building, without treating parcel-level records as verified tenants or facades.

- [ ] Join through stable parcel/program identifiers and retain one-to-many buildings, businesses and spaces rather than copying one tenant onto every building.
- [ ] Show observation date, source, completion state, match confidence and unknown/stale states for occupancy and business information.
- [ ] Use a field allowlist; suppress owner/contact details, free-text notes and held records from public exports until existing source release gates are satisfied.
- [ ] Differentiate actual business identities, generic visual signs and historical records; conflicting tenants enter review.
- [ ] Provide tests for duplicate IDs, address/suite ambiguity, null vacancy fields and expired observations using synthetic/redacted fixtures.

Deliverables: BOOMS import mapping, object inspector, approved export schema and reconciliation report.

### [TWIN-07: Build a verified Edgewater storefront reference and asset register](https://github.com/ajoiventures/TWIN/issues/8)

Priority: P1. Dependencies: TWIN-04, TWIN-06.

Create a building-by-building reference set to replace generic facades with defensible current storefront details.

- [ ] Start with one continuous pilot block identified by parcel/building IDs; expand only after the reference workflow is reviewed.
- [ ] Record dated, permitted-to-use references for heights, rooflines, doors, glazing, awnings, signs, colors and entrances.
- [ ] Track capture/usage rights and attribution for photographs and textures; do not download or reuse restricted street imagery by assumption.
- [ ] Verify business identity and date separately from architectural appearance; preserve unknowns and avoid invented tenants.
- [ ] Record approximate dimensions and evidence confidence, and list missing reference work per property.

Deliverables: Pilot-block reference register, asset rights manifest, facade measurement sheets and review queue.

### [TWIN-08: Replace simplified trees with detailed oak and palm assets](https://github.com/ajoiventures/TWIN/issues/9)

Priority: P1. Dependencies: TWIN-01, TWIN-04.

Improve vegetation appearance with detailed trunks, branches and leaf canopies while keeping placement evidence and rendering cost explicit.

- [ ] Evaluate redistributable or user-licensed vegetation assets; record source, license, scale, species label and texture requirements before importing.
- [ ] Use detailed bark, branching, leaf materials, varied silhouettes, healthy scale variation and correct normals; remove visibly spherical/faceted prototype crowns.
- [ ] Use available tree inventory or dated references where feasible. Mark procedural tree positions as illustrative rather than surveyed.
- [ ] Check trunks against buildings, carriageways, water, entrances and accessible routes; allow overhead canopy only where appropriate.
- [ ] Provide instancing and at least three distance-detail levels. Verify close-up, sidewalk and aerial views for texture, transparency and shadow defects.

Deliverables: Vegetation asset library, placement rules, placement confidence layer and visual comparison captures.

### [TWIN-09: Replace box vehicles with realistic parked car models and valid parking](https://github.com/ajoiventures/TWIN/issues/10)

Priority: P1. Dependencies: TWIN-01, TWIN-04.

Add realistic static vehicles at plausible mapped parking locations, independent of any future traffic simulation.

- [ ] Select licensed passenger-car/SUV/van assets with believable bodywork, wheels, glass, lights and materials; record provenance and redistribution rights.
- [ ] Use real dimensions, ground contact, varied orientation/color and sufficient wheel/body detail at the closest camera.
- [ ] Derive allowed placement from verified curb spaces or parking areas; exclude travel lanes, intersections, crosswalks, entrances, sidewalks and buildings.
- [ ] Provide collision and clearance QA plus manual review of the pilot block; schematic current placements are not assumed valid.
- [ ] Use instancing or asset variants and distance-detail levels; label vehicles as static illustration, with no live-traffic claim.

Deliverables: Vehicle asset library, parking-placement layer, collision report and before/after street-level captures.

### [TWIN-10: Model a verified pilot block of storefronts and pedestrian streetscape](https://github.com/ajoiventures/TWIN/issues/11)

Priority: P1. Dependencies: TWIN-05, TWIN-07, TWIN-08, TWIN-09.

Deliver a coherent, recognizable pilot block along Edgewater before spreading facade generation across the district.

- [ ] Implement referenced rooflines, facade proportions, entrances, recessed glazing, awnings and signage with correct text orientation and physical scale.
- [ ] Model sidewalks, curbs, tree wells, crossings, lighting and furniture from evidence; keep accessibility and entrance clearances visible.
- [ ] Use physically plausible materials, texture scales, UVs, normals and contact shadows; verify grass, asphalt and concrete masks do not bleed into one another.
- [ ] Separate existing conditions from planned street-project scenarios. No future plan is silently presented as built.
- [ ] Review five fixed close/wide camera views against dated references and record accepted discrepancies; unresolved properties retain generic labels.

Deliverables: Pilot-block USD layer, material library, existing/planned scenario distinction and visual review checklist.

### [TWIN-11: Add provenance, accuracy filters and dependable scene refresh controls](https://github.com/ajoiventures/TWIN/issues/12)

Priority: P1. Dependencies: TWIN-04, TWIN-05, TWIN-06.

Help users distinguish observed, estimated, illustrative and proposed content while preserving manual edits across refreshes.

- [ ] Object inspection shows source, date, identifier, evidence quality and last refresh, with clear unknown/stale states.
- [ ] Add independent switches for parcel boundaries, data confidence, detailed storefronts, vegetation, vehicles and future scenarios.
- [ ] Refresh uses staged snapshots and layer replacement with a change report; manual edits and previous versions remain recoverable.
- [ ] Handle unavailable assets, interrupted downloads and missing datasets without silently producing a blank screen.
- [ ] Open with a visible useful camera, readable daylight and sensible clipping; prevent unintended selection outlines and camera changes from polluting source layers.

Deliverables: Provenance UI, layer controls, safe refresh workflow and recovery checks.

### [TWIN-12: Verify geographic accuracy, visual realism and laptop performance before release](https://github.com/ajoiventures/TWIN/issues/13)

Priority: P1. Dependencies: TWIN-08, TWIN-09, TWIN-10, TWIN-11.

Define a repeatable acceptance pass for the accurate, visually improved College Park twin.

- [ ] Report parcel/building/BOOMS match coverage, unresolved exceptions, reference-point residuals and height-quality coverage; no unexplained denominator changes.
- [ ] Check USD composition, missing assets, mesh topology, UVs, normals, mirrored signs, material boundaries, tree/vehicle collision and dated business labels.
- [ ] Capture the same street-level, sidewalk and aerial views for baseline and updated scenes; obtain a pilot-block review before broad rollout.
- [ ] Measure a declared 1080p camera route on the RTX 5070 Ti laptop with 12 GB VRAM. Initial target: 30 FPS median with adequate RAM/VRAM headroom; report measured results and tune detail levels if missed.
- [ ] Verify fresh launch, reopen, layer toggles, 2D/3D selection and data refresh. Document source limitations and license/redistribution status before a shareable build.

Deliverables: Acceptance report, comparison captures, performance measurements and release-ready manifest.


### Full Main Street extraction checkpoint (October 28, 2026)

Shared scope configuration now fully contains the official City College Park Main Street polygon. The rebuilt 3D ground has 100% area coverage and 0 m² uncovered; 3,216 building groups are composed. Wider neighborhood coverage is partial (60.77%). See `docs/STUDY_SCOPE.md` and `docs/EXECUTION_STATUS.md`. Remaining #5/#6/#17 acceptance includes current building completeness, missing redevelopment geometry, heights and accurate pedestrian infrastructure; spatial coverage alone does not close those tickets.

### Princeton / Edgewater conference focus

Prioritize #15/#16/#17/#18/#13 on the Princeton–Edgewater intersection. The source review finds close centerline agreement but generic widths and unverified sidewalk buffers; it does not accept the intersection geometry. Required correction and presentation gates: `docs/PRINCETON_EDGEWATER_REVIEW.md`.

### Multifamily accuracy workstream

Prioritize Princeton at College Park redevelopment geometry, then 624/520 W Princeton parcel/footprint mismatches and other apartment candidates. A bounded 557-record OCPA review separates apartments, small multifamily, condo unit records and mixed-use review; no unit-record count is presented as building or dwelling-unit count. Evidence: `docs/MULTIFAMILY_REVIEW.md`. #3/#6/#17 remain open pending physical geometry acceptance.

## Transportation engineering document work package

Prioritize #25 acquisition, then #15/#16 evidence extraction and #17 Princeton–Edgewater geometry. Verified official PDFs, exact page references, outstanding plan sets and acceptance gates are in [Transportation document plan](docs/TRANSPORTATION_DOCUMENT_PLAN.md). The April 2009 support plan explicitly describes the Princeton–Smith bike-lane exception; verify against dated existing conditions rather than repeating a generic corridor section. Proposed improvements remain separate under #21; final presentation review stays in #18/#13.

## Main Street street-lighting work package

Priority: P1; Princeton–Edgewater first, then the Main Street corridor. Responsible: Lighting/Environment Artist; accountable: 3D Technical Lead; source verification: Transportation GIS Analyst; independent review: QA Analyst. Dependencies: #25 engineering records, #16/#17 pedestrian geometry; implementation #18, proposed scenario #21, presentation acceptance #13.

- [ ] Inventory existing pole positions, fixture family, mounting/arm height, orientation and source/date from City/OUC plans or dated authorized references. Existing illustrative lamps are not an inventory.
- [ ] Obtain applicable lighting and photometric sheets, fixture schedules and manufacturer IES distributions where available; record lumens, color temperature, optics and uncertainty. Do not choose real-world specifications solely for appearance.
- [ ] Model correctly scaled poles, arms and fixtures; check placement against ramps, crossings, trees, parking and storefront entrances.
- [ ] Build daylight, dusk and night presets with controlled exposure, believable light falloff/contact shadows and restrained bloom. Label artistic settings separately from measured lighting data.
- [ ] Keep existing lighting and proposed Complete Street decorative lighting in separate switchable layers.
- [ ] Review Princeton intersection and sidewalk approach plus Main Street tilt-shift views. Check glare, tree occlusion, spill toward residences and performance at conference resolution. A rendered lighting review does not certify photometric compliance.

Official references: [OUC Development Services Guide](https://www.ouc.com/wp-content/uploads/2024/12/Development_Services_dev_guide.pdf), lighting discussion p.28; [OUC outdoor lighting](https://www.ouc.com/solutions-programs/business/outdoor-lighting/); [Orlando Engineering Standards Manual](https://www.orlando.gov/files/sharedassets/public/documents/engineering/platting/engineeringstandardsmanual.pdf); [Edgewater project](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project). These establish records/coordination leads, not verified existing fixture locations or a selected Main Street fixture. Downtown-only fixture guidance and unincorporated County rules must not be applied to College Park automatically. No utility request, purchase or installation is authorized or performed by this plan.

## Conference visual-quality acceptance — required, still pending

Focus: Princeton–Edgewater first, then all College Park Main Street. The final visual check is pending. Existing presentation settings and passing geometry/code tests do not establish realism.

- [ ] **Façades (#8/#18):** replace generic walls/shopfronts with evidence-referenced building-specific proportions, upper-floor windows, entrances, awnings, glazing, materials, signage and roof/parapet detail. Preserve verified heights and courtyard/component geometry. Record dated reference evidence and image/asset rights; retain unknown tenants/details as unknown.
- [ ] **Streets (#15/#16/#17/#18):** replace generic pavement/sidewalk buffers at Princeton–Edgewater with accepted road edges, turning lanes, crossing/stop-bar markings, curb returns, sidewalk corners, driveway/parking interfaces and signals. Add convincing surface/joint/material detail after alignment is validated.
- [ ] **Scene dressing (#9/#10/#18):** match supported tree/pole/furniture locations and vehicle scale/parking; remove floating, intersecting or obstructing placements. Label illustrative placements rather than claiming inventory accuracy.
- [ ] **Lighting/camera (#18):** verify the actual running Main Street tilt-shift camera, focus/depth of field, exposure, shadows, texture scale and dusk/night lighting on screen. A saved setting alone is not visual acceptance.
- [ ] **Final visual check (#13):** capture repeatable daylight aerial/tilt-shift, Princeton intersection, sidewalk, storefront and evening frames; compare with dated references and review visible errors independently. Provide captures plus a resolved/open defect list.
- [ ] **Conference readiness (#13):** test fresh launch/reload, useful opening view, legible presentation controls and actual presentation-resolution frame rate/memory. Record hardware, resolution and camera route; do not claim world-class or presentation-ready until accuracy and visual gates both pass.

Responsible: Environment Artist and Civil/3D Geometry Engineer; accountable: 3D Technical Lead; independent reviewer: QA Analyst; delivery coordinator: PM Agent. Work remains open until evidence and rendered captures satisfy these gates.

## Princeton–Edgewater showcase: sequenced delivery breakdown

The scene remains a GIS prototype; final visual readiness is unproven. Use [the showcase delivery plan](docs/PRINCETON_EDGEWATER_SHOWCASE_PLAN.md) as the detailed execution sequence for #14.

1. **WQ-01 / #5/#8/#20/#25:** freeze the exact showcase boundary, dated references, camera baseline and defect list.
2. **WQ-02 / #3/#6:** correct building/redevelopment forms, heights, roofs, garages and courtyards.
3. **WQ-03 / #15/#16/#17:** reconstruct Princeton–Edgewater roads, corners, sidewalks, crossings, parking and signals from accepted evidence.
4. **WQ-04 / #8/#18:** finish recognizable property-specific façades, shopfronts and roof details.
5. **WQ-05 / #9/#10/#18:** finish landscape, palms, cars, materials and clear placements.
6. **WQ-06 / #18:** finish and inspect daylight/evening lighting and the actual tilt-shift camera; retain sharp accuracy views.
7. **WQ-07 / #13:** independent same-camera visual review; resolve blockers and major visible defects.
8. **WQ-08 / #13/#14:** verify fresh launch, conference-resolution performance and human presentation sign-off; then replicate the accepted quality along Main Street.

No package is complete merely because this breakdown exists. Owners, dependencies, deliverables, review gates and four-agent capacity limits are specified in the linked plan. Existing, historical and proposed geometry remain separate.

## Living documentation and source recency

Use [docs/INDEX.md](docs/INDEX.md) as the starting point. Prefer the newest applicable official adopted/approved revision; track observation, document/revision, effective and retrieval/build dates separately. Preserve older sources as history and keep future designs separate from existing conditions. Update affected registers, tickets, provenance and checks after each implementation batch. MetroPlan FY27–31 amended September 9, 2026 now takes priority over the 2025 TIP for current program context; it is not an as-built geometry source.

## Consolidated execution and reuse review

Use [docs/DELIVERY_PLAN.md](docs/DELIVERY_PLAN.md) as the current execution overview, with the existing showcase work packages as its detailed subtasks. It audits reusable GIS, geometry, assets and tools; distinguishes integrated work from pending prototypes; defines the critical path and avoids duplicate tickets or unnecessary full rebuilds.

Required outcomes remain: correct physical scene → recognizable façades/roofs → consistent materials/assets → finished lighting/cameras → actual rendered comparison and conference playback. Finish and judge Princeton–Edgewater before replicating the standard along Main Street. Wider original scope remains tracked; no completion or visual-readiness claim is made by this planning update.
# Confirmed platform scope — October 28, 2026

The owner confirmed **both planning and live operations**. The existing [smart-city platform plan](docs/SMART_CITY_PLATFORM_PLAN.md#confirmed-dual-purpose-delivery-contract) now defines deliverables, AI role ownership and acceptance for both. Reuse the shared GIS/evidence/semantic scene foundation; extend #28 for recorded event replay and #29 for a separately accepted bounded live-feed pilot. Proposed, simulated, synthetic and observed data remain explicitly distinct. This adds acceptance scope to existing tickets rather than creating duplicate ingestion tickets; no live feed or NVIDIA server deployment is claimed.

## Parking feasibility gaps — October 28, 2026

The [parking evidence review and eight work packages](docs/PARKING_FEASIBILITY_REVIEW.md) add missing deliverables to #14/#15/#16/#17/#21/#25/#28/#29/#13: recover the final Orlando Main Street study and original counts; create a dated space-level inventory; verify public/shared garage access and accessible walking routes; measure demand/turnover and event peaks; compare construction and future-design impacts; assess shared-parking and capital alternatives with current costs; validate any occupancy feed; and independently reconcile findings. Existing illustrative cars are not measured occupancy. No parking deficit, garage feasibility or current capacity is established yet. AI role ownership, dependencies and acceptance are specified in the linked review.

P-01 fallback artifact is prepared: [unsent records-request brief](docs/PARKING_RECORDS_REQUEST_DRAFT.md). Acquisition remains open. P-02 also includes verified bike racks, scooter corrals and secure/cargo-bike facilities; the City's separate micromobility study must pass geographic coverage and existing/proposed status checks before its data is used for College Park.

## Parks, vacant/public land and zoning — October 28, 2026

[Source findings and L-01–L-07 work packages](docs/PARKS_PUBLIC_LAND_ZONING.md) extend #3/#4/#5/#13/#14/#17/#18/#20/#21/#22/#23/#25/#28. Acquire full-neighborhood park coverage and comprehensive public ownership; separately verify vacant land/buildings; reconcile parcel zoning, overlays, future land use and PD ordinances; produce reviewed residential/mixed/commercial/public/conservation breakdowns and model accepted park amenities. Current extraction yields eight park/recreation records and no local matches in the City's 61-record vacant inventory; neither result establishes complete neighborhood coverage or absence of City-owned land. `C` is conservation/water and `/T` is Traditional City, not commercial or townhouse. Exact source fields, clipped areas, ownership evidence and site constraints must remain distinct.

## Rear parking and tree-lined Main Street views

[MS-01–MS-07](docs/MAIN_STREET_GROUND_AND_CANOPY.md) add concrete corrections to #8/#9/#10/#13/#14/#15/#16/#17/#18: paved rear lots and islands; stalls/aisles/loading/driveways; storefront walking links; continuous evidence-backed canopy; recognizable façades at human height; sharp matched reference views; and full-corridor replication. Direct review of the January 2025 OCPA pilot aerial confirms substantial paved rear parking on both sides of Edgewater. Access rights, current capacity and hidden geometry remain unverified. Actual render review still shows procedural trees, blank façades and incomplete ground detail; tree color/tilt-shift changes do not satisfy visual acceptance.

The same document now includes **A-01–A-08 aerial-driven production**: validate returned image extent and ground-control alignment; map supported surfaces; reconcile roof/ground/building/access geometry; add parking detail; rebuild canopy; finish street-facing façades from additional references; compare actual fixed-view renders; replicate block-by-block across Main Street. Reuse cached dated exports and receipts. Existing preview acceptance is false and positional accuracy unknown; do not silently promote it to surveyed geometry or redistribute aerial pixels. AI owners, dependencies, measurable deliverables and separate accuracy/visual/performance gates are recorded in the breakdown.

## Full Edgewater property audit and omissions

[EW-01–EW-07 and implementation ledger](docs/EDGEWATER_PROPERTY_AUDIT.md) expand commercial verification beyond the prior four-address review. OCPA attributes were checked for 456 parcel features/455 IDs; 162 commercial-tax-family records include 35 without accepted model links and 17 without a visible legacy footprint candidate. These are review records, not a proven missing-building count. Reconcile every property with City zoning/overlays/PD/FLU, OCPA building/condo-parent records, dated aerial/street evidence and appropriate broker/permit/operator sources. Distinguish actual use, entitlement, physical building, storefront, business and listing. No old/conceptual listing becomes current geometry or availability. Deliver a complete corridor checklist, corrections, source dates and independent visual/identity acceptance. All wider project requirements remain active.

## Continuous sidewalks — P0 corridor requirement

Owner explicitly reconfirmed sidewalks October 28, 2026. Extend existing #16, with #15/#17/#18/#25 dependencies and #13 acceptance, across **both sides of the full College Park Main Street / Edgewater corridor**. Princeton–Edgewater is the first detailed intersection, not the full scope.

- [ ] **SW-01 — Inventory continuity:** map each sidewalk segment and gap, frontage, intersection approach, storefront entrance and rear-parking connection. Record source/date and existing/historical/proposed status; unknown or obscured geometry remains unknown.
- [ ] **SW-02 — Obtain actual geometry:** reconcile City ADA/sidewalk/ramp layers, signed engineering/as-built sheets, dated aerials and street-level references. Measure supported clear width, curb/setback, driveway crossings and elevation transitions. Current uniform 2 m road buffers are approximate and do not satisfy this requirement.
- [ ] **SW-03 — Reconstruct corners and routes:** model all four Princeton–Edgewater corners, curb ramps, landings, detectable warnings and crosswalk connections where supported, then repeat along the corridor. Add verified paths from rear lots and accessible parking to storefronts. Do not invent ramps, slopes or striping hidden in imagery.
- [ ] **SW-04 — Preserve usable walking space:** verify tree wells, poles, signs, furniture, utility boxes, driveways, doors and parked cars against the actual path. Track obstructions and missing clear-width/slope evidence; neither a visual clearance check nor an aerial proves ADA compliance.
- [ ] **SW-05 — Finish surfaces:** author concrete slabs/joints, curb edges and pavement/planting transitions at consistent scale and elevation. Prevent buried paths, floating curbs, gaps at corners and asphalt covering pedestrian space. Materials follow accepted geometry.
- [ ] **SW-06 — Accept actual views and connectivity:** deliver a corridor gap/coverage map, per-segment evidence and uncertainty, sharp human-height north/south views, corner close-ups and rear-lot-to-door walkthroughs. Independent QA checks continuity and reference agreement; missing segments remain open. Keep future Complete Street sidewalks in a separate scenario.

AI ownership: transportation GIS analyst sources and maps; civil/scene engineer reconstructs routes/corners; environment artist finishes materials; independent accessibility/QA reviewer checks evidence and gaps. GIS/3D leads accept their domains, PM tracks every block and Director accepts integration. Sidewalks must be resolved before trees, furniture, cars and final conference views are accepted.

## Recognizable churches, post office and offices

[Named-source register and LM-01–LM-07](docs/LANDMARK_RECONSTRUCTION.md) prioritize Church on the Drive (1914 Edgewater), College Park United Methodist (644 W Princeton), Incarnation (OCPA 1505/operator 1515 Edgewater), College Park Post Office (1705 Edgewater), and offices at 1615 and 1420 Edgewater. Resolve exact building/campus identities, model separate wings/roofs and actual façade proportions, connect sidewalks/parking/landscape, and compare real rendered views against dated exterior references. USPS address corroboration found is historical; current facility details still need official locator verification. Incarnation's operator reports an active 2026 rebuild: keep old structures, dated construction and future finished design separate. Priority omission/link checks include the post office and 1615 office. Generic boxes, invented church features and proposed renderings presented as current conditions do not pass acceptance.

## Management-level clarification

PM and Delivery Director are separate levels: **human owner → VP/Sponsor → Delivery Director → PM → delivery workstreams**. PM coordinates tickets, dependencies and reporting; Director oversees PM, resolves delivery priorities and accepts quality gates based on technical/independent review. PM cannot waive gates or approve its own completion. See [management authority](docs/AI_TEAM_MANAGEMENT.md#distinct-management-levels-and-reporting-line). Legacy combined agent task names do not combine these positions.

The [full-project team model](docs/AI_TEAM_MANAGEMENT.md#full-project-delivery-team--current-operating-model) covers GIS/property, planning/zoning, civil/transport, architectural reconstruction, environment/rendering, terrain/environment, commercial evidence, simulation, NVIDIA/platform and independent QA. Execution uses four slots: integrator, two builders and reviewer. PM manages one ready backlog; Director resolves delivery decisions; VP handles strategic milestone issues. Reuse cached sources and accepted methods, rebuild only changed dependencies, batch reviews/status and track real cycle time/rework/coverage. Keep management overhead low and the full project scope intact; no speed claim or ticket completion is inferred from the organization chart.

## District-wide missing-building process and current review cadence

Apply the [repeatable process](docs/EDGEWATER_PROPERTY_AUDIT.md#repeatable-missing-building-process--full-project) to every potential omission across all building types, the full Main Street boundary and wider neighborhood coverage ledger. Compare original and corrected geometry, classify link failures/parking/condos/construction/outside-extraction separately, verify OCPA plus dated independent evidence, then correct ready buildings by block with source-based IDs and explicit uncertainty. Missing wings/upper floors count as defects even when a footprint exists. One difficult property must not hold the rest of the corridor.

Owner instruction: keep highest quality, execute independent tickets in parallel, and consolidate review after every five completed tickets. Necessary local construction checks continue; five small edits or five unverified building candidates do not equal five completed tickets. This supersedes earlier per-change review/one-showcase-first sequencing where inconsistent.
