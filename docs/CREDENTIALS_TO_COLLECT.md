# Nomad Radar — credential collection sheet

**Fill this file in and send it back. Send nothing else.**

There are 11 tasks. Do all 11, in order. `CREDENTIALS_HOW_TO_GET.md` tells you exactly how.

Fill in the value after each equals sign. Set the `_STATUS` line for every task. Keep every
line, including the blank ones.

### Two hard rules

1. **Register everything to the project account, not to yourself.** Step 0 of the how-to.
2. **No service on this list charges anything. If one asks for a payment card, stop that task,
   set its status to `WANTS_PAYMENT`, and go to the next one.** Never enter a card.

### Status values

| Value | Means |
|---|---|
| `OK` | Done, value is in the file |
| `WANTS_PAYMENT` | Asked for a card, so I stopped |
| `REPORTED` | Task 11 only — questions answered in my message |
| `NEEDS_OWNER` | Requires the owner's ID verification |
| `FAILED` | Could not complete. Reason in my message. |

### Rules for the file

1. Never invent or guess a value. A blank with a status is correct. A made-up key looks real
   and fails silently, which is worse than nothing.
2. Passwords for the project accounts go in this file. They are purpose-made and will all be
   changed on receipt. **Your own passwords go nowhere.**
3. Put secrets in the file, not in the chat message.
4. Do not reformat, reorder or delete lines. Fill in values.
5. Send back one file.

---

```dotenv
# Nomad Radar credentials
# Collected by:
# Date collected:

# ---------- STEP 0 — THE PROJECT ACCOUNT ----------

PROJECT_EMAIL=
PROJECT_EMAIL_PASSWORD=
PROJECT_EMAIL_RECOVERY_ADDRESS=
PROJECT_PHONE_USED=
PROJECT_2FA_ENABLED=
PROJECT_ACCOUNT_STATUS=

# ---------- TASK 1 — EVENTBRITE ----------

EVENTBRITE_PRIVATE_TOKEN=
EVENTBRITE_STATUS=

# ---------- TASK 2 — REDDIT ----------

REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_STATUS=

# ---------- TASK 3 — WIKIMEDIA ----------

WIKIMEDIA_ACCESS_TOKEN=
WIKIMEDIA_CLIENT_ID=
WIKIMEDIA_CLIENT_SECRET=
WIKIMEDIA_USERNAME=
WIKIMEDIA_PASSWORD=
WIKIMEDIA_STATUS=

# ---------- TASK 4 — CLOUDFLARE RADAR ----------

CLOUDFLARE_RADAR_API_TOKEN=
CLOUDFLARE_STATUS=

# ---------- TASK 5 — TICKETMASTER ----------

TICKETMASTER_API_KEY=
TICKETMASTER_STATUS=

# ---------- TASK 6 — OPENAQ ----------

OPENAQ_API_KEY=
OPENAQ_STATUS=

# ---------- TASK 7 — BLUESKY ----------

BLUESKY_HANDLE=
BLUESKY_APP_PASSWORD=
BLUESKY_ACCOUNT_PASSWORD=
BLUESKY_STATUS=

# ---------- TASK 8 — FOURSQUARE ----------

FOURSQUARE_API_KEY=
FOURSQUARE_FREE_ALLOWANCE_SEEN=
FOURSQUARE_STATUS=

# ---------- TASK 9 — GITHUB ----------

NOMAD_GITHUB_TOKEN=
GITHUB_USERNAME=
GITHUB_PASSWORD=
GITHUB_STATUS=

# ---------- TASK 10 — AMADEUS ----------

AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=
AMADEUS_STATUS=

# ---------- TASK 11 — META (report only, create nothing) ----------

FACEBOOK_STATUS=
```

---

## In your message, tell me

1. Any task where you could not use the project account, and what the service demanded instead.
2. Any service that asked for a payment card.
3. Any link in the how-to that was wrong, and the correct one.
4. Your answers to the three Task 11 questions.
