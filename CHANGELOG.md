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
- `step5b_viability.py` reads `scored.json`, which `step6_h3.py` produces, but
  `build.sh` ran it first. On a cold build the file was simply absent and the
  step wrote an empty climate layer without erroring; the damage surfaced only
  as a worse Nomad Fit. Reordered, and it now refuses to run without its input.
- `write_json` wrote in place. Steps run concurrently and read each other's
  output, so a reader could catch a half-written file — rare, silent, and
  indistinguishable from corrupt data. Now atomic.

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
