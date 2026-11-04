# City park facility references

November 3, 2026. Additive local delivery for ticket #4, L-01. The existing eleven [full-neighborhood park footprints](FULL_NEIGHBORHOOD_PARKS.md) retain their exact IDs, source attributes and geometry. The new references answer what the City directory **publishes** about each named facility. They do not verify physical access, current opening, actual amenity location or title.

| Source ID | Official directory context | Published schedule | Examples of published features |
|---|---|---|---|
| 62 | [Lake Ivanhoe Park](https://www.orlando.gov/Parks-the-Environment/Directory/Lake-Ivanhoe-Park) | Sunrise to sunset | Playground for ages 2–5; directory location differs from GIS, so no park-wide transfer |
| 66 | [Albert Park](https://www.orlando.gov/Parks-the-Environment/Directory/Albert-Park) | Daily 6 a.m.–11 p.m. | Picnic tables, accessibility and parking labels; description gives nominal 20 × 30 ft pavilion with stage |
| 79 | [Dartmouth Park](https://www.orlando.gov/Parks-the-Environment/Directory/Dartmouth-Park) | Sunrise to sunset | Paved path, playgrounds, exercise stations, pavilions and [official amenity map link](https://www.orlando.gov/files/sharedassets/public/park-images/other-parks/dartmouth-park-map.png) |
| 81 | [Don Dudley Park](https://www.orlando.gov/Parks-the-Environment/Directory/Don-Dudley-Park) | Daily 6 a.m.–11 p.m. | Open space |
| 91 | [Guernsey Park](https://www.orlando.gov/Parks-the-Environment/Directory/Guernsey-Park) | Sunrise to sunset | Playground |
| 94 | [Ivanhoe Plaza Park](https://www.orlando.gov/Parks-the-Environment/Directory/Ivanhoe-Plaza-Park) | Sunrise to sunset | Open space; distinct from Lake Ivanhoe Park |
| 113 | [Mathews Park](https://www.orlando.gov/Parks-the-Environment/Directory/Mathews-Park) | Sunrise to sunset | Baseball field |
| 121 | [Overbrook Park](https://www.orlando.gov/Parks-the-Environment/Directory/Overbrook-Park) | Sunrise to sunset | Open space; directory supplies a street number absent from GIS |
| 125 | [Princeton Park and College Park Pool](https://www.orlando.gov/Parks-the-Environment/Directory/Princeton-Park-and-College-Park-Pool) | Park page: daily 7 a.m.–9 p.m. | Playground and restrooms; no independently verified pool operating schedule |
| 145 | [Lake Adair Park](https://www.orlando.gov/Parks-the-Environment/Directory/Lake-Adair-Park) | Daily 6 a.m.–11 p.m. | Open space; street number conflicts with GIS |
| 239 | [College Park Neighborhood Center](https://www.orlando.gov/Parks-the-Environment/Directory/College-Park-Neighborhood-Center) | Center page: Mon–Fri 8 a.m.–9 p.m.; Sat 9 a.m.–9 p.m.; Sun 1–6 p.m. | Gymnasium, multipurpose room, fitness and other center facilities; not the neighboring park schedule |

The directory labels describe facilities at page scope. For example, Albert's feature list still uses a gazebo label, while its description specifies a pavilion with a stage. Neither label fixes footprint, orientation, parking capacity or entrances. Dartmouth's description identifies two small pavilions and a nominal 20 × 30 ft shade structure. The linked amenity-map image was not fetched, inspected or registered in this delivery. Published accessibility labels are not an accessible-route survey or certification.

Lake Ivanhoe's page says 6 North Ivanhoe Boulevard East; the GIS feature says 57 South Ivanhoe Boulevard. Preserve the directory page as east-side named context, not evidence that the playground belongs to every part of the clipped lake/shoreline polygon. Lake Adair's 951/995 mismatch and Dartmouth's source spelling difference remain explicit. Princeton Park/Pool and the Neighborhood Center retain separate IDs and separate page schedules even though the pages display the same 2393 Elizabeth Avenue reference address; the original park GIS address is 2411 Elizebeth St. Pool operation is unknown.

## Reuse and script contract

`tools/enrich_park_facilities.py` extends the existing inventory through a separate read-only product. It calls the existing inventory validator and requires the eleven reviewed City source OBJECTID strings. It checks each official page's canonical URL, title and structured location, hours and feature sections. The helper reads only the named official directory pages and caches original HTML with URL, retrieval timestamp and SHA-256 receipt. It does not fetch linked imagery, scripts, maps or third-party resources.

```text
python tools/enrich_park_facilities.py --live
python tools/enrich_park_facilities.py
python tools/enrich_park_facilities.py --validate
```

`--live` fills missing cached pages only. The default rebuild is offline; use the same project Python as the park inventory. Acquisitions use bounded 2 MiB reads, 30-second timeouts and up to three attempts for transient failures. Failed or changed identity/schema does not replace the last good packet. Existing incomplete or altered cache/output pairs are held for review. A checked rebuild backs up the previous packet/receipt before replacement. Retain prior versions when a new official reference is reviewed; changing receipt dates cannot make old bytes current.

Outputs remain local under ignored `data/processed/park_facility_references/`: `packet.json`, `receipt.json` and backups. The packet carries all 18 published-field definitions, eleven rows, five previews and 25 direct dependency hashes. Validation also checks the upstream inventory and its transitive sources. Raw HTML and receipt files remain ignored in `data/cache/park_facility_references/`; only selected factual fields enter the derived packet. No owner/contact fields, map keys, raw HTML or page pixels are published. No affirmative source redistribution or derivative-model license is inferred from public directory access.

The actual acquired pages reproduce all eleven records offline. Six publish textual sunrise/sunset schedules and five publish explicit seven-day schedules. Two focused tests cover schedule scoping, name/URL changes, exclusion of contact/footer content, offline missing/altered caches and the official-host guard. Retrieval timestamps are distinct from any publisher page dates and HTTP modification headers. Observation/effective dates, live opening and current field conditions remain unknown. The output is local and additive; no API, map, scene or geometry change was applied by this helper.

## Local API and source browser

Use the [City-published park features and hours preview](http://127.0.0.1:8769/source-browser?source=park_facility_references). `GET /api/v1/park_facility_references?limit=5` returns the first five reference records, all 18 field definitions and a packet hash. `GET /api/v1/park_facility_quality` returns the limits and counts. The browser requires matching snapshot and packet hash before display. Both actual API responses and the actual browser page were checked on November 3; the separate preserving review service was restarted to load the new routes and the selection hash stayed unchanged. The source browser does not change the park map or Omniverse geometry. Local screenshot: `data/diagnostics/park_facility_review_20261103/browser.png`.

[Independent review](evidence/park-facility-reference-review.json) confirms all eleven exact original identities, 25 direct dependency hashes plus upstream validation, original page receipts, independently replayed schedules/features, three location/scope conflicts, and no claim of verified current access or accepted facility geometry.

L-01 still needs dated site reconciliation, independently verified access and actual amenity placement where required. The wider ownership, vacancy, planning and site-detail gates still keep ticket #4 open.
