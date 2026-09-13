"""Step 6c - compute the validity statistics the app displays about itself.

The audit report used to be a separate document that could silently go stale.
These numbers are recomputed from each build's own outputs and shipped into the
page, so the report a reader sees always describes the data they are looking at.
"""
import json, math, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import read_json, write_json
from step6_h3 import KIND_SPEC

NOMAD_SPECIFIC = {"coworking_space", "coworking", "coliving", "hackerspace", "apartment"}
NOMAD_ADJACENT = {"hostel", "language_school", "internet_cafe"}


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
    if len(xs) < 3:
        return 0.0
    rx, ry = rank(xs), rank(ys)
    n = len(xs); mx = sum(rx) / n; my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else 0.0


def main():
    sc = read_json("scored.json")
    eco = (read_json("ecosystem.json", {}) or {}).get("places", {})
    evs = (read_json("events.json", {}) or {}).get("places", {})
    vfe = read_json("venue_feeds.json", {}) or {}
    base = (read_json("mapping_baseline.json", {}) or {})
    comm = (read_json("community.json", {}) or {})
    gb = read_json("geobase.json")
    lang = read_json("locallang.json", {}) or {}
    att = read_json("attention.json", {}) or {}
    L = sc["localities"]
    ranked = [x for x in L if x.get("ranked")]

    # --- composition by nomad specificity, at the weights the model uses ---
    kw, kn = Counter(), Counter()
    for rec in eco.values():
        for v in rec["venues"]:
            w = KIND_SPEC.get(v["kind"], (0.0, ""))[0]
            kw[v["kind"]] += w
            kn[v["kind"]] += 1
    tot = sum(kw.values()) or 1
    def tier(k):
        return ("specific" if k in NOMAD_SPECIFIC else
                "adjacent" if k in NOMAD_ADJACENT else "generic")
    composition = [{"tag": k, "objects": kn[k], "weight_pct": round(100 * w / tot, 1),
                    "tier": tier(k)} for k, w in kw.most_common() if w > 0]
    dropped = [{"tag": k, "objects": kn[k]} for k in kn
               if KIND_SPEC.get(k, (0.0,))[0] <= 0]
    shares = {t: round(100 * sum(w for k, w in kw.items() if tier(k) == t) / tot, 1)
              for t in ("specific", "adjacent", "generic")}

    # --- confound tests ---
    sub = ranked or L
    def col(f):
        return [f(x) for x in sub]
    confounds = [
        ("Population", spearman(col(lambda x: x["live_score"]), col(lambda x: x["pop"]))),
        ("Mapped venues", spearman(col(lambda x: x["live_score"]), col(lambda x: x["venues"]))),
        ("Wikipedia attention", spearman(col(lambda x: x["live_score"]), col(lambda x: x["daily_attention"]))),
        ("Live events found", spearman(col(lambda x: x["live_score"]), col(lambda x: x["events_total"]))),
        ("Community posts", spearman(col(lambda x: x["live_score"]), col(lambda x: x["community_posts"]))),
        ("OSM mapping baseline", spearman(col(lambda x: x["live_score"]), col(lambda x: x.get("mapping_baseline", 0)))),
    ]

    # --- OSM mapping-completeness bias, by country ---
    pop_cc, ven_cc, cow_cc = Counter(), Counter(), Counter()
    for rec in eco.values():
        cc = rec["cc"]
        pop_cc[cc] += rec["pop"]
        ven_cc[cc] += len(rec["venues"])
        cow_cc[cc] += sum(1 for v in rec["venues"]
                          if v["kind"] in ("coworking", "coworking_space", "coliving"))
    cc_name = {c: v["name"] for c, v in gb["countries"].items()}
    bias = []
    for cc in pop_cc:
        if pop_cc[cc] < 3_000_000:
            continue
        per = pop_cc[cc] / 100_000
        bias.append({"cc": cc, "country": cc_name.get(cc, cc),
                     "coworking_per_100k": round(cow_cc[cc] / per, 2),
                     "venues_per_100k": round(ven_cc[cc] / per, 1)})
    bias.sort(key=lambda r: -r["coworking_per_100k"])

    # --- circularity of the event sample ---
    sel = Counter(v.get("selected_for", "merit") for v in evs.values())

    # --- corroboration ---
    fam = Counter()
    for x in L:
        fam[len(x.get("evidence_families", []))] += 1

    stats = {
        "generated_at": common.iso(),
        "composition": composition, "composition_shares": shares, "dropped_tags": dropped,
        "confounds": [{"against": a, "rho": round(b, 3)} for a, b in confounds],
        "osm_bias": bias,
        "event_sample": {"total": len(evs), "by_selection": dict(sel),
                         "events": sum(len(v["events"]) for v in evs.values())},
        "venue_feeds": {"probed": vfe.get("sites_probed", 0),
                        "with_feeds": vfe.get("sites_with_feeds", 0),
                        "localities": len(vfe.get("places", {}))},
        "baseline_objects": sum(t.get("objects", 0) for t in base.get("per_tag", {}).values()),
        "baseline_tags": base.get("tags", []),
        "community": {"posts": comm.get("posts_scanned", 0),
                      "localities": len(comm.get("places", {}))},
        # How wide the attention layer's language coverage actually is. An
        # English-only attention layer under-counts every place whose readers
        # do not read English Wikipedia, so this is the honest measure of how
        # far that bias has been closed rather than merely normalised away.
        "attention_languages": {
            "editions": len(lang.get("wikis_queried", [])),
            "places_with_local_title": len(lang.get("places", {})),
            "projects_tracked": att.get("projects_tracked") or 0,
            "title_pairs": att.get("title_pairs") or 0,
        },
        "corroboration": {"scanned": len(L), "ranked": len(ranked),
                          "by_family_count": dict(sorted(fam.items()))},
    }
    write_json("audit_stats.json", stats)
    print(f"audit stats: composition {shares}, {len(bias)} countries, "
          f"{len(ranked):,}/{len(L):,} ranked")


if __name__ == "__main__":
    main()
