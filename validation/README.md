# Validation

`reference_set.json` is a hand-labelled set of 129 places, tiered by how
established each is as a digital-nomad destination. It exists because before it
there was no number that said whether a model change made the index better or
worse — which is why the first validity audit had to be done by hand.

## The rule

**Nothing in the pipeline may be tuned to maximise these numbers.** The moment a
weight is chosen because it improves the score here, the score stops measuring
anything. Changes should be justified by a stated principle (specificity,
normalisation, corroboration); the reference set then tells you whether the
principle helped. If you find yourself iterating against it, stop.

## Why negative controls matter most

35 of the 129 entries are tier 0: large, thoroughly mapped cities with no
particular nomad reputation — Brussels, Milan, Bradford, Essen, Nagoya. They are
the entries that catch the failure mode this index is most prone to: measuring
urban infrastructure and OSM mapping completeness rather than nomad activity. A
model that ranks those highly is broken no matter how good the rest looks.

## Metrics

| Metric | Meaning | Target |
|---|---|---|
| Spearman(tier, score) | Does the ordering match human judgement? | > 0.55 |
| AUC hub vs control | Chance a tier-3 hub outranks a tier-0 control | > 0.85 |
| Precision @ 30 | Share of the top 30 that are tier 2 or 3 | > 0.80 |
| Negative controls in top 30 | Count of tier-0 entries near the top | ≤ 2 |

```bash
python3 validation/evaluate.py
```

## Limits of this instrument

The labels are one person's judgement, made from general knowledge of the nomad
community, not a survey. They are a sanity check against gross failure, not
ground truth. A model that scores well here can still be wrong; a model that
scores badly here is definitely wrong.
