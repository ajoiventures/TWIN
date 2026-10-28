# Wellesley roof correction — revision 2 applied

Revision 2 was applied October 28, 2026 after independent evidence review and inspection of the actual Kit proposal render `data/renders/20261028T173244Z/MainStreetOverview.png`. The active correction fills the three false roof voids and preserves the observed courtyard. Main roof height remains 23.35 m and documentary storeys remain seven; the maximum rendered roof/equipment surface is 28.393 m and is explicitly not an occupied-storey height. Semantic registry, housing review, extent guard and reconstruction register were refreshed. Validation passed across 20 layers and 17,611 meshes. This is acceptance of the scoped historical roof correction, not current survey or conference visual acceptance.

The scoped correction reconstructs the missing tall Wellesley mass at 2305 Edgewater Drive. It never extrudes the 114-record tax envelope or promotes the original ambiguous parcel match. Current stable target is Building_2939 (original alias Building_2933), resolved by PID `292214147406110`, BLDG_NUM 1 and nine exact source OBJECTIDs. Snapshot: `20261028T160543372334Z`.

## Applied baseline and diagnosed defect

The earlier applied layer used a 23.35 m roof height, derived from 55.04 m NAVD88 main roof minus 31.69 m local ground. This agrees within 0.49 m with the independent historical MetroPlan seven-storey/75 ft (22.86 m nominal) report. Its conservative 3,106.41 m² upper mask incorrectly left several equipment areas as full-depth voids. Revision 2 was first generated and rendered as a separate proposal before explicit application.

The actual `20261028T171454Z/MainStreetOverview.png` render showed jagged walls and false full-depth holes. The local 2025 OCPA aerial was visually reviewed only; it shows a continuous broad roof, rooftop equipment and an elevated central courtyard. No aerial tracing, textures or imagery redistribution are used.

All three enclosed holes in the old roof have dense historical point observations:

| Old hole area m² | Points | Z p10 / median / p90 NAVD88 m |
| ---: | ---: | --- |
| 87.1875 | 2,711 | 55.07 / 55.71 / 59.48 |
| 81.5625 | 2,481 | 55.02 / 56.09 / 58.52 |
| 29.8125 | 603 | 55.04 / 55.23 / 57.968 |

The prior all-return median/spread gate rejected mixed roof/equipment returns. These observations support roof or raised equipment, not ground-reaching voids. Opening and a dominant-plane-only filter also fragmented edges and equipment notches.

The actual courtyard is different: its frozen 300 m² core has 7,235 points, Z p05/median/p95 48.50/49.30/51.313 m, substantially below the 55.04 m upper roof. It is an elevated lower courtyard/deck, not an upper roof or an observed ground opening. The upper mass must exclude this core. Lower courtyard architecture is not reconstructed in this revision.

## Evidence-based revision 2

`tools/correct_wellesley.py` verifies the existing cloud checksum, accepted meter Z check, exact source subareas, base mesh checksum and unchanged unmatched source identity. Historical points are clipped to the union only as a search boundary, then projected to EPSG:32617 XY. Source NAVD88 Z remains meters. No network access is needed.

The dominant roof is still derived from dense class 1 observations. For geometry, each 0.75 m cell now counts returns within 0.4 m of the main plane separately from higher equipment returns, requiring at least three deck returns. A one-cell closing connects supported fragments; large connected components remain required. Enclosed gaps are filled only where they are at most 150 m², have at least 20 observations, and at least 80% of observed points are at or above the deck. Empty or lower-surface gaps remain unresolved. The manifest documents every gap and its decision.

Dense raised patches require at least five elevated returns per cell, p85–p15 spread at most 0.4 m, connected area at least 2.25 m² and half-meter elevation grouping. They are clipped to the supported main roof and authored from the main deck upward, never from the ground. Their semantic use remains uncertain roof/equipment; class 1 is unclassified and is not a certified roof label.

The outer roof is simplified within 1.0 m of the source-supported raster geometry, with a containment check. It reduces boundary vertices from 817 to 123; no perfect orthogonal outline is invented. The shape remains historically derived and is not claimed as surveyed edge accuracy. The explicit courtyard upper-void guard is EPSG:32617 bounds `[461960,3160660,461990,3160670]`; both source geometry and exported roof faces must exclude it.

Current proposal output:

- Main roof area: **4,337.98 m²** within a **6,146.46 m²** property envelope.
- Main roof height: **23.35 m**, with **62** supported raised patches; maximum patch height **28.393 m** above local ground.
- All three old enclosed equipment holes are covered by supported deck geometry, with no courtyard-core overlap.
- Original unresolved lower mass is retained only outside the reconstructed roof, **575.34 m²** at its original **4.3 m** height.
- No other building, parcel link, source base, active root or global height row is changed by proposal generation.

## Proposal, application and verification

Default command `python tools/correct_wellesley.py` writes only the new `scene/wellesley_roof_proposal.usda` and review artifacts under `data/heights/wellesley_roof_proposal/`. The active `scene/landmark_corrections.usda`, global heights and quality report remain unchanged. The manifest records `global_height_writes_applied=false`, geometry revision 2 and action `await_parent_review_before_apply`.

After parent coordination, `python tools/correct_wellesley.py --apply` writes the active scoped layer and updates exactly the Wellesley height row plus aggregate quality report. Main-roof height stays separate from the taller equipment patches. Parent must refresh semantic provenance, composition, running viewport and rendered review. The tool never edits root assembly or global generators.

`python -m unittest discover -s tests -p test_wellesley.py -v`: **12 tests pass**. Coverage includes actual cached point evidence for all three holes, an actual roof-face courtyard regression, mixed equipment surfaces, preservation of empty unobserved holes, unchanged source identity safeguards, topology/UV/normals and one-row-only height changes. The actual-data test explicitly skips if ignored source artifacts are unavailable; synthetic guards remain mandatory.

## Limits and provenance

[MetroPlan reference](WELLESLEY_REFERENCE.md) supplies the historical seven-storey/75 ft cross-check; it is not a current survey. The existing 2018–2019 cloud remains the geometry source. Roof equipment, sloped caps, parapets, facade details and low podium geometry remain approximate. Aerial access is local qualitative review only. Ground remains the current scene datum; terrain rebasing is a separate coordinated task. Original ambiguous parcel matching evidence remains intact.
