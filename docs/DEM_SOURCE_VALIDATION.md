# Original DEM acquisition and validation

Ticket #6 checkpoint, October 28, 2026. This work acquires and validates source terrain rasters. It does **not** author a terrain USD layer, move scene objects, activate a snapshot or claim surveyed accuracy.

## Reproduce

```
python tools/acquire_dem.py
python tools/acquire_dem.py --offline
python -m unittest discover -s tests -p test_acquire_dem.py -v
```

Use the project Python runtime and installed `.dependencies` (Pillow, NumPy and pyproj). Rasterio is not required for these files.

`config/terrain_sources.json` freezes six specific original DEM/XML URLs selected from the accepted FloridaGIO tile index in `data/processed/source_catalog.json`. The configuration records the selection catalog checksum, source index IDs, expected source CRS/vertical units/acquisition interval, pixel scale and review thresholds. Only six tiles can be acquired; each raster is capped at 32 MiB and each metadata response at 1 MiB, with at most two concurrent downloads. Downloads use official allowlisted USGS HTTPS hosts.

## Acquired sources

Original TIFFs and source XMLs are preserved byte-for-byte in ignored `data/heights/dem/`. Per-file `.source.json` receipts retain exact URL, final URL, downloaded bytes, original fetch time, server Last-Modified/ETag where supplied and locally computed SHA-256. A checksum is not claimed to be an externally published agency checksum. Offline replay verifies local source bytes against the receipt and does not replace the original fetch time.

| Tile | Original TIFF bytes | Raster size |
|---|---:|---|
| DEM257172 | 8,568,020 | 2,000 × 2,000 |
| DEM257173 | 13,569,272 | 2,000 × 2,000 |
| DEM257472 | 13,010,000 | 2,000 × 2,000 |
| DEM257473 | 15,446,214 | 2,000 × 2,000 |
| DEM257772 | 14,590,916 | 2,000 × 2,000 |
| DEM257773 | 11,805,968 | 2,000 × 2,000 |
| **Total** | **76,990,390** | **24,000,000 source pixels** |

The six metadata records identify acquisition **2018-12-04 through 2019-04-12**, published **2021-04-20**. They belong to the same Orange acquisition as the existing USGS/NOAA EPT sampling; original rasters and EPT are not independent measurements.

## CRS and units verified in all six files

Pillow decodes every raster and GeoTIFF directory; pyproj independently resolves the named horizontal/vertical CRS. Source XML and embedded keys agree:

- Horizontal: **EPSG:6438**, NAD83(2011) / Florida East (ftUS).
- Vertical: **EPSG:6360**, NAVD88 height in US survey feet; vertical datum key identifies North American Vertical Datum 1988.
- Projected and vertical unit keys: **9003**, US survey foot.
- PixelScale: **2.5 × 2.5 US survey feet**, approximately **0.762001524 × 0.762001524 meters**.
- Raster interpretation: PixelIsArea, normal top-left orientation, one Float32 band.
- Embedded NoData: **-999999**. Nonfinite values are also invalid; negative real elevations are not automatically rejected.

**Original raster Z values are feet. The existing transformed EPT Z values are meters.** No blanket multiplication can be applied to both. Source raster bytes are never converted in place. The derived seam metrics use `1200 / 3937` meters per US survey foot.

The manifest retains each GeoTIFF key set, source origin/bounds, dimensions, pixel counts, original elevation range, XML dates/constraints and source receipts. A changed CRS, units or acquisition interval fails validation rather than silently reusing the tile.

## Actual valid-pixel coverage

This replaces metadata-envelope assumptions with decoded pixel checks. All **24,000,000** pixels across the six original tiles are finite and not the declared NoData value.

For the extraction rectangle `[-81.398, 28.5605, -81.379, 28.5845]`, the tool creates a common source-aligned grid of **2,452 × 3,500** pixels. Every grid pixel center is transformed to WGS84 to determine membership in the geographic rectangle. Every applicable source raster pixel is then checked for validity:

- Pixel centers inside study rectangle: **8,514,759**.
- Valid elevations: **8,514,759 (100%)**.
- Source-tile NoData pixels inside rectangle: **0**.
- Uncovered study pixel centers: **0**.

The rectangle remains a project extraction extent, not an official district boundary. Pixel validity establishes data availability at this raster resolution; it does not establish survey precision, present-day conditions or centimeter-scale curb geometry.

Generated evidence:

- `data/heights/dem/manifest.json` — source/validation/coverage/seam report.
- `data/heights/dem/study_valid_pixels.npz` — exact `valid`, `source_covered` and `inside_study` masks, plus source grid origin/pixel size/EPSG. These arrays are not terrain activation.
- `data/heights/dem/study_valid_pixels.png` — same grid: green valid elevations, red source NoData, gray missing source tile, white outside extraction rectangle. The current study area is entirely green.

## Adjacency, overlaps and seams

The tiles form two columns and three rows with **seven adjoining edges**. All tile origins align to the common 2.5-foot pixel lattice. No duplicate overlapping valid pixels were encountered within the study mosaic; overlap checks nevertheless preserve differences if overlapping inputs occur.

Each adjacent edge has **2,000 valid pixel pairs**. Raw differences between neighboring centers include genuine terrain slope. The seam screen therefore also subtracts the mean of the immediately neighboring interior slopes and reports signed median, 95th-percentile absolute and maximum absolute residuals.

| Adjacent pair | Median residual (m) | 95th-percentile absolute residual (m) |
|---|---:|---:|
| DEM257172 → DEM257173 | 0.00000 | 0.03307 |
| DEM257172 → DEM257472 | 0.00000 | 0.04349 |
| DEM257173 → DEM257473 | 0.00027 | 0.05441 |
| DEM257472 → DEM257473 | approximately 0 | 0.03279 |
| DEM257472 → DEM257772 | -0.0000035 | 0.05617 |
| DEM257473 → DEM257773 | 0.00186 | 0.07516 |
| DEM257772 → DEM257773 | 0.00000 | 0.04492 |

All seven pass the configured **screening** triggers: absolute median residual above 0.2 m or 95th-percentile absolute residual above 0.5 m requires review. These are explicit project review triggers, not a published survey accuracy standard. The largest single residual is **0.26636 m**; no claim of perfect seams or independent vertical accuracy is made.

## Validation and downstream limits

Thirteen tests pass: cached source checksum/fetch dates, bounded streaming/partial cleanup, official-host restriction, no-network offline miss, changed acquisition and meter/foot conflicts, actual synthetic GeoTIFF geokeys/nodata, negative elevations, artificial seam shifts versus real slope, missing pairs, overlapping values and subpixel grid misalignment. A full offline replay also validates all six real tiles and regenerates the manifest/masks.

The next #6 step can reproject XY into the twin's metric local frame, convert original Z feet to meters exactly once, establish a documented vertical origin, mesh suitable terrain and re-anchor objects. That step still needs scene-composition, object-base, road/sidewalk-join and visual checks. This acquisition does not perform it.

Historical hydro-flattened bare-earth DEMs can improve terrain. They do not supply current roof forms, surveyed sidewalk slopes, curb edges or flood simulation. Source disclaimers and modification/attribution notes remain in the downloaded XML and manifest. No private BOOMS data or application snapshot was changed.

Expanded-scope replay on October 28 validated all **9,082,385 study pixel centers** for the full Main Street extraction: 100% valid, zero uncovered/NoData pixels, and zero seam review triggers. Source bytes and original fetch receipts were unchanged.
