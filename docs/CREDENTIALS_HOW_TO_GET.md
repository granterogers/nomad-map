# Nomad Radar — how to get each credential

**Companion file:** `CREDENTIALS_TO_COLLECT.md`. That is the sheet you fill in and send back.
This document tells you where each value comes from.

**Every link below was opened and checked on 13 September 2026.** Where a page is behind a
login or blocks automated checks, that is stated explicitly rather than hidden.

---

## Read this first

**Work top to bottom. Items 1–5 are free and are the ones that matter most to me.**
Items 6–11 are paid or need approval — for those I mostly want an answer, not a purchase.

**Do not spend any money.** If something requires payment, write down the price, set the status
to `SKIPPED_PAID`, and move on. I will decide.

**Create new accounts in your own name where a service allows it**, and tell me which account
each key belongs to. Where a service needs *my* identity, my card, or my business details, stop
and mark it `NEEDS_OWNER` — do not attempt to work around an identity or billing check.

**When you create a key:**
- Use **read-only** permissions wherever the service offers a choice.
- Set a **spending cap or quota limit** on anything that could bill. Google especially.
- Restrict the key **by API or service**, never by IP address or HTTP referrer. This project
  runs from a server whose IP changes, so an IP or referrer restriction will break the key
  and it will look like you gave me a bad one.

**Assume every key you send is burned.** It travels through a chat transcript, so scope it
tightly and I will rotate it. That is my problem, not yours — just don't create anything with
broad account access.

---

# FREE — do these five first

## 1. Eventbrite — the biggest free win

*Why I want it: event coverage in Latin America and Southeast Asia, where my current source is
weak.*

| | |
|---|---|
| Account needed | Free Eventbrite account — **make your own**, no card |
| Cost | Free |
| Difficulty | Easy, about 5 minutes |

