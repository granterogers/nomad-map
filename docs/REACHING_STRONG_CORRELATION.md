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

### Credential-free sources probed in the widening pass (Sept 2026)

Reachable without any key, built as a feature, measured against the reference set, and
**not shipped**. Recorded here because a source that was tested and failed is worth as
much to the next person as one that worked.

| Source | Reachable | Measured | Verdict |
|---|---|---|---|
| **OurAirports** (`airports.csv`, 86k rows, 4,335 with scheduled service) | yes | air-connectivity feature ρ **+0.010** against the labels | Rejected. Every reference place, negative controls included, has a large airport within range: the feature has almost no variance where it matters. |
| **Wikivoyage** (MediaWiki API, 103 of 128 reference places have an article) | yes, with a User-Agent | article length ρ **+0.243**, "digital nomad" mentions ρ **+0.218**, coworking mentions ρ **+0.061** | Rejected. Length is a notability proxy, not activity, and the coworking signal is near zero — tier-3 places average 0.27 coworking mentions against 0.09 for the negative controls. |
| **Telegram public channel previews** (`t.me/<handle>`) | yes — real channels are distinguishable from missing ones by their `og:title` | guessed city handles resolved to channels of 3 to 128 members | Rejected. Telegram has no keyless search, so coverage depends on guessing handles; the real communities have unguessable names and the guessable ones are empty. Shipping it would have added noise wearing the clothes of evidence. |
| **Eventbrite public pages** | no — HTTP 429 even following redirects | — | Still blocked from this egress IP. Remains item 5 on the credentials list. |

### Credential-free sources that were shipped in that pass

| Change | Effect |
|---|---|
| **QLever's Wikidata index** in place of the public Query Service for sitelinks | The reason only 5 of 22 local-language Wikipedia editions had landed was that WDQS timed out on the large ones. QLever answers the same query in ~6 seconds. All 22 editions now land. |
| **Local-language Wikipedia widened 5 → 22 editions** | Places carrying a local-language title went from 2,858 to 12,445 (4.4×); the attention layer now tracks 129,212 project/title pairs across 46 Wikipedia projects. This is the direct fix for anglophone bias in attention, not a normalisation patch over it. |
| **OSM evidence tags widened** — added `amenity=library`, `amenity=university`, `tourism=apartment`, `tourism=guest_house` | Coworking tags are mapped overwhelmingly by European mappers; these four are mapped everywhere, so they corroborate in the regions where the coworking tags go quiet. Weights are deliberately low (0.4–0.6) — corroboration, not primary signal. `tourism=apartment` was specified in the scoring table at 1.5 but had never actually been pulled, so that weight had never been exercised; it was lowered to 0.5 before switching it on. |
| **OSM mapping-density baseline widened 6 → 11 tags** | The baseline is the denominator of the mapping-bias correction, so noise in it propagates into every corrected score. Added `place_of_worship`, `school`, `bakery`, `kindergarten`, `doctors` — all things a town has because it is a town. |
| **Community layer widened** — Mastodon 3 → 9 instances, 10 → 20 hashtags (including non-English), 3 pages each; Lemmy 1 → 2 instances, 5 → 13 communities, paged; HN Algolia 7 → 14 queries, 3 pages each | The community layer was the thinnest evidence family in the build and what it found skewed European. The English-only tag list was part of that, not incidental to it. |

### What the widening actually changed — measured, not asserted

**Coverage and corroboration went up substantially.**

| | Before | After |
|---|---|---|
| Community posts scanned | 2,850 | **22,906** |
| Localities with community evidence | 166 | **384** |
| Local-language Wikipedia editions | 5 | **22** |
| Places with a local-language title | 2,858 | **12,445** |
| Mapping-baseline objects | 2,733,419 | **6,593,906** |
| Ranked (corroborated) localities | 960 | **1,086** |
| Places with four evidence families | 124 | **213** |
| Places with three evidence families | 633 | **674** |

**Accuracy against the reference set did not move.**

| | Before | After |
|---|---|---|
| Live score, Spearman | +0.322 | +0.329 |
| Live score, AUC hub vs control | 0.791 | 0.785 |
| Live score, Precision@30 | 0.767 | **0.800** |
| Negative controls in top 30 | 4 | 4 |
| Nomad Fit, whole reference set | +0.738 | +0.733 |
| **Nomad Fit, holdout** | **+0.656** | **+0.655** |
| Nomad Fit, holdout AUC | 0.955 | 0.946 |
| Activity-only on the same holdout | +0.315 | **+0.336** |

Every movement in that second table is inside the noise of a 128-item reference set, with
the arguable exception of Precision@30 and the activity-only holdout figure, both of which
improved slightly.

**This is the expected result, and it is worth being explicit about why.** The earlier work
established that the reference labels are dominated by *viability* — cost alone scored +0.53
and warmth alone +0.53, each beating the entire activity model at +0.32. Adding more evidence
of the same kinds makes the activity measurement better supported without changing what it is
a measurement *of*. More corroboration raises confidence in each detection; it does not change
the ordering, because the ordering was never limited by evidence volume.

So the honest summary of this pass is: **the detections are better corroborated and less
geographically skewed, and the index is no more accurate than it was.** Reaching ρ ≥ 0.80
still requires the items at the top of the credentials list — city-level cost data above all,
and a larger labelled reference set — not more of what is already free.

One caveat on the geography: ranked localities are now 42% Europe, 22% Asia, 19% North
America, 10% Africa, 5% South America, 2% Oceania. Europe is still over-represented relative
to where nomads actually are. The widening narrowed that gap; it did not close it.
