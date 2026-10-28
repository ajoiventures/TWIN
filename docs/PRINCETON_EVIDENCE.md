# Princeton historical component reconstruction

Status: proposal ready for parent review and composition. `scene/princeton_correction.usda` is additive and is **not activated by this tool**. No global height row, source parcel link, semantic registry or root assembly is edited. This is a historically derived shape improvement over obsolete detached-house geometry, not a current survey or accepted as-built building footprint.

## Identity and evidence

Current snapshot `20261028T160543372334Z` identifies Princeton at College Park, PIN `292214725701000`, 646 W Smith Street, project maximum STYS 6, AYB 2019. Six is a property-level maximum; individual wings and parking components have unknown storey counts. The live safe-field OCPA query and its cached response receipts are included in the manifest. No owner fields or private BOOMS records are used.

The source is the existing accepted [USGS Orange County 2018 EPT project](https://s3-us-west-2.amazonaws.com/usgs-lidar-public/FL_Peninsular_FDEM_Orange_2018/ept.json). Its project acquisition interval is December 4, 2018 through April 12, 2019. Local flight date and construction phase are unresolved. The bounded reader selects 28 source hierarchy nodes and clips 279,457 points to the actual parcel, including the eastern sliver outside the earlier pilot. Existing source bytes are reused, node URLs/checksums preserved, and global pilot coverage is unchanged. XY is converted to EPSG:32617; Z is NAVD88 meters, guarded by the accepted project vertical-unit check. Original DEM US survey feet are never substituted.

[City ordinance 2014-47](https://orlando.novusagenda.com/AgendaPublic/AttachmentViewer.ashx?AttachmentID=58930&ItemID=37138) supplies proposed redevelopment context, not as-built dimensions. Referenced architectural exhibits were not included in the retrieved eight-page ordinance. The [City November 2024 market report](https://www.orlando.gov/files/sharedassets/public/v/1/departments/edv/business-development/city-of-orlando-market-report_final_november-2024.pdf) confirms completion in 2019; conflicting text/graphic unit counts are not used. The 2025 OCPA aerial was reviewed locally to check for completed stepped buildings, western parking deck, eastern open courtyard and absence of detached houses. No image textures, imagery redistribution or traced geometry are promoted.

A bounded City ArcGIS organization search for building/footprint items and OCPA Base service layer-name inspection did not establish a suitable current whole-building footprint. Exact queries, candidates and access outcomes appear in `alternate_current_source_review`. This search is not proof that no better municipal source exists.

## Geometry and uncertainty

One-meter cells require at least five source points and an 85th-minus-15th percentile spread no larger than 0.55 m. Four fixed elevation bands, small-gap filling and component-size filtering produce diagnostic masks. The parcel is only a search/clipping boundary, never the roof extrusion outline. Local median ground is 31.59 m.

| Diagnostic zone | Roof elevation NAVD88 m | Relative height m | Class 1 / Class 6 support points |
| --- | ---: | ---: | ---: |
| Highest west | 52.05 | 20.46 | 37,011 / 0 |
| Middle | 49.55 | 17.96 | 43,196 / 10 |
| Lower east | 43.09 | 11.50 | 3,867 / 37,886 |
| Higher eastern hipped parts | 44.69 | 13.10 | 5,319 / 23,869 |

Support counts refer to points within accepted, source-supported cells before polygon overlap trimming. Class 1 is unclassified, **not certified roof**. Planarity/density can retain smooth canopy, equipment or construction surfaces, including small isolated components. These are explicit historical candidates, not authoritative semantic roof classes. West/middle planes approximate roof/deck levels; parking ramps and architectural details remain unresolved.

The rendered proposal has three components under `/World/Landmarks/PrincetonAtCollegePark`: highest west, middle, and an eastern variable roof. The eastern two diagnostic bands are merged once, using continuous shared-corner cell heights rather than duplicate slabs or a uniform six-floor extrusion. Eastern relative heights range 10.72–15.3775 m; its mesh contains 13,181 faces and 40,554 vertices. Actual rendered union is 6,546.57 m² within a 10,206.12 m² property.

Higher west geometry takes priority over the middle zone: 1.05 m² of simplified overlap is subtracted from the middle. Eastern cells are clipped outside these two components. No overlapping west/middle mass is retained. A frozen 8 m × 8 m core of the actual point-derived open courtyard, EPSG:32617 bounds `[462075,3160574,462083,3160582]`, must remain empty. This guards a real courtyard independently of the broad 85% parcel-area sanity check. The current mask and actual exported roof faces intersect that core by 0 m². It is a protected core, not a claim that every courtyard edge has surveyed accuracy.

## Obsolete source groups and integration

Fourteen old house groups are checked against source PID, building number, exact source object IDs, canonical target mesh hash and current spatial-review assignment. A source identity/geometry/assignment change fails regeneration. Thirteen fully contained groups receive additive visibility overrides. Building_3024 overlaps the project 98.912%; its 2.048 m² outside-property remainder is retained at its original height. Accepted links or same-parcel source groups cannot be silently superseded. Raw source geometry and all original parcel matching evidence remain unchanged.

`data/heights/princeton/manifest.json` records action `proposal_ready_for_parent_review_not_composed`, acceptance `historical_component_reconstruction_only_current_as_built_validation_pending`, snapshot/configuration lineage, per-zone support, supersession actions and remaining limitations. Parent integration should surface new landmark components separately from the 3,216 legacy registry rows, preserving their unresolved raw links. Camera: `/World/Cameras/PrincetonEvidence`.

## Reproduce and validate

Run `python tools/princeton_evidence.py` for an entirely cached/offline replay; `--live` allows bounded official-source misses. Dependencies are the current Python runtime plus `.dependencies`. Generated point cache, preview, manifest, GeoJSON and layer are local ignored artifacts. Reproduction requires the source snapshot, accepted vertical-unit record and guarded base scene.

`python -m unittest discover -s tests -p test_princeton_evidence.py -v`: **14 tests pass**, including actual cached cloud/mask/exported-face courtyard regression, source slope/holes, property clipping, overlapping-height priority, supersession safety, no-network offline misses and USD topology/normals/UV. The actual-data regression explicitly skips when ignored source artifacts are unavailable; synthetic guards remain mandatory.

Current as-built component boundaries, roof pitch, local acquisition timing, architectural use and per-component storeys remain pending. Do not present this reconstruction as verified current geometry or apply six storeys to the entire property.
