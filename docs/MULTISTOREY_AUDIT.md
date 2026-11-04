# Multi-storey and condominium representation audit

Read-only checkpoint on October 28, 2026, before the Wellesley correction. Source snapshot: `20261028T145054204280Z`. This audit writes review evidence only; it does not change floors, parcel matches, USD geometry, API responses or the active snapshot.

## Reproduce and outputs

```
python tools/storey_audit.py --live
python tools/storey_audit.py
python -m unittest discover -s tests -p test_storey_audit.py -v
```

The first command permits bounded public OCPA queries, cached with exact safe field lists, response hashes and retrieval times. Subsequent offline audits use that cache. Only property/building identifiers, site addresses, property names, floor/story fields, condo flags and year-built fields are requested; no owner/contact/mailing data or BOOMS records are read.

- `data/heights/storey_audit.json`: source comparisons, official scope counts, safe property evidence, Wellesley cloud statistics and disk-scene checks.
- `data/heights/storey_exception_queue.json`: prioritized review-only exceptions, each explicitly disallowing automatic height changes.

## Actual scope counts

The headline 728 multi-storey groups applies to the entire rectangular extraction. It is not a count of buildings along Edgewater or inside the official Main Street boundary.

| Scope | Building groups | Modeled 2+ floors | Raw footprint maximum FLOOR_NUM 2+ |
|---|---:|---:|---:|
| Entire extraction | 3,090 | 728 (722 two-floor, 6 three-floor) | 226 (222 floor 2, 4 floor 3) |
| Representative point inside official Main Street | 190 | 23 | 7 |
| Any footprint intersection with Main Street | 201 | 26 | 8 |
| Representative point inside official neighborhood | 3,065 | 726 | 224 |

Different spatial tests intentionally have separate denominators. The extraction rectangle covers approximately **96.16%** of the official Main Street polygon's projected area; it does not cover the whole official neighborhood or guarantee complete district data.

Among **54 current-snapshot parcel features** intersecting Main Street with STYS 2+:

- 34 are represented by at least one accepted building group with that many modeled floors.
- 17 lack an accepted ID-plus-geometry building link.
- 2 have multiple groups but none with matching storey evidence.
- 1 has an extreme parcel/building count conflict retained for review.

These are parcel-feature review counts, not 20 independently proven missing buildings. Condo stacking, multiple buildings, boundary touches and duplicate/ambiguous representations require entity-level review.

A separate official-boundary query returned 201 safe property rows with STYS 2+ or a non-ground condo FLOOR_NO. One two-storey property was outside the current parcel snapshot: **3480 Fairway Lane**, PIN `292211305603060`, OCPA STYS 2, year built 2024. Its absence is a scope/acquisition gap, not permission to invent its footprint.

## Wellesley: concrete whole-building failure

The [official OCPA parcel service](https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4) identifies **WELLESLEY CONDO / WELLESLEY CONDOMINIUM** at **2305 Edgewater Drive**. The bounded site-address query returns **114** parcel rows:

- STYS is zero/unknown on 113 rows and 1 on one row.
- Unit `FLOOR_NO` positions: 2 → 15 rows; 3 → 15; 4 → 14; 5 → 15; 6 → 23; 7 → 23; 0 → 9.
- Example PIN `292214913217010`, 2305 Edgewater Drive Unit 1701, explicitly reports FLOOR_NO 7 with STYS 0.

Unit STYS describes the unit record's context, not the whole condominium's storeys. Unit floor positions reach 7 and demonstrate a major conflict with a one-floor whole-building model; the audit does not turn maximum unit FLOOR_NO into an automatic whole-building height.

The existing group is **`Building_2933`**, source footprint PID `292214147406110`, building number 1. Nine raw commercial subareas report FLOOR_NUM 1. Their old parcel ID does not resolve to the overlapping current condo/master parcels, so the link is correctly ambiguous/unmatched rather than accepted.

The pre-correction height record applies **4.3 m / one modeled floor**, reduced from the previous generic 6.5 m. The connected disk-stage mass agrees with that incorrect record. This is actual underrepresentation, not merely a stale viewer or missing upper-floor window texture.

The existing height pipeline also records a rejected class-6 roof candidate: 47.91 m roof minus 31.95 m local ground = **15.96 m**. That candidate was rejected against the one-floor prior. It is not necessarily the tallest Wellesley roof because the old group is multipart and extends beyond the condo property union.

### Why class-6-only sampling misses the tall surfaces

