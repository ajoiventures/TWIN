# Official LYNX static schedule reference

Existing ticket #15 delivery, October 28, 2026 local time. This supplements the existing static GIS packet without replacing its IDs, geometry or active snapshot. No real-time protobuf, vehicle position or arrival-prediction endpoint is fetched.

## Actual access and feed

The [official LYNX download page](https://www.golynx.com/maps-schedules/data-download.stml) links **HTTP** `http://gtfsrt.golynx.com/gtfsrt/`. The earlier HTTPS timeout did not establish that this official HTTP resource was unavailable. The public directory returned 200 and linked `google_transit.zip`; the original **2,358,835-byte** archive, index/page bytes and checksum/retrieval receipts are cached locally. No credentials, forms or outreach were needed. The official page's as-is terms remain linked and preserved; public access is not a survey warranty or a broader asset/imagery license.

The feed publishes validity **2026-10-02 through 2026-12-12**, with agency timezone America/New_York. The provider directory lists October 2, 2026 at 16:06 for the ZIP, but supplies no timezone; that is not an acquisition date. There are 3,687 stops, 62 routes, 7,674 trips, 110,627 shape points, 359,274 stop-time rows, eight calendars and 15 date exceptions. The loader checks original IDs, foreign keys, finite/in-range stop and shape coordinates, semantic numeric uniqueness of shape/stop sequences, calendar codes and times. Sequence strings such as `01` and `1` cannot bypass duplicate detection; their original source values remain unchanged. Source IDs retain padding and leading zeroes exactly. Provider times reach hour 26; these remain service-day times rather than being truncated to 24 hours or mislabeled UTC.

## Actual College Park coverage

| Record | Observed study-area result | Limit |
|---|---:|---|
| Static stops | 15 | Published stop references, not surveyed boarding areas or verified accessibility |
| Intersecting shape variants | Four | Scheduled paths clipped to the unchanged extraction rectangle; not carriageway edges |
| Route short names with intersecting shapes | 106 and 125 | Provider labels are not interchangeable with GIS object IDs |
| Trips serving stops or intersecting shapes | 374 | Includes multiple weekday/weekend services; not today's observed vehicle count |
| Trips serving the 15 stops across all services | 205 | Only route 125 serves these stops in this feed; route 106 paths intersect the study extent |
| October 28 scheduled trips serving those stops | 100 | Published weekday schedule, not proof the trips actually operated |

The older GIS packet has route labels 89, 106 and 125. Route 89 has no intersecting shape in this current feed/query. Both vintages remain separate; absence here does not establish cancellation. All 15 GIS StopId values have a single GTFS candidate after **explicit whitespace-only trimming**, with maximum point separation about 0.799 m. Original padded GTFS IDs remain unchanged, candidates do not become accepted physical-pole identities, and original GIS OBJECTIDs are retained. No route/stop is silently merged or removed.

## Reproduction, contract and temporal safeguards

Run `python tools/lynx_gtfs_reference.py --offline --service-date 2026-10-28`. Normal mode acquires missing official page/index/ZIP pairs only; partial or modified caches require review instead of silent overwriting. ZIP loading is in-memory with flat-path and 64 MiB total expanded-size bounds. No raw ZIP or imagery is committed. Approved tables exclude agency contact and fare values.

Ignored outputs under `data/processed/lynx_gtfs_reference/` are `packet.json`, `stops.geojson`, `shapes.geojson`, checksum receipt and timestamped previous publication bundles. The packet contains source fields/dictionaries, first five safe rows, normalized selected stops/routes/trips/stop-times/calendars/exceptions/feed metadata, source receipts, temporal/coverage quality and GIS discrepancy candidates. The first-five previews also include original shape-sequence rows restricted to the four study-intersecting shape IDs; the full shape-point table is not duplicated. The geojson products contain published static stop points and clipped shape paths only. No active layer is authored.

`validate(root, service_date=None)` returns the verified report without network requests. It checks the comparison snapshot, required artifact receipt and every cached/page/index/ZIP/tool dependency, including the GIS request-cache/provenance chain used for comparison. It recomputes separate read-time feed status and scheduled counts for the supplied service date, or current America/New_York date. Expired and not-yet-effective feeds remain visibly labeled; they do not silently become current service. Original October 28 evaluation results remain identified as that date's schedule.

Rebuild refuses manually modified/unreceipted generated outputs and backs up the prior good packet/GeoJSON/receipt. Failed acquisition, schema/FK/calendar validation or changed source bytes cannot replace the previous publication. Numeric rate limits and precise GTFS refresh cadence are not published; the [LYNX GIS overview](https://www.golynx.com/maps-schedules/gis-gtfs-lynx.stml) describes GIS updates with three annual bid changes, which is not a guaranteed exact GTFS refresh schedule. Stops/shapes are WGS84; comparison distances use EPSG:32617 metres. No vertical datum, current arrival, traffic load or ADA compliance is inferred.

## Remaining #15 acceptance

The previous GTFS access/calendar gap now has actual source data and validity evidence. Root can integrate the verified packet as paginated read-only schedule/reference tables, date-aware summaries and source/quality previews. Independent review and actual API/UI checks remain pending for this delivery. The separate FDOT RCI/traffic packet must still establish actual Edgewater coverage, source units and unmatched records. The combined City backbone, OSM supplemental namespace, FDOT and LYNX outputs need one independent ticket-level coverage/ID/date review before #15 closure. This supplement alone does not close the ticket or claim live operations.

## App integration

`GET /api/v1/transit_schedule?service_date=2026-10-28` returns validated schedule validity, calendar-derived counts, source fields, first five safe rows and limits. The optional date defaults to the agency's New York date. Invalid dates return an error; unavailable/stale dependencies reject the response. No agency call occurs during display.

The existing `/transit` page now includes a service-date selector and expandable schedule evidence alongside the separate static GIS map. Actual API/browser checks verified October 28 (100 scheduled stop-serving trips; 170 including passing shape trips) and January 1, 2027 (expired; UI says availability unknown instead of implying zero service). Source-schema/sample rows were inspected. [Actual browser view](evidence/lynx-schedule-browser.png). Static route 89 remains visible as a separate older GIS reference and its absence from current intersecting GTFS shapes is flagged, not treated as proof of cancellation.

The old `config/transit_sources.json` HTTPS timeout describes the earlier GIS adapter's probe, not current GTFS access. This additive validated packet and live page supersede that availability statement without rewriting the frozen GIS acquisition.

Independent source/geometry/calendar review passed, including the final shape-point preview and coordinate/sequence guards. [Review record](evidence/lynx-gtfs-review.json) binds the final packet checksum. Broader #15 network, parking and mobility requirements remain open.
