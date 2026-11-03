# Source building footprints on the property map

November 3, 2026. Existing ticket #5 remains open.

The [review map](http://127.0.0.1:8769/) now includes cached OCPA building-subarea outlines. Search a property to highlight its assigned and possible exact parcel-feature contexts. Select a footprint, or focus it and press Enter, to inspect its original source IDs and parcel contexts. The separate footprint toggle hides/restores the layer. Unaccepted contexts cannot publish a new 3D selection; switching off **Link property selection with 3D** keeps all inspection in the map.

These are original source-subarea unions, not surveyed wall lines, current reconstructed roofs or a physical-building census. Acquisition/effective dates remain unknown. Inherited parcel associations are retained: 2,976 accepted links already existed; this addition accepts zero new links.

## Reused source and adapter contract

`tools/build_map_footprints.py` fills the missing geographic footprint layer without replacing the existing snapshot, parcel API, lineage adapter or semantic registry. It reads the raw cached footprint extraction, active snapshot parcels, asset registry and validated transitive lineage. Geometry is projected from EPSG:4326 to the map's existing EPSG:32617 metre frame, then unioned by exact registered membership. Holes remain holes; orphan membership remains separate.

Run `python tools/build_map_footprints.py` to derive an immutable content-addressed GeoJSON under ignored `data/derived/map-footprints/` and publish its guarded local pointer/receipt. Run with `--validate` to check the current product. The reader checks the active snapshot, dependency hashes, transitive lineage fingerprints, coordinate/schema contract and complete property dictionary. Changed sources return an unavailable/stale response instead of an apparently current map.

`GET /api/v1/building_footprints` serves the validated cache with no-store caching. It returns 3,262 features: 3,216 registered source groups and 46 review-only groups containing 73 unrepresented subareas. Every one of the 13,999 raw OBJECTIDs occurs exactly once. The dictionary documents all 21 properties plus geometry. No external imagery or per-display agency request is included.

The [source-record preview](http://127.0.0.1:8769/source-browser?source=building_footprints) displays that complete dictionary and the first five records, including original IDs, assigned/candidate parcel-feature contexts, original floor values and explicit unknown dates. Large geometry arrays are represented by their geometry type in this readable preview; the original projected coordinates remain available from the API. An actual November 3 browser check verified 22 dictionary entries and Building_0000 through Building_0004 with provenance and policy flags. The screenshot remains local at `data/diagnostics/map_footprints_20261103/fields.png`. This preview does not alter selection or the source cache.

Three focused checks cover holes, conflicting/duplicate source membership, retained duplicate parcel-feature contexts, stale snapshot/tampered packet and transitive validation failure. Independent review replayed the full ID census and 27 distributed projected unions with zero symmetric-difference area. [Independent evidence](evidence/map-footprints-review.json).

## Actual runtime review and remaining work

On November 3, the separate preserving review service on port8769 returned HTTP200 with the expected snapshot and full dictionary. Actual browser review verified layer loading, property search and exact parcel selection, keyboard footprint inspection, footprint-to-parcel navigation, one context highlight and off/on toggling. The selection bridge, saved connected scene and manual layer hashes stayed unchanged. Actual pointer selection at 2204 Edgewater opens Building_2945 and its original OBJECTID1169695; both source groups highlight against exact parcel feature ocpa:332228. The screenshot remains local at `data/diagnostics/map_footprints_20261103/mainstreet.png`. An initial mouse click on Building_0000 did not open its inspector because its geometry is entirely outside the official boundary clip. Keyboard focus can still reach that invisible path; outside-scope keyboard accessibility remains a known usability gap, not a failed in-boundary pointer test.

The study map now requests `GET /api/v1/building_footprints?scope=study`. The response selects source groups with positive-area overlap against the same projected boundary union used by the display. The source-record endpoint without this filter serves all 3,262 groups. Actual browser inspection found 3,194 focusable footprint paths. The formerly invisible Building_0000 is absent from the map, and pressing Enter on Building_2945 opens its inspector.

The current review service runs on port 8769. The map offers a [separate Edgewater focus corridor](EDGEWATER_FOCUS_CORRIDOR.md) and a dated NAIP aerial reference. Full ticket #5 still requires source-supported positional tolerance, broader native counterpart verification, and independent acceptance.

## Dated aerial reference

Run `python tools/naip_basemap.py` to cache the local display image. The builder verifies four public Florida raster IDs, requests an EPSG:32617 export with those rasters locked, and records the returned extent, image dimensions, acquisition date and checksum. The image and manifest are stored in the ignored `data/imagery/naip_basemap/` directory. Map requests read this local cache. The overlay is off by default and displays date, source attribution and a catalog link when available. [GeoPlatform NAIP service](https://imagery.geoplatform.gov/iipp/rest/services/NAIP/NAIP2023_CONUS/ImageServer) · [USDA public-domain catalog entry](https://catalog.data.gov/dataset/national-agriculture-imagery-program-naip-imagery)

The four raster names record January 12, 2023 acquisition. The 1,600 × 2,000 JPEG has approximately 2.06 m export sampling. Projection and geometry checks confirm coverage of the full City neighborhood and Main Street polygons and both corridor features. Browser inspection verified the overview, the overlay at 2204 Edgewater, and separate visibility controls. The map places the image from its returned metre bounds using the same origin and axis conversion as the vector overlays. Field control and measured local positional accuracy remain outstanding. Screenshot evidence is local at `data/diagnostics/naip_basemap_20261103/2204-edgewater.png`.
