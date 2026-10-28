# College Park and Main Street focus

The detailed focus is **College Park Main Street**, with the wider **College Park neighborhood** as context. These are distinct official City polygons, not interchangeable labels or a rectangular district boundary.

Sources:

- City `OrlandoMainStreetProgram/FeatureServer/0`, `BUISNESSNE='College Park'`, OBJECTID 3, GlobalID `88cb7589-7266-449e-85f6-532359ab4cef`.
- City `OrlandoPoliticalNeighborhoods/FeatureServer/0`, `NeighborhoodName='College Park'`, Object_ID 1737, NeighborhoodID 13.
- Both use the public City organization `mMuoPCaIYD4wEgDl` and owner `OpenData_Orlando`. Query full polygons by name, not the current extraction bbox. Native EPSG:2236 feet is transformed to WGS84 for interchange and EPSG:32617 meters for the map/scene.

`python tools/study_boundaries.py` saves full reference polygons and provenance in local `data/processed/study_boundaries.geojson` and `study_scope_quality.json`. The City layer edit timestamps are separate from item-modification timestamps. No effective/adoption date is inferred.

October 28 checks: Main Street approximately 390,204 m² (96.42 acres), neighborhood 8,374,758 m² (2,069.45 acres). About 12,910 m² of Main Street lies outside the neighborhood polygon; preserve separate memberships and use the union for combined focus rather than intersecting away valid Main Street sections.

The expanded extraction and actual 3D ground now cover **100% of the official Main Street area**, with **0 m� uncovered**, and **60.77% of the wider neighborhood**. The extraction spans [-81.398, 28.5602, -81.379, 28.5858] and contains 13,999 source footprint subareas grouped into 3,216 modeled buildings. These are spatial coverage checks, not verified building/sidewalk completeness. Snapshot: `20261028T160543372334Z`. The browser map defaults to Main Street, offers a whole-neighborhood view, displays both City boundaries and labels current 3D coverage. Alignment uses common real-world coordinates; no surveyed accuracy or completed aerial-control-point registration is claimed.

## Out-of-map placements

`python tools/constrain_scene.py` applies a reversible display guard based on the actual current ground polygon. It hides 31 out-of-bounds car/furniture objects and 102 tree instances whose centers or full canopies cross the ground boundary, plus the broad context backdrop. The checked composition has zero remaining visible object/tree spillovers. Original source geometry and placement records are retained. The slanted projected ground edges are checked against mesh vertices, not just world-axis bounding boxes.

This guard is a display boundary, not a substitute for official neighborhood/Main Street membership or field-verified planting/parking locations. It remains a separate USD layer. Source generation and future terrain refresh must preserve/recompute it.
