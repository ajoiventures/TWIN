# TWIN — College Park, Orlando

An Omniverse/OpenUSD prototype and a source-traceable GIS ingestion project for College Park and Edgewater Drive.

## Work plan

- [GitHub roadmap](https://github.com/ajoiventures/TWIN/issues/14)
- [Ticket specifications](TICKET_PLAN.md)
- [Transportation and sidewalk plan](docs/TRANSPORTATION_PLAN.md)

Building heights now distinguish historical LiDAR from floor-count estimates. Ground remains flat; storefront designs, sidewalks and detailed tree/car placement are illustrative. The transportation plan replaces centerline-buffer approximations with verified pedestrian and roadway geometry before final placement.

## Official-source snapshot pipeline

Use Python 3.12 and install `requirements.txt` into your environment, or into `.dependencies` with `python -m pip install --target .dependencies -r requirements.txt`.

`python tools/data_pipeline.py` retrieves bounded official OCPA parcel data, city streets/neighborhoods/zoning/parks, recent parcel-linked permit records, and historical/current business license rows. `--force` rechecks sources; `--offline` reuses the cache and fails on an unavailable cached request. All source calls have timeouts and bounded retry behavior. Per-source field allowlists exclude owner/contact/free-text columns.

Outputs are local, ignored by Git:

- `data/cache/official/`: cached source responses.
- `data/snapshots/<UTC timestamp>/`: source metadata, normalized parcels, building links, GIS collections, permit/license rows, quality report and review queue.
- `data/processed/active.json`: atomic pointer to the last fully successful snapshot. A failed refresh leaves the prior pointer intact.

The public-data base scene must be at `scene/college_park.usda` for footprint-to-parcel matching. Build it with `tools/build_scene.py` after reviewing source terms. The local snapshot API and composed scene are connected; geographic acceptance, terrain and pedestrian accuracy remain open.

Permit retrieval uses parcel IDs rather than relying only on potentially incomplete point geocoding. Permits are currently limited to processed dates from October 27, 2024 onward. An attached permit is parcel context, not a verified exact-subject-address match. Business license case numbers may occur in multiple source rows; rows are retained by source row ID and must not be treated as a unique list of current storefront tenants.

No private BOOMS source values are imported or included in this repository. The existing local source project remains read-only and its release gates still apply.

Run checks with `python -m unittest discover -s tests -v`.

## Local scene and application

Run these steps in order after the base scene and official snapshot exist:

1. `python tools/detail_edgewater.py`, then `python tools/build_detailed_assets.py` generate original illustrative details/assets. The asset-upgrade generator requires the detail layer. Review generator outputs before replacing an edited layer.
2. For historical LiDAR evidence: `python tools/sample_lidar.py`, `python tools/validate_vertical_units.py`, then `python tools/build_heights.py`. The first two download/cache public pilot data; floor estimates remain outside accepted LiDAR coverage.
3. `python tools/semantic_registry.py`, `python tools/connect_scene.py`, then `python tools/validate_scene.py` build stable source-based identities and inspect the composed local visualization profile.
4. `python tools/configure_editor.py --kit-root <Kit SDK release folder>` creates an independent editor configuration and `Open College Park.bat`. It does not modify the SDK. `tools/prepare_workspace.py` forwards to this portable setup.
5. `python tools/serve.py` starts the read-only map/API at `http://127.0.0.1:8768/`.

Regenerate height evidence and semantic layers after changing the active snapshot. Derived API products reject stale snapshot associations. The local visualization validator does not certify physics, ADA compliance or NVIDIA SimReady readiness. It checks units, mesh indices, finite points, source identity coverage, file hashes, height agreement and dependencies, including instance proxies.

Source discovery: `python tools/source_catalog.py` and `python tools/pedestrian_discovery.py`; `--offline` replays caches without claiming fresh agency data. See [source catalog](docs/SOURCE_CATALOG.md), [pedestrian access](docs/PEDESTRIAN_ACCESS_REPORT.md), [platform plan](docs/SMART_CITY_PLATFORM_PLAN.md), and [AI management](docs/AI_TEAM_MANAGEMENT.md).

Cached requests preserve known network-fetch dates; legacy caches have unknown original retrieval times. Snapshot-build time is distinct from source acquisition and download time. No live agency request is made by the interactive map/API.

## Prototype history

See [prototype notes](docs/PROTOTYPE_HISTORY.md). The original prototype remains separate. Migrated generators and working local connections alone do not establish full ticket acceptance; source coverage and release evidence are tracked on the roadmap.
