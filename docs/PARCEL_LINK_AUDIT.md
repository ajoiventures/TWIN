# OCPA parcel and building link audit

## Current full-extraction checkpoint — October 28, 2026

The latest generated audit targets snapshot `20261028T160543372334Z`: 3,916 parcel features / 3,915 PINs, 3,216 building groups, 2,976 exact links, 202 spatial-review links, 3 ambiguous and 35 unmatched groups. It independently recomputed 3,178 assigned overlaps with zero integrity/schema/source-identity errors. There are 103 accepted one-to-many parcels (224 building groups) and 561 floor disagreements (555 one-floor, six larger). No link decisions changed. The 240 unaccepted links and expanded full-project property/sketch/frontage verification remain open. The cache-only candidate adapter additionally quarantines ten source-returned polygons outside the actual study extent; this does not alter the active snapshot. See [adapter contract and current construction evidence](SOURCE_ADAPTER_CONTRACT.md).

## Historical narrower-extraction evidence

Audit run October 28, 2026 against active local snapshot `20261028T145054204280Z`. The audit reads existing public snapshots, the base scene, public footprint subareas and current height evidence. It makes no network requests and does not rewrite links or promote spatial matches.

## Results

| Check | Observed result |
|---|---:|
| Parcel geometry features | 3,783 |
| Unique parcel ID strings | 3,782 |
| Repeated parcel ID groups | 1 |
| Building groups | 3,090 |
| Stored ID-plus-geometry matches | 2,857 (92.46%) |
| Spatial-only review matches | 196 |
| Ambiguous/unmatched bucket | 37: 3 have candidates, 34 have none |
| Total unaccepted/review building links | 233 |
| Distinct parcels with stored accepted building links | 2,744 |
| Accepted one-to-many parcels | 97, containing 210 building groups |
| Independently recomputed assigned footprint overlaps | 3,053 |
| Exact-link, source-object or schema integrity errors found | 0 |
| Current-snapshot height records | 3,090; zero stale/missing |
| Building-floor versus parcel-story disagreements | 555: 550 differ by one floor, 5 by more than one |

These are reference-data consistency checks, not survey accuracy or evidence that every stored accepted match is correct in the real world. The independent overlap calculation reconstructs each group from base-scene footprint triangles, projects parcel polygons into local UTM 17N coordinates and checks the assigned feature. It validates stored overlap rounding and the 0.8 exact-match threshold without discovering or promoting alternative links.

## Duplicate parcels and one-to-many relationships

Parcel `292211305620072` appears in two distinct OCPA source features (`110413`, `406083`), with differing polygon areas. Both are retained. Repeated parcel IDs must not be collapsed by silently selecting the first feature. A feature ID identifies a geometry row; a parcel ID identifies a tax parcel record. Likewise, the 97 one-to-many parcels must preserve all linked building groups; parcel stories cannot be copied indiscriminately to accessory structures.

## Floor disagreements

The 555 discrepancies compare the building-footprint maximum positive integer `FLOOR_NUM` with the current assigned accepted parcel's story attribute. The audit independently checks building floors against current raw footprint subareas and copied height-record parcel stories against the assigned parcel. Nonfinite/out-of-range overlap ratios are rejected. Different source definitions, building grouping, renovations, accessory structures or stale records can explain disagreement. A discrepancy is a review queue, not proof either value is wrong. No floor count or height changes automatically. All floor-based heights remain estimates.

Review the five larger conflicts first, then the selected pilot's one-floor differences using dated aerials/property records. Preserve the current two-floor versus eleven-story outlier handling rather than constructing an unsupported tower.

## Identifiers and map references

The safe identifier registry records:

- Source parcel ID, source `BLDG_NUM`, component footprint object IDs, assigned parcel feature ID and generated USD path.
- A source building key `ocpa-building:<parcel ID>:<BLDG_NUM>` for cross-snapshot reconciliation. This retains leading zeroes. It identifies a source record grouping, not a permanent surveyed physical-building identity; splits/merges or parcel renumbering require lineage review.
- Source query links to the public footprint service using explicit IDs and allowlisted fields.
- The official [OCPA map search page](https://webmap.ocpafl.org/search) with its parcel search token. No unverified parcel-specific map deep link is manufactured.

Generated `Building_####` names are snapshot-local and can shift when grouping/order changes. OCPA object IDs can also change on republication. A stable application identity registry with source lineage should be added before promising permanent deep links across refreshes.

## Schema, freshness and access caveats

Required parcel/building fields are checked row by row and included in the quality output. All exported values are allowlisted; owner/contact/free-text records are absent. Nulls and string identifiers are preserved.

The parcel source manifest reports `source_updated: null`, `retrieved_utc: null` and `retrieval_quality: some_or_all_cached_request_times_unknown`. Its snapshot-build timestamp is known; the original fetch dates of legacy cached requests are not. Rebuilding cached data does not establish current source freshness. The audit records SHA-256 hashes of every input so the result can be reproduced for that exact dataset version.

The extraction rectangle is not an official College Park/Main Street boundary. Geometry is appraisal/reference data and not a boundary survey. No parcel is a verified storefront tenant, and no story attribute is a measured roof height.

## Run and outputs

Run `python tools/parcel_audit.py --offline` after the normal local snapshot/height build. The audit is always offline, with or without the explicit flag. Generated files are ignored by Git under `data/processed/`:

- `parcel_audit_quality.json`: denominators, match counts, one-to-many/floor statistics, schema, input hashes and freshness caveats.
- `parcel_audit_exceptions.json`: duplicate IDs, unaccepted links, integrity errors, one-to-many groups, floor conflicts, stale evidence and source exceptions.
- `parcel_audit_identifiers.json`: source grouping keys, USD paths, component IDs, map tokens and independent overlap evidence.
- `parcel_audit_preview.json`: exact safe field lists, first five parcel/building rows and first five entries from each exception queue.

## Remaining #3 acceptance work

1. Review or explicitly defer the 233 non-exact links with evidence; no spatial match should be silently upgraded.
2. Explain the duplicate parcel geometry relationship and validate one-to-many pilot parcels before relying on derived per-building attributes.
3. Review high-severity floor conflicts and pilot disagreements; preserve separate source definitions and historical dates.
4. Add permanent application-entity lineage across source refreshes, including split/merge/renumbered parcels and building groups.
5. Establish original fetch times for newly refreshed responses and keep legacy-cache freshness unknown until a real refresh occurs.
6. Complete adapter/API contract, outage/schema/geometry-update tests and clean-checkout portability/recovery evidence. Existing local implementation and this audit are partial progress, not closure of the full ticket.
