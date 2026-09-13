# Nomad Radar — credential collection sheet

**Fill this file in and send it back. Do not send anything else.**

**Every service on this list is free.** Nothing here should ever ask you for a payment card.
If any of them does, **stop immediately**, set that service's status to `WANTS_PAYMENT`, and
move on to the next one. Do not enter a card — not mine, and definitely not yours.

Fill in the value after each equals sign. Leave a value blank if you could not get it, and
set the matching `_STATUS` line so I know why. **Keep every line, even the blank ones** —
a blank line with a status is useful information; a missing line is not.

Companion document: `CREDENTIALS_HOW_TO_GET.md` tells you where each one comes from.

### Status values — set one for every service

| Value | Means |
|---|---|
| `OK` | Got it, it's in the file above this line |
| `WANTS_PAYMENT` | It asked for a card or a paid plan — I stopped, as instructed |
| `PENDING_REVIEW` | Application submitted, waiting on their approval |
| `NEEDS_OWNER` | Blocked because it needs the owner's own account or ID verification |
| `FAILED` | Tried, could not complete. Say why in your message. |

### Rules

1. **Never invent or guess a value.** A blank with a status is correct; a made-up key is worse
   than nothing because it will look real and fail silently.
2. **Put secrets in this file, not in the chat message.**
3. Do not reformat, reorder, or delete lines. Just fill in values.
4. Send back **one file**.

---

```dotenv
# Nomad Radar credentials
# Collected by:
# Date collected:

# ---------- CORE FIVE — these are the ones that matter most ----------

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

TICKETMASTER_API_KEY=
TICKETMASTER_STATUS=

# ---------- ALSO WORTH HAVING ----------

OPENAQ_API_KEY=
OPENAQ_STATUS=

BLUESKY_HANDLE=
BLUESKY_APP_PASSWORD=
BLUESKY_STATUS=

FOURSQUARE_API_KEY=
FOURSQUARE_STATUS=
FOURSQUARE_FREE_ALLOWANCE_SEEN=

# ---------- ONLY IF YOU HAVE TIME — experimental, low priority ----------

NOMAD_GITHUB_TOKEN=
GITHUB_STATUS=

AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=
AMADEUS_STATUS=

# ---------- FREE, BUT SLOW AND MAY NEED ME — attempt last ----------

FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_ACCESS_TOKEN=
FACEBOOK_STATUS=
```

---

## Also tell me, in your message (not in the file)

- Which account each credential sits under (a new one you made, or one of mine).
- **Anything that asked you for a payment card**, even if you backed out. I want to know which
  ones have started charging for what used to be free.
- Anything you had to agree to — terms, a plan, a trial that would start billing later.
- Anything that needs **me** to finish it: an ID check, a business verification, an approval
  only the account owner can click.
- Anything you think is wrong or out of date in the instructions document, so I can fix it.