Clipping the existing historical point cloud to the union of all 114 current parcel geometries yields **178,401 points**. This union is a property mask, not a certified roof footprint.

| Class | Points | Selected elevation evidence |
|---|---:|---|
| 1, unclassified | 167,652 | Median Z ≈55.02 m; p75 ≈55.12 m; p95 ≈57.41 m; maximum ≈60.36 m |
| 2, ground | 2,573 | Median Z ≈31.69 m; p95 ≈31.96 m |
| 6, building | 8,131 | Median Z ≈37.38 m; p95 ≈39.23 m; maximum ≈45.16 m |
| 7, noise | 45 | Excluded from roof interpretation |

The dense high surfaces are overwhelmingly **unclassified**, so requiring class 6 excludes important tall-building evidence. Class 1 is not automatically roof: roof/vegetation separation, connected planar surfaces, stepped sections and current imagery must still be reviewed. The old parcel/footprint grouping also misses part of the actual complex. Neither the one-floor prior nor a single class-6 p95 should control the corrected whole-building representation.

The parallel primary-reference review found the [MetroPlan Orlando sustainable land-use report](https://metroplanorlando.gov/wp-content/uploads/2040-LRTP-TR1-Sustainable-Land-Use-Forecast.pdf), Table B-1 and Figure B-5 (printed B-7 / physical PDF page 62), reporting seven storeys and 75 feet for the Wellesley. That is a dated documentary reference, not a current survey. It provides a separate basis for the parent correction, which must preserve a distinct podium/courtyard/upper-volume geometry rather than raising every surrounding footprint to seven floors.

## Princeton: another high-priority missing redevelopment entity

Official OCPA evidence identifies **PRINCETON AT COLLEGE PARK**, **646 W Smith Street**, PIN `292214725701000`, STYS **6**, year built **2019**, condo flag 0.

The existing model instead contains **14 spatial-review groups** from old `292214147407...` parcel IDs, all one-floor masses around 4.2–4.3 m. No accepted current parcel-to-building entity link exists. Raising all 14 former house/accessory groups to six floors would produce a false model. Current whole-building geometry and redevelopment lineage must be resolved first.

## Other review outcomes and visual/runtime distinctions

The pre-correction queue contains **116 review items**, not 116 proven missing buildings. It includes:

- The named Wellesley conflict first, followed by the six-storey Princeton parcel case.
- Main Street parcel/link/story exceptions.
- 24 applied-height versus much taller rejected-LiDAR candidate conflicts across the extraction.
- 72 one-floor groups whose subarea descriptions mention an upper story; these are outside the Main Street-intersection scope and require semantic/source-date review. A description does not automatically certify a current second floor.
- The one official Main Street property outside the current parcel snapshot.

For the current pre-correction disk composition, the modeled mesh spans agree with the height records; no missing-layer-height mismatch or stale height-snapshot discrepancy was found. A running Omniverse process can still hold an older stage; this audit does not inspect or certify its reload state.

The generic facade generator also creates ground-level shop glazing/awnings and lacks evidence-based upper-storey window layouts. That can make correctly tall masses look visually flat. It is a separate issue from the genuine Wellesley/Princeton geometry and attribution failures.

## Corrective order

1. Fix Wellesley whole-entity attribution, dated reported storeys/height, actual footprint and stepped volumes; retain documentary/LiDAR quality labels.
2. Resolve Princeton redevelopment footprint lineage before applying its six-storey parcel attribute.
3. Review remaining Main Street exceptions using source dates, IDs, geometry and building versus accessory semantics.
4. Extend roof evidence beyond class 6 only where supported by planar/connected geometry, current reference review and explicit uncertainty.
5. Add upper-floor facade detail after the corrected building masses and references are accepted; verify the actual running scene reload separately.

Twelve tests cover accessory protection, unaccepted spatial links, parcel outliers, unit floor semantics, address digits not becoming floor counts, rejected tall candidates, height-per-floor conflicts, source floors lost from output, safe fields and no-network offline behavior. No source links or building heights are promoted by this audit.

## Expanded-scope refresh

The October 28 refresh against snapshot `20261028T160543372334Z` uses the snapshot parcel source extent rather than the old hardcoded rectangle. All 3,216 groups were checked: 211 intersect Main Street, 27 of those model two or more floors, including Wellesley at seven. The review queue has 113 entries; no Main Street source rows remain outside the snapshot. Missing redevelopment geometry and other unresolved source conflicts remain open.
