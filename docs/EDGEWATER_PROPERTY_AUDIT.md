# Edgewater corridor property and zoning verification

October 28, 2026. The earlier four-address commercial listing review was bounded research, not a corridor inventory. This audit expands the review queue to every parcel intersecting the official College Park Main Street boundary plus Edgewater-address parcels in the current extraction. It does not cover the entire Edgewater roadway outside the College Park project limits.

## Work executed and findings

`tools/audit_edgewater_properties.py` queried OCPA parcel attributes for **456 features / 455 unique parcel IDs**, using source OBJECTIDs and exact parcel identity checks. Original responses and request receipts are cached under `data/cache/edgewater_audit`; offline replay succeeds. Owner/contact and valuation fields are excluded. Each row retains City zoning polygon intersections above 1 m², exact overlays, PD name, tax/land/building use codes, parcel storeys, separate condo unit floor, year, accepted model links and spatial footprint candidates. It does not promote a spatial overlap to an accepted identity.

Results: **162 commercial-tax-family review records**, **35 without an accepted model link**, and **17 without a visible legacy building footprint intersecting their parcel by more than 1 m²**. These are parcel records, not 17 or 35 proven missing physical buildings. Parking/vacant parcels, condo units, multi-parcel buildings, redevelopment reconstructions and source geometry errors require classification first. The audit also identifies **201 records intersecting selected mixed-use/activity-center/office/industrial-commercial zoning families**; these overlap the tax review and must not be added to it as separate properties.

Local deliverables: `data/commercial/edgewater_property_audit.json` (full evidence/quality queue) and `.csv` (safe flat inventory), with source fields and hashes. Current listing status remains unknown; physical-building verification is false until reviewed. Fresh OCPA attribute retrieval does not refresh historical footprints or prove present occupancy.

| First review examples | OCPA parcel | Model finding | Next verification |
|---|---|---|---|
| 1300 Edgewater Dr | 292223298001041 | Building_3053 overlaps; spatial-review identity only | Resolve source identity and current form/use. Historical broker office label conflicts with later change-of-use evidence. |
| 1301 Edgewater Dr | 292223001201060 | No visible legacy footprint candidate; tax code 2800 | Determine parking/land use before declaring a missing building. |
| 1305 Edgewater Dr | 292223001201050 | No visible legacy footprint candidate; tax code 1105 | Verify commercial condo/building-parent geometry and dated roof/ground reference. |
| 1311 Edgewater Dr | 292223001201042 | No visible legacy footprint candidate; tax code 1100 | Review continuous retail row, shared walls and parcel versus building extent. |
| 1313 Edgewater Dr | 292223001201041 | No visible legacy footprint candidate; tax code 1100 | Review together with adjacent storefront row; avoid one invented building per tax parcel. |

These examples lie in MU-1/T/SP/AR in the City extract; 1300 also intersects a 1.46 m² R-1A/T sliver, which is unresolved rather than silently assigned as meaningful split zoning.

## Other-source checks, not automatic model changes

