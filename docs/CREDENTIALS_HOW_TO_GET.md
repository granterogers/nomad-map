# Nomad Radar — how to get each credential

**Companion file:** `CREDENTIALS_TO_COLLECT.md`. That is the sheet you fill in and send back.
This document tells you where each value comes from.

**Every link below was opened and checked on 13 September 2026.** Where a page is behind a
login or blocks automated checks, that is stated explicitly rather than left to look broken.

---

## Read this first

**Everything on this list is free.** There is nothing to buy, and no paid service is being
asked for. If any service asks you for a payment card or pushes you to a paid plan:

> **Stop. Set that service's status to `WANTS_PAYMENT`. Move to the next one.**

Do not enter a card — not mine, not yours, not "just to verify". A service that has started
charging is a useful thing for you to tell me; it is not a problem for you to solve.

**Work top to bottom.** The first five matter most. The rest are genuinely optional.

**Do not use your own personal accounts for any of this, and do not register anything in your
own name.** Everything goes under one dedicated project identity, described in Step 0 below.
That matters to both of us: you should not still be attached to my project after the work is
finished, and I should not be depending on accounts I cannot recover. Where a service demands
identity verification of the project owner, stop and mark `NEEDS_OWNER`.

**When you create a key:**
- Use **read-only** permissions wherever the service offers a choice.
- Restrict the key **by API or service**, never by IP address or HTTP referrer. This project
  runs from a server whose IP changes, so an IP or referrer restriction will break the key
  and it will look like you gave me a bad one.
- Several of these show the secret **once only**. Copy it into the sheet before closing the tab.

**Assume every key you send is burned.** It travels through a chat transcript, so scope it
tightly and I will rotate it. Just don't create anything with broad account access.

---

# Step 0 — the project account (do this before anything else)

**Every account you create must belong to one dedicated project identity, not to you.**

The reason is simple. If these accounts are registered to your email and your phone, then when
this job finishes I am left depending on accounts I cannot get back into, and you are left
permanently attached to a project you no longer work on. Neither of us wants that. One shared
project identity fixes it.

### Which identity to use

**Look at the message this document came with.** I should have supplied a project email address
and password — probably a Google/Gmail account created for this purpose. **Use that account for
everything below.**

If I did *not* supply one, create it yourself as your first task, and hand it back in the sheet:

1. Create a new Google account at <https://accounts.google.com/signup> using a name that
   describes the project, not you — something like `nomadradar.data@gmail.com`.
2. Set a long random password. Put it in the sheet.
3. **Do not turn on two-factor authentication.** I will enable it myself after handover, on my
   own device. If you switch it on, the account becomes unrecoverable for me the moment you
   stop answering messages.
4. If Google demands a phone number for verification, use one — but **tell me whose number it
   was** in `PROJECT_PHONE_USED` so I know to replace it. This is the one part of the handover
   that cannot be made clean, and I would rather know about it than discover it later.
5. Fill in `PROJECT_EMAIL`, `PROJECT_EMAIL_PASSWORD`, `PROJECT_EMAIL_RECOVERY_ADDRESS`,
   `PROJECT_2FA_ENABLED` (should be `no`) and `PROJECT_ACCOUNT_STATUS` at the top of the sheet.
   **If I supplied the account, still repeat `PROJECT_EMAIL` back** so I can confirm you used it
   and did not quietly register things elsewhere.

### How to use it for each service

- Where a service offers **"Sign in with Google"** (or Continue with Google), use it with the
  project account. That gives everything a single recovery path and is the least work for you.
- Where a service wants its own username and password — Reddit, Wikimedia, Bluesky, GitHub —
  register it **with the project email address**, set a password, and **write that username and
  password into the sheet.** These accounts are part of the deliverable, not just the API keys
  they produce. An API key without the account behind it cannot be regenerated when it expires.
- Never link any of these to your personal Google, Facebook, Apple or GitHub identity.

### On sending me passwords

For these accounts, yes — send them, in the sheet. They are purpose-made throwaways with
nothing personal in them, and I will change every password the moment I receive the file. That
is normal handover, not carelessness.

**Your own passwords are a different matter: never send me one, for any reason.** If a step
seems to require your personal credentials, it means something has gone wrong — stop and ask.

---

# The core five

## 1. Eventbrite

