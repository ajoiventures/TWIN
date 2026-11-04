# College Park parking and mobility references

Bounded implementation for [ticket15](https://github.com/ajoiventures/TWIN/issues/15), P-02/P-04 of [parking review](PARKING_FEASIBILITY_REVIEW.md). Owner: GIS/Data Analyst. This delivers attributable source records and a precise missing-data queue, not a complete parking study. No active scene/API/UI/root, user editor, private BOOMS data, agency contact or GPU operation changed.

## Useful acquired local records

`tools/mobility_inventory.py` publishes ignored `data/processed/mobility_inventory/packet.json` and selectable `coverage.html`. Its three tables have **4 local reference contexts,24 published study count cells and70 proposed recommendation rows**, with source register, schemas, first-five previews (four when only four exist), dates, hashes, geographic status and unresolveds. Never combine these table types into a capacity total.

| Reference | Actual attributable fact | Limit |
| --- | --- | --- |
| Albert Park | [District operator](https://www.thedrivecollegepark.com/plan-your-day/) reports8 standard spaces plus1 accessible space and a3-hour limit08:00Ã¢â‚¬â€œ18:00 every day |9 is arithmetic of the operator's claim, not surveyed or legally usable capacity. No occupancy/ADA certification. |
| Edgewater Drive | Same operator reports2-hour parking MondayÃ¢â‚¬â€œSaturday08:00Ã¢â‚¬â€œ18:00, without restrictions after18:00 or Sunday |Not a City ordinance/sign survey, fee rule or precise regulated-blockface inventory. City centerlines supply reference context only. |
| Wellesley | Same operator reports public parking on the second floor |Quantity, fees, hours, entrance, current legal access and whole-garage parcel identity remain unknown. No public/private capacity inferred. |
| College Park Neighborhood Center EV | [City facility page](https://www.orlando.gov/Our-Government/Departments-Offices/Executive-Offices/CAO/Sustainability-Resilience/Green-Works-Focus-Areas/Alternative-Transportation/Expanding-Public-Electric-Vehicle-EV-Charging-Infrastructure/College-Park-Neighborhood-Center-Station) reports2 chargers at2393Elizabeth Avenue |Static charger count, not2vehicle spaces or live charger availability. |

The [official Albert Park page](https://www.orlando.gov/Parks-the-Environment/Directory/Albert-Park) corroborates a parking-lot/on-street amenity and supplies a facility reference point at2400Edgewater. Its park-opening hours remain park context, not a parking access agreement. Official webpage coordinates are interpreted as EPSG4326 display references; a surveyed datum/accuracy is not supplied.

All located contexts intersect the actual official College Park neighborhood; Main Street intersection is recorded separately. The map uses facility/address points and a City street reference clipped to Main Street, **not** parking polygons, stall centers or entrances. The exact2305Edgewater City address point is reference context for Wellesley. Its original PID can be a condo/unit reference and is retained separately; it is not promoted to a garage parcel or ownership link. Existing City/FDOT adapter validators and transitive source hashes bind these contextual locations.

No observation dates or legally verified capacity/access were supplied for these local claims. Retrieval on October29,2026UTC is not the sign/rule effective date. Occupancy, demand, turnover, observation intervals, loading/EV/reserved-space splits and district-wide deficit/surplus stay unknown. Illustrative scene cars and private access are never used as inventory evidence.

## New actual City report, and its missing inventory

The actual [City study page](https://www.orlando.gov/Building-Development/City-Projects/Bike-and-Micromobility-Parking-Study) now links both the [final report](https://www.orlando.gov/files/sharedassets/public/v/1/departments/transportation/bike-and-micromobility-parking-study-final-report-8.26.pdf) and [recommendations](https://www.orlando.gov/files/sharedassets/public/v/1/departments/transportation/bike-parking-study-final-recommendations-8.26.pdf). Both original PDFs were downloaded and checksummed; the report is10,626,719bytes/93physicalpages.

- Cover document date: **July31,2026**. PDF creation metadata: August3,2026. Neither is the inventory observation date, which remains unknown.
- Actual rendered physicalpage6/Figure1 was inspected: its legend identifies downtown districts, Ivanhoe Village, Parramore, Creative Village and Thornton Park, with major venues. College Park is not a named study district. Without its GIS boundary, exact intersection with the wider College Park neighborhood is **unknown**, not an asserted zero.
- Actual rendered physicalpage90/AppendixD contains only its inventory title/divider, with no map, records or link annotations. Pages91Ã¢â‚¬â€œ93 are other appendix dividers. The only embedded files are two accessibility HTML reports; no GIS inventory is embedded. The helper pins the actually reviewed report SHA256 `3a81831860dd55f195809463fbde0d4ac01a4d37c89a8f1c7275cea74188914a`, so a revised report requires a new visual/geographic review.
- The separate recommendations PDF provides70 original OBJECTID/ID rows. These are normalized as **proposed, unlocated** records, not existing College Park facilities. Original names/districts/locations/priorities and incomplete source text remain intact. No geocoder or invented coordinates were applied.

The report's existing counts are facility records, **not spaces**. The parser preserves source inconsistencies rather than resolving them by assumption: prose325bike facilities versus Table9's323; Table9 formal total51 versus district-cell sum52; informal total61 versus sum60; City District formal17 in Table9 versus16 in Table11. These are separate source-conflict records, never College Park supply estimates.

The precise remaining artifact is the original existing/proposed **GIS/FieldMaps inventory and study boundary**, including stable features, coordinates, capacity units, public/private/status fields and actual inventory dates. The report says it exists, but the retrieved public attachments do not contain it. Public City Socrata and verified City ArcGIS catalog searches found no selected space/rack/corral capacity dataset; the BikeFacilities layer describes lanes/trails, not a bike-parking inventory. A bounded search is not proof that no agency/internal data exists. No application, records request or other outreach was sent.

## Script contract and source handling

The helper reuses the existing JSON Client/cache and validated City-address/FDOT-street adapters. It adds document/web-reference normalization because those existing adapters do not supply parking counts, local visitor rules or the final micromobility report. It never changes their implementation or active data.

Original HTML/PDFs, source receipts and locally rendered reportpages remain in ignored `data/processed/mobility_inventory/sources`. Only normalized references and a pixel-free map are integration candidates; do not expose raw page/PDF/image files through a general file route. No affirmative redistribution license was established. Public access was observed without credentials; source refresh cadence and request-rate limits were not published. The helper limits HTML downloads to5MB, PDFs to20MB and uses45-second timeouts. No private/restricted canopy, individual trip logs or private BOOMS data was read.

```powershell
& '<configured-python.exe>' tools/mobility_inventory.py --live  # acquire missing bounded public sources
& '<configured-python.exe>' tools/mobility_inventory.py         # default offline replay
```

Prerequisites: existing project Python/.dependencies, pypdf, Shapely/pyproj and accepted City/FDOT packets. Rebuilding is a single-writer operation. A separate receipt binds packet and coverage bytes; dependencies bind original source bytes/receipts, snapshot/boundary, helper and contextual adapter evidence. Modified or unreceipted prior outputs are refused, with a timestamped backup before guarded replacement. `validate(root=ROOT)` returns the verified packet or raises ValueError/OSError; integrations must call it and serve only allowlisted artifacts. There is no scene/apply mode.

Observed checks are recorded in ignored `checks.json`: actual source parsing/geographic checks, semantic offline replay, exact70recommendation IDs, packet-only/source-only mutation rejection and preservation of edited prior outputs. Generated map JavaScript is syntax-checked. Actual browser integration and independent acceptance remain separate. No broad test scaffolding was added.

This completes the bounded acquisition/reference packet. P-02's space-level capacity/access/entrance inventory and P-04's dated weekday/weekend/event demand/turnover observations are still unfinished; neither this packet nor the separate FDOT/LYNX work alone closes the expanded ticket15 scope.


## Completed schema and local integration handoff

`table_field_dictionaries` now covers every actual exported field in each of the three tables, including `scope.*`, park-hours context and all seven original `source_fields.*` recommendation columns. Entries describe meaning, observed JSON types, optional presence and unknown/null semantics. The original generic dictionary remains compatible. The validator rejects incomplete top-level/original-column definitions; a new exported field also fails the builder until documented. The actual source tables remain identical to the initial source/guard review.

Read-only local integration is implemented at:

- `/mobility-inventory`: fixed, fully validated pixel-free coverage page. Raw source/PDF paths and traversal variants are not served.
- `/api/v1/mobility_inventory_quality`: source register, scope, table counts/dictionaries, first-five previews, report findings/conflicts and limits.
- `/api/v1/mobility_local_facility_references`:4reference contexts.
- `/api/v1/mobility_published_study_existing_facility_counts`:24published study-count cells, not CollegePark space capacity.
- `/api/v1/mobility_study_proposed_recommendations`:70proposed/unlocated records, not existing local facilities.

All three table routes retain standard limit/offset pagination and add their full dictionary, original first-five sample and packet checksum. The source browser checks both snapshot and packet checksum against the quality response, resets stale selection output and shows the appropriate dictionary/provenance. Navigation labels identify mixed government/district source records. The source helper and packet were frozen during integration; no API process restart or browser/Kit/GPU operation was performed by this implementer.

Actual direct route verification passed pagination(limit2,offset1),4/24/70totals,51/10/18dictionary entries, exact first-five samples, matching packet checksums, coverage200, raw-source/traversal404 and stale-evidence409. Both browser scripts pass syntax checking. `integration_checks.json` records these checks; live browser verification and independent integration review are owned by the integrator/reviewer.


The coverage page now uses a concise selected-facility card: reported spaces/charger quantity, parking level/time limits, plain-language location basis, unverified capacity/access/demand, and source links/retrieval dates. Original rows remain available only in a collapsed technical-details section. The generated script was executed against all four actual records in an isolated DOM smoke check, including Wellesley level/unknown hours and the charger-versus-space distinction. Source tables, source register and complete field dictionaries are unchanged from the independently accepted packet. The HTML/packet receipts were rebuilt because the generator changed; final visual browser review remains separate.


## Actual browser delivery review

The running local app loaded the final readable facility card. Selecting Wellesley shows second-floor parking as attributed district guidance, unknown space count/hours and unverified legal access/entrance. Source links and dates are readable; raw records are collapsed. The source browser selected the 70 proposed study records and displayed their complete nested field dictionary plus first-five preview. [Facility card](evidence/mobility-reference-card.png) and [source browser](evidence/mobility-source-browser.png). The coverage map is a reference overview; its tight facility labels still overlap at full-neighborhood scale. No scene geometry or parking capacity is inferred.
