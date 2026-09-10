"""Step 6 - H3 spatial model, scoring, clustering and roll-ups.

Implements spec §6-§13, §17-§24, §33, §35, §63. Every geocodable signal is
assigned an H3 cell at a resolution justified by its geographic precision;
city-level-only evidence is kept at city precision and never promoted to a
neighbourhood claim (§30, §79).

Pipeline: evidence -> H3 cells (res 8) -> parent roll-up (res 7..2) ->
contiguous hotspot clustering -> locality scores -> admin_1 / country roll-ups
that preserve max and concentration, not just the mean (§11).
"""
import json, math, os, re, sys, time
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(__file__))
import h3
import common
from common import read_json, write_json

FINE_RES = 8          # ~0.46 km edge - neighbourhood/street scale
RES_CHAIN = [8, 7, 6, 5, 4, 3, 2]
HOT_CELL_MIN = 0.9    # weighted evidence needed before a cell counts as "active"

# Scoring weights (spec §19) - configurable, not baked into the maths.
WEIGHTS = {
    "nomad_presence": 0.25, "event_activity": 0.25, "community_activity": 0.20,
    "coworking_infra": 0.10, "international_social": 0.10, "momentum": 0.05,
    "confidence": 0.05,
}

NOMAD_CATEGORIES = {"digital nomad", "coworking", "expat / international",
                    "language exchange", "networking", "startup"}
SOCIAL_CATEGORIES = {"social", "nightlife", "music / festival", "wellness",
                     "sport", "outdoor / hiking", "creative", "cultural"}


def now_utc():
    return datetime.now(timezone.utc)


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def sat(x, k=1.0):
    """Saturating 0..1 curve - keeps large cities from running away (§21)."""
    return 1.0 - math.exp(-max(x, 0.0) / max(k, 1e-9))


def s100(x):
    return int(round(max(0.0, min(1.0, x)) * 100))


def band(score):
    return ("EXTREMELY HOT" if score >= 90 else "VERY ACTIVE" if score >= 80 else
            "ACTIVE" if score >= 70 else "MODERATE" if score >= 55 else
            "QUIET" if score >= 40 else "LOW ACTIVITY")


def presence_band(score):
    return ("VERY HIGH" if score >= 82 else "HIGH" if score >= 66 else
            "MODERATE" if score >= 48 else "LOW" if score >= 28 else "VERY LOW")


def momentum_label(r):
    if r is None:
        return "UNKNOWN"
    return ("STRONGLY RISING" if r >= 1.35 else "RISING" if r >= 1.10 else
            "STABLE" if r >= 0.92 else "COOLING" if r >= 0.75 else "STRONGLY COOLING")


def trend_icon(r):
    if r is None:
        return "?"
    return "HOT" if r >= 1.5 else "RISING" if r >= 1.1 else "STABLE" if r >= 0.92 else \
           "COOLING" if r >= 0.75 else "QUIET"


def freshness_label(hours):
    if hours is None:
        return "NO LIVE SIGNAL"
    return ("LIVE" if hours <= 24 else "<7 DAYS" if hours <= 168 else
            "<30 DAYS" if hours <= 720 else "STALE")


# ---------------------------------------------------------------- evidence

