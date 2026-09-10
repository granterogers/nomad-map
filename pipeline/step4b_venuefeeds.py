"""Step 4b - event feeds published by the coworking spaces themselves.

Validity audit fix #5. The strongest evidence a place has a live nomad scene is
that its coworking spaces are running events - and the ecosystem layer already
knows exactly where those spaces are. ~5,100 of them publish a website in OSM.

This visits each one politely (one request, then at most one more for a feed it
advertises) and extracts schema.org Events, iCalendar feeds or RSS/Atom feeds.
Unlike Meetup, this evidence is attached to a PRECISE coordinate, so it lands in
an H3 cell rather than at city precision - and it is independent of whether a
city happens to have a Meetup presence, which is what most of the unranked
tier-3 hubs were missing.
"""
import html, json, os, re, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register
from step3_ecosystem import QLEVER, PREFIX, POINT_RE, PlaceGrid
from step4_events import parse_ldjson_events, classify

UA = "Mozilla/5.0 (compatible; NomadRadar/1.0; +https://github.com/granterogers/nomad-map)"
LIM = RateLimiter(0.05)          # per-host politeness comes from breadth, not queueing
MAX_SITES = 4200

FEED_LINK = re.compile(
    r'<link[^>]+type=["\'](?:text/calendar|application/rss\+xml|application/atom\+xml)["\'][^>]*>',
    re.I)
HREF = re.compile(r'href=["\']([^"\']+)["\']', re.I)
ICS_EVENT = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.S)
ICS_FIELD = lambda k, b: (re.search(rf"^{k}[^:]*:(.*)$", b, re.M) or [None, ""])[1].strip()


def pull_sites():
    q = PREFIX + """SELECT ?o ?nm ?w (geof:centroid(?g) AS ?c) WHERE {
  { ?o osmkey:office "coworking" } UNION { ?o osmkey:amenity "coworking_space" }
  UNION { ?o osmkey:leisure "hackerspace" } UNION { ?o osmkey:residential "coliving" }
  ?o osmkey:website ?w ; geo:hasGeometry/geo:asWKT ?g .
  OPTIONAL { ?o osmkey:name ?nm }
} LIMIT 12000"""
    res = fetch(QLEVER, source_id="qlever_osm", data=q.encode(),
                headers={"Content-Type": "application/sparql-query",
                         "Accept": "application/qlever-results+json"},
                timeout=180, retries=2, as_json=True, cache_ttl=5 * 86400)
    if not res or res.get("status") != "OK":
        return []
    out, seen = [], set()
    for row in res.get("res", []):
        oid, nm, w, wkt = row[0], row[1], row[2], row[3]
        m = POINT_RE.search(wkt or "")
        if not m:
            continue
        url = (w or "").strip('"').strip()
        if not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        host = urllib.parse.urlparse(url).netloc.lower()
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"osm": oid.strip("<>").rsplit("openstreetmap.org/", 1)[-1],
                    "name": (nm or "").strip('"')[:80], "url": url,
                    "lat": round(float(m.group(2)), 5), "lon": round(float(m.group(1)), 5)})
    return out


def parse_ics(text, limit=25):
    out = []
    now = datetime.now(timezone.utc)
    for blk in ICS_EVENT.findall(text)[:200]:
        summary = ICS_FIELD("SUMMARY", blk)
        dt = ICS_FIELD("DTSTART", blk)
        if not summary:
            continue
        iso = ""
        m = re.match(r"(\d{4})(\d{2})(\d{2})", dt)
        if m:
            iso = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00"
            try:
                d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
                age = abs((d - now).total_seconds() / 3600.0)
                if age > 2160:
                    continue
            except ValueError:
                pass
        out.append({"title": summary[:160], "start": iso})
        if len(out) >= limit:
            break
    return out


def parse_rss(text, limit=25):
    out = []
    for item in re.findall(r"<(?:item|entry)>(.*?)</(?:item|entry)>", text, re.S)[:60]:
        t = re.search(r"<title[^>]*>(.*?)</title>", item, re.S)
        d = re.search(r"<(?:pubDate|updated|published)>(.*?)</", item, re.S)
        if not t:
            continue
        title = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
        if title:
            out.append({"title": title[:160], "start": (d.group(1)[:19] if d else "")})
        if len(out) >= limit:
            break
    return out


def probe(site, sink, lock, prog):
    page = fetch(site["url"], source_id="venue_feeds", headers={"User-Agent": UA},
                 timeout=14, retries=0, limiter=LIM, cache_ttl=3 * 86400)
    events, how = [], None
    if page:
        txt = page.decode("utf-8", "replace")[:400000]
        for raw in parse_ldjson_events(txt):
            if isinstance(raw, dict) and raw.get("name"):
                events.append({"title": str(raw["name"])[:160],
                               "start": str(raw.get("startDate") or "")[:19]})
        if events:
            how = "schema.org on site"
        else:
            tag = FEED_LINK.search(txt)
            if tag:
                href = HREF.search(tag.group(0))
                if href:
                    feed = urllib.parse.urljoin(site["url"], html.unescape(href.group(1)))
                    body = fetch(feed, source_id="venue_feeds", headers={"User-Agent": UA},
                                 timeout=14, retries=0, limiter=LIM, cache_ttl=3 * 86400)
                    if body:
                        b = body.decode("utf-8", "replace")[:300000]
                        if "BEGIN:VCALENDAR" in b:
                            events, how = parse_ics(b), "iCalendar feed"
                        else:
                            events, how = parse_rss(b), "RSS/Atom feed"
    with lock:
        prog[0] += 1
        if events:
            sink.append({**site, "events": events[:20], "via": how})
        if prog[0] % 200 == 0:
            print(f"  {prog[0]}/{prog[1]} sites, {len(sink)} with feeds, "
                  f"{sum(len(s['events']) for s in sink)} events", flush=True)


def main():
    gb = read_json("geobase.json")
    grid = PlaceGrid(gb["places"])
    sites = pull_sites()[:MAX_SITES]
    print(f"coworking/hackerspace/coliving sites with a website: {len(sites)}")
    sink, lock, prog = [], threading.Lock(), [0, len(sites)]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=14) as ex:
        list(ex.map(lambda s: probe(s, sink, lock, prog), sites))

    by_place = {}
    for s in sink:
        p, _ = grid.nearest(s["lat"], s["lon"])
        if not p:
            continue
        rec = by_place.setdefault(str(p["gid"]), {"gid": p["gid"], "name": p["name"],
                                                  "cc": p["cc"], "venues": []})
        rec["venues"].append({
            "osm": s["osm"], "venue": s["name"], "url": s["url"], "via": s["via"],
            "lat": s["lat"], "lon": s["lon"],
            "events": [{**e, "category": classify(e["title"])} for e in s["events"]]})
    write_json("venue_feeds.json", {
        "generated_at": common.iso(), "sites_probed": len(sites),
        "sites_with_feeds": len(sink), "places": by_place})
    register("venue_feeds", source_name="Coworking-space event feeds (ICS/RSS/schema.org)",
             domain="various (from OSM website tags)", source_type="events",
             access_method="anonymous, one request per site", credential_required=False,
             geographic_scope="wherever OSM records a coworking website",
             coverage=len(sink), freshness="live",
             terms_notes="public feeds the venue publishes for syndication")
    common.save_registry()
    print(f"done in {time.time()-t0:.0f}s: {len(sink)}/{len(sites)} sites had a feed, "
          f"{sum(len(s['events']) for s in sink)} events across {len(by_place)} localities")


if __name__ == "__main__":
    main()
