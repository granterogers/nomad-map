# Nomad Radar — credential acquisition brief

**This file is a prompt.** Paste it whole into an AI agent that has a browser, signed in as
the account owner. Its job is to obtain the credentials listed below and return **one file**
in the exact format given in §4.

Every URL here was checked and resolves. Work top to bottom: the list is ordered by value to
the project, and **items 1–5 are free**.

---

## 1. What this is for

Nomad Radar is a live world map of digital-nomad activity built entirely from credential-free
open data. Measured against a held-out reference set of hand-labelled places it reaches a rank
correlation of 0.656 and a hub-vs-control AUC of 0.955. The target is 0.80 correlation.

The research established that the remaining gap is **not** solved by more of the same data. It
is dominated by two things: cost-of-living data is country-level (Chiang Mai and Bangkok score
identically on affordability, which is plainly wrong), and event coverage is skewed to Europe
and North America because that is where Meetup is strong. The credentials below close exactly
those gaps.

---

## 2. Before you start — read this

- **Create low-privilege, revocable keys.** Read-only scopes wherever the service offers them.
- **Set a spending cap** on anything billable (Google Cloud especially). A key without a quota
  is a liability, not a convenience.
- **Do not use IP or HTTP-referrer restrictions.** This project calls these APIs from a server
  whose IP changes; referrer restrictions will simply break the key. Restrict **by API/service**
  instead, which every provider here supports.
- **These keys will be pasted into a chat transcript.** Treat every one as compromised the
  moment it is shared: cap it, scope it, and rotate it when the work is finished.
- If a service requires a paid plan, **do not purchase it** — record `SKIPPED_PAID` and move on.
  Report the price you saw so the owner can decide.
- If a service requires app review or a waiting period, **do not attempt to bypass it**. Record
  `PENDING_REVIEW` with the date submitted.

---

## 3. The credentials, in priority order

### FREE — do these first

#### 1. Eventbrite (free) — biggest free coverage win
Strong in Latin America and Southeast Asia, exactly where the current event source is weakest.

- Sign in / create account: <https://www.eventbrite.com/signin/>
- API overview: <https://www.eventbrite.com/platform/api>
- Docs: <https://www.eventbrite.com/platform/docs/introduction>
- **Get the key here:** <https://www.eventbrite.com/account-settings/apps>
  (create an API key, then copy the **private token**)
- Also reachable at: <https://www.eventbrite.com/platform/api-keys>

Return: `EVENTBRITE_PRIVATE_TOKEN`

#### 2. Reddit OAuth (free) — restores a blocked source
Reddit's JSON and OAuth endpoints currently return 403 to this project; only the public RSS
feeds work, which caps community evidence at a few thousand posts. An OAuth app fixes that.

- **Create the app here:** <https://www.reddit.com/prefs/apps>
- Choose **"script"** as the app type. Redirect URI can be `http://localhost:8080`.
- Docs: <https://www.reddit.com/dev/api/> and <https://github.com/reddit-archive/reddit/wiki/OAuth2>

