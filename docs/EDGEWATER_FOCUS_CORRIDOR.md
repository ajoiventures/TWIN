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
