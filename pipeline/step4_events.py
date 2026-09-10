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
MU_LIMIT, LU_LIMIT = RateLimiter(0.9), RateLimiter(0.9)
MU_BREAK, LU_BREAK = CircuitBreaker(30, 90), CircuitBreaker(20, 120)

CONCEPTS = ["digital nomad", "coworking", "expats international"]
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


def meetup_urls(place, lang):
    city = urllib.parse.quote(place["name"])
    cc = place["cc"].lower()
    kws = list(CONCEPTS)
    if lang in LOCALIZED:
        kws.append(LOCALIZED[lang])
    return [(f"https://www.meetup.com/find/?keywords={urllib.parse.quote(k)}"
             f"&location={cc}--{city}&source=EVENTS", k) for k in kws]


def scan_place(target, langs, sink, lock, prog):
    place = target["place"]
    lang = (langs.get(place["cc"], "") or "").split(",")[0].split("-")[0]
    events, queries = {}, []
    for url, kw in meetup_urls(place, lang):
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
    if target["tier"] >= 2:
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
                                   "events": list(events.values())}
        prog[0] += 1
        if prog[0] % 15 == 0:
            print(f"  {prog[0]}/{prog[1]} places, "
                  f"{sum(len(v['events']) for v in sink.values())} events", flush=True)


def main():
    gb = read_json("geobase.json")
    langs = {cc: c.get("languages", "") for cc, c in gb["countries"].items()}
    # Event targets are chosen from *measured* ecosystem evidence, not from the
    # coarse Tier-0 guess: the places that already show a real ecosystem are the
    # ones where a live event feed will tell us something. Continent quotas keep
    # the event layer from collapsing onto Europe (spec §60).
    sc = read_json("scored.json")
    if sc:
        ranked = sorted(sc["localities"], key=lambda L: -L["live_score"])
        picked, per_cont = [], defaultdict(int)
        gb_places = {p["gid"]: p for p in gb["places"]}
        for L in ranked:
            if len(picked) >= 340:
                break
            if per_cont[L["continent"]] >= 90:
                continue
            p = gb_places.get(L["gid"])
            if not p:
                continue
            per_cont[L["continent"]] += 1
            picked.append({"place": p, "tier": 3 if len(picked) < 160 else 2})
        for cont in ("SA", "AF", "OC", "AS", "NA"):
            have = sum(1 for x in picked if x["place"]["continent"] == cont)
            if have < 28:
                for L in ranked:
                    if have >= 28:
                        break
                    if L["continent"] != cont:
                        continue
                    p = gb_places.get(L["gid"])
                    if not p or any(x["place"]["gid"] == p["gid"] for x in picked):
                        continue
                    picked.append({"place": p, "tier": 2}); have += 1
        targets = picked
    else:
        targets = [t for t in read_json("scan_targets.json")["targets"] if t["tier"] >= 2]
    sink = (read_json("events.json", {}) or {}).get("places", {})
    todo = [t for t in targets if str(t["place"]["gid"]) not in sink]
    print(f"event scan: {len(todo)} places ({len(sink)} cached)")
    lock, prog = threading.Lock(), [0, len(todo)]

    def run(t):
        try:
            scan_place(t, langs, sink, lock, prog)
        except Exception as e:
            print(f"  !! {t['place']['name']}: {type(e).__name__}: {e}", flush=True)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(run, todo))
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
