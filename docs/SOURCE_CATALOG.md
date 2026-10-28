# Government source register and access probes

Implemented for ticket #19 on October 28, 2026. The source catalog is a reproducible metadata/access and coverage checkpoint; it does not download full datasets or certify new sources for scene use.

## Run

Use the project's Python runtime (standard library only for this tool):

```
python tools/source_catalog.py --refresh --timeout 12
python tools/source_catalog.py --offline
python -m unittest discover -s tests -p test_source_catalog.py -v
```

Configuration: `config/government_sources.json`. Output: `data/processed/source_catalog.json`. Probe response envelopes: `data/cache/source_catalog/`. Generated data/cache folders are ignored by Git. Each response is limited to 2 MiB, requests have a timeout, and at most four sources probe concurrently. Offline mode makes no network requests and reports cache misses as unknown.

## Current observed result

The first live pass observed eleven reachable endpoints. The expanded register now includes seventeen endpoints, three explicit bounded discovery searches and specific dataset selections. One refresh recorded a USGS TNM connection reset, retained as unknown rather than zero coverage; a targeted retry succeeded and restored six catalog candidates. Florida's tile index independently returned six matching tile records. See each probe's checked time and status in the JSON rather than treating this document as a live health dashboard.

| Source | Observation | What remains unknown |
|---|---|---|
| Florida GIO portal | Portal reachable | Selected dataset access, dates, resolution, terms and College Park coverage |
| NOAA Digital Coast | Portal reachable | Complementary selected product coverage/access |
| USGS TNM product catalog | Six LiDAR tile candidates intersect the extraction rectangle | Actual classified roof/ground completeness and newer acquisitions outside this query |
| USGS Orange EPT | EPT metadata reachable; prior local pilot has 4,366,627 clipped points | Full neighborhood sample coverage/accuracy |
| NOAA Orange metadata | Metadata page reachable; linked to the known USGS acquisition | No independent second flight is established |
| OCPA parcels | Bbox query: 3,783 intersecting features | Current district membership and surveyed boundary accuracy |
| OCPA building subareas | Bbox query: 13,500 intersecting subareas | Independent buildings are not equivalent to subarea rows |
| City street centerlines | Bbox query: 464 intersecting segments | Curb/sidewalk boundary geometry and inventoried widths |
| City permits | Socrata schema metadata reachable; prior snapshot available | No new permit query is performed by this catalog |
| FDOT GIS page | Download page reachable | Selected layer corridor coverage and width/traffic semantics |
| LYNX download page | Page reachable | GTFS binary reachability, valid calendars and stop alignment |

These numbers are rectangle-intersection counts, not official College Park district totals. The extraction rectangle is `[-81.398, 28.5605, -81.379, 28.5845]`. Accessible pages do not prove that their datasets can be downloaded or reused.

The six USGS tile records are all within the known `FL_Peninsular_FDEM_Orange_2018` project directory. Their catalog publication date is 2021-04-20; publication is not acquisition. The configured project acquisition interval is 2018-12-04 through 2019-04-12. USGS EPT, NOAA metadata and matching tile source IDs form one acquisition group, not independent corroborating measurements. Unknown acquisitions remain ungrouped rather than being merged on publisher/date similarity.

## Evidence and safe previews

The register retains endpoint URL, publisher, live/cached/offline mode, checked time, response checksum, HTTP/content status, dataset fields where available, source updates, stated CRS/units/datum and reuse unknowns. ArcGIS schema success triggers a separate bounded bbox-count request; only a successful integer count becomes observed coverage. Errors and inaccessible responses never become zero coverage.

Existing active snapshot tables supply allowlisted first-five-row previews for parcels, City streets and permits. No owner/contact/private notes or BOOMS fields are read. Parcel IDs remain strings. The local snapshot checksum, reported retrieval timestamp, source update and scope are preserved separately. Legacy snapshot timestamps may represent build time when cached data were reused; this limitation is explicitly recorded. New probe cache timestamps remain the original request time when read offline or cached.

The EPT source metadata identifies horizontal EPSG:3857 meters; original project vertical metadata uses survey feet while the transformed EPT elevations have a separate local meter-unit check. This catalog reports that distinction and does not convert geometry or claim independent survey-grade vertical accuracy.

## Catalog acceptance versus downstream activation

