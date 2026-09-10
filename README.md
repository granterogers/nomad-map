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
python3 pipeline/probe_sources.py     # source feasibility audit
python3 pipeline/step1_geobase.py     # world place universe + Wikipedia crosswalk
python3 pipeline/step2_attention.py   # live attention from Wikimedia dumps  (~14 min)
python3 pipeline/step2b_tier0.py      # coarse global pass + scan allocation
python3 pipeline/step3_ecosystem.py   # global OSM ecosystem via QLever       (~2.5 min)
python3 pipeline/step4_events.py      # live public event listings            (~10 min)
python3 pipeline/step5_community.py   # community velocity feeds
python3 pipeline/step6_h3.py          # H3 indexing, clustering, scoring
python3 pipeline/step7_artifacts.py   # precomputed web artifacts
python3 pipeline/step8_build.py       # single self-contained HTML page
python3 tests/test_pipeline.py        # test suite
```

Every step is independently re-runnable and cached; a failing source degrades
that source's contribution and nothing else.

## Documentation

| File | What is in it |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline shape and why it is a build-time pipeline plus a static page |
| [DATA_SOURCES.md](docs/DATA_SOURCES.md) | Full feasibility audit: what works, what is blocked, what was rejected |
| [SCORING.md](docs/SCORING.md) | Every metric, weight and warning rule |
| [GEOSPATIAL.md](docs/GEOSPATIAL.md) | Projection, attribution, precision handling |
| [H3_MODEL.md](docs/H3_MODEL.md) | Resolutions, roll-ups, clustering, performance |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | How it is published and why |
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
