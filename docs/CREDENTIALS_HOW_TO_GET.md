# Nomad Radar — credential collection instructions

**11 tasks. Do all 11, in order.** Fill your results into `CREDENTIALS_TO_COLLECT.md` and send
that file back.

Every link was opened and checked on 13 September 2026.

---

## Three rules that apply to every task

**1. Register everything to the project account. Never to yourself.**
Do Step 0 first. Do not link any of these to your personal Google, Facebook, Apple or GitHub
identity.

**2. No service here charges anything. If one asks for a payment card, stop that task, set its
status to `WANTS_PAYMENT`, move to the next task.** Do not enter a card — not mine, not yours,
not "just to verify".

**3. Copy each secret into the sheet before closing the tab.** Several of these are shown once
and cannot be retrieved afterwards.

When creating keys: read-only permissions where the service offers a choice, and **never
restrict a key by IP address or HTTP referrer** — this project runs from a server whose IP
changes, so those restrictions break the key.

---

# Step 0 — the project account

Everything below is registered to one dedicated identity so that the accounts, and not just the
keys, are handed over at the end.

**The project email address and password were supplied with this document. Use that account for
all 11 tasks.**

If they were not supplied, create the account now as your first task:

1. Go to <https://accounts.google.com/signup>.
2. Create the account with a project name, not your name — for example `nomadradar.data`.
3. Set a long random password.
4. **Do not enable two-factor authentication.** The owner enables it after handover.
5. If Google requires a phone number, use one and record whose it was in `PROJECT_PHONE_USED`.

Fill in: `PROJECT_EMAIL`, `PROJECT_EMAIL_PASSWORD`, `PROJECT_EMAIL_RECOVERY_ADDRESS`,
`PROJECT_PHONE_USED`, `PROJECT_2FA_ENABLED` (must be `no`), `PROJECT_ACCOUNT_STATUS`.

**Fill in `PROJECT_EMAIL` even if the account was supplied to you.** It confirms which account
the other ten tasks were registered under.

**How to sign up for each service:**
- Where the service offers **"Sign in with Google"**, use it with the project account.
- Where the service wants its own username and password — Tasks 2, 3, 7 and 9 — register with
  the project email address, set a password, and **put that username and password in the
  sheet**. A key whose account cannot be reached cannot be renewed when it expires.

**On passwords:** the project account passwords go in the sheet. They are purpose-made and will
all be changed on receipt. **Your own passwords go nowhere in this job.** If a step appears to
need your personal credentials, you are signed in as the wrong account — stop and ask.

---

# Task 1 — Eventbrite

Event listings. Sign in with Google using the project account.