Return: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`
(username/password only if the script-type app requires them; otherwise leave blank)

#### 3. Wikimedia API token (free) — unblocks a rate-limited source
Every Wikimedia REST API host returns HTTP 429 to this project's egress IP. The attention layer
currently works around it by stream-filtering static dump files. An authenticated token removes
the limit and would allow live, per-language pageview queries.

- Create account / sign in: <https://api.wikimedia.org/wiki/Main_Page>
- **Create the app here:** <https://api.wikimedia.org/wiki/Special:AppManagement>
- Choose a **personal API token** (simplest) unless OAuth is offered and easy.
- Docs: <https://api.wikimedia.org/wiki/Documentation>

Return: `WIKIMEDIA_ACCESS_TOKEN` (and `WIKIMEDIA_CLIENT_ID`, `WIKIMEDIA_CLIENT_SECRET` if issued)

#### 4. Cloudflare Radar (free tier) — internet quality per location
Real connection-speed data. Currently absent from the model entirely, and a genuine factor in
where remote workers can actually work.

- Sign in / create account: <https://dash.cloudflare.com/sign-up>
- **Create the token here:** <https://dash.cloudflare.com/profile/api-tokens>
  → *Create Token* → *Custom token* → permission **Account · Radar · Read**
- Docs: <https://developers.cloudflare.com/radar/get-started/first-request/>

Return: `CLOUDFLARE_RADAR_API_TOKEN`

#### 5. Foursquare Places (free tier) — non-OSM venue coverage
The single largest bias in the current model is OpenStreetMap mapping completeness (France
records 4.06 mapped coworking spaces per 100k people; Indonesia 0.06). A second, independent
venue source attacks that at the root rather than correcting for it statistically.

- **Developer console:** <https://foursquare.com/developers/home>
- Product page: <https://location.foursquare.com/developer/>
- Create a project, then generate a **Service API Key**.

Return: `FOURSQUARE_API_KEY`

---

### PAID OR APPROVAL-GATED — report the price, do not purchase

#### 6. Numbeo (paid) — **the single highest-value item on this list**
City-level cost of living, rent and prices. This replaces the country-level proxy that is
currently the biggest modelling limitation in the entire project.

- API information and pricing: <https://www.numbeo.com/common/api.jsp>
- API documentation: <https://www.numbeo.com/api/doc.jsp>
- Contact for a key is on the API page above.

Return: `NUMBEO_API_KEY` — or `SKIPPED_PAID` plus the quoted price and any free-tier terms.

#### 7. Meetup API (requires Meetup Pro, paid)
Proper group, member and RSVP data. The current approach reads public event pages, which makes
the sample *query-conditioned* — a measured and significant flaw, because "share of events that
are nomad-related" turns out to be an artifact of the search terms rather than a property of the
city. A real API removes that.

- API overview: <https://www.meetup.com/api/general/>
- OAuth client management: <https://www.meetup.com/api/oauth/list/>
- Legacy docs: <https://www.meetup.com/meetup_api/>

Return: `MEETUP_CLIENT_ID`, `MEETUP_CLIENT_SECRET`, `MEETUP_REDIRECT_URI`
— or `SKIPPED_PAID` plus the Pro price.

#### 8. Google Places / Maps Platform (billable, has free monthly credit)
Coworking and café coverage that is not OpenStreetMap-derived.

- Get-a-key guide: <https://developers.google.com/maps/documentation/places/web-service/get-api-key>
- **Credentials page:** <https://console.cloud.google.com/google/maps-apis/credentials>
- Console: <https://console.cloud.google.com/>
- API overview: <https://developers.google.com/maps/documentation/places/web-service/overview>

Steps: create a project → enable **Places API (New)** → create an API key → restrict it
**by API** (Places only), **not** by referrer → **set a daily quota cap**.

Return: `GOOGLE_MAPS_API_KEY`

#### 9. Meta / Facebook Graph API (free, but app review required)
The largest *coverage* gap in the system. Nomad communities in Bali, Thailand and Latin America
organise on Facebook, not Meetup. Group and event data needs app review, which takes time.

- **App dashboard:** <https://developers.facebook.com/apps/>
- Graph API docs: <https://developers.facebook.com/docs/graph-api/>

Return: `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `FACEBOOK_ACCESS_TOKEN`
— or `PENDING_REVIEW` with the submission date.

#### 10. Instagram Platform (free, app review required)
Geotagged activity volume as a presence proxy. Hardest to obtain; lowest priority.

- Docs: <https://developers.facebook.com/docs/instagram-platform/>
- Same dashboard as item 9: <https://developers.facebook.com/apps/>

Return: `INSTAGRAM_ACCESS_TOKEN` — or `PENDING_REVIEW`.

