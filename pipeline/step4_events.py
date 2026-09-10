"""Step 4 - Live event layer (spec §22, §23, §28, §29).

Sources are public pages that publish schema.org/Event JSON-LD for indexing:
  * meetup.com/find/  - robots.txt permits /find/ (only /files/, /fb/, /preview/,
    /n/* and calendar atom/rss feeds are disallowed). Returns localized events
    with organizer, venue name and street address.
  * luma.com/<city>   - ItemList of Event objects for cities Luma covers.

Queries are generated per place from concept templates and, where the country's
primary language is known, from a localized variant too (spec §29) - not from a
hard-coded destination list.

Events are deduplicated across sources, classified into categories, and scored
on organizer diversity and recency rather than raw count (spec §22).
"""
import html, json, os, re, sys, threading, time, unicodedata, urllib.parse
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register

BROWSER_UA = "Mozilla/5.0 (compatible; NomadRadar/1.0; +https://github.com/granterogers/nomad-map)"
MU_LIMIT, LU_LIMIT = RateLimiter(0.4), RateLimiter(0.9)
MU_BREAK, LU_BREAK = CircuitBreaker(30, 90), CircuitBreaker(20, 120)

CONCEPTS = ["digital nomad", "coworking", "expats international"]
MERIT_BUDGET, RANDOM_BUDGET = 420, 620

LOCALIZED = {
    "es": "nómadas digitales", "pt": "nômades digitais", "fr": "nomades numériques",
    "de": "digitale nomaden", "it": "nomadi digitali", "nl": "digitale nomaden",
    "pl": "cyfrowi nomadzi", "tr": "dijital göçebe", "th": "ดิจิทัลโนแมด",
    "id": "digital nomad indonesia", "vi": "du mục kỹ thuật số", "ja": "ノマドワーカー",
    "ko": "디지털 노마드", "zh": "数字游民", "ru": "цифровые кочевники",
    "cs": "digitální nomádi", "el": "ψηφιακοί νομάδες", "hu": "digitális nomádok",
    "ro": "nomazi digitali", "bg": "дигитални номади", "hr": "digitalni nomadi",
}

CATEGORIES = [
    ("digital nomad", ["nomad", "nômade", "nomade", "remote work", "remoto", "노마드", "游民"]),
    ("coworking", ["cowork", "co-work", "coworking"]),
    ("startup", ["startup", "founder", "pitch", "venture", "entrepreneur", "empreend"]),
    ("technology", ["tech", "developer", "code", "coding", "ai ", "data", "hack", "web3", "python"]),
    ("networking", ["networking", "network", "mixer", "connect"]),
    ("language exchange", ["language exchange", "intercambio", "sprachcafe", "tandem", "polyglot", "conversation club"]),
    ("expat / international", ["expat", "international", "internationals", "erasmus", "newcomers"]),
    ("nightlife", ["party", "night", "club", "bar crawl", "drinks", "rooftop"]),
    ("outdoor / hiking", ["hike", "hiking", "trail", "walk", "trek", "cycling", "surf", "climb"]),
    ("wellness", ["yoga", "meditation", "wellness", "breathwork", "sauna", "mindful", "retreat"]),
    ("sport", ["run", "running", "football", "padel", "tennis", "volleyball", "basketball", "gym"]),
    ("cultural", ["museum", "history", "tour", "culture", "cultural", "film", "book"]),
    ("creative", ["art", "photo", "design", "craft", "draw", "music jam", "writing"]),
    ("music / festival", ["concert", "festival", "dj", "live music", "gig"]),
    ("social", ["social", "meet", "hangout", "coffee", "brunch", "dinner", "games", "board game"]),
]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def classify(text):
    t = text.lower()
    for cat, keys in CATEGORIES:
        if any(k in t for k in keys):
            return cat
    return "other"


def parse_ldjson_events(page: str):
    out = []
    for blk in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        try:
            d = json.loads(blk.strip())
        except Exception:
            continue
        stack = [d]
        while stack:
            n = stack.pop()
            if isinstance(n, list):
                stack.extend(n)
            elif isinstance(n, dict):
                if n.get("@type") == "Event":
                    out.append(n)
                elif n.get("@type") == "ItemList":
                    stack.extend(i.get("item") for i in n.get("itemListElement", []) if isinstance(i, dict))
                elif "itemListElement" in n:
                    stack.extend(n["itemListElement"])
    return out


