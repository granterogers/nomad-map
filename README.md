# Nomad Radar

**Where in the world is genuinely good for digital nomads right now?**

Nomad Radar is a live, finely grained world heat map of current digital-nomad,
international and community activity. It is a *discovery engine*, not a city
comparison tool: you do not tell it where to look. It starts from the entire
world, measures what it can actually observe, and shows you where the evidence
is — down to the individual neighbourhood-scale H3 hexagon where the data
supports that precision, and no finer.

It runs on zero credentials. There is no API key, no login, no database to
provision, and no ongoing cost.

**Live:** https://granterogers.github.io/nomad-map/ — **v2.0.0**

Also published as a Claude Artifact (private link):
https://claude.ai/artifact/U1zBkXMyuS5yJx6gF6HnKd

## What it answers

- *Where on Earth is active right now?* — the world map, on open.
- *Which part of this city should I actually stay in?* — contiguous hotspot
  clusters of hot H3 cells inside a city, named only by what is really there.
- *Is this famous place actually lively, or just famous?* — historical
  reputation contributes nothing to the score, and places that coast on
  reputation are explicitly flagged.
- *How much should I believe this?* — every score carries a separate
  confidence, an evidence trail, and an honest list of what could not be seen.

## Quick start

```bash
pip install h3
./build.sh                            # the whole pipeline, ~45 min cold
```

To publish:

```bash
NOMAD_SHIP_SCALE=2 ./build.sh         # Pages-sized build (100 MB ceiling)
./deploy-pages.sh                     # force-push dist/ to the gh-pages branch
```

`build.sh` runs the steps below in order. Every one is independently
re-runnable and cached, so a step can be run on its own; a failing source
degrades that source's contribution and nothing else.

| Step | What it does | Cold time |
|---|---|---|
| `probe_sources.py` | source feasibility audit | ~2 min |
| `step1_geobase.py` | world place universe + Wikipedia crosswalk | ~4 min |
| `step1b_locallang.py` | local-language Wikipedia crosswalk, 22 editions | ~4 min |
| `step2_attention.py` | live attention from Wikimedia dumps | ~14 min |
| `step2b_tier0.py` | coarse global pass + scan allocation | ~1 min |
| `step3_ecosystem.py` | global OSM ecosystem via QLever | ~2.5 min |
| `step3b_baseline.py` | OSM mapping-density baseline | ~5 min |
| `step4_events.py` | live public event listings | ~10 min |
| `step4b_venuefeeds.py` | coworking venue feeds | ~3 min |
| `step5_community.py` | community velocity feeds | ~12 min |
| `step5b_viability.py` | cost, climate and visa | ~35 min |
| `step6_h3.py` | H3 indexing, clustering, scoring | ~2 min |
| `step6c_auditstats.py` | validity statistics for the in-app report | <1 min |
| `step6d_nomadfit.py` | Nomad Fit, fitted on a held-out split | <1 min |
| `step7_artifacts.py` | precomputed web artifacts | ~1 min |
| `step8_build.py` | single self-contained HTML page | <1 min |
| `tests/test_pipeline.py` | test suite | <1 min |

The GeoNames dumps `step1_geobase.py` needs are downloaded automatically, so a
clean checkout builds without any manual setup.

## Documentation

| File | What is in it |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline shape and why it is a build-time pipeline plus a static page |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | Full feasibility audit: what works, what is blocked, what was rejected |
| [SCORING.md](docs/SCORING.md) | Every metric, weight and warning rule |
| [GEOSPATIAL.md](docs/GEOSPATIAL.md) | Projection, attribution, precision handling |
| [H3_MODEL.md](docs/H3_MODEL.md) | Resolutions, roll-ups, clustering, performance |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | How it is published and why |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each version |
| [HANDOVER.md](docs/HANDOVER.md) | Current status, coverage, limitations, next steps |
| [AGENTS.md](AGENTS.md) | Notes for the next agent working on this |

## Honesty rules the code enforces

- City-level evidence is never promoted to a neighbourhood claim. Community
  posts and events without a mapped venue are counted for the locality and are
  given no H3 cell at all.
- Nomad *population* is never invented. Presence is a band with a confidence,
  not a fabricated headcount.
- Sources that are blocked or credential-walled contribute exactly zero and are
  listed as contributing zero, in the UI, per place.
- Nothing is called LIVE unless its supporting evidence is under 24 hours old.

## Licences of the underlying data

OpenStreetMap contributors (ODbL) · GeoNames (CC-BY 4.0) · Wikimedia
pageview dumps and Wikidata (CC0) · public schema.org event listings.
