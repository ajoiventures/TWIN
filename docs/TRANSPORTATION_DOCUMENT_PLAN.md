# Transportation documents and correction plan

Checked October 28, 2026. Priority area: Princeton Street / Edgewater Drive, then College Park Main Street. Owners: Transportation GIS Analyst (source review), Civil/3D Geometry Engineer (reconstruction), independent QA Analyst (acceptance), PM Agent (dependencies).

## Latest applicable revision check — October 28, 2026

The [official MetroPlan TIP page](https://metroplanorlando.gov/plans/transportation-improvement-program/) now links [FY27–31, adopted July 2026 and amended September 2026](https://metroplanorlando.gov/wp-content/uploads/TIP_FY27-31_Adopted-July-2026_Amended-September-2026.pdf). The publisher states approval July 8 and amendment September 9, 2026. Use this version for applicable current program records; the November 2025 PDF below remains historical. Review changed Edgewater project entries before updating any program claim; neither edition supplies accepted roadway geometry. Follow [the living documentation rules](INDEX.md).

## Verified official references

| Document | Verified location | Application and limit |
|---|---|---|
| [Edgewater Drive Vision Plan Support Document, final v1.4, April 22, 2009](https://www.orlando.gov/files/sharedassets/public/documents/city-and-district-plans/edgewater_support_document_v1-4.pdf) | Downloaded; 101 PDF pages; Transportation starts physical/printed p.34 | Historical lane/parking/bicycle context. Crucially describes bike lanes absent between Princeton and Smith to accommodate turn lanes. Do not apply a corridor-wide generic bike section here. Reconcile with a dated existing-condition reference before geometry acceptance. |
| [Orlando Engineering Standards Manual, fifth edition](https://www.orlando.gov/files/sharedassets/public/documents/engineering/platting/engineeringstandardsmanual.pdf) | Linked by current City Engineering Documents page; adoption table says April 18, 2016 | Sections 1.02.02/1.04: records/digital access; 5.03: as-built surveys; 6.12: sidewalks/curbs; Chapter 8: markings, intersections, pedestrian facilities, turn lanes, driveways, signals and parking. Standards define construction requirements, not measured existing features. Check amendments and actual project sheets. |
| [City 2021 ADA Transition Plan, Appendix L](https://www.orlando.gov/files/sharedassets/public/documents/public-works/ada-transition/14-appendix-l.pdf) | Readable 23-page PDF; layer inventory physical p.2 | Documents ramp, sidewalk and crossing datasets and lifecycle attributes. Acquire actual layers plus dictionaries; the PDF is not the geometry. Preserve historical, missing, future and under-construction distinctions. |
| [MetroPlan FY26–FY30 TIP, amended November 12, 2025](https://metroplanorlando.gov/wp-content/uploads/FY26-FY30-Transportation-Improvement-Program-Amended-November-12_2025.pdf) | Downloaded; physical pp.81–82 | 441275-1 covers Lakeview–Par; 441275-2 is Segment A, Lakeview–Lake Adair. Use these project identifiers to find records. Segment A does not establish the Princeton intersection layout. TIP funding entries are not construction drawings. |
| [City Complete Street project](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project) | Current public project history and timeline | Confirms design milestones through final-plan submission in December 2025. Use to locate the corresponding sheets and distinguish proposed changes from existing conditions. A milestone does not mean the sheets were acquired. |
| [FHWA Road Diet guide, Appendix A](https://highways.dot.gov/safety/other/road-diets/road-diet-informational-guide/appendix-road-diet-safety-assessment-studies) | Readable federal reference | Identifies City of Orlando's 2002 Edgewater before/after re-striping study. Original report remains an acquisition target; short-term historic safety findings are not current model validation or a forecast. |

Local source PDFs/receipts remain ignored in `data/transport/references/`. Download dates, document dates and physical PDF page numbers are distinct. The 2009 support document SHA-256 is `d98190341b1047b29ee7995a4b41b37f7102c24dcc2effffb0487c8caaf9bb2a`; TIP SHA-256 is `e15b5f75653d0442c86edc3185382b81362b70a991519cefeded60a29aede291`.

## Acquisition targets, not obtained plan sets

- Full May 2018 MetroPlan Edgewater concept-development report, existing-condition exhibits and alternatives. Completion is documented in [MetroPlan's final FY2021–22 work program](https://metroplanorlando.gov/wp-content/uploads/MetroPlan-Orlando_FINAL-FY2021-FY2022-UPWP-2020-09-10.pdf), but the report itself was not located in this pass.
- City's latest signed/sealed corridor roadway, signing/marking, signal, pedestrian/ADA and landscape sheets, revision history and existing-condition survey. Request the Princeton–Edgewater sheets specifically; do not substitute Lakeview roundabout sheets.
- Existing/as-built Princeton intersection signal and pavement-marking plans, topographic/ROW survey, curb returns, ramps, crossing/stop-bar locations, turn-pocket tapers, parking and driveway plans, plus CAD/LandXML/GIS originals if available.
- March 2020 Lakeview roundabout analysis: context for the future scenario, not Princeton existing geometry.
- [Orlando procurement project 194432](https://procurement.opengov.com/portal/orlando/projects/194432): identified as a Segment A CEI lead; direct access returned 403. Contents were not reviewed; no access workaround or outreach performed.
- [City agreement attachment 6554](https://pub-orlando.escribemeetings.com/FileStream.ashx?DocumentId=6554): indexed engineering scope lead; direct access returned 403. Treat as unreviewed until obtained.

Use the [City Engineering Documents route](https://www.orlando.gov/Our-Government/Records-and-Documents/Engineering-Documents) for engineering/as-built records. No records request has been submitted.

## Ticket execution and acceptance

1. **#25 — Acquire and index documents (P0 prerequisite).** Obtain the targets above; record title, issuer, document/revision/observation dates, geographic limits, sheet numbers, scale, horizontal CRS/units, vertical datum, status (existing/as-built/design), permitted use and retrieval receipt. Deliver a sheet-by-sheet source register and explicit missing-record list.
2. **#15/#16 — Extract evidence.** Extract only supported lane, curb, crossing, ramp, signal, parking and sidewalk attributes. Resolve units and lifecycle codes. Deliver georeferenced reference features, a data dictionary and an uncertainty queue. Standards and budget pages cannot substitute for actual measurements.
3. **#17 — Rebuild Princeton–Edgewater first.** Align accepted existing-condition sheets to City coordinates; construct road edges, approach lanes/turn pockets, crossing/stop bars, curb returns, sidewalk corners and driveway joins. Preserve hidden/uncertain areas and report source residuals rather than claiming a survey tolerance.
4. **#21 — Separate future scenario.** Build proposed improvements only from the applicable dated design sheets; retain existing conditions independently. Reconcile superseded 2018 alternatives with later designs.
5. **#18/#13 — Conference acceptance.** Review plan and tilt-shift views together; check lane connectivity, corner joins and walking-path clearances, then capture repeatable frames and measure performance at the actual presentation resolution. Completion requires both visual review and evidence-backed geometry; this document does not mark road accuracy complete.

## Main Street street-lighting work package

Priority: P1; Princeton–Edgewater first, then the Main Street corridor. Responsible: Lighting/Environment Artist; accountable: 3D Technical Lead; source verification: Transportation GIS Analyst; independent review: QA Analyst. Dependencies: #25 engineering records, #16/#17 pedestrian geometry; implementation #18, proposed scenario #21, presentation acceptance #13.

- [ ] Inventory existing pole positions, fixture family, mounting/arm height, orientation and source/date from City/OUC plans or dated authorized references. Existing illustrative lamps are not an inventory.
- [ ] Obtain applicable lighting and photometric sheets, fixture schedules and manufacturer IES distributions where available; record lumens, color temperature, optics and uncertainty. Do not choose real-world specifications solely for appearance.
- [ ] Model correctly scaled poles, arms and fixtures; check placement against ramps, crossings, trees, parking and storefront entrances.
- [ ] Build daylight, dusk and night presets with controlled exposure, believable light falloff/contact shadows and restrained bloom. Label artistic settings separately from measured lighting data.
- [ ] Keep existing lighting and proposed Complete Street decorative lighting in separate switchable layers.
- [ ] Review Princeton intersection and sidewalk approach plus Main Street tilt-shift views. Check glare, tree occlusion, spill toward residences and performance at conference resolution. A rendered lighting review does not certify photometric compliance.

Official references: [OUC Development Services Guide](https://www.ouc.com/wp-content/uploads/2024/12/Development_Services_dev_guide.pdf), lighting discussion p.28; [OUC outdoor lighting](https://www.ouc.com/solutions-programs/business/outdoor-lighting/); [Orlando Engineering Standards Manual](https://www.orlando.gov/files/sharedassets/public/documents/engineering/platting/engineeringstandardsmanual.pdf); [Edgewater project](https://www.orlando.gov/Building-Development/City-Projects/Edgewater-Drive-Complete-Street-Project). These establish records/coordination leads, not verified existing fixture locations or a selected Main Street fixture. Downtown-only fixture guidance and unincorporated County rules must not be applied to College Park automatically. No utility request, purchase or installation is authorized or performed by this plan.

The September 2026 TIP PDF was downloaded and inspected locally on October 28; Edgewater project references occur on physical PDF pages 434–435, with additional index references at 742–743. Original bytes and retrieval/checksum receipt are preserved in ignored `data/transport/references/metroplan_tip_2026_09.pdf` and its source receipt. This verifies availability and reference locations, not an engineering geometry acceptance.