def build_evidence(gb, eco, evs, comm, att):
    """Normalize every source into provenance-carrying evidence records (§32)."""
    ev_id = 0
    per_place = defaultdict(list)
    now = now_utc()

    for gid, rec in eco.items():
        for v in rec["venues"]:
            ev_id += 1
            per_place[gid].append({
                "id": f"e{ev_id}", "source_id": "osm_overpass", "type": "venue",
                "family": v["family"], "kind": v["kind"], "title": v["name"] or v["kind"],
                "lat": v["lat"], "lon": v["lon"], "precision": "point",
                "h3": h3.latlng_to_cell(v["lat"], v["lon"], FINE_RES),
                "weight": v["w"], "observed_at": rec["scanned_at"],
                "age_hours": 0, "url": f'https://www.openstreetmap.org/{ {"n":"node","w":"way","r":"relation"}[v["id"][0]] }/{v["id"][1:]}',
            })

    for gid, rec in evs.items():
        place_seen = set()
        for e in rec["events"]:
            if e["status"] == "cancelled" or e["online"]:
                continue
            key = (re.sub(r"\W+", "", e["title"].lower())[:48], e["start"][:10])
            if key in place_seen:      # cross-source duplicate (§22)
                continue
            place_seen.add(key)
            start = parse_dt(e["start"])
            if start:
                dh = (start - now).total_seconds() / 3600.0
                if dh < -336 or dh > 2160:      # older than 14d / further than 90d
                    continue
                age = abs(dh)
            else:
                age = 720
            ev_id += 1
            lat, lon = e.get("lat"), e.get("lon")
            prec, cell = "locality", None
            if lat and lon:
                prec, cell = "point", h3.latlng_to_cell(lat, lon, FINE_RES)
            per_place[gid].append({
                "id": f"e{ev_id}", "source_id": e["source"], "type": "event",
                "family": "event", "kind": e["category"], "title": e["title"],
                "lat": lat, "lon": lon, "precision": prec, "h3": cell,
                "venue": e["venue"], "street": e["street"], "organizer": e["organizer"],
                "weight": 1.0, "observed_at": rec["scanned_at"], "event_date": e["start"],
                "age_hours": round(age, 1), "url": e["url"],
            })

    for gid, rec in comm.items():
        for m in rec["samples"]:
            ev_id += 1
            at = parse_dt(m["at"])
            per_place[gid].append({
                "id": f"e{ev_id}", "source_id": m["source"], "type": "community_post",
                "family": "community", "kind": m["channel"], "title": m["title"],
                "lat": None, "lon": None, "precision": "locality", "h3": None,
                "weight": 1.0, "observed_at": m["at"],
                "age_hours": round((now - at).total_seconds() / 3600.0, 1) if at else None,
                "url": m["url"],
            })
    return per_place


# ---------------------------------------------------------------- cells

def build_cells(per_place):
    """Fine cells from point-precision evidence, then parent roll-up (§8)."""
    cells = {}
    for gid, items in per_place.items():
        for it in items:
            c = it.get("h3")
            if not c:
                continue
            cell = cells.setdefault(c, {
                "h3": c, "res": FINE_RES, "gid": gid, "w": defaultdict(float),
                "n": 0, "sources": set(), "kinds": Counter(), "titles": [],
                "min_age": 1e9,
            })
            cell["w"][it["family"]] += it["weight"]
            cell["n"] += 1
            cell["sources"].add(it["source_id"])
            cell["kinds"][it["kind"]] += 1
            if it.get("age_hours") is not None:
                cell["min_age"] = min(cell["min_age"], it["age_hours"])
            if len(cell["titles"]) < 6 and it["title"]:
                cell["titles"].append(it["title"][:60])
    return cells


# Per-resolution normalisers, fitted to the actual weight distribution at each
# resolution. A res-2 cell aggregates ~7^6 times the area of a res-8 cell, so a
# single fixed saturation constant makes every coarse cell saturate to the same
# colour and the world map becomes one flat blob. These are set by fit_norms().
CELL_NORM = {r: 6.0 for r in RES_CHAIN}
CELL_DIST = {}          # res -> sorted weight list, for percentile ranking


def fit_norms(levels):
    """Two normalisers per resolution, because either alone misleads.

    Absolute saturation keeps the score meaningful (a cell with more evidence
    scores higher, full stop). Percentile rank within the resolution keeps the
    ramp usable (without it, Europe saturates and the rest of the world is one
    flat dark field). The cell score blends them."""
    for res, lv in levels.items():
        tot = sorted(sum(c["w"].values()) for c in lv.values())
        if not tot:
            continue
        CELL_DIST[res] = tot
        p = tot[int(len(tot) * 0.99)] if len(tot) > 200 else tot[-1]
        CELL_NORM[res] = max(p / 3.0, 1.2)
    return CELL_NORM