1. Sign in: <https://www.eventbrite.com/signin/>
2. Go to **<https://www.eventbrite.com/account-settings/apps>**
   (also at <https://www.eventbrite.com/platform/api-keys>)
3. Create an API key. For the application name and description, use
   "Nomad Radar — research map of event activity by city".
4. Open the key and copy the **private token**. Not the "API key" / client ID shown beside it —
   the **private token**.

Docs: <https://www.eventbrite.com/platform/docs/introduction> ·
<https://www.eventbrite.com/platform/docs/authentication>
<https://www.eventbrite.com/platform/api> returns an error unless you are signed in. Expected.

**Fill in:** `EVENTBRITE_PRIVATE_TOKEN`, `EVENTBRITE_STATUS`

---

# Task 2 — Reddit

Create a new Reddit account using the project email address, then create an app on it.

1. Go to **<https://www.reddit.com/prefs/apps>**
2. Bottom of the page: **"are you a developer? create an app"**
3. Type: **`script`**
4. Name: `nomad-radar`
5. Redirect URI: `http://localhost:8080`
6. Create. Then read the two values off the page:
   - The string **directly under the app name, top left** = the **client ID**
   - The value labelled **`secret`** = the client secret

A Reddit `script` app is bound to the account that made it, so the account's username and
password go in the sheet as well.

Docs: <https://www.reddit.com/dev/api/> · <https://www.reddit.com/wiki/api>

**Fill in:** `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`,
`REDDIT_STATUS`

---

# Task 3 — Wikimedia

Create a new Wikimedia account using the project email address.

1. Create the account: <https://api.wikimedia.org/wiki/Special:CreateAccount>
2. Go to **<https://api.wikimedia.org/wiki/Special:AppManagement>**
3. Choose **"Personal API token"**. Use the OAuth client option only if the personal token is
   not offered.
4. **Copy the token immediately — Wikimedia shows it once.**

Wikimedia accounts are username-based, so record the username and password too.

Docs: <https://api.wikimedia.org/wiki/Documentation>

**Fill in:** `WIKIMEDIA_ACCESS_TOKEN`, `WIKIMEDIA_USERNAME`, `WIKIMEDIA_PASSWORD`,
`WIKIMEDIA_STATUS` (and `WIKIMEDIA_CLIENT_ID` / `WIKIMEDIA_CLIENT_SECRET` only if you used OAuth)

---

# Task 4 — Cloudflare Radar

Internet quality data. No card, no domain.

1. Create the account: <https://dash.cloudflare.com/sign-up>. Skip every upsell. Do not add a
   domain. Do not add a card.
2. Go to **<https://dash.cloudflare.com/profile/api-tokens>**
3. **Create Token** → **Create Custom Token**
4. Permission: **Account · Radar · Read**. Add nothing else.
5. Leave IP filtering empty.
6. Create and copy the token. **Shown once.**

Docs: <https://developers.cloudflare.com/fundamentals/api/get-started/create-token/> ·
<https://developers.cloudflare.com/radar/get-started/first-request/>
Both `dash.cloudflare.com` links load only in a real browser. Expected.

**Fill in:** `CLOUDFLARE_RADAR_API_TOKEN`, `CLOUDFLARE_STATUS`

---

# Task 5 — Ticketmaster

Second event source. Free quota is 5,000 calls/day.

1. Register: **<https://developer.ticketmaster.com/user/register>**
2. An app is created automatically with a **Consumer Key**. That key is the value needed.
3. Confirm it works: <https://developer.ticketmaster.com/api-explorer/v2/>

Docs: <https://developer.ticketmaster.com/products-and-docs/apis/getting-started/> ·
<https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/>

**Fill in:** `TICKETMASTER_API_KEY`, `TICKETMASTER_STATUS`

---

# Task 6 — OpenAQ

Air quality data.

1. Register: **<https://explore.openaq.org/register>**
2. Verify the email.
3. The API key is on the account page. Sign in at <https://explore.openaq.org/login>.

Docs: <https://docs.openaq.org/using-the-api/api-key> · <https://docs.openaq.org/>

**Fill in:** `OPENAQ_API_KEY`, `OPENAQ_STATUS`

---

# Task 7 — Bluesky

Create a new Bluesky account using the project email address.

1. Create the account: <https://bsky.app/>
2. Go to **<https://bsky.app/settings/app-passwords>**
3. Create an **app password**. This is separate from the account password and is revocable on
   its own.
4. Record three things: the handle (e.g. `something.bsky.social`), the app password, and the
   account's own login password.

Docs: <https://docs.bsky.app/docs/get-started>

**Fill in:** `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `BLUESKY_ACCOUNT_PASSWORD`,
`BLUESKY_STATUS`

---

# Task 8 — Foursquare Places

Venue data. **This is the one task most likely to ask for a card. If it does, stop and set
`WANTS_PAYMENT`.**

1. Sign up: <https://foursquare.com/developers/signup>
   (console: <https://foursquare.com/developers/home>)
2. Create a **project**.
3. Generate a **Service API Key**.
4. Record the free monthly allowance shown on screen in `FOURSQUARE_FREE_ALLOWANCE_SEEN`.

Docs: <https://docs.foursquare.com/fsq-developers-places/reference/places-api-overview> ·
<https://location.foursquare.com/products/places-api/>

**Fill in:** `FOURSQUARE_API_KEY`, `FOURSQUARE_FREE_ALLOWANCE_SEEN`, `FOURSQUARE_STATUS`

---

# Task 9 — GitHub

Create a new GitHub account using the project email address.

1. Go to **<https://github.com/settings/tokens>** (the page errors if you are not signed in —
   expected).
2. Create a token with **public read access only**. No repository write access, no account
   scopes, no organisation access.
3. Set the expiry to **90 days**.
4. Record the account username and password as well.

Docs: <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>

**Fill in:** `NOMAD_GITHUB_TOKEN`, `GITHUB_USERNAME`, `GITHUB_PASSWORD`, `GITHUB_STATUS`

---

# Task 10 — Amadeus

Travel data. **Test environment only. Do not move the app to Production — Production bills.**

1. Register: **<https://developers.amadeus.com/register>**
2. Create an app in the **Test** environment.
3. Copy the **API Key** and **API Secret**.
4. Leave the app in Test.

Docs: <https://developers.amadeus.com/self-service> ·
<https://developers.amadeus.com/self-service/apis-docs/guides/developer-guides/API-Keys/authorization/>

**Fill in:** `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `AMADEUS_STATUS`

---

# Task 11 — Meta: report only

**Create nothing. Do not register as a developer. Do not attach any Facebook profile to this
project.** Meta requires a real personal profile and may demand government ID, so this one is
handled by the owner.

Open <https://developers.facebook.com/apps/> and <https://developers.facebook.com/docs/graph-api/>
in a browser, start the app-creation flow far enough to see its requirements, and **answer these
three questions in your message**:

1. What does Meta require to create an app today — profile age, ID, business verification?
2. Which permission is needed to read public Group and Event data, and does it require app
   review?
3. How long does Meta state that review takes?

Then **back out without creating anything.**

Set `FACEBOOK_STATUS=REPORTED`.

*(These two links cannot be machine-checked — Meta rejects automated requests to every page on
that domain. They open normally in a browser.)*

---

# Do not sign up for these

Numbeo, the Meetup API, Google Places and Nomads.com all charge money and are **not** part of
this job. If you reach a payment page, you have left this list.

---

# Checklist

| Task | Service | Deliverable |
|---|---|---|
| 0 | Project account | Email, password, recovery address, phone used |
| 1 | Eventbrite | Private token |
| 2 | Reddit | Client ID, secret, account username + password |
| 3 | Wikimedia | Access token, account username + password |
| 4 | Cloudflare Radar | API token |
| 5 | Ticketmaster | Consumer key |
| 6 | OpenAQ | API key |
| 7 | Bluesky | Handle, app password, account password |
| 8 | Foursquare | Service API key + free allowance seen |
| 9 | GitHub | Read-only token, account username + password |
| 10 | Amadeus | API key + secret, Test environment |
| 11 | Meta | Three answers, no account created |
