# Handover

> Regenerate the numbers in this file with `python3 pipeline/gen_docs.py`
> after any rebuild. Everything below reflects the current build.

## Live URL

**https://claude.ai/code/artifact/dac9fc4c-ac07-4b44-bcbc-da2fe2efaf5c**

Published as a Claude Artifact (private to the owner until shared from the
page's share menu). Republishing `dist/nomad-radar.html` updates the same URL.

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

## Validity — what is measured and how well

The index is measured against a **held-out reference set** of 129 hand-labelled
places (`validation/`), including 35 negative controls: large, thoroughly mapped
cities with no nomad reputation. Run `python3 validation/evaluate.py` for current
numbers; `validation/history.json` is the regression log.

**No weight or threshold is tuned against those numbers.** See
`validation/README.md` — the moment the model is fitted to the reference set, the
reference set stops measuring anything.

### Corrections the model applies

1. **Mapping-density normalisation.** Infrastructure is scored as a share of what
   OSM has mapped locally, against 2.27M deliberately nomad-irrelevant civic
   objects (pharmacies, fuel, supermarkets, banks, hairdressers, post boxes).
   Without this the ranking mostly measured OSM completeness: France records 4.06
   mapped coworking spaces per 100k people, Indonesia 0.06.
2. **Specificity weighting.** `sports_centre` is weight 0 and not evidence at all;
   `community_centre` is 0.05. Those two tags previously carried 49% of all
   evidence weight while saying nothing about nomads.
3. **Corroboration gate.** A place is *ranked* only with two or more independent
   evidence families, at least one nomad-targeted (events or community).
   Everything else renders on the map with its evidence and an explicit
   `NOT RANKED — INFRASTRUCTURE ONLY` warning.
4. **Half the event budget is a stratified random sample** over continent x
   population band, independent of any score, so the event layer can contradict
   the infrastructure layer instead of confirming it.
5. **Coworking-space event feeds** (`step4b_venuefeeds.py`) — 1,011 of 4,139
   coworking websites recorded in OSM publish a machine-readable calendar. This
   is nomad-specific AND point-precise, so it lands in an H3 cell.
6. **Title-anchored, quote-aware, country-qualified name matching** replaced the
   5-character rule that silenced 196 place names including Ubud, Lima and Rome,
   and produced errors like crediting a post about Goa to Las Vegas.

### Three scores

**Live score** — activity only, unchanged. **Per capita** — the same activity divided by
population. **Nomad fit** — activity blended with cost, climate and visa access, which is the
score that actually correlates with human judgement (0.656 held out vs 0.315 for activity
alone, AUC 0.955 vs 0.762). See `docs/REACHING_STRONG_CORRELATION.md` for the research, and
for the ranked list of things that need your credentials to go further.

### Two activity scales

The app toggles between an **absolute** score and a **per-capita** score
(`fit_per_capita` in `step6_h3.py`). Per capita answers the "big cities win by
construction" objection, and it does surface small dense places the absolute
view buries. It also scores materially worse against the reference set, because
dividing out population amplifies the event-detection bias it cannot see. Both
sets of numbers ship into the page and are shown per scale in the Method tab.

### What is still true and worth knowing

- **Nothing observes a digital nomad directly.** Every signal is a proxy. The
  ranking is only as good as the proxies, and the honest ceiling is limited.
- **The event layer inherits some OSM bias** through `step4b`, because it is
  seeded from OSM `website` tags — well-mapped regions get more detectable feeds.
- **Local-language attention is partial.** Five editions (fr, de, pt, id, th)
  are covered; the public Wikidata endpoint times out on the largest ones. Places
  in uncovered countries are still measured on English Wikipedia alone.
- **Meetup throttles**, so the stratified random half of the event scan is
  partially complete. Re-running `step4_events.py` resumes from cache and
  extends coverage; `EVENT_BUDGET_S` bounds the run.

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
