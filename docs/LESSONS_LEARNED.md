# TWIN lessons learned

Seeded October 29, 2026 UTC from observed project work. These entries are evidence-bound workflow lessons, not model training. Use the [lesson template](templates/LESSON_RECORD.md) for new entries and [protocol](protocols/LEARNING_AND_SCRIPT_CREATION.md) for adoption.

| ID / status | Observed result and evidence | Adopted action and limit |
|---|---|---|
| L-001 · Adopted | Candidate lineage for all 3,216 buildings matched every existing frozen field. [Replay and preservation evidence](evidence/building-lineage-acceptance.json). | Publish additive lineage in an immutable derived packet; retain active snapshot/entity IDs. This does not authorize changed joins, geometry or the separate parcel-exclusion policy. Implemented in `tools/build_building_lineage.py`. |
| L-002 · Adopted | Full source-footprint intersection found Wellesley omitted from the frozen parcel-linked aerial queue. [Aerial review](PILOT_AERIAL_REVIEW.md). | Check the physical source-context census independently of parcel joins; preserve supplemental and out-of-frame cases. A complete queue is not automatically a complete physical-building census. |
| L-003 · Adopted | API data and image files were valid, but the browser showed a placeholder for the SVG image. Normal image plus SVG overlay displayed the actual photos. [Acceptance](evidence/pilot-aerial-review-acceptance.json). | Inspect actual pixels after UI changes; the local fix is in `web/aerial-review.html`. Do not generalize this observed display issue to every browser or claim API status proves visual success. |
| L-004 · Adopted | Native picking exposed an integer-to-`omni.ui.Label.height` error and roof/body identity gap despite function-level checks. [Native evidence](evidence/workspace-native-controls.json). | Use the appropriate UI dimension type; resolve a roof to its exact current paired building. Keep native control acceptance open until exercised; unit checks do not certify button behavior. |
| L-005 · Adopted | The isolated reviewer became the user's active window with unsaved camera opinions. [Native evidence](evidence/workspace-native-controls.json). | Re-observe ownership/use before toggling, restarting or saving; preserve unsaved work. Use map-only inspection where suitable. A process started by an agent is not permanently disposable. |
| L-006 · Adopted | Source-membership reconciliation found 73 raw subareas outside modeled membership, including partial and wholly unrepresented groups. [Lineage evidence](evidence/building-lineage-acceptance.json). | Publish an orphan review queue; do not automatically attach or extrude them. These records are not confirmed missing physical buildings. |
| L-007 · Adopted | Optional scene composition changed dependency hashes and made earlier reconstruction/corridor ledgers stale. [Execution checkpoints](EXECUTION_STATUS.md). | Rebuild affected derived ledgers after accepted composition changes; bind unrelated metadata separately when possible. Successful source ingestion alone does not prove downstream freshness. |

For each future lesson, record the actual trigger, evidence, owner role, review result and adoption path. Supersede an entry explicitly when its assumptions or implementation change. Do not accumulate repetitive status notes as lessons.

## Initial record ownership

Curated by the root integrator from linked implementation and acceptance records. Responsible roles: L-001/L-002/L-006 GIS Data Lead; L-003 Web UI Lead; L-004/L-005 Editor Integration Lead; L-007 Delivery Integrator. Initial protocol review is recorded in the execution checkpoint; linked technical evidence retains its own original reviewers. The protocol review does not re-certify every underlying implementation.


| Lesson | Responsible role | Concrete adoption location |
|---|---|---|
| L-001 | GIS Data Lead | `tools/build_building_lineage.py`; `docs/BUILDING_LINEAGE.md` |
| L-002 | GIS Data Lead | `tools/complete_pilot_aerial_review.py`; `docs/PILOT_AERIAL_REVIEW.md` |
| L-003 | Web UI Lead | `web/aerial-review.html` |
| L-004 | Editor Integration Lead | `tools/open_workspace.py`, `tools/workspace_evidence.py`, `tools/selection_bridge.py` |
| L-005 | Editor Integration Lead | `AGENTS.md`; map-only checkbox in `web/index.html` |
| L-006 | GIS Data Lead | `tools/build_building_lineage.py` orphan queue |
| L-007 | Delivery Integrator | `tools/register_reconstructions.py`, `tools/review_corridor_buildings.py`, source guards in `tools/serve.py` |

