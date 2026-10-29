# Full-neighborhood City park inventory

Delivery for #4/#22, October 29, 2026 UTC. The official City park service was queried across the complete official College Park neighborhood envelope, then clipped against the actual neighborhood polygon. This supplements the smaller frozen extraction; it does not expand the 3D scene.

The service returned 14 unique candidates. Eleven have positive-area neighborhood intersections; three outside candidates are excluded. All eight previously extracted park records remain, with unchanged source geometry. Additional records are Mathews Park (113), Overbrook Park (121) and Don Dudley Park (81). Albert Park is the only returned park footprint intersecting the official Main Street polygon.

## Reproduce and inspect

Run `python tools/inventory_neighborhood_parks.py --offline` using the configured project Python and existing cached inputs. Omit `--offline` to allow missing bounded source requests. The helper reuses the existing cached City client and writes only `data/land/full_neighborhood_parks/`: inventory, clipped GeoJSON, coverage diagram and checksum receipt. Existing outputs are guarded against manual alteration and backed up before replacement. Original source responses stay in the ignored cache. The active snapshot, source geometry and user scene are unchanged.

`validate(root)` checks all three published artifacts and source/tool dependencies without agency requests. `/api/v1/full_neighborhood_parks?limit=5`, `/api/v1/full_neighborhood_parks_quality` and `/parks-inventory/coverage` expose validated results. The local `/source-browser` page shows fields, first five records, coverage and provenance, alongside the supplemental City address and future-land-use datasets.

Coordinates are WGS84 for published GeoJSON; intersection areas use EPSG:32617 metres. Source OBJECTIDs remain strings. Retrieval, source edit, acquisition and effective dates are distinct; the latter two remain unknown. Park footprint area can include water and is not usable park acreage.

## Acceptance and remaining scope

[Independent review](evidence/full-neighborhood-parks-review.json) reconciled advertised IDs against all returned features, independently repeated clipping/area calculations, verified the original eight and checked output hashes. Root integration verifies the local API and actual browser display. This establishes published-service coverage only, not all public/private/school/County open space.

Legal ownership, current public access, hours and amenities remain unverified. Park categories do not prove ownership or available development land. Full government-owner classification, vacancy, governing zoning/FLU/PD conditions and accepted park-site details remain ticket requirements; neither #4 nor #22 is closed by this inventory.
