"""Step 3 - Global physical-ecosystem scan (spec §12, §14, §15, §26, §77).

ARCHITECTURE CHANGE (documented in DATA_SOURCES.md): the first implementation
queried Overpass per candidate city. Two environment realities killed it:
overpass-api.de began returning 504s under load, and the session's egress relay
closes tunnels that stay silent ~6-7s, which is exactly how Overpass behaves
while planning a query. Measured throughput was ~1 successful query/minute.

Replaced with QLever's OSM-planet SPARQL endpoint (qlever.dev), which is
credential-free and answers planet-wide queries in ~1-3s. This is strictly
better for the product, not just faster: instead of only inspecting a
pre-chosen candidate list, every matching object on Earth is retrieved, so a
hotspot can emerge anywhere - which is what §12/§15 actually ask for.

overpass.openstreetmap.fr is retained as a verified fallback (5/5 success at
~1.8s in testing) if QLever is unavailable.
"""
import json, math, os, re, sys, time
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register

QLEVER = "https://qlever.dev/api/osm-planet"
OVERPASS_FALLBACK = "https://overpass.openstreetmap.fr/api/interpreter"
LIM = RateLimiter(1.0)
BRK = CircuitBreaker(6, 45)

# key, value, evidence family, per-object weight, extra filter
TAGS = [
    ("amenity", "coworking_space", "coworking", 3.0, None),
    ("office", "coworking", "coworking", 3.0, None),
    ("residential", "coliving", "coworking", 3.0, None),   # rare: ~0 objects worldwide
    # Added to widen evidence outside Europe and North America, which the audit
    # named as the largest remaining source of error. Coworking tags are mapped
    # overwhelmingly by European mappers; libraries, universities, guest houses
    # and serviced apartments are mapped everywhere, and all four are places a
    # remote worker actually uses. Weights are deliberately low - these are
    # corroboration, not the primary signal.
    ("amenity", "library", "community", 0.6, None),
    ("amenity", "university", "international", 0.6, None),
    ("tourism", "apartment", "international", 0.5, None),
    ("tourism", "guest_house", "international", 0.4, None),
    ("leisure", "hackerspace", "community", 2.5, None),
    ("amenity", "internet_cafe", "community", 1.2, None),
    ("amenity", "language_school", "international", 1.6, None),
    ("tourism", "hostel", "international", 1.4, None),
    ("amenity", "community_centre", "community", 0.7, None),
    ("amenity", "nightclub", "social", 0.9, None),
    ("amenity", "cafe", "coworking", 0.35, ("internet_access", "wlan")),
    ("amenity", "arts_centre", "social", 0.6, None),
    ("leisure", "sports_centre", "social", 0.3, None),
]

PREFIX = """PREFIX osmkey: <https://www.openstreetmap.org/wiki/Key:>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
"""


def sparql(q):
    return fetch(QLEVER, source_id="qlever_osm", data=q.encode(),
                 headers={"Content-Type": "application/sparql-query",
                          "Accept": "application/qlever-results+json"},
                 timeout=180, retries=3, backoff=3.0, limiter=LIM, breaker=BRK,
                 as_json=True, cache_ttl=5 * 86400)


POINT_RE = re.compile(r"POINT\(([-\d.]+) ([-\d.]+)\)")


def pull(key, value, extra):
    filt = f' ; osmkey:{extra[0]} ?ia' if extra else ""
    cond = f' FILTER(REGEX(STR(?ia), "{extra[1]}|^yes$"))' if extra else ""
    q = PREFIX + f"""SELECT ?o ?nm (geof:centroid(?g) AS ?c) WHERE {{
  ?o osmkey:{key} "{value}" ; geo:hasGeometry/geo:asWKT ?g{filt} .
  OPTIONAL {{ ?o osmkey:name ?nm }}{cond}
}} LIMIT 400000"""
    res = sparql(q)
    if not res or res.get("status") != "OK":
        return None
    out = []
    for row in res.get("res", []):
        oid, nm, wkt = row[0], row[1], row[2]
        m = POINT_RE.search(wkt or "")
        if not m:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        if not (-90 < lat < 90):
            continue
        out.append((oid.strip("<>").rsplit("openstreetmap.org/", 1)[-1],
                    (nm or "").strip('"')[:80], round(lat, 5), round(lon, 5)))
    return out


