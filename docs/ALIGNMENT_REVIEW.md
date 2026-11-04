# College Park coordinate alignment review

October 29, 2026 · Ticket #5 remains open · Snapshot `20261028T160543372334Z`.

The offline run of `tools/review_alignment.py` checked **ten distributed City Main Street boundary vertices against the actual composed USD curve**, plus **ten original DEM-grid ties against the separate inactive terrain proposal**. Both numerical consistency screens passed. This establishes coordinate arithmetic and serialization consistency; it does **not** establish independently surveyed positional accuracy.

## Actual results

| Comparison | References | East/west span | North/south span | RMS residual | Maximum residual |
|---|---:|---:|---:|---:|---:|
| City source boundary → composed Main Street curve | 10 | 777.20 m | 2,816.90 m | 0.00000849 m | 0.00002166 m |
| Original native DEM grid → inactive terrain proposal | 10 | 1,860.93 m | 2,835.96 m | 0.00002937 m | 0.00004907 m |

The independently calculated origin is WGS84 longitude/latitude `[-81.389, 28.572]`, projected to UTM17N. East increases local X; north increases local Y. The composed scene declares meters and Z-up. The software screen is **0.001 m**, chosen to detect transform/float32 serialization regressions. It is **not a City, USGS, survey or construction tolerance**.

The ten City references are vertices of official College Park Main Street OBJECTID3, GlobalID `88cb7589-7266-449e-85f6-532359ab4cef`. The cached response is revalidated through the existing offline Client and must exactly match the derived reference polygon. Farthest-point sampling provides geographic distribution rather than ten adjacent points.

| Vertex index | Source longitude | Source latitude | Residual, m |
|---|---:|---:|---:|
| 64 | -81.388917083861 | 28.560287756964 | 0.00000787 |
| 1 | -81.393569308910 | 28.585700856353 | 0.00001189 |
| 77 | -81.388502665200 | 28.573654652119 | 0.00000035 |
| 96 | -81.385606535991 | 28.581608064030 | 0.00000586 |
| 71 | -81.388796685264 | 28.566662089723 | 0.00000002 |
| 21 | -81.390125945765 | 28.578420115415 | 0.00000185 |
| 29 | -81.390023487962 | 28.583079891033 | 0.00002166 |
| 35 | -81.389876340283 | 28.570318646615 | 0.00000255 |
| 31 | -81.389957931313 | 28.563794801076 | 0.00000178 |
| 93 | -81.387030221324 | 28.571541254413 | 0.00000060 |

## Independence and source limits

The scene composer uses PROJ. This review separately implements the WGS84 transverse-Mercator series through the sixth-order term, then subtracts its independently computed origin. The calculation is checked against PROJ at nine locations across the project. City points are compared to the nearest actual authored curve, including its world transform; no invented closing segment or extraction-rectangle boundary is substituted.

The retained City query explicitly requested WGS84 `outSR4326`; independent native-coordinate point attributes were not retained. Its source polygon and the scene outline represent the **same source**, so close agreement cannot expose a common error in the original City geometry. Layer-edit/item dates do not establish effective dates or survey accuracy; the source's effective date remains unknown.

The second comparison reads the six original, receipt-hashed USGS/FDEM GeoTIFFs: native EPSG6438, NAD83(2011)/Florida East, US survey feet, 2.5-foot pixels. Actual GeoTIFF scale/tiepoint/CRS/unit tags must agree with the grid, and every chosen source pixel must be valid and inside the extraction. Native grid centers are compared to the float32 terrain-proposal coordinates after the declared datum operation and independent UTM calculation. This is a **grid/transform check on an inactive proposal**, not a control-point check of the active flat ground. The operation reports 2 m accuracy in its EPSG metadata; that value is not a measured dataset error or project acceptance tolerance. Acquisition is December2018–April2019, separate from retained October2026 retrieval receipts.

The reviewer identified a robustness gap in inferring source pixels by inverse-transforming and snapping the mesh coordinates: a whole-pixel translation could snap to another valid pixel. The helper now reconstructs the full **141,934-vertex source order from the source validity/inside mask, stride and accepted quad corners**, checks the mesh count, and associates each selected mesh vertex with its independently determined original row/column. It applies the proposal's full local-to-world transform before comparing. A one-pixel displacement is therefore detectable rather than relabeled as a different source pixel. Targeted checks cover a whole 2.5-foot pixel shift, an actual USD ancestor translation and a mismatched vertex count. The actual artifact still passes with the residuals above; the current proposal transform is identity.

**No independently surveyed control network or source-supported positional acceptance tolerance was available in the retained evidence.** The report records zero survey controls and a null tolerance. A task-specific control source and justified acceptance tolerance are still needed before claiming external positional accuracy. No new acquisitions were made for this review.

## November 3 follow-up on available control

