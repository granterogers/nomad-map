# Validity audit

These scripts test whether Nomad Radar measures digital-nomad activity or
something else that correlates with it. They read the built pipeline outputs
directly and print their findings; nothing here is cached or precomputed.

```bash
python3 audit/audit.py    # evidence composition, confound correlations, coverage asymmetry
python3 audit/audit2.py   # OSM mapping bias, event-scan circularity, attribution error rates
python3 audit/audit3.py   # face validity vs known hubs, object spot-checks, matcher false positives
python3 audit/audit4.py   # short-name matcher bug, specificity-only counterfactual re-ranking
```

Report of the 2026-09-10 run:
https://claude.ai/code/artifact/71d9916d-1cd5-4a55-a791-8629ac0941fd

## Headline findings

| Finding | Measure |
|---|---|
| Evidence carrying no nomad-specific information | 64.2% of ecosystem weight |
| Localities resting on a single source | 93.4% |
| Localities with any nomad-targeted evidence | 7.4% |
| Top-100 localities with live event evidence | 100 / 100 |
| Event-covered places already in the top 400 beforehand | 53% (circularity) |
| Coworking mapped per 100k: France vs Indonesia | 4.06 vs 0.06 (68x) |
| Wikipedia titles that are ambiguous | 19.3% |
| Place names silenced by the <5-character matcher rule | 196 |

The dominant confound is **OpenStreetMap mapping completeness**, not the tag
mix. `audit4.py` demonstrates this: removing generic infrastructure and scoring
only on nomad-specific evidence promotes well-mapped French provincial cities
(Bordeaux, Lille, Nantes) and demotes real hubs (Las Palmas #716 → #1025). A
bias that lives inside the source cannot be reweighted away — it has to be
normalised against a mapping-density baseline, or corroborated by non-OSM
evidence.