def pct_rank(res, v):
    d = CELL_DIST.get(res)
    if not d:
        return 0.5
    import bisect
    return bisect.bisect_left(d, v) / max(len(d) - 1, 1)


def score_cell(c, res=None):
    w = c["w"]
    k = CELL_NORM.get(res if res is not None else c.get("res", FINE_RES), 6.0)
    cw = w.get("coworking", 0.0)
    com = w.get("community", 0.0)
    intl = w.get("international", 0.0)
    soc = w.get("social", 0.0)
    evt = w.get("event", 0.0)
    sub = {
        "coworking": s100(sat(cw, k * 0.42)),
        "community": s100(sat(com + 0.5 * evt, k * 0.38)),
        "international": s100(sat(intl, k * 0.44)),
        "social": s100(sat(soc, k * 0.55)),
        "events": s100(sat(evt, k * 0.30)),
    }
    total = cw * 1.5 + com * 1.1 + intl * 1.0 + soc * 0.55 + evt * 1.6
    pr = pct_rank(res if res is not None else c.get("res", FINE_RES), sum(w.values()))
    live = s100(0.46 * (pr ** 1.25) + 0.42 * sat(total, k)
                + 0.12 * sat(len(c["sources"]) - 0.5, 1.6))
    div = len({k for k in w if w[k] > 0})
    conf = s100(0.30 * sat(len(c["sources"]), 1.5) + 0.28 * sat(c["n"] / 4.0, 1.0)
                + 0.22 * sat(div, 1.6) + 0.20)
    return sub, live, conf, round(total, 2)


def rollup(cells):
    """Aggregate fine cells into every coarser resolution (§8, §63)."""
    levels = {FINE_RES: cells}
    cur = cells
    for res in RES_CHAIN[1:]:
        parent = {}
        for c in cur.values():
            p = h3.cell_to_parent(c["h3"], res)
            pc = parent.setdefault(p, {"h3": p, "res": res, "gid": c["gid"],
                                       "w": defaultdict(float), "n": 0, "sources": set(),
                                       "kinds": Counter(), "titles": [], "min_age": 1e9,
                                       "children": 0, "max_child": 0.0})
            for k, v in c["w"].items():
                pc["w"][k] += v
            pc["n"] += c["n"]
            pc["sources"] |= c["sources"]
            pc["kinds"].update(c["kinds"])
            pc["children"] += 1
            pc["min_age"] = min(pc["min_age"], c["min_age"])
            tot = sum(c["w"].values())
            if tot > pc["max_child"]:
                pc["max_child"] = tot
                pc["gid"] = c["gid"]
                pc["titles"] = c["titles"][:4]
        levels[res] = parent
        cur = parent
    return levels


# ---------------------------------------------------------------- clusters

