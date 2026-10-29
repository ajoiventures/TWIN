# Native editor controls review

October 29, 2026 UTC, ticket #12. The separate `TWIN_CONTROLS_REVIEW` process opened the current composed scene with MainStreetOverview, readable daylight and an actual visible district. The owner's existing editor and Rhino sessions were untouched.

`TWIN_REVIEW_ONLY=1` selects the transient session as the edit target, disables the project's Save button and prevents both directions of the shared map-selection bridge. It is a review convenience, not a security boundary: the application's general File menu is not disabled. Do not use that menu to save source layers during review.

Native viewport selection of `/World/Roofs/Roof_2874` displayed 2201 EDGEWATER DR, its building entity and parcel, original source object IDs, a 5.14 m height, historical LiDAR evidence category and matching snapshot status. Unknown source fields remain explicitly unknown. [Actual native screenshot](evidence/native-roof-inspector.jpg).

The native Review button produced a same-snapshot change report. Apply correctly returned `no_local_changes`, but its human-readable message incorrectly claimed an update had been applied. The message now says no local changes and unchanged view. The native Undo button clearly reported that no applied refresh existed. This is no-change/unavailable-state verification, not acceptance of a changed-layer apply/undo cycle. The latest wording change is inspected in code and remains pending reload in a new native session.

Checkbox round trips were not established reliably in this session; no independent-switch acceptance is claimed. Further native checks remain: visibility/confidence round trips, changed-layer apply/undo/recovery, and optional dated-aerial inspector controls. Existing helper-level checks do not substitute for those interactions.

The review window was closed through Don't Save, and its process terminated. SHA256 checks confirmed the saved connected scene, manual edits, active dataset pointer and shared selection state stayed unchanged. Review-only sessions do not inherit the owner's unsaved in-memory work. The original editor remained running. Full #12 and its source/scenario dependencies remain open.
