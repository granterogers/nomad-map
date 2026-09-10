"""Step 2b - Tier 0 global coarse pass + adaptive scan allocation (spec §14-§16, §34, §66).

Scores all ~34k populated places on cheap signals (population + live Wikipedia
attention + momentum), then allocates the expensive Overpass budget by
*potential and uncertainty*, not by score alone:

  - merit slots      : highest coarse score
  - momentum slots   : fastest-rising attention regardless of absolute size
  - uncertainty slots: plausible upside but thin evidence (spec §15, §34)
  - diversity slots  : per-continent and per-country floors so discovery is
                       not structurally Euro-centric

No destination list is hard-coded. Which places get deep-scanned is derived.
"""
import math, os, sys, random
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import read_json, write_json

TIER3, TIER2, TIER1 = 110, 210, 430          # deep / medium / shallow scan budgets
MOMENTUM_SHARE, UNCERTAIN_SHARE = 0.14, 0.10
MIN_PER_CONTINENT, MIN_PER_COUNTRY = 22, 1
MAX_PER_COUNTRY, MAX_PER_ADMIN1 = 26, 7
MIN_ABS_ATTENTION = 8.0                      # views/day floor before merit selection


def lg(x):
    return math.log10(max(x, 1.0))


def main():
    gb = read_json("geobase.json")
    att = read_json("attention.json", {"places": {}})["places"]
    places = gb["places"]

    # normalisers
    views = [v["daily_avg"] for v in att.values() if v["daily_avg"] > 0]
    views.sort()
    p95 = views[int(len(views) * 0.95)] if views else 1.0

    # The attention source is English Wikipedia, which is structurally biased
    # toward anglophone places. Rank attention-per-capita *within each country*
    # so a place competes against its own national baseline, not against the
    # advantage its language gives it (spec §29, §60).
    percap = {}
    for p in places:
        a = att.get(str(p["gid"]))
        d = a["daily_avg"] if a else 0.0
        percap[p["gid"]] = d / max(p["pop"] / 100000.0, 0.35)
    by_country = defaultdict(list)
    for p in places:
        by_country[p["cc"]].append(percap[p["gid"]])
    country_rank = {}
    for cc, vals in by_country.items():
        vals.sort()
        n = len(vals)
        for p in places:
            pass
    rank_lookup = {}
    for cc, vals in by_country.items():
        rank_lookup[cc] = vals
    import bisect
    for p in places:
        vals = rank_lookup[p["cc"]]
        country_rank[p["gid"]] = bisect.bisect_left(vals, percap[p["gid"]]) / max(len(vals) - 1, 1)

    scored = []
    for p in places:
        a = att.get(str(p["gid"]))
        daily = a["daily_avg"] if a else 0.0
        mom = (a or {}).get("momentum_ratio")
        pop_s = min(lg(p["pop"]) / 7.0, 1.0)                 # 10M -> 1.0
        att_s = min(lg(daily + 1) / lg(p95 + 1), 1.2) if daily else 0.0
        # attention per capita: small places punching above their weight
        per_cap = (daily / (p["pop"] / 100000.0)) if p["pop"] else 0
        pc_s = min(lg(per_cap + 1) / 2.6, 1.0)
        mom_s = 0.5 if mom is None else max(0.0, min((mom - 0.75) / 0.9, 1.0))

        rel_s = country_rank[p["gid"]]
        coarse = (0.30 * rel_s + 0.20 * att_s + 0.14 * pc_s + 0.22 * pop_s + 0.14 * mom_s)
        if daily < MIN_ABS_ATTENTION:
            coarse *= 0.55          # too little live signal to trust a high rank
        # confidence in the coarse estimate itself
        cov = (a or {}).get("recent_days_covered", 0)
        conf = 0.15 + 0.55 * min(cov / 14.0, 1.0) + (0.2 if a else 0.0)
        if a and a.get("ambiguous_title"):
            conf -= 0.12
        conf = max(0.05, min(conf, 0.95))
        # upside = what the score could be if we looked harder
        upside = coarse + (1 - conf) * (0.35 + 0.25 * pc_s)

        scored.append({"place": p, "coarse": round(coarse, 4), "confidence": round(conf, 3),
                       "upside": round(upside, 4), "daily_views": daily,
                       "country_attention_rank": round(rel_s, 3),
                       "momentum": mom, "per_capita_attention": round(per_cap, 2)})

    scored.sort(key=lambda x: -x["coarse"])
    total_budget = TIER3 + TIER2 + TIER1
    picked, seen = [], set()

    cc_count, a1_count = defaultdict(int), defaultdict(int)

    def take(cands, n, reason, respect_caps=True):
        c = 0
        for s in cands:
            if c >= n:
                break
            pl = s["place"]
            g = pl["gid"]
            if g in seen:
                continue
            if respect_caps:
                if cc_count[pl["cc"]] >= MAX_PER_COUNTRY:
                    continue
                a1k = (pl["cc"], pl.get("admin1", ""))
                if a1_count[a1k] >= MAX_PER_ADMIN1:
                    continue
            seen.add(g)
            cc_count[pl["cc"]] += 1
            a1_count[(pl["cc"], pl.get("admin1", ""))] += 1
            s = dict(s); s["selected_for"] = reason
            picked.append(s); c += 1
        return c

    n_mom = int(total_budget * MOMENTUM_SHARE)
    n_unc = int(total_budget * UNCERTAIN_SHARE)
    n_merit = total_budget - n_mom - n_unc

    # 1. merit
    take(scored, int(n_merit * 0.75), "merit")
    # 2. momentum: rising fast, any size, with enough coverage to be believable
    mom_pool = [s for s in scored if s["momentum"] and s["momentum"] > 1.12
                and s["daily_views"] >= 20]
    mom_pool.sort(key=lambda x: -(x["momentum"] * (0.5 + x["coarse"])))
    take(mom_pool, n_mom, "momentum")
    # 3. uncertainty: high upside, low confidence (spec §34)
    unc_pool = sorted([s for s in scored if s["confidence"] < 0.62
                       and s["daily_views"] >= MIN_ABS_ATTENTION],
                      key=lambda x: -x["upside"])
    take(unc_pool, n_unc, "uncertainty")
    # 4. geographic diversity floors (spec §60 - discovery must not be Euro-centric)
    by_cont, by_cc = defaultdict(list), defaultdict(list)
    for s in scored:
        by_cont[s["place"]["continent"]].append(s)
        by_cc[s["place"]["cc"]].append(s)
    for cont, pool in by_cont.items():
        have = sum(1 for p in picked if p["place"]["continent"] == cont)
        if have < MIN_PER_CONTINENT:
            take(pool, MIN_PER_CONTINENT - have, "continent_floor")
    for cc, pool in by_cc.items():
        have = sum(1 for p in picked if p["place"]["cc"] == cc)
        if have < MIN_PER_COUNTRY:
            take(pool, MIN_PER_COUNTRY - have, "country_floor", respect_caps=False)
    # 5. fill remaining merit slots
    take(scored, total_budget - len(picked), "merit")

    picked.sort(key=lambda x: -max(x["coarse"], x["upside"] * 0.9))
    for i, s in enumerate(picked):
        s["tier"] = 3 if i < TIER3 else (2 if i < TIER3 + TIER2 else 1)

    write_json("scan_targets.json", {
        "generated_at": common.iso(),
        "universe_size": len(places),
        "countries_in_universe": len({p["cc"] for p in places}),
        "budget": {"tier3": TIER3, "tier2": TIER2, "tier1": TIER1},
        "selection_reasons": {r: sum(1 for p in picked if p["selected_for"] == r)
                              for r in {p["selected_for"] for p in picked}},
        "targets": picked,
    })
    from collections import Counter
    print(f"universe {len(places)} places / {len({p['cc'] for p in places})} countries")
    print("selected", len(picked), Counter(p["selected_for"] for p in picked))
    print("continents", Counter(p["place"]["continent"] for p in picked))
    print("top 15:", ", ".join(f'{p["place"]["name"]}({p["place"]["cc"]})' for p in picked[:15]))


if __name__ == "__main__":
    main()
