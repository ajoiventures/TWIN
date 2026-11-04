# Road reference and surface-quality review

This local gallery presents actual images for two different jobs: the OCPA aerial documents a historical place; the Poly Haven asphalt is a representative rendering material. Road and sidewalk geometry acceptance remains separate.

Run `python tools/road_reference_gallery.py` after the parent material acquisition. It reads `data/processed/road_materials.json`, verifies referenced local files exist, and writes ignored `data/transport/road_reference_gallery.html`. The parent serves this page at `/road-review` and whitelists four local image routes:

- `/road-reference/aerial2025`: original January 2025 OCPA pilot aerial export.
- `/road-reference/asphalt-1k`: actual 1K diffuse map.
- `/road-reference/asphalt-2k`: actual 2K diffuse map.
- `/road-reference/asphalt-4k`: actual 4K diffuse map.

The gallery initially focuses **balanced 2K**, matching the current material register. Each card explains purpose and offers image inspection without implying that a browser button changes the live scene. The aerial can be opened at its original local resolution. Image alternatives, keyboard-operable buttons, visible focus and a live preview caption support inspection.

| Quality role | File resolution | Intended job | Acceptance limit |
|---|---|---|---|
| Preview | 1K | Iteration and distant views | Detail/performance tradeoff still measured on the target scene |
| Balanced — current working choice | 2K | Working scene and normal playback | Not proof of visual or performance acceptance |
| Presentation | 4K | Close rendered inspection | Higher detail costs memory; benchmark before broader use |

All tiers use the same approximately **3 m × 3 m physical repeat**, from the publisher's physical size recorded in the local register. Resolution changes texture sampling, not road widths, surface geometry or geographic location. The diffuse previews are color maps, not final PBR renders; the parent scene also uses OpenGL normal and roughness maps. Street-level material scale, daylight, shadows, markings, curb joins, sidewalks and performance remain review items.

The surface source is [Poly Haven asphalt_02](https://polyhaven.com/a/asphalt_02), [CC0](https://polyhaven.com/license). Credit displayed in the gallery: **Powered by Poly Haven**. The parent acquisition manifest records publisher MD5, local SHA-256, file size and source URL for all nine maps. This generator does not download, edit or commit image assets.

The January 2025 aerial is sourced from the [official OCPA service](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json), whose description identifies the January 2025 Sanborn flight. It supports local review of existing-condition road layout, markings, parking and canopy at that date. Shadows, trees, historical changes and unverified native acquisition accuracy limit measurement. It is not used as a pavement texture, and public redistribution/AI-use eligibility is not inferred from service access. Keep the original export under ignored `data/imagery/` for local review.

The gallery deliberately keeps dated place evidence and representative PBR material separate. Realism, road geometry, pedestrian clearance and laptop-performance acceptance remain pending; this page supplies concrete review inputs rather than claiming those checks passed.

# Integration evidence — October 28, 2026

The local API serves `/road-review` and four explicitly allowed image routes. HTTP checks returned 200 for the gallery, dated aerial and all three texture previews; unknown image names return 404. No request fetches an agency image. The 2K material is composed in the working scene; a real 1920×1080 Kit render is recorded at `data/renders/20261028T173244Z/manifest.json`. That render also uses a temporary Wellesley roof proposal, so it does not prove the proposal is active. Visual inspection still shows simplified façades, approximate street edges and excessive depth-of-field blur. This is not conference visual acceptance. Scene validation checked 20 layers and 17,611 meshes with no local-profile errors; terrain remains flat and pedestrian geometry is unverified.

