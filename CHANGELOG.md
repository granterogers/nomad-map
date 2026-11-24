# Changelog

Versioning starts at 2.0.0, covering the project as it stood after the
September 2026 source-widening work. Each subsequent change takes the next
minor version.

The version is shown in the page footer and recorded in `data/bundle.json`
under `meta.version`, so any published build can be identified from the page
itself.

Live: https://granterogers.github.io/nomad-map/

---

## 2.0.0 — 24 November 2026

First numbered release. Rebuilt from a cold start after the build container
was recycled, which exposed four defects that made the project unbuildable or
silently degraded. All four are fixed here.

**Fixed**

- `step1_geobase.py` expected the GeoNames dumps to already exist in
  `data/raw`, which is git-ignored. They had been fetched by hand in the
  original session, so the pipeline could not run from a clean checkout at all.
  It now downloads them itself.
- The GeoNames to English Wikipedia crosswalk ran against the public Wikidata
  Query Service, which times out at this scale. Two population bands failed and
  the step exited successfully with 23,385 rows against September's 85,695,
  putting English Wikipedia titles on 9.4% of places instead of ~40% and
  quietly running the attention layer at a quarter strength. Moved to QLever's
  Wikidata index — the same fix `step1b_locallang.py` received in September —
  which answers it unbanded in under three seconds and returns 86,090 pairs.
- Circuit breakers were shared across the sources of a step, so one dead source
  silenced the rest in total silence. Reddit's public RSS feeds began returning
  404 after September; 20 of those 404s opened the breaker that
  `step5_community.py` shared across all four adapters, and Mastodon, Lemmy and
  Hacker News were never asked. The step reported "0 posts" and exited 0.
  Keying breakers per source was not enough on its own — nine Mastodon
  instances share one `source_id`, so one failing instance still cost ~9,700
  posts — so they are now keyed by host. `step5b_viability.py` had the same
  latent fault between World Bank and NASA POWER.
- `step7_artifacts.py` read `data/raw/world_countries.json`, which nothing
  downloaded: the same hand-fetched-once pattern as the GeoNames dumps. A clean
  rebuild died at step 7 after every expensive step had finished. It now
  fetches the Natural Earth 110m outlines.
- `h3` was declared only in a README prose line. `requirements.txt` now exists
  and `build.sh` preflights it, so a missing dependency costs a second rather
  than the hour of gathering that preceded the failure.
- `step5b_viability.py` reads `scored.json`, which `step6_h3.py` produces, but
  `build.sh` ran it first. On a cold build the file was simply absent and the
  step wrote an empty climate layer without erroring; the damage surfaced only
  as a worse Nomad Fit. Reordered, and it now refuses to run without its input.
- `write_json` wrote in place. Steps run concurrently and read each other's
  output, so a reader could catch a half-written file — rare, silent, and
  indistinguishable from corrupt data. Now atomic.

**Validation — the activity-only Live Score regressed, and it is not a bug**

| Live Score (activity only) | Sept 2026 | 2.0.0 |
|---|---|---|
| Spearman | +0.329 | **+0.246** |
| AUC hub vs control | 0.785 | **0.721** |
| Precision@30 | 0.800 | **0.700** |
| Negative controls in top 30 | 4 | **6** |

| Nomad Fit | Sept 2026 | 2.0.0 |
|---|---|---|
| Holdout Spearman (n=63) | +0.655 | **+0.638** |
| Holdout AUC | 0.955 | **0.937** |
| Controls in holdout top 20 | 0 | **0** |

The cause is better data, not worse code. September's event scan was throttled
partway and covered 1,011 places; this one completed inside its budget and
covered 1,807, with 28,956 events against 22,073. The places that gained most
are large, well-served Western European cities — Brussels now carries 986
evidence items, Milan 950, Toulouse 587 — and the activity-only score cannot
distinguish "many events because this is a large European city" from "many
events because nomads are here". Tier-3 hubs average 860 evidence items; those
controls rival them.

This is the confound the September validity audit already measured, surfacing
more strongly because coverage improved. Nothing was tuned in response:
`validation/README.md` forbids fitting to these numbers, and the honest record
of a build that scored worse is worth more than a build quietly adjusted until
it scored better. Nomad Fit, which blends activity with cost, climate and visa
access, is unchanged within the noise of a 63-item holdout and remains the
score that orders destinations usefully.

**Changed**

- Published to GitHub Pages from the `main` branch, alongside the existing
  Claude Artifact.
- Ship-time payload caps are now scaled by `NOMAD_SHIP_SCALE` rather than
  forked per publishing target. The Artifact host allows 16 MB per page and
  GitHub Pages allows 100 MB, so the Pages build ships roughly twice the cell
  detail and drill-down depth. It governs payload only and changes no scoring.
- NASA POWER climatology is cached between builds instead of refetched. It is a
  30-year average that cannot change, and refetching it was ~35 minutes of
  every rebuild — the slowest step in the pipeline.
- `build.sh` gained `step5b_viability`, `step6c_auditstats` and
  `step6d_nomadfit`, which it had never been updated to include; running it as
  published would have produced a build with no Nomad Fit in it.
- README quick start replaced with `build.sh` and a step table with cold
  timings. The listed sequence predated six pipeline steps.
