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
from collections import defaultdict, Counter
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
# Hashtags include non-English ones deliberately. The community layer was the
# thinnest evidence family in the build (2,850 posts scanned, 166 attributions)
# and what it did find skewed European, so the English-only tag list was part of
# the problem rather than incidental to it.
MASTODON_TAGS = ["digitalnomad", "remotework", "nomadlife", "coworking", "expat",
                 "travel", "expatlife", "workfromanywhere", "remotelife", "slowtravel",
                 "nomadadigital", "nomadedigital", "trabajoremoto", "teletrabajo",
                 "teletravail", "homeoffice", "backpacking", "vanlife",
                 "livingabroad", "wanderlust"]
# Each instance shows its own federated view of a hashtag, so more instances
# means genuinely more posts rather than the same posts again - and instances
# outside the anglophone default reach different corners of the fediverse.
MASTODON_HOSTS = ["mastodon.social", "mastodon.world", "fosstodon.org",
                  "mastodon.online", "mstdn.social", "mas.to",
                  "universeodon.com", "mastodonapp.uk", "hachyderm.io"]
MASTODON_PAGES = 3              # 40 posts a page, paged back with max_id
LEMMY_HOSTS = ["lemmy.world", "lemmy.ml"]
LEMMY_COMMUNITIES = ["digitalnomad", "travel", "europe", "asia", "worldnews",
                     "latinamerica", "africa", "expats", "remotework",
                     "backpacking", "solotravel", "nomad", "citylife"]
HN_QUERIES = ["digital nomad", "remote work city", "coworking", "moving abroad",
              "expat", "living in", "best city for developers",
              "relocating to", "working remotely from", "visa remote work",
              "cost of living", "moved to", "living abroad", "nomad visa"]
HN_PAGES = 3                    # Algolia pages 100 hits at a time

# Words that are also city names. A bare occurrence of these is almost never a
# place reference, so they always require an explicit country/region qualifier.
STOPNAMES = {"of","most","best","why","san","new","one","are","for","the","and","but","not","you",
             "mobile","reading","bath","nice","split","hope","york","boston","same","many",
             "general","industry","independence","liberty","cost","price","union","victoria",
             "aurora","eight","normal","surprise","enterprise","hot springs","riverside","lake",
             "valley","or","angel","paradise","hollywood","eden","sale","march","mercedes",
             "metro","central","north","south","east","west","capital","commerce","garden",
             "athens","florence","rome","paris","dublin","memphis","odessa","vienna","berlin",
             "moscow","cambridge","richmond","hamilton","auburn","salem","franklin","clinton"}

# Terms that make a post plausibly about living/working in a place rather than
# merely mentioning it. Used to corroborate a weak name match.
CONTEXT_TERMS = ("nomad","remote","coworking","co-working","expat","visa","rent","apartment",
                 "living","live in","move to","moving","relocat","stay","month","cost of living",
                 "wifi","internet","community","meetup","based in","spent","travel","trip")

QUALIFIER_WINDOW = 26     # characters after a name in which a country may appear


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def build_matcher(places, limit=6000):
    """Name -> place index with an explicit ambiguity model.

    The first implementation simply dropped every name under five characters,
    which silenced 196 places including Ubud, Goa, Lima, Rome, Oslo and Riga -
    several of them major nomad destinations - and still produced false hits
    like crediting "Goa - the 'Las Vegas' of India" to Las Vegas.

    Now: a name is SAFE if its largest claimant is at least three times the
    population of the next, and it is not a common word. Everything else is
    AMBIGUOUS and only counts when the post also supplies a country/region
    qualifier, or names it in the title with nomad context. Names inside
    quotation marks are never matched - that is the "Las Vegas of India" case.
    """
    ranked = sorted(places, key=lambda p: -p["pop"])[:limit]
    claims = defaultdict(list)
    for p in ranked:
        for nm in {p["name"], p["ascii"]}:
            k = strip_accents(nm).lower()
            if len(k) < 4 or not re.fullmatch(r"[a-z][a-z' \-]+", k):
                continue
            claims[k].append(p)
    idx = {}
    for k, ps in claims.items():
        ps.sort(key=lambda p: -p["pop"])
        top = ps[0]
        runner = ps[1]["pop"] if len(ps) > 1 else 0
        safe = (k not in STOPNAMES) and (runner == 0 or top["pop"] >= 3 * runner) and len(k) >= 5
        idx[k] = {"gid": top["gid"], "safe": safe, "cc": top["cc"],
                  "country": strip_accents(top.get("country", "")).lower(),
                  "admin1": strip_accents(top.get("admin1_name", "")).lower(),
                  "claimants": len(ps)}
    pattern = re.compile(r"(?<![a-z])(" + "|".join(
        sorted((re.escape(k) for k in idx), key=len, reverse=True)) + r")(?![a-z])")
    return idx, pattern


def quoted_spans(text):
    """Character ranges inside quotation marks - a name there is a simile."""
    spans = []
    for m in re.finditer(r"[\"\u201c\u2018']([^\"\u201d\u2019']{1,60})[\"\u201d\u2019']", text):
        spans.append((m.start(1), m.end(1)))
    return spans


