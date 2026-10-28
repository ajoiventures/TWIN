Documentation starts at [the living project index](docs/INDEX.md), which links the latest applicable plans, evidence and source-revision rules.

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

The public-data base scene must be at `scene/college_park.usda` for footprint-to-parcel matching. After reviewing source terms, run `python tools/acquire_footprints.py`, then `python tools/build_scene.py`, then `python tools/data_pipeline.py`. The shared `config/study_area.json` extent fully contains the official Main Street district; acquisition checks the full source-ID set before replacing cached footprints. Generated Building_N aliases may change when scope expands; source identities remain the linkage authority. The local snapshot API and composed scene are connected; geographic acceptance, terrain and pedestrian accuracy remain open.

Permit retrieval uses parcel IDs rather than relying only on potentially incomplete point geocoding. Permits are currently limited to processed dates from October 27, 2024 onward. An attached permit is parcel context, not a verified exact-subject-address match. Business license case numbers may occur in multiple source rows; rows are retained by source row ID and must not be treated as a unique list of current storefront tenants.

No private BOOMS source values are imported or included in this repository. The existing local source project remains read-only and its release gates still apply.

Run checks with `python -m unittest discover -s tests -v`.

## Local scene and application

Run these steps in order after the base scene and official snapshot exist:

1. `python tools/detail_edgewater.py`, then `python tools/build_detailed_assets.py` generate original illustrative details and an inactive environment revision proposal. The asset-upgrade generator requires the detail layer and existing district composition. Compare actual renders before using `python tools/activate_environment_assets.py --apply`; activation checks captured asset hashes and preserves placements, manual layers and a rollback backup. This district upgrade workflow is separate from the clean-checkout [portable sample](docs/SAMPLE_BUILD.md).
2. For historical LiDAR evidence: `python tools/sample_lidar.py`, `python tools/validate_vertical_units.py`, then `python tools/build_heights.py`. The first two download/cache public pilot data; floor estimates remain outside accepted LiDAR coverage.
3. Reapply reviewed landmark corrections with `python tools/correct_wellesley.py` after rebuilding height evidence; see [required local inputs and guards](docs/WELLESLEY_CORRECTION.md). Then run `python tools/semantic_registry.py` and `python tools/connect_scene.py`. Fetch full official boundaries with `python tools/study_boundaries.py`, add their scene overlay with `python tools/compose_scope.py`, recompose with `python tools/connect_scene.py`, apply `python tools/constrain_scene.py`, and run `python tools/validate_scene.py`. This verifies the actual ground coverage and guards against visible spillovers.
4. `python tools/configure_editor.py --kit-root <Kit SDK release folder>` creates an independent editor configuration and `Open College Park.bat`. It does not modify the SDK. `tools/prepare_workspace.py` forwards to this portable setup.
5. `python tools/serve.py` starts the read-only map/API at `http://127.0.0.1:8768/`.

Regenerate height evidence and semantic layers after changing the active snapshot. Derived API products reject stale snapshot associations. The local visualization validator does not certify physics, ADA compliance or NVIDIA SimReady readiness. It checks units, mesh indices, finite points, source identity coverage, file hashes, height agreement and dependencies, including instance proxies.

Source discovery: `python tools/source_catalog.py` and `python tools/pedestrian_discovery.py`; `--offline` replays caches without claiming fresh agency data. See [source catalog](docs/SOURCE_CATALOG.md), [pedestrian access](docs/PEDESTRIAN_ACCESS_REPORT.md), [platform plan](docs/SMART_CITY_PLATFORM_PLAN.md), and [AI management](docs/AI_TEAM_MANAGEMENT.md).

Cached requests preserve known network-fetch dates; legacy caches have unknown original retrieval times. Snapshot-build time is distinct from source acquisition and download time. No live agency request is made by the interactive map/API.

## Prototype history

For source field lists and five-row previews, run `python tools/preview_tables.py`. It uses the configured study extent and writes to ignored `data/private/previews` by default. An optional local tracker must be explicitly selected with `--booms-tracker PATH`; no workstation-specific source path is assumed and the source CSV is read-only. Use `--output PATH` to choose another local preview directory. This utility performs bounded source requests; the interactive map continues to read cached snapshots.

See [prototype notes](docs/PROTOTYPE_HISTORY.md). The original prototype remains separate. Migrated generators and working local connections alone do not establish full ticket acceptance; source coverage and release evidence are tracked on the roadmap.

Main Street presentation: after defining the pilot, run `python tools/present_main_street.py` and recompose with `python tools/connect_scene.py`. The College Park Main Street saved view uses a closer 55 mm oblique camera, shallow depth of field and warmer light. Official outlines are hidden in this reversible presentation layer; geographic data remains available in the map and layer controls. This is a presentation improvement, not photogrammetric reconstruction.
