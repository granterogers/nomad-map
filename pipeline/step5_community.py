"""Step 5 - Community velocity layer (spec §24, §26, §28).

Credential-free public community feeds. Reddit's JSON API and OAuth API are
403-blocked for this egress IP, but the public Atom feeds are reachable, so the
adapter uses those. Fediverse (Mastodon/Lemmy) and Hacker News Algolia need no
credentials at all.

Place attribution is deliberately conservative: a post only counts for a place
when its name appears as a whole word, the name is distinctive enough not to be
a common word, and the post is recent. Attribution is city-level precision and
is recorded as such - it is never promoted to a neighbourhood/H3 claim.
"""
import html, json, os, re, sys, time, unicodedata, urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import fetch, read_json, write_json, RateLimiter, CircuitBreaker, register

LIM = RateLimiter(1.1)
BRK = CircuitBreaker(20, 60)

SUBREDDITS = ["digitalnomad", "expats", "solotravel", "remotework", "IWantOut",
              "travel", "backpacking", "coworking", "nomadlifestyle", "Shoestring",
              "onebag", "TravelHacks", "digitalnomadsindia", "eurotrip", "asia",
              "southamerica", "AskEurope", "expatriates", "WorkOnline", "Nomad",
              "TravelNoPics", "SoloTravelers", "remoteplaces", "livingabroad"]
REDDIT_SORTS = ["", "top/?t=week", "hot"]
REDDIT_SEARCHES = ["digital nomad", "coworking city", "best place remote work",
                   "moving to", "expat community", "nomad visa"]
MASTODON_TAGS = ["digitalnomad", "remotework", "nomadlife", "coworking", "expat",
                 "travel", "expatlife", "workfromanywhere", "remotelife", "slowtravel"]
MASTODON_HOSTS = ["mastodon.social", "mastodon.world", "fosstodon.org"]
LEMMY_COMMUNITIES = ["digitalnomad", "travel", "europe", "asia", "worldnews"]
HN_QUERIES = ["digital nomad", "remote work city", "coworking", "moving abroad",
              "expat", "living in", "best city for developers"]

# words that are also city names - never attribute on these alone
STOPNAMES = {"of","most","best","why","san","new","one","are","for","the","and","but","not","you",
             "mobile","reading","bath","nice","split","hope","york","boston","paris","same","many",
             "general","industry","independence","liberty","cost","price","union","victoria","aurora",
             "eight","normal","surprise","enterprise","hot springs","riverside","lake","valley","or"}


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def build_matcher(places, limit=4000):
    """Distinctive place names only, biggest-population-wins on collisions."""
    ranked = sorted(places, key=lambda p: -p["pop"])[:limit]
    idx = {}
    for p in ranked:
        for nm in {p["name"], p["ascii"]}:
            k = strip_accents(nm).lower()
            if len(k) < 5 or k in STOPNAMES or not re.fullmatch(r"[a-z][a-z' \-]+", k):
                continue
            idx.setdefault(k, p["gid"])
    pattern = re.compile(r"(?<![a-z])(" + "|".join(
        sorted((re.escape(k) for k in idx), key=len, reverse=True)) + r")(?![a-z])")
    return idx, pattern


def _reddit_parse(txt, channel, posts):
    for entry in re.findall(r"<entry>(.*?)</entry>", txt, re.S):
        t = re.search(r"<title>(.*?)</title>", entry, re.S)
        u = re.search(r'<link href="(.*?)"', entry)
        d = re.search(r"<updated>(.*?)</updated>", entry)
        c = re.search(r"<content[^>]*>(.*?)</content>", entry, re.S)
        if not t:
            continue
        posts.append({"source": "reddit_rss", "channel": channel,
                      "title": html.unescape(t.group(1))[:220],
                      "text": html.unescape(re.sub(r"<[^>]+>", " ", c.group(1)))[:800] if c else "",
                      "url": u.group(1) if u else "", "at": d.group(1)[:19] if d else ""})


def reddit_feeds():
    posts = []
    urls = [(f"https://www.reddit.com/r/{s}/{srt}", f"r/{s}")
            for s in SUBREDDITS for srt in ("", "top/?t=week")]
    urls = [((u + (".rss" if u.endswith("/") else "&f=flair_name")) if "?" in u else u + ".rss", ch)
            for u, ch in urls]
    urls = [(f"https://www.reddit.com/r/{s}/.rss", f"r/{s}") for s in SUBREDDITS] + \
           [(f"https://www.reddit.com/r/{s}/top/.rss?t=week", f"r/{s}") for s in SUBREDDITS] + \
           [(f"https://www.reddit.com/search.rss?q={urllib.parse.quote(q)}&sort=new&t=month", f"search:{q}")
            for q in REDDIT_SEARCHES]
    for u, ch in urls:
        raw = fetch(u, source_id="reddit_rss", timeout=35, retries=2, limiter=LIM,
                    breaker=BRK, cache_ttl=6 * 3600)
        if not raw:
            continue
        _reddit_parse(raw.decode("utf-8", "replace"), ch, posts)
    return posts


