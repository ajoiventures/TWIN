# Source audit and OCPA adapter contract

Implementation checkpoint: October 28, 2026. This covers the full configured extraction containing College Park Main Street, with neighborhood context. It does not reduce tickets #2/#3 to a showcase block or complete their expanded property-verification criteria.

## Source audit and release boundary — #2

`python tools/audit_sources.py --source-root C:/Projects/BTR/Economic-Development` now runs the aggregate-only `source_audit_contract` implementation. It reads the inventory, completion tracker, normalized parcel spine and polygon snapshot separately. It reports row/unique-ID/duplicate/blank-ID/invalid-polygon counts and cross-source reconciliation **counts**, without writing private IDs, records, vacancy/use values, owner/contact details or notes. Missing sources are unavailable, not successful zero-row sources. Source fingerprints are checked after profiling; the source project is never written.

The local aggregate report stays in ignored `data/private/source_audit_summary.json`. The separate ignored public metadata register `data/processed/source_audit_register.json` contains official OCPA/City source schemas, URLs, dates, CRS, license notes and first-class City portal/GIS catalog URLs, plus a static mapping contract. It contains no private source counts or observations. No held 2026 dataset or BOOMS row is exported. The BOOMS public field allowlist is empty until source-side release gates authorize a particular release.

The mapping distinguishes `parcel_pin → parcel_id`, `cp_uid → program_record_id`, `num_floors → reported_floors`, `vacancy_status`, `building_use`, `parcel_use`, `parcel_in_use_yn`, and `last_edit_date`. Completion fields `b_buildings_complete`, `o_owners_complete`, `m_merchants_complete`, `s_spaces_complete`, `overall_complete`, `completion_score`, `booms_record_status`, and `booms_public_release_tier` are workflow/release gates, not physical building facts. Actual field presence is recorded per input. This is a mapping specification, not approval to import its values.

Source refresh code was inspected without execution. BTR's parcel refresher targets OCPA layer 4 but requests owner-related fields, so it cannot be copied into a public adapter unchanged. Its polygon acquisition uses layer 1, which must not be presumed interchangeable with TWIN's current layer 4. Its completion generator marks records for staff validation. TWIN reuses the bounded cached-query pattern with an independent safe projection. No live BOOMS API is established.

Original source acquisition/retrieval dates, licenses and CRS remain explicitly unknown where the source lacks them; local file modification dates are recorded separately. Private exception identities and held-snapshot reconciliation/release acceptance remain source-side work. The older ignored `source_audit.json` is a historical local artifact, not the current contract or a publishable output.

## Shared public ingestion interface — #3

| Interface | Behavior and limits |
|---|---|
| `Client(cache, offline=False, refresh=False)` | 60-second timeout; up to 3 attempts for transient HTTP/network failures; 1/2-second backoff. Offline miss fails without contacting an agency. Known cache checksum mismatch fails closed. Legacy retrieval time stays unknown. |
| `arcgis(client, source, bbox)` | Schema checks, bounded EPSG:4326 envelope, object-ID discovery and 50-ID batches. Missing/duplicate/unexpected rows and transfer truncation fail. Default 100,000-feature ceiling is overridable by source config. Returns GeoJSON plus original service metadata. |
| `normalize_parcels(collection)` | String PIN/source identifiers; zero/invalid/nonfinite story/year values remain unknown. Unsafe fields are projected out. Invalid geometry, missing identity and polygons outside the configured extent are quarantined with separate reasons. |
| `building_joins(parcels, base_path)` | Independent building groups, exact parcel feature IDs, source object IDs and parcel+building source keys. Multiple exact-feature candidates remain ambiguous. Spatial fallback records overlap fraction and stays unaccepted. It does not identify storefronts or suites. |
| `refresh(offline=False, force=False)` | Builds normalized tables, source manifests and quality/exception reports, then atomically advances the active pointer only after every stage succeeds. Failure preserves the previous pointer. Map/editor clients read snapshots; this adapter does not fetch on render. |

Public parcel fields are enumerated in `source_audit_contract.PUBLIC_ALLOWLIST`; OCPA request fields are in `data_pipeline.SOURCES['parcels']`. Source IDs and requested/output schemas remain separate. GeoJSON uses EPSG:4326; scene matching projects to local EPSG:32617 metres. Original source timestamps, request retrieval receipts, snapshot build time and activation time are distinct; no read/build time repairs an unknown acquisition date.

New link rows include `source_building_key`, `source_building_number`, `source_object_ids`, `candidate_parcel_features`, `join_state` and `match_confidence_basis`. Source keys preserve leading zeroes and support lineage reconciliation, but do not establish permanent physical identity across parcel splits, merges or source republication. `Building_####` remains snapshot-local.

## Usable candidate tables and current evidence

`python tools/check_ocpa_adapter.py` performs a cache-only bounded replay and writes ignored `data/processed/ocpa_adapter_preview/{parcels,buildings,quality,first_five}.json`. It does not activate a snapshot. The run produced 3,906 in-extent parcel features/3,905 PINs and 3,216 building groups: 2,976 accepted, 202 spatial-review, 3 ambiguous and 35 unmatched. Ten service-returned polygons are outside the actual study polygon intersection and are explicitly queued as `outside_study_extent`; the active snapshot retains its original 3,916 features. Existing building link decisions did not change in this replay.

The refreshed independent-overlap construction audit of the **active** snapshot records 3,178 assigned overlap recomputations, no integrity/schema errors, 103 accepted one-to-many parcels containing 224 building groups, and 561 floor disagreements (six large). It makes no acceptance decisions and never promotes a spatial link.

The existing targeted adapter regressions now cover malformed/missing attributes, swapped geometry, duplicate exact-feature ambiguity, geometry changes, source outage preserving the active pointer, timeout/retry receipts and corrupt cache rejection. These are construction checks, not independent ticket acceptance.

Remaining #3 scope includes disposition of 240 unaccepted links, high-severity floor conflicts, source-date/licensing gaps, sketch/dimension review, cross-refresh split/merge lineage and full-project missing-building/frontage verification. Existing dated landmark/property investigations contribute evidence but do not certify every Main Street/neighborhood property. Independent review and issue closure have not been performed by this builder.
