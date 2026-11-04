# Parks, vacant land, City ownership and zoning

Reviewed October 28, 2026 against snapshot `20261028T160543372334Z` and the official City portal. Full Main Street coverage is available; the current extraction covers approximately 60.77% of the official College Park neighborhood. Results from this extraction are not a complete neighborhood inventory.

## Located sources and findings

**October 29 supplement:** [Full-neighborhood park inventory](FULL_NEIGHBORHOOD_PARKS.md) supersedes the eight-record coverage limitation below for the City park service: 11 intersecting footprints, including Mathews, Overbrook and Don Dudley. Independent source/clipping review and actual API/browser display are verified. The 3D extraction remains unchanged. L-01 still requires facility details, access, hours and dated site reconciliation. [City adapter delivery](CITY_ADAPTER_CONTRACT.md) adds 4,621 address points and 46 future-land-use polygons in the existing extract; L-04 ordinance/parcel reconciliation remains open.

- City GIS `OrlandoParks` yields eight park/recreation records intersecting the neighborhood within the extract: Lake Ivanhoe Park; Albert Park; Dartmouth Park; Guernsey Park; Ivanhoe Plaza Park; Princeton Park and College Park Pool; Lake Adair Park; College Park Neighborhood Center. The last is a recreation site, not another park. Albert intersects the Main Street program boundary. Intersection does not mean every record is wholly inside either scope.
- [Albert Park](https://www.orlando.gov/Parks-the-Environment/Directory/Albert-Park) is at 2400 Edgewater Drive; the City describes its pavilion/stage, gathering space and parking. [Dartmouth Park](https://www.orlando.gov/Parks-the-Environment/Directory/Dartmouth-Park) is at 822 Dartmouth Street and has paths, playgrounds and exercise facilities. Directory details must be reconciled with dated maps before detailed modeling; GIS address spelling is retained in raw evidence.
- The [City-owned vacant-lot inventory](https://data.cityoforlando.net/w/bkpt-5h2w) contains 61 records citywide; metadata reports rows updated February 4, 2026. Original JSON/metadata and checksum receipts were saved locally under `data/land/`. No inventory records matched either project boundary by local parcel polygon or publisher geocoded point. Records without a usable location remain separately counted in the derived report. This does not establish that there is no vacant or City-owned land in College Park, nor that this inventory is complete/current at parcel level. Some notes describe houses or constraints, so the dataset title alone does not prove physical vacancy.
- The [Real Estate Management Division](https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/Real-Estate-Management-Division) distinguishes property management, leasing and redevelopment. Being City-owned or vacant does not establish surplus status, public access or availability for sale/development.

`tools/review_land.py` creates `data/land/land_review.json` from cached evidence. City printed parcel numbers use section–township–range; the tool reorders these to OCPA range–township–section and preserves leading zeroes. Exact parcel-polygon matching and publisher-point matching are labeled separately. Zoning areas are clipped to the official scope AND extraction and measured in EPSG:32617. Areas are unioned within exact codes; unresolved overlaps between different codes are not an accepted land-use allocation.

## Zoning breakdown to retain

The snapshot contains 29 exact zoning codes/overlay combinations intersecting Main Street and 47 in the extracted neighborhood. These are district combinations, not counts of properties or permitted development sites. Main Street includes MU-1, AC-1, P, PD, residential R-1/R-2/R-3 families and O-1. Residential families dominate the extracted neighborhood, with conservation/water and public-use areas also significant. The derived report retains exact codes and clipped square-meter areas; no definitive residential/commercial percentage is claimed before coverage/overlap reconciliation.

Use the City's [zoning legend](https://gis.orlando.gov/PDF_Docs/PlanningMaps/ZoningMapSeries/ZON_07.pdf) for terminology, with the current code and official zoning record for parcel decisions. The printed map is dated reference material, not evidence that a parcel's zoning is unchanged today:

| Code/family | Meaning for review |
|---|---|
| R-1 variants | One-family residential district family; retain precise suffixes |
| R-2A / R-2B | One-to-two / one-to-five family district labels; actual housing permissions require current tables |
| R-3 variants | Residential intensity district family; do not equate to a verified apartment building |
| O-1 | Office–residential; not exclusively commercial |
| MU-1 | Mixed-use corridor; retain residential and nonresidential possibilities |
| AC-1 | Community activity center; not simply a commercial-only parcel |
| P | Public use; does not by itself prove City ownership |
| PD | Planned development; obtain the governing plan/ordinance and amendments |
| C | Conservation/water; **not commercial** |
| /T | Traditional City overlay; **not townhouse designation** |

The [City residential standards guide](https://www.orlando.gov/Our-Government/Departments-Offices/Economic-Development/City-Planning/Residential-Development-Standards-Guide) links housing types to district tables. Townhouse form, existing residential use, zoning entitlement and design-overlay requirements must be separate fields. Do not generate townhouse geometry or development yield from `/T`.

## Work packages added to existing tickets

- [ ] **L-01 / #4/#5:** expand park/recreation coverage to the full official neighborhood; reconcile park identities, facility types, amenity maps, access, hours and source dates. Retain Main Street and neighborhood membership separately.
- [ ] **L-02 / #3/#22/#25:** acquire a comprehensive current City property/real-estate register or verifiable government-owner classification; match exact parcel IDs. Separate City, County, school district, utility and other public ownership. Existing clean parcel extracts exclude owner fields, so they cannot establish ownership. Import only the government ownership classification needed for the project.
- [ ] **L-03 / #3/#20:** inventory vacant-land candidates across all ownership types using documented OCPA use-code definitions plus dated aerial/permit review. Separate vacant land, vacant building, demolition/construction, park/open space, water, parking and underused developed land. Absence of a building polygon is insufficient evidence of vacancy.
- [ ] **L-04 / #4/#5:** reconcile exact City zoning with parcel geometry, split-zoned sites, future land use, overlays, effective ordinance dates and PD conditions. Deliver fields and five safe sample rows, coverage/overlap report and map filters. Keep unknown/conflicting cases visible.
- [ ] **L-05 / #14/#21/#28:** produce reviewed residential/office/mixed-use/activity-center/public/conservation breakdowns with clear denominators: parcels and clipped land area separately. Evaluate townhouse/residential/commercial scenarios only after current allowable-use and site constraints review. Zoning is not a guarantee of approval or financial feasibility.
- [ ] **L-06 / #17/#18/#23:** model verified parks and public-space connections, paths, canopy, play/pavilion footprints and parking/access; do not treat every green or publicly zoned polygon as developable vacant land. Preserve existing and proposed public-space scenarios.
- [ ] **L-07 / #13:** independent QA samples parcel identities, ownership evidence, vacancy labels and zoning joins; verifies full-scope coverage and source dates before opportunity-site claims or published totals.

AI responsibility: GIS analyst sources/profiles; property analyst resolves public ownership/vacancy; planning analyst reviews zoning/PD/FLU; environment artist models accepted park detail. GIS lead is accountable, PM coordinates dependencies, Director accepts integration and independent QA verifies findings. No acquisition, sale or development approval is implied.