def _legacy_unused(txt):
        posts = []
        return posts


def mastodon():
    posts = []
    for host in MASTODON_HOSTS:
      for tag in MASTODON_TAGS:
        j = fetch(f"https://{host}/api/v1/timelines/tag/{tag}?limit=40",
                  source_id="mastodon_public", as_json=True, timeout=35, retries=2,
                  limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
        for s in (j or []):
            posts.append({"source": "mastodon_public", "channel": f"#{tag}",
                          "title": re.sub(r"<[^>]+>", " ", s.get("content", ""))[:220],
                          "text": re.sub(r"<[^>]+>", " ", s.get("content", ""))[:800],
                          "url": s.get("url", ""), "at": (s.get("created_at") or "")[:19]})
    return posts


def lemmy():
    posts = []
    for c in LEMMY_COMMUNITIES:
        j = fetch(f"https://lemmy.world/api/v3/post/list?community_name={c}&limit=40&sort=New",
                  source_id="lemmy_public", as_json=True, timeout=35, retries=1,
                  limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
        for p in ((j or {}).get("posts") or []):
            pv = p.get("post", {})
            posts.append({"source": "lemmy_public", "channel": f"!{c}",
                          "title": (pv.get("name") or "")[:220],
                          "text": (pv.get("body") or "")[:800],
                          "url": pv.get("ap_id", ""), "at": (pv.get("published") or "")[:19]})
    return posts


def hackernews():
    posts = []
    for q in HN_QUERIES:
        j = fetch("https://hn.algolia.com/api/v1/search_by_date?query="
                  + urllib.parse.quote(q) + "&tags=(story,comment)&hitsPerPage=100",
                  source_id="hn_algolia", as_json=True, timeout=35, retries=2,
                  limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
        for h in ((j or {}).get("hits") or []):
            posts.append({"source": "hn_algolia", "channel": "hn:" + q,
                          "title": (h.get("title") or h.get("story_title") or "")[:220],
                          "text": (h.get("comment_text") or h.get("story_text") or "")[:800],
                          "url": h.get("url") or f'https://news.ycombinator.com/item?id={h.get("objectID")}',
                          "at": (h.get("created_at") or "")[:19]})
    return posts


def main():
    gb = read_json("geobase.json")
    idx, pattern = build_matcher(gb["places"])
    print(f"place-name matcher: {len(idx)} distinctive names")

    posts = []
    for fn in (reddit_feeds, mastodon, lemmy, hackernews):
        try:
            got = fn()
            print(f"  {fn.__name__}: {len(got)} posts")
            posts.extend(got)
        except Exception as e:
            print(f"  {fn.__name__}: FAILED {type(e).__name__}: {e}")

    mentions = defaultdict(list)
    for p in posts:
        blob = strip_accents(f'{p["title"]} {p["text"]}').lower()
        hits = set(pattern.findall(blob))
        for h in hits:
            gid = idx.get(h)
            if gid is None:
                continue
            mentions[str(gid)].append({"source": p["source"], "channel": p["channel"],
                                       "title": p["title"][:160], "url": p["url"], "at": p["at"],
                                       "matched": h, "precision": "locality"})

    out = {}
    for gid, ms in mentions.items():
        srcs = {m["source"] for m in ms}
        chans = {m["channel"] for m in ms}
        out[gid] = {"mentions": len(ms), "unique_sources": len(srcs), "unique_channels": len(chans),
                    "sources": sorted(srcs), "samples": ms[:8]}

    write_json("community.json", {
        "generated_at": common.iso(), "posts_scanned": len(posts),
        "attribution": "whole-word city-name match on recent public posts; locality precision only",
        "places": out,
    })
    for sid, name, dom, note in [
        ("reddit_rss", "Reddit public Atom feeds", "reddit.com", "JSON + OAuth APIs are 403 for this IP; .rss is open"),
        ("mastodon_public", "Mastodon public hashtag timelines", "mastodon.social", "open fediverse API"),
        ("lemmy_public", "Lemmy public post API", "lemmy.world", "open fediverse API"),
        ("hn_algolia", "Hacker News Algolia search API", "hn.algolia.com", "open, no key")]:
        register(sid, source_name=name, domain=dom, source_type="community",
                 access_method="anonymous", credential_required=False,
                 geographic_scope="global (English-skewed)", freshness="hours",
                 terms_notes=note)
    common.save_registry()
    print(f"{len(posts)} posts -> {len(out)} places with community mentions")


if __name__ == "__main__":
    main()