- Specific Florida GIO/NOAA datasets, direct download links, metadata/terms evidence and unknowns are recorded below.
- Ranked selection decisions and a geographic metadata-coverage artifact are generated reproducibly.
- Imagery/transport discovery queries, bounds, result limits, candidate IDs and access outcomes are recorded below.
- The restricted canopy product is explicitly excluded from AI candidate use, regardless of pixel availability; it is not activated.
- Application integration verified: `/api/v1/source_catalog` returns the 17-source register and `/source-coverage` returns the interactive diagram. Checkbox behavior and the full page were reviewed in-browser; evidence is `docs/evidence/source-coverage.png`. Independent PM/Director review accepted this bounded catalog/discovery delivery on October 28, 2026.
- All-tile terrain validation belongs to #6; imagery/Maxar access/eligibility belongs to #20; FDOT corridor coverage and LYNX calendars belong to #15. Those downstream activations are not prerequisites for catalog discovery completion.

Twenty tests cover offline/cache behavior, portal-versus-coverage distinction, service errors, observed zero counts, acquisition grouping, safe previews/path containment, TIFF resolution, ISO envelopes, NoData, bounded metadata failures, malformed optional evidence, exact normalized license restrictions, unknown expiry, AI exclusion despite valid pixels and bounded-search interpretation.

## Specific selected datasets and ranking