def norm_event(e, source, place):
    if not isinstance(e, dict):
        return None
    name = html.unescape((e.get("name") or "").strip())
    url = e.get("url") or e.get("@id") or ""
    if not name or not url:
        return None
    loc = e.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    addr = loc.get("address") if isinstance(loc, dict) else None
    if isinstance(addr, str):
        addr = {"streetAddress": addr}
    addr = addr or {}
    org = e.get("organizer") or {}
    if isinstance(org, list):
        org = org[0] if org else {}
    geo = loc.get("geo") if isinstance(loc, dict) else None
    lat = lon = None
    if isinstance(geo, dict):
        try:
            lat, lon = float(geo.get("latitude")), float(geo.get("longitude"))
        except (TypeError, ValueError):
            lat = lon = None
    online = "OnlineEventAttendanceMode" in str(e.get("eventAttendanceMode") or "")
    return {
        "title": name[:160], "url": url,
        "start": (e.get("startDate") or "")[:19],
        "status": "cancelled" if "Cancelled" in str(e.get("eventStatus") or "") else "scheduled",
        "venue": (loc.get("name") or "")[:90] if isinstance(loc, dict) else "",
        "street": (addr.get("streetAddress") or "")[:140],
        "locality": (addr.get("addressLocality") or "")[:60],
        "organizer": (org.get("name") or "")[:90] if isinstance(org, dict) else "",
        "organizer_url": (org.get("url") or "") if isinstance(org, dict) else "",
        "category": classify(name + " " + (e.get("description") or "")[:400]),
        "online": online, "lat": lat, "lon": lon,
        "source": source, "gid": place["gid"],
    }


def meetup_urls(place, lang, deep=True):
    city = urllib.parse.quote(place["name"])
    cc = place["cc"].lower()
    # The random-sample half is a wide net, not a deep probe: two concepts are
    # enough to detect whether an ecosystem exists at all, and the saved budget
    # buys far more places, which is the whole point of sampling randomly.
    kws = list(CONCEPTS) if deep else CONCEPTS[:2]
    if deep and lang in LOCALIZED:
        kws.append(LOCALIZED[lang])
    return [(f"https://www.meetup.com/find/?keywords={urllib.parse.quote(k)}"
             f"&location={cc}--{city}&source=EVENTS", k) for k in kws]


def scan_place(target, langs, sink, lock, prog):
    place = target["place"]
    lang = (langs.get(place["cc"], "") or "").split(",")[0].split("-")[0]
    deep = target.get("selected_for") == "merit"
    events, queries = {}, []
    for url, kw in meetup_urls(place, lang, deep):
        page = fetch(url, source_id="meetup_public", headers={"User-Agent": BROWSER_UA},
                     timeout=40, retries=2, backoff=2.0, limiter=MU_LIMIT, breaker=MU_BREAK,
                     cache_ttl=2 * 86400)
        queries.append({"source": "meetup_public", "query": kw, "ok": page is not None})
        if not page:
            continue
        for raw in parse_ldjson_events(page.decode("utf-8", "replace")):
            ev = norm_event(raw, "meetup_public", place)
            if ev:
                events[ev["url"]] = ev
    if deep and target["tier"] >= 2:
        slug = slugify(place["name"])
        page = fetch(f"https://luma.com/{slug}", source_id="luma_public",
                     headers={"User-Agent": BROWSER_UA}, timeout=35, retries=1,
                     limiter=LU_LIMIT, breaker=LU_BREAK, cache_ttl=2 * 86400)
        queries.append({"source": "luma_public", "query": slug, "ok": page is not None})
        if page:
            txt = page.decode("utf-8", "replace")
            # only trust the page if it is actually about this city
            if re.search(r'events in %s' % re.escape(place["name"]), txt, re.I) or \
               re.search(r'"name":"[^"]*%s' % re.escape(place["name"]), txt, re.I):
                for raw in parse_ldjson_events(txt):
                    ev = norm_event(raw, "luma_public", place)
                    if ev:
                        events.setdefault(ev["url"], ev)
    with lock:
        sink[str(place["gid"])] = {"gid": place["gid"], "name": place["name"], "cc": place["cc"],
                                   "scanned_at": common.iso(), "queries": queries,
                                   "selected_for": target.get("selected_for", "merit"),
                                   "events": list(events.values())}
        prog[0] += 1
        if prog[0] % 15 == 0:
            print(f"  {prog[0]}/{prog[1]} places, "
                  f"{sum(len(v['events']) for v in sink.values())} events", flush=True)


