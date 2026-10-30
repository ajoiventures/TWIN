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
