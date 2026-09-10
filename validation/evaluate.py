"""Evaluate the index against the held-out reference set.

This is the instrument that turns "is it working?" from an opinion into a
number. Run it on every build; a change that lowers these numbers is a
regression regardless of how sensible it looked.

RULE: nothing in the pipeline may be tuned to maximise these numbers. The
reference set is a measurement, not a training signal.
"""
import json, math, os, sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v); i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs); mx = sum(rx) / n; my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def auc(pos, neg):
    """Probability a random tier-3 place outranks a random tier-0 place."""
    if not pos or not neg:
        return float("nan")
    wins = sum(1 for a in pos for b in neg if a > b) + \
           0.5 * sum(1 for a in pos for b in neg if a == b)
    return wins / (len(pos) * len(neg))


def evaluate(scored_path=None, quiet=False):
    ref = json.load(open(os.path.join(ROOT, "validation", "reference_set.json")))
    sc = json.load(open(scored_path or os.path.join(ROOT, "data", "scored.json")))
    L = sc["localities"]
    by = {}
    for x in L:
        by.setdefault((x["name"], x["cc"]), x)
    ranked = sorted(L, key=lambda z: -z["live_score"])
    rank_of = {(x["name"], x["cc"]): i + 1 for i, x in enumerate(ranked)}

    rows, missing = [], []
    for name, cc, tier in ref["places"]:
        x = by.get((name, cc))
        if not x:
            missing.append(f"{name}({cc})")
            continue
        rows.append({"name": name, "cc": cc, "tier": tier,
                     "score": x["live_score"], "rank": rank_of[(name, cc)],
                     "conf": x["confidence"], "ev": x["evidence_count"],
                     "srcs": x["unique_sources"]})

    tiers = defaultdict(list)
    for r in rows:
        tiers[r["tier"]].append(r["score"])
    rho = spearman([r["tier"] for r in rows], [r["score"] for r in rows])
    a = auc(tiers[3], tiers[0])
    top30 = sorted(rows, key=lambda r: r["rank"])[:30]
    precision = sum(1 for r in top30 if r["tier"] >= 2) / max(len(top30), 1)
    controls_in_top = sum(1 for r in top30 if r["tier"] == 0)

    res = {
        "n_evaluated": len(rows), "n_missing": len(missing), "missing": missing,
        "spearman_tier_vs_score": round(rho, 3),
        "auc_hub_vs_control": round(a, 3),
        "precision_at_30": round(precision, 3),
        "negative_controls_in_top_30": controls_in_top,
        "median_score_by_tier": {str(t): sorted(v)[len(v) // 2] for t, v in sorted(tiers.items()) if v},
        "rows": rows,
    }
    if not quiet:
        print(f"reference places matched : {len(rows)}/{len(ref['places'])}"
              + (f"  (missing: {', '.join(missing[:6])})" if missing else ""))
        print(f"\n  Spearman(tier, score)        {rho:+.3f}   "
              f"{'GOOD' if rho > .6 else 'WEAK' if rho > .35 else 'POOR'}   (1.0 = perfect ordering)")
        print(f"  AUC hub(3) vs control(0)     {a:.3f}   "
              f"{'GOOD' if a > .85 else 'WEAK' if a > .7 else 'POOR'}   (0.5 = coin flip)")
        print(f"  Precision@30 (tier>=2)       {precision:.3f}")
        print(f"  Negative controls in top 30  {controls_in_top}   (lower is better)")
        print(f"\n  median score by tier: " +
              "  ".join(f"tier {t}={s}" for t, s in sorted(res['median_score_by_tier'].items(), reverse=True)))
        print(f"\n  {'place':30} {'tier':>4} {'score':>6} {'rank':>6} {'conf':>5} {'src':>4}")
        for r in sorted(rows, key=lambda r: r["rank"])[:16]:
            flag = "  <-- NEGATIVE CONTROL" if r["tier"] == 0 else ""
            print(f"  {r['name'][:29]:30} {r['tier']:>4} {r['score']:>6} {r['rank']:>6} "
                  f"{r['conf']:>5} {r['srcs']:>4}{flag}")
        print("  ...")
        worst = [r for r in sorted(rows, key=lambda r: -r["rank"]) if r["tier"] == 3][:8]
        print(f"\n  worst-placed tier-3 hubs:")
        for r in worst:
            print(f"  {r['name'][:29]:30} {r['tier']:>4} {r['score']:>6} {r['rank']:>6} "
                  f"{r['conf']:>5} {r['srcs']:>4}")
    return res


def append_history(res, label=""):
    """Keep a regression log so model changes stay accountable across builds."""
    hp = os.path.join(ROOT, "validation", "history.json")
    h = json.load(open(hp)) if os.path.exists(hp) else {"builds": []}
    sc = json.load(open(os.path.join(ROOT, "data", "scored.json")))
    entry = {
        "build": __import__("time").strftime("%Y-%m-%dT%H:%MZ", __import__("time").gmtime()),
        "label": label or "build",
        "spearman_tier_vs_score": res["spearman_tier_vs_score"],
        "auc_hub_vs_control": res["auc_hub_vs_control"],
        "precision_at_30": res["precision_at_30"],
        "negative_controls_in_top_30": res["negative_controls_in_top_30"],
        "ranked_localities": sum(1 for L in sc["localities"] if L.get("ranked")),
        "notes": "",
    }
    prev = h["builds"][-1] if h["builds"] else None
    h["builds"].append(entry)
    json.dump(h, open(hp, "w"), indent=1)
    if prev:
        d = entry["spearman_tier_vs_score"] - prev["spearman_tier_vs_score"]
        da = entry["auc_hub_vs_control"] - prev["auc_hub_vs_control"]
        print(f"\n  vs previous build ({prev['label']}): "
              f"Spearman {d:+.3f}, AUC {da:+.3f}"
              + ("   REGRESSION" if d < -0.02 or da < -0.02 else ""))


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else ""
    r = evaluate()
    json.dump(r, open(os.path.join(ROOT, "data", "validation_result.json"), "w"), indent=1)
    if label:
        append_history(r, label)
