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
