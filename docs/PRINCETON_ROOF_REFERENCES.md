# Princeton completed-roof reference handoff

Status: completed-building architectural form evidence found and visually inspected; exact measured roof breaklines/elevations remain unresolved. No geometry, active layer, root composition or user editor was changed. This supports an explicitly interpreted candidate, not acceptance of a current measured roof.

## Identity and original sources

The operator identifies The Princeton at College Park at 646 W Smith Street, Orlando, consistent with project parcel 292214725701000. The original electrical contractor independently names the project and provides exterior, courtyard and oblique aerial photographs. Its textual description is 205 units / 5 stories / parking garage; this is a project description, not a measured per-component floor count and does not override OCPA's parcel STYS=6.

- [Operator](https://www.theprincetonatcollegepark.com/): retrieved 2026-10-29 UTC. Original HTML cached as `data/imagery/princeton_roof_references/operator.html`; its photo image IDs include the same 149596154 family as the contractor. Unit floor plans are representations, not roof/as-built plans.
- [Cable Electrical original project gallery](https://www.cableelectrical.com/project-type/wrap/): retrieved 2026-10-29 UTC; ten original-resolution project images downloaded, not thumbnails. HTML and per-file URL, retrieval time, SHA256, dimensions and unknown capture date are preserved in ignored `data/imagery/princeton_roof_references/receipts.json`.
- [Completed-building oblique aerial](https://www.cableelectrical.com/wp-content/uploads/2024/11/149596176.jpg): 1219 x 1259 pixels, local `contractor_149596176.jpg`, SHA256 `1bd09a2682ea1ee10b0b10dd17fb61a0ca4ebe6439e2d170f409398f8690f99f`. Actually viewed at full resolution, not inferred from the filename. The URL upload directory 2024/11 is **not** a capture date. Capture, flight, camera calibration, georeferencing, publication date and positional accuracy are unknown.
- [Corner exterior](https://www.cableelectrical.com/wp-content/uploads/2024/11/149596152.jpg) and [taller wing exterior](https://www.cableelectrical.com/wp-content/uploads/2024/11/149596154.jpg): actually inspected in the local ten-photo contact sheet. These corroborate completed facade/roof form and roof-level differences, not precise dimensions.

Reuse permission was not established. Keep original photos/HTML/PDFs/contact sheet ignored and local-review-only; no aerial/photo pixels, textures, derived photogrammetry or source-image redistribution are delivered. Documented visual observations do not assert a general modeling license.

## Actionable architectural correspondence

The oblique shows the triangular Princeton/Smith corner in the foreground, the broad pale parking/upper-wing roof behind it, and the adjacent curved road frontage. These landmarks permit qualitative correspondence with the cached January 2025 OCPA nadir review and existing parcel envelope; the photograph is not metrically registered.

| Visible completed form | Constraint on the next candidate | Still unknown |
| --- | --- | --- |
| Foreground corner has coherent dark pitched caps with intersecting ridges/hips, broad roof faces and visible small raised roof features | Treat roof faces as architectural patches; do not repeat nearest-cell facets or insert vertical fins at every point-label boundary | Exact ridge/valley coordinates, pitch, eave elevations and dimensions of small features |
| A long dark pitched perimeter wraps around lower white roof terraces; white terraces carry equipment | Separate sloping perimeter caps from lower flat service roofs. The prior unknown interface cannot automatically become a ground-reaching void or a wall up to the neighboring plane | Exact terrace levels, hidden drainage geometry and parapet height |
| Red pitched accent sections occur along one side and near the far/right connection | Keep them as distinct interpreted roof components if geographically corroborated; do not assign every red or dark image region an arbitrary elevation | Exact component registration and hidden slopes |
| Higher rear/garage roof is broad and comparatively flat, with perimeter enclosures/raised boxes | Preserve its separation from lower perimeter housing roofs; avoid applying a single hip/gable model to the entire tax parcel | Height/datum of garage deck, rooftop enclosures and concealed portions |
| Corner exterior and courtyard photographs show completed occupied-looking architecture and regular parapet/roof transitions | They refute a visually crumpled roof as the intended completed form; use only visible component topology, not invented hidden facade detail | Photograph capture dates and whether each detail already existed during the historical scan |

The photograph establishes form plausibility, not numerical agreement. A future candidate should explicitly label photograph-interpreted breaklines and source-fitted height anchors separately; retain unresolved hidden interfaces. Do not describe an interpreted join as a LiDAR-measured breakline.

## Historical scan versus completed references

The accepted original USGS project acquisition range is 2018-12-04 through 2019-04-12; exact local flight day and construction phase remain unknown. January 2025 OCPA imagery is a separately dated nadir reference, not a newer measured elevation source. Contractor photos show a completed form but cannot be assigned to January 2025 or to a particular year.

The City search index returns its *Current Plans and Projects List as of May 2019*, row590, with a January2019 near-completion comment. Direct retrieval of both indexed URL forms returned404 during this review. Treat that statement as an indexed lead, not a newly acquired primary-document page or proof that every roof was complete on the LiDAR flight day:
[City indexed appendix](https://www.orlando.gov/files/sharedassets/public/v/1/documents/city-and-district-plans/comprehensive-plan/growth-projections/appendix-k-current-plans-and-projects-list-2019.pdf).

## Plan search outcome and precise missing inputs

[City ordinance2014-47 amendment attachment59485](https://orlando.novusagenda.com/AgendaPublic/AttachmentViewer.ashx?AttachmentID=59485&ItemID=37298) was actually retrieved: eight physical pages, SHA256 `4514e5d8685a8f3534a572ec8328325bd99f093241fa29cb8ad9f7a783dc9415`. It is proposed ordinance text with references to a Development Plan/Exhibit C; the retrieved eight pages contain no roof plan or architectural elevation sheets. It cannot be substituted for the missing exhibit or for completed as-built drawings. The associated [City cover sheet](https://orlando.novusagenda.com/AgendaPublic/CoverSheet.aspx?ItemID=37298) actually returns "This Agenda is not available." No attachment enumeration was possible there.

Bounded searches for the exact property, City ZON2014-00013, original architect/developer and roof plans did not retrieve a usable as-built roof plan or a newer measured elevation source. Exclude similarly named Princeton projects in Miami-Dade and the nearby Princeton hotel; neither is this parcel.

The remaining acceptance input is a dimensioned completed roof plan and elevations (including ridge/valley breaklines, parapets, roof terraces and a stated vertical datum), or a suitably licensed newer measured point cloud with actual acquisition metadata. The blocked historical interfaces are localized in `data/heights/princeton/architectural_regions/seam_conflicts.geojson` and summarized by `docs/evidence/princeton-roof-interface-constraints.json`. Existing class6 support can anchor measured historical patches, but conflicting/unsupported interfaces must remain explicit until the missing input or an honestly estimated interpretation is reviewed.

## Delivery and next bounded action

The useful delivery is the original-resolution completed oblique plus nine corroborating original photographs, source receipts and the component constraints above. Next geometry work can use these observations to propose a few coherent perimeter caps and lower terraces, preserving source-supported height anchors and clearly marking estimated connections. No automatic slope extrapolation, photogrammetric measurement, current-state claim or activation is authorized by this reference packet alone. The rejected roof remains rejected; no new render or acceptance claim was made.

Integrator review: independently opened the original oblique and confirmed the dark intersecting perimeter caps, white service terraces, red accent roofs and higher rear enclosure. This supports the documented form constraints; it does not resolve dimensional registration or capture date.


## Separate interpreted geometry candidate (2026-10-29 UTC)

`tools/princeton_interpreted_roofs.py` now implements a **separate, inactive interpreted candidate**, not a measured current roof. It reuses the frozen historical support arrays/cloud, completed contractor oblique and existing source-derived eastern envelope. Ten broad architectural caps and a common lower terrace replace nearest-cell plane labels. Each hip is an analytical minimum of sloping faces; intersections between caps and terrace use analytical maximum envelopes, creating continuous joins rather than vertical interface fins. Four additional estimated extent planes per cap bound extrapolation to its documented source-context search window. Their 0.75 slope, component dimensions, opposite faces and joins are explicit estimates, not source-measured breaklines. Per-face region/plane/quality mapping is in the manifest.

The source grid's small roof holes were investigated against actual cached returns: 45 of52 enclosed gaps, totaling203.000m², have at least10 class6 returns at or above terrace-minus0.5m and at least90% of all returns at that upper level. Their continuous roof surface is an explicitly interpreted correction; class1 returns remain unclassified, not promoted to roof. Seven ambiguous holes remain. Protected courtyard overlap is zero. This repairs roof-supported voids, not parcel-envelope extrusion. Outer envelope simplification is1m, with15mm erosion/10mm dilation to remove source-grid point contacts; footprint/symmetric-difference metrics and each hole's evidence are retained. The real courtyard/open interior is preserved.

Actual generated result:60 analytical regions,1276 meshfaces. Reopened serialized USD has subdivision `none` and passes edge-incidence closure with zero boundary, nonmanifold, orientation-conflict or collapsed edges. Internal vertical interface-wall area is0m². These checks do not establish architectural correctness or self-intersection freedom. Source comparison over69,290 class6 returns has absolute residual p50/p95/max **0.125/1.659/4.195m**. The common terrace omits equipment/individual level differences, and curved/corner caps have uncertain dimensions; this is **not an accuracy acceptance result**. Strong square/front cap support fits more closely, while missing/partial opposite faces are explicitly estimated. The CPU diagnostic was actually inspected, not treated as a Kit proof.

Reproduce from the project root using the configured Python runtime:

```powershell
& '<configured-python.exe>' tools/princeton_interpreted_roofs.py
```

The helper caps numerical workers at1, performs no network acquisition, checks cloud/support/snapshot/photo identity and records dependency hashes. Outputs are ignored proposal/review USD layers plus `data/heights/princeton/interpreted_roof/{manifest.json,regions.json,regions.svg,cpu_roof.png}`. No active/root/model source is overwritten. Recovery consists of leaving the proposal uncomposed; no active rollback is needed. Rebuilding changes timestamped manifest bytes, so use its new SHA for each review.

Frozen handoff:

- Proposal: `scene/princeton_interpreted_roof_proposal.usda`, SHA256 `6f5f5eccb31c4fc880cf92e7cbd6cccabc712b511fc510dc442ac870d4b6073b`.
- Manifest: `data/heights/princeton/interpreted_roof/manifest.json`, SHA256 `34f28b28a01f6641e5c6145ef3c149c5ff4a32ea97b8faedac8e0ba3359a1983`.
- Matched scenes: `scene/princeton_interpreted_roof_baseline_review.usda` and `scene/princeton_interpreted_roof_proposal_review.usda`; camera `/World/Cameras/PrincetonInterpretedRoofEvidence`. Both share the same camera, inherited district lights and neutral review colors. The baseline retains the old mesh; only the proposal hides it and supplies the new eastern mesh. West/middle masses are unchanged.

Actual reopened review scenes resolve successfully; all recorded dependencies match. Source acquisition remains2018-12-04 through2019-04-12; completed photo capture remains unknown. No GPU render, active composition, current-state certification or ticket closure occurred in this geometry handoff. The integrator must inspect the actual matched render before any acceptance/activation.

## Actual matched render decision

The subsequent 1920x1080 Kit captures were inspected by the integrator and an independent visual reviewer: [baseline](evidence/princeton-interpreted-baseline.png) and [interpreted candidate](evidence/princeton-interpreted-proposal.png). The candidate removes fine pits and microterraces, but compound triangular joins and cap transitions remain architecturally implausible. The unchanged west/middle walls retain severe scan corrugations. Activation and architectural acceptance are rejected.

Composed USD inspection confirms subdivision is off, one uniform normal exists per face, and faces are planar. The rounded impression comes from the piecewise geometry and lighting; changing normals alone will not produce the missing architectural hierarchy. Next correction requires coherent component outlines, terraces, roof-level transitions and a clean wall/roof relationship rather than further numerical fit optimization alone. [Independent render and geometry evidence](evidence/princeton-interpreted-roof-visual-review.json). The source scene remains unchanged.