*Why I want it: event coverage in Latin America and Southeast Asia, where my current source is
weak.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | No |
| Time | ~5 minutes |

1. Sign in or create an account: <https://www.eventbrite.com/signin/>
2. Go to the API keys page: **<https://www.eventbrite.com/account-settings/apps>**
   (also reachable at <https://www.eventbrite.com/platform/api-keys>)
3. Create an API key. You'll be asked for an application name and description — anything
   honest is fine, e.g. "Nomad Radar, research map of event activity by city".
4. Open the key and copy the **private token**. It is the private token I need, not the
   "API key" / client ID shown next to it.

- Docs: <https://www.eventbrite.com/platform/docs/introduction>
- Auth docs: <https://www.eventbrite.com/platform/docs/authentication>
- Note: <https://www.eventbrite.com/platform/api> requires you to be signed in first and
  returns an error otherwise. Expected, not a broken link.

**Fill in:** `EVENTBRITE_PRIVATE_TOKEN`, `EVENTBRITE_STATUS`

---

## 2. Reddit OAuth app

*Why I want it: Reddit currently blocks my server, so I only get a few thousand posts through
public RSS. An app key removes that ceiling.*

| | |
|---|---|
| Account | A **new Reddit account** registered to the project email (see Step 0) |
| Card needed | No |
| Time | ~5 minutes |

1. Go to **<https://www.reddit.com/prefs/apps>** (sign in first).
2. Scroll to the bottom, click **"are you a developer? create an app"**.
3. Choose type **`script`**.
4. Name: anything, e.g. `nomad-radar`. Description optional.
5. Redirect URI: `http://localhost:8080` — required by the form, not actually used.
6. After creating, you'll see two values:
   - The string **directly under the app name at the top left** is the **client ID**.
   - The value labelled **`secret`** is the client secret.

A Reddit `script` app is tied to the account that created it, so I also need that account's
username and password — which is fine, because per Step 0 this is a fresh account registered to
the project email, not yours. Put both in the sheet.

**Never send me the password to your own Reddit account.** If you find yourself about to, stop:
it means you signed in with the wrong account.

- Docs: <https://www.reddit.com/dev/api/> · <https://www.reddit.com/wiki/api>

**Fill in:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`,
`REDDIT_STATUS`

---

## 3. Wikimedia API token

*Why I want it: every Wikimedia API host rate-limits my server to zero. A token removes that.*

| | |
|---|---|
| Account | A **new Wikimedia account** registered to the project email |
| Card needed | No |
| Time | ~5 minutes |

1. Create an account or sign in: <https://api.wikimedia.org/wiki/Special:CreateAccount>
   (main page: <https://api.wikimedia.org/wiki/Main_Page>)
2. Go to **<https://api.wikimedia.org/wiki/Special:AppManagement>**
3. Choose **"Personal API token"** — the simple option, and the one I want. Only use the OAuth
   client option if the personal token isn't available.
   Also record the account's own `WIKIMEDIA_USERNAME` and `WIKIMEDIA_PASSWORD` — Wikimedia
   accounts are username-based, so without them I cannot reissue the token when it expires.
4. Copy the token **immediately**. Wikimedia shows it once and will not show it again.

- Docs: <https://api.wikimedia.org/wiki/Documentation>

**Fill in:** `WIKIMEDIA_ACCESS_TOKEN`, `WIKIMEDIA_STATUS`
(plus `WIKIMEDIA_CLIENT_ID` / `WIKIMEDIA_CLIENT_SECRET` only if you had to use OAuth)

---

## 4. Cloudflare Radar token

*Why I want it: real internet speed and quality per city. My model has nothing on this today,
and it's a genuine factor in where someone can actually work.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | No — and no domain either |
| Time | ~10 minutes |

1. Create a free account: <https://dash.cloudflare.com/sign-up>
   You do **not** need to add a domain or a payment card. Skip any upsell.
2. Go to **<https://dash.cloudflare.com/profile/api-tokens>**
3. **Create Token** → **Create Custom Token**
4. Permission: **Account · Radar · Read**. Nothing else — Radar Read only.
5. Leave IP filtering **empty**.
6. Create, then copy the token. Shown once only.

- Token guide: <https://developers.cloudflare.com/fundamentals/api/get-started/create-token/>
- Radar docs: <https://developers.cloudflare.com/radar/get-started/first-request/>

Note: both `dash.cloudflare.com` links refuse automated tools and load only in a real browser.
That's Cloudflare's bot protection — the links are correct.

**Fill in:** `CLOUDFLARE_RADAR_API_TOKEN`, `CLOUDFLARE_STATUS`

---

## 5. Ticketmaster Discovery API

*Why I want it: a second global event source, independent of the one I have. Free quota is
5,000 calls a day, which is plenty.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | No |
| Time | ~5 minutes |

1. Register: **<https://developer.ticketmaster.com/user/register>**
2. Once signed in, an app is created for you with a **Consumer Key**. That key is the value
   I need.
3. You can confirm it works in their browser tool: <https://developer.ticketmaster.com/api-explorer/v2/>

- Getting started: <https://developer.ticketmaster.com/products-and-docs/apis/getting-started/>
- Discovery API docs: <https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/>
- Their published free limit, as of today: **5,000 calls/day, 5 requests/second.**

**Fill in:** `TICKETMASTER_API_KEY`, `TICKETMASTER_STATUS`

---

# Also worth having

## 6. OpenAQ — air quality

*Why I want it: air quality is a real factor in whether somewhere is liveable for months at a
time, and it separates places that otherwise look identical — Chiang Mai in burning season is
not Chiang Mai in December. My model has nothing on this.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | No |
| Time | ~5 minutes |

1. Register: **<https://explore.openaq.org/register>** (sign in: <https://explore.openaq.org/login>)
2. The API key appears in your account page after you verify your email.
3. Key docs: <https://docs.openaq.org/using-the-api/api-key>

- Docs home: <https://docs.openaq.org/>

**Fill in:** `OPENAQ_API_KEY`, `OPENAQ_STATUS`

---

## 7. Bluesky app password

*Why I want it: Bluesky's public API refuses my server, but an app password gets me in. It
feeds the same community-post analysis I already run on Mastodon, and it reaches a different
set of people.*

| | |
|---|---|
| Account | A **new Bluesky account** registered to the project email |
| Card needed | No |
| Time | ~5 minutes |

1. Create a new account at <https://bsky.app/> using the project email address.
2. Go to **<https://bsky.app/settings/app-passwords>**
3. Create an **app password**. This is Bluesky's purpose-built revocable credential — it is
   **not** the account password, and it can be revoked without touching the account.
4. Send me the **handle** (e.g. `something.bsky.social`) and the app password.
5. Also put the account's own login password in `BLUESKY_ACCOUNT_PASSWORD`, so I can issue a
   fresh app password myself when this one is revoked or expires.

- Docs: <https://docs.bsky.app/docs/get-started>

**Fill in:** `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `BLUESKY_STATUS`

---

## 8. Foursquare Places

*Why I want it: venue data that doesn't come from OpenStreetMap. My single biggest measured
bias is that OpenStreetMap is mapped far more thoroughly in Europe than elsewhere — France
records 4.06 coworking spaces per 100,000 people, Indonesia 0.06. Nobody believes that's real.
An independent venue source attacks that at the root.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | **Possibly.** If it asks, stop — `WANTS_PAYMENT`. |
| Time | ~15 minutes |

1. Sign up: <https://foursquare.com/developers/signup>
   (console: <https://foursquare.com/developers/home>)
2. Create a **project**.
3. Generate a **Service API Key** for that project.
4. Note what free monthly allowance is displayed, and put it in
   `FOURSQUARE_FREE_ALLOWANCE_SEEN`.

- Product page: <https://location.foursquare.com/products/places-api/>
- Docs: <https://docs.foursquare.com/fsq-developers-places/reference/places-api-overview>

This is the one on the free list I'm least certain stays free. If it wants a card at any point,
that's a genuinely useful finding — tell me.

**Fill in:** `FOURSQUARE_API_KEY`, `FOURSQUARE_STATUS`, `FOURSQUARE_FREE_ALLOWANCE_SEEN`

---

# Only if you have time — experimental

These two are ideas I haven't validated. Don't spend long on them, and don't worry if they
don't work out.

## 9. GitHub personal access token

*Why: developers publish a location on their profile, which might indicate where remote workers
actually are. It might also just measure where tech companies are — I don't know yet, which is
why it's down here.*

| | |
|---|---|
| Account | A **new GitHub account** registered to the project email |
| Card needed | No |
| Time | ~5 minutes |

1. Create a GitHub account with the project email address, then go to
   **<https://github.com/settings/tokens>** (the page returns an error to anyone not logged in,
   which is expected). Put `GITHUB_USERNAME` and `GITHUB_PASSWORD` in the sheet too.
2. Create a **fine-grained** or classic token with **public read access only**. No repo write,
   no account scopes, no organisation access.
3. Set an expiry of 90 days or less.

- Docs: <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>

**Fill in:** `NOMAD_GITHUB_TOKEN`, `GITHUB_STATUS`

---

## 10. Amadeus for Developers (self-service)

*Why: their travel-analytics endpoints show which cities people actually fly to. The free test
tier may only return a limited sample, which is the reason this is experimental rather than in
the core list.*

| | |
|---|---|
| Account | **The project account** (see Step 0) |
| Card needed | No for the **Test** environment. **Do not enable Production** — that bills. |
| Time | ~10 minutes |

1. Register: **<https://developers.amadeus.com/register>**
2. Create an app in the **Test** environment. Copy the **API Key** and **API Secret**.
3. Stay on Test. Do not move the app to Production.

- Self-service home: <https://developers.amadeus.com/self-service>
- Auth guide: <https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/API-Keys/authorization/>

**Fill in:** `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_STATUS`

---

# Attempt last — free, but slow and may need me

## 11. Meta / Facebook Graph API

*Why I want it: this is the largest coverage gap in the whole system. Nomad communities in
Bali, Thailand and Latin America organise on Facebook, not Meetup. It costs nothing — but the
permissions that matter need app review, which takes days and can require identity or business
verification.*

| | |
|---|---|
| Account | A Facebook account — see the note below, this one is awkward |
| Card needed | No |
| Time | Days, mostly waiting |

**A warning specific to this one.** Meta ties developer accounts to a *real* Facebook profile
and will not accept a throwaway — they actively remove accounts that look synthetic, and they
may ask for government ID. That means this is the one item on the list that cannot be handed
over cleanly, and **you should not attach your own Facebook profile to my project.**

So: **look, report, and stop.** Tell me what Meta requires today, and I will do it under my own
profile if I decide it is worth it. Mark `FACEBOOK_STATUS=NEEDS_OWNER`.

1. App dashboard: **<https://developers.facebook.com/apps/>**
2. Look at what creating an app actually demands now — profile age, ID, business verification.
3. Do not create one under your personal profile.

Report what you found. Do not submit anything.

- Docs: <https://developers.facebook.com/docs/graph-api/>

*Honest note: I could not machine-verify these two links. Meta rejects automated requests to
every path on that domain, homepage included, so an automated check returns an error whether
the page exists or not. Open them in a normal browser; if a path has moved, tell me.*

**Fill in:** `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`, `FACEBOOK_ACCESS_TOKEN`, `FACEBOOK_STATUS`

---

# What I actually expect

| # | Service | Realistic outcome |
|---|---|---|
| 1 | Eventbrite | Should work |
| 2 | Reddit | Should work |
| 3 | Wikimedia | Should work |
| 4 | Cloudflare Radar | Should work |
| 5 | Ticketmaster | Should work |
| 6 | OpenAQ | Should work |
| 7 | Bluesky | Should work |
| 8 | Foursquare | Probably; may have started asking for a card |
| 9 | GitHub | Easy, but I'm unsure it's useful |
| 10 | Amadeus | Easy, but the free tier may be too limited |
| 11 | Meta | Report only — cannot be handed over, see the section |

**Getting items 1–7, all registered to the project account, is a good result.** Everything
below that is a bonus. A key I cannot renew because the account behind it belongs to someone
else is worth less than no key at all, so Step 0 matters more than any individual item here.

If a page has moved or an instruction here is wrong, say so — the links were checked on
13 September 2026 and developer portals change often. A corrected link is worth as much to me
as a key.

---

## A note on what is deliberately *not* on this list

Numbeo, the Meetup API, Google Places and Nomads.com would all help this project, and three of
them would help a lot. **They are all paid, so they are not being asked for.** They are
recorded in `REACHING_STRONG_CORRELATION.md` as a separate decision for me to make, not work
for anyone else. If you find yourself on a payment page for anything, you have wandered off
this list.
