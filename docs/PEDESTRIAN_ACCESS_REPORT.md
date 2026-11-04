# Pedestrian GIS access and coverage report

Discovery run October 28, 2026, for GitHub #16. This is a bounded access/coverage investigation, not a completed sidewalk model or citywide source audit.

## Findings

Four public crosswalk candidate layers were successfully queried inside the existing prototype extraction rectangle, longitude -81.398 to -81.379 and latitude 28.5605 to 28.5845. This rectangle is not an official College Park boundary and no pilot block has been frozen. The counts are intersecting features, not a count of accepted existing crossings. Versions overlap and must not be summed.

| Candidate | Intersecting rows | Access / decision |
|---|---:|---|
| [January 20 named layer](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/PedestrianCrosswalks_Updated_2026_01_20/FeatureServer/0) | 124 | Public query works; reference only |
| [V1 named layer](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/308090_004_FORWARD_Pedestrian_Crosswalks_WFL1/FeatureServer/0) | 125 | Public query works; reference only |
| [February named layer](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/PedestrianCrosswalks_020926Update/FeatureServer/0) | 127 | Public query works; reference only |
| [May 28 named layer](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/PedestrianCrosswalks_Updated_2026_05_28/FeatureServer/0) | 166 | Public query works; reference only |
| [Orlando Sidewalks AGOL layer 1](https://services.arcgis.com/04HiymDgLlsbhaV4/ArcGIS/rest/services/Orlando_Sidewalks_AGOL/FeatureServer/1) | 0 | Public query works, no intersecting records; description identifies Roads in RCI. Not actual walkway-edge geometry. |
| MapWorks Transportation, internal .cit host | Not queried | Public map references an internal service. No access attempt or workaround performed. |

Two [public City-organization web maps](https://www.arcgis.com/home/item.html?id=e65f6e0935e4456f946554f4f4600c60) reference the crosswalk candidates. Live metadata confirms organization `mMuoPCaIYD4wEgDl`, owner `GRE39394_orl`, and titles explicitly containing **Draft**. The [January map](https://www.arcgis.com/home/item.html?id=a6b83c314766472cae5e1479f68f7e65) likewise says draft. Consultant-hosted feature-service accessibility and a City map reference do not establish final adoption or current field conditions.

All four crosswalk candidates are polylines. Their schemas include `PAINTED`, `FADED`, `PedPlan`, `Width`, and length fields. The May candidate has `PedPlan` codes 0:24, 1:102 and 2:40 within the rectangle. Forty May rows have null `PAINTED`; no interpretation that they are existing or proposed is assigned without a data dictionary. Field domains were absent for these fields in the queried layer metadata. Width units and acquisition dates remain unknown. Layer names and ArcGIS modified timestamps are not acquisition dates. The City map even labels one version `2026-02-29`, an invalid calendar date, reinforcing that display titles cannot be treated as authoritative observation dates.

## Accepted versus unresolved

### Extended metadata and candidate geometry review

The latest named candidate service identifies public ArcGIS item [`86a267015798478b8952faccb54d14c9`](https://www.arcgis.com/home/item.html?id=86a267015798478b8952faccb54d14c9), owner `rvanhorn_kai`. Its service-root geometry unit is `esriMeters` and spatial reference is Web Mercator (EPSG:3857). **These XY geometry units do not establish the units of the separately stored `Width` or `length` attributes.**

Checked the layer field domains, subtype domains/names, service renderer, item styling/popup metadata, City web-map renderer and the item's public XML metadata. `PedPlan` subtype names and renderer labels remain numeric `1` and `2`; fields have no semantic coded-value domains. XML has no semantic definition for `PedPlan` or width unit. The City map and service item renderer supply no verified existing/proposed meaning. No status decoding is justified.

An allowlisted WGS84 review-only export now contains **166 candidate polylines**, preserving raw `PedPlan` codes and source identifiers. Every feature has `lifecycle_bucket: unresolved`, unknown `existing_status`/`proposed_status`, null width units and explicit review flags. Existing and proposed acceptance buckets both contain zero accepted assignments; this does **not** claim that no existing/proposed crossings occur. It means classification remains unverified. Do not convert these lines into stripes, ramps or sidewalk boundaries automatically.

Accepted: the stated public endpoints respond to bounded metadata, count, object-ID and attribute queries; the recorded rectangle counts reconcile to retrieved IDs. The candidates are useful for source review and comparing versions.

Unresolved: final City source of record; meanings of status codes; existing versus missing/under-construction/future facilities; width units; acquisition/update dates; actual sidewalk segment/edge and curb-ramp geometry; field accuracy; current pilot-block coverage. **No source is accepted for automatic scene geometry creation.** Zero features in the RCI-derived layer does not mean sidewalks are absent.

## Reproducible outputs

- Configuration: `config/pedestrian_sources.json`.
- Run `python tools/pedestrian_discovery.py`; `--offline` replays cached responses without establishing current freshness.
- Ignored output `data/transport/pedestrian_access_report.json` contains normalized access decisions, schemas, safe status histograms, IDs, City-map provenance and first five safe rows per source.
- Ignored output `data/transport/pedestrian_safe_samples.json` provides the first five allowlisted attribute rows. Notes, owner/contact and City review free text are excluded. Unknown width units/status meanings remain explicit.
- Ignored `data/transport/crosswalk_candidates.geojson` contains the 166 bounded, review-only WGS84 polylines. Geometry is validated for line type, finite WGS84 coordinates and exact requested object-ID coverage.
- Ignored `data/transport/crosswalk_field_dictionary.json` records every source field's exact name, alias, type, nullability, domain, published XML definition and whether attribute values are exported. Fields without definitions stay undefined; no unit is inferred from plausible values.
- Metadata and bounded attribute responses are cached under ignored `data/cache/pedestrian_discovery/`. No scene or active data snapshot is changed.

## Next acceptance steps

1. Confirm the authoritative existing-condition source and crosswalk revision with City Transportation/Public Works through approved records channels.
2. Obtain sidewalk and ramp layers plus the data dictionary; retain existing/missing/future status, source units and dates.
3. Freeze pilot endpoints and compare candidate crossings to dated aerials/engineering records. Only then acquire accepted geometry and perform topology/dimensional checks.

## Records-request draft — not sent

Subject: Existing pedestrian GIS and metadata for College Park / Edgewater Drive

Please provide available public electronic GIS records for sidewalks, sidewalk edges or polygons, curb ramps, marked crossings, curbs/curb cuts, and relevant pedestrian facility inventory/as-built references in College Park, Orlando, especially Edgewater Drive from Lakeview Street to Par Street. The prototype extraction rectangle is WGS84 [-81.398, 28.5605, -81.379, 28.5845]; please identify any corridor coverage outside this rectangle.

Requested format: available native geodatabase, GeoPackage, Shapefile or GeoJSON, or an existing public feature-service/download URL. Please provide feature IDs, geometry, facility status (existing, missing, under construction, future/proposed), width and units, slope/grade where recorded, inspection/acquisition and last-update dates, source/accuracy metadata, horizontal CRS and any vertical datum, and field/code-domain definitions. We request existing records, not new measurements or analysis.

Please identify the current authoritative dataset and its coverage, and clarify the relationship between the 2021 ADA transition inventory and the public Pedestrian Facilities Plan Crosswalk Inventory Draft maps (`a6b83c314766472cae5e1479f68f7e65`, `e65f6e0935e4456f946554f4f4600c60`). In particular, please clarify `PedPlan`, `PAINTED`, `FADED`, width units, the current adopted revision, and whether proposed facilities are present. If the MapWorks Transportation reference has an existing public equivalent, please provide that public access route; internal-system access is not requested.

Please distinguish existing-condition/as-built records from proposed Edgewater Complete Street designs and provide any applicable public reuse/attribution terms. If a requested layer is unavailable, please identify the gap and any existing alternative public records.