def cluster(cells, place_by_gid):
    """Contiguous hotspot clusters from neighbouring hot cells (§13)."""
    hot = {k: v for k, v in cells.items() if sum(v["w"].values()) >= HOT_CELL_MIN}
    seen, clusters = set(), []
    for start in hot:
        if start in seen:
            continue
        stack, members = [start], []
        seen.add(start)
        while stack:
            cur = stack.pop()
            members.append(cur)
            for nb in h3.grid_disk(cur, 1):
                if nb in hot and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if len(members) < 2:
            continue
        w = defaultdict(float)
        n, srcs, kinds, titles, minage = 0, set(), Counter(), [], 1e9
        for m in members:
            c = cells[m]
            for k, v in c["w"].items():
                w[k] += v
            n += c["n"]; srcs |= c["sources"]; kinds.update(c["kinds"])
            minage = min(minage, c["min_age"])
            titles.extend(c["titles"])
        lats, lons = zip(*[h3.cell_to_latlng(m) for m in members])
        gid = Counter(cells[m]["gid"] for m in members).most_common(1)[0][0]
        pl = place_by_gid.get(gid, {})
        total = sum(w.values())
        clusters.append({
            "id": f"c{len(clusters)+1}", "cells": members, "n_cells": len(members),
            "lat": round(sum(lats) / len(lats), 5), "lon": round(sum(lons) / len(lons), 5),
            "gid": gid, "place": pl.get("name", ""), "cc": pl.get("cc", ""),
            "country": pl.get("country", ""),
            "area_km2": round(len(members) * 0.737, 2),
            "evidence": n, "sources": sorted(srcs), "weight": round(total, 2),
            "families": {k: round(v, 2) for k, v in w.items()},
            "dominant": [k for k, _ in kinds.most_common(5)],
            "landmarks": titles[:6],
            "min_age_hours": None if minage > 1e8 else round(minage, 1),
            "score": s100(sat(total, 9.0) * 0.7 + sat(len(members), 5.0) * 0.3),
            "confidence": s100(0.34 * sat(len(srcs), 1.6) + 0.33 * sat(n / 8.0, 1.0) + 0.25),
        })
    clusters.sort(key=lambda c: -c["weight"])
    return clusters


def trim_clusters(clusters, cap=3000):
    out = []
    for c in clusters[:cap]:
        out.append({k: v for k, v in c.items() if k not in ("cells",)})
        out[-1]["landmarks"] = [t for t in c["landmarks"][:3] if t]
        out[-1]["dominant"] = c["dominant"][:4]
        out[-1]["sources"] = c["sources"][:4]
    return out


# ---------------------------------------------------------------- localities

