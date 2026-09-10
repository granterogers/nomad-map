# H3 model

## Why H3

Administrative geography answers "where is this?"; it cannot answer "where
exactly is the activity?", because activity does not respect municipal
boundaries and municipalities differ wildly in size. H3's hexagonal hierarchy
gives equal-area-ish cells at every scale, cheap parent/child roll-up, and
`grid_disk` neighbour queries — which is exactly what contiguous hotspot
clustering needs. Library: `h3-py` 4.5.0 (build time only).

## Resolutions

| Res | Edge | Role |
|---|---|---|
| 8 | ~0.46 km | **Fine resolution.** Every point-precision signal is indexed here first. Neighbourhood/street scale. |
| 7 | ~1.2 km | Neighbourhood clusters |
| 6 | ~3.2 km | City districts |
| 5 | ~8.5 km | Metropolitan areas |
| 4 | ~22.6 km | Regions |
| 3 | ~60 km | Country interiors, corridors |
| 2 | ~158 km | Global hotspots |

## Resolution by zoom

The map replaces coarse parent cells with finer child cells as you zoom; it
never simply enlarges big hexagons.

| Slippy zoom | Res |
|---|---|
| < 2.6 | 2 |
| 2.6 – 3.8 | 3 |
| 3.8 – 5.0 | 4 |
| 5.0 – 6.4 | 5 |
| 6.4 – 7.8 | 6 |
| 7.8 – 9.4 | 7 |
| ≥ 9.4 | 8 |

## Aggregation

Fine cells accumulate weighted evidence per family (coworking, community,
international, social, event), an evidence count, a set of contributing source
ids, a kind histogram, and the age of the freshest signal. `cell_to_parent`
rolls every fine cell up through res 7…2; parents sum weights and counts, union
source sets, and inherit their strongest child's locality attribution so a
coarse cell is labelled by what actually dominates it.

Roll-up conserves evidence exactly — the test suite asserts that the total
evidence count is identical at every resolution.

## Hotspot clustering

Cells whose total weight clears a floor are "hot". Hot cells are grouped into
connected components using `grid_disk(cell, 1)` adjacency — a flood fill over
the hex grid. A component of one cell is not a cluster; two or more is. Each
cluster carries cell count, area, evidence volume, source count, family
breakdown, dominant venue kinds, freshest signal, score and confidence.

**Clusters are not given invented neighbourhood names.** A cluster is labelled
by its city plus its own size, and shows the real mapped objects inside it. If
the data cannot justify the name "Cais do Sodré", the product does not say it.

## Low-precision evidence

Evidence with only locality precision — a Reddit thread about a city, an event
listing with no mapped venue — is attached to the locality and assigned **no
H3 cell**. It contributes to the locality's score and never to any hexagon.
This is asserted by `TestBundle.test_no_invented_precision`.

## Performance

- Boundaries are projected once at build time and delta-encoded as integers
  (centre on a ¼-pixel grid, vertices as ⅛-pixel offsets from the centre).
- The client decodes each resolution lazily, only when a zoom level asks for it.
- Cells are kept in an x-sorted index so viewport culling is a binary search
  plus a linear slice, not a full scan.
- Cells are painted coldest-first so hot cells are never hidden by neighbours.
- Antimeridian-crossing cells are unwrapped at build time so no hexagon smears
  across the map.
- Per-resolution ship caps keep the page inside the host's 16 MB limit; the
  unpruned model stays in `data/scored.json`.

## Known limitations

- Fine cells exist only where point-precision evidence exists. Empty map area
  means "no observed evidence", not "nothing there".
- Cell momentum is inherited from its locality's attention series; there is no
  per-cell time series yet, because no per-venue time series is available
  without credentials.
- Ship caps mean the very finest resolution is present for the strongest cells
  worldwide rather than for every cell on Earth.
