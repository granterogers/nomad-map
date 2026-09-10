#!/usr/bin/env python3
"""Nomad Radar - source feasibility audit.
Tests candidate public data sources for credential-free automated access.
Writes results to data/source_audit.json (consumed by docs/DATA_SOURCES.md generator).
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error, ssl, socket
from concurrent.futures import ThreadPoolExecutor

UA = "NomadRadar/1.0 (open-data research bot; +https://github.com/granterogers/nomad-map)"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "source_audit.json")

# name, family, url, method, body(or None), needs_credential, notes
PROBES = [
 # --- Open geography ---
 ("OpenStreetMap Overpass (overpass-api.de)","geo","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];node["amenity"="coworking_space"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Primary physical-ecosystem source"),
 ("OpenStreetMap Overpass (osm.ch mirror)","geo","https://overpass.osm.ch/api/interpreter","POST",'data=[out:json][timeout:25];node["amenity"="coworking_space"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Failover mirror"),
 ("Overpass (kumi.systems mirror)","geo","https://overpass.kumi.systems/api/interpreter","POST",'data=[out:json][timeout:25];out count;',False,"Mirror"),
 ("Wikidata SPARQL","geo","https://query.wikidata.org/sparql","POST",'query=SELECT ?c WHERE { ?c wdt:P31 wd:Q515 } LIMIT 2',False,"City/admin hierarchy + population"),
 ("Nominatim geocoder","geo","https://nominatim.openstreetmap.org/search?q=Lisbon&format=json&limit=1","GET",None,False,"Geocoding fallback, 1 req/s"),
 ("GeoNames dump (cities15000)","geo","https://download.geonames.org/export/dump/readme.txt","GET",None,False,"Bulk populated places"),
 ("Natural Earth (raw github)","geo","https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson","GET",None,False,"Country boundaries"),
 ("REST Countries","geo","https://restcountries.com/v3.1/all?fields=cca2,name,latlng,region","GET",None,False,"Country metadata"),
 ("OSM Nominatim reverse","geo","https://nominatim.openstreetmap.org/reverse?lat=38.71&lon=-9.14&format=json","GET",None,False,"Reverse geocode for neighbourhood names"),
 ("Overpass admin boundaries","geo","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];rel["admin_level"="8"]["name"="Lisboa"](38.6,-9.3,38.85,-9.05);out ids 2;',False,"Admin hierarchy"),
 # --- Current attention / momentum ---
 ("Wikimedia Pageviews REST","attention","https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Lisbon/daily/20260801/20260810","GET",None,False,"Daily article views = live interest time series"),
 ("Wikimedia top-pageviews","attention","https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2026/08/01","GET",None,False,"Trending articles"),
 ("Wikipedia REST summary","attention","https://en.wikipedia.org/api/rest_v1/page/summary/Lisbon","GET",None,False,"Article metadata + coords"),
 ("Wikipedia geosearch API","geo","https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=38.72%7C-9.14&gsradius=10000&gslimit=5&format=json","GET",None,False,"Nearby notable places"),
 ("Wikimedia Commons API","attention","https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=coworking&format=json&srlimit=2","GET",None,False,"Weak signal"),
 ("Google Trends (unofficial)","attention","https://trends.google.com/trends/api/explore","GET",None,False,"Unofficial, expect block"),
 # --- Events ---
 ("Luma public discover","events","https://lu.ma/discover","GET",None,False,"Public event pages"),
 ("Luma public city page","events","https://lu.ma/lisbon","GET",None,False,"City event listings"),
 ("Meetup public find page","events","https://www.meetup.com/find/?keywords=digital%20nomad","GET",None,False,"Public listings"),
 ("Meetup GraphQL API","events","https://api.meetup.com/find/upcoming_events","GET",None,True,"OAuth required"),
 ("Eventbrite public search","events","https://www.eventbrite.com/d/portugal--lisbon/events/","GET",None,False,"Public listings"),
 ("Eventbrite API v3","events","https://www.eventbriteapi.com/v3/events/search/","GET",None,True,"API key required"),
 ("Partiful","events","https://partiful.com/","GET",None,False,"Mostly private events"),
 ("Eventful / misc ICS probe","events","https://www.gcal.example/nonexistent.ics","GET",None,False,"Control probe (expected fail)"),
 ("OpenStreetMap events venues (Overpass)","events","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];node["amenity"="events_venue"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Venue infrastructure"),
 ("Wikimedia Meetup calendars","events","https://meta.wikimedia.org/w/api.php?action=query&list=search&srsearch=meetup&format=json&srlimit=2","GET",None,False,"Marginal"),
 # --- Community ---
 ("Reddit public JSON","community","https://www.reddit.com/r/digitalnomad/new.json?limit=5","GET",None,False,"Historically open, now bot-blocked"),
 ("Reddit RSS","community","https://www.reddit.com/r/digitalnomad/.rss","GET",None,False,"RSS variant"),
 ("Reddit OAuth API","community","https://oauth.reddit.com/r/digitalnomad/new","GET",None,True,"Requires app credentials"),
 ("Hacker News Algolia API","community","https://hn.algolia.com/api/v1/search?query=digital%20nomad&tags=story&hitsPerPage=5","GET",None,False,"Open, no key"),
 ("Lobste.rs JSON","community","https://lobste.rs/newest.json","GET",None,False,"Tech community"),
 ("Mastodon public timeline (mastodon.social)","community","https://mastodon.social/api/v1/timelines/public?limit=5","GET",None,False,"Open fediverse API"),
 ("Mastodon hashtag timeline","community","https://mastodon.social/api/v1/timelines/tag/digitalnomad?limit=5","GET",None,False,"Geo-taggable community signal"),
 ("Lemmy public API","community","https://lemmy.world/api/v3/post/list?limit=5&sort=New","GET",None,False,"Fediverse forum"),
 ("Bluesky public AppView search","community","https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=digital%20nomad&limit=5","GET",None,False,"Unauthenticated public AppView"),
 ("Telegram public channel preview","community","https://t.me/s/durov","GET",None,False,"Public channel web preview"),
 ("Discord discovery","community","https://discord.com/api/v9/discovery/search?query=nomad","GET",None,True,"Auth required"),
 ("Facebook Groups","community","https://www.facebook.com/groups/","GET",None,True,"Login wall"),
 ("Instagram","community","https://www.instagram.com/explore/tags/digitalnomad/","GET",None,True,"Login wall"),
 ("X / Twitter","community","https://api.twitter.com/2/tweets/search/recent?query=nomad","GET",None,True,"Paid API"),
 ("LinkedIn","community","https://www.linkedin.com/feed/","GET",None,True,"Login wall"),
 ("InterNations","community","https://www.internations.org/","GET",None,True,"Membership wall"),
 ("Couchsurfing","community","https://www.couchsurfing.com/","GET",None,True,"Login wall"),
 ("Nomads.com (nomadlist)","community","https://nomads.com/","GET",None,True,"Paid membership"),
 ("Coworker.com","infra","https://www.coworker.com/","GET",None,False,"Directory, ToS-restricted scraping"),
 # --- Physical ecosystem via OSM (all credential-free) ---
 ("OSM coliving","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["residential"="coliving"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Coliving"),
 ("OSM hackerspace","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["leisure"="hackerspace"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Maker/tech community"),
 ("OSM internet_cafe","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"="internet_cafe"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Connectivity venue"),
 ("OSM hostel","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["tourism"="hostel"](38.6,-9.3,38.85,-9.05);out center 2;',False,"International traveller density"),
 ("OSM language school","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"="language_school"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Language exchange proxy"),
 ("OSM cafe with wifi","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"="cafe"]["internet_access"~"wlan|yes"](38.70,-9.16,38.73,-9.13);out center 2;',False,"Work-friendly cafés"),
 ("OSM university","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"="university"](38.6,-9.3,38.85,-9.05);out center 2;',False,"International student hubs"),
 ("OSM international airport","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["aeroway"="aerodrome"]["aerodrome:type"="international"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Connectivity"),
 ("OSM nightlife (bar/pub/nightclub)","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"~"^(bar|pub|nightclub)$"](38.70,-9.16,38.72,-9.13);out center 2;',False,"Social ecosystem"),
 ("OSM wellness (yoga/gym)","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["leisure"="fitness_centre"](38.70,-9.16,38.73,-9.13);out center 2;',False,"Wellness ecosystem"),
 ("OSM community centre","infra","https://overpass-api.de/api/interpreter","POST",'data=[out:json][timeout:25];nwr["amenity"="community_centre"](38.6,-9.3,38.85,-9.05);out center 2;',False,"Community infrastructure"),
 ("Google Places API","infra","https://maps.googleapis.com/maps/api/place/textsearch/json?query=coworking","GET",None,True,"API key + billing"),
 ("Foursquare Places API","infra","https://api.foursquare.com/v3/places/search","GET",None,True,"API key"),
 ("AirDNA","infra","https://www.airdna.co/","GET",None,True,"Commercial paid"),
 # --- Local current intelligence ---
 ("Wikinews RSS","media","https://en.wikinews.org/w/index.php?title=Special:NewsFeed&feed=rss","GET",None,False,"Open news feed"),
 ("GDELT 2.0 doc API","media","https://api.gdeltproject.org/api/v2/doc/doc?query=%22digital%20nomad%22&mode=artlist&format=json&maxrecords=5","GET",None,False,"Global news monitoring, no key"),
 ("GDELT geo API","media","https://api.gdeltproject.org/api/v2/geo/geo?query=%22digital%20nomads%22&format=geojson","GET",None,False,"Geolocated news mentions"),
 ("OpenAQ air quality","media","https://api.openaq.org/v3/locations?limit=1","GET",None,True,"Now requires key"),
 ("Open-Meteo weather","media","https://api.open-meteo.com/v1/forecast?latitude=38.72&longitude=-9.14&daily=temperature_2m_max&forecast_days=1","GET",None,False,"No key, liveability context"),
 ("Protomaps public tiles","map","https://demo-bucket.protomaps.com/v4.pmtiles","HEAD",None,False,"Basemap option"),
 ("OSM raster tiles","map","https://tile.openstreetmap.org/3/4/2.png","GET",None,False,"Basemap (CSP-blocked in artifact host)"),
]

def probe(p):
    name, family, url, method, body, needs_cred, notes = p
    rec = dict(source=name, family=family, url=url, credential_required=needs_cred, notes=notes)
    t0 = time.time()
    try:
        data = body.encode() if body else None
        req = urllib.request.Request(url, data=data, method=("POST" if body else method))
        req.add_header("User-Agent", UA)
        req.add_header("Accept", "application/json, text/html, */*")
        if body:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read(20000)
            rec.update(http=r.status, bytes=len(raw), content_type=r.headers.get("Content-Type", ""),
                       sample=raw[:160].decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        rec.update(http=e.code, bytes=0, error=f"HTTP {e.code} {e.reason}")
    except Exception as e:
        rec.update(http=0, bytes=0, error=f"{type(e).__name__}: {e}")
    rec["ms"] = int((time.time() - t0) * 1000)
    ok = rec.get("http") == 200 and rec.get("bytes", 0) > 50
    if needs_cred:
        rec["status"] = "BLOCKED" if not ok else "OPTIONAL"
    else:
        rec["status"] = "ACTIVE" if ok else ("BLOCKED" if rec.get("http") in (401,403,429) else "REJECTED")
    return rec

if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(probe, PROBES))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results},
              open(OUT, "w"), indent=1)
    for r in sorted(results, key=lambda x: (x["family"], x["status"])):
        print(f'{r["status"]:9} {r["http"]:>4} {r["family"]:10} {r["source"][:46]:46} {r.get("error","")[:50]}')
    from collections import Counter
    print(Counter(r["status"] for r in results))
