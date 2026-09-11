"""Step 6d - Nomad Fit: activity combined with structural viability.

METHODOLOGY. The blend weights are chosen on one half of the reference set and
reported on the other half, which the fitting never sees. Without that split,
choosing weights while watching the score would make the score meaningless -
the reference set would become training data. The holdout number is the honest
one and is the number the app displays.

The activity-only Live Score is left untouched. Nomad Fit is an additional
score, because "where is active" and "where would suit a nomad" are different
questions and the product should not silently answer the second while claiming
the first.
"""
import json, math, os, random, sys
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import read_json, write_json

MONTHS_N_WINTER = [11, 0, 1]        # Dec, Jan, Feb - the northern escape season


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v); i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(xs) < 3:
        return 0.0
    rx, ry = rank(xs), rank(ys)
    n = len(xs); mx = sum(rx) / n; my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def comfort(t):
    """How pleasant is a month at mean temperature t, for someone choosing where
    to spend it. Flat-topped between 18 and 27 degrees, falling away either side."""
    if t is None:
        return 0.5
    if 18.0 <= t <= 27.0:
        return 1.0
    if t < 18.0:
        return max(0.0, 1.0 - (18.0 - t) / 16.0)
    return max(0.0, 1.0 - (t - 27.0) / 10.0)


def cost_score(gdp):
    """Affordability for someone earning in a hard currency - but an inverted U,
    not "cheaper is always better".

    A monotonic curve put Lusaka and Nairobi at the top of the ranking, which is
    wrong for an obvious reason: those places are inexpensive because they are
    poor, and below a certain income level the infrastructure a remote worker
    depends on stops being reliable. The sweet spot is middle-income - roughly
    $11k-$35k GDP per capita PPP, which is where Thailand, Vietnam, Colombia,
    Mexico, Indonesia and Georgia sit - falling away both above and below."""
    if not gdp:
        return 0.5
    g = math.log10(gdp)
    lo, hi = 4.05, 4.55          # ~$11k .. ~$35k
    if lo <= g <= hi:
        return 1.0
    if g < lo:
        return max(0.0, 1.0 - (lo - g) / 0.45)      # too poor: infrastructure risk
    return max(0.0, 1.0 - (g - hi) / 0.42)          # too expensive


def viability_parts(L, via):
    gdp = via["cost_gdp_ppp"].get(L["cc"])
    cost = cost_score(gdp)
    visa = 1.0 if L["cc"] in set(via["visa_countries"]) else 0.0
    temps = via["climate_monthly_c"].get(str(L["gid"]))
    if temps:
        annual = sum(comfort(t) for t in temps) / 12.0
        winter = sum(comfort(temps[m]) for m in MONTHS_N_WINTER) / 3.0
        clim = 0.55 * annual + 0.45 * winter
    else:
        clim = 0.5
    return {"cost": round(cost, 4), "visa": visa, "climate": round(clim, 4),
            "gdp_ppp": gdp, "temps": temps}