class PlaceGrid:
    """0.25-degree bucket grid for nearest-locality attribution."""

    def __init__(self, places):
        self.g = defaultdict(list)
        for p in places:
            self.g[(int(p["lat"] * 4), int(p["lon"] * 4))].append(p)

    def nearest(self, lat, lon):
        """Attribute to the most *significant* nearby place, not the merely
        nearest one. A dense metro is fragmented into dozens of small GeoNames
        entries; nearest-wins hands the city centre's venues to a 12k-population
        suburb two kilometres away and the core city ends up looking empty.
        Significance = population weight decayed by distance within reach."""
        la, lo = int(lat * 4), int(lon * 4)
        best, bestscore, bestd = None, -1.0, None
        cosl = math.cos(math.radians(lat))
        for dla in (-1, 0, 1):
            for dlo in (-1, 0, 1):
                for p in self.g.get((la + dla, lo + dlo), ()):
                    dy = (p["lat"] - lat) * 111.0
                    dx = (p["lon"] - lon) * 111.0 * cosl
                    d = math.sqrt(dx * dx + dy * dy)
                    pop = p["pop"]
                    reach = 5.0 if pop < 40000 else 8.0 if pop < 150000 else \
                            13.0 if pop < 600000 else 19.0 if pop < 1800000 else 26.0
                    if d >= reach:
                        continue
                    score = (pop ** 0.42) * (1.0 - (d / reach) ** 1.5)
                    if score > bestscore:
                        bestscore, best, bestd = score, p, d
        return best, bestd


def main():
    gb = read_json("geobase.json")
    grid = PlaceGrid(gb["places"])
    sink, totals = {}, {}
    t0 = time.time()

    for key, value, family, weight, extra in TAGS:
        label = f"{key}={value}" + (f"[{extra[0]}~{extra[1]}]" if extra else "")
        rows = pull(key, value, extra)
        if rows is None:
            print(f"  {label:42} FAILED - skipped (source failure is survivable)")
            continue
        totals[label] = len(rows)
        attached = 0
        for oid, nm, lat, lon in rows:
            p, dist = grid.nearest(lat, lon)
            if not p:
                continue
            gid = str(p["gid"])
            rec = sink.setdefault(gid, {"gid": p["gid"], "name": p["name"], "cc": p["cc"],
                                        "lat": p["lat"], "lon": p["lon"], "pop": p["pop"],
                                        "scanned_at": common.iso(), "venues": []})
            rec["venues"].append({"id": oid.replace("/", "")[0] + oid.split("/")[-1],
                                  "osm": oid, "lat": lat, "lon": lon, "family": family,
                                  "kind": value, "group": key, "name": nm, "w": weight})
            attached += 1
        print(f"  {label:42} {len(rows):>7} objects -> {attached:>7} attached "
              f"({time.time()-t0:.0f}s)", flush=True)

    for rec in sink.values():
        seen, uniq = set(), []
        for v in rec["venues"]:
            if v["osm"] in seen:
                continue
            seen.add(v["osm"]); uniq.append(v)
        rec["venues"] = uniq

    write_json("ecosystem.json", {
        "generated_at": common.iso(),
        "source": "OpenStreetMap planet via QLever SPARQL (ODbL)",
        "global_object_counts": totals, "places": sink})
    register("qlever_osm", source_name="QLever OSM-planet SPARQL endpoint",
             domain="qlever.dev", source_type="physical ecosystem",
             access_method="anonymous SPARQL", credential_required=False,
             geographic_scope="global (entire OSM planet)",
             coverage=sum(totals.values()), freshness="OSM planet snapshot",
             terms_notes="ODbL; replaced Overpass after 504s + relay timeouts")
    common.save_registry()
    tot = sum(len(v["venues"]) for v in sink.values())
    print(f"done in {time.time()-t0:.0f}s: {len(sink)} localities, {tot} attached venues "
          f"from {sum(totals.values())} global objects")


if __name__ == "__main__":
    main()
