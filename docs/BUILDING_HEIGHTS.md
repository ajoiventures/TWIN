# Building height evidence

The connected scene now composes `scene/building_heights.usda` over the original geometry. Base geometry and manual edits remain in independent layers. Height records are saved locally in `data/heights/building_heights.json`; quality totals are in `height_quality.json`.

## Current result

- 3,090 building groups evaluated.
- 90 historical LiDAR-derived heights in the central pilot area.
- 3,000 explicitly labeled floor-count estimates elsewhere or where LiDAR fails checks.
- 976 heights changed from the earlier uniform 4.2/6.5 m masses.
- Applied heights range from 3.14 to 12.64 m after outlier checks.

## Sources and units

1. OCPA public footprint subareas provide `FLOOR_NUM` records linked through source object IDs to each prototype building group.
2. The official OCPA parcel snapshot provides `STYS`. It is used only for an accepted ID-plus-geometry parcel match with one building group, and large conflicts with building-level floor records are queued rather than applied.
3. The [USGS Orange County EPT point cloud documented by NOAA](https://www.fisheries.noaa.gov/inport/item/69496/full-list) supplies classified ground (2) and building (6) points. The project metadata describes acquisition from December 4, 2018 through April 12, 2019. The pilot covers longitude -81.391 to -81.387 and latitude 28.570 to 28.574. Only intersecting EPT nodes are downloaded, through depth 10.

The original project metadata uses US survey feet, but the streamed EPT elevations are in meters. Three independent [USGS ground-elevation queries](https://www.usgs.gov/the-national-map-data-delivery/gis-data-download) were compared with nearby classified EPT ground points. The median discrepancy under the meter hypothesis was approximately 0.013 m; interpreting the same values as feet produced approximately 21.9 m discrepancy. This establishes a unit sanity check, not independent survey-grade accuracy, because the products may share elevation source data. The point metadata and unit-check responses remain in the local cache.

## Height methods

**Historical LiDAR-derived:** roof elevation is the 95th percentile of classified building points inside the footprint eroded by 0.4 m. Local ground is the median of nearby classified ground points. At least 30 roof points, 12 ground points within 35 m, and one roof point per square meter are required. Height, roof spread, and consistency with reported floors are checked. Footprints must lie wholly inside the pilot area. Buildings with a parcel year-built newer than 2019 do not inherit the old roof measurement.

**Floor-count estimate:** residential height is `floors × 3.0 m + 1.2 m roof allowance`; commercial height is `floors × 3.6 m + 0.7 m parapet allowance`. These are modeling assumptions, not measured heights. Footprint floor records and parcel stories retain their separate provenance. Parcel stories are not copied onto every structure on a multi-building parcel. An extreme parcel/building count conflict remains a review case.

All values retain method, quality, source snapshot, source floor values, LiDAR sample count and review notes. Roof surfaces move with the corresponding mass. Generic parapet caps are moved to the new roof height; incompatible generic storefront detail is hidden on unusually low buildings.

## Limits

The pilot LiDAR is historical and covers only part of the neighborhood. No current survey or property-by-property roof-form verification has been completed. Building groups may contain disconnected accessory structures; a single group height is approximate. The scene still uses flat ground, so this layer improves above-ground massing without claiming surveyed terrain elevations or roof shapes.

Run `python tools/height_probe.py`, `python tools/sample_lidar.py`, `python tools/validate_vertical_units.py`, `python tools/build_heights.py`, then `python tools/connect_scene.py`. The large raw LAZ download is optional and was not required for the EPT workflow. Source caches and generated height data are ignored by Git. API routes: `/api/v1/heights`, `/api/v1/height_quality`; building responses expose the applied height, method and quality when the source snapshot matches.
