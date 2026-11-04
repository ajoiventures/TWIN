# Inactive church integration candidate

**Current status, November 2, 2026:** the separately reviewed historical sanctuary assembly is now locally composed and applied in the original Omniverse editor. The preparation sections below describe its earlier inactive candidate. Current conditions, whole-campus completeness and public derivative release remain unaccepted.

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

## Separate guarded application helper

`tools/activate_church_integration.py` provides the application mechanism. Running without arguments prepares ignored `church_integration_20261102_b/activation_plan.json` only. `validated_church(root)` returns a receipt dictionary, returns `None` only when both active layer and receipt are absent, and rejects incomplete pairs. Reserved destinations are `scene/church_historical.usda` and `data/processed/church_historical_activation.json`. Explicit `--apply` is required for adoption; it has not been executed in this delivery.

The helper pins the canonical package/site/producer, original source/mask reviews, packaging review, clean C frame-gate review and image/capture manifest. Critical diagnostic source/geometry/texture records are separated from unrelated captured district context. Python source dependencies are frozen into content-addressed local `activation_source_versions/` archives; changed/missing archives reject, while later working-helper changes do not invalidate unchanged reviewed geometry. The six affected legacy groups, source custom data, world transforms, geometry, heights, bindings and bound material definitions have a fixed semantic fingerprint. Manual model opinions use the existing camera-independent fingerprint.

The single sanctuary assembly has primary parcel_id and parcel_ids containing only 292214146005190 as dated sanctuary/photo context. Both source PIDs remain separately in source_parcel_context; the adjoining gym is not marked reconstructed. Components are dictionaries with stable id and prim_path. Physical building count is unknown, rendered entity count one, and current/raw-tax/public-release acceptance must explicitly remain false.

Application stages output files, backs up the current root and plan under timestamped data/backups/church_integration_*, inserts only the new layer immediately after manual, revalidates dependencies/manual/legacy, and refuses a concurrently changed root before atomically replacing it last. Ordinary pre-publication failures remove staged outputs. Multi-file publication is not globally atomic: root publication occurs last and incomplete pairs fail closed. No editor reload/save occurs. Root-owned dispatch, connection, refresh, confidence and registry integration remain separate.

Focused in-memory checks passed for a valid plan, both-absent optional behavior, and rejection of wrong schema, stale snapshot, layer SHA, current/tax/public promotion, legacy fingerprint, manual fingerprint, missing dependencies and whole-campus parcel-context promotion. No source mutation or application was used for these checks. Final prepared plan SHA256 is 96d0a3c1ef5faf6dec8cc90e89d5a2bea766c49f456734aabb85b98793070a91; helper SHA256 is 0f7832bf4134c939fc342b50beccfa0e8790994ab599f3ef99df51c40207eb1c. Independent preapplication review remains required.

## Local adoption and running editor — November 2, 2026

The [independent preapplication check](evidence/church-activation-code-review.json) passed before `python tools/activate_church_integration.py --apply`. Application preserved all root opinions except one additive `church_historical.usda` sublayer immediately after manual. Root SHA changed from `23a668244b25cbc8d32cc30fe1df3f0b0ba0715ff834b07a584d83c6a44433e9` to `6ff1ba0fe8afeda4bc990c511c86d3705824d1c7a3a9812114cfeec0464495ed`; the exact original root and plan are backed up under `data/backups/church_integration_20261102T162810786761Z`. The layer retains exact canonical bytes, including its candidate-origin metadata; current local adoption is established by root composition and the separate guarded receipt, not a rewritten source claim.

Independent [postapplication review](evidence/church-adoption-review.json) verifies seven protected non-root files, legacy identities/heights/materials, matching render attributes and exactly one sanctuary register entry. Reconstruction and corridor reports were rebuilt. The existing API returns the one sanctuary record with four components and false current/raw-link acceptance; it was not restarted. [Runtime API evidence](evidence/church-api-review.json).

The actual active-root capture `data/renders/20261102T163017Z/ChurchAssembly.png` passed [independent integrated visual review](evidence/church-integrated-render-review.json). It uses only the current project root and a copied fixed camera; no historical A/C proposal stack is nested into the deliverable. All 34 captured layers match. Masonry, entrance, belfry and spire are coherent, without the prior global road/wall artifacts. Plain roof/context masses, generic furnishings, side detail and existing-condition uncertainty remain visible limitations.

The original editor's **Review local scene updates → Apply reviewed scene update** controls then applied root and already-reviewed office changes in memory. MainStreetOverview and selected Building_2939 remained intact; source/manual/snapshot/selection bytes remain unchanged. No editor save/restart occurred. [Native receipt and screenshot hash](evidence/church-native-refresh.json); the screenshot and recovery payload remain private local evidence. One existing refresh/undo preservation regression passes. Future fresh workspaces include the church refresh allowlist and validate its canonical receipt when the church/root changes; the already-running editor used its existing loaded controls with the independently checked source package.

Rebuild order in `connect_scene.py` matches actual adoption. `register_reconstructions.py` exposes one historical sanctuary entity, with source parcel ambiguity retained separately. Tickets #6/#11 remain open for their broader height/terrain, complete architecture and verified pedestrian-block scope.

The refreshed [local scene profile](evidence/church-scene-validation.json) checks 17,876 meshes, 3,480 instance-proxy meshes, 37 layers and 23 external assets with zero errors. Its 3,216 building entities are frozen registry rows, not a newly certified physical-building census. Flat ground, collision/clearance and current-condition limitations remain explicit; this is not NVIDIA certification or conference-quality acceptance.
