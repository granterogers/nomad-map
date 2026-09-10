"""Step 1 - Global geographic baseline (spec §5, §16, §62).

Builds the complete world candidate universe from GeoNames (every populated
place >= 15k people, ~34k places, 200+ countries) and joins an authoritative
GeoNames -> English Wikipedia crosswalk from Wikidata so the attention layer
can attach real pageview evidence.

No city list is hard-coded anywhere: the world is the query.
"""
import csv, io, json, os, sys, time, urllib.parse, zipfile
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, write_json, read_json, RateLimiter, register

RAW = os.path.join(common.DATA, "raw")
WD = RateLimiter(1.2)

GEONAMES_COLS = ["geonameid","name","asciiname","alternatenames","lat","lon","fclass","fcode",
                 "country","cc2","admin1","admin2","admin3","admin4","population","elevation",
                 "dem","timezone","moddate"]


def load_countries():
    out = {}
    for line in open(os.path.join(RAW, "countryInfo.txt"), encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.rstrip("\n").split("\t")
        if len(f) < 17:
            continue
        out[f[0]] = {"iso2": f[0], "iso3": f[1], "name": f[4], "continent": f[8],
                     "capital": f[5], "population": int(f[7] or 0),
                     "area_km2": float(f[6] or 0), "languages": f[15]}
    return out


def load_admin1():
    out = {}
    for line in open(os.path.join(RAW, "admin1CodesASCII.txt"), encoding="utf-8"):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 2:
            out[f[0]] = f[1]
    return out


def load_places():
    places = []
    with open(os.path.join(RAW, "cities5000.txt"), encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) < 19:
                continue
            r = dict(zip(GEONAMES_COLS, row))
            try:
                pop = int(r["population"] or 0)
                lat, lon = float(r["lat"]), float(r["lon"])
            except ValueError:
                continue
            if pop < 5000:
                continue
            places.append({
                "gid": int(r["geonameid"]), "name": r["name"], "ascii": r["asciiname"],
                "lat": round(lat, 4), "lon": round(lon, 4), "cc": r["country"],
                "admin1": r["admin1"], "admin2": r["admin2"], "pop": pop, "tz": r["timezone"],
                "fcode": r["fcode"], "dem": int(r["dem"] or 0),
            })
    return places


SPARQL = """SELECT ?gn ?article WHERE {
  ?city wdt:P1566 ?gn ; wdt:P1082 ?pop .
  FILTER(?pop >= %d && ?pop < %d)
  ?article schema:about ?city ; schema:isPartOf <https://en.wikipedia.org/> .
}"""

BANDS = [(5000, 15000), (15000, 25000), (25000, 40000), (40000, 60000), (60000, 90000), (90000, 140000),
         (140000, 220000), (220000, 400000), (400000, 800000), (800000, 2000000),
         (2000000, 100000000)]


def wikidata_crosswalk():
    """GeoNames id -> en.wikipedia title, pulled in population bands to stay
    inside the public SPARQL endpoint's time budget."""
    mapping = {}
    for lo, hi in BANDS:
        q = SPARQL % (lo, hi)
        res = fetch("https://query.wikidata.org/sparql", source_id="wikidata_sparql",
                    data=urllib.parse.urlencode({"query": q}),
                    headers={"Accept": "application/sparql-results+json"},
                    timeout=180, retries=3, limiter=WD, as_json=True,
                    cache_ttl=14 * 86400, cache_key=f"wd_band_{lo}_{hi}")
        if not res:
            print(f"  band {lo}-{hi}: FAILED (continuing)")
            continue
        rows = res["results"]["bindings"]
        n = 0
        for b in rows:
            try:
                gid = int(b["gn"]["value"])
            except ValueError:
                continue
            title = urllib.parse.unquote(b["article"]["value"].rsplit("/", 1)[-1])
            # keep the first / shortest title per geonames id (most canonical)
            if gid not in mapping or len(title) < len(mapping[gid]):
                mapping[gid] = title
            n += 1
        print(f"  band {lo}-{hi}: {len(rows)} rows -> {n} mapped (total {len(mapping)})")
    return mapping


def main():
    countries, admin1 = load_countries(), load_admin1()
    places = load_places()
    print(f"GeoNames places >=5k: {len(places)} across "
          f"{len({p['cc'] for p in places})} countries/territories")

    print("Wikidata crosswalk...")
    xwalk = wikidata_crosswalk()
    common.save_registry()

    hit = 0
    for p in places:
        t = xwalk.get(p["gid"])
        if t:
            p["wiki"] = t
            hit += 1
        c = countries.get(p["cc"], {})
        p["country"] = c.get("name", p["cc"])
        p["continent"] = c.get("continent", "")
        p["admin1_name"] = admin1.get(f'{p["cc"]}.{p["admin1"]}', "")
    print(f"Wikipedia titles attached to {hit}/{len(places)} places ({100*hit/len(places):.1f}%)")

    write_json("geobase.json", {
        "generated_at": common.iso(),
        "source": "GeoNames cities5000 (CC-BY 4.0) + Wikidata SPARQL crosswalk",
        "countries": countries, "admin1": admin1, "places": places,
    })
    register("geonames_cities5000", source_name="GeoNames cities5000 dump",
             domain="download.geonames.org", source_type="geography",
             access_method="anonymous bulk download", credential_required=False,
             geographic_scope="global", coverage=len(places), freshness="monthly dump",
             terms_notes="CC-BY 4.0")
    register("wikidata_sparql", source_name="Wikidata Query Service",
             domain="query.wikidata.org", source_type="geography/crosswalk",
             access_method="anonymous SPARQL", credential_required=False,
             geographic_scope="global", coverage=len(xwalk), freshness="live",
             terms_notes="CC0")
    common.save_registry()
    print("wrote data/geobase.json")


if __name__ == "__main__":
    main()
