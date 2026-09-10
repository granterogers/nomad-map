# Data sources

Every source below was **tested from this environment**, not assumed. Status
values are what the probe actually returned, and the probe is re-runnable:
`python3 pipeline/probe_sources.py`.

- **ACTIVE** — reachable anonymously and contributing evidence.
- **OPTIONAL** — reachable, but the useful data sits behind a credential, a
  login wall or terms that forbid automated collection. Contribution: zero.
- **BLOCKED** — refused automated access from here (401/403/404/429).
  Contribution: zero.
- **REJECTED** — reachable but unusable for this purpose, or a control probe.

Nothing here bypasses a login, a CAPTCHA, an anti-bot system, a paywall or any
access control. Where a platform publishes schema.org structured data on public
pages for indexing, that public markup is what is read, and robots.txt is
respected — Meetup's `/find/` path is not disallowed; its `/files/`, `/fb/`,
`/preview/`, `/n/*` and calendar feed paths are, and are not touched.


## Sources currently contributing evidence

| Source | Domain | Type | Access | Reliability | Coverage |
|---|---|---|---|---|---|
| OSM mapping-density baseline (QLever) | `qlever.dev` | normalisation | anonymous SPARQL | 100% | 2,269,942 |
| QLever OSM-planet SPARQL endpoint | `qlever.dev` | physical ecosystem | anonymous SPARQL | 100% | 693,832 |
| Wikidata Query Service | `query.wikidata.org` | geography/crosswalk | anonymous SPARQL | 100% | 85,695 |
| GeoNames cities5000 dump | `download.geonames.org` | geography | anonymous bulk download | 100% | 69,058 |
| Wikimedia hourly pageview dumps | `dumps.wikimedia.org` | attention/momentum | anonymous static file streaming | 100% | 38,331 |
| GeoNames cities15000 dump | `download.geonames.org` | geography | anonymous bulk download | 100% | 34,090 |
| Coworking-space event feeds (ICS/RSS/schema.org) | `various (from OSM website tags)` | events | anonymous, one request per site | 82% | 1,011 |
| Luma public city pages (schema.org ItemList/Event) | `luma.com` | events | anonymous HTML + JSON-LD | 46% | 0 |
| Meetup public /find pages (schema.org Event) | `meetup.com` | events | anonymous HTML + JSON-LD | 100% | 0 |
| Reddit public Atom feeds | `reddit.com` | community | anonymous | 39% | 0 |

### What each contributes

- **OpenStreetMap planet via QLever** — 693,832 matching objects worldwide, 527,072 attributed to 34,841 localities. This is the only source with true point precision everywhere, so it is what makes sub-city hotspots possible.
- **Wikimedia hourly pageview dumps** — dated daily series for 38,331 places over 28 days (112/112 hourly files streamed). Supplies current attention and real momentum.
- **Meetup + Luma public listings** — 22,073 schema.org Event objects across 1,011 localities, with organiser and venue.
- **Reddit / Mastodon / Lemmy / Hacker News** — 2,850 recent public posts scanned, attributed to 166 localities at city precision.
- **Coworking-space event feeds** — 1,011 of 4,139 coworking websites recorded in OSM publish a machine-readable calendar (iCalendar, RSS/Atom or schema.org). 8,002 events across 588 localities. Unlike Meetup listings these carry the venue's exact coordinates, so they land in an H3 cell rather than at city precision.
- **OSM mapping-density baseline** — 2,733,419 deliberately nomad-irrelevant civic objects (amenity=pharmacy, amenity=fuel, shop=supermarket, amenity=bank, shop=hairdresser, amenity=post_box) used to correct for how thoroughly each region has been mapped. Not a signal; a normaliser.
- **GeoNames + Wikidata** — the place universe, the GeoNames↔Wikipedia crosswalk, and local-language sitelinks for 2,858 places so attention is not measured on English Wikipedia alone.

## Full audit


### ACTIVE (22)

| Source | Family | HTTP | Credential | Note |
|---|---|---|---|---|
| Hacker News Algolia API | community | 200 | no | Open, no key |
| Lemmy public API | community | 200 | no | Fediverse forum |
| Lobste.rs JSON | community | 200 | no | Tech community |
| Mastodon hashtag timeline | community | 200 | no | Geo-taggable community signal |
| Reddit RSS | community | 200 | no | RSS variant |
| Telegram public channel preview | community | 200 | no | Public channel web preview |
| Eventbrite public search | events | 200 | no | Public listings |
| Luma public city page | events | 200 | no | City event listings |
| Luma public discover | events | 200 | no | Public event pages |
| Meetup public find page | events | 200 | no | Public listings |
| Partiful | events | 200 | no | Mostly private events |
| GeoNames dump (cities15000) | geo | 200 | no | Bulk populated places |
| Natural Earth (raw github) | geo | 200 | no | Country boundaries |
| Nominatim geocoder | geo | 200 | no | Geocoding fallback, 1 req/s |
| OSM Nominatim reverse | geo | 200 | no | Reverse geocode for neighbourhood names |
| OpenStreetMap Overpass (osm.ch mirror) | geo | 200 | no | Failover mirror |
| REST Countries | geo | 200 | no | Country metadata |
| Wikidata SPARQL | geo | 200 | no | City/admin hierarchy + population |
| OSM hostel | infra | 200 | no | International traveller density |
| OSM university | infra | 200 | no | International student hubs |
| OSM raster tiles | map | 200 | no | Basemap (CSP-blocked in artifact host) |
| Open-Meteo weather | media | 200 | no | No key, liveability context |

### OPTIONAL (8)

