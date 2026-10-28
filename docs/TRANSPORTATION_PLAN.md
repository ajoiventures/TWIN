# Transportation, sidewalks and street visuals — implementation plan

## Delivery sequence

1. Finish official-source ingestion and join QA; keep the existing centerline preview labeled approximate.
2. Connect FDOT roadway/traffic and LYNX transit sources after verifying corridor coverage and current feed dates.
3. Acquire Orlando sidewalk, ramp and crossing geometry; compare inventory statuses and dates with current evidence.
4. Select and validate one continuous existing-condition Edgewater block, including widths, curb cuts, entrances and parking.
5. Build accurate road/sidewalk surfaces. Keep proposed redesign geometry in a separate scenario layer.
6. Place detailed tree and car assets using accepted clearances/parking; improve materials, signs, lighting and shadows.
7. Review fixed street-level/aerial views and laptop performance before extending to the rest of the corridor.

## Accuracy rule

Road centerlines, sidewalk edges, traffic counts and transit feeds are distinct sources. A buffered centerline is an illustrative fallback, not a surveyed sidewalk. Unknown width, slope and condition stay unknown or clearly estimated. Do not infer current traffic from AADT or real-time vehicles from static GTFS.

## Tickets

### [Connect transportation data: city streets, FDOT roadway/traffic and LYNX transit](https://github.com/ajoiventures/TWIN/issues/15)

Priority: P0. Depends on #3, #4, #5.

Build a transportation source register and normalized adapters for the Edgewater corridor. Treat street geometry, traffic measurements and transit schedules as different data products.

- [ ] Use official Orlando street-centerline IDs as the local network backbone and preserve OSM identifiers as supplemental references, not interchangeable IDs.
- [ ] Inventory and verify FDOT RCI lane/surface-width/speed/sidewalk datasets and traffic-count sites. Audit actual Edgewater coverage; state datasets do not necessarily cover every local street.
- [ ] Inspect the official LYNX GTFS download for stops, routes, shapes, service calendars and feed validity dates; use GIS stop/route layers where appropriate.
- [ ] Record provider, endpoint/download URL, schema, source date, CRS, units, license, refresh cadence and authentication/rate limits for each selected source.
- [ ] Keep AADT/historical counts distinct from live traffic, and static GTFS distinct from vehicle positions or arrival predictions. Do not simulate live conditions from historical data.
- [ ] Normalize and cache by corridor/segment/stop IDs. Validate spatial/temporal joins, unmatched coverage, duplicate routes and expired service calendars; public scene clients read snapshots.

Deliverables: Transportation catalog, normalized street/count/transit tables, coverage map, adapters and offline fixtures.