| Rank | Dataset / decision | Evidence and limits |
|---|---|---|
| 1 | Florida GIO [LAS/DEM tile index](https://www.arcgis.com/home/item.html?id=b7fb9a247dce4c97b360b364419e8f86): accept original DEM tiles for historical terrain preparation | Official `FloridaGIO` item owner verified. Six actual index polygons intersect the study rectangle. Each provides direct LAZ/DEM/XML URLs. Representative DEM byte-range request returned TIFF data (HTTP 206); GeoTIFF pixel-scale tag is **2.5 US survey feet**, approximately **0.762001524 m**. Original XML identifies NAVD88 elevations in US survey feet and NAD83(2011) Florida East horizontal coordinates. This selects a source, not production terrain acceptance. |
| 2 | [NOAA-referenced Orange USGS EPT](https://www.fisheries.noaa.gov/inport/item/69496/full-list): accept historical classified point sampling | Existing sampled pilot and public EPT metadata establish useful roof/ground evidence. NOAA's processing description explicitly states EPT conversion to EPSG:3857 with NAVD88 meters. Original and transformed products must retain different unit records. Same flight as rank 1, not independent corroboration. |
| 3 | [NOAA Florida East 1 regional DEM](https://www.fisheries.noaa.gov/inport/item/70061): reject for precise streetscape; pending as context fallback | Actual ISO bbox intersects College Park. Approximate 3m resolution, NAVD88 meters. [Specific 5.42GB BigTIFF](https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/dem/SLR_viewer_DEM_6230/FL/FL_East_1_GCS_3m_NAVDm.tif) binary range is reachable; full raster not downloaded. It incorporates the same Orange flight, is too coarse for curbs/sidewalks and still needs local valid-pixel checks. Catalog access-level inconsistency and the regional abstract's inconsistent label are recorded for review. |
| 4 | Florida-hosted [NOAA canopy 2020–2021](https://www.arcgis.com/home/item.html?id=5288fc04c2ed4c3ba86bb2469b3d1acf): excluded from AI candidate use | The item license restricts machine-learning purposes for five years from product creation except with Ecopia written consent. Original product creation and restriction expiry are not established; no consent evidence is supplied. A pilot-center sample is also NoData. No tree positions/species or ML datasets are generated from it. |

The original DEM tiles are `DEM257172`, `DEM257173`, `DEM257472`, `DEM257473`, `DEM257772`, and `DEM257773`. The register preserves all six direct URLs, index source IDs, dates and actual tile envelopes. Only a representative raster's binary metadata was checked; all tile seams/nodata/CRS must be checked before terrain activation.

Both original USGS tile XML and NOAA ISO constraints are retained locally as evidence, with source URLs/checksums. Original USGS metadata has no access constraint subject to its disclaimer and warns against misrepresentation of modified data. NOAA metadata lists no access restriction while requiring appropriate citation and suitability review. Florida index item license text is empty, which is recorded as unknown rather than permission. These observations do not grant redistribution rights to unrelated portal assets.

## Geographic coverage artifact

`data/processed/source_coverage.html` is a standalone interactive coverage diagram. It uses the query-returned tile footprint envelopes, previously sampled pilot rectangle and NOAA ISO regional bbox. Layers can be toggled; hovering shows the evidence basis. The red rectangle is the extraction extent, not an official district boundary. A hatched regional envelope is explicitly not valid-pixel coverage. Unknown canopy coverage remains undrawn.

The generated register reports the active snapshot IDs used for safe previews and checks that those source previews use one consistent snapshot. The latest build detected the refreshed local snapshot rather than retaining the previous pointer. Regenerate after any subsequent snapshot activation.

The catalog is ready for final reviewer acceptance after application route/runtime checks. Explicitly excluded or pending candidates are valid catalog outcomes and must not become activated datasets. Terrain production, roof expansion and transport-feed validity remain their own downstream tickets.

## Canopy license control

The [source item metadata](https://www.arcgis.com/sharing/rest/content/items/5288fc04c2ed4c3ba86bb2469b3d1acf?f=json) contains an explicit Ecopia restriction covering creation, training, improvement, modification, validation, testing and evaluation of machine-learning algorithms for five years from the product's creation, except with express written consent. The exact restriction text is retained in `use_restrictions.restriction_text`, alongside its source metadata URL and source item timestamps.

`ml_use_allowed` is false; the candidate decision is `exclude_from_ai_candidate_use`. Original product creation, expiry and written-consent evidence remain null. The ArcGIS item creation timestamp and imagery title years are deliberately not used to infer expiry. No consent request is sent. Empty or missing license text for other candidates never becomes affirmative ML permission.

## Bounded imagery and transportation discovery

Each ArcGIS search is cached with exact query, study bbox, response timestamp/checksum, result limit (30), reported total, next-page marker, candidate IDs/URLs/titles and disposition. This is a bounded search of named publisher/owner namespaces, not an exhaustive statewide search.

| Search/access test | Observed outcome | Disposition |
|---|---|---|
| FloridaGIO org `Gh9awoU677aKree0`, `imagery OR orthophoto`, study bbox | 15 items, all returned (`nextStart=-1`), including Maxar Hurricane Ian footprint `275cd82000f846d7aa7a117766ed380c`, Planet footprint `13e4b719ac334f5e8d4f7eba04e6e0ad`, GIC footprint `6325291c5a414b9ca4feb80b23f302d6`, thematic C-CAP layers and event/reference maps | Specific candidate list preserved; historic event footprints are not current orthophotos. None activated. Canopy is excluded from AI use; other local pixels/access/terms require #20 verification. |
| Specific Maxar Hurricane Ian 2022 footprint service | Metadata reachable; study-bbox count query timed out | Coverage remains unknown, not zero. No claim of usable local imagery; defer actual imagery acquisition to #20. |
| Same FloridaGIO org, `transportation OR roadway OR sidewalk`, study bbox | 0 results for this exact bounded query | No suitable result selected from this namespace/query; does not imply Florida has no transport data. |
| Named owner `FDOT_OpenData`, `sidewalk OR lanes OR AADT`, study bbox | 0 results for this exact bounded query | Owner-alias search failure is documented, not interpreted as absent data. Official FDOT page supplies specific direct downloads below. |
| [FDOT sidewalk width/separation ZIP](https://ftp.fdot.gov/public/file/p0waamicg0ebhsyx9j5rdw/sidewalk_width_sep.zip), linked by official GIS page | HTTP 206, ZIP signature, advertised total 11,490,838 bytes; only 1,024 bytes read | Specific downloadable candidate established. Fields, dates, width units and Edgewater coverage remain #15 checks. No sidewalk geometry activated. |
| [FDOT AADT ZIP](https://ftp.fdot.gov/public/file/83nno5eage6zae57e4utrw/aadt.zip), linked by official GIS page | HTTP 206, ZIP signature, advertised total 7,824,953 bytes; only 1,024 bytes read | Specific downloadable candidate established. Local count sites, years and segment mapping remain #15 checks; AADT is not live traffic. |

FDOT ZIP access does not establish schema or local coverage. LYNX page access likewise does not establish a reachable current GTFS feed or valid service calendar. These exact unknowns are retained rather than replaced by inferred operational data.
