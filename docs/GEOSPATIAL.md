# Geospatial model

## Administrative hierarchy

Places come from the GeoNames `cities5000` gazetteer: ~69,000 populated places
of 5,000+ people across 210 countries and territories, each with coordinates,
population, elevation, timezone and admin codes. Country and first-level admin
names come from GeoNames' `countryInfo` and `admin1CodesASCII`.

Levels are represented generically — `admin_level_0` (country),
`admin_level_1` (state/province/region/prefecture — whatever the country calls
it), locality — rather than assuming every country is country → state → county
→ city. Where a country has no meaningful admin-1 for a place, the locality
simply rolls straight up to the country.

Administrative geography is used for **context and navigation only**. It is
never the finest unit of analysis; H3 is.

## Projection

One Web Mercator pixel space, 65,536 px wide, clamped to ±82° latitude. Country
outlines are projected into a 2,048-px reference space (the client scales them
by 32) and every H3 cell boundary is projected into the full-resolution space.
The client's only geometry work is a linear pan/zoom transform.

Country outlines are simplified at build time: coordinates are quantised,
consecutive duplicate points are dropped, and rings whose projected area falls
below a threshold are discarded — which removes thousands of unrenderable
islets without changing anything visible.

## Signal attribution

Every OSM object arrives with its own coordinates, so it needs no geocoding. It
is attributed to the nearest GeoNames locality using a 0.25° bucket grid, with a
population-scaled reach: 6 km for a small town, up to 24 km for a metropolis of
over 1.5 million. Objects with no locality inside reach are not attributed to
anything — they are not force-fitted to a distant city.

Events carry a venue name and street address. Where a source supplies real
coordinates they are used and the evidence is marked **point** precision.
Otherwise the event keeps **locality** precision and receives no H3 cell.
Coordinates are never invented from an address string.

Community posts are attributed by whole-word city-name matching against
distinctive names (five characters or more, not common English words),
resolved to the largest claimant. This is coarse and is recorded as
**locality** precision, always.

## Precision ladder

| Precision | Source | H3 cell? |
|---|---|---|
| point | OSM object, or an event with real coordinates | yes, res 8 |
| locality | event with only a city, community post, attention series | **no** |

The map only ever draws point-precision evidence. Locality-precision evidence
moves a city's score and is visible in its evidence list, but never places a
hexagon anywhere.

## Coastal and elevation classification

"Coastal" is derived by testing a locality against a 0.5° bucket grid built from
every country-outline vertex on Earth — outlines are overwhelmingly coastline.
Elevation comes from GeoNames' digital elevation model field; "high altitude"
is 700 m and above. Both feed the coast/peaks rankings and the terrain filter.

## Known limitations

- Coastal classification is approximate at 0.5° buckets: a place a few
  kilometres inland may register as coastal.
- Community-post attribution cannot distinguish two same-named places when the
  smaller one is meant.
- Nominatim is available and verified but is not used at scale: at its one
  request per second policy limit, reverse-geocoding every cluster would take
  longer than the entire rest of the pipeline, for a cosmetic gain the product
  deliberately refuses to make (it will not print a neighbourhood name it
  cannot stand behind).