- [Official source 1](https://www.fdot.gov/statistics/gis/default.shtm)
- [Official source 2](https://www.fdot.gov/statistics/hwydata)
- [Official source 3](https://www.golynx.com/maps-schedules/data-download.stml)

### [Acquire and reconcile actual sidewalk, curb-ramp and crossing geometry](https://github.com/ajoiventures/TWIN/issues/16)

Priority: P0. Depends on #4, #5, #15.

Replace the assumption that a sidewalk is a uniform buffer around a road centerline with evidence-based pedestrian-facility data.

- [ ] Locate the City of Orlando ADA inventory's sidewalk, ramp and crosswalk GIS layers, and verify the actual public download/service or request route; the existence of an inventory does not establish a publicly accessible API.
- [ ] Record the source inventory year, last update, coverage, geometry accuracy and facility status. Preserve existing, missing, under-construction and future facilities separately.
- [ ] Reconcile official geometry with dated aerials and available as-built/design drawings; identify sidewalk width, curb line, curb cuts, tree wells, bus stops and obstructions where evidence exists.
- [ ] Audit gaps and stale features against the Edgewater Complete Street project. Do not apply future widening, removed driveways or proposed crossings to the existing-condition layer.
- [ ] Produce segment-level confidence and missing-width/grade queues; unmeasured widths and slopes remain unknown or explicitly estimated.
- [ ] A pilot-block reference map shows every sidewalk segment, crossing and ramp source, status and geometry mismatch; no source notes or held internal data are published by default.

Deliverables: Sidewalk/ramp/crossing source register, normalized pedestrian GIS layers, coverage/conflict map and field-verification queue.

- [Official source 1](https://www.orlando.gov/files/sharedassets/public/documents/public-works/ada-transition/14-appendix-l.pdf)
- [Official source 2](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project)

### [Build accurate Edgewater road and sidewalk geometry for one pilot block](https://github.com/ajoiventures/TWIN/issues/17)

Priority: P1. Depends on #6, #15, #16.

Construct a source-referenced road-to-frontage cross section on one continuous block before replicating the model along the full corridor.

- [ ] Choose pilot-block endpoints/intersections and freeze an existing-condition reference date. Document coordinate origin, units, horizontal accuracy and any vertical uncertainty.
- [ ] Build carriageway edges, lane markings, parking bays, curb/gutter, sidewalk edges, crossings, ramps, driveways and entrances from the accepted transportation/pedestrian layers.
- [ ] Use measured/official widths where available. A centerline buffer is only an explicitly marked fallback; do not fabricate sidewalk slopes, curb heights or engineering tolerances.
- [ ] Check joins and topology across corners, driveways, ramps, building entrances and bus-stop boarding areas; flag gaps, overlaps, self-intersections and abrupt elevations.
- [ ] Keep existing conditions and proposed Edgewater redesign in independent, switchable USD layers with source/date labels.
- [ ] Validate dimensions and alignment at a documented sample of critical points against references and record residuals; the visual model must not claim ADA compliance without supporting measurements.

Deliverables: Pilot-block road/sidewalk USD layers, cross-section data, alignment report and topology/clearance QA.

- [Official source 1](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project)

### [Improve street visuals and place realistic assets against verified pedestrian geometry](https://github.com/ajoiventures/TWIN/issues/18)

Priority: P1. Depends on #9, #10, #11, #17.

Make the verified block look convincing while preserving its geometry, clearances and evidence quality.

- [ ] Use correctly scaled asphalt, concrete, joints, curb materials, road markings, glazing and facade textures with consistent normals, UVs, daylight and contact shadows.
- [ ] Correct visible material-mask/ground-surface defects before cosmetic work; grass, pavement and parking must remain distinct at street level and aerial scale.
- [ ] Place detailed trees only in supported tree wells/landscape areas and realistic vehicles only in valid parking areas; trunks, wheels and furniture cannot obstruct crossings, ramps, entrances or the pedestrian route.
- [ ] Use the same five fixed cameras for before/after review: corridor aerial, intersection, sidewalk approach, storefront entrance and pedestrian eye level.
- [ ] Apply instancing and distance detail; compare performance and memory against the baseline on the target laptop.
- [ ] Sign off the pilot block against dated source references, then expand by block with a confidence report. Unverified placement stays labeled illustrative.

Deliverables: Reviewed visual pilot block, licensed/original asset manifest, clearance report, fixed-camera comparisons and performance results.



## Current ingestion checkpoint

The first live-source snapshot contains 3,783 parcel features (3,782 unique parcel IDs), 464 city street segments, 4 intersecting neighborhoods, 91 zoning features, 8 parks, 3,228 recent permit rows, and 3,587 business-license rows. Business rows include historical licenses and multiple categories; they are not a verified tenant list.

2,857 of 3,090 prototype building groups match by parcel ID plus footprint geometry; 196 spatial-only matches and 37 ambiguous/unmatched groups require review. No private BOOMS values were imported. The local snapshot API/map and USD metadata are connected. This is partial implementation, not acceptance of geographic accuracy or pedestrian geometry. Public draft crosswalk access findings and unresolved status/units are recorded in [PEDESTRIAN_ACCESS_REPORT.md](PEDESTRIAN_ACCESS_REPORT.md).

See [the master roadmap](https://github.com/ajoiventures/TWIN/issues/14).

