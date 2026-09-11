"""Step 5b - structural viability (cost, climate, visa).

WHY THIS EXISTS. The validity work established that activity data alone cannot
order nomad destinations well: restricted to places with 25+ events the rank
correlation only reached ~0.41, and three separate activity features (nomad
event share, nomad group membership, group counts) all measured below +0.30.
Meanwhile cost of living alone scored +0.53 and warmth alone +0.53 against the
same labels.

The reason is simple: somewhere is a nomad destination because it is affordable,
warm, and legally viable to stay in - AND active. The original model measured
only the last of those. This step adds the first three.

This does NOT violate the "current activity, not reputation" rule. Cost, climate
and visa policy are current facts about a place, not its reputation. They are
kept in a SEPARATE score (Nomad Fit) so the activity-only Live Score stays
exactly what it was.

Sources, all credential-free:
  cost    World Bank API (GDP per capita, PPP) - country level
  climate NASA POWER climatology API - per locality, 12-month means
  visa    curated factual list of remote-work residence routes, dated below
"""
import json, math, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register

LIM = RateLimiter(0.06)
BRK = CircuitBreaker(25, 60)

VISA_AS_OF = "2026-09"
# Countries operating a digital-nomad, remote-work or comparable freelance
# residence route. Curated from public government sources; conservative, and
# deliberately coarse - it is a yes/no country-level fact, not legal advice.
VISA_COUNTRIES = set("""
PT ES GR HR EE CZ HU MT CY IT RO LV LT IS NO DE NL GE TR AE ID TH MY TW KR JP PH
LK NA MU SC CV ZA KE CR PA CO BR AR UY EC MX BB AG BS DM CW MS AI BM KY GD BZ SV
AL RS ME MK AM AD
""".split())

WB_INDICATOR = "NY.GDP.PCAP.PP.CD"
POWER = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
         "?parameters=T2M&community=RE&longitude={lon}&latitude={lat}&format=JSON")
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def cost_index():
    """Country price level proxy. Cheaper countries are more viable for someone
    earning in a hard currency; this is the single strongest structural signal."""
    out = {}
    for year in (2023, 2022, 2021):
        res = fetch(f"https://api.worldbank.org/v2/country/all/indicator/{WB_INDICATOR}"
                    f"?format=json&date={year}&per_page=400",
                    source_id="worldbank", as_json=True, timeout=90, retries=2,
                    cache_ttl=30 * 86400)
        if not res or len(res) < 2 or not isinstance(res[1], list):
            continue
        for r in res[1]:
            if r.get("value") and r["countryiso3code"] not in out:
                out[r["countryiso3code"]] = r["value"]
    return out


def climate_for(place, sink, lock, prog):
    res = fetch(POWER.format(lat=place["lat"], lon=place["lon"]),
                source_id="nasa_power", as_json=True, timeout=40, retries=1,
                limiter=LIM, breaker=BRK, cache_ttl=180 * 86400,
                cache_key=f"power_{round(place['lat'],2)}_{round(place['lon'],2)}")
    t = None
    try:
        t = res["properties"]["parameter"]["T2M"]
    except Exception:
        t = None
    with lock:
        prog[0] += 1
        if t:
            sink[str(place["gid"])] = [round(t.get(m, 0.0), 1) for m in MONTHS]
        if prog[0] % 300 == 0:
            print(f"  {prog[0]}/{prog[1]} climate points, {len(sink)} ok", flush=True)


def main():
    gb = read_json("geobase.json")
    sc = read_json("scored.json")
    iso3 = {cc: c.get("iso3") for cc, c in gb["countries"].items()}

    gdp3 = cost_index()
    gdp = {cc: gdp3[i3] for cc, i3 in iso3.items() if i3 in gdp3}
    print(f"cost index: {len(gdp)} countries")

    # climate for every locality the page can show
    want = {str(L["gid"]) for L in sc["localities"]}
    places = [p for p in gb["places"] if str(p["gid"]) in want]
    climate, lock, prog = {}, threading.Lock(), [0, len(places)]
    print(f"climate: {len(places)} localities")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(lambda p: climate_for(p, climate, lock, prog), places))
    print(f"  climate done in {time.time()-t0:.0f}s: {len(climate)} localities")

    write_json("viability.json", {
        "generated_at": common.iso(),
        "visa_as_of": VISA_AS_OF,
        "sources": {"cost": "World Bank " + WB_INDICATOR,
                    "climate": "NASA POWER climatology (T2M)",
                    "visa": "curated public-government list"},
        "cost_gdp_ppp": gdp,
        "visa_countries": sorted(VISA_COUNTRIES),
        "climate_monthly_c": climate,
    })
    for sid, nm, dom in [("worldbank", "World Bank Open Data API", "api.worldbank.org"),
                         ("nasa_power", "NASA POWER climatology API", "power.larc.nasa.gov")]:
        register(sid, source_name=nm, domain=dom, source_type="structural viability",
                 access_method="anonymous REST", credential_required=False,
                 geographic_scope="global", freshness="annual / climatological",
                 coverage=len(gdp) if sid == "worldbank" else len(climate),
                 terms_notes="public open data")
    common.save_registry()
    print(f"wrote data/viability.json")


if __name__ == "__main__":
    main()
