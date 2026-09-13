# Nomad Radar — credential collection sheet

**Fill this file in and send it back. Do not send anything else.**

Fill in the value after each equals sign. Leave a value blank if you could not get it, and
set the matching `_STATUS` line so I know why. **Keep every line, even the blank ones** —
a blank line with a status is useful information; a missing line is not.

Companion document: `CREDENTIALS_HOW_TO_GET.md` tells you where each one comes from.

### Status values — set one for every service

| Value | Means |
|---|---|
| `OK` | Got it, it's in the file above this line |
| `SKIPPED_PAID` | It costs money — I did not buy it. Price noted. |
| `PENDING_REVIEW` | Application submitted, waiting on their approval |
| `NEEDS_OWNER` | Blocked because it needs the owner's own account, card, or ID |
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

# ---------- FREE — expected to be obtainable ----------

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
FOURSQUARE_FREE_ALLOWANCE_SEEN=

# ---------- PAID OR APPROVAL-GATED — do not purchase, just report ----------

NUMBEO_API_KEY=
NUMBEO_STATUS=
NUMBEO_PRICE_SEEN=
NUMBEO_ACADEMIC_APPLIED=

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

---

## Also tell me, in your message (not in the file)

- Which account each credential sits under (a new one you made, or one of mine).
- Anything you had to agree to — terms, a plan, a trial that will start billing.
- Anything that needs **me** to finish it: an ID check, a card, a business verification,
  an approval that only the account owner can click.
- Anything you think is wrong or out of date in the instructions document, so I can fix it.