All seven seed records use the date above, have no superseding record, and share the independent protocol review by the VP review agent on October 29, 2026 UTC. That review checked the lessons' scope, references and adoption clarity; technical findings and their original reviewers remain in each linked evidence record. Future records use the full template rather than relying on this shared seed metadata.

## L-008: Source-fit and mesh closure do not establish architectural quality

Date: October 29, 2026 UTC. Status: verified observation; replacement method remains candidate. Owner: 3D Reconstruction Lead. Independent reviewer: VP review agent acting as visual QA. Supersession: none.

Actual matched renders of Princeton showed new triangular pits, fins and microterraces despite passing support, plane-fit and shell checks. [Images and findings](PRINCETON_ROOF_REVIEW.md) preserve the rejected layer and rendering conditions. The builder attributes the artifacts to nearest-support grid assignment and artificial height-order switches; the replacement region method still needs its own evidence and render.

Decision: reject activation, preserve the current source scene, and inspect source-supported connected regions/shared boundaries before another full render. This applies to roof reconstruction with discontinuous regional fits; it is not permission to fabricate missing architectural detail. Adoption location: `docs/PRINCETON_ROOF_REVIEW.md` correction gate. No claim that the pending replacement is verified.

## L-009: Government use codes and inventory membership are separate evidence

Date: October 29, 2026 UTC. Status: adopted. Owner: GIS Data Lead. Reviewer: independent VP technical QA agent, [population and geometry review](evidence/public-ownership-review.json). Supersession: none.

Trigger: the full-neighborhood City vacant-lot inventory matched five parcels, including one whose OCPA use code is `0001`; the prior partial extraction missed all five. A County building inventory also disagrees with one parcel's municipal assessment class. The GIS exemption namespace could not be established as the public numeric exemption dictionary.

Decision: reconcile exact publisher parcel IDs against the full required boundary, retain assessment classification and official inventory membership as distinct observations, and expose conflicting agency references. Never translate an unestablished code namespace or classify unlabelled parcels as privately owned. Legal title, current vacancy and public access remain separate unverified questions.

Verification and adoption: independent replay reconciled 5,732 source features and 93 combined references; `tools/public_ownership.py` preserves unknowns, exact code definitions and conflict records. The method applies to reference screening, not a comprehensive deed/title register. [Contract and limitations](PUBLIC_OWNERSHIP.md).


## L-010: Render wrappers must preserve physical stage metadata

Date: October 30, 2026. Status: adopted. Owner: 3D Delivery Integrator. Independent reviewer: GIS analyst, [setup and actual-image review](evidence/office-frontage-review.json). Supersession: earlier integrated-render project-quality diagnosis is superseded by the corrected setup.

Temporary USD review wrappers omitted stage-level units and orientation, defaulting to Y-up and 0.01 metres/unit while the actual project is Z-up and 1 metre/unit. The earlier full-scene capture showed severe brick striping and black road bands. Exact old wrapper bytes are archived by their original capture hashes. The corrected actual comparison keeps camera, source geometry, materials and lighting layers unchanged; only the common wrapper layer hash differs, and both artifacts disappear. [Evidence](evidence/render-stage-correction.json).

Decision and adoption: `create_review_stage` in `tools/workspace_evidence.py` requires explicit units/orientation, copies stage metadata to a transient root and composes proposal overrides before attachment. `tools/render_review.py` uses it and records stage settings on future captures. Twenty focused checks cover metadata preservation, precomposed overrides, missing authoring and existing controls. This establishes a repeatable review setup; it does not certify the remaining building geometry, street accuracy, assets or professional presentation.

## L-011: Wait for viewport frames before scheduling a review capture

Date: November 2, 2026. Status: adopted bounded capture guard. Owner: Rendering Lead. Independent reviewers: GIS analyst for installed SDK semantics; visual QA for the controlled actual-image comparison. Supersession: none; L-010's physical-stage requirements still apply.

