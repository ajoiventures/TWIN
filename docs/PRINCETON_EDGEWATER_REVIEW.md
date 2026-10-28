# Princeton Street / Edgewater Drive road review

Reviewed October 28, 2026 against active snapshot `20261028T160543372334Z`. Priority: conference demonstration focus. The existing intersection is **not yet accepted as dimensionally accurate**.

## Measured source comparison

Within 160 m of the City centerline intersection, sample both directions at intervals no greater than 2 m in EPSG:32617. These measurements compare OSM model inputs with City GIS centerlines; neither is independent survey control.

| Road | City-to-OSM median | 95th percentile | Maximum |
|---|---:|---:|---:|
| Edgewater Drive | 0.38 m | 1.33 m | 1.36 m |
| W Princeton Street | 0.47 m | 1.33 m | 1.36 m |

Reproduce: `python tools/review_roads.py`. Detailed source-way IDs, fallback widths, raw lane tags and method limits are in ignored `data/transport/princeton_road_review.json`.

## Geometry findings

- Edgewater uses generic 10 m or 11 m widths based on highway class; none of the four nearby OSM ways supplies a width. Raw lane tags vary from two to three. The model does not convert these into a reviewed cross-section.
- Princeton uses a generic 11 m width, with no width tags in its two nearby source ways.
- The sidewalk/shoulder surface is a uniform buffer extending 2 m beyond each road. It is not an accepted sidewalk boundary, accessible path or corner treatment.
- Edgewater has a single schematic yellow centerline. Turn pockets, lane separators, bike/parking lanes, stop bars, four intersection crosswalks and sidewalk corner geometry are not reconstructed from accepted evidence.
- Local visual review of the January 2025 OCPA aerial shows zebra crossings on all four arms at Princeton, contrasting corner paving, adjacent curbside parking and lane/turn markings. This is a dated visual observation, not proof of current conditions or a survey. Source imagery remains local and is not redistributed or activated as scene geometry.

## Existing versus proposed

The [City project page](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project), checked October 28, describes the existing road diet with one travel lane each direction, on-street parking and bicycle lanes. Proposed design removes on-street bicycle lanes and expands sidewalks from as little as 5 ft to 9–12 ft. These corridor statements do not assign a single width to every block or intersection. The Lakeview roundabout timeline currently indicates construction beginning early 2027; it must remain a future scenario, not be shown as an existing Princeton treatment.

## Required correction and conference acceptance

1. Obtain an accepted existing-condition road/curb plan or dated reference with adequate measurement/reuse rights. Record the Princeton intersection footprint and all four approach lane/turn layouts; retain uncertainty where obscured.
2. Reconstruct road edges and corner radii, then crossing/stop-bar geometry and sidewalk continuity. Do not stamp generic stripes across the whole corridor.
3. Review curb cuts, parking interruptions, signals and vegetation against that same dated baseline. Cars and trees must clear the accepted walking/crossing paths.
4. Validate the intersection in plan view and from the tilt-shift presentation camera; compare existing and future scenarios explicitly.
5. Capture a repeatable presentation frame and benchmark the actual conference display resolution. Visual quality and engineering accuracy remain separate acceptance checks.
