# Existing-condition review pilot

The first bounded review area is Edgewater Drive from W Princeton Street to the **southern** W Smith Street junction. City centerline geometry has two staggered Smith intersections; the southern endpoint is explicitly selected. This is a working modeling choice within the authorized Edgewater scope, not an official district or surveyed construction limit.

`python tools/define_pilot.py` derives endpoints from the active City street snapshot and records exact coordinates, source IDs, source snapshot and baseline date. The October 28, 2026 extraction uses centerline object 4285 and is approximately 85.44 m long. A 60 m context buffer selects adjacent parcel context; it is **not** a road width, right-of-way, sidewalk edge or accessibility standard.

The initial context links 21 building groups: 20 ID-and-geometry matches and one spatial-only review case. Context can include properties beyond immediate storefront frontage. The model review baseline date does not assert that historical source geometry depicts current field conditions.

Local definition: `data/processed/pilot.json`. API: `/api/v1/pilot`, rejecting stale snapshot associations. This unblocks consistent aerial/records review and baseline comparison. Accepted curb/sidewalk geometry, widths, grades, parking and final field conditions still require evidence under #16/#17/#20/#25.