def score_locality(place, items, cells_here, clusters_here, att_rec, comm_rec, ev_rec):
    """Locality-level metrics. All inputs are evidence; nothing is reputational."""
    now = now_utc()
    pop = max(place["pop"], 1)
    pop100k = pop / 100000.0

    venues = [i for i in items if i["type"] == "venue"]
    events = [i for i in items if i["type"] == "event"]
    posts = [i for i in items if i["type"] == "community_post"]

    fam = defaultdict(float)
    for v in venues:
        fam[v["family"]] += v["weight"]

    # ---- event quality (§22): not a raw count
    upcoming = [e for e in events if (e.get("age_hours") or 999) <= 720]
    organizers = {e.get("organizer") for e in events if e.get("organizer")}
    venues_used = {e.get("venue") for e in events if e.get("venue")}
    cats = {e["kind"] for e in events}
    nomad_events = [e for e in events if e["kind"] in NOMAD_CATEGORIES]
    per_week = len(upcoming) / 4.0
    org_conc = (1.0 - 1.0 / max(len(organizers), 1)) if organizers else 0.0
    event_activity = s100(
        0.42 * sat(per_week, 2.2) + 0.22 * sat(len(organizers), 2.2)
        + 0.14 * sat(len(venues_used), 3.0) + 0.12 * sat(len(cats), 3.0)
        + 0.10 * sat(len(nomad_events), 1.5))

    # ---- community velocity (§24)
    n_posts = comm_rec.get("mentions", 0)
    community_activity = s100(
        0.45 * sat(n_posts, 2.5) + 0.25 * sat(comm_rec.get("unique_sources", 0), 1.2)
        + 0.30 * sat(len(organizers) + 0.5 * len(nomad_events), 2.5))

    # ---- infrastructure
    coworking_infra = s100(0.6 * sat(fam["coworking"], 5.0)
                           + 0.4 * sat(fam["coworking"] / max(pop100k, 0.35), 3.0))
    international_social = s100(
        0.45 * sat(fam["international"], 6.0) + 0.25 * sat(fam["social"], 8.0)
        + 0.30 * sat(fam["international"] / max(pop100k, 0.35), 3.0))

    # ---- attention / presence
    daily = (att_rec or {}).get("daily_avg", 0.0)
    per_cap = daily / max(pop100k, 0.35)
    nomad_presence = s100(
        0.34 * sat(per_cap, 22.0) + 0.20 * sat(daily / 400.0, 1.0)
        + 0.28 * sat(fam["coworking"] * 1.4 + len(nomad_events) * 1.6, 6.0)
        + 0.18 * sat(n_posts, 2.0))

    # ---- Active Community Density (§21): concentration beats raw size
    top = clusters_here[0] if clusters_here else None
    concentration = 0.0
    if cells_here:
        tot = sum(sum(c["w"].values()) for c in cells_here)
        if tot > 0:
            top_cells = sorted((sum(c["w"].values()) for c in cells_here), reverse=True)[:5]
            concentration = sum(top_cells) / tot
    acd = s100(
        0.30 * sat(len(upcoming) + len(organizers) * 1.4, 5.0)
        + 0.22 * sat((top or {}).get("weight", 0.0), 8.0)
        + 0.18 * concentration
        + 0.16 * sat(fam["coworking"] + fam["community"], 5.0)
        + 0.14 * sat(n_posts, 2.0))

    # ---- momentum (§35)
    mratio = (att_rec or {}).get("momentum_ratio")
    ev_recent = len([e for e in events if (e.get("age_hours") or 999) <= 168])
    ev_bias = (ev_recent / max(len(events), 1)) if events else None
    momentum_score = s100(0.5 if mratio is None else max(0.0, min((mratio - 0.7) / 0.9, 1.0)))
    if ev_bias is not None:
        momentum_score = int(round(0.75 * momentum_score + 0.25 * s100(ev_bias * 1.4)))

    # ---- confidence (§33)
    src = {i["source_id"] for i in items}
    # Freshness describes *activity*, not infrastructure. A coworking space
    # mapped in OSM is not a live signal, so venue evidence is excluded here.
    ages = [i["age_hours"] for i in items
            if i.get("age_hours") is not None and i["type"] != "venue"]
    freshest = min(ages) if ages else None
    families_present = len({i["family"] for i in items})
    cov = (att_rec or {}).get("recent_days_covered", 0)
    confidence = s100(
        0.26 * sat(len(src), 1.6) + 0.20 * sat(len(items) / 25.0, 1.0)
        + 0.16 * sat(families_present, 1.8) + 0.14 * min(cov / 14.0, 1.0)
        + 0.12 * (1.0 if cells_here else 0.0)
        + 0.12 * (1.0 if events else 0.0))
    if (att_rec or {}).get("ambiguous_title"):
        confidence = int(confidence * 0.88)

    parts = {
        "nomad_presence": nomad_presence, "event_activity": event_activity,
        "community_activity": community_activity, "coworking_infra": coworking_infra,
        "international_social": international_social, "momentum": momentum_score,
        "confidence": confidence,
    }
    live = int(round(sum(parts[k] * w for k, w in WEIGHTS.items())))

    # ---- honest warnings (§50)
    warn = []
    if confidence < 45:
        warn.append(("LOW DATA CONFIDENCE", "Few independent sources corroborate this location."))
    if daily > 260 and event_activity < 30 and community_activity < 30:
        warn.append(("HISTORICALLY POPULAR, CURRENTLY QUIET",
                     "Widely referenced, but live event and community evidence is thin right now."))
    if coworking_infra >= 60 and community_activity < 32:
        warn.append(("STRONG INFRASTRUCTURE BUT WEAK COMMUNITY",
                     "Coworking exists; current social/community evidence is limited."))
    if len(organizers) == 1 and len(events) >= 4:
        warn.append(("EVENT ACTIVITY DOMINATED BY ONE ORGANIZER",
                     f"Nearly all listed events come from {list(organizers)[0]}."))
    if mratio is not None and mratio < 0.78:
        warn.append(("ACTIVITY RAPIDLY COOLING", "Current attention is well below the previous window."))
    if cells_here and concentration < 0.24 and live >= 55:
        warn.append(("VERY ACTIVE BUT HIGHLY DISPERSED",
                     "Evidence is spread widely rather than forming one walkable hub."))
    if live >= 60 and not clusters_here:
        warn.append(("NO CLEAR CONCENTRATED HOTSPOT",
                     "Scores well overall, but no contiguous hotspot cluster emerged."))

    return {
        "live_score": live, "band": band(live), "parts": parts,
        "presence": presence_band(nomad_presence),
        "active_community_density": acd, "concentration": round(concentration, 3),
        "momentum_ratio": mratio, "momentum": momentum_label(mratio), "trend": trend_icon(mratio),
        "confidence": confidence,
        "freshness": freshness_label(freshest), "freshest_hours": freshest,
        "evidence_count": len(items), "unique_sources": len(src), "sources": sorted(src),
        "events_total": len(events), "events_upcoming": len(upcoming),
        "events_per_week": round(per_week, 2), "organizers": len(organizers),
        "organizer_concentration": round(org_conc, 2),
        "event_categories": sorted(cats), "community_posts": n_posts,
        "venues": len(venues), "venue_families": {k: round(v, 2) for k, v in fam.items()},
        "daily_attention": daily, "attention_per_100k": round(per_cap, 2),
        "n_cells": len(cells_here), "n_clusters": len(clusters_here),
        "warnings": [{"code": c, "detail": d} for c, d in warn],
    }


