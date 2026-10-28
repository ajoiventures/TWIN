# Frozen-pilot OCPA aerial reference discovery

Bounded #20 progress, October 28, 2026. The frozen pilot is `edgewater-princeton-smith-south-v1`, Edgewater Drive from W Princeton Street to the southern W Smith Street junction, 85.44 m of centerline. The 60 m context buffer is an extraction/review context, not surveyed right-of-way. Source snapshot: `20261028T145054204280Z`.

## Official source discovery

The public [OCPA services root](https://vgispublic.ocpafl.org/server/rest/services) identifies a public [OCPA folder](https://vgispublic.ocpafl.org/server/rest/services/OCPA). Its observed dated aerial services are 2006, 2017, 2022, 2024 and 2025. This is the observed public folder, not a claim that all available county imagery has been inventoried. No protected/private service was used.

Three public MapServer exports cover the frozen pilot context and were visually inspected as actual aerial imagery:

| Reference | Official descriptive acquisition evidence | Remaining date uncertainty |
|---|---|---|
| [Aerials2025](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer) | [Item metadata](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2025/MapServer/info/iteminfo?f=json): “Orthophotos flown January 2025 by Sanborn” | Exact flight day and local frame date unverified |
| [Aerials2024](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2024/MapServer) | [Item metadata](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2024/MapServer/info/iteminfo?f=json): “2024 Aerial imagery flown Jan by Sanborn” | Exact flight day and local frame date unverified |
| [Aerials2022](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2022/MapServer) | [Item metadata](https://vgispublic.ocpafl.org/server/rest/services/OCPA/Aerials2022/MapServer/info/iteminfo?f=json): “Aerial photography acquired in January 2022” | Exact flight day and local frame date unverified |

Month-level dates come from descriptive metadata, not filenames, item creation, service modification or the model baseline date. The 2024/2025 XML also contains an older 2023 metadata date, which is not treated as capture time. No claim is made that January 2025 depicts current October 2026 conditions.

## Local reference outputs

Run `python tools/imagery_reference.py --refresh`; `--offline` replays existing metadata and verifies preview checksums against the same pilot hash. Export URLs are requested freshly because ArcGIS output image URLs are temporary. No source datasets are modified.

Outputs under ignored `data/imagery/`:

- `pilot_imagery_reference.html`: side-by-side local reference sheet with capture month, attribution link and limits.
- Three original JPEG API exports named `OCPA_Aerials<year>_edgewater-princeton-smith-south-v1.jpg`.
- `pilot_imagery_manifest.json`: service/catalog IDs and URLs, original descriptive dates, metadata checksums/retrieval times, export request/bounds, image hashes and image sampling statistics.
- `pilot_aerial_review_queue.json`: **21 building groups**, with safe parcel/address/match fields and unresolved roof, addition, parking/driveway, canopy and curb-frontage review topics. Twenty have stored exact links and one remains a spatial review link; no link is promoted.
- `cache/`: source metadata response envelopes. Offline outputs receive an `_offline` suffix.

Exports are 768 × 1,152 pixels in EPSG:2236, NAD83 Florida East US survey feet. The returned adjusted export extent yields approximately **0.178384 m per output pixel** in each direction. This is export sampling, not verified native acquisition GSD, roof-position accuracy or a survey tolerance. Cached-service LOD metadata is retained separately; render sampling must not be confused with a sensor's ground resolution.

The three images show the same corridor context with roofs, street markings, parking and canopy visible. Visual inspection confirms useful nonblank imagery, but does not complete property-by-property alignment or change detection. Perspective/roof displacement, shadows, trees and image dates can limit measurements.

## Reuse and publication limits

Public export access is observed. The selected item metadata has empty `licenseInfo`; that is not an affirmative redistribution or machine-learning license. The 2022 source credits OCPA and states the map is for reference only, not a survey. Keep these bounded exports as local review references; do not commit imagery, deploy it publicly, extract ML training/evaluation data, or imply unrestricted rights without source-specific terms review. No rights are inferred from a vendor name or empty copyright text.

## Acceptance still required for full #20

1. Review all pilot buildings and curb frontages against the three dated references and current accepted footprint geometry; record source/version and any residuals rather than eyeballing a survey tolerance.
2. Create an evidence-linked discrepancy layer for roof/addition, parking/driveway and canopy differences. No automated accuracy or change conclusion is generated here.
3. Keep occluded or unclear features unresolved. Aerials do not establish current tenants, facade appearance, measured roof height, sidewalk grade or ADA compliance.
4. Resolve reuse/redistribution/AI eligibility for any intended use beyond local review and obtain exact dates/native resolution if the use requires them.
5. Preserve pilot/snapshot identity and separate existing, historical and proposed designs before feeding scene geometry.

This completes bounded official imagery discovery and local reference acquisition, not full ticket acceptance or source-geometry promotion.
