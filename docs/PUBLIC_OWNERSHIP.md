# Government and public-ownership references

L-02 delivery for #3/#4/#22, October 28, 2026 local time. This is a full-neighborhood **reference screen**, not a comprehensive legal ownership register or a deed search. It requests no owner names, contacts, mailing addresses, staff notes or BOOMS records, and changes no active extraction or scene.

## Actual result

The bounded OCPA parcel query returned 7,532 envelope features. Exact positive-area intersection with the official College Park neighborhood retains **5,732 features / 5,730 parcel strings**; all source geometries are valid. The two repeated parcel IDs remain distinct source geometry rows. There are 1,800 envelope exclusions and 3,842 exact source OBJECTID + parcel string + geometry matches to the frozen active extraction. Additional neighborhood records do not silently expand the 3D scene.

| Reference | Observed result | Meaning |
|---|---:|---|
| Exact government/lease assessment-use codes | 92 parcel features | 34 municipal, 36 state, three County, three public-school-district references, one federal, 13 government-level-unspecified and two municipal leaseholds |
| City Owned Vacant Lots inventory | Five exact parcel matches from 61 Citywide records | One has OCPA use `0001`, illustrating why government ownership cannot be screened completely from government-use codes |
| County Owned Buildings inventory | One exact parcel match and one unmatched envelope point | Matched County inventory context disagrees with the parcel's municipal tax-use class; the agency conflict stays open |
| Combined government-related references | **93** parcel features; nine intersect Main Street | Assessment and official-inventory observations; not 93 title-verified public parcels |
| Without either reference | 5,639 parcel features | Ownership unknown; never classified private by absence |
| Legal title, current vacancy or public access verified | **Zero** | Unknown for every parcel in this delivery |

The official neighborhood covers about 8.375 km². Approximately 1.636 km² is not covered by any returned parcel polygon; roads, water and other cadastral gaps may contribute. No ownership class or missing-parcel count is invented for that area. The query is complete for this service, envelope and date; that is not comprehensive government-land or legal-title coverage.

## Exact definitions, not name or zoning guesses

OCPA's public website Code Tables supplies `api/RP/GetUseCodes` and `api/RP/GetExemptionCodes` through the website's published API host. The adapter uses **explicit reviewed four-character code rules**, pinned against the exact returned OCPA descriptions. A changed definition fails for review. It does not derive classification by matching owner-name keywords, infer ownership from zoning `P`, or copy another county's local suffix definitions. Original code strings, source OBJECTIDs and parcel strings retain their leading zeroes.

The current lookup contains 398 use-code definitions. County, State and municipal parks, utilities and land subcodes remain distinguished; a generic governmental park code does not identify a municipality. Municipal leaseholds remain separate from direct municipal-use references. The municipality's identity stays unknown unless a separate exact City inventory record supplies that reported agency context. All legal owner fields remain unknown.

The [Florida Department of Revenue's final 2026 standards](https://www.floridarevenue.com/property/Documents/2026FINALCompSubmStd.pdf), published **March 27, 2026**, provide the general government categories in Addendum E, PDF page 65. OCPA's own local four-digit definitions govern this implementation; no automatic translation from three-digit state codes is performed. The original PDF and checksum receipt stay in ignored cache. Acquisition accepts only the independently reviewed PDF SHA-256 `558abe7336d8c05638b4fa09046acfb2617deda31f5d0844f6f212f13c4271a3`; unknown response bytes receive no publication-date assertion or file write. Partial or changed existing document/receipt pairs are preserved for review. The OCPA dictionary's original publication/effective date and the map layer's tax-roll year are not supplied and remain unknown; retrieval and build dates do not replace them.

The public numeric exemption dictionary is **not** applied to the parcel GIS field `EXEMPT_CODE`: its namespace is not established as that dictionary. The exploratory safe query included that coded field, but its values are neither published nor used to assign government ownership. Blank exemption fields do not become private ownership. No private owner fields were requested.

## Official register corroboration

The [City Owned Vacant Lots dataset](https://data.cityoforlando.net/w/bkpt-5h2w), attributed to the Real Estate Management Division, is queried only for original row ID, property ID and parcel string. Its source rows were updated February 4, 2026. Five exact matches are obtained after the documented City section–township–range to OCPA range–township–section formatting conversion. All matching geometry features are retained; no spatial-only ownership link is accepted. The earlier partial extraction missed these matches. The inventory is not a complete City property register, and its title does not verify present physical vacancy, availability or legal title.

Orange County Government GIS's public **Orange County Owned Buildings** item `a4bdbefbfd914033a1f8e839165d57f6` is a point/address inventory. Publisher organization, public access and exact service association are checked. Only original point/enterprise/parcel identifiers, source use code and modification date are queried. One source point's parcel ID matches a neighborhood parcel; one does not. The matched parcel's OCPA municipal-use reference conflicts with the County inventory context. Both observations remain visible, with no selected owner or relocated point. A building inventory is not a complete County land register.

## Reproduction and integration

Run `python tools/public_ownership.py --offline` against the acquired original caches. Normal mode fetches missing bounded requests and the original final FDOR source document; it does not publish a new active snapshot. The script returns to the same frozen study polygon and retains source request/metadata checksums. The original OCPA query requests only OBJECTID, PARCEL, DOR_CODE and the unusable GIS coded exemption field. The publication includes only needed identity/use/classification fields and exact corroboration evidence.

Ignored outputs under `data/processed/public_ownership/`:

- `register.json`: all 5,732 source-feature reference rows, 93 combined references, exact rule/dictionary, source dates/requests, first five safe rows, coverage and unresolved conflicts.
- `government_references.geojson`: the 93 government-related source geometries clipped to the official neighborhood, including the City-inventory-only candidate; no parcel is promoted to a building or storefront.
- `coverage.svg`: pixel-free neighborhood reference map; other areas remain ownership unknown.
- `receipt.json` and timestamped backups: output checksums and recoverable previous bundles. Original acquisition caches and the FDOR PDF are ignored separately.

`validate(root)` returns the report after checking the current comparison snapshot, every required artifact receipt and source/cache/tool dependencies, without agency calls. Modified or unreceipted outputs refuse rebuilding. Root/API integration can paginate `rows`, filter `government_reference_present` or conflict status, expose the dictionaries/source register and serve the validated SVG/GeoJSON. No default-on 3D layer is proposed. Current title/agency conflicts, unresolved exemption mapping, unrepresented cadastral space and the broader vacancy/planning/park-detail gates remain open. Independent review is required before accepting this bounded reference screen.

## App integration and review

Independent source/geometry review passed for this bounded government-reference screen; [review record](evidence/public-ownership-review.json) preserves exact packet hashes and remaining limits. The API exposes `/api/v1/public_property_references` (5,732 rows), `/api/v1/government_property_references` (93 rows), `/api/v1/public_property_quality` and validated `/public-property/coverage`. Standard `parcel_id`, `limit` and `offset` parameters preserve distinct source features. Every request validates the current snapshot, artifacts and dependency hashes before returning data.

Actual API and browser inspection on local review service port8773 verified five returned rows, original source identifiers, explicit unknown legal title, source dates, conflict records and the rendered coverage image. `web/source-browser.html` includes both full-neighborhood choices, field names/dictionaries and provenance; stale requests keep coverage hidden. [Actual fields view](evidence/government-property-browser.png) is committed; the coverage screenshot is saved locally as `data/processed/public_ownership/browser-coverage.png`. The main property inspector has not yet added per-feature government references. No active source snapshot or 3D geometry was changed.
