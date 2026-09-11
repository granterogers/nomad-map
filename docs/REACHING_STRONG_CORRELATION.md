# Getting the correlation strong

Target: Spearman ≥ 0.80 against the held-out reference set.
Achieved autonomously this session: **0.656 held out** (from 0.315), AUC **0.955** (from 0.762).

## What the research established

Three findings, in order of importance.

**1. The ceiling is 0.962, not 1.0.** The reference set has 128 places in 4 tiers, so ties
cap the achievable correlation. A score of 0.80 means being accurate to roughly ±0.65 of a
tier; 0.32 meant being off by more than a full tier.

**2. More activity data would not have fixed it.** Restricting the measurement to places
with 25+ events raised the correlation only from 0.32 to 0.41. Three separate activity
features were built and tested, and all three were weak:

| Feature tested | rho vs human labels |
|---|---|
| Nomad-intent share of events | +0.17 |
| Nomad/expat group membership (Meetup group pages) | +0.15 |
| Number of nomad/expat groups | +0.28 |
| *(the whole activity model, for comparison)* | +0.32 |

The nomad-share feature failed for an instructive reason: the event queries *search for*
nomad keywords, so the share is an artifact of the query, not a property of the city.

**3. The labels encode viability, which activity cannot see.** Somewhere is a nomad
destination because it is affordable, warm and legally viable — *and* active. Measured
against the same labels:

| Structural feature | rho |
|---|---|
| Cost of living (World Bank GDP per capita PPP) | **+0.53** |
| Climate comfort (NASA POWER climatology) | **+0.53** |
| Remote-work visa route | +0.34 |
| *Activity (the entire original model)* | +0.32 |

Each structural feature alone beat the whole activity model.

## What was implemented

`pipeline/step5b_viability.py` and `pipeline/step6d_nomadfit.py` add a second score,
**Nomad Fit**, blending activity with cost, climate and visa access. The activity-only Live
Score is unchanged — "where is active" and "where would suit me" are different questions.

Weights are chosen on one half of the reference set and reported on the other half, which
the fitting never sees. Chosen: activity 45%, cost 25%, climate 25%, visa 5%.

The cost curve is an **inverted U**, not "cheaper is better". A monotonic curve put Lusaka
and Nairobi at the top, which is wrong: those places are inexpensive because they are poor,
and below a certain income level the infrastructure a remote worker depends on stops being
reliable. The peak sits at roughly $11k–$35k GDP per capita PPP.

| | Live score (activity) | Nomad Fit |
|---|---|---|
| Spearman, held out | 0.315 | **0.656** |
| AUC hub vs control, held out | 0.762 | **0.955** |
| Negative controls in holdout top 20 | 5 | **0** |

## Why it stopped at 0.656, and what would close the gap

The fit half reaches 0.80 and the holdout 0.66. That 0.14 spread is small-sample
overfitting: 65 items is not many to choose four weights on. The single cheapest
improvement is therefore **more labels**, not more model.

The remaining modelling gap is dominated by one thing: **cost and visa data are
country-level**. Chiang Mai and Bangkok receive identical affordability scores, as do Lisbon
and Porto. City-level cost is the largest single lever left, and it is not available without
a commercial API.

### Requires your intervention

Ranked by expected gain per unit of effort.

| # | What | Why it matters | What you'd need to do |
|---|---|---|---|
| 1 | **Numbeo API key** | City-level cost of living, rent and meal prices. Replaces the country-level proxy that is currently the biggest modelling limitation. Expected the largest single gain. | Register at numbeo.com/api, paid tier |
| 2 | **A larger labelled reference set** | 65 fit items is too few for four weights; the 0.14 fit/holdout spread is mostly this. 400+ labels, ideally from several people, would both raise the measured number and make it trustworthy. | A few hours of your time, or a small panel |
| 3 | **Meetup API (OAuth)** | Proper group, member and RSVP data globally. Removes the query-conditioned sampling artifact that made the nomad-share feature useless, and fixes coverage outside Europe. | Meetup Pro account / OAuth client |
| 4 | **Facebook Graph API** | Nomad communities in Bali, Thailand and Latin America live on Facebook, not Meetup. This is the largest *coverage* gap in the whole system. | Meta developer app + review |
| 5 | **Eventbrite API key** | Strong in Latin America and Southeast Asia exactly where Meetup is weak. | Free developer key |
| 6 | **Google Places API key** | Coworking and café coverage that is not OpenStreetMap-derived — directly attacks the mapping-completeness confound rather than correcting for it. | Google Cloud project + billing |
| 7 | **Ookla / Cloudflare Radar key** | Real internet speed per city. Currently absent; a genuine nomad decision factor. | Free-tier API key |
| 8 | **Instagram / TikTok location data** | Geotagged activity volume, a direct presence proxy. | Business API access, hard to obtain |

### Already tried and rejected

- **World Bank homicide and internet-users indicators** — fetchable, but both correlate with
  wealth and would partly cancel the cost signal rather than add information.
- **Open-Meteo archive/climate endpoints** — rate-limited to zero for this environment's
  egress IP. NASA POWER was used instead and is better suited anyway.
- **Meetup group search pages** — client-rendered, no structured data. Group *pages* reached
  via organiser URLs do expose member counts, which is how feature 2 above was tested.
