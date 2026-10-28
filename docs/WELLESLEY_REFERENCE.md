# Wellesley, 2305 Edgewater Drive: independent height and shape reference

Verified October 28, 2026. This is a source-review artifact, not a scene change or a new surveyed building footprint.

## Primary height reference

The official [MetroPlan Orlando Sustainable Land Use Forecast PDF](https://metroplanorlando.gov/wp-content/uploads/2040-LRTP-TR1-Sustainable-Land-Use-Forecast.pdf) has a cover publication of **January 2016, Final Adopted Plan**. It is Technical Report #1 of the 2040 Long Range Transportation Plan. Appendix B reproduces earlier density examples; its embedded page footer says Technical Report #3. This naming difference is preserved rather than treated as two independent documents.

**Physical PDF page 62, printed page B-7, Figure B-5**, identifies Wellesley Condos at 2305 Edgewater Drive and reports **seven stories and 75 ft tall**, conventionally converted to **22.86 m**. The figure's text is embedded in a raster image. The complete page was rendered and visually inspected; extraction alone misses the figure text. Separately, **physical PDF page 57, printed B-2, Table B1** identifies the same property and seven stories.

This is credible independent evidence that the identified Wellesley mass is a high-rise compared with the current low-rise model. It is a historical planning/density reference, with rounded reported height, not a current roof survey, precise parapet elevation, vertical datum or height of every wing. The older embedded photographs are not current condition evidence. The appropriate quality label is `historical_planning_reported_nominal_height_not_surveyed`.

Local ignored source evidence:

- `data/imagery/wellesley/metroplan_2040_tr1.pdf`: 15,965,548 bytes; SHA-256 `2bbd566889f59a395f32f35497428bd703786932934955faf1eb05e5d049ef1b`.
- `data/imagery/wellesley/figure_page62.png`: full rendered Figure B-5 page for read-only review.
- `data/imagery/wellesley/reference_evidence.json`: source/version, page locators, scoped height statement and geometry comparisons.

## Current aerial and footprint comparison

A wider original [OCPA January 2025 aerial](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer) was exported around the full condo-family context, beyond the earlier frozen-pilot crop. Its [item description](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json) identifies the January 2025 Sanborn flight. The 1,280 by 960 JPEG shows the western multiwing Wellesley roof, central courtyard/pool and separate eastern blocks. The exact capture day, native acquisition GSD, positional accuracy and redistribution/AI-use eligibility remain unresolved. Export sampling is recorded separately in the manifest and is not acquisition accuracy.

The old `Building_2933` source is parcel `292214147406110`, building number 1, composed of nine footprint subareas. Current normalized parcel links leave it ambiguous/unmatched against replacement condo records; the old parcel ID must not be faked into an exact modern parcel match.

| Evidence | Observation | Interpretation |
|---|---|---|
| Old nine-subarea union | 1,335.87 m²; latitude range 28.57220874 to 28.57267728 | Small/disconnected component representation, insufficient to stand for the complete current multiwing building |
| 114 address-linked condo records | Union 6,146.46 m²; latitude range 28.57199782 to 28.57266505 | Tax/unit/common envelope includes courtyard and other non-roof space; not a building outline |
| Tax union outside old footprint | 5,040.91 m² | A coverage discrepancy indicator only; **not measured missing roof area** |
| Jan 2025 aerial | Multiwing roof/courtyard and southern Smith Street frontage visible beyond the old source's southern extent | Clear representation gap requiring a traced/validated roof-zone reconstruction, not uniform extrusion of tax geometry |

The whole condo-family framing also contains 630 Vassar Street records/eastern blocks. The 2305 seven-story reference must not be blindly assigned to these neighboring components.

## Why unit-floor polygons do not solve the stepped shape

Official condo `FLOOR_NO` values describe unit floor positions. They corroborate upper-level units but are not whole-building story counts or guaranteed architectural floor plates. The nine floor-code-0 records repeat the full tax envelope. Source unit polygon union areas are:

| Source unit floor code | Records | Union area m² |
|---|---:|---:|
| 0 | 9 | 6,146.46 |
| 2 | 15 | 2,131.14 |
| 3 | 15 | 2,131.14 |
| 4 | 14 | 2,043.63 |
| 5 | 15 | 2,131.14 |
| 6 | 23 | 3,349.61 |
| 7 | 23 | 3,349.61 |

The apparent increase at upper unit-floor positions reinforces the need to interpret the tax mapping before using it as architecture. Do not build automatic floor slabs, fill the courtyard, or raise all tax-parcel geometry to 22.86 m.

## Recommended scoped correction

1. Attach the historical seven-story/75-ft reference to the identified Wellesley building entity, with explicit source/page/date/quality and unresolved modern-parcel lineage.
2. Reconstruct the major roof wings, courtyard void and lower deck/garage zones from accepted aerial/LiDAR geometry. Keep uncertainty and component heights separate.
3. Use the historical nominal height as a high-rise massing reference only where the identified upper building zone is supported. Do not treat the 2016 reference as a surveyed roof measurement or a license to assign one height everywhere.
4. Preserve visible differences between historical planning reference, LiDAR-derived roof zones and estimated lower components in the inspector.
5. Review current roof/ground points after resolving the source's floor-count outlier gate; a low source floor attribute must not automatically reject plausible high-rise roof evidence.

## Reproduce and tests

`python tools/wellesley_reference.py` retains the official PDF, renders the relevant page if needed, obtains the wider public aerial export and writes safe source-geometry evidence. `--offline` replays existing local sources and verifies the aerial checksum. Outputs remain under ignored `data/imagery/wellesley/`; no owner/contact or BOOMS values are read. `shape_candidates.geojson` stores the old source and tax/unit unions, all explicitly unaccepted as a current roof footprint.

Three tests check scoped historical height, non-promotion of tax floor geometry and rejection of missing geometry. This tool changes no scene, height layer, parcel match or GitHub ticket.
