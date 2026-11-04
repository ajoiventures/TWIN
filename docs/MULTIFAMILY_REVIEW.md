# Multifamily accuracy review

October 28, 2026. Snapshot `20261028T160543372334Z`. Focus: Princeton / Edgewater and the official College Park Main Street district, with surrounding extraction context.

## Inventory

Bounded OCPA queries checked 557 parcel records: 8 apartment-family candidates, 164 small-multifamily candidates, 351 condominium records and 34 mixed-use review records. 206 intersect Main Street; 196 lie within 350 m of the pilot center. These are **tax records, not physical buildings, complexes or dwelling-unit counts**. Mixed-use codes do not establish residential occupancy.

State DOR families select candidates; county subtypes remain raw. [Florida DOR definitions](https://floridarevenue.com/property/Documents/2023FINALCompSubmStd.pdf) distinguish apartments, smaller multifamily and condominiums. No owner/contact fields, rents or occupancy inference are imported.

The 365 records without an accepted model link comprise 351 condominium unit/component records, 3 apartment candidates, 8 small-multifamily candidates and 3 mixed-use candidates. This does not mean 365 missing buildings. Wellesley's physical correction remains separate from its unaccepted unit-to-building tax links.

## Highest-priority local findings

| Property | Official story evidence | Model finding / next correction |
|---|---|---|
| Princeton at College Park, 646 W Smith | 6; built 2019 | 14 old source groups, only spatial-review assignments; reconstruct redevelopment components rather than raising old houses |
| Wellesley, 2305 Edgewater | Unit floors through 7; separate historic seven-story documentary evidence | Corrected upper mass at 23.35 m historical height; retain courtyard and unresolved podium components |
| 624 W Princeton | 2; built 1985 | No accepted current building link. Source PID matches Building_1966, but its geometry is mostly assigned to 644 W Princeton as spatial review; resolve location/lineage before moving or raising it |
| 520 W Princeton | 2; built 1978 | No accepted current building link. One intersecting raw upper-story subarea belongs to 521 W Harvard's source group; do not transfer it automatically |
| Vassar St Apartments, 805 Vassar | 2 | One accepted identity link; current facade/roof/height still requires dated visual validation |
| City Haven Apartments, 713 Rugby | 2 | One accepted identity link; no missing-building inference from link review alone |

[Princeton's operator](https://www.theprincetonatcollegepark.com/) and [BET Investments](https://www.betinvestments.com/properties/florida/the-princeton-at-college-park-orlando-fl/) independently identify the apartment community at 646 W Smith. Marketing text confirms identity, not measured roof height or current geometric accuracy.

## Reproduce and inspect

`python tools/review_multifamily.py` checks the allowlisted property fields using bounded source-object queries; `--offline` replays cached responses and their original receipts. The ignored local report preserves source requests, raw codes, parcel stories, unit floor positions, source-PID candidates and model-link exceptions. No snapshot or geometry is overwritten.

Read-only API: `/api/v1/multifamily_review?limit=5`, `/api/v1/multifamily_quality`; filter rows with `parcel_id`. Stale snapshot reports and reports built against a different height-file hash are rejected. Zero/null unit-story values follow the snapshot normalization, avoiding false source-change alerts. All 141 repository tests pass. The map's Housing evidence inspector distinguishes an appraiser attribute from a measured height and calls out missing accepted geometry links.

## Remaining acceptance

Resolve Princeton's whole-building roof and garage/courtyard components from dated government geometry/elevation evidence; verify the two nearby Princeton-address mismatches; then review the remaining apartment candidates and condo complexes without counting unit parcels as buildings. Preserve uncertainty, source dates and stable identities. This inventory is progress toward accuracy, not full multifamily acceptance.

Independent review caught and resolved stale parcel-selection responses, hidden story-conflict warnings and same-snapshot height-refresh staleness. The browser now displays the actual 240 W Orlando two-story/model-count conflict rather than silently presenting accepted identity links as geometric accuracy.
