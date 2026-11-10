# Pedestrian source acquisition follow-up

## Edgewater crossing lifecycle and bus stop references — November 10, 2026

Two public consultant-hosted prioritization layers give explicit planning statuses for **39 Edgewater corridor lines**. All 39 match the May draft on the original object ID and projected geometry, with under 1 mm of Hausdorff and length difference. On these rows, May `PedPlan=1` matches **27 existing crossings considered for upgrades or additional treatments**, and `PedPlan=2` matches **12 proposed new crossings**. These are classifications in the planning packet. Retain separate status for the existing feature and its proposed treatment. Keep the other draft rows unresolved, including all code 0 rows. The “Existing Crosswalk (All Criteria Met)” layer returned five IDs inside the larger study rectangle, including Smith east ID 630, but its feature queries returned an ArcGIS error. Do not infer line attributes or assign status from that ID-only response. [Prioritization service](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/Task_Force_Meeting__Prioritization_WFL1/FeatureServer) · [39 exact matches and query evidence](evidence/edgewater-pedestrian-catalog-review.json)

The task-force bus stop layer reports eight Edgewater sidewalk spot references, all categorized as 3–5 ft with nearby curb cuts. The southbound Maury Road stop at station **2,491.73 m** is the only one marked without sidewalk connection. The eight Trapeze IDs each match a cached LYNX GTFS stop by ID and lie 0.61–0.80 m from those transit points. The contractor-hosted rows show August 20, 2025 record changes. Inspection dates, sidewalk edges, and route continuity remain unknown. Use these locations to target SW-01 field or aerial review, including both Rugby stops as distinct points. A separate LYNX reverification layer returned zero features in the same rectangle. [Task-force bus stop layer](https://services.arcgis.com/4qIOeADCgonipFEW/arcgis/rest/services/Orlando_Ped_Plan_Task_Force_Meeting__July__WFL1/FeatureServer/3) · [LYNX reverification layer](https://services2.arcgis.com/rp0R3ANPwsAdELpS/arcgis/rest/services/ADAStops_Reverification_20260410/FeatureServer/0)

The public City ArcGIS service directory returned 133 entries. The City organization keyword search returned the two known draft crossing web maps, and the City Open Data search returned a sidewalk café permit catalog entry. Orange County consultant gap, bundle, and 2024 active transportation layers returned 4, 2, and 1 features respectively in the study rectangle, with zero intersections with the exact Edgewater focus polygon. The City ADA Appendix L remains the reference for the underlying curb-ramp, sidewalk and marked-crossing inventory. The public queries did not locate those feature classes. The records request remains prepared in the [pedestrian access report](PEDESTRIAN_ACCESS_REPORT.md#records-request-draft--not-sent). [City public GIS page](https://www.orlando.gov/Our-Government/Records-and-Documents/Map-Library/GIS-Data-Download) · [City ADA Appendix L](https://www.orlando.gov/files/sharedassets/public/v/3/documents/public-works/ada-transition/14-appendix-l.pdf)

## Crossing support in the saved 3D roads

The [local Smith north paint preview](../data/diagnostics/smith_north_paint_20261104/review.usda) adds nine aerial-interpreted paint pieces (two borders and seven clearly visible bars) for the January 2025 condition. It projects the traced image coordinates into the established local frame and partitions each piece at existing road and shoulder edges. Each triangle follows its modeled support with a 2 mm display offset. The reopened USD contains nine paint meshes and 30 triangles. No traced area fell outside the union of those supports. The preview uses a plain paint material and contains no aerial image pixels. It does not cover the shadowed paint ends or reconstruct curb ramps. The saved production stage is untouched. Rendered inspection of the surface transitions is pending.

An elevation check of the reopened paint USD finds two modeled support levels at 0.037 m and 0.067 m. Both paint borders and the westernmost traced bar span the 30 mm road-to-shoulder difference. The other six bars are wholly on the upper road surface. This is a modeled discontinuity. Until the junction surface is reconciled, the paint preview remains unsuitable for production use. The local per-piece triangle-level receipt is `data/diagnostics/smith_north_paint_20261104/height_review.json`.

The follow-up mesh trace locates both unsupported road-only segments of Smith north line 3731. The western 1.749 m falls at aerial pixels (336.74, 208.24)–(346.52, 208.87), and the eastern 0.152 m falls at (413.81, 213.18)–(414.66, 213.24). Both segments are fully supported in XY by `/World/Streets/Shoulders_83288818`. The dated image shows marked pavement around those positions, so the 1.901 m discrepancy is between modeled roadway and shoulder classes at the painted crossing. Treat the existing shoulder geometry as an approximation. Verify the actual curb, paint ends and vertical transitions before adjusting either surface.

Projected all eight draft lines into the saved scene's local frame and intersected them with the union of visible roadway meshes. Six lines lie entirely on modeled road surfaces to the reported precision. The Smith south line has about 1 mm outside the road union. The **Smith north traverse, draft line 3731, has 1.901 m of its 14.034 m outside the modeled road union**. Inspect the aerial and verified curb edges at that junction before adding or clipping paint. The audit found no prim named for a crosswalk. That name search does not classify all markings, and line support alone cannot establish paint coverage or dimensions. [Per-crossing road mesh paths and lengths](evidence/pilot-crossing-road-support.json)

## Smith–Edgewater crossing reconciliation

The January 2025 OCPA image shows crossing paint at four locations around the offset Smith approaches. Shadows partly obscure the west approach, and the two Edgewater traversals must be kept separate. All four MetroPlan points have `EDGEDUP=0`. The May 2026 and task-force line geometries match exactly for these four line IDs.

| Location in the offset junction | MetroPlan point | Draft line | Point-to-line distance | Draft line length |
|---|---:|---:|---:|---:|
| North traverse of Edgewater | 6993 | 3731 | 0.142 m | 14.034 m |
| East Smith approach | 6994 | 630 | 0.564 m | 15.921 m |
| South traverse of Edgewater | 6995 | 3870 | 0.752 m | 15.113 m |
| West Smith approach | 6996 | 631 | 0.317 m | 11.221 m |

The local [aerial review](http://127.0.0.1:8769/aerial-alignment) shows the Princeton and Smith reference sets on one optional overlay. The distances above compare the point and draft line in EPSG:32617. Existing paint in January 2025 does not establish the current route, curb-ramp configuration, width, grade or the alignment of future work. Keep those fields open.

## Princeton–Edgewater crossing reconciliation

The January 2025 OCPA image shows paint on all four legs. Using the actual returned aerial frame and transforming the cached candidate sources to EPSG:32617, the MetroPlan reference points pair with the following draft lines. All four points have `EDGEDUP=0`. The May 2026 and task-force line coordinates are identical for these IDs. Treat them as duplicate line evidence.

| Leg | MetroPlan point | Draft line | Point-to-line distance | Draft line length |
|---|---:|---:|---:|---:|
| North | 6999 | 3869 | 0.064 m | 16.649 m |
| East | 7000 | 3871 | 0.403 m | 13.607 m |
| South | 7001 | 3872 | 0.749 m | 16.956 m |
| West | 7002 | 3873 | 0.149 m | 13.951 m |

This establishes four dated marked-crossing observations for the intersection. The point-to-line distance measures agreement between GIS references, and the line length describes the draft geometry. Paint limits, ramp endpoints, grades, usable widths, and current facility status require separate evidence. The May 2026 `Width` field remains unit-unknown. Keep the four draft lines as references and use the dated paint observations to prioritize end-by-end curb and ramp checks. [MetroPlan points](https://www.arcgis.com/home/item.html?id=7689d18e7f8f49d9b0ffb08e57a14e42) · [City draft lines](https://www.arcgis.com/home/item.html?id=3a0cc13f4606423ba2e4da700a019920) · [OCPA aerial metadata](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json)

The public Orlando Sidewalks service directory contains layer 0 Bike Lanes and layer 1 Sidewalks. Layer 1 is based on FDOT roadway inventory and its rendered class indicates sidewalk on one or both sides. It does not provide independently positioned walk edges or ramp locations. [Service directory](https://services.arcgis.com/04HiymDgLlsbhaV4/ArcGIS/rest/services/Orlando_Sidewalks_AGOL/FeatureServer)

This bounded #16/#25 delivery preserves new public crossing evidence for review; it does not close either ticket or change a scene. Original ticket bodies were fetched on October 29, 2026. The full College Park neighborhood polygon, rather than the smaller extraction rectangle, defines the spatial query and exact feature intersection.

## Actual acquisitions

| Source | Neighborhood / Main Street intersections | Readiness |
|---|---:|---|
| [MetroPlan-hosted xCrosswalks](https://www.arcgis.com/home/item.html?id=7689d18e7f8f49d9b0ffb08e57a14e42) | 67 / 25 | Point references with published field definitions; lifecycle/acquisition/accuracy unknown. Not paint polygons, curb lines or ramp geometry. |
| [Orlando task-force service](https://www.arcgis.com/home/item.html?id=3a0cc13f4606423ba2e4da700a019920), layer 0, **Draft Crosswalk Expansion Recommendations** | 263 / 78 | Explicit draft recommendations; never promoted to existing facilities. Width values retained with units unresolved. |

These overlap conceptually and must not be summed as unique physical crossings. The normalized packet contains 330 source features, not 330 accepted facilities. In particular, **18 MetroPlan neighborhood points have EDGEDUP=1**. Its original description explicitly says these analytical duplicates are placed where a crossing does not exist to support distance calculations. They carry `synthetic_edge_duplicate_not_physical_crossing` status. PAINTED=1 therefore cannot alone establish a physical facility. The metadata also defines FADED as a qualitative assessment and park/school/transit distances from joined roadway centroids, not crossing coordinates.

The City organization catalog query `(sidewalk OR ramp OR crosswalk OR ADA)` returned two public Web Maps, both the previously known draft crossing maps; pagination ended. This is a bounded catalog result, not proof that the City lacks data. The consultant service organizations are not City ownership evidence. Publicly named “Curb Ramps” item d2277f2ca92b4865b83967525d2df209 and “Sidewalks Base” item af1034dd7033443f97f7788114ce6ab7 were rejected by actual Arizona/North Carolina metadata extents. No geometry was downloaded from these wrong-geography candidates.

## Reproduction and source contract

New helper `tools/pedestrian_source_evidence.py` supplements the existing `pedestrian_discovery.py`; its distinct responsibility is full-neighborhood comparison of additional hosted candidates and explicit synthetic-point exclusion. Run with the project Python runtime:

```text
python tools/pedestrian_source_evidence.py --live
python tools/pedestrian_source_evidence.py
```

The first command only acquires missing public cache entries; the second replays receipt-verified original bytes without network. Output folder: `data/processed/pedestrian_source_evidence/`. `packet.json` records original field schemas, safe first-five attributes, item/feature IDs, metadata dates separately from receipt retrieval dates, original terms/attribution/descriptions, native CRS, exact polygon counts and explicit unknowns. `candidate_crossings.geojson` contains review-only WGS84 geometries clipped to the neighborhood. Every query batch must return its exact requested ID set; truncated or invalid geometry fails. Source checksums and helper/boundary dependency hashes accompany the packet. The replay reproduced the same packet SHA. This is an acquisition/review artifact, without activation or API publication; recovery is rerunning from unchanged source receipts, preserving original bytes. It does not implement a generated-file manual-edit protection contract and must not be used as an activation writer.

Source reuse text is preserved where supplied; absent terms remain unknown. Item modification and layer edit timestamps are not inventory observation dates. No source field geometry units imply width units; grade and survey accuracy remain null. No internal .cit endpoint, private data, restricted canopy or imagery pixels were acquired or published.

## Remaining engineering inputs and geometry decision

Actual City ADA sidewalk polylines/polygons and curb-ramp records with lifecycle domains, observation dates and width/grade definitions remain missing. Existing FDOT side-relative roadway inventory supports attributed reference screening, not sidewalk edge geometry. The City's 2021 Appendix L documents datasets; it is not their API.

The acquired March 20, 2023 HDR agreement scope lists Princeton/Smith mast arms, but supplies neither surveyed positions nor constructed curb/ADA geometry. Latest signed/sealed and as-built Princeton–Smith roadway, marking, signal, drainage and ADA sheets, revision history, survey control and native files remain unacquired. The existing unsent `ENGINEERING_RECORDS_REQUEST_DRAFT.md` already names those exact inputs; no outreach occurred.

For the pilot, dated aerial review can flag visible discrepancies but cannot establish slopes, hidden curb cuts, clear widths or legal/ADA compliance. Thus **no new sidewalk/ramp/curb geometry is ready for promotion**. Newly acquired crossing references are ready for side-by-side source review, with synthetic duplicates excluded, proposed layers distinct and the remaining field-verification queue covering widths, grades, lifecycle, curb/tree-well/driveway joins and obstructions. No future Complete Street widening replaces existing conditions.
