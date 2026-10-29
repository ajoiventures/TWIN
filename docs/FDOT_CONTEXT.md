# FDOT roadway and annual traffic context

Implemented bounded source delivery for [ticket15](https://github.com/ajoiventures/TWIN/issues/15), separate from LYNX, parking-demand and geometry acceptance. Owner: GIS/Data Analyst. No active snapshot, API/UI configuration, scene, user editor or private BOOMS source changed.

## Actual delivery

`tools/fdot_context.py` builds guarded `data/processed/fdot_context/packet.json` and a standalone interactive `coverage.html`. The packet contains original fields, field dictionaries/source XML definitions, first five safe rows per table, publication/retrieval/inventory dates, source IDs, null/blank/zero profiles, original download receipts, exact query receipts, hashes and coverage/exclusion queues. Original JSON caches remain in `data/cache/fdot_context`; exact source ZIP/XML/PDF bytes remain in `data/transport/fdot_context`. No aerial/canopy/private imagery is used.

The query uses the **full official College Park neighborhood**, bbox[-81.4046556182154,28.5529171498791,-81.3750768508643,28.5900242176227], followed by exact polygon intersection. Main Street is checked separately. Boundary-touch-only line candidates are excluded from positive-length counts. These are source-event counts, not independent physical road/sidewalk counts.

| Table | Neighborhood | Main Street |
| --- | ---: | ---: |
| City official street centerlines |767|86|
| FDOT native roadway names |32|6|
| RCI Top30 attribute events |69|13|
| Through-lane count events |70|15|
| Through-lane surface-width events |49|11|
| Posted-speed events |13|4|
| Sidewalk width/separation events |148|32|
| SHS sidewalk/gap inventory events |3|1|
| Annual average traffic events |26|5|
| Portable monitoring sites |16|1|
| Telemetered monitoring sites |0|0|

All16 portable sites match an AADT event by **COSITE + SECTION_/ROADWAY + YEAR_=2025**, with equal reported AADT values. Their source-point/event distances are at most0.000048m after transformation: numerical/source correspondence, not surveyed accuracy. No matching site was inferred solely from location. There are no telemetered sites inside this boundary; this does not claim no live sensors exist elsewhere or in other systems.

Concrete Edgewater reference: portable site `COSITE755154`, original OBJECTID11679, roadway75260000, reports **12,700 vehicles/day for2025**, described by the source as200ft south of Princeton. Site758280 on roadway75260500 reports8,600 for2025 north of Colonial. Site758034's9,200 belongs to **Par Street**, despite its comment mentioning Edgewater; it is not assigned to Edgewater by a text search.

## Official source selection and dates

FDOT's [official GIS directory](https://www.fdot.gov/statistics/gis/default.shtm) links its [ArcGIS organization](https://fdot.maps.arcgis.com/home/index.html). The public portal-self metadata verifies organization ID `O1JpcwDW8sjYuddV` and name Florida Department of Transportation. Hosted item association/public access and service URL namespace are checked before querying. Unrelated consultant/county copies are not used as primary FDOT data.

| Product | Selected original source |
| --- | --- |
| Annual traffic |[Official item ceb698fb86d446c08f0b8e54acab6293](https://www.arcgis.com/home/item.html?id=ceb698fb86d446c08f0b8e54acab6293)|
| Lane count |[Official item3f217f88f25347709458ee7f9f651e03](https://www.arcgis.com/home/item.html?id=3f217f88f25347709458ee7f9f651e03)|
| Posted speed |[Official item4a61f17ab4784202ae10d7d5fb3bf9de](https://www.arcgis.com/home/item.html?id=4a61f17ab4784202ae10d7d5fb3bf9de)|
| Sidewalk width/separation |[Official item9ccec088b77e4f3ebe9b2deccda7347d](https://www.arcgis.com/home/item.html?id=9ccec088b77e4f3ebe9b2deccda7347d)|
| Sidewalk/gap inventory |[Official item4c970deb696d451283e8e4b7f4464667](https://www.arcgis.com/home/item.html?id=4c970deb696d451283e8e4b7f4464667)|
| Native names/RCI/monitor sites |[FDOT RCI MapServer](https://gis.fdot.gov/arcgis/rest/services/RCI_Layers/MapServer), layers13/29/9/16|
| Surface width |[Original statewide ZIP](https://ftp.fdot.gov/public/file/7haqhkucfeizcbq_wua8kw/surface_width.zip) and [original XML](https://ftp.fdot.gov/public/file/orx24p1f70wc9nrxq3rjpg/surface_width.shp.xml)|
| City backbone |[City Street_Centerline service](https://services5.arcgis.com/mMuoPCaIYD4wEgDl/arcgis/rest/services/Street_Centerline/FeatureServer/0)|

Hosted spatial-publication and original surface-width metadata dates are **2026-10-24**. FDOT publishes GIS exports weekly; this does **not** date the field survey or certify current conditions. Annual traffic records here are2025; the directory describes annual traffic updates each April. Exact count observation intervals and most inventory acquisition/effective dates remain unknown. Sidewalk/gap EFFDT/LASTINVDT/NEXTINVDT are retained as separate original dates, not replaced by the2026 export date. MapServer products without an explicit publication date retain unknown. Every actual request/download retrieval time is recorded separately in receipts.

The original surface-width ZIP is13,175,137 bytes. Its embedded XML and separately fetched XML have identical SHA256 `ed658cc13935cb938d8a1116744c0565f16f8bb96fa8dcd8ac6bf20a5a3ac9ce`; the helper rejects a mismatch. Native CRS is EPSG26917 (NAD83/UTM17N), meters. City source native CRS is EPSG2236/102658; output geometry is EPSG4326 and coverage computations EPSG32617 meters. No vertical datum is used to infer elevation. Source geometry is preserved in caches; normalized records carry explicitly clipped reference geometry.

## Units, identities and unknowns

- Original8-character ROADWAY and6-character COSITE strings keep leading zeroes. FDOT FID/OBJECTID or shapefile record ordinal is revision-specific; original ROADWAY/roadside/milepoint/site/year fields are also retained in native event keys. A shapefile ordinal is not a global agency feature ID.
- City OBJECTID, GlobalID and CenterlineID remain distinct from FDOT event IDs. No OSM IDs are imported or treated as interchangeable; the packet explicitly leaves the OSM reference absent.
- Original surface WIDTH is **feet of total through-lane width for one roadside**, not ROW, all pavement, curb-to-curb or sidewalk width. Convert using0.3048m/ft only after the XML unit check.
- Sidewalk SWSCD is feet, recorded to nearest foot. DISTFMRD is sidewalk separation in feet, referenced to the outer pavement/back of curb, documented by [F216](https://ftp.fdot.gov/public/file/FEpK78STbEepvxkCCln3Dw/FDOT_RCI_Handbook_F216.pdf) physicalpage11/printed7-201. Its half-foot collection precision is not surveyed positional accuracy. Zero separation is valid; blank remains unknown because source instructions also allow no recorded offset for a back-of-curb sidewalk. No blank-to-zero coercion occurs.
- Lane counts apply to C/R/L roadside records. They are not blindly summed. Posted speed is mph ([F311](https://ftp.fdot.gov/public/file/3Sk3Lfw5_0WgiGgjclpuaA/FDOT_RCI_Handbook_F311.pdf), physicalpage2), not measured operating speed or a current legal verification.
- ROAD_SIDE/DIRFMRD domains are retained; relative right/left is **not** promoted to an east/west/north/south sidewalk or City travel direction. Cardinal-side/linear-reference alignment is still unverified, so the tool authors no offset sidewalk geometry.
- AADT is an annual daily average, not live flow or the original short-count measurement. XML defines S/F/C estimation flags; the packet recognizes those only. Observed T(7rows) and R(1row) remain definition-unresolved; no method is invented. A source ACTIVE=Y does not mean a live feed is available.
- Raw null/blank/zero values remain distinguishable. Nonpositive widths, lanes, speeds and AADT normalize to unknown. Source-coded gap G means an inventory classification in its SHS scope, not a complete present-day sidewalk census.

## Actual local coverage screen

City segments are sampled at intervals no greater than10m. A candidate FDOT line must lie within12m and have a local tangent within20degrees of parallel. This is a documented inventory/alignment screen, **not** accepted network identity, positional tolerance, curb/sidewalk edges, travel direction or proof of physical presence/absence. Intersections do not qualify solely by proximity when tangents disagree. All candidate source-row IDs and uncovered sampled lengths remain in the packet.

| Named City reference | City segments | Sampled length | Lane/surface-width/sidewalk/AADT nearby-line screen | Speed nearby-line screen |
| --- | ---: | ---: | ---: | ---: |
| Edgewater |42|4,222.55m|83.68%|56.93%|
| Princeton |24|2,744.04m|93.15%|79.21%|

These percentages include partial records across the full neighborhood and are **not sidewalk completeness percentages**. The coverage page shows City streets, explicit below80% sidewalk-inventory screening candidates, source lines/sites, the Main Street boundary, selectable rows and separate layer controls. Current Edgewater inventory has real attributes, but both local-road coverage gaps and alignment gaps remain. Original widths cannot replace source-referenced curb/frontage geometry under #16/#17.

## Script contract, reproduction and preservation

This new helper reuses `data_pipeline.Client/arcgis` for bounded query IDs, complete batches, cache provenance and offline replay. It extends the earlier consultant-hosted `acquire_transport.py` discovery with verified primary FDOT products and full official-boundary coverage; it does not alter that adapter or the active network.

Prerequisites: current project Python, existing `.dependencies`, plus pinned **pyshp2.3.1**. It was installed with `python -m pip install --target .dependencies --no-deps pyshp==2.3.1`; no shared lock file changed. The original [PyPI release](https://pypi.org/project/pyshp/2.3.1/) wheel was downloaded against its official index, checked against release SHA256, and installed `shapefile.py` compared byte-for-byte. Ignored `pyshp_install_receipt.json` records the proof. A new environment may create a runtime fingerprint-only receipt and leaves its independent official-wheel comparison unknown.

```powershell
& '<configured-python.exe>' tools/fdot_context.py --live  # populate missing bounded public caches
& '<configured-python.exe>' tools/fdot_context.py         # offline replay; default
```

FDOT public REST/download requests succeeded without tokens or credentials. No published request-rate limit was found; this does not imply unlimited access. Queries use50-ID batches, timeout/retry bounds and a5,000-feature per-layer cap. The original surface ZIP has a16MB download cap and200MB uncompressed cap; no ZIP entries are extracted onto disk. XML/PDF downloads have smaller explicit caps. JSON checksums bind parsed/reserialized cache files, not HTTP wire bytes; ZIP/XML/PDF checksums bind exact downloaded bytes. FDOT's actual as-is/no-warranty terms are retained in the register; no additional reuse warranty or survey certification is inferred.

`validate(root=ROOT)` returns the verified packet or raises ValueError/OSError for stale/changed/missing evidence. A separate receipt binds both packet and coverage bytes; dependencies bind source cache/provenance, binaries, source dictionaries, boundary, snapshot pointer, helper and pyshp source. Rebuild refuses modified/unreceipted prior outputs and preserves timestamped rollback backups before guarded publication. There is no apply/scene mode. For integration, expose the validated packet's tables/summary and the fixed allowlisted coverage file; do not serve unchecked arbitrary paths or invoke agencies per browser refresh.

Meaningful local verification: successful real acquisition, identical offline table/join/coverage replay, matching source ZIP/XML, actual packet validation, packet-only tamper rejection, source-only tamper rejection, and modified-output rebuild refusal with unchanged bytes. Evidence is ignored `data/processed/fdot_context/checks.json`; no broad test suite or new test scaffolding was added. Independent source review passed; see [review evidence](evidence/fdot-context-review.json). Browser integration is recorded below.

The expanded #15 scope includes the delivered [LYNX integration/review](LYNX_GTFS_REFERENCE.md), and still requires verified stop-side/pedestrian connections, cardinal-side/LRS checks, and the added parking/bike/scooter capacity/restriction/demand/turnover work. This FDOT packet alone does not close ticket15 or establish current road, sidewalk or traffic geometry.


## App integration and actual verification

The validated coverage map is available at `/fdot-context`; `/source-browser` lists all eleven tables with original field dictionaries and the first five records. API tables use `/api/v1/fdot_<table>?limit=5`; `/api/v1/fdot_context_quality` returns source/coverage metadata and table dictionaries without full row arrays. Fixed allowlists and the adapter validator protect these routes. No agency requests occur per display refresh.

Actual API checks returned 148 sidewalk records with five samples and zero telemetered records with an empty sample. All eleven table readers matched the reviewed counts. Actual browser selection showed sidewalk dictionaries and five rows; map selection of portable site11679 exposed original COSITE755154, roadway75260000 and the 2025 annual average12,700vehicles/day at Edgewater200feet south of Princeton. This is not a live count. [Browser screenshot](evidence/fdot-source-browser.png).

The integrator refreshed only its owned review API on port8773 with selection preservation. Original API, user Rhino/Omniverse sessions, active snapshot and scene geometry were not changed. Ticket15 remains open for its wider acceptance scope.

Independent integration review by the PM agent passed the route allowlists, validation, zero-row field dictionaries, snapshot guard, safe text rendering and live HTTP responses. The reviewer did not implement these API/browser changes.
