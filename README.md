# TWIN — College Park, Orlando

An Omniverse/OpenUSD prototype and a source-traceable GIS ingestion project for College Park and Edgewater Drive.

## Work plan

- [GitHub roadmap](https://github.com/ajoiventures/TWIN/issues/14)
- [Ticket specifications](TICKET_PLAN.md)
- [Transportation and sidewalk plan](docs/TRANSPORTATION_PLAN.md)

The current scene's trees, vehicles, storefront designs, uniform heights and sidewalks are illustrative. The transportation plan replaces centerline-buffer approximations with verified pedestrian and roadway geometry before final asset placement.

## Official-source snapshot pipeline

Use Python 3.12 and install `requirements.txt` into your environment, or into `.dependencies` with `python -m pip install --target .dependencies -r requirements.txt`.

`python tools/data_pipeline.py` retrieves bounded official OCPA parcel data, city streets/neighborhoods/zoning/parks, recent parcel-linked permit records, and historical/current business license rows. `--force` rechecks sources; `--offline` reuses the cache and fails on an unavailable cached request. All source calls have timeouts and bounded retry behavior. Per-source field allowlists exclude owner/contact/free-text columns.

Outputs are local, ignored by Git:

- `data/cache/official/`: cached source responses.
- `data/snapshots/<UTC timestamp>/`: source metadata, normalized parcels, building links, GIS collections, permit/license rows, quality report and review queue.
- `data/processed/active.json`: atomic pointer to the last fully successful snapshot. A failed refresh leaves the prior pointer intact.

The original public-data base scene must be at `scene/college_park.usda` for footprint-to-parcel matching. Build it with `tools/build_scene.py` after reviewing source terms. Scene generators are a prototype; portable Kit setup, a local serving API and full scene integration are still open baseline tasks.

Permit retrieval uses parcel IDs rather than relying only on potentially incomplete point geocoding. Permits are currently limited to processed dates from October 27, 2024 onward. An attached permit is parcel context, not a verified exact-subject-address match. Business license case numbers may occur in multiple source rows; rows are retained by source row ID and must not be treated as a unique list of current storefront tenants.

No private BOOMS source values are imported or included in this repository. The existing local source project remains read-only and its release gates still apply.

Run checks with `python -m unittest discover -s tests -v`.

## Prototype history

See [prototype notes](docs/PROTOTYPE_HISTORY.md). Existing workstation launch scripts remain in the original prototype folder. New scene generators and detailed-asset work are being migrated into this repository; their presence alone does not mean all ticket acceptance criteria are complete.
