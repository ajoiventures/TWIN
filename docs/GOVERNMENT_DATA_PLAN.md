# College Park government data improvement plan

Prepared October 28, 2026. Scope: College Park, Orlando, starting with one continuous Edgewater Drive block. This is an implementation backlog, not a claim that every listed dataset is available or connected.

## Starting point

The platform direction and expanded delivery waves are defined in [Smart City Platform Plan](SMART_CITY_PLATFORM_PLAN.md). This document remains the source-ingestion workstream beneath that architecture.

The local active snapshot contains OCPA parcels and building links, City streets, neighborhoods, zoning, parks, permits and business-tax records. The scene has 3,090 building groups: 90 historical LiDAR-derived heights and 3,000 floor-count estimates; 976 heights changed. Ground remains flat. Detailed tree and car assets exist, but placement still needs verified pedestrian and parking geometry. The current rectangular extraction is not an official district boundary.

## Shared requirements for every source

1. Confirm publisher, geographic coverage, acquisition/effective date, update date, access method and reuse conditions. A portal listing alone does not prove coverage or downloadable geometry.
2. Record source URL, dataset/item ID, stable feature ID, fields, units, horizontal CRS, vertical datum, status codes, checksum and retrieval time. Preserve acquisition dates separately from download dates.
3. Cache clipped source snapshots locally; validate geometry, duplicates, missing IDs, counts and schema changes before activation. Keep the previous snapshot available for rollback.
4. Publish a field dictionary, first five safe rows, coverage map, unresolved-match report and quality summary. Preserve nulls and leading zeroes.
5. Expose read-only local API tables and separate USD layers. Preserve manual edits. Show source date, method and quality in the inspector.
6. Keep existing, historic, under-construction and proposed features distinct. Keep private BOOMS data and staff-validation release gates separate from public GIS.

## Source work packages, in requested priority order