1. Sign in or create an account: <https://www.eventbrite.com/signin/>
2. Go to the API keys page: **<https://www.eventbrite.com/account-settings/apps>**
   (also reachable at <https://www.eventbrite.com/platform/api-keys>)
3. Create an API key. You will be asked for an application name and description — anything
   honest is fine, e.g. "Nomad Radar, research map of event activity by city".
4. Once created, open the key and copy the **private token**. It is the private token I need,
   not the "API key" / client ID shown next to it.

- Docs, if you need them: <https://www.eventbrite.com/platform/docs/introduction>
- Auth docs: <https://www.eventbrite.com/platform/docs/authentication>
- Note: <https://www.eventbrite.com/platform/api> requires you to be signed in first — it
  returns an error to anyone not logged in. That is expected, not a broken link.

**Fill in:** `EVENTBRITE_PRIVATE_TOKEN`, `EVENTBRITE_STATUS`

---

## 2. Reddit OAuth app

*Why I want it: Reddit currently blocks my server, so I only get a few thousand posts through
public RSS. An app key removes that ceiling.*

| | |
|---|---|
| Account needed | Reddit account — **your own is fine**; a fresh one works |
| Cost | Free |
| Difficulty | Easy, about 5 minutes |

1. Go to **<https://www.reddit.com/prefs/apps>** (sign in first).
2. Scroll to the bottom, click **"are you a developer? create an app"**.
3. Choose type **`script`**.
4. Name: anything, e.g. `nomad-radar`. Description optional.
5. Redirect URI: `http://localhost:8080` — required by the form, not actually used.
6. Click create. You now see two values:
   - The string **directly under the app name at the top left** is the **client ID**.
   - The value labelled **`secret`** is the client secret.

Reddit `script` apps are tied to the account that made them, so I also need the username and
password of that account. **If that account is your personal Reddit account, do not send me
the password** — make a throwaway account for this instead and send me that one's details.

- Docs: <https://www.reddit.com/dev/api/> · <https://www.reddit.com/wiki/api>

**Fill in:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`,
`REDDIT_STATUS`

---

## 3. Wikimedia API token

*Why I want it: every Wikimedia API host rate-limits my server to zero. A token removes that.*

| | |
|---|---|
| Account needed | Free Wikimedia account — **make your own** |
| Cost | Free |
| Difficulty | Easy, about 5 minutes |

1. Create an account or sign in: <https://api.wikimedia.org/wiki/Special:CreateAccount>
   (main page: <https://api.wikimedia.org/wiki/Main_Page>)
2. Go to **<https://api.wikimedia.org/wiki/Special:AppManagement>**
3. Choose **"Personal API token"** — that is the simple option and it is what I want. Only use
   the OAuth client option if the personal token is unavailable.
4. Copy the token **immediately**. Wikimedia shows it once and will not show it again.

- Docs: <https://api.wikimedia.org/wiki/Documentation>

**Fill in:** `WIKIMEDIA_ACCESS_TOKEN`, `WIKIMEDIA_STATUS`
(plus `WIKIMEDIA_CLIENT_ID` / `WIKIMEDIA_CLIENT_SECRET` only if you had to use OAuth)

---

## 4. Cloudflare Radar token

*Why I want it: real internet speed and quality per city. My model has nothing on this today.*

| | |
|---|---|
| Account needed | Free Cloudflare account — **make your own**, no card, no domain needed |
| Cost | Free |
| Difficulty | Easy, about 10 minutes |

1. Create a free account: <https://dash.cloudflare.com/sign-up>
   You do **not** need to add a domain or a payment card. Skip any upsell.
2. Go to **<https://dash.cloudflare.com/profile/api-tokens>**
3. **Create Token** → **Create Custom Token**
4. Permission: **Account · Radar · Read**. Add nothing else — Radar Read only.
5. Leave IP filtering **empty**. Do not restrict by IP.
6. Create, then copy the token. It is shown once only.

- Token guide: <https://developers.cloudflare.com/fundamentals/api/get-started/create-token/>
- Radar docs: <https://developers.cloudflare.com/radar/get-started/first-request/>

Note: the two `dash.cloudflare.com` links refuse automated tools and load only in a real
browser. That is Cloudflare's bot protection — the links are correct.

**Fill in:** `CLOUDFLARE_RADAR_API_TOKEN`, `CLOUDFLARE_STATUS`

---

## 5. Foursquare Places

*Why I want it: venue data that does not come from OpenStreetMap. My single biggest measured
bias is that OpenStreetMap is mapped far more thoroughly in Europe than elsewhere — France
records 4.06 coworking spaces per 100,000 people, Indonesia 0.06. Nobody believes that is
real. An independent venue source attacks that at the root.*

| | |
|---|---|
| Account needed | Free Foursquare developer account — **make your own** |
| Cost | Free tier available; **card may be requested — if so, stop and mark `NEEDS_OWNER`** |
| Difficulty | Medium, about 15 minutes |

1. Sign up: <https://foursquare.com/developers/signup>
   (console: <https://foursquare.com/developers/home>)
2. Create a **project**.
3. Generate a **Service API Key** for that project.
4. Before you finish: note what the free monthly allowance is shown as, and write it into
   `FOURSQUARE_FREE_ALLOWANCE_SEEN`.

- Product page: <https://location.foursquare.com/products/places-api/>
- Docs: <https://docs.foursquare.com/fsq-developers-places/reference/places-api-overview>

**Fill in:** `FOURSQUARE_API_KEY`, `FOURSQUARE_STATUS`, `FOURSQUARE_FREE_ALLOWANCE_SEEN`

---

# PAID OR APPROVAL-GATED — report, do not buy

## 6. Numbeo — most valuable item here, and expensive

*Why I want it: city-level cost of living. Right now I only have country-level data, so Chiang
Mai and Bangkok score identically on affordability, which is obviously wrong. This is the
single biggest limitation in the whole project.*

**I have already checked the price, so you do not need to.** As of 13 September 2026:

| Plan | Monthly | Yearly |
|---|---|---|
| Basic — 200,000 queries/month | $260 USD | $3,000 USD |
| Professional — 1,000,000 queries/month | $480 USD | $5,600 USD |
| Enterprise — 5,000,000 queries/month | $1,250 USD | $14,500 USD |

**Do not buy any of these.** Set `NUMBEO_STATUS=SKIPPED_PAID` and `NUMBEO_PRICE_SEEN` to the
prices you actually see (tell me if they differ from the table above — that is genuinely
useful).

**There is one thing worth doing here.** Numbeo grants free academic licences at their
discretion for university research. The application form is at
<https://www.numbeo.com/common/apply_academic_api.jsp>. **Read it and tell me whether this
project could plausibly qualify — but do not submit it.** I will decide and submit it myself
if so, because it has to be truthful about who I am. Record what you found in
`NUMBEO_ACADEMIC_APPLIED`.

- Pricing: <https://www.numbeo.com/common/api.jsp> (yearly: append `?billing=yearly`)
- Docs: <https://www.numbeo.com/api/doc.jsp>
- Overview: <https://www.numbeo.com/api/cost-of-living-api>
- Their contact address is `contact@numbeo.com`

**Fill in:** `NUMBEO_STATUS`, `NUMBEO_PRICE_SEEN`, `NUMBEO_ACADEMIC_APPLIED`
(`NUMBEO_API_KEY` stays blank unless a free academic licence is actually granted.)

---

## 7. Meetup API

*Why I want it: real group and RSVP data. I currently read public event pages, which biases the
sample towards whatever I searched for.*

**Heads up: Meetup moved to a GraphQL API and it requires a paid Meetup Pro subscription.**
`https://www.meetup.com/api/general/` now redirects to <https://www.meetup.com/graphql/>.

| | |
|---|---|
| Account needed | Meetup account, and **Pro** for API access |
| Cost | Paid — **do not buy** |
| Difficulty | Medium |

What I want from you: **find and report the current Meetup Pro price**, and confirm whether API
access is still Pro-only. That's it.

1. API overview: <https://www.meetup.com/api/> · <https://www.meetup.com/api/guide/>
2. Auth: <https://www.meetup.com/api/authentication/>
3. OAuth clients (if you can reach it): <https://www.meetup.com/api/oauth/list/>

If — and only if — you find that a free tier now exists, create an OAuth client with redirect
URI `http://localhost:8080` and send the client ID and secret.

**Fill in:** `MEETUP_STATUS`, `MEETUP_PRICE_SEEN` — and `MEETUP_CLIENT_ID`,
`MEETUP_CLIENT_SECRET`, `MEETUP_REDIRECT_URI` **only** if you found a genuinely free route.

---

## 8. Google Places / Maps Platform

*Why I want it: a second non-OpenStreetMap venue source, same reason as Foursquare.*

| | |
|---|---|
| Account needed | Google Cloud project **with billing enabled — this needs my card** |
| Cost | Billable, with a monthly free credit |
| Difficulty | Medium — **likely blocked for you** |

**This one probably needs me.** Google requires a billing account with a real payment card
before it will issue a Maps key. Do **not** put your own card on it. If you hit the billing
wall, set `GOOGLE_MAPS_STATUS=NEEDS_OWNER` and tell me exactly which step stopped you — I will
do the billing part and you can finish the rest if I hand you access.

If you do get through:
1. Console: <https://console.cloud.google.com/>
2. Create a project.
3. Enable **Places API (New)**.
4. Credentials: **<https://console.cloud.google.com/google/maps-apis/credentials>**
   (generic version: <https://console.cloud.google.com/apis/credentials>)
5. Create an API key.
6. **Restrict it by API** — Places only. **Do not** add an IP or HTTP-referrer restriction.
7. **Set a daily quota cap** so a mistake cannot run up a bill. Confirm you did this in
   `GOOGLE_MAPS_QUOTA_CAP_SET`.

- Guide: <https://developers.google.com/maps/documentation/places/web-service/get-api-key>
- Overview: <https://developers.google.com/maps/documentation/places/web-service/overview>

**Fill in:** `GOOGLE_MAPS_API_KEY`, `GOOGLE_MAPS_STATUS`, `GOOGLE_MAPS_QUOTA_CAP_SET`

---

## 9. Meta / Facebook Graph API

*Why I want it: the largest coverage gap in the system. Nomad communities in Bali, Thailand and
Latin America organise on Facebook, not Meetup.*

| | |
|---|---|
| Account needed | Facebook account + developer registration |
| Cost | Free, but group and event data needs **app review** |
| Difficulty | Hard — slow, and may need my ID |

1. App dashboard: **<https://developers.facebook.com/apps/>**
2. Create an app. Register as a developer if prompted.
3. Add the Graph API. Getting the permissions that actually matter requires **app review**,
   which takes days and can require business verification.

**Submit the review if you can get that far, then stop and report `PENDING_REVIEW` with the
date.** If Meta asks for identity or business verification, that is me — mark `NEEDS_OWNER`.

- Docs: <https://developers.facebook.com/docs/graph-api/>

*Honest note: I could not machine-verify these two Meta links — Meta rejects automated requests
outright, so an automated check returns an error for every page on that domain including the
homepage. Open them in a normal browser. If a path has moved, tell me the correct one.*

**Fill in:** `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_STATUS`

---

## 10. Instagram Platform

*Why I want it: geotagged activity as a presence proxy. Lowest priority on this list.*

Same dashboard and same app-review process as item 9: <https://developers.facebook.com/apps/>
Docs: <https://developers.facebook.com/docs/instagram-platform/>

**Only attempt this if item 9 succeeded.** Otherwise mark it `PENDING_REVIEW` or `FAILED` and
move on — I am not expecting this one.

**Fill in:** `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_STATUS`

---

## 11. Nomads.com / NomadList — skip unless trivial

Paid membership. This is roughly the thing my project is trying to predict, so it is only
useful to me for checking my own accuracy, not as an input.

<https://nomads.com/>

**Do not buy a membership.** Mark `NOMADS_STATUS=SKIPPED_PAID` and note the price.

**Fill in:** `NOMADS_STATUS` (leave `NOMADS_API_KEY` blank)

---

# Summary of what I actually expect

| # | Service | Realistic outcome |
|---|---|---|
| 1 | Eventbrite | Should work — free, quick |
| 2 | Reddit | Should work — free, quick |
| 3 | Wikimedia | Should work — free, quick |
| 4 | Cloudflare Radar | Should work — free, no card |
| 5 | Foursquare | Probably works; may ask for a card |
| 6 | Numbeo | Price report + academic-licence assessment only |
| 7 | Meetup | Price report only |
| 8 | Google Places | Probably blocked on billing — tell me where |
| 9 | Meta | App review submitted at best |
| 10 | Instagram | Likely not achievable |
| 11 | Nomads.com | Price report only |

**Getting items 1–5 is a good result.** Items 6–11 are mostly questions I want answered, not
things I expect you to obtain.

If a page has moved or an instruction here is wrong, say so — the links were checked on
13 September 2026 and these services change their developer portals often. A corrected link is
worth as much to me as a key.
