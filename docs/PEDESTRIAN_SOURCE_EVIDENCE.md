# Pedestrian source acquisition follow-up

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