| ID / priority | Official source | Work and output | Completion check / dependencies |
|---|---|---|---|
| G01 / P0 | [USGS LiDAR Explorer](https://www.usgs.gov/tools/lidarexplorer) | Inventory all intersecting point clouds and DEMs; compare acquisition dates and classification quality; expand roof sampling beyond the pilot; create bare-earth terrain. Output building-height evidence and terrain tiles. | Every building has a measured, estimated or unresolved label; ground/building units and vertical datum agree; no building floats or sinks after terrain placement. Depends on G07 parcel links and the shared register. Extends existing ticket #6. |
| G02 / P0 | [Florida Geospatial Portal](https://geodata.floridagio.gov/) | Search elevation, orthophotos, structures and transportation by College Park coverage; identify newer or complementary source products. Record original steward and compare against G01/G03. | Candidate catalog includes date, resolution, coverage and access tests. Mirrored USGS/NOAA products are deduplicated rather than counted as independent measurements. Feeds G01/G03/G05. |
| G03 / P0 | [OCPA aerial map](https://webmap.ocpafl.org/search) | Identify available dated imagery and permitted image-service access; compare roof outlines, additions, canopy, parking stripes and driveways across dates. Produce a dated discrepancy layer and pilot reference sheets. | Review every pilot-block building and curb frontage; record image date/resolution and confidence. Occluded curbs stay unresolved. Aerial imagery does not establish facade appearance or surveyed heights. Depends on G07. |
| G04 / P0 | [Orlando GIS downloads](https://www.orlando.gov/Our-Government/Records-and-Documents/Map-Library/GIS-Data-Download) and [Open Data](https://data.cityoforlando.net/) | Extend existing adapters with official study boundaries, addresses and public pedestrian/asset layers where available. Reconcile zoning, permits and business records through stable IDs and dates. | Actual neighborhood versus Main Street boundaries are distinguished; unmatched records are reported; business-tax rows are not presented as verified active storefronts. Extends #4/#5/#12. |
| G05 / P0 | [FDOT GIS](https://www.fdot.gov/statistics/gis/default.shtm) | Acquire lanes, surface width, speed, sidewalk width/separation and traffic-count data; clip and match inventoried segments to City streets. Produce segment attributes and a coverage-gap map. | Verify Edgewater coverage, units, segment direction and location; no countywide or state-road attribute is blindly applied to local streets. AADT remains historical aggregate traffic. Depends on G04. Extends #15. |
| G06 / P1 | [NOAA Digital Coast](https://www.coast.noaa.gov/digitalcoast/tools/dav.html) | Search LiDAR, imagery and land cover by project extent; compare dates and metadata with G01/G02; use as an alternate acquisition route or complementary source. | Document whether a product is the same flight as an existing USGS source. Select on date, quality and coverage, not portal count. Depends on G01/G02 catalog. |
| G07 / P0 | [OCPA property records](https://ocpaweb.ocpafl.org/), [GIS services](https://vgispublic.ocpafl.org/server/rest/services) and [parcel metadata](https://ocpaimages.ocpafl.org/api/Content/GetContentDynamicFile?contentFileID=405230) | Strengthen existing parcel/building adapter; verify building/subarea floor counts, year built and available property sketches; review conflicting stories and multi-building parcels; add stable property/map links. | Preserve source IDs and one-to-many links; each conflict has evidence or an unresolved flag; parcel stories are not replicated onto accessory buildings. Property sketches are evaluated for footprint dimensions before use. Extends #3/#6. |
| G08 / P0 | [Orlando ADA inventory documentation](https://www.orlando.gov/files/sharedassets/public/documents/public-works/ada-transition/14-appendix-l.pdf) | Locate public sidewalk, ramp and crossing layers or prepare a precise records-request specification if unavailable. Retain existing/missing/future status; compare dates and aerials. Produce actual pedestrian geometry and gaps. | Inventory documentation is not treated as a working API. Pilot widths, curb cuts, entrances and crossings are evidence-linked; centerline buffers remain illustrative. Depends on G03/G04. Extends #16/#17. |
| G09 / P1 | [Edgewater Complete Street project](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project) | Inventory published drawings, cross-sections and revisions; obtain available georeferenced plans. Model proposed sidewalks, crossings, landscaping and Lakeview roundabout in a future scenario. | Each modeled design has sheet/revision/date/status; proposed construction is never shown as existing. Compare existing/future using matching camera views. Depends on G03/G05/G08. |

G07 and the source register run alongside G01: parcel links and floor conflicts are prerequisites for safe height expansion. G08 begins early because public access may be the longest dependency.

## Additional useful government and public-agency sources

| ID / priority | Source | Planned improvement and acceptance check |
|---|---|---|
| G10 / P1 | [Orange County Open Data Hub](https://orange-county-open-data-ocfl.hub.arcgis.com/) | Inspect address, right-of-way, drainage and transportation candidates. Use only verified public layers intersecting the pilot. Reconcile City/County stewardship; the County portal does not replace OCPA as parcel steward. |
| G11 / P1 | [LYNX GIS and GTFS](https://www.golynx.com/maps-schedules/data-download.stml) | Connect stops, routes, shapes and valid service calendars; verify stop side of street and accessible sidewalk connection. Current feed reachability must be resolved. Static schedules do not create live bus positions. Extends #15. |
| G12 / P2 | [St. Johns River Water Management District GIS](https://ra.sjrwmd.com/data/gis/) | Inspect public water, land-cover and elevation candidates for actual College Park coverage. Use water polygons and documented land cover to improve lakes and landscape context; do not assume historic district DEMs cover urban Orlando. |
| G13 / P2 | [FEMA Map Service Center](https://msc.fema.gov/portal/home) | Add effective flood-hazard polygons as an optional information overlay with map dates and zone codes. A published hazard zone is not a live flood simulation or a prediction of water depth. |
| G14 / P1 | City GIS, G03 aerials and G01 LiDAR | Search for a public tree inventory, including species and last inspection if available. Where absent, derive approximate canopy locations/heights and label them inferred; species remains unknown. Place trees outside accepted walkways/entrances using documented clearance rules. Extends #9/#18. |
| G15 / P1 | City/County public engineering and project records | Seek public curb, parking, lighting, drainage and as-built plans for the pilot. Inventory access and dates first; do not assume utilities or survey files are publicly downloadable. Trace only supplied geometry; distinguish designed from constructed. Supports #10/#11/#17/#18. |

## Delivery phases and review gates

### Phase A — Source and parcel foundation

- Build one source register and official boundary/extent configuration.
- Complete G02 catalog and G07 conflict audit; establish G03 imagery references.
- Probe G08/G10/G15 public access and log exact gaps. Prepare request drafts if needed; sending requests is a separate authorized action.
- Gate: reproducible snapshots, source dates, field dictionaries and safe first-five-row previews; all unknown coverage explicitly listed.

### Phase B — Heights and terrain

- Expand G01 in bounded tiles; use G06 only for alternate/complementary products.
- Derive local terrain and building heights in a common metric/vertical reference.
- Re-anchor buildings, streets and vegetation to ground; preserve floor estimates where roof evidence fails.
- Gate: coverage/quality map, outlier report, sampled roof/ground reviews and no unexplained vertical offsets. Record acquisition age and uncertainty without claiming survey precision.

### Phase C — Accurate existing Edgewater block

- Choose a continuous block with useful source coverage; record exact endpoints before modeling.
- Integrate G04/G05/G08/G10/G11 and accepted public plans.
- Build road edges, sidewalks, curb ramps, crossings, driveways and parking from evidence. Add canopy/tree locations and detailed assets only after space is verified.
- Gate: every frontage reviewed; conflicting widths and inaccessible features queued; cars stay in accepted parking and trees do not obstruct pedestrian routes. No invented ADA compliance claim.

### Phase D — Future scenario and context

- Build G09 as a separate switchable scenario using dated design sheets.
- Add G12/G13 optional water/land-cover/flood context.
- Gate: existing versus proposed clearly labeled in API, scene and UI; no proposed feature leaks into existing-condition outputs.

### Phase E — Release and repeat

- Compare fixed street-level and aerial views; verify source links, selection, layer controls and rollback.
- Measure performance at a recorded resolution and machine configuration; use instancing, tiling and detail levels as needed.
- Gate: geographic review evidence, meaningful adapter/geometry tests, missing-asset checks and repeatable refresh. Extend block by block only after the pilot passes. Extends #12/#13.

## Prioritization and effort

Role ownership, skill requirements, bounded AI-agent dispatch, review gates and the first ready batch are maintained in [AI Team Management](AI_TEAM_MANAGEMENT.md). Every GitHub ticket has a responsible AI role and a review role; this is separate from assigning human GitHub accounts.

P0 establishes geometry and evidence. P1 improves streetscape, scenarios and operations. P2 adds context after the pilot is trustworthy. First delivery should include Phase A and a bounded Phase B expansion; do not promise all sources in one sprint.

Indicative engineering sizing, not a calendar commitment: catalog/adapter work is small to medium per accessible source; terrain integration and verified pilot geometry are large; external records access is unknown. Choose dates and capacity after coverage/access checks. No team availability or delivery deadline has been assumed.

## Ticket alignment

Converted to GitHub issues on October 28, 2026: seven new tickets (#19–#25), nine existing implementation tickets expanded, and roadmap #14 updated. Work-package coverage:

| Work package | GitHub issue |
|---|---|
| G01 USGS heights/terrain | [#6](https://github.com/ajoiventures/TWIN/issues/6) |
| G02 Florida GIO / G06 NOAA | [#19](https://github.com/ajoiventures/TWIN/issues/19) |
| G03 OCPA aerials | [#20](https://github.com/ajoiventures/TWIN/issues/20) |
| G04 City GIS/boundaries | [#4](https://github.com/ajoiventures/TWIN/issues/4), [#5](https://github.com/ajoiventures/TWIN/issues/5) |
| G05 FDOT / G11 LYNX | [#15](https://github.com/ajoiventures/TWIN/issues/15) |
| G07 OCPA records/GIS | [#3](https://github.com/ajoiventures/TWIN/issues/3), [#6](https://github.com/ajoiventures/TWIN/issues/6) |
| G08 ADA pedestrian geometry | [#16](https://github.com/ajoiventures/TWIN/issues/16) |
| G09 future Edgewater | [#21](https://github.com/ajoiventures/TWIN/issues/21) |
| G10 County GIS | [#22](https://github.com/ajoiventures/TWIN/issues/22) |
| G12 water/land cover | [#23](https://github.com/ajoiventures/TWIN/issues/23) |
| G13 flood overlay | [#24](https://github.com/ajoiventures/TWIN/issues/24) |
| G14 tree evidence | [#9](https://github.com/ajoiventures/TWIN/issues/9), [#18](https://github.com/ajoiventures/TWIN/issues/18) |
| G15 engineering references | [#25](https://github.com/ajoiventures/TWIN/issues/25) |

Execution update: #19 passed independent source-catalog/discovery acceptance and is closed. Other tickets remain open pending their implementation and acceptance evidence. See [Execution Status](EXECUTION_STATUS.md).

Existing tickets were reused for OCPA, City GIS, boundaries, heights/terrain, trees, transportation, pedestrian geometry, provenance and release QA. G01–G15 remain work-package IDs; the table above maps them to actual GitHub issue numbers.

## Main risks and responses

- Old LiDAR versus new construction: compare acquisition and construction dates, retain estimate/review status where incompatible.
- Different vertical references or feet/meters: validate units and datum before any mesh displacement.
- Sidewalk GIS unavailable: document access attempts and request exact layers; retain clearly labeled approximate preview until evidence arrives.
- Duplicate portals: track original acquisition/steward, avoiding false independent corroboration.
- Wrong parcel links or multi-part building groups: preserve match confidence and component limitations; manually review pilot conflicts.
- Public imagery hides facade details: use dated, authorized street-level references for signs/materials; generic storefronts remain illustrative.
- Large scenes: tile data, instance assets and benchmark at a stated resolution before expansion.
