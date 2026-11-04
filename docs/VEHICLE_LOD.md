# Vehicle source-detail culling candidates

## Compact SUV material batching

The local `data/diagnostics/vehicle_body_style_sources/compact_suv_material_batches.usda` groups the SUV's 435 meshes into 12 material batches. It retains all 126,758 triangles and all 12 color textures. Reopened USD matches the assembled vertex positions, normalized transformed normals, UVs, indices and material targets. The original separately addressable wheel and body prims remain available in the unbatched source for fit and inspection. Actual render comparison and performance measurement are still required. [Batch audit](evidence/suv-material-batch-audit.json)

## Saved-scene parking clearance screen

The [west lot plan comparison](evidence/west-stall-vehicle-plan.svg) shows all seven January 2025 stall traces and the car, SUV and van hulls extracted from their actual composed USD meshes. The drawing uses equal XY scale and no aerial pixels. It is a plan-clearance review and does not show materials, shadows, doors opening or vehicle movement.

The local `data/diagnostics/vehicle_placement_audit/west_stall_two_vehicle_terrain_preview.usda` places the car and van together on the LiDAR-derived parking preview. Direct interpolation on the reopened pavement triangles gives van tire gaps of 0, 2.37, 3.50 and 10.64 mm after a rigid vertical lift. The van retains 0.231 m minimum plan clearance to the stall trace and 8.316 m separation from the car. This is a static mesh fit. Actual grade, door swing, circulation and rendered contact remain open. [Terrain fit receipt](evidence/west-stall-van-terrain-fit.json)

