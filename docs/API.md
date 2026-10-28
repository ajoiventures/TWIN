# Local read-only API

Run `python tools/serve.py --port 8768` and open `http://127.0.0.1:8768`. This binds to localhost only and serves the last complete local snapshot. Requests never call source agencies.

GET `/api/v1/health`, `/api/v1/sources`, `/api/v1/quality`, `/api/v1/map`.

GET `/api/v1/{parcels,buildings,streets,neighborhoods,zoning,parks,permits,businesses,building_review}` accepts `limit` (1–1000), `offset` (nonnegative), and optional `parcel_id`. GeoJSON collections return feature rows; other tables return record rows. Responses include snapshot, total, limit, offset and rows. Source/quality reports are served directly as appropriate. Unknown tables return 404; invalid pagination returns 400; missing snapshots return 503. Writes return 405.

Examples: `/api/v1/parcels?limit=5`, `/api/v1/permits?parcel_id=292223149200010&limit=5`.

The map links parcel selection to building IDs and USD paths. This is an inspection map, not an authoritative survey or a replacement for agency source viewers.

Building heights: `/api/v1/heights` and `/api/v1/height_quality`. Building and map responses include applied height, method and quality for the matching active snapshot. Historical LiDAR and floor-count estimates remain distinct.

Semantic evidence: `/api/v1/assets`, `/api/v1/asset_quality`, `/api/v1/scene_validation`. Building rows also include stable source-based entity IDs and evidence references when the current registry exists. `/api/v1/pilot` returns the bounded review extent and its limitations. A mismatched derived snapshot returns HTTP 409; a missing required local product returns 503.

Discovery products: `/api/v1/source_catalog`, `/api/v1/pedestrian_access`, `/api/v1/crosswalk_candidates`. These retain their own probe/source dates and review flags; the active snapshot wrapper does not imply acceptance or synchronization with that snapshot. Crosswalk candidates remain draft/status-unresolved reference data, excluded from accepted scene geometry.