def main():
    gb = read_json("geobase.json")
    langs = {cc: c.get("languages", "") for cc, c in gb["countries"].items()}
    # Event coverage is split in two on purpose (validity audit fix #2).
    #
    # The first implementation chose every event target from the OSM-derived
    # score, which made the event layer confirm the ranking instead of testing
    # it: 53% of covered places were already top-400 before a single event was
    # fetched, and a genuine hotspot with a thin OSM footprint could never earn
    # event points. That is a selection artifact, not discovery.
    #
    # MERIT half   - places the ecosystem layer thinks are interesting.
    # RANDOM half  - a stratified random sample over continent x population
    #                band, drawn with a fixed seed and completely independent of
    #                any score. This is the half that can surprise the model,
    #                and the half that makes the ranked set representative.
    import random
    rng = random.Random(20260910)
    sc = read_json("scored.json")
    gb_places = {p["gid"]: p for p in gb["places"]}
    picked, seen = [], set()

    def add(p, why, tier):
        if p["gid"] in seen:
            return False
        seen.add(p["gid"])
        picked.append({"place": p, "tier": tier, "selected_for": why})
        return True

    if sc:
        ranked = sorted(sc["localities"], key=lambda L: -L["live_score"])
        per_cont = defaultdict(int)
        for L in ranked:
            if len(picked) >= MERIT_BUDGET:
                break
            if per_cont[L["continent"]] >= MERIT_BUDGET * 0.42:
                continue
            p = gb_places.get(L["gid"])
            if p:
                per_cont[L["continent"]] += 1
                add(p, "merit", 3 if len(picked) < 170 else 2)

    # stratified random draw
    def band(pop):
        return 0 if pop < 25000 else 1 if pop < 100000 else 2 if pop < 400000 else \
               3 if pop < 1500000 else 4
    strata = defaultdict(list)
    for p in gb["places"]:
        if p["pop"] >= 12000:
            strata[(p["continent"], band(p["pop"]))].append(p)
    keys = sorted(strata)
    total = sum(len(strata[k]) for k in keys)
    for k in keys:
        # proportional to stratum size, softened so small continents are not erased
        share = (len(strata[k]) / total) ** 0.62
        n = max(2, int(RANDOM_BUDGET * share))
        pool = strata[k][:]
        rng.shuffle(pool)
        got = 0
        for p in pool:
            if got >= n:
                break
            if add(p, "random", 2):
                got += 1
    print(f"targets: {sum(1 for t in picked if t['selected_for']=='merit')} merit + "
          f"{sum(1 for t in picked if t['selected_for']=='random')} stratified random "
          f"= {len(picked)}")
    from collections import Counter as _C
    print("  by continent:", dict(_C(t["place"]["continent"] for t in picked)))
    targets = picked

    sink = (read_json("events.json", {}) or {}).get("places", {})
    todo = [t for t in targets if str(t["place"]["gid"]) not in sink]
    print(f"event scan: {len(todo)} places ({len(sink)} cached)")
    lock, prog = threading.Lock(), [0, len(todo)]

    def run(t):
        try:
            scan_place(t, langs, sink, lock, prog)
        except Exception as e:
            print(f"  !! {t['place']['name']}: {type(e).__name__}: {e}", flush=True)

    # Save periodically and honour a wall-clock budget. HTTP responses are
    # cached, so a run that stops early and is resumed later replays what it
    # already fetched almost instantly and carries on. Merit targets are
    # processed first so the deep probes are never the ones dropped.
    t0 = time.time()
    budget = float(os.environ.get("EVENT_BUDGET_S", 2100))
    stop, last_saved = threading.Event(), [0]

    def run_budgeted(t):
        if stop.is_set():
            return
        run(t)
        with lock:
            # threshold, not modulo: with several workers the exact multiple is
            # skipped between a thread's own increment and its check
            if prog[0] - last_saved[0] >= 50:
                last_saved[0] = prog[0]
                write_json("events.json", {"generated_at": common.iso(), "places": sink})
            if time.time() - t0 > budget and not stop.is_set():
                stop.set()
                print(f"  budget reached at {prog[0]}/{prog[1]} - saving and stopping", flush=True)

    todo.sort(key=lambda t: 0 if t.get("selected_for") == "merit" else 1)
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(run_budgeted, todo))
    write_json("events.json", {"generated_at": common.iso(), "places": sink})
    for sid, name, dom in [("meetup_public", "Meetup public /find pages (schema.org Event)", "meetup.com"),
                           ("luma_public", "Luma public city pages (schema.org ItemList/Event)", "luma.com")]:
        register(sid, source_name=name, domain=dom, source_type="events",
                 access_method="anonymous HTML + JSON-LD", credential_required=False,
                 geographic_scope="global (coverage varies)", freshness="live listings",
                 terms_notes="public indexable structured data only; robots.txt respected")
    common.save_registry()
    tot = sum(len(v["events"]) for v in sink.values())
    print(f"done in {time.time()-t0:.0f}s: {len(sink)} places, {tot} events")


if __name__ == "__main__":
    main()
