# Princeton duplex identity and displaced sketch investigation

Primary-source review October 28, 2026. Subjects: parcel `292214147800250` (624 W Princeton) and `292214147800330` (520 W Princeton). No parcel match, geometry, height or scene layer is changed by this investigation.

## Identity resolved; drawn geometry remains unaccepted

| Subject parcel | Official address aliases on the same PID | Primary photograph | Storey interpretation |
|---|---|---|---|
| `292214147800250` | **624 and 626 W Princeton Street**, both address records at [-81.3879492166, 28.5710045004] | [OCPA image](https://ocpaimages.ocpafl.org/api/Image/GetPIDImage?pid=292214147800250), caption May 20, 2015. Facade numbers624/626 visible; caption626. | Property STYS2, but front image shows a single-story gabled front mass. Upper-story subareas exist in source records; rear/partial upper mass needs verification. Do not uniformly raise the whole mass two storeys. |
| `292214147800330` | **520 and 522 W Princeton Street**, address records at [-81.3867281590, 28.5710629919] and [-81.3866234009, 28.5710632903] | [OCPA image](https://ocpaimages.ocpafl.org/api/Image/GetPIDImage?pid=292214147800330), caption February 12, 2024. Both520/522 entrances and two full facade levels visible. | Two-storey duplex corroborated by the historical photograph, STYS2 and base/upper area accounting. Roof geometry still needs reconstruction on the correct parcel. |

Both aliases for each subject are contained by their respective current parcel polygon. The official [ADDRESS_POINT layer](https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/0) provides the same source PID for each pair. These are primary address/parcel associations, not matching assumptions based on a web search.

The [parcel service](https://vgispublic.ocpafl.org/server/rest/services/DynamicForJs/PARCEL/MapServer/4) reports:

| Subject | STYS | Year built | Living area SF | Gross area SF |
|---|---:|---:|---:|---:|
| 624 / 626 | 2 | 1985 | 1,820 | 2,340 |
| 520 / 522 | 2 | 1978 | 2,448 | 2,448 |

No owner/contact, financial assessment or private BOOMS fields were requested. Photos remain ignored local source references; public access does not establish redistribution or machine-learning eligibility. A photograph's caption date is its historical evidence date, not a current condition guarantee.

## Why the current drawn footprints cannot be promoted

The public [building subarea service](https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Layers/MapServer/28) still returns the displaced geometry. These discrepancies are in the source linework, not just the local join:

| Subject source group | Union area m² | Fraction overlapping its own parcel | Union-centroid distance to parcel centroid |
|---|---:|---:|---:|
| 624 PID / building1, eight subareas | 217.246 | **8.6029%** | 15.621m |
| 520 PID / building1, two subareas | 114.805 | **0%** | 15.351m |

624's old group lands largely on neighboring 644 W Princeton (`292214147800150`, College Park Methodist source property), producing the existing 91.4% spatial-review result. That does not make it a church building. 520's old group is displaced east of its own parcel. The separate 521 W Harvard group (`292214147800440`) has an upper-story subarea grazing the south edge of the520parcel, but its PID and address remain Harvard; that overlap cannot represent the520duplex.

The footprint rows' `X_COORD`/`Y_COORD` reference points, interpreted in the service's Florida East US survey feet system, transform to the parcel's published longitude/latitude virtually exactly:

- 624 source XY [531652.792,1540481.698] → approximately [-81.3879245069,28.5709323713].
- 520 source XY [532053.278,1540482.710] → approximately [-81.3866768214,28.5709387154].

This establishes consistent source record anchoring while the drawn component polygons are mislocated. It **does not** establish a surveyed building center, an approved translation vector or permission to shift the polygons automatically. Source centroids, property representative points and actual roof centers are different things.

624 subarea `SKETCH_DT` is July24,2003; 520 subarea `SKETCH_DT` is October18,2002. Both have `PULL_DT` January18,2006. These are the named source fields, not independently verified acquisition/last-survey dates. Their age reinforces the need to validate against newer aerial/roof evidence.

## Area accounting resolves the FLOOR_NUM trap

Every subject subarea says `FLOOR_NUM="1"`, including rows explicitly labeled `FUS` / upper story. Thus this field cannot safely be treated as whole-building story count for these groups.

| Subject | Source accounting | Reconciliation |
|---|---|---|
| 624 / 626 | BAS494SF×2 + FUS416SF×2 = 1,820SF; plus FGR240SF×2 and FOP20SF×2 | Exactly equals parcel living1,820SF and gross2,340SF. Supports base/partial-upper/garage/porch components, not a uniform two-floor prism. |
| 520 / 522 | BAS1,224SF + FUS1,224SF | Exactly equals living/gross2,448SF. Corroborates two levels; the drawn floor plate remains geographically displaced. |

A two-story source attribute is credible context here, while geometric placement and per-component height remain separate acceptance decisions.

## Recommended correction path

1. Preserve aliases624/626 and520/522 under their source PIDs. Show these address identities even while footprint match is unresolved.
2. Use the current parcel, official address points, dated OCPA aerials and classified roof points to identify the actual roof on each parcel. The local January2025 aerial reference is `data/imagery/princeton_parcel_review/aerial2025.jpg`; trees obscure parts of the624area.
3. Keep624's front/base, upper portion, garage and porch distinct. Its2015front photo does not locate the rear upper mass. Do not copy a two-floor estimate across every component.
4. Reconstruct520/522's two-story roof at its own identified location; do not use the adjacent Harvard upper-story polygon as a substitute.
5. Record source geometry lineage, any measured/digitized roof reference and uncertainty; independently review before promoting a correction. Avoid automatic translation based solely on parcel/geometry centroid difference.

The bounded City-organization building/footprint search did not return an alternate residential footprint source in this immediate area. Public property sketch requests returned404 for these two PIDs. No protected/private services or authentication workarounds were used. These access results are not a general claim that no alternate dataset or sketch exists.

## Reproduce and source receipts

Run `python tools/princeton_identity_reference.py`; `--offline` replays cached public query responses and local photographs without contacting sources. New files are configuration, tool, tests and this report only. Safe results under ignored `data/imagery/princeton_parcel_review/identity_evidence.json` include source-query URLs, retrieval times/checksums, safe property records, source address points, subarea dates/areas, photo-caption references and unaccepted geometry metrics.

Three tests verify exact area accounting, partial upper-story semantics and explicit mismatch handling. No code promotes a spatial match, shifts geometry or changes a model height.