# ---------------------------------------------------------------- admin roll-up

def admin_rollup(localities, key_fn, label_fn):
    """Region aggregate that preserves the maximum and the concentration,
    so a hot city is never averaged away by a quiet hinterland (§11)."""
    groups = defaultdict(list)
    for L in localities:
        groups[key_fn(L)].append(L)
    out = []
    for key, ls in groups.items():
        if not key:
            continue
        scores = sorted((l["live_score"] for l in ls))
        pops = [max(l["pop"], 1) for l in ls]
        top = max(ls, key=lambda l: l["live_score"])
        n_hot = sum(1 for s in scores if s >= 70)
        mean = sum(scores) / len(scores)
        median = scores[len(scores) // 2]
        popw = sum(l["live_score"] * p for l, p in zip(ls, pops)) / sum(pops)
        evw_den = sum(max(l["evidence_count"], 1) for l in ls)
        evw = sum(l["live_score"] * max(l["evidence_count"], 1) for l in ls) / evw_den
        out.append({
            "key": key, "label": label_fn(ls[0]), "n_localities": len(ls),
            "mean": round(mean, 1), "median": median, "max": scores[-1],
            "population_weighted": round(popw, 1), "evidence_weighted": round(evw, 1),
            "hot_localities": n_hot,
            "active_pct": round(100.0 * sum(1 for s in scores if s >= 55) / len(scores), 1),
            "top_locality": {"name": top["name"], "gid": top["gid"], "score": top["live_score"],
                             "lat": top["lat"], "lon": top["lon"]},
            "clusters": sum(l["n_clusters"] for l in ls),
            "evidence": sum(l["evidence_count"] for l in ls),
            "confidence": round(sum(l["confidence"] for l in ls) / len(ls), 1),
            "concentration": round(scores[-1] / max(mean, 1e-6), 2),
            "lat": round(sum(l["lat"] for l in ls) / len(ls), 3),
            "lon": round(sum(l["lon"] for l in ls) / len(ls), 3),
        })
    out.sort(key=lambda r: -r["max"])
    return out


def main():
    gb = read_json("geobase.json")
    att = read_json("attention.json", {"places": {}})["places"]
    eco = (read_json("ecosystem.json", {}) or {}).get("places", {})
    evs = (read_json("events.json", {}) or {}).get("places", {})
    comm = (read_json("community.json", {}) or {}).get("places", {})
    place_by_gid = {str(p["gid"]): p for p in gb["places"]}

    print(f"inputs: {len(eco)} ecosystem, {len(evs)} event, {len(comm)} community, "
          f"{len(att)} attention records")

    per_place = build_evidence(gb, eco, evs, comm, att)
    cells = build_cells(per_place)
    print(f"evidence items: {sum(len(v) for v in per_place.values())}; "
          f"fine cells (res {FINE_RES}): {len(cells)}")

    clusters = cluster(cells, place_by_gid)
    print(f"hotspot clusters: {len(clusters)}")
    clusters_by_gid = defaultdict(list)
    for c in clusters:
        clusters_by_gid[c["gid"]].append(c)

    cells_by_gid = defaultdict(list)
    for c in cells.values():
        cells_by_gid[c["gid"]].append(c)

    localities = []
    scanned = set(eco) | set(evs)
    for gid in sorted(scanned, key=lambda g: -place_by_gid.get(g, {}).get("pop", 0)):
        p = place_by_gid.get(gid)
        if not p:
            continue
        m = score_locality(p, per_place.get(gid, []), cells_by_gid.get(gid, []),
                           clusters_by_gid.get(gid, []), att.get(gid, {}),
                           comm.get(gid, {}), evs.get(gid, {}))
        a = att.get(gid) or {}
        m["att_series"] = [[d, v] for d, v in sorted((a.get("series") or {}).items())]
        m["att_recent_views"] = a.get("recent_views", 0)
        m["att_prior_views"] = a.get("prior_views", 0)
        m.update({"gid": int(gid), "name": p["name"], "cc": p["cc"], "country": p["country"],
                  "continent": p["continent"], "admin1": p.get("admin1_name", ""),
                  "lat": p["lat"], "lon": p["lon"], "pop": p["pop"], "tz": p["tz"],
                  "wiki": p.get("wiki")})
        localities.append(m)
    localities.sort(key=lambda l: -l["live_score"])
    print(f"scored localities: {len(localities)}")

    # cell scores + resolution levels
    levels = rollup(cells)
    norms = fit_norms(levels)
    print("cell normalisers:", {r: round(v, 1) for r, v in sorted(norms.items())})
    for res, lv in levels.items():
        for c in lv.values():
            sub, live, conf, tot = score_cell(c, res)
            c["sub"], c["live"], c["conf"], c["total"] = sub, live, conf, tot
    print("cells per resolution:", {r: len(levels[r]) for r in RES_CHAIN})

    # Ship-time pruning (spec §54, §65): roll-ups above already used every cell,
    # but a fine cell holding one low-signal object is noise on the map and bulk
    # in the payload. Keep cells that carry real weight or corroboration.
    SHIP_MIN_W = {8: 1.0, 7: 1.0, 6: 0.9, 5: 0.8, 4: 0.6, 3: 0.0, 2: 0.0}
    SHIP_CAP = {8: 19000, 7: 14500, 6: 10500, 5: 7500, 4: 5000, 3: 3000, 2: 1200}
    LABEL_CAP = 1200   # only the strongest cells carry names/kind lists
    shipped = {}
    for r in RES_CHAIN:
        keep = [c for c in levels[r].values()
                if c["total"] >= SHIP_MIN_W[r] or c["n"] >= 3]
        keep.sort(key=lambda c: -c["total"])
        shipped[r] = keep[:SHIP_CAP[r]]
        for j, c in enumerate(shipped[r]):
            c["_lab"] = j < LABEL_CAP
        print(f"  res {r}: {len(levels[r])} -> {len(shipped[r])} shipped")

    countries = admin_rollup(localities, lambda l: l["cc"], lambda l: l["country"])
    regions = admin_rollup(localities, lambda l: f'{l["cc"]}|{l["admin1"]}',
                           lambda l: f'{l["admin1"]}, {l["country"]}' if l["admin1"] else l["country"])

    # Ship-time locality selection: a place with two sports centres and nothing
    # else is real data but not a destination. Keep places that carry a hotspot,
    # meaningful evidence, or a score worth looking at.
    keep_ids = {L["gid"] for L in localities
                if (L["n_clusters"] > 0 and L["evidence_count"] >= 8)
                or L["evidence_count"] >= 22 or L["live_score"] >= 30}
    ship_loc = [L for L in localities if L["gid"] in keep_ids]
    top_ids = {L["gid"] for L in sorted(ship_loc, key=lambda x: -x["live_score"])[:1900]}
    for L in ship_loc:
        if L["gid"] not in top_ids:
            L.pop("att_series", None)
        elif L.get("att_series"):
            days = L["att_series"]
            L["att_series"] = [days[0][0], [v for _, v in days]]
        L["venue_families"] = {k: round(v, 1) for k, v in L["venue_families"].items()}
        for k in ("warnings", "event_categories", "sources"):
            if not L.get(k):
                L.pop(k, None)
        if L.get("freshest_hours") is None:
            L.pop("freshest_hours", None)
    print(f"shipping {len(ship_loc)} of {len(localities)} localities "
          f"({len(top_ids)} with attention series)")

    ev_ids = {L["gid"] for L in sorted(ship_loc, key=lambda x: -x["live_score"])[:1900]}

    write_json("scored.json", {
        "generated_at": common.iso(), "weights": WEIGHTS, "fine_res": FINE_RES,
        "localities": ship_loc, "countries": countries, "regions": regions[:420],
        "clusters": trim_clusters(clusters),
        "levels": {str(r): [{"h": c["h3"], "s": c["live"], "c": c["conf"], "n": c["n"],
                             "u": len(c["sources"]), "t": round(c["total"], 2),
                             "g": int(c["gid"]), "sub": c["sub"],
                             "k": [k for k, _ in c["kinds"].most_common(3)] if c["_lab"] else 0,
                             "ti": [t for t in c["titles"][:3] if t] if c["_lab"] else 0,
                             "a": None if c["min_age"] > 1e8 else round(c["min_age"], 1)}
                            for c in shipped[r]] for r in RES_CHAIN},
    })
    # short wire keys, expanded by the client (see EV_KEYS in step7)
    EV_MAP = {"type": "t", "source_id": "s", "kind": "k", "title": "n", "url": "u",
              "venue": "v", "organizer": "o", "age_hours": "a", "event_date": "d"}
    EV_SOURCES = ["qlever_osm", "meetup_public", "luma_public", "reddit_rss",
                  "mastodon_public", "lemmy_public", "hn_algolia", "osm_overpass"]
    EV_TYPES = ["venue", "event", "community_post"]

    def _keep(i):
        d = {}
        for k, short in EV_MAP.items():
            v = i.get(k)
            if v in (None, "", []):
                continue
            if k == "source_id":
                v = EV_SOURCES.index(v) if v in EV_SOURCES else 0
            elif k == "type":
                v = EV_TYPES.index(v)
            elif k == "age_hours":
                v = round(v)
            elif k == "url":
                v = v.replace("https://www.openstreetmap.org/", "~o/") \
                     .replace("https://www.meetup.com/", "~m/") \
                     .replace("https://luma.com/", "~l/") \
                     .replace("https://www.reddit.com/", "~r/") \
                     .replace("https://", "~")
            d[short] = v
        if i.get("precision") == "point":
            d["p"] = 1
        return d

    def _rank(i):
        return (0 if i["type"] == "event" else 1 if i["type"] == "community_post" else 2,
                -(len(i.get("title") or "")) if i["type"] == "venue" else 0,
                i.get("age_hours") if i.get("age_hours") is not None else 999)

    ev_out = {}
    for g, items in per_place.items():
        if int(g) not in ev_ids:
            continue
        ranked = sorted(items, key=_rank)
        ev_out[g] = [_keep(i) for i in
                     [x for x in ranked if x["type"] != "venue"][:20] +
                     [x for x in ranked if x["type"] == "venue" and x.get("title")][:9]]
    write_json("evidence.json", {"generated_at": common.iso(), "places": ev_out})
    print("wrote data/scored.json + data/evidence.json")
    print("top 20:", ", ".join(f'{l["name"]} {l["live_score"]}' for l in localities[:20]))


if __name__ == "__main__":
    main()
