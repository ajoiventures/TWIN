# Source audit and OCPA adapter contract

Implementation checkpoint: October 28, 2026. This covers the configured extraction containing College Park Main Street with neighborhood context. Ticket #2 is a source inventory and release-boundary audit; ticket #3 separately owns physical property/link verification.

## Source audit and release boundary — #2

`python tools/audit_sources.py --source-root C:/Projects/BTR/Economic-Development` now runs the aggregate-only `source_audit_contract` implementation. It reads the inventory, completion tracker, normalized parcel spine and polygon snapshot separately. It reports row/unique-ID/duplicate/blank-ID/invalid-polygon counts and cross-source reconciliation **counts**, without writing private IDs, records, vacancy/use values, owner/contact details or notes. Missing sources are unavailable, not successful zero-row sources. Source fingerprints are checked after profiling; the source project is never written.

The local aggregate report stays in ignored `data/private/source_audit_summary.json`. The separate ignored public metadata register `data/processed/source_audit_register.json` contains official OCPA/City source schemas, URLs, dates, CRS, license notes and first-class City portal/GIS catalog URLs, plus a static mapping contract. It contains no private source counts or observations. No held 2026 dataset or BOOMS row is exported. The BOOMS public field allowlist is empty until source-side release gates authorize a particular release.

The mapping distinguishes `parcel_pin → parcel_id`, `cp_uid → program_record_id`, `num_floors → reported_floors`, `vacancy_status`, `building_use`, `parcel_use`, `parcel_in_use_yn`, and `last_edit_date`. Completion fields `b_buildings_complete`, `o_owners_complete`, `m_merchants_complete`, `s_spaces_complete`, `overall_complete`, `completion_score`, `booms_record_status`, and `booms_public_release_tier` are workflow/release gates, not physical building facts. Actual field presence is recorded per input. This is a mapping specification, not approval to import its values.

Source refresh code was inspected without execution. BTR's parcel refresher targets OCPA layer 4 but requests owner-related fields, so it cannot be copied into a public adapter unchanged. Its polygon acquisition uses layer 1, which must not be presumed interchangeable with TWIN's current layer 4. Its completion generator marks records for staff validation. TWIN reuses the bounded cached-query pattern with an independent safe projection. No live BOOMS API is established.

Original source acquisition/retrieval dates, licenses and CRS remain explicitly unknown where the source lacks them; local file modification dates are recorded separately. Private exception identities and held-snapshot reconciliation/release acceptance remain source-side work. The older ignored `source_audit.json` is a historical local artifact, not the current contract or a publishable output.

## Ticket #2 final acceptance evidence

The October 28 source audit now inventories **six separate inputs**: BOOMS inventory, completion tracker, normalized spine, polygon snapshot, A016 parcel-map output and ontology parcel-profile output. It profiles only source metadata/aggregate results. Nested owner/business objects and raw map payloads are never imported or displayed. Every available profile includes SHA-256, schema/storage types, null counts, identifier grain, duplicate groups/excess rows, normalization collisions, explicit CRS or unknown, geometric bounds where available, source URL or unknown, retrieval/acquisition/effective date or unknown, local modification time, and redistribution/release posture. CSV geographic coverage remains unknown; source membership is not silently equated with TWIN's current boundaries.

The ignored `data/private/source_audit_summary.json` is the restricted source register, freshness report, reconciliation report and aggregate exception queue. `profiles` holds all six schemas; `freshness_report` distinguishes original date-field ranges from file timestamps; `reconciliation_counts` compares inventory membership against every other input; `exception_queue` gives stable category keys, counts, accountable role and a source-side next action. Missing inputs produce **unknown reconciliation**, never apparent zero differences. Normalized identifier collisions are review exceptions, not accepted joins. Row-accounting arithmetic checks unique IDs + duplicate excess + blank IDs = rows. Count differences may reflect grain/vintage and must not be treated as additions/deletions of buildings.

The two source refresh/parcel-polygon registry files are fingerprinted and their schemas inventoried. Only official OCPA/City source URLs without query/fragment, and parseable check/download dates, enter the private metadata summary; free-form registry notes and identifier-bearing query URLs do not. These registry dates are explicitly registry reports, not verified acquisition dates. Source policy and refresh-script hashes bind the review to the inspected versions. No source generators execute. Existing bounded/cached acquisition patterns are reused through TWIN's independent allowlisted adapter; layer 1 polygons and layer 4 parcel queries remain distinct. The completion generator's staff-validation default remains a hold, not approval.

Publication contract:

- Official public parcel output is restricted to `PUBLIC_ALLOWLIST`; it excludes owner/contact content, business names, staff notes and arbitrary source fields.
- BOOMS row publication allowlist is **empty**. Even a source row labelled `public_record_detail` does not authorize export without the source project's release/QA gates.
- Aggregate private audit counts/date ranges remain in ignored `data/private`; the ignored public-side metadata register includes only official-source metadata, the static field mapping and allowlist.
- Held 2026 BTR snapshots are never opened, scanned or reconciled by this bounded audit. Their release prerequisites remain intact. No live BOOMS API is assumed.

Verification: the actual six-input audit completes read-only; the existing two privacy regressions pass, with coverage extended inside the same cases for normalization collisions, malformed dates, unknown release tiers and row accounting. A fixture verifies private identifiers, contact notes and observation values never appear in reports, and input bytes remain unchanged. Generated audit files are ignored; no source records are staged. These are builder checks; an independent GIS/QA review is required before closure.

Remaining source limitations are explicit **audit findings**, not fabricated metadata: original receipts/acquisition dates, exact local snapshot CRS where undeclared, redistribution authorization, and source-side disposition of identity exceptions may be unavailable. They block future release/physical integration, not recording the inventory. The audit does not authorize publishing those inputs. Source staff must supply original receipts/terms and resolve private record identities within BTR before any later release. The older map payloads' presence on disk is not proof that all nested content is publicly eligible.

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

## Independent acceptance — October 29, 2026

The parent reviewer independently inspected the implementation and actual restricted aggregate report, verified all six current source fingerprints and policy fingerprints against their audit receipts, checked complete schema/freshness/reconciliation coverage and confirmed ignored outputs. Synthetic privacy/unchanged-source checks passed after the reviewer identified and the builder fixed credential-bearing registry URL handling. [Public acceptance record](evidence/source-audit-acceptance.json) contains verification results only, without private counts or source records. Ticket #2's inventory/reconciliation-report scope is accepted; unknown provenance/terms and source-side exception disposition remain explicit constraints on later integration/release.
