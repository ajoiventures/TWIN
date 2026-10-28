# College Park digital twin — prototype 02

An editable geographic base for College Park, Orlando, centered on Edgewater Drive. This is the foundation for a digital twin, not yet a live operational twin.

## Edgewater visual detail update

The launcher now opens `scene/college_park_realistic.usda`, which composes the original geographic base with the separate `scene/edgewater_details.usdc` detail layer. The original `college_park.usda` remains unmodified by this update.

- 484 instanced trees: broad shade trees and palms along Edgewater and nearby residential streets. Placement is procedural, with building, road, and water clearance checks; it is not a surveyed tree inventory.
- 126 commercial building groups near Edgewater receive 367 storefront bays, dark reflective glazing, framed doors, awnings, masonry plinths, cornices, and generic category signs.
- 32 benches, planters, 27 decorative lamps, and 100 schematic static vehicles provide street scale.
- Original procedural textures for asphalt, concrete paving, brick, stucco, roofing, bark, and ground, plus varied facade colors and warmer daylight.
- Two new cameras: **Tree-lined Edgewater** and **Storefront walk**. New layer switches control trees, storefronts, street furniture, and parked vehicles.

Storefront designs and signs are illustrative, not verified business identities or as-built facades. Trees and furniture do not claim exact existing locations. The city's [2009 Edgewater Vision Plan Support Document](https://www.orlando.gov/files/sharedassets/public/v/1/documents/city-and-district-plans/edgewater_support_document_v1-4.pdf) informed the general visual vocabulary (awnings, arcades, palms); it is not a current property inventory. The [city's street project](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project) provides project context, not the modeled construction design.

All texture imagery was generated procedurally locally; no downloaded street photographs are embedded. Counts and limitations are in `data/detail_manifest.json`. Regenerate the detail layer with `tools/detail_edgewater.py`; save a separate copy before manually editing that generated layer.

## Open

Double-click **Open College Park.bat** in this folder. It uses the existing Omniverse Kit installation at `C:\Omniverse\kit-app-template`. Allow initial renderer startup to finish.

The scene opens automatically. The **College Park | Project** panel contains three camera views, layer switches, and **Save scene**. Its tab shares space with **Stage**, where all geometry is organized. The **Property** panel edits selected objects. File, Edit, and Create menus and transform tools are enabled.

Use the saved views to return after exploring. Standard Omniverse navigation is available in the viewport; select an object and press **F** to frame it. Save your work through File > Save or the project panel. Rebuilding from source replaces the generated scene, so save a separate copy before making manual edits.

## Included geographic base

- 3,090 building groups made from 13,500 property-appraiser footprint subareas, dissolved by parcel and building number.
- 1,250 OpenStreetMap street/path segments, 3 park polygons, and 18 water polygons.
- Flat ground, simplified building masses and roofs, lighting, and three cameras.
- Parcel identifiers, source object identifiers, estimated heights, and residential/commercial classification on building objects.
- A self-contained OpenUSD scene at `scene/college_park.usda` with no external asset dependencies.

## Geographic reference

- Study rectangle: longitude -81.398 to -81.379; latitude 28.5605 to 28.5845. This is not an official neighborhood or Main Street boundary.
- Projection: WGS84 / UTM zone 17N (EPSG:32617), with projected coordinates of longitude -81.389, latitude 28.572 subtracted as a local origin.
- Scene units: meters. X east, Y north, Z up.
- Ground elevation is zero throughout; no vertical datum or surveyed elevations are represented.

## Sources and accuracy

Building footprints: [Orange County Property Appraiser public GIS, Building_FootPrints layer 28](https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28). Original features are cached in `data/buildings.geojson` and their retrieval batches. This layer includes building subareas, not necessarily one polygon per entire structure; dissolving uses available parcel/building identifiers. Source geometry is used as published, not survey verified. Review source terms before distributing derived data.

Streets, paths, parks, water: **© OpenStreetMap contributors**, [ODbL attribution and license](https://www.openstreetmap.org/copyright). The raw Overpass response is cached in `data/openstreetmap.json`. Preserve source attribution and review ODbL obligations when distributing the data or derivatives.

Retrieval time, counts, bounds, and source links are recorded in `data/manifest.json`.

All building heights are **estimates**: residential 4.2 m and commercial 6.5 m. Roofs are flat placeholders. Street widths are inferred by road category except where an OSM width is available. The surrounding strips are schematic shoulders/sidewalk context, not engineered sidewalk alignments. The base layer has no imagery, measured terrain, facade details, trees, live traffic, sensors, or simulations. Prototype 02 adds the illustrative details described above. OSM closed ways are included; relation-only water and park features may be missing.

## Next modeling priorities

1. Confirm the project boundary and intended use (planning, business directory, traffic, events, or other).
2. Replace flat ground and estimated heights with licensed elevation/LiDAR data.
3. Refine Edgewater Drive intersections, sidewalks, building entrances, and recognizable storefronts.
4. Attach business or asset records to stable identifiers.
5. Add live feeds or simulations only after the geographic base is verified.

## Rebuild

The generator is `tools/build_scene.py`; Python dependencies are isolated in the parent workspace's `.dependencies` folder. It reuses cached source downloads. Run with the bundled Python runtime already used for this project. `tools/prepare_workspace.py` regenerates the separate workspace configuration and launcher without modifying the original viewer configuration.

The launcher uses `C:\Omniverse\college_park_boot.py` as a small bridge to handle spaces in the project path. The main project remains in this folder. Moving the project requires updating the root path in `tools/open_workspace.py` and regenerating the launcher.
