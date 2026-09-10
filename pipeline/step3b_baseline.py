"""Step 3b - OSM mapping-completeness baseline (fixes the dominant confound).

The validity audit found that the strongest driver of the ranking was not nomad
activity but how thoroughly a region has been mapped in OpenStreetMap: France
records 4.06 mapped coworking spaces per 100k people, Indonesia 0.06 - a 68x gap
that nobody believes is real.

The fix is to measure each locality's *general* OSM richness using tags that are
(a) present roughly in proportion to population everywhere on earth, (b) mapped
by the same generic volunteer effort, and (c) completely uninformative about
digital nomads. Nomad signals are then scored as a share of what is mapped
locally, not as an absolute count - which is scale-free and mapping-bias-free.

Deliberately NOT used as baseline tags: anything a nomad would care about
(cafes, coworking, hostels, nightlife, coliving, language schools).
"""
import json, math, os, re, sys, time
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register
from step3_ecosystem import PlaceGrid, QLEVER, POINT_RE, PREFIX

LIM = RateLimiter(1.0)
BRK = CircuitBreaker(6, 45)

# Mundane civic infrastructure. Every inhabited place has these in rough
# proportion to its population; none of them says anything about nomads.
BASELINE_TAGS = [
    ("amenity", "pharmacy"),
    ("amenity", "fuel"),
    ("shop", "supermarket"),
    ("amenity", "bank"),
    ("shop", "hairdresser"),
    ("amenity", "post_box"),
]


def pull_points(key, value):
    """Coordinates only - names are irrelevant for a density baseline and
    doubling the payload for them would be wasteful."""
    q = PREFIX + f"""SELECT (geof:centroid(?g) AS ?c) WHERE {{
  ?o osmkey:{key} "{value}" ; geo:hasGeometry/geo:asWKT ?g .
}} LIMIT 900000"""
    res = fetch(QLEVER, source_id="qlever_osm_baseline", data=q.encode(),
                headers={"Content-Type": "application/sparql-query",
                         "Accept": "application/qlever-results+json"},
                timeout=600, retries=2, backoff=4.0, limiter=LIM, breaker=BRK,
                as_json=True, cache_ttl=5 * 86400)
    if not res or res.get("status") != "OK":
        return None
    out = []
    for row in res.get("res", []):
        m = POINT_RE.search(row[0] or "")
        if not m:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        if -90 < lat < 90:
            out.append((lat, lon))
    return out


def main():
    gb = read_json("geobase.json")
    grid = PlaceGrid(gb["places"])
    counts = defaultdict(int)
    per_tag = {}
    t0 = time.time()

    for key, value in BASELINE_TAGS:
        label = f"{key}={value}"
        pts = pull_points(key, value)
        if pts is None:
            print(f"  {label:26} FAILED - skipped")
            continue
        attached = 0
        for lat, lon in pts:
            p, _ = grid.nearest(lat, lon)
            if p:
                counts[str(p["gid"])] += 1
                attached += 1
        per_tag[label] = {"objects": len(pts), "attached": attached}
        print(f"  {label:26} {len(pts):>8,} objects -> {attached:>8,} attached "
              f"({time.time()-t0:.0f}s)", flush=True)

    write_json("mapping_baseline.json", {
        "generated_at": common.iso(),
        "source": "OpenStreetMap planet via QLever (ODbL)",
        "tags": [f"{k}={v}" for k, v in BASELINE_TAGS],
        "rationale": "population-proportional civic infrastructure, nomad-irrelevant",
        "per_tag": per_tag,
        "counts": dict(counts),
    })
    register("qlever_osm_baseline", source_name="OSM mapping-density baseline (QLever)",
             domain="qlever.dev", source_type="normalisation",
             access_method="anonymous SPARQL", credential_required=False,
             geographic_scope="global", coverage=sum(counts.values()),
             freshness="OSM planet snapshot",
             terms_notes="ODbL; used only to correct for mapping completeness")
    common.save_registry()
    tot = sum(counts.values())
    print(f"done in {time.time()-t0:.0f}s: {tot:,} baseline objects across "
          f"{len(counts):,} localities")


if __name__ == "__main__":
    main()
