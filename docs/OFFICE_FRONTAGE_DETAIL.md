# Office frontage detail review

October 29, 2026. Tickets #6/#8/#11/#32 remain open. This is one appearance improvement within the full Main Street building queue.

The existing 1615 Edgewater draft is recognizable as the two-storey brick office with a central clock portico, dormers and chimneys. Its first actual review still missed the smaller front pediments and continuous pale cornice, and the roof appeared lighter than the address-specific broker photographs. Window rhythm, side openings, roof proportions and present-day condition remain unresolved. The historical cloud is from 2018â€“2019; the brochure photograph capture date is unknown.

`tools/refine_office_frontage.py` reuses that existing frontage and roof assembly. It produces a detail-only delta: ten wall-following cornice segments, two small front pediments with approximate proportions, and an original darker roof material. It does not replace the historical roof mesh, alter building heights or infer unseen rear details. Source photos are qualitative references; no photo pixels, logos or contact details are embedded in the model or committed images.

## Script contract

- Inputs: `scene/office_frontage_review.usda` and its used layers; existing address-specific broker reference pages 3/4/9 under ignored local imagery.
- Units: existing project local coordinates, metres, Z up. No new georeferencing or height datum transformation.
- Execution: `python tools/refine_office_frontage.py --output data/diagnostics/<new-review-name>`.
- Publication: requires a new contained output directory. Existing outputs are refused. No network, active pointer update, scene reload, activation or source write.
- Outputs: `detail.usda`, a `workview.usda` using the unchanged camera/lighting, and a manifest with source/photo hashes and interpreted dimensions. Raw references remain local.
- Verification: inspect actual same-camera renders and review the composed source geometry. Added architectural proportions are estimates; a better picture does not certify survey/currentness. Adoption requires exact compatibility with the active office and independent review. The scene builder now retains the layer only when its activation receipt, snapshot, base-layer and detail hashes match.
- Recovery: remove only the separate detail sublayer while retaining current root/manual opinions. The activation receipt records the prior root copy and expected hashes; do not overwrite later user changes with an old backup.

## Actual matched images

The initial draft and detail candidate used the same OfficeFrontage camera, lighting and 1920Ã—1080 capture. Review inputs are frozen under `data/diagnostics/office_frontage_detail_20261029_a`; captures are `data/renders/20261029T162514Z` and `data/renders/20261029T162931Z`.

![Existing interpreted draft](evidence/office-frontage-baseline.png)

![Detail candidate](evidence/office-frontage-detail.png)

Independent findings and acceptance limits: [office-frontage-review.json](evidence/office-frontage-review.json). The detail improvement passed bounded appearance review. An additional comparison found all 177 geometry-bearing office/frontage prims and their world transforms match the currently composed office. The accepted appearance detail is now composed on disk in a separate layer after manual edits. A recorded root backup, exact base-equivalence check and unchanged other source/manual/pointer/selection hashes preserve recovery. The owner's running editor was not reloaded. The integrated-scene render passed detail placement review but failed broader scene presentation: façade striping and black road/sidewalk polygons remain visible. Those defects are recorded separately and are under diagnosis. The underlying historical roof has remaining whole-cloud residuals and qualitative shape limits. This work does not close a district-wide building or storefront ticket.


[Activation and preservation receipt](evidence/office-frontage-activation.json) records the appearance-only adoption. `validated_active_detail` guards reuse in the scene builder; the native refresh allowlist includes the new layer. Dependent reconstruction/corridor reports are refreshed after composition.


The integrated capture `data/renders/20261029T163710Z/OfficeFrontage.png` was independently inspected. Its detail placement passes; its overall appearance does not pass professional-quality acceptance. A separate normal-map diagnostic is being rendered to isolate the façade striping. No shading cause has yet been established.


![Integrated scene: placement passed, broader materials and streets still fail presentation review](evidence/office-frontage-integrated.png)
