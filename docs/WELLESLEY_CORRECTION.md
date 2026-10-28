# Wellesley historical upper-roof correction

This scoped correction reconstructs the missing tall C-shaped Wellesley mass at 2305 Edgewater Drive. It does not extrude the 114-record tax envelope, promote ambiguous parcel matches or assign seven floors to surrounding podium/garage structures.

## Applied checkpoint

Applied October 28, 2026 to refreshed snapshot **`20261028T160543372334Z`**. Stable source identity resolved the target as **`Building_2939`**, while its original extraction alias was `Building_2933`. The exact nine source OBJECTIDs and target base-mesh hash still matched, so no geometry guard was bypassed.

- Historical planar upper height: **23.35 m** (55.04 m NAVD88 roof support minus 31.69 m local ground).
- Independently reported documentary count: **seven storeys**; nominal height **22.86 m**, 0.49 m below the derived roof-zone height.
- Accepted upper C-shaped footprint after cleanup: **3,106.41 m²**, supported by **74,661** points.
- Retained original lower mass outside the upper footprint: **820.99 m²** at its prior **4.3 m** height, still unresolved.
- Property envelope: **6,146.46 m²**; it was not extruded. The broad courtyard opening remains absent from the upper mass.
- Exactly one height row changed; **all 3,215 other rows** remained unchanged. An idempotent rerun reproduced the same height and geometry.

Generated writes are finished. The parent handles final layer composition, semantic-registry refresh, actual editor reload and rendered review. This document does not claim those parent integration checks have already passed.

## Source evidence and failure

The [independently reviewed MetroPlan reference](WELLESLEY_REFERENCE.md) reports seven storeys and 75 feet (22.86 m nominal) in January 2016. OCPA safe unit records independently report FLOOR_NO positions through 7, while most unit STYS values are zero/unknown. The old source group uses parcel `292214147406110`, building number 1 and nine footprint subareas; its current parcel match remains ambiguous/unmatched.

The earlier height pipeline used only classified building points (class 6) and a one-floor source prior. Within the current property envelope, high surfaces are instead predominantly class 1 (unclassified), including a dense plane near 55.0 m NAVD88. Classified local ground is near 31.69 m. The old class-6-only candidate follows lower or unrelated components and cannot represent the whole tall building.

## Reproducible bounded method

`config/building_corrections.json` freezes the source parcel/building number, exact nine source OBJECTIDs, original source mesh hash, point-cloud checksum, documentary reference and extraction parameters. The generated `Building_####` name is a historical alias, not the target identity. The tool resolves the current group from the stable source identity and fails on changed membership/geometry/cloud or changed match status. A refreshed extraction/snapshot may change enumeration IDs without silently targeting another building.

`tools/correct_wellesley.py`:

1. Uses the current 2305 Edgewater property union only as a clipping/search mask, never as an extrusion outline.
2. Reads existing historical EPT points, verifies the accepted meter-unit check, projects XY to metric UTM and uses class-2 local ground.
3. Finds the dominant high class-1 elevation mode 15–30 m above local ground.
4. Accepts 0.75 m cells with at least five points, median within 0.4 m of that plane and p85–p15 spread no greater than 0.3 m. Density and planarity reduce vegetation inclusion; class 1 alone is not a roof label.
5. Applies one-cell opening/closing, drops components below 100 m², optionally fills enclosed gaps no larger than 25 m² and simplifies by 0.4 m. These processing assumptions remain explicit shape uncertainty. The large open courtyard must remain absent.
6. Rejects a roof under 1,500 m², an outline filling more than 80% of the tax envelope, a loss of at least 400 m² of concavity/void space or a derived height differing from the nominal documentary height by more than 2 m. These are review gates, not accuracy standards.
7. Authors only the supported upper footprint to its derived height. It retains the original lower source mass **only outside** that upper footprint at its prior unresolved low height.

Early read-only extraction produced a clear roughly 3,379 m² C-shaped planar roof with a large eastern courtyard opening, near 23.35 m above local ground. The final conservative grid/planarity cleanup yields 3,106.41 m²; the manifest retains counts and processing assumptions. Internal roof-equipment/terrace gaps larger than the small-gap infill threshold remain unresolved holes rather than being silently filled. Neither outline is asserted as a current survey.

## Layers, height data and guards

The generated additive `scene/landmark_corrections.usda` replaces the resolved building mesh/roof with independent upper and retained-lower components. It resets mesh topology, outward winding, normals and UV arrays rather than inheriting arrays sized for the old footprint. Nested height-inspector metadata is overridden consistently with the new mass. It adds `/World/Cameras/WellesleyEvidence` for repeatable review. Source base geometry and original source IDs are untouched.

The tool updates exactly one current height row, retaining its raw source floor fields and ambiguous parcel identity. It sets documentary storeys to seven and labels the derived height/shape historical with uncertainty. All other height rows are checked unchanged. The aggregate quality report is recalculated from the current rows. The previous one-floor record is backed up locally; reruns are idempotent for the same correction identity.

The parent composition must place the correction layer stronger than generated height/semantic layers, then rebuild provenance and inspect the actual running viewport. The tool does not edit the connected assembly, shared generators or API. Running the generic height generator later requires reapplying this correction before final composition/provenance.

## Run and evidence

After the parent confirms regenerated base/snapshot readiness:

```
python tools/correct_wellesley.py
python -m unittest discover -s tests -p test_wellesley.py -v
```

Generated review evidence remains ignored under `data/heights/wellesley_correction/`: `manifest.json`, `upper_roof.geojson` and `roof_support_mask.png`. The manifest records exact source/configuration identity, derived upper area/height, retained lower area, documentary reference, prior/current target row and target-ID crosswalk.

Nine tests cover courtyard preservation, rejection of a full-envelope rectangle, classification scope, nonplanar isolated points, one-row-only updates, duplicate target protection, hole-preserving triangulation, valid topology/normals/UV arrays and stable identity resolution across a generated-ID change.

## Limits

The source cloud and documentary report are historical; neither establishes current roof details. Roof-equipment gaps, balconies, parapets, exact stepped heights and vegetation separation remain approximate. Small gap infill and smoothing are disclosed. The retained low source components remain unresolved rather than being misrepresented as seven storeys. Ground stays at the current flat model datum until terrain integration separately establishes vertical rebasing. No facade/window layout or precise architectural reconstruction is claimed.
