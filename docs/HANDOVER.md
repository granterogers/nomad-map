# Handover

> Regenerate the numbers in this file with `python3 pipeline/gen_docs.py`
> after any rebuild. Everything below reflects the current build.

## Status

Working and deployed. The world map, H3 heat layers, zoom-driven resolution
switching, sub-city hotspot clusters, rankings, filters, evidence explorer and
source-health view are all live and driven by real collected data. The test
suite passes.

## Architecture in one line

A build-time Python pipeline collects credential-free public data, indexes every
geocodable signal into H3, scores and clusters it, and emits a single
self-contained HTML page that is published as a Claude Artifact.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture and
[DEPLOYMENT.md](DEPLOYMENT.md) for why the target was chosen.

## Working data sources

| Source | Role |
|---|---|
| OpenStreetMap planet via QLever SPARQL | Point-precision ecosystem worldwide — the basis of every sub-city hotspot |
| Wikimedia hourly pageview dumps | Dated attention series → current interest and real momentum |
| Meetup + Luma public schema.org listings | Live events with organiser and venue |
| Reddit Atom, Mastodon, Lemmy, Hacker News | Community velocity at city precision |
| GeoNames + Wikidata | Place universe, admin hierarchy, Wikipedia crosswalk |

## Broken or unavailable

- **Wikimedia REST APIs** — 429 for this egress IP on every host. Worked around
  via the dump server; the capability was preserved, not dropped.
- **overpass-api.de** — 504s plus a relay timeout interaction; ~1 successful
  query/minute. Replaced by QLever. `overpass.openstreetmap.fr` is a verified
  fallback.
- **Reddit JSON and OAuth APIs** — 403. Public Atom feeds used instead.
- **Bluesky public AppView, GDELT** — 403 / 429 from here.

## Credential-walled, contributing zero

Google Places, Google Trends, Foursquare, Instagram, Facebook Groups and Events,
TikTok, WhatsApp, X, LinkedIn, InterNations, Couchsurfing, Nomads.com, AirDNA,
Coworker.com. All listed in the audit and surfaced in the UI as contributing
zero, per place.

## Known limitations

1. **Event coverage is a few hundred localities, not all of them.** Public event
   listings are fetched per place; the budget goes to the places that already
   show ecosystem evidence, with per-continent quotas. Elsewhere event activity
   reads as 0 — which the UI states as "no listings found", not as "nothing is
   happening".
2. **Community attribution is English-skewed.** The reachable community feeds
   are largely anglophone, so non-English-speaking regions are under-measured
   on that one component.
3. **Attention is English Wikipedia only.** Normalising within country removes
   most of the language bias from the ranking, but not all of it.
4. **No per-cell time series.** Cell momentum is inherited from the locality;
   spatial momentum (hotspots moving between neighbourhoods) needs successive
   builds to become measurable.
5. **Seasonality needs history.** The pipeline stores dated snapshots, but a
   single build cannot show a seasonal pattern.
6. **Ship caps.** The published page carries the strongest cells per resolution,
   not every cell on Earth. The full model is in `data/scored.json`.
7. **No coliving data.** `residential=coliving` returns zero objects worldwide —
   the tag is essentially unused in OSM. Coliving is therefore not measured.

## Next priorities

1. Broaden events beyond Meetup and Luma — public ICS and RSS calendars
   published by individual coworking spaces would raise coverage a lot, since
   the ecosystem layer already knows where those spaces are.
2. Run the pipeline repeatedly and keep the snapshots: momentum becomes far
   stronger, and seasonality and spatial momentum become possible at all.
3. Non-English community feeds, and per-language Wikipedia attention.
4. Progressive loading, so the ship caps can be lifted.

## Technical decisions worth knowing

- Attention is normalised **within country** before ranking. Without it the
  global top-20 fills with US suburbs, because English Wikipedia is biased
  toward anglophone places.
- Venues attach to the most **significant** nearby place, not the nearest one.
  Nearest-wins handed a metro's centre to whichever small suburb happened to be
  closest, and large cities looked empty.
- Cell scores blend an absolute saturation curve with a percentile rank within
  their own resolution. Absolute alone makes the world map one flat colour;
  percentile alone makes the score meaningless.
- Freshness is computed from events and community posts only. A coworking space
  mapped in OSM is infrastructure, not a live signal, and letting it count made
  every place look LIVE.
