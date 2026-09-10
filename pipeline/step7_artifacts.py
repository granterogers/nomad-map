"""Step 7 - Precomputed web artifacts (spec §54, §65).

Projects every H3 cell boundary and every country outline into a single
Web-Mercator pixel space at build time, then delta-encodes them into compact
integer arrays. The browser therefore needs no H3 library, no map tiles and no
network at all: the published page is fully self-contained, which is what makes
a zero-credential deployment possible.

Antimeridian-crossing cells are split so hexagons never smear across the map.
"""
import json, math, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import h3
import common
from common import read_json, write_json

W = 65536.0                     # world pixel width at max detail
LAT_MAX = 82.0
RES_CHAIN = [8, 7, 6, 5, 4, 3, 2]


def merc_y(lat):
    lat = max(-LAT_MAX, min(LAT_MAX, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


Y0, Y1 = merc_y(LAT_MAX), merc_y(-LAT_MAX)
H = W * (Y0 - Y1) / (2 * math.pi)


def project(lat, lon):
    x = (lon + 180.0) / 360.0 * W
    y = (Y0 - merc_y(lat)) / (Y0 - Y1) * H
    return x, y


def encode_cells(cells):
    """[cx, cy, 12 vertex deltas] per cell, all ints, delta-coded on centre."""
    flat, meta = [], []
    prev_cx = prev_cy = 0
    for c in cells:
        try:
            bnd = h3.cell_to_boundary(c["h"])
        except Exception:
            continue
        lons = [p[1] for p in bnd]
        if max(lons) - min(lons) > 180:        # antimeridian: unwrap to one side
            bnd = [(la, lo + 360 if lo < 0 else lo) for la, lo in bnd]
        pts = [project(la, lo) for la, lo in bnd]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        icx, icy = int(round(cx * 4)), int(round(cy * 4))     # quarter-pixel grid
        flat.append(icx - prev_cx)
        flat.append(icy - prev_cy)
        prev_cx, prev_cy = icx, icy
        n = len(pts)
        flat.append(n)
        for x, y in pts:
            flat.append(int(round((x - cx) * 8)))
            flat.append(int(round((y - cy) * 8)))
        meta.append(c)
    return flat, meta


def encode_world(paths_file):
    src = json.load(open(paths_file))
    feats = []
    for f in src["f"]:
        # re-project from the generator's 1000-wide space into ours
        feats.append({"n": f["n"], "d": f["d"]})
    return src, feats


def build_world_paths():
    """Country outlines, projected into the same pixel space, simplified per zoom."""
    import subprocess
    raw = read_json("raw/world_countries.json")
    out = []
    for f in raw["features"]:
        name = f["properties"].get("name") or f["properties"].get("NAME") or ""
        if name == "Antarctica":
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        parts = []
        for poly in polys:
            for ring in poly:
                pts, last = [], None
                for lon, lat in ring:
                    if lon > 180: lon = 180
                    if lon < -180: lon = -180
                    x, y = project(lat, lon)
                    p = (round(x / 32, 1), round(y / 32, 1))   # 2048-wide reference
                    if p != last:
                        pts.append(p); last = p
                if len(pts) < 4:
                    continue
                a = 0.0
                for i in range(len(pts)):
                    x1, y1 = pts[i]; x2, y2 = pts[(i + 1) % len(pts)]
                    a += x1 * y2 - x2 * y1
                if abs(a) / 2 < 1.2:
                    continue
                parts.append("M" + " ".join(f"{x},{y}" for x, y in pts) + "Z")
        if parts:
            out.append({"n": name, "d": "".join(parts)})
    return out


def coastal_index(raw):
    """Approximate coastline proximity from country outline vertices - used for
    the 'beach' / 'mountain' rankings. Vertices are bucketed on a 0.5-degree grid."""
    grid = set()
    for f in raw["features"]:
        if (f["properties"].get("name") or "") == "Antarctica":
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                for lon, lat in ring:
                    grid.add((round(lat * 2), round(lon * 2)))
    return grid


def is_coastal(grid, lat, lon):
    la, lo = round(lat * 2), round(lon * 2)
    for dla in (-1, 0, 1):
        for dlo in (-1, 0, 1):
            if (la + dla, lo + dlo) in grid:
                return True
    return False


# Wire schema: localities travel as plain arrays (no repeated keys) and the
# client expands them back into objects at load. Strings that are pure
# functions of a number (band, presence, momentum label, freshness) are not
# transmitted at all - the client derives them from the same thresholds.
LOC_SCHEMA = ["gid","name","cc","country","admin1","continent","px","py","pop","tz","wiki",
              "live_score","confidence","active_community_density","concentration",
              "momentum_ratio","freshest_hours","evidence_count","unique_sources",
              "events_total","events_upcoming","events_per_week","organizers",
              "organizer_concentration","community_posts","venues","daily_attention",
              "attention_per_100k","n_cells","n_clusters","elev","coastal",
              "parts","sources","event_categories","venue_families","warnings",
              "att_series","att_recent_views","att_prior_views",
              "ranked","evidence_families","mapping_baseline","coworking_share",
              "live_score_pc","parts_pc"]
PART_KEYS = ["nomad_presence","event_activity","community_activity","coworking_infra",
             "international_social","momentum","confidence"]
SOURCE_KEYS = ["qlever_osm","meetup_public","luma_public","venue_feeds","reddit_rss",
               "mastodon_public","lemmy_public","hn_algolia","wikimedia_pageview_dumps"]
FAMILY_KEYS = ["infrastructure","events","community","attention"]
EV_KEYS = {"t":"type","s":"source_id","k":"kind","n":"title","u":"url",
           "v":"venue","o":"organizer","a":"age_hours","d":"event_date","p":"point"}
EV_SOURCES = ["qlever_osm","meetup_public","luma_public","reddit_rss",
              "mastodon_public","lemmy_public","hn_algolia","osm_overpass"]
EV_TYPES = ["venue","event","community_post"]
URL_PREFIX = {"~o/":"https://www.openstreetmap.org/","~m/":"https://www.meetup.com/",
              "~l/":"https://luma.com/","~r/":"https://www.reddit.com/","~":"https://"}
WARN_CODES = ["NOT RANKED - INFRASTRUCTURE ONLY","LOW DATA CONFIDENCE","HISTORICALLY POPULAR, CURRENTLY QUIET",
              "STRONG INFRASTRUCTURE BUT WEAK COMMUNITY",
              "EVENT ACTIVITY DOMINATED BY ONE ORGANIZER","ACTIVITY RAPIDLY COOLING",
              "VERY ACTIVE BUT HIGHLY DISPERSED","NO CLEAR CONCENTRATED HOTSPOT"]


def encode_localities(locs):
    out = []
    for L in locs:
        row = []
        for k in LOC_SCHEMA:
            v = L.get(k)
            if k == "parts":
                v = [L["parts"][x] for x in PART_KEYS]
            elif k == "parts_pc":
                v = [L.get("parts_pc", {}).get(x, 0) for x in PART_KEYS]
            elif k == "sources":
                m = 0
                for i, s in enumerate(SOURCE_KEYS):
                    if s in (L.get("sources") or []):
                        m |= 1 << i
                v = m
            elif k == "ranked":
                v = 1 if L.get("ranked") else 0
            elif k == "evidence_families":
                m = 0
                for i, f in enumerate(FAMILY_KEYS):
                    if f in (L.get("evidence_families") or []):
                        m |= 1 << i
                v = m
            elif k == "warnings":
                v = [[WARN_CODES.index(w["code"]) if w["code"] in WARN_CODES else -1,
                      w["detail"]] for w in (L.get("warnings") or [])]
            elif k == "venue_families":
                v = L.get("venue_families") or {}
            elif k in ("daily_attention", "attention_per_100k", "concentration",
                       "events_per_week", "organizer_concentration"):
                v = round(v, 2) if isinstance(v, (int, float)) else v
            out_v = v
            row.append(out_v)
        while row and row[-1] in (None, 0, [], {}):
            row.pop()
        out.append(row)
    return out


def main():
    sc = read_json("scored.json")
    gb = read_json("geobase.json")
    ev = read_json("evidence.json", {"places": {}})["places"]

    levels_out = {}
    for r in RES_CHAIN:
        cells = sc["levels"][str(r)]
        cells.sort(key=lambda c: -c["t"])
        flat, meta = encode_cells(cells)
        levels_out[str(r)] = {
            "geom": flat,
            "s": [c["s"] for c in meta], "c": [c["c"] for c in meta],
            "n": [c["n"] for c in meta], "u": [c["u"] for c in meta],
            "g": [c["g"] for c in meta],
            "sub": [[c["sub"]["coworking"], c["sub"]["community"], c["sub"]["international"],
                     c["sub"]["social"], c["sub"]["events"]] for c in meta],
            "k": [c["k"] for c in meta], "ti": [c["ti"] for c in meta],
            "a": [c["a"] for c in meta],
        }
        print(f"  res {r}: {len(meta)} cells, {len(flat)} ints")

    raw_world = read_json("raw/world_countries.json")
    cgrid = coastal_index(raw_world)
    dem = {p["gid"]: p.get("dem", 0) for p in gb["places"]}
    for L in sc["localities"]:
        x, y = project(L["lat"], L["lon"])
        L["px"], L["py"] = round(x, 1), round(y, 1)
        L["elev"] = dem.get(L["gid"], 0)
        L["coastal"] = is_coastal(cgrid, L["lat"], L["lon"])
    for c in sc["clusters"]:
        x, y = project(c["lat"], c["lon"])
        c["px"], c["py"] = round(x, 1), round(y, 1)
        c.pop("cells", None)
    for r in sc["countries"] + sc["regions"]:
        x, y = project(r["lat"], r["lon"])
        r["px"], r["py"] = round(x, 1), round(y, 1)

    world = build_world_paths()
    audit = read_json("source_audit.json", {"results": []})
    val = read_json("validation_result.json", {})
    if val:
        val = {k: v for k, v in val.items() if k != "rows"}
    registry = read_json("source_registry.json", {})
    att = read_json("attention.json", {})

    bundle = {
        "generated_at": common.iso(),
        "world_px": {"w": W, "h": round(H, 1), "ref": 2048, "lat_max": LAT_MAX},
        "meta": {
            "universe_places": len(gb["places"]),
            "universe_countries": len({p["cc"] for p in gb["places"]}),
            "scanned_localities": len(sc["localities"]),
            "ranked_localities": sum(1 for L in sc["localities"] if L.get("ranked")),
            "clusters": len(sc["clusters"]),
            "weights": sc["weights"], "fine_res": sc["fine_res"],
            "attention_window": {"start": att.get("window_start"), "end": att.get("window_end"),
                                 "files_ok": att.get("files_ok"),
                                 "files_attempted": att.get("files_attempted")},
        },
        "countries_geo": world,
        "levels": levels_out,
        "loc_schema": LOC_SCHEMA, "part_keys": PART_KEYS,
        "ev_keys": EV_KEYS, "ev_sources": EV_SOURCES, "ev_types": EV_TYPES,
        "url_prefix": URL_PREFIX,
        "source_keys": SOURCE_KEYS, "warn_codes": WARN_CODES,
        "family_keys": FAMILY_KEYS,
        "localities": encode_localities(sc["localities"]),
        "clusters": sc["clusters"],
        "country_rollup": sc["countries"],
        "region_rollup": sc["regions"],
        "evidence": ev,
        "sources": {"audit": audit["results"], "registry": registry},
        "validation": val,
    }
    p = write_json("bundle.json", bundle)
    print(f"wrote {p} ({os.path.getsize(p)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