The [NOAA Data Explorer bounds query](https://geodesy.noaa.gov/api/nde/bounds?minlat=28.552917&maxlat=28.590025&minlon=-81.404656&maxlon=-81.375076) returned 36 marks in the neighborhood bounding box. Exact polygon screening found nine in the official neighborhood and zero in either Main Street or the Edgewater focus corridor. The index identifies nine adjusted horizontal positions, 17 `HD_HELD1` positions and ten scaled positions. The adjusted positions use NAD83(1990) and are approximately 845–1,506 m from the corridor centerline in a screening projection. The bounds response SHA256 is `77ed6ffde8cedbcb10158f3e3cf659de1c5d25f97332f3aea7f447df01203c1b`. [NOAA index documentation](https://geodesy.noaa.gov/web_services/data-explorer.shtml)

Three adjusted marks fall in the neighborhood. Two are I-4 marks and one is a radio tower. The latest recovery listed for I-4 mark AK0334 records that the mark could not be found in 1995. An eligible control needs a verified match to a scene feature and a documented datum transformation. The control screen found no such pair for Edgewater, so the survey-control residual and project tolerance remain unavailable. [AK0334 datasheet](https://geodesy.noaa.gov/cgi-bin/ds_mark.prl?PidBox=AK0334)

The [NAIP service metadata](https://imagery.geoplatform.gov/iipp/rest/services/NAIP/NAIP2023_CONUS/ImageServer) describes generic ±6 m true-ground rectification for its stated 1 m and 60 cm products. The map uses local 30 cm source rasters. A tile-specific accuracy report is still needed to establish an applicable source tolerance.

## Building counterpart identity

The selection bridge now retains the exact registered building ID when Kit publishes a building selection. The map highlights that footprint and styles the other parcel footprints as context. A parcel selection continues to request all accepted building counterparts. The editor verifies each expected USD path against its own registered entity ID and reports partial delivery when scene identity or snapshot evidence is missing.

Seven selection bridge tests passed, including the same-parcel swapped-identity regression in a real USD stage. A browser session backed by a temporary copy of the current registry and parcels received a simulated Kit event for `Building_2945`. It highlighted that building while showing `Building_2978` as parcel context. Selecting 2204 Edgewater returned both registered scene paths, and selecting 1615 Edgewater displayed the unmatched state.

The footprint inspector now offers **Select this building in 3D**. The isolated Kit probe used the full saved scene and the normal workspace event handlers. The building request selected only `Building_2945`, the parcel request selected both registered paths, and `ocpa:99613` reported unmatched. Programmatically selecting `Roof_2945` through Kit's selection API published the exact building identity. Browser inspection separately confirmed that the action prompts for the link to be enabled when the link checkbox is off. [Native event evidence](evidence/native-exact-building-selection.json)

The subsequent connected replay used an actual browser action and a dedicated Kit process sharing an isolated selection bridge. Clicking **Select this building in 3D** for Building_2945 selected exactly its USD path and received the editor acknowledgment. Selecting Roof_2978 through Kit's selection API then highlighted Building_2978 in the same browser, with both buildings shown as parcel context. The browser later reported the link unavailable when the dedicated service shut down. Manual viewport picking and field positional tolerance remain pending. Existing Kit instances need to load the updated workspace code before using the exact-building action. [Connected replay evidence](evidence/browser-native-selection-replay.json)

## Remaining ticket #5 gates

| Criterion | Evidence and remaining limit |
|---|---|
| Distinct neighborhood/Main Street/focus geometries | Official separate neighborhood/Main Street polygons exist, with provenance and incomplete neighborhood 3D coverage recorded in [STUDY_SCOPE.md](STUDY_SCOPE.md). The 85.44 m Princeton–southern Smith review pilot is an explicitly chosen focus segment, not an official whole-corridor boundary; see [PILOT_BLOCK.md](PILOT_BLOCK.md). |
| Ten distributed references and tolerance | Numerical checks delivered here. Source-supported external positional tolerance/control gate remains unavailable. |
| Parcel/building/street map and dated licensed basemap | Main map draws cached projected vectors and source attribution. Dated local aerial review exists separately; the main parcel map still lacks a fully accepted dated reference basemap/registration and redistribution eligibility must not be inferred. |
| Stable counterpart selection | Exact-feature map↔Kit delivery, unmatched and clearing have prior runtime evidence. Native roof-picking fixes and checkbox acceptance remain open in [workspace-native-controls.json](evidence/workspace-native-controls.json); a function pass is not a final user-interaction acceptance. |
| Existing/proposed separation | Proposal layers and optional context remain separate. Future scenario geometry and its full user-control acceptance remain open; this review promotes no geometry. |

## Reproduce and preserve

Run the repository's configured Python with `python tools/review_alignment.py`. Outputs are ignored `data/processed/alignment_review.json` and `alignment_reference_points.geojson`; they include all twenty point records, native headers, dates, source identifiers and input SHA256s. Re-run after relevant reference/scene/frame changes. Three focused arithmetic/distribution/source-order checks pass in `tests/test_review_alignment.py`. The analysis is ready to share **with the explicit accuracy and scope caveats above**, not as full ticket acceptance.

Contract: inputs are the cached official boundary, composed USD, declared project frame and retained DEM originals/proposal; outputs are the report and point map. No network, scene, snapshot, registry, source or user-session writes occur. Missing/stale sources fail explicitly. Rollback is retaining/removing these report files; there is no activation mode. Independent acceptance remains with the integrating reviewer.