The installed NVIDIA `Capture.wait_for_result(completion_frames=60)` awaits the capture future before advancing 60 application updates. It never supplies 60 rendered frames before capture. The viewport utility's explicit `next_viewport_frame_async(viewport, n_frames=60)` instead counts matching viewport NEW_FRAME events. [Versioned SDK references and line findings](evidence/viewport-capture-sdk-review.json); no proprietary source text is republished.

The old and new Church C images use identical layer hashes, camera and physical metadata. The new capture, with the explicit pre-capture frame gate, has clean roads and walls where the old image had global bands and waviness. [Independent controlled comparison](evidence/church-frame-gate-review.json). This supports a timing/readiness explanation for this observed defect; a single comparison does not establish its unique cause or guarantee shader/PSO convergence.

Adoption: `tools/render_review.py` counts 60 viewport frames with a bounded timeout before scheduling capture, records the pre-capture frame count separately from post-capture application updates, and retains image-completion/source-preservation checks. A timeout is a failed observation, not permission to restart the owner's editor. No global material-ready API was verified; do not invent one or label an image fully converged from frame counts alone. The old October 30–November 2 wall-clock interval is not a performance measurement.

## November 2 follow-up to L-002 and L-008

L-002's full-source census rule applies to campus aliases too. Restricting the church analysis to two groups/ten subareas incorrectly suggested a missing footprint. [Independent full census](evidence/church-wing-census-replay.json) reconciles all 18 raw features across six aliases and identifies existing Building2892 as the underheight wing. Search all source memberships and spatial candidates before declaring a physical omission; preserve raw IDs and assigned/unaccepted parcel contexts separately. The corrected [wing workflow](CHURCH_WING_REVIEW.md) binds that complete census before preparing masks.

L-008 was reproduced by cutting lower LiDAR returns into an upper roof without establishing that they represented openings. The actual image had triangular pits and transition fins despite tiny plane/projection residuals. [Rejected image review](evidence/church-wing-fullroof-review.json). Cross-date aerials and multiple-height evidence did not support exclusive upper-roof cutouts; the corrected continuous form removes them and records lower returns separately. [Corrected review](evidence/church-wing-continuous-review.json). Adopt source semantics and supported interfaces before joining surfaces; class 6 and a planar normal alone are insufficient.

Likewise, the [car QEM review](evidence/vehicle-qem-review.json) rejects new seam/reflection defects despite sampled 2 mm geometric checks. Open-border preservation is not material-join or shading-field preservation. The revised helper retains appearance-critical parts and captures producer bytes at build start; strict trials' negligible reduction is recorded rather than promoted as a performance success. These follow-ups extend the existing lessons, not a claim of automatic model learning.

## November 2 follow-up to L-011: bind the captured frame to its camera

A five-camera batch produced identical PNG bytes for two different camera poses. The installed viewport camera-path getter returns a requested/cached path; viewport NEW_FRAME events alone do not identify which camera delivered those pixels. The capture delegate exposes the actual frame's view matrix. [Independent SDK and two-camera image review](evidence/viewport-camera-switch-review.json).

`tools/render_review.py` now requires 60 consecutive advancing delivered frames matching the requested view, checks the actual capture delegate's view again, records frame number/view/projection/handle, rejects nonfinite or mismatched matrices, and rejects identical PNGs from different poses. The controlled switch produces distinct actual views with numerical view-matrix errors below 0.000000000001. This binds camera pose, not shader convergence or scene quality; a camera named TreeLinedEdgewater actually framed a generic awning close-up. Review the pixels as well as their provenance. Original failed captures remain preserved locally.

## L-012: Reuse the producer's semantic validator for derived consumers

Date: November 3, 2026. Status: adopted for the footprint and parcel-disposition consumers. Owner: GIS Data Engineer. Independent reviewers: footprint_review and parcel_review.

Both consumers initially checked a lineage pointer, receipt and direct dependency hashes without proving the registry/base geometry still matched the lineage producer's semantic fingerprints. A receipt establishes packet integrity; it does not establish that every source contract still holds. Independent review caught both gaps before publication. [Footprint evidence](evidence/map-footprints-review.json) and [disposition C evidence](evidence/parcel-dispositions-review.json) verify reuse of `build_building_lineage.validate`, plus rejection when that shared validation fails. Retain consumer-specific scope and hash checks alongside the shared validator. This guards source identity, not physical currentness or survey accuracy.