- [1300 broker archive](https://www.loopnet.com/Listing/1300-Edgewater-Dr-Orlando-FL/21235451/) describes a one-storey office and is no longer advertised. [City December 6, 2021 minutes](https://orlando.novusagenda.com/agendapublic/DisplayAgendaPDF.ashx?MinutesMeetingID=2680) record assistance for Learning Minds Montessori's change of use/site improvements at this address. This demonstrates why an old commercial listing cannot establish the current tenant/use, stall count or availability.
- [1401 Edgewater broker flyer](https://www.bbdre.com/wp-content/uploads/2021/08/1401-Edgewater-Dr-1.pdf) describes renovation/office space. Current audit links one accepted model group, Building_2921. Flyer history is reference evidence, not present leasing status or an as-built façade.
- [2816 Edgewater broker redevelopment flyer](https://images1.showcase.com/d2/iIGbxo1GjsGnmD4xOHMmOlNx_CZMPt3QhOfer9WB9Vk/document.pdf) explicitly labels its leasing site plan conceptual. The [property operator contact page](https://www.edgewatermarketgardens.com/sell) corroborates address context. Audit finds three accepted parcel links and eight spatially overlapping legacy groups; neither count is a verified physical-building census. Reconcile existing structures, redevelopment status and the conceptual scheme before editing geometry.

All sources checked October 28, 2026; observation/document dates remain distinct. No outreach occurred. Search results for Edgewater Court, the City of Edgewater, other states and similarly numbered addresses are excluded. Do not import another county's detailed tax subcode meanings as OCPA definitions.

## Corridor completion packages

- [ ] **EW-01 / #3/#4/#5:** freeze the complete project corridor boundary and coverage ledger; review every parcel, exact City zoning/overlays/PD/FLU and split/sliver case. Extend acquisition if a frontage lies outside current coverage.
- [ ] **EW-02 / #3/#6:** resolve the 35 unaccepted-link and 17 no-footprint queues; distinguish physical omissions, parking/vacant land, commercial condos, parent sites and source shifts. Verify OCPA building subareas/records and component identities. Record accepted, unresolved or excluded with reason for every row.
- [ ] **EW-03 / #8/#20/#32:** verify every commercial/mixed-use frontage using dated aerial plus suitable street/site/broker/permit evidence. Record source independence, address/parcel/suite match and observation date. Marketing concepts, old listings and business registrations cannot establish current as-built form or availability.
- [ ] **EW-04 / #6/#17/#18:** correct accepted missing/misplaced buildings, stepped roofs, upper storeys, shared walls, garage/podium and rear paving. Preserve source geometry and manual edits through additive layers. Use measured/estimated/historical labels and independent checks.
- [ ] **EW-05 / #8/#18/#32:** separate parcel → site → physical building → storefront/suite → business → listing entities. Maintain current verified listing status as unknown when unsupported; retain historical reported status separately. Verify frontage/entrance/roof and material detail without inventing tenants.
- [ ] **EW-06 / #13/#14:** produce block-by-block counts and fixed-view before/after renders, plus a property checklist with evidence and open defects. Independently sample every resolved exception and all major multi-storey/redevelopment sites. Do not call the corridor complete from a handful of showcase properties.
- [ ] **EW-07 / #14:** maintain the implementation ledger below and link commits, source reports and acceptance results to tickets. Preserve wider parks, terrain, transportation, parking, scenario and operations scope.

Responsible: GIS/property analyst (inventory and identity), planning analyst (zoning/PD/FLU), reference analyst (independent corroboration), reconstruction/environment leads (geometry/detail). GIS lead and 3D lead accept their domains; PM coordinates; independent QA checks completeness; Director accepts integration. Physical/visual verification remains open.

## Appropriate implementation ledger

| Work already performed | Actual status and limit |
|---|---|
| Official GIS/OCPA acquisition, clean local API and source/identity registry | Implemented; source links do not prove current geometry or occupancy |
| Full official Main Street extraction | Ground coverage complete; feature/property correctness remains open; wider neighborhood extraction partial |
| Wellesley roof revision 2 | Applied historical correction, equipment height separate; façade/podium/current survey incomplete |
| Princeton reconstruction | Reviewed historical component composed; present-day detail and visual acceptance incomplete |
| Multifamily and commercial evidence | Review queues implemented; earlier broker work limited to four addresses/six claim groups, not full corridor verification |
| Roads, sidewalks and engineering evidence | Centerline/document work implemented; accurate curbs, intersections, ramps and walking routes remain incomplete |
| Aerial registration | Returned-frame overlay implemented; 13.46% requested/returned width difference caught; independent survey controls unresolved |
| Rear paving | Three interpreted interiors / 1,082.14 m² composed; complete lot edges/islands/markings/access unresolved |
| Trees/cars/materials/cameras | Original assets, palms, asphalt tiers and render pipeline implemented; recognizable tree-lined street views not accepted |
| Parks/vacant land/zoning | Extract profiled and land-review view implemented; comprehensive ownership, vacancy and full-neighborhood verification open |
| Parking studies | Sources/plan/unsent request prepared; final district report/raw counts and feasibility conclusion missing |
| NVIDIA planning/operations | Architecture/host assessment and offline replay implemented; no calibrated mobility, live feed or full server stack deployed |
| Release | Automated/local-profile checks exist; world-class visual and conference-performance acceptance remain open |
