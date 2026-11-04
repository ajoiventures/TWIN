# Commercial reference and listing-status verification

## November 4 evidence update

The Wellesley marketing footprint is now restricted to eight base-address OCPA records with use code `1101` in the active snapshot. The older JLL marketing page names one of those PINs (`292214913201003`) and describes the larger first-floor offering, so its one PIN cannot enumerate the current offering. A syndicated CBRE campaign page lists parcel IDs that include residential units, in conflict with its stated first-floor retail scope. Treat those IDs as unverified marketing metadata. The map now excludes residential parcel features from all three Wellesley retail claims. Exact legal sale and suite assignments remain unresolved. [Historical JLL listing](https://www.crexi.com/properties/529402/florida-the-wellesley-retail) · [CBRE syndicated listing](https://www.showcase.com/2305-edgewater-dr-orlando-fl-32804/41801447/)

The live City permit dataset resolves the gap in the cached 1717 parcel extract. A query for exact PIN `292223000000091`, address prefix `1717 EDGEWATER` and the two known permit IDs returned 16 rows, all processed in 2021 or earlier. The City lists demolition permit `DEM2021-10093` as closed, issued October 14, 2021. The companion engineering site-work permit `ENG2021-11849` and fence permit `BLD2021-17611` were both finaled December 15, 2021. The remaining open 2021 record `SBF2021-145-1` is a sewer-benefit fee record with no issued date in the response. This search found no later replacement construction permit. The aerial remains the dated physical observation, and post-January-2025 conditions remain unverified. The safe-field API response is local at `data/diagnostics/edgewater_1717_aerial_20261104/city-permits.json`, SHA256 `a65c1ccee68f22039a6ef47759edd53f6223174dab25f91c28bc3a55ff06c878`. [City permit dataset](https://data.cityoforlando.net/Permitting/Permit-Applications/ryhf-m453)

The **January 2025 OCPA aerial** independently supports the City's demolition record for 1717. The actual 900 × 700 JPEG was inspected locally. Projecting the composed body and roof through the local origin and returned EPSG:4326 frame places both over pixels X 276.33–467.82 and Y 327.14–440.07. That rectangle shows cleared or paved ground and shadows, with no visible building at the modeled outline. JPEG SHA256 `2a2d7b8226669c5d161d42c5a62f11561cea730b6229c5c42716ac614a90cdf3`. A separate inactive `data/diagnostics/edgewater_1717_aerial_20261104/review.usda` hides only the legacy body and roof for a January 2025 comparison. Reopening the USD verified both visibility opinions. The source aerial remains local. The public OCPA folder listed 2025 as the newest annual service checked, so later construction status remains unverified. [OCPA flight metadata](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json)

**1717 Edgewater Drive** is a proposed build-to-suit project on parcel `292223000000091`, exact feature `ocpa:99558`. The broker describes three proposed stories, 8,909 sq ft of office and 989 sq ft of retail. The City identifies the same site as case `MPL2020-10076` and records demolition of the earlier office and the replacement as unbuilt as of September 2024. The City table lists 899 sq ft of retail while its narrative says 989. Treat those as conflicting reported figures. The active OCPA parcel reports unknown year and stories. The active registry links `Building_3088` to this parcel, so this is a potential stale-geometry discrepancy requiring dated post-demolition and recent evidence before geometry changes. The active permit extract returns zero parcel rows, which does not establish current construction status. The map shows the broker values as proposed property context. [Broker listing](https://www.loopnet.com/Listing/1717-Edgewater-Dr-Orlando-FL/23379028/) · [City project list](https://www.orlando.gov/files/sharedassets/public/v/1/departments/edv/city-planning/appendix-k-current-plans-and-projects-list-as-of-september-17-2024.pdf)

Added **1610 Edgewater Drive** to the property context register. The broker listing describes a freestanding, single-story 1950 retail building with 11,937 square feet and 75 reported parking spaces. The active OCPA snapshot has one exact situs match, feature `ocpa:345458` and parcel `292223949602010`, with consistent year, stories, lot area and zoning. The sale offer is a publisher-reported observation. The 75 spaces are a parking inventory lead. Current availability, occupancy, field counts and a physical 3D assignment remain unverified. [Broker listing 40304288](https://www.loopnet.com/Listing/1610-Edgewater-Dr-Orlando-FL/40304288/)

The Wellesley listing text was rechecked and still identifies the sale scope as the 19,827-square-foot ground-floor retail condominium within the seven-story project. The listing update field supplies no date. Residential and suite assignments remain separate and unresolved. [CBRE-attributed listing 41801447](https://www.loopnet.com/Listing/2305-Edgewater-Dr-Orlando-FL/41801447/)

Offline replay now yields eight scoped claims and two accepted property-context links. The separate 1610 physical reference resolves to the unique ID-and-geometry-linked building group. A fresh read of the composed USD verifies the broker-reported area and story count on `/World/Buildings/Building_3090`, with current status unknown and the market-status update flag off. No geometry was resized. The refreshed metadata layer changes the input hash recorded by older terrain previews.

Bounded ticket #32 implementation, October 28, 2026. This register separates broker-reported physical facts, marketing status, component/suite scope, current verification and government entity links. It does not change scene geometry or activate market-status labels.

## Verified source observations

| Source / property | Safe reported facts | Scope and limits |
|---|---|---|
| [CBRE-attributed LoopNet listing 41801447](https://www.loopnet.com/Listing/2305-Edgewater-Dr-Orlando-FL/41801447/) / Wellesley, 2305 Edgewater | Retail condominium component offered for sale; 19,827 SF; listing start August 19, 2026 | Indexed broker listing observed; direct page restricted. This is the ground-floor retail component, not the residential tower or all residential condos. Start date is not a verified status-update date. |
| [Crossman broker index](https://www.crossmanco.com/properties/) / Wellesley | Named property, address and 19,827 SF retail GLA | Indexed direct-broker page observed; exact suite-detail page not verified. No current specific-suite status is inferred. |
| [PropertyShark syndicated Wellesley listing](https://www.propertyshark.com/cre/commercial-property/us/fl/orlando/2305-edgewater-dr/) | Suite I advertised for lease, 945 SF, attributed to Crossman | Syndicated only. Search variant reports September 16, 2026 update, opened variant August 17. Both retained as a freshness conflict. No direct broker suite confirmation or physical suite mapping. |
| [BBD direct property 6282](https://www.bbdre.com/properties/professional-office-space-in-college-park/) / 1615 Edgewater | Office leasing offer; reported building area 25,324 SF, year 2002; page available range 2,789–6,315 SF | Direct broker page verified. Unique government parcel supports property-address context, not automatic physical-suite assignment or whole-building availability. |
| [BBD direct brochure](https://www.bbdre.com/wp-content/uploads/2023/05/1615-Edgewater-Dr-2025-1.pdf) | Suite 190: 2,507 RSF; Suite 200B1: 3,426 RSF; same building area/year | File-created February 27, 2025 is not availability as-of. Suite schedule differs from page range; conflict remains unresolved. Sources share one marketing evidence group. |
| [JLL-authored 1420 Edgewater brochure](https://images1.showcase.com/d2/lvjT5gaqmC3LIrytPi5vTozAOKxT7JRm0JWVewFNNhw/document.pdf) | Two-story office building, 15,556 SF | Physical building facts verified from broker-authored PDF; current sale/lease status and effective date not established. CDN copies are not independent corroboration. |
| [Bywater-authored 2114 Edgewater brochure](https://images1.showcase.com/d2/rykYlhKYHY0C8_R_jEyecvx8s7X7b86GOpgW6lGyR4U/document.pdf) | Retail space offered for lease, approximately 1,100 SF; reported dimensions 15 by 70 ft | Undated source. The reference to a 2024 expense estimate is not an availability date. Historical occupant description is not imported as a verified current tenant. |

Only factual fields are normalized. No individual broker names/contact details, rents, prices, yield/financial metrics, private BOOMS records or copyrighted broker photos/floor plans enter the committed configuration or normalized register. Source URLs and document hashes preserve attribution. A locally retrieved BBD brochure remains in ignored `data/commercial/source_documents/`; its contents/assets are not committed or published.

## Entity and model-update decisions

The current public snapshot is `20261028T160543372334Z`. Address normalization creates candidates; it never proves a suite or component identity by itself.

Generated building IDs below are examples from that snapshot, not permanent assignments. Physical fact links are derived on every run from reviewed source parcel/feature IDs and a unique accepted active building group. A regrouped parcel with multiple building groups returns to review instead of copying the fact to every building.

- **1420 Edgewater:** reviewed physical-entity mapping to parcel `292223181900010`, feature `ocpa:99727`, `Building_2875`, which already has an ID-plus-geometry match. The broker's two stories agree with government stories. Two broker-reported metadata facts (stories and reported area) are accepted for this physical-entity inspector. Area does not resize geometry; current market status stays unknown. Parent/director review is recorded in configuration.
- **1615 Edgewater:** unique parcel `292223016600090`, source feature `ocpa:99613`, supports reviewed property-address context. Reported year 2002 agrees with the parcel. No matching building record appears in the current normalized building links, so no scene building/suite receives an availability label.
- **Wellesley retail and Suite I:** overlapping condo/address candidates remain unresolved. Sale of the retail interest must never mark the residential tower for sale. A 945 SF advertised suite must never mark all 19,827 SF, all condos or the whole building vacant.
- **2114 Edgewater:** no exact normalized base-address parcel candidate in the snapshot. The storefront may share another situs/parcel; do not fabricate a parcel link or label an adjacent building.

The register has **six scoped claim groups from seven source records**: one source-reported sale offer, three source-reported lease offers and two unknown-status references. **All six current verified statuses remain unknown.** These are not unique vacant-building totals, citywide market coverage or available-area totals. Accepted physical metadata and property context can be useful even when listing status is unknown.

## Time, conflict and syndication rules

- Source-check time is fixed to the actual observation batch, not regenerated as a fresh broker check when normalizing offline.
- Keep source-reported effective/status dates separate from listing-start, PDF creation, filename and copyright dates. Unknown status dates remain unknown.
- Review threshold is 30 days. Stale checks/status dates, future dates and conflicting publisher variants remain explicit; recent source reports still are not live broker confirmation.
- Deduplicate only explicit campaign/source groups. Do not merge sale and lease offers merely because the address matches. Conflicting scope/status/facts within a claimed duplicate group fail instead of overwriting evidence.
- BBD page/brochure availability disagreement enters the conflict queue; no advertised areas are summed into inferred vacancy.
- No approved AI/ML use is inferred from accessibility. `approved_for_ml` is false and eligibility unestablished for all sources; copyrighted assets are excluded from model training/evaluation inputs.

## Reproduce and integrate

Run `python tools/commercial_evidence.py --offline`. The tool is deliberately an offline normalizer of reviewed factual observations and public snapshots, not a scraper or live market feed. Refresh the curated observation record only after a new source check; it retains the access method (direct broker, broker-authored brochure, indexed listing or syndication) and date conflicts.

Generated outputs under ignored `data/commercial/`:

- `commercial_evidence.json`: sources, scoped claims, freshness, conflicts/limitations, entity review and quality totals.
- `commercial_listing_status.json`: listing-reported status register; current verified status, physical occupancy and whole-building status remain independently unknown.
- `commercial_entity_review.json`: accepted physical metadata, accepted property context and unresolved candidate queues. Parent integration may expose accepted facts with their source quality; status updates remain disabled.
- `commercial_verification_queue.json`: scope-aware source-date, availability and identity/conflict follow-ups.
- `commercial_preview.json`: field list and first five safe rows/entity reviews.

Full #32 acceptance still requires broker-current status confirmation, scope-specific identity/physical suite mapping, resolved duplicate/conflicting evidence, refresh behavior and reviewed UI/scene integration. No phone call, email or broker request was sent.
