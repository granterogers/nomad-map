# Architecture

## Shape

Nomad Radar is a **build-time intelligence pipeline** that emits a **single
self-contained page**. There is no application server, no database to
provision, and no runtime API call from the browser.

```
SOURCE FEASIBILITY AUDIT        probe_sources.py
        │
GEOGRAPHIC BASELINE             step1_geobase.py     GeoNames + Wikidata crosswalk
        │
LIVE ATTENTION                  step2_attention.py   Wikimedia hourly pageview dumps
        │
TIER-0 COARSE GLOBAL PASS       step2b_tier0.py      scan-budget allocation
        │
┌───────┴────────┬───────────────┬──────────────────┐
ECOSYSTEM        EVENTS          COMMUNITY          (adapters, independent)
step3            step4           step5
QLever/OSM       Meetup+Luma     Reddit/Mastodon/Lemmy/HN
└───────┬────────┴───────────────┴──────────────────┘
        │  normalize → geocode → H3 → dedupe → classify → evidence
H3 SPATIAL MODEL                step6_h3.py
  fine cells (res 8) → parents (res 7..2)
  contiguous hotspot clustering
  locality scoring + confidence + warnings
  admin roll-ups preserving max & concentration
        │
PRECOMPUTED WEB ARTIFACTS       step7_artifacts.py   projection + delta encoding
        │
SINGLE HTML PAGE                step8_build.py
```

## Why this shape

The spec required a live public URL with **zero user intervention and zero
secrets**. Every persistent-server option available here (managed Postgres,
Supabase, a hosted queue, scheduled workers) needs an account, a project or a
key that only the user can create. A static, fully self-contained page needs
none, and the Artifact host is already authorised in this environment.

Spec §53 explicitly permits this trade, and it is the right one: the user gets a
working autonomous system instead of an architecture that stalls on a signup
form. The intelligence is not weakened by it — all the discovery, H3
aggregation, clustering and scoring still happen; they happen at build time and
ship precomputed.

## Consequences and how they are handled

| Consequence | Handling |
|---|---|
| No server to compute on demand | Every H3 level, cluster and ranking is precomputed and shipped |
| No map tile server (the host's CSP blocks external images) | Country outlines and every hexagon boundary are projected at build time into one pixel space and drawn on canvas |
| No H3 library in the browser | Cell boundaries are computed by `h3-py` at build time and delta-encoded; the client needs no H3 code |
| 16 MB page limit | Ship-time pruning by evidence weight, per-resolution caps, and a keyless wire format the client expands |
| Refresh is a rebuild | Every fetch is cached with a TTL, so a rebuild only re-fetches what expired |

## Adapter contract

Each source adapter implements discover → fetch → normalize → validate →
geocode → signals, and **fails independently**. `pipeline/common.py` provides
retries with jittered exponential backoff, per-host rate limiting, circuit
breakers, on-disk gzip caching, and a persistent source registry with
reliability tracking. An adapter that cannot reach its source returns `None`;
the world scan continues and the UI reports that source as contributing zero.

## Refresh policy

Cache TTLs encode the intended refresh cadence (spec §41): community feeds 6 h,
event listings 2 d, OSM ecosystem 5 d, the Wikidata crosswalk 14 d, the
geographic baseline effectively never. Re-running the pipeline refreshes only
what has expired.