#### 11. Nomads.com / NomadList (paid membership) — optional, calibration only
Effectively the target variable this project is trying to predict. Useful for calibration, not
as an input. Only pursue if a membership already exists.

- <https://nomads.com/>

Return: `NOMADS_API_KEY` or `NOMADS_SESSION_COOKIE` — or `SKIPPED_PAID`.

---

## 4. Required output format

Return **exactly one file** named `nomad-radar.env`, plain text, UTF-8, no surrounding
commentary inside the file itself. Use this template verbatim. Keep every line even if the
value is empty — an empty value is information, and the pipeline treats a missing key as
"source unavailable" rather than failing.

```dotenv
# Nomad Radar credentials
# Generated: YYYY-MM-DD
# Status values for the _STATUS lines: OK | SKIPPED_PAID | PENDING_REVIEW | FAILED

EVENTBRITE_PRIVATE_TOKEN=
EVENTBRITE_STATUS=

REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_STATUS=

WIKIMEDIA_ACCESS_TOKEN=
WIKIMEDIA_CLIENT_ID=
WIKIMEDIA_CLIENT_SECRET=
WIKIMEDIA_STATUS=

CLOUDFLARE_RADAR_API_TOKEN=
CLOUDFLARE_STATUS=

FOURSQUARE_API_KEY=
FOURSQUARE_STATUS=

NUMBEO_API_KEY=
NUMBEO_STATUS=
NUMBEO_PRICE_SEEN=

MEETUP_CLIENT_ID=
MEETUP_CLIENT_SECRET=
MEETUP_REDIRECT_URI=
MEETUP_STATUS=
MEETUP_PRICE_SEEN=

GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_STATUS=
GOOGLE_MAPS_QUOTA_CAP_SET=

FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_STATUS=

INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_STATUS=

NOMADS_API_KEY=
NOMADS_STATUS=
```

### Rules for the returned file

1. **One file only.** Do not split credentials across several files or messages.
2. **No placeholder values.** If a key was not obtained, leave it empty and set the matching
   `_STATUS` line. Never invent, guess, or pattern-match a plausible-looking key.
3. **No secrets in the chat body** — put them in the file.
4. Set `_STATUS` for **every** service, including the ones you skipped.
5. If a signup flow fails, record `FAILED` and note the reason in your reply (not in the file).

---

## 5. What happens once the file is uploaded

Upload the file to the project root as `nomad-radar.env` (it is git-ignored). Then
`python3 pipeline/credentials.py` prints exactly which sources it has unlocked:

```
credentials file: /home/user/nomad-map/nomad-radar.env
  ENABLED   numbeo             city-level cost of living
  disabled  facebook           communities outside Europe and North America
  ...
```

An adapter is written for each credential that arrives; anything absent stays disabled, and
the app continues to report that source as contributing zero, exactly as it does today. The
zero-secret build never stops working. Expected effect, in order:

| Credential | Expected effect |
|---|---|
| Numbeo | City-level affordability replaces the country proxy — the largest single modelling gain |
| Eventbrite | Event coverage in Latin America and Southeast Asia, reducing the Euro-bias |
| Foursquare / Google Places | Venue data independent of OpenStreetMap, attacking the root confound |
| Meetup API | Removes the query-conditioned sampling flaw |
| Facebook | Closes the largest coverage gap outside Europe and North America |
| Cloudflare Radar | Adds internet quality, currently absent |
| Reddit OAuth | Community evidence beyond the ~3k posts the RSS feeds allow |
| Wikimedia token | Live per-language attention instead of stream-filtered dumps |

**One thing no key can fix:** the gap between the fit and holdout correlation (0.80 vs 0.66) is
small-sample overfitting on 65 labelled places. That needs a **larger labelled reference set** —
several hundred places, ideally judged by more than one person — which is human work, not a
credential. It is probably the cheapest single improvement available, and it is the one thing on
this page the browsing agent cannot do.
