#!/usr/bin/env bash
# Full Nomad Radar build. Every step is cached and independently re-runnable;
# a failing source degrades that source's contribution and nothing else.
set -euo pipefail
cd "$(dirname "$0")"

step() { echo; echo "=== $* ==="; }

step "0/9  source feasibility audit";      python3 pipeline/probe_sources.py
step "1/9  geographic baseline";           python3 pipeline/step1_geobase.py
step "1b/9 local-language crosswalk";      python3 pipeline/step1b_locallang.py
step "2/9  live attention (~14 min)";      python3 pipeline/step2_attention.py
step "2b/9 coarse pass + scan allocation"; python3 pipeline/step2b_tier0.py
step "3/9  global OSM ecosystem";          python3 pipeline/step3_ecosystem.py
step "3b/9 OSM mapping-density baseline";  python3 pipeline/step3b_baseline.py
step "4/9  public event listings";         python3 pipeline/step4_events.py
step "4b/9 coworking venue feeds";         python3 pipeline/step4b_venuefeeds.py
step "5/9  community velocity";            python3 pipeline/step5_community.py
step "6/9  H3 model + scoring";            python3 pipeline/step6_h3.py
# viability needs step6's locality list; Nomad Fit (6d) then needs viability.
step "5b/9 structural viability";          python3 pipeline/step5b_viability.py
step "6c/9 audit statistics";              python3 pipeline/step6c_auditstats.py
step "6d/9 Nomad Fit";                     python3 pipeline/step6d_nomadfit.py
step "6b/9 validation against reference set"; python3 validation/evaluate.py build | head -12
step "7/9  web artifacts";                 python3 pipeline/step7_artifacts.py
step "8/9  self-contained page";           python3 pipeline/step8_build.py
step "9/9  documentation";                 python3 pipeline/gen_docs.py

step "TESTS"
python3 tests/test_pipeline.py 2>&1 | tail -3

step "VALIDITY AUDIT"
python3 audit/audit.py  2>/dev/null | sed -n '/nomad-specific weight/,+3p'
python3 audit/audit2.py 2>/dev/null | sed -n '/CIRCULARITY/,+5p'

echo
echo "Build complete: dist/nomad-radar.html"
echo "  Artifact (16MB ceiling): publish dist/nomad-radar.html"
echo "  GitHub Pages (100MB):    NOMAD_SHIP_SCALE=2 ./build.sh && ./deploy-pages.sh"
