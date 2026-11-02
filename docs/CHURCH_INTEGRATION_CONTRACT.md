# Inactive church integration candidate

`tools/prepare_church_integration.py` packages the reviewed C church contributors into a separate local-only candidate. It does not activate, acquire data, rewrite the project root, refresh the editor, change the registry or touch an API. This advances the historical main sanctuary assembly; it does not complete tickets #6 or #11 or establish current/whole-campus accuracy.

## Inputs and run

The fixed source is snapshot `20261028T160543372334Z` and the exact November 2 clean C capture manifest (`d5fbe7d871994110b74b4efd3c4d5d218ee128b28dbbeb5e75a7f9f1aba962c3`). Each of the five input layers must match that capture's layer hashes. Existing source manifests provide checked dependency closure, including the original historical point cloud and dated OCPA photograph. No new downloads occur.

From `C:/Projects/TWIN`, with the existing Python runtime and `.dependencies`:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
& 'C:/Users/ajoiv/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/prepare_church_integration.py --output data/diagnostics/church_integration_replay_new
```

The destination must be a fresh directory under ignored `data/diagnostics`. Existing outputs are refused. A failed pre-publication check leaves project sources untouched. An exported candidate failing a later check must remain unaccepted; use a fresh output directory after resolving the cause. No rollback of the active scene is necessary because preparation never changes it.

## Exact package

The output `site.usda` has Z-up/meters and no sublayers. It contains:

- `/World/Landmarks/ChurchOnDriveSanctuaryCandidateV3`
- `/World/Landmarks/ChurchOnDriveSteepleCandidate`
- `/World/ChurchFrontageAppearance`
- `/World/ChurchBelfryAppearance`
- The exact original-surface remainder overrides at `/World/Buildings/Building_3065` and `/World/Roofs/Roof_3065`.
- Visibility-only suppression of the unrelated illustrative `/World/Storefronts/Building_2919` and `/World/Storefronts/Building_3065`.
- Required external bound material subtrees and locally resolved original TWIN texture assets.

It excludes old A contributors, full scene/root composition, cameras, lights and already adopted paving. Building 2919 source body and roof remain untouched. The 3065 override retains the original surface outside the replacement envelope, not an invented parcel extrusion or closed solid. Existing source identities and ambiguous spatial links inherit from the original source; the new layer does not claim accepted physical/tax identity.

The four reconstruction/appearance roots carry inherited source URL, publishers, snapshot, historical project acquisition range, separate photo date, NAVD88/meter scope, stable component identifier and explicit current/raw-tax-link/public-release false flags. Acquisition dates refer to the USGS project range, not a known local flight. The OCPA photograph visibly dates November 8, 2021; its pixels are not embedded in materials or published. Belfry proportions/louvers and facade dimensions remain photo estimates. The spire apex is the highest observed return proxy, not a surveyed physical tip.

## Verification and canonical recipe

Preparation compares all authored attribute values (normalizing resolved texture paths), relationship targets and world transforms for every descendant under the four reconstruction roots, both legacy remainder roots and untouched Building/Roof 2919 against composed C. Visibility suppressions are checked explicitly. The comparison occurs before adding provenance metadata. The root/manual, office, post-office, paving and active snapshot files are byte-hashed before and after, and must remain identical.

`manifest.json` records those comparisons, protected-file hashes, source dependencies, output SHA and limits. `captured_helper.py` freezes the exact producing script and its hash; later working-helper changes should not invalidate the reviewed frozen artifact. Texture files and source-manifest dependencies are checked and hashed. Full root/manual byte hashes are preservation evidence, not canonical immutable recipe dependencies; future adoption should use the recorded camera-independent manual-model fingerprint. The C review wrapper is review evidence only and is not composed by the output. Its capture references other unrelated layers; those are not promoted into this package.

OpenUSD may warn while reading the full review composition about unknown Kit-only `no_delete`/`hide_in_stage_window` fields. They are not geometry/material attributes; every compared render attribute still must match. This CPU check is not independent review or a new rendered-image acceptance.

Actual run: `data/diagnostics/church_integration_20261102_b` completed with 1,980 matching composed attributes and matching world transforms, 77 meshes, zero cameras, no sublayers and 66 hashed source dependencies. The six protected files were byte-identical. `site.usda` SHA256 is `55388928a2750ed22e739ef9fad2c5137835a60335a3abe45ab08cc1c50e3fbc`; manifest SHA256 is `14e13bfce1f39555a9768c47d66bff4514be237cf44ab290a9089acce2ba8af4`; frozen producer SHA256 is `b32b031c1156ad9632476558bd6423999f488ff42073185384379c96e30bbbcf`. No new GPU capture was run.

## Remaining application gate

Independent [package review](evidence/church-integration-package-review.json) accepts this inactive preparation and binds the clean C view: 2,064 composed attributes, 167 relationships and 84 world transforms match; 11 additional copied-material attributes match. All 66 dependencies and six protected files match, with no off-whitelist prims or embedded cameras/lights/sublayers. This checks the candidate, not scene application or native runtime behavior.

Production validation should distinguish critical source/material/geometry dependencies from the broader historical comparison context. The original mask recipe records unrelated scene/tree/car layers as context; do not freeze those as eternal prerequisites for unchanged church geometry. Freeze producing script versions by archive and exact hashes, as for accepted paving, so a later working-helper edit does not invalidate an unchanged reviewed artifact. Neither relaxation permits changed sanctuary geometry, material textures, source identity, manual model opinions or snapshot to bypass review.

Root must independently inspect the package and bind the latest clean C visual review before any adoption. Extend the existing accepted-layer mechanism with a church-specific canonical recipe/schema/output contract; the paving-specific implementation cannot validate church via a config entry alone. Application must preserve all manual/root opinions and existing office/post/paving layers, insert only this separate layer, and validate source identity, required hashes, source snapshot, local-only/current-false policies and manual-model fingerprint before writing. Add the distinct layer to guarded refresh. The inspector now supports inherited top-level publisher/source URL and the two appearance roots enter confidence filters; photograph date and project acquisition interval retain separate labels. Six existing targeted inspector/filter checks and actual candidate inspection pass. Native editor refresh/application has not been exercised for this package. Keep a single bounded sanctuary assembly record with no accepted tax links, no asserted physical-building count and no whole-campus/current claim. No application code or activation is delivered by this preparer.