The [CC0 Innerscene delivery van](https://www.innerscene.com/tools/library/3d-parts/delivery-van-131990b3) was tested at original scale across all seven west stall traces. It fits each polygon at its centered pose but has only 8 mm plan clearance in stall 5. The local two-vehicle preview `data/diagnostics/vehicle_placement_audit/west_stall_van_preview.usda` uses stall 7, with 0.231 m clearance to its trace and 8.316 m plan separation from the car in stall 3. Reopened USD confirms both hulls fit their own stalls and both lowest mesh vertices meet the flat modeled paving. The 0.12 m selection margin is a modeling criterion. Door swing, vehicle maneuvering, actual parking restrictions, terrain wheel contact for the van, and rendered appearance remain open.

The separate terrain comparison `data/diagnostics/vehicle_placement_audit/west_stall_vehicle_terrain_preview.usda` retains the west stall 3 car's XY and yaw and raises it 1.053922 m onto the LiDAR-derived flush-parking preview. Four sampled tire patches have estimated residual gaps of 0.00, 7.12, 10.42 and 0.38 mm after the vertical lift. A plane fit leaves 8.65 mm peak-to-peak residual at the sampled contacts, so the preview uses the simpler rigid vertical adjustment. Reopening the USD verified the translation. This uses historical modeled terrain and the saved parking offset. Tire deformation, surveyed grade, clearance for opening doors and rendered contact shadows remain unverified.

The local `data/diagnostics/vehicle_placement_audit/west_stall_vehicle_preview.usda` places one mid-detail Khronos CarConcept in traced west stall 3 at original asset scale. The reopened mesh hull is entirely within the stall and one modeled rear pavement mesh, with 0.133 m minimum plan clearance to the traced edges. The 4.357 × 2.542 × 1.149 m asset was aligned to the visible striping. Its lowest vertex coincides with the flat modeled pavement. This check does not establish four-wheel contact on measured terrain, usable door clearance, current occupancy, or accessible-route compliance. The asset retains CC BY 4.0 attribution to ©2024 Darmstadt Graphics Group GmbH, model and textures by Eric Chadwick, with the benchmark modifications documented in [the asset notes](CAR_CONCEPT_BENCHMARK.md).

Seven adjacent stalls in the west rear lot were traced between clearly visible January 2025 divider stripes. Traced widths range from 2.50 to 2.94 m. The visible row spans 7.98 m between traced ends, which describes the image interpretation rather than a legal stall depth. All seven traced polygons are covered by the combined modeled rear paving and service aisles to four decimal places of the area fraction. The local polygon and source hash receipt is `data/diagnostics/vehicle_placement_audit/west_stall_traces.json`. These are candidates for vehicle-fit and wheel-contact tests. Current striping, restrictions, legal use, and occupancy remain unverified.

The November 4 screen projects the visible transformed meshes of all 70 visible parked vehicles into ground-plan convex hulls. Every hull intersects a modeled road mesh and a schematic shoulder. No hull has a positive overlap above 0.01 m² with the tested building, dedicated sidewalk or expanded rear parking meshes. Road overlap alone cannot distinguish a valid curb parking lane from a travel lane, especially where the road and shoulder meshes overlap. A separate comparison to the eight Princeton and Smith draft crossing lines found no direct line overlap. One vehicle, `Car_018`, lies 4.097 m from the Smith south draft line (3870) and is the first curb-clearance review target. Neither painted stall extents nor crossing widths were tested. Local receipts are under `data/diagnostics/vehicle_placement_audit/`. Final placement requires verified stalls, curb restrictions and pedestrian geometry.

**Current result, November 2:** independent actual four-angle review accepts mid's hidden-interior removal only in the tested opaque-glass configuration. Far visibly loses brakes/wipers in close views. The first genuine QEM pilot fails visual quality; stricter trials deliver negligible savings. No district replacement, switching distance or performance acceptance is claimed. Earlier preparation descriptions below remain historical; [culling review](evidence/vehicle-lod-culling-review.json) and [QEM rejection](evidence/vehicle-qem-review.json) are the current visual evidence.

Ticket #10 now has inactive full/mid/far CarConcept candidates with actual geometry reduction. This is **source-component culling, not mesh decimation**. Body, glazing, tires and rims retain their exact source geometry, attributes, material bindings and world transforms. All variants have the same source bounding box; that numerical check does not establish an unchanged rendered silhouette or appearance.

Initial local inspection found no installed decimator. Source-component culling used existing USD/NumPy/SciPy only. A subsequent QEM trial acquired [PyVista fast-simplification 0.2.0](https://pypi.org/project/fast-simplification/0.2.0/) into an isolated ignored CPU-tool directory, with the original wheel checked against the publisher's SHA-256 and its [MIT license](https://github.com/pyvista/fast-simplification/blob/main/LICENSE) retained. Neither the global Python environment nor Kit was modified. A useful seam/material-aware far LOD remains unmet.

## Delivered geometry

Authoritative candidate: `data/diagnostics/vehicle_lods_20261102/candidate_v4/`. Earlier candidate folders are preserved camera-framing iterations, not the final review target.

| Variant | Mesh primitives | Vertices | Triangles | Triangle reduction |
| --- | ---: | ---: | ---: | ---: |
| full | 108 | 162,718 | 213,313 | 0% |
| mid | 62 | 127,774 | 169,084 | 20.73% |
| far | 51 | 87,063 | 129,672 | 39.21% |

Mid removes 46 named cabin/under-hood interior primitives, retaining engine, brake hardware and wipers. Far additionally removes 11 engine, brake-pad/disc and windshield-wiper primitives. `lod_manifest.json` lists **every exact source path, node ID/name, category, vertex and triangle count** removed at each level. Only primitive meshes are removed; ancestor transforms and their other descendants survive.

Opaque V3 glazing supports examining cabin-detail removal, but interiors might still be visible outside the body or through openings. Brake hardware can be visible through rims; engines through vents; wipers are exterior details. The subsequent actual comparisons confirm mid's bounded four-view appearance and reject far for close views; no open-door/underside/transmitting-glass proof or distance threshold is established.

## Contract and reproduction

[prepare_vehicle_lods.py](../tools/prepare_vehicle_lods.py) reads only the [reviewed V3 benchmark](CAR_CONCEPT_BENCHMARK.md), verifies its pinned `car.usda` hash and manifest dependencies, and requires `tinted-opaque` mode. It rejects an existing output directory. It uses existing USD Python dependencies, performs no downloads/installations/rendering, and never changes district placements, source/manual layers, editor sessions or API state.

```powershell
python tools/prepare_vehicle_lods.py --source data/diagnostics/car_concept_20261030/converted_v3 --output data/diagnostics/vehicle_lods_20261102/replay
```

Choose a fresh replay directory. The helper caps numeric worker threads and creates contained relative texture dependencies, three pruned USD assets, `vehicle_lods.usda`, review wrappers, attribution/license and a hash manifest. An interrupted build may leave partial output; it is not accepted evidence.

`vehicle_lods.usda` provides `/Vehicle` with explicit `lod` variants `full`, `mid`, `far`. Default is **full**, with no automatic distance selection and no active district adoption. Each variant references its own source-derived asset. The package retains CC-BY-4.0 attribution to ©2024 Darmstadt Graphics Group GmbH, model/textures by Eric Chadwick, pinned Khronos source links, trademark exclusions and modification notices. It adds the component-culling notice. Original geometry/source/license bytes are preserved; the opaque glass and other material limitations remain.

All 19 original V3 package files remained unchanged during generation. Every retained primitive's authored attributes, bindings and world transform matched the source; retained shader and ancestor attributes matched too. Isolated wrapper composition/dependency checks passed. CPU fixtures rejected tampered input before output creation and refused existing output without mutation. Twelve all-angle camera bounding-box checks pass with maximum absolute NDC below 0.90; `cpu_checks_v4.json` records them. These are builder selfchecks, not independent acceptance.

Final `lod_manifest.json` SHA-256: `e50861a3e91d0d4a2424bb26407c3412be31174931b7749f06465cf37a047e45`. `review.usda`: `a9067c702ca3a6384dff2c2734f240e867080275409f2354ad3cfef470d132a1`.

## Render-ready inspection

`review.usda` places full/mid/far left-to-right under the same lights, physical scale and Z-up/meters metadata. Combined camera aliases are `/World/Cameras/LODComparisonFront` and `/World/Cameras/LODComparisonRear`.

For unoccluded per-level comparisons, use `full_review.usda`, `mid_review.usda`, `far_review.usda`. These wrappers hide the other two diagnostic vehicles; source visibility is unchanged. Their matching camera paths are `/World/Cameras/{level}Front`, `{level}Rear`, `{level}Side`, `{level}Top`, with lowercase `full`, `mid` or `far`. Same-angle cameras have identical relative framing. Side-view isolation avoids a neighboring vehicle blocking the selected model. No GPU jobs or actual LOD renders have been run by this builder.

## Cost budget and remaining adoption gates

The three authored ASCII assets are approximately 27.57/21.53/15.30 MB, sharing one texture directory. File size is not runtime RAM/VRAM. Instancing can share mesh/material storage, but visible instances still incur geometry, shading and ray-tracing work. At 87 hypothetical visible copies, the respective triangle workload is 18,558,231 / 14,710,308 / 11,281,464 before other scene content. This arithmetic is not a performance measurement or a statement that all district vehicles are visible.

A useful first benchmark budget is **3 million visible vehicle triangles**, a provisional allocation rather than an accepted project requirement. It accommodates only 14 full, 17 mid or 23 far copies in isolation. Even this far candidate is therefore too dense to assume a district solution. Measure actual frame times and process/device memory at representative visible-car counts, with fixed camera/resolution/lights and clear user-runtime contention records; set an agreed budget from those observations. Do not infer FPS from triangle reduction.

After all-angle review, test screen-height-based transitions and visible popping; keep full near the camera and accept culling only where removed details no longer matter. No pixel thresholds are implemented or accepted. Proper material/UV-seam-aware simplification of detailed wipers/rims and other high-cost geometry may be needed for useful far LODs. Vehicle variety, local distribution, stall fit, varied-ground wheel contact, clearance/collision and traffic behavior remain open. No active adoption or ticket completion is implied.

## Actual quadric pilot — November 2, 2026

**Actual visual result: QEM V2 is rejected.** Matched front/side captures in `data/renders/20261102T171004Z/` show a jagged lower glazing join, wavy glass/door notch and slight paint faceting compared with `20261102T165222Z`. Exact open boundaries plus a sampled 2 mm positional guard and a 0.5 face-normal dot threshold did not protect glossy appearance or closely layered material joins. The V2 counts below are historical experimental results, not accepted LOD quality.

**Historical producer limitation:** V2's manifest records producer SHA `07b9c7ceb529e0bfd19353e7e596f5e9ef7f6144d6818fda13b560f165af009b`, but no exact producer-byte archive was recovered from the available candidate folders or Git file history. The working helper has since changed. The old method description below records historical manifest/author observations; it does not certify the exact old producer or claim that today's helper reproduces V2. Existing artifacts are preserved; missing source history has not been reconstructed or relabeled as authentic.

A separate genuine QEM candidate now exists at `data/diagnostics/vehicle_lods_20261102/qem_v2/`. This retains all cabin, brake, engine and wiper components; it does **not** apply the earlier component culling. [decimate_vehicle_lods.py](../tools/decimate_vehicle_lods.py) uses the isolated official PyVista `fast-simplification` 0.2.0 Windows wheel, acquired by the project coordinator from the [official PyPI release](https://pypi.org/project/fast-simplification/0.2.0/) with [MIT source/license](https://github.com/pyvista/fast-simplification). Wheel SHA-256 is `ce22a6f015707eb1d6d431c4896a18eb15c5f3cbaf32533d90371ea1b06875ad`; original wheel, publisher metadata, acquisition receipt and MIT license remain in `data/diagnostics/mesh_tools_20261102/`. Nothing was installed in Kit or the global Python environment.

The bound-material graph audit found 97 untextured primitives containing 208,645 triangles. The other 11 primitives, 4,668 triangles, have reachable texture shaders and remain **exact**, including geometry, normals and UV attributes. The algorithm never merges material primitives or welds coincident seam vertices. It simplifies indexed connected components with at least 100 faces, `preserve_border=True`, reduction target 40% and aggressiveness 3. This target is attempted per eligible component, not promised globally.

Accepted reductions must preserve exact boundary coordinates/edges, component count and Euler characteristic; remain finite with valid indices, nondegenerate faces and no nonmanifold edges; keep component bounds within 2 mm; pass sampled bidirectional surface checks within 2 mm; and retain a near-source face-normal dot product of at least 0.5. Failures retain the exact component. These are geometric safeguards, not exhaustive self-intersection, silhouette or architectural-quality certification.

Surface checks sample deterministic vertices and face centroids in both directions. Distance to the best of 32 centroid-near triangles is an **upper bound at each sample**, so the check can conservatively reject a valid candidate; unsampled maxima remain unknown. It is not a Hausdorff certificate. Source-normal interpolation uses four nearby original vertices **within the same indexed component**, with exact original normals at retained source coordinates; it does not smooth across source seams. Stale unused UV/tangent primvars are removed only on changed, untextured primitives. The pinned source's world transforms are effectively rigid (maximum singular-value deviation from 1 approximately `1.99e-7`), so its local-meter error checks closely match physical scale.

Actual result: **213,313 → 175,267 triangles (17.84% reduction)**, with 205 reduced components. Another 6,707 small components remain untouched. Conservative fallbacks retained 105 components exceeding sampled error, 25 failing orientation, 19 with no reduction and one failing bounds. The maximum accepted sampled distance upper bound was 1.991 mm. Rear panels reduce 12,984→8,324 triangles; hood 13,296→8,876; secondary panels 13,360→9,404. Rim reductions vary because source seam topology differs. This measured result supersedes any expectation of an automatic 80% reduction.

All 19 original V3 files remain unchanged. Serialized output passes finite-value, index/cardinality, exact textured-attribute and unchanged world-transform checks. A real planar QEM fixture reduced 800→480 faces with borders/normals retained; injected boundary damage triggered exact fallback. These are builder checks, not independent visual acceptance. The output still needs actual close/far silhouette, reflection/shading, wheel-detail and transition review, plus runtime measurements.

```powershell
python tools/decimate_vehicle_lods.py --output data/diagnostics/vehicle_lods_20261102/qem_replay
```

The isolated tool cache and pinned V3 source must already exist; this command performs no installation or download. A fresh output directory is mandatory. `full_review.usda` and `qem_review.usda` share the original `/Review/Camera`, ground and lights; matching `/Review/Front`, `/Review/Rear`, `/Review/Side` and `/Review/Top` cameras support all-angle review. Both use Z-up/meters. No GPU launch, active placement or district adoption is performed.

Final QEM asset SHA-256: `6785ada161465362426139dd1df521e0ed671764fedb6d1673a1941fd73fd94e`; manifest: `3df926b5d04969cde87bfe1aff3746512e8810d813235755b231585fbb861072`. At 87 hypothetical copies this pilot still represents 15,248,229 triangles, so it is a conservative first reduction, not an accepted far-distance budget or FPS result. Full CC-BY attribution/modification notices remain in the package. All variety, parking, terrain-contact, collision and physical-glass limits above remain open.

### Appearance-safe follow-up: reduction remains unresolved

The earlier nearest-four-vertex normal transfer was an approximation to the original shading field, not source-triangle barycentric interpolation. Also, unchanged perimeter edges do not constrain the interior surface immediately next to another material: millimeter-scale motion can expose or overlap closely spaced layers. These mechanisms are consistent with the failed image; no isolated render has established a single exclusive cause.

The revised helper preserves all 49 Body-named/glass/paint/tire/glossy-rim primitives exactly, plus the 11 textured primitives. It transfers normals barycentrically from original triangles within each indexed component and requires new face-centroid shading normals to deviate by at most **3 degrees** from the original field. Position/boundary/topology guards remain unchanged. This is still a sampled appearance safeguard, not complete shading or silhouette equivalence.

At the original 40% requested reduction, `qem_v3/` retains every component: **213,313→213,313 triangles**. Another bounded trial at 10%, `qem_v4/`, reduces only **213,313→213,119 triangles (0.091%)**. The strict rules were not relaxed to manufacture a large reduction. These candidates provide no material district-performance benefit; no additional GPU run or adoption is justified by their counts alone.

Current replay defaults to the safer 10% target and accepts `--target-reduction` greater than zero and at most 0.4. For example:

```powershell
python tools/decimate_vehicle_lods.py --output data/diagnostics/vehicle_lods_20261102/safe_replay --target-reduction 0.1
```

Original V2/V3/V4 artifacts remain preserved. Source-component culling and QEM studies remain inactive; a useful normal/material-aware far LOD with actual accepted appearance is still unmet.

Historical trial manifests record the actual target in the method text (0.4 for V2/V3 and 0.1 for V4/V5). The current helper additionally emits a numeric `requested_target_reduction` field for direct machine inspection. Frozen outputs were not rewritten for this metadata extension.

### Captured-producer repeat

`qem_v5/` repeats the same 10% request with unchanged quality gates and again yields **213,119 triangles**. Before dependency validation or geometry processing, the builder now saves its exact starting bytes as `captured_helper.py`. The completion manifest records `captured_helper_sha256` and `tool_sha256`, and publication fails if the working file changes during execution. The archived file is included in output checksums. It is an audit source snapshot, not a portable launcher (its project-root assumptions still require the original project location).

Direct read-back confirms the 49 appearance-critical and 11 textured primitives retain every source attribute and relationship target exactly. This reproducible negligible reduction is not a newly accepted useful LOD; no GPU proof or adoption is claimed. V3/V4 descriptions remain historical trials rather than proof of their unarchived producers. Future runs preserve producer bytes from the outset; the missing old V2 producer remains explicitly unavailable.
