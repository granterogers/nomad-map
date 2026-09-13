"""Step 1b - local-language Wikipedia crosswalk (reduces anglophone bias).

The attention layer measured English Wikipedia only, which structurally
under-measures places whose readers do not read English Wikipedia. The Tier-0
ranking already normalises attention within country to compensate, but that is a
patch over a hole rather than a fix.

This pulls the sitelink for each place in its own country's primary language
wiki, so a place's attention is the sum of what English readers AND local
readers actually looked at. Same dump files, no extra bandwidth - just a wider
filter.
"""
import os, sys, urllib.parse
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter

WD = RateLimiter(1.2)

# Wikipedia editions worth querying: every language that is primary somewhere
# with a meaningful number of places in the universe.
# Ordered by how much bias each removes: the editions whose readers are most
# under-counted by an English-only attention layer, in regions that matter most
# for this product. The list is truncated rather than exhaustive because each
# edition costs several minutes against the public endpoint, and the tail
# editions add very little coverage.
WIKIS = ["es","pt","id","th","vi","tr","de","fr","it","ru","ja","pl",
         "ko","nl","cs","el","hu","bg","hr","ro","ka","uk"]

SPARQL = """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
SELECT ?gn ?article WHERE {
  ?city wdt:P1566 ?gn ; wdt:P1082 ?pop .
  FILTER(?pop >= 4000)
  ?article schema:about ?city ; schema:isPartOf <https://%s.wikipedia.org/> .
}"""

# The public Wikidata Query Service times out on the large editions (es, ru, ja,
# it, pl, ko all failed there), which is why only five editions had landed. The
# same query against QLever's Wikidata index returns 100k rows in six seconds,
# so it is tried first and WDQS is kept only as a fallback.
QLEVER_WD = "https://qlever.dev/api/wikidata"


def _sitelinks(w):
    res = fetch(QLEVER_WD, source_id="qlever_wikidata", data=(SPARQL % w).encode(),
                headers={"Accept": "application/sparql-results+json",
                         "Content-type": "application/sparql-query"},
                timeout=240, retries=2, limiter=WD, as_json=True,
                cache_ttl=14 * 86400, cache_key=f"qlwd_lang_{w}")
    if res and "results" in res:
        return res["results"]["bindings"]
    res = fetch("https://query.wikidata.org/sparql", source_id="wikidata_sparql",
                data=urllib.parse.urlencode({"query": SPARQL % w}),
                headers={"Accept": "application/sparql-results+json"},
                timeout=240, retries=2, limiter=WD, as_json=True,
                cache_ttl=14 * 86400, cache_key=f"wd_lang_{w}")
    return res["results"]["bindings"] if res and "results" in res else None


def main():
    gb = read_json("geobase.json")
    # which language does each country actually read?
    lang_of_cc = {}
    for cc, c in gb["countries"].items():
        primary = (c.get("languages") or "").split(",")[0].split("-")[0].strip()
        if primary:
            lang_of_cc[cc] = primary
    wanted = {lang_of_cc.get(p["cc"]) for p in gb["places"]}
    wikis = [w for w in WIKIS if w in wanted]
    print(f"{len(wikis)} language editions cover the countries in the universe")

    by_gid = defaultdict(list)
    landed = []          # only editions that actually returned are claimed
    for w in wikis:
        rows = _sitelinks(w)
        if rows is None:
            print(f"  {w:4} FAILED - skipped")
            continue
        n = 0
        for b in rows:
            try:
                gid = int(b["gn"]["value"])
            except ValueError:
                continue
            title = urllib.parse.unquote(b["article"]["value"].rsplit("/", 1)[-1])
            by_gid[gid].append([w, title.replace(" ", "_")])
            n += 1
        print(f"  {w:4} {n:>7,} sitelinks (total places {len(by_gid):,})", flush=True)
        landed.append(w)
        _save(gb, lang_of_cc, by_gid, landed)     # partial runs stay useful

    _save(gb, lang_of_cc, by_gid, landed)
    common.save_registry()
    print(f"local-language titles attached to "
          f"{len(read_json('locallang.json', {'places': {}})['places']):,} places")


def _save(gb, lang_of_cc, by_gid, wikis):
    """Written after every edition so a partial run is still useful."""
    out = {}
    for p in gb["places"]:
        want = lang_of_cc.get(p["cc"])
        if not want:
            continue
        for lang, title in by_gid.get(p["gid"], []):
            if lang == want:
                out[str(p["gid"])] = [lang, title]
                break
    write_json("locallang.json", {"generated_at": common.iso(),
                                  "wikis_queried": wikis, "places": out})


if __name__ == "__main__":
    main()
