# Native editor controls review

October 29, 2026 UTC, ticket #12. The separate `TWIN_CONTROLS_REVIEW` process opened the current composed scene with MainStreetOverview, readable daylight and an actual visible district. The owner's existing editor and Rhino sessions were untouched.

`TWIN_REVIEW_ONLY=1` selects the transient session as the edit target, disables the project's Save button and prevents both directions of the shared map-selection bridge. It is a review convenience, not a security boundary: the application's general File menu is not disabled. Do not use that menu to save source layers during review.

Native viewport selection of `/World/Roofs/Roof_2874` displayed 2201 EDGEWATER DR, its building entity and parcel, original source object IDs, a 5.14 m height, historical LiDAR evidence category and matching snapshot status. Unknown source fields remain explicitly unknown. [Actual native screenshot](evidence/native-roof-inspector.jpg).

The native Review button produced a same-snapshot change report. Apply correctly returned `no_local_changes`, but its human-readable message incorrectly claimed an update had been applied. The message now says no local changes and unchanged view. The native Undo button clearly reported that no applied refresh existed. This is no-change/unavailable-state verification, not acceptance of a changed-layer apply/undo cycle. The subsequent review below verifies the corrected wording in a new native session.

Checkbox round trips were not established reliably in this session; no independent-switch acceptance is claimed. Further native checks remain: visibility/confidence round trips, changed-layer apply/undo/recovery, and optional dated-aerial inspector controls. Existing helper-level checks do not substitute for those interactions.

The review window was closed through Don't Save, and its process terminated. SHA256 checks confirmed the saved connected scene, manual edits, active dataset pointer and shared selection state stayed unchanged. Review-only sessions do not inherit the owner's unsaved in-memory work. The original editor remained running. Full #12 and its source/scenario dependencies remain open.

## Follow-up: usable labels and actual round trips

The separate `TWIN_CONTROLS_REVIEW2` session loaded the updated controls. Readable row labels now toggle the same model as their small checkboxes. Actual native interactions verified trees, parked vehicles and storefronts independently disappearing and returning. With evidence filtering enabled, disabling Illustrative removed these details while retaining source building masses; disabling the master restored them. [Restored native view](evidence/native-controls-restored.jpg). This does not establish every category or restoration of an intentionally hidden independent layer.

The same session verified the corrected no-change message after Review and Apply. Future scenarios were explicitly unavailable. Evidence filtering briefly stalled native observations for several seconds before completing; this remains a responsiveness issue, not a failed or restarted session.

The review window closed normally using Don't Save. The connected scene, manual layer, active pointer and shared selection file match their pre-review SHA256 values. The machine-readable evidence records exact hashes. Changed-layer native recovery, remaining switches and optional aerial inspection still keep #12 open.


## Follow-up: independent boundaries, faster filters and durable recovery

Actual review found a hidden `/World/StudyBoundaries` parent preventing Main Street from appearing despite its checked switch. `normalize_boundary_switches` now transfers that initial hidden state to the two child boundaries in the session before building controls. Both remain initially hidden; enabling Main Street leaves the neighborhood hidden. Source layers and other ancestor visibility remain untouched. This was verified in the native viewer.

The confidence helper now classifies each target once and batches Sdf-only edits after composed-stage queries. Actual-scene CPU timings improved from 1.58/1.54 seconds to 0.89/0.79 seconds for illustrative hide/reset; 6,250 estimated groups improved from 1.62/1.51 to 0.85/0.79 seconds. These are helper timings, not viewport FPS. Sixteen focused checks include exact restoration of animated visibility and metadata. Native checks filtered illustrative, estimated, historical LiDAR and unknown content; master-off restored content while independently hidden trees stayed hidden. Empty observed/proposed/stale groups are not claimed as populated visual cases.

An isolated copy of the actual 19,959-prim scene tested only a copied boundary layer update. Native Review listed that sole file; Apply changed yellow to cyan; Undo restored yellow. After closing without saving, a fresh process loaded cyan from disk; native Recover restored yellow from the saved receipt. The candidate file stayed unchanged. This proves local completed-layer adoption/recovery, not agency snapshot generation. The temporary observer initially had a path serialization defect; it was corrected before the fresh-process recovery observations, and no failed observer output is used as proof.

All three owned reviewer processes closed normally without saving. All 60 original scene files plus the active pointer and shared selection file remained unchanged (62 physical files; duplicate path spellings removed). Original owner editor process57516 remained running; Rhino was untouched. [Recovery and preservation evidence](evidence/native-refresh-recovery.json), [Apply](evidence/native-refresh-applied.jpg), [Undo](evidence/native-refresh-undone.jpg), [fresh-process recovery](evidence/native-refresh-recovered.jpg).

Independent PM review accepted the bounded static-scene control/recovery evidence. The remaining concrete ticket12 gate is startup failure handling: a present root with missing required dependencies must show a retry error rather than successfully attach a partial/blank stage. This is under implementation; no whole-ticket closure yet.


## Startup recovery verified

The startup preflight rejects incomplete composition, missing loaded assets and scenes without useful visible geometry before attaching a candidate to the editor. Dormant variants and deliberately unloaded payloads are excluded. The actual complete scene passes; 18 focused checks cover failure and preservation behavior.

An isolated native session showed explicit errors for a missing required base layer and a missing dataset manifest. After restoring those copied inputs, the scene opened at MainStreetOverview. The fixture also lacked its active snapshot pointer, which produced a separate explicit error; restoring the copied pointer and fixture directory allowed Retry to finish with the full controls visible. This is local startup recovery, not source ingestion. The review closed with Don't Save; its process is absent and the original editor remains running. All 62 protected physical files remain unchanged.

[Missing asset](evidence/native-startup-missing-asset.jpg), [missing dataset](evidence/native-startup-missing-dataset.jpg), [restored native scene](evidence/native-startup-restored.jpg). The existing source-outage check separately verifies that failed refresh preserves the active snapshot pointer. Complete-ticket acceptance is recorded in the independent review matrix when finalized; visual production quality remains outside this controls acceptance.

Independent final review passed all five original acceptance criteria and three government controls: [ticket 12 acceptance matrix](evidence/native-ticket12-review.json). This accepts editor controls and recovery, not architectural realism, survey accuracy or the full project.
