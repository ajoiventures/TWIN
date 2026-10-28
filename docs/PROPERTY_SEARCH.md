# Property search

Implemented October 28, 2026 for the active local parcel extract. Open the [local map](http://127.0.0.1:8768/), enter an address or parcel number under **Find a property**, then select a result. The map zooms to and highlights the parcel; its inspector shows appraiser attributes, building-link evidence, permit context, zoning reference and a parcel reference coordinate.

Address matching accepts street abbreviations, reordered words and word prefixes. Exact parcel numbers rank first, followed by exact addresses; up to ten results are displayed with the total match count. Parcel numbers retain leading zeroes. OCPA's formatted `14-22-29-1478-00-150` form is also supported. Condominium unit records can share a street address, so the result's parcel number remains visible and selection uses its exact feature identity.

Search covers the loaded snapshot, not all Orange County properties. An absent result does not establish that a property is absent in the real world. Owner names are not indexed. Parcel reference coordinates are interior representative points in latitude/longitude, not surveyed entrance or building locations. The map uses projected meter coordinates for geometry. The app rejects a search response from a different snapshot and asks for a reload.

**Verification:** automated address, PIN, input-limit, no-result and pagination/snapshot tests pass. Actual browser checks covered 1615 Edgewater Drive, formatted parcel number `14-22-29-1478-00-150`, selection, coordinates, clearing and an unmatched address. [Captured browser evidence](evidence/property-search.png). Building reconstruction, current listing status and full corridor accuracy remain separate open acceptance work.

API: `GET /api/v1/parcels?q=1615%20Edgewater%20Drive&limit=10`. Filtering and ranking occur before pagination. Search reads the cached snapshot without calling an agency service per request.