def accept_match(name, meta, blob, title_len, start, end, quoted):
    """Decide whether a name occurrence really refers to that place."""
    for a, b in quoted:
        if a <= start and end <= b:
            return False, "inside quotes"
    tail = blob[end:end + QUALIFIER_WINDOW]
    qualified = bool(meta["country"] and meta["country"] in tail) or \
                bool(meta["admin1"] and len(meta["admin1"]) > 3 and meta["admin1"] in tail)
    # the OCCURRENCE must be in the title, not merely the name - Reddit feeds
    # repeat the title inside the body, which let a rejected quoted mention
    # sneak back in via its unquoted echo
    in_title = end <= title_len
    if qualified:
        return True, "country-qualified"
    # A name that only appears in the body is usually a comparison, not the
    # subject: "Goa - the 'Las Vegas' of India" is a post about Goa. Requiring
    # the title (or an explicit country) keeps the subject and drops the simile.
    if not in_title:
        return False, "body-only mention"
    if meta["safe"]:
        return True, "unambiguous, in title"
    if any(t in blob for t in CONTEXT_TERMS):
        return True, "title + nomad context"
    return False, "ambiguous, unqualified"


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
        max_id = None
        for _ in range(MASTODON_PAGES):
            url = f"https://{host}/api/v1/timelines/tag/{tag}?limit=40"
            if max_id:
                url += f"&max_id={max_id}"
            j = fetch(url, source_id="mastodon_public", as_json=True, timeout=35,
                      retries=2, limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
            if not isinstance(j, list) or not j:
                break
            for s in j:
                posts.append({"source": "mastodon_public", "channel": f"#{tag}",
                              "title": re.sub(r"<[^>]+>", " ", s.get("content", ""))[:220],
                              "text": re.sub(r"<[^>]+>", " ", s.get("content", ""))[:800],
                              "url": s.get("url", ""), "at": (s.get("created_at") or "")[:19]})
            max_id = j[-1].get("id")
            if not max_id:
                break
    return posts


def lemmy():
    posts = []
    for host in LEMMY_HOSTS:
      for c in LEMMY_COMMUNITIES:
        for page in (1, 2):
            j = fetch(f"https://{host}/api/v3/post/list?community_name={c}"
                      f"&limit=50&page={page}&sort=New",
                      source_id="lemmy_public", as_json=True, timeout=35, retries=1,
                      limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
            got = ((j or {}).get("posts") or [])
            for p in got:
                pv = p.get("post", {})
                posts.append({"source": "lemmy_public", "channel": f"!{c}@{host}",
                              "title": (pv.get("name") or "")[:220],
                              "text": (pv.get("body") or "")[:800],
                              "url": pv.get("ap_id", ""),
                              "at": (pv.get("published") or "")[:19]})
            if len(got) < 50:
                break                 # community absent here, or exhausted
    return posts


def hackernews():
    posts = []
    for q in HN_QUERIES:
      for page in range(HN_PAGES):
        j = fetch("https://hn.algolia.com/api/v1/search_by_date?query="
                  + urllib.parse.quote(q) + f"&tags=(story,comment)&hitsPerPage=100&page={page}",
                  source_id="hn_algolia", as_json=True, timeout=35, retries=2,
                  limiter=LIM, breaker=BRK, cache_ttl=6 * 3600)
        hits = ((j or {}).get("hits") or [])
        for h in hits:
            posts.append({"source": "hn_algolia", "channel": "hn:" + q,
                          "title": (h.get("title") or h.get("story_title") or "")[:220],
                          "text": (h.get("comment_text") or h.get("story_text") or "")[:800],
                          "url": h.get("url") or f'https://news.ycombinator.com/item?id={h.get("objectID")}',
                          "at": (h.get("created_at") or "")[:19]})
    return posts


def main():
    gb = read_json("geobase.json")
    idx, pattern = build_matcher(gb["places"])
    nsafe = sum(1 for v in idx.values() if v["safe"])
    print(f"place-name matcher: {len(idx):,} names ({nsafe:,} unambiguous, "
          f"{len(idx)-nsafe:,} require a qualifier)")

    posts = []
    for fn in (reddit_feeds, mastodon, lemmy, hackernews):
        try:
            got = fn()
            print(f"  {fn.__name__}: {len(got)} posts")
            posts.extend(got)
        except Exception as e:
            print(f"  {fn.__name__}: FAILED {type(e).__name__}: {e}")

    mentions = defaultdict(list)
    rejected = Counter()
    for p in posts:
        title_blob = strip_accents(p["title"]).lower()
        title_len = len(title_blob)
        blob = strip_accents(f'{p["title"]} {p["text"]}').lower()
        quoted = quoted_spans(blob)
        seen_here = set()
        for m in pattern.finditer(blob):
            name = m.group(1)
            meta = idx.get(name)
            if not meta or meta["gid"] in seen_here:
                continue
            ok, why = accept_match(name, meta, blob, title_len, m.start(1), m.end(1), quoted)
            if not ok:
                rejected[why] += 1
                continue
            seen_here.add(meta["gid"])
            mentions[str(meta["gid"])].append(
                {"source": p["source"], "channel": p["channel"],
                 "title": p["title"][:160], "url": p["url"], "at": p["at"],
                 "matched": name, "basis": why, "precision": "locality"})
    print("  rejected matches:", dict(rejected))

    out = {}
    for gid, ms in mentions.items():
        srcs = {m["source"] for m in ms}
        chans = {m["channel"] for m in ms}
        out[gid] = {"mentions": len(ms), "unique_sources": len(srcs), "unique_channels": len(chans),
                    "sources": sorted(srcs), "samples": ms[:8],
                    "match_basis": sorted({m["basis"] for m in ms})}

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
