# Edgewater Drive focus corridor

The project review corridor follows the full Edgewater Drive centerline within the City’s College Park Main Street program boundary. The derivation selects cached City street features named `EDGEWATER DR`, projects them to EPSG:32617, clips them to the Main Street polygon and merges them into one line running south to north. The source comprises 33 City records, OBJECTIDs 4270–4302, with common CenterlineID 2271. [City Street Centerline](https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Street_Centerline/FeatureServer/0) · [City Main Street program boundary](https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/OrlandoMainStreetProgram/FeatureServer/0)

The review polygon uses the frozen Princeton–Smith pilot’s 60 m context distance on each side of the alignment, with flat ends and a Main Street boundary clip. The scope describes where to inspect the project. Right-of-way, sidewalk and proposed design geometry require their own sources. The City neighborhood and Main Street polygons remain separate reference layers. The overlay retains 12,542.828 m² of Main Street context outside the neighborhood polygon. [Pilot definition](PILOT_BLOCK.md)

| Derived measure | Result |
| --- | --- |
| Centerline length | 2,916.566 m |
| Corridor area | 300,843.187 m² |
| South endpoint, longitude and latitude | −81.3888926653, 28.5602880827 |
| North endpoint, longitude and latitude | −81.3931994831, 28.5851355510 |
| Source snapshot | `20261028T160543372334Z` |
| Project context rule reference date | October 28, 2026 |
| Observation and effective dates | Unknown |

## Script contract

Run `python tools/build_edgewater_focus_corridor.py` with the project Python runtime and dependencies. The builder reads the active snapshot pointer, cached streets, street metadata and source register, study boundary registry and frozen pilot. It atomically publishes `data/processed/edgewater_focus_corridor.json`. `validate(root)` compares the local packet to a fresh derivation from those six hashed dependencies. The packet contains two WGS84 GeoJSON features, `edgewater_focus_corridor` and `edgewater_focus_centerline`, and labels both `project_review_scope`. Source edit and retrieval dates are stored separately from unknown effective and observation dates. Consumers can project the overlay with their existing EPSG:32617 display transform.

The geometry replay confirmed full Main Street coverage by the street source query extent, a single simple line, endpoints on the program boundary and inclusion of the frozen pilot centerline. A union-first reconstruction from the cached City lines matched the exported centerline within 0.000001 m. The projected export’s area beyond Main Street was below 0.0001 m² after coordinate round-trip. These tolerances measure derivation and serialization consistency. A changed output metric and changed source bytes each triggered validation failure in separate temporary-copy probes.

## Sidewalk station review for SW-01

The updated screen lists nearby sidewalks outside the review polygon separately, using the same distance and heading rules. On the west side, it finds adjacent references for stations 0–60 m (`1416575073`) and the last 1.57 m (`1473552012`). This leaves **310 m west and 220 m east** without either an in-scope or adjacent sidewalk match. The original in-scope intervals and crossings reproduced exactly. The adjacent references identify places to reconcile with the aerial and mapped road edges. Actual continuity and the program boundary are separate questions. [Updated station screen](evidence/edgewater-sidewalk-station-adjacent.json)

All 39 unmatched station runs now have registered January 2025 OCPA aerial crops. The first 70 m west-side flag includes visible sidewalk outside the clipped review polygon. Cached OSM way `1416575073` is tagged as concrete sidewalk and lies wholly outside that polygon, with its nearest point 11.67 m from the City spine. A 58.38 m² trace of the visible portion overlaps 48.41 m² of its modeled sidewalk and 21.56 m² of the modeled Edgewater carriageway. These overlaps are measured separately and can share area. The clipped fragment is held pending road-edge reconciliation. Initial checks of west 1760–1780 m, east 1475–1495 m and west 2710–2730 m show intersections and marked crossings that need corner-level review. [Crop register](evidence/edgewater-sidewalk-aerial-registration.json) · [South trace audit](evidence/edgewater-south-visible-sidewalk-conflict.json)

The cached OpenStreetMap screen covers the full 2.92 km City spine on both sides. It matched 42 of the 80 tagged sidewalk ways intersecting the review polygon and located 19 tagged crossing ways that intersect the spine. The west side has 22 unmatched runs totaling 371.57 station metres. The east side has 17 totaling 220.00 m. The longest unmatched run is the first 70 m on the west side. Each run records its station endpoints, WGS84 coordinates and matching way ID where available. These are source-review locations. Actual sidewalk continuity, width, curb and ramp detail, and storefront and rear-lot walking links remain open. [Station inventory](evidence/edgewater-sidewalk-station-screen.json)

Run `python tools/review_edgewater_sidewalks.py --corridor data/processed/edgewater_focus_corridor.json --osm data/openstreetmap.json --output data/diagnostics/edgewater_sidewalk_stations.json`. The read-only screen projects cached inputs to EPSG:32617, probes each side at 5 m station intervals, and selects the nearest tagged sidewalk within 25 m whose local heading differs by at most 45 degrees. The output must be a new file. Each report pins both input hashes. Two real-input runs produced byte-identical reports, and the saved intervals on each side cover the full spine without overlap. Sampling can miss short features and the heading or distance rules can exclude real paths. An unmatched station needs review against aerial or City inventory evidence before it is treated as a physical gap.
