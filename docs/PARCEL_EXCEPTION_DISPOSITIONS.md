# Parcel and floor exception dispositions

November 3, 2026 Â· prepared local candidate for existing #3/G07, not ticket completion.

The existing parcel audit already finds relationship and floor-value exceptions. Its new `--dispositions` mode supplies the missing per-record reason, next action, source identity, exact parcel-feature candidates and reusable historical evidence context. It avoids rerunning the costly USD geometry audit or inventing another ingestion adapter.

```text
python tools/parcel_audit.py --dispositions --output data/diagnostics/NEW_FRESH_DISPOSITIONS
```

The command reads cached audit, immutable lineage, current corridor classification, historical reconstruction and completed dated aerial review packets. It verifies active snapshot identity, lineage pointer/receipt/hash and all original packet dependencies, reuses `build_building_lineage.validate` for registry/base-geometry fingerprints, replays the exact existing two queue derivations against source snapshot/heights, then rechecks hashes before writing a fresh ignored candidate directory. The shared lineage validator opens the small base building layer to verify its semantic geometry fingerprint; this does not open the full composed scene or rerun the geometry-overlap audit. File hashes stream in bounded chunks. The command never requests agency data, changes active tables, promotes property links or alters heights. Existing `--offline` audit behavior is retained. The output is `dispositions.json` plus captured producer bytes; an existing directory or changed source is rejected. Publication/API integration and independent acceptance remain separate.

Candidate `data/diagnostics/parcel_dispositions_20261103_c/` contains 801 disposition rows bound to 188 dependencies:

| Queue | Rows | Recorded interpretation |
|---|---:|---|
| Spatial relationships | 202 | Overlap alone does not accept source identity. |
| Ambiguous relationships | 3 | Candidate features remain separate; compare exact identities. |
| Unmatched relationships | 35 | No accepted parcel feature; absence is not a missing-building conclusion. |
| One-floor numerical differences, one accepted building | 517 | Source subarea floor and parcel maximum story attributes can describe different things. |
| One-floor numerical differences, multiple accepted buildings | 38 | Parcel maxima cannot be assigned to every wing/accessory component. |
| Larger numerical differences | 6 | Check original STYS/FLOOR_NUM/unit FLOOR_NO definitions and property/component evidence first. |

Every row retains `source_building_key`, existing semantic entity ID, local alias/USD path, original OBJECTIDs, source parcel number, exact assigned parcel feature and distinct candidate features. All are `deferred_pending_property_component_evidence`, with explicit reason and next action. This is a routed work queue, not 801 completed property reviews or 561 incorrect buildings. Existing numerical floor values, height method and quality remain unchanged.

The six larger differences are Building_0434 (subarea maximum2 versus parcel11) and Buildings_1025, _2142, _2809, _2991, _3207 (1 versus3). These are source-value comparisons, not verified occupied storey counts. No automatic correction is authorized. Dimensioned sketches have not been evaluated by this derivation.

Eleven exception rows reuse completed aerial observations only when the original PID+BLDG_NUM **and full original source membership** match. Nineteen rows have historical reconstruction context. A shared parcel is explicitly labeled context only; it cannot accept an identity or prove current height. Exact existing form-correction aliases are distinguished from parcel context. Original historical observation limitations and unknown current conditions remain visible.

Coverage reports all 3,916 active parcel features, 3,216 active source groups and 3,849 corridor-classified parcel features. The official Main Street area falls within the extraction; only60.768% of neighborhood area does. Neither establishes parcel/building/sketch completeness. Full district sketch inventory, individual property/component checks, outside-extraction census and all-frontage independent reference verification remain unfinished. Two focused tests cover leading-zero/exact-feature preservation, source-membership-specific aerial reuse, nonpromotion, differing attribute meanings, changed join state and missing exact features. [Independent candidate C review](evidence/parcel-dispositions-review.json) passes this bounded offline work queue: 188 dependency hashes, exact replay, 801 policy-preserving rows and a failed-lineage injection. Full property/sketch verification and ticket acceptance remain open.

## First prioritized outlier: 1108 Edwards Lane

The original queue ties Building_0434 to parcel feature `ocpa:314028` (PIN `292223146500050`) by an accepted existing source/geometry association. Its source subarea maximum is two, the cached parcel `STYS` value is eleven, and the existing model already uses the two-floor estimate. [OCPA parcel metadata](https://ocpaimages.ocpafl.org/api/Content/GetContentDynamicFile?contentFileID=405230), PDF page 9, defines `STYS` as a single-precision story-count field; the definition does not supply a special decoding rule for eleven.

A separate [Stellar MLS archive distributed via Redfin](https://www.redfin.com/FL/Orlando/1108-Edwards-Ln-32804/home/46839670), record O5343138 listed January 30, 2015, describes the same street address as a two-story house, with bedrooms on the second floor. This is corroborating historical address context; the page does not expose the exact OCPA PIN, a dimensioned sketch or a current measured height. The finding supports retaining the existing two-floor estimate pending specific OCPA component/sketch and recent elevation evidence. It does not edit the cached eleven, accept a new relationship or verify present conditions. Checked November 3, 2026; not automatically applied to candidate C.