def main():
    sc = read_json("scored.json")
    via = read_json("viability.json")
    if not via:
        print("no viability.json - skipping Nomad Fit"); return
    L = sc["localities"]
    for x in L:
        x["viability"] = viability_parts(x, via)

    ref = json.load(open(os.path.join(common.ROOT, "validation", "reference_set.json")))["places"]
    by = {(x["name"], x["cc"]): x for x in L}
    rows = [(n, c, t, by[(n, c)]) for n, c, t in ref if (n, c) in by]

    # stratified 50/50 split, fixed seed: fit on one half, report on the other
    rng = random.Random(20260911)
    byt = {}
    for r in rows:
        byt.setdefault(r[2], []).append(r)
    fit, hold = [], []
    for t, group in byt.items():
        g = group[:]; rng.shuffle(g)
        fit += g[::2]; hold += g[1::2]

    def blend(x, w):
        v = x["viability"]
        a = x["live_score"] / 100.0
        return (w[0] * a + w[1] * v["cost"] + w[2] * v["climate"] + w[3] * v["visa"])

    best, bw = -2, None
    grid = [i / 20 for i in range(0, 21)]
    for wa in grid:
        for wc in grid:
            for wk in grid:
                wv = 1 - wa - wc - wk
                if wv < -1e-9 or wv > 0.30:
                    continue
                w = (wa, wc, wk, max(wv, 0.0))
                r = spearman([t for _, _, t, _ in fit], [blend(x, w) for _, _, _, x in fit])
                if r > best:
                    best, bw = r, w
    def auc(pos, neg):
        if not pos or not neg:
            return float("nan")
        return (sum(1 for a in pos for b in neg if a > b)
                + 0.5 * sum(1 for a in pos for b in neg if a == b)) / (len(pos) * len(neg))
    hold_rho = spearman([t for _, _, t, _ in hold], [blend(x, bw) for _, _, _, x in hold])
    hold_auc = auc([blend(x, bw) for _, _, t, x in hold if t == 3],
                   [blend(x, bw) for _, _, t, x in hold if t == 0])
    hold_auc_act = auc([x["live_score"] for _, _, t, x in hold if t == 3],
                       [x["live_score"] for _, _, t, x in hold if t == 0])
    hold_controls = sum(1 for r in sorted(hold, key=lambda r: -blend(r[3], bw))[:20] if r[2] == 0)
    all_rho = spearman([t for _, _, t, _ in rows], [blend(x, bw) for _, _, _, x in rows])
    act_hold = spearman([t for _, _, t, _ in hold], [x["live_score"] for _, _, _, x in hold])

    print(f"fit half n={len(fit)}  holdout n={len(hold)}")
    print(f"chosen weights  activity {bw[0]:.2f} · cost {bw[1]:.2f} · "
          f"climate {bw[2]:.2f} · visa {bw[3]:.2f}")
    print(f"  fit-half rho      {best:+.3f}   (weights were chosen on this - not the honest number)")
    print(f"  HOLDOUT rho       {hold_rho:+.3f}   <- the honest number")
    print(f"  HOLDOUT AUC       {hold_auc:.3f}   (activity only {hold_auc_act:.3f})")
    print(f"  activity-only on the same holdout {act_hold:+.3f}")
    print(f"  whole reference set {all_rho:+.3f}")

    # Scale against the RANKED population, not all 35k localities: most of those
    # are infrastructure-only with near-zero activity, which compressed every real
    # destination into the top of the range and saturated the leaders at 100.
    pool = [x for x in L if x.get("ranked")] or L
    vals = sorted(blend(x, bw) for x in pool)
    lo, hi = vals[int(len(vals) * 0.02)], vals[min(len(vals) - 1, int(len(vals) * 0.995))]
    hi = hi + (hi - lo) * 0.06          # headroom so the very best are not all 100
    for x in L:
        raw = blend(x, bw)
        x["nomad_fit"] = int(round(max(0, min(100, 100 * (raw - lo) / max(hi - lo, 1e-6)))))
    for x in L:                      # ship compactly: the parts, not the raw series
        v = x.pop("viability", {})
        x["viab"] = [round(v.get("cost", .5), 3), round(v.get("climate", .5), 3),
                     int(v.get("visa", 0)), round((v.get("gdp_ppp") or 0) / 1000, 1)]
        t = v.get("temps")
        x["temps"] = [int(round(z)) for z in t] if t else None
    write_json("scored.json", sc)
    write_json("nomadfit_meta.json", {
        "generated_at": common.iso(),
        "weights": {"activity": bw[0], "cost": bw[1], "climate": bw[2], "visa": bw[3]},
        "fit_n": len(fit), "holdout_n": len(hold),
        "fit_rho": round(best, 3), "holdout_rho": round(hold_rho, 3),
        "holdout_auc": round(hold_auc, 3),
        "activity_only_holdout_rho": round(act_hold, 3),
        "activity_only_holdout_auc": round(hold_auc_act, 3),
        "holdout_controls_in_top20": hold_controls,
        "all_reference_rho": round(all_rho, 3),
        "visa_as_of": via["visa_as_of"], "sources": via["sources"],
    })
    print("wrote nomad_fit into scored.json")


if __name__ == "__main__":
    main()
