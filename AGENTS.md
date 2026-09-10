# Notes for the next agent

## Environment constraints that shaped real decisions

1. **Wikimedia's REST APIs return 429 for this egress IP** — all of them
   (`wikimedia.org`, `api.wikimedia.org`, every `*.wikipedia.org`). The static
   dump server `dumps.wikimedia.org` is *not* blocked. The attention layer
   therefore stream-filters hourly pageview dumps instead of calling the API.
   Do not "fix" this by reintroducing the REST API; re-test it first.

2. **The egress relay closes tunnels that go ~6-7s without bytes.** Overpass
   sends nothing while planning a query, so any non-trivial Overpass query fails
   with a connection reset regardless of how healthy Overpass is. Measured
   throughput was ~1 successful query per minute. `qlever.dev` answers
   planet-scale SPARQL in 1-3s and is the primary ecosystem source now.
   `overpass.openstreetmap.fr` is a verified fallback (fast, 5/5 in testing);
   `overpass-api.de` is not usable from here.

3. **Reddit's JSON and OAuth APIs are 403.** The public `.rss` Atom feeds are
   not. That is the whole reason the community adapter parses Atom.

## Things that are deliberate, not oversights

- The candidate ranking normalises attention *within each country*. English
  Wikipedia is structurally biased toward anglophone places; without this the
  global top-20 fills with US suburbs. It did, before the fix.
- `leisure=sports_centre` and `amenity=community_centre` are high-volume,
  low-signal. They are kept at low weight and filtered out of the shipped map
  by the ship-time weight threshold, not dropped from the analysis.
- The shipped bundle is capped per H3 resolution. The caps exist because the
  Artifact host enforces a 16 MB page limit, not because the data is unavailable
  — `data/scored.json` holds the full unpruned model.
- Search moves the map and nothing else. It is deliberately not the
  intelligence mechanism (spec §82).

## If you extend it

- Adding a source: write an adapter that returns normalised evidence records
  and register it in `common.register()`. Everything downstream is source-
  agnostic. A source that fails must return `None`, never raise.
- Changing weights: `WEIGHTS` in `pipeline/step6_h3.py`. They are read once and
  shipped into the page, so the UI always describes the model that produced the
  numbers on screen.
- Re-running: every fetch is cached on disk under `data/cache`. Delete the
  relevant cache subtree to force a refresh; adapters are otherwise idempotent.