| Source | Family | HTTP | Credential | Note |
|---|---|---|---|---|
| Couchsurfing | community | 200 | yes | Login wall |
| Facebook Groups | community | 200 | yes | Login wall |
| Instagram | community | 200 | yes | Login wall |
| InterNations | community | 200 | yes | Membership wall |
| LinkedIn | community | 200 | yes | Login wall |
| Nomads.com (nomadlist) | community | 200 | yes | Paid membership |
| AirDNA | infra | 200 | yes | Commercial paid |
| Google Places API | infra | 200 | yes | API key + billing |

### BLOCKED (17)

| Source | Family | HTTP | Credential | Note |
|---|---|---|---|---|
| Wikimedia Commons API | attention | 429 | no | Weak signal |
| Wikimedia Pageviews REST | attention | 429 | no | Daily article views = live interest time series |
| Wikimedia top-pageviews | attention | 429 | no | Trending articles |
| Wikipedia REST summary | attention | 429 | no | Article metadata + coords |
| Bluesky public AppView search | community | 403 | no | Unauthenticated public AppView |
| Discord discovery | community | 404 | yes | Auth required |
| Reddit OAuth API | community | 403 | yes | Requires app credentials |
| Reddit public JSON | community | 403 | no | Historically open, now bot-blocked |
| X / Twitter | community | 401 | yes | Paid API |
| Eventbrite API v3 | events | 404 | yes | API key required |
| Meetup GraphQL API | events | 404 | yes | OAuth required |
| Wikimedia Meetup calendars | events | 429 | no | Marginal |
| Wikipedia geosearch API | geo | 429 | no | Nearby notable places |
| Coworker.com | infra | 403 | no | Directory, ToS-restricted scraping |
| Foursquare Places API | infra | 401 | yes | API key |
| GDELT 2.0 doc API | media | 429 | no | Global news monitoring, no key |
| OpenAQ air quality | media | 401 | yes | Now requires key |

### REJECTED (19)

| Source | Family | HTTP | Credential | Note |
|---|---|---|---|---|
| Google Trends (unofficial) | attention | 400 | no | Unofficial, expect block |
| Mastodon public timeline (mastodon.social) | community | 422 | no | Open fediverse API |
| Eventful / misc ICS probe | events | — | no | Control probe (expected fail) |
| OpenStreetMap events venues (Overpass) | events | — | no | Venue infrastructure |
| OpenStreetMap Overpass (overpass-api.de) | geo | — | no | Primary physical-ecosystem source |
| Overpass (kumi.systems mirror) | geo | — | no | Mirror |
| Overpass admin boundaries | geo | — | no | Admin hierarchy |
| OSM cafe with wifi | infra | — | no | Work-friendly cafés |
| OSM coliving | infra | — | no | Coliving |
| OSM community centre | infra | — | no | Community infrastructure |
| OSM hackerspace | infra | — | no | Maker/tech community |
| OSM international airport | infra | — | no | Connectivity |
| OSM internet_cafe | infra | — | no | Connectivity venue |
| OSM language school | infra | — | no | Language exchange proxy |
| OSM nightlife (bar/pub/nightclub) | infra | — | no | Social ecosystem |
| OSM wellness (yoga/gym) | infra | — | no | Wellness ecosystem |
| Protomaps public tiles | map | 200 | no | Basemap option |
| GDELT geo API | media | 404 | no | Geolocated news mentions |
| Wikinews RSS | media | 404 | no | Open news feed |

## Does any of this actually measure digital nomads?

Measured against a held-out reference set of 128 hand-labelled places
(including negative controls - large, well-mapped cities with no nomad reputation):

| Metric | Value |
|---|---|
| Rank correlation with human labels | 0.323 |
| Hub vs negative-control separation (AUC) | 0.782 |
| Precision @ top 30 | 0.767 |
| Negative controls in the top 30 | 5 |

No weight, threshold or source selection is tuned against these numbers - see
`validation/README.md`. Run `python3 validation/evaluate.py` to reproduce.


## Architecture changes forced by source testing

**Overpass → QLever.** The ecosystem layer originally queried Overpass per
candidate city. `overpass-api.de` began returning 504s, and independently the
session's egress relay closes tunnels that go ~6–7 s without bytes — which is
precisely how Overpass behaves while planning a query. Measured throughput:
~1 successful query per minute, against a need for thousands. QLever's
OSM-planet SPARQL endpoint answers planet-wide queries in 1–3 s and is
credential-free. The switch was also a product upgrade: instead of inspecting
only a pre-chosen candidate list, every matching object on Earth is retrieved,
so a hotspot can emerge anywhere. `overpass.openstreetmap.fr` was verified as a
working fallback (5/5 successes at ~1.8 s).

**Wikimedia REST API → Wikimedia dumps.** Every Wikimedia API host returns 429
for this environment's shared egress IP. The static dump server is not blocked,
so the attention layer stream-filters hourly pageview files without storing
them. The capability was preserved rather than dropped.

**Reddit JSON/OAuth → Reddit Atom.** The JSON and OAuth APIs return 403. The
public `.rss` feeds do not, so the adapter parses Atom.

## Sources deliberately not used

Google Places, Google Trends, Foursquare, Instagram, Facebook Groups and Events,
TikTok, WhatsApp, X, LinkedIn, InterNations, Couchsurfing, Nomads.com, AirDNA
and Coworker.com all require credentials, a login, payment, or forbid automated
collection. Each is listed in the audit, contributes exactly zero, and is shown
in the UI as contributing zero — per place, in the source-coverage panel. The
product's strength is multi-source corroboration; no single proprietary provider
determines whether it works.

