# Scoring

Every number on the map is derived from evidence collected in this build. No
component of the score reads a reputation list, a "best places" ranking, or any
prior belief about a destination.

## Nomad Live Score (0–100)

| Component | Weight | What it measures |
|---|---|---|
| Nomad presence | 25% | Attention per capita, current attention volume, nomad-specific venue and event density, community chatter |
| Live event activity | 25% | Events per week, distinct organisers, distinct venues, category diversity, nomad-oriented events |
| Community activity | 20% | Recent public posts mentioning the place, source diversity, organiser and nomad-event continuity |
| Coworking infrastructure | 10% | Coworking, coliving and hackerspace weight, absolute and per capita |
| International / social ecosystem | 10% | Hostels, language schools, nightlife, social venues, absolute and per capita |
| Momentum | 5% | Recent attention window vs previous window, plus event recency skew |
| Evidence confidence | 5% | Corroboration, see below |

Weights live in `WEIGHTS` in `pipeline/step6_h3.py`, are shipped into the page,
and are displayed in the UI so the interface always describes the model that
produced the numbers on screen.

Every input passes through a saturating curve `1 − e^(−x/k)`. This is why a city
ten times bigger does not score ten times higher: the curve is deliberately
sub-linear, and per-capita terms sit alongside absolute terms throughout.

## Bands

| Score | Band |
|---|---|
| 90–100 | EXTREMELY HOT |
| 80–89 | VERY ACTIVE |
| 70–79 | ACTIVE |
| 55–69 | MODERATE |
| 40–54 | QUIET |
| 0–39 | LOW ACTIVITY |

## Nomad presence

Reported as a band — VERY LOW … VERY HIGH — with a confidence percentage.
**A nomad headcount is never displayed**, because no credential-free source can
substantiate one. "Presence: VERY HIGH, confidence 82%" is honest;
"3,714 nomads" would not be.

## Active Community Density

Answers: *if I arrive here alone, how easy is it likely to be to enter a
substantial active international ecosystem?*

It combines upcoming events and distinct organisers, the strength of the single
best hotspot cluster, geographic concentration (what share of a city's evidence
weight sits in its top five cells), coworking and community infrastructure, and
community chatter. Concentration is a first-class input: a compact, walkable
community scores above a diffuse one of the same size. Large cities do not
dominate automatically — `test_population_does_not_dominate_density` asserts it.

## Event quality, not event count

Events are deduplicated across sources on a normalised title plus date. Online
and cancelled events are dropped. Events outside a −14 day … +90 day window are
dropped. What is scored is events per week, distinct organisers, distinct
venues, category diversity, and the share that are nomad-oriented — so twenty
listings from one organiser score below eight from five organisers.

Categories: digital nomad, coworking, startup, technology, networking, language
exchange, expat/international, nightlife, outdoor/hiking, wellness, sport,
cultural, creative, music/festival, social.

## Momentum

Attention in the last 14 days against the previous 14, from dated Wikipedia
pageview dumps — a genuine before/after comparison, not a guess.

STRONGLY RISING ≥1.35 · RISING ≥1.10 · STABLE ≥0.92 · COOLING ≥0.75 ·
STRONGLY COOLING below · UNKNOWN when there is not enough coverage to say.

## Confidence — separate from score

Confidence rises with the number of independent sources, total evidence volume,
the diversity of evidence families, how much of the attention window is
covered, whether any point-precision cell evidence exists, and whether any event
evidence exists. It is reduced when the place's Wikipedia title is ambiguous.

Score and confidence are always displayed together. *Score 78, confidence 43%*
is a legitimate and useful output.

## Freshness

LIVE ≤24 h · <7 DAYS ≤168 h · <30 DAYS ≤720 h · STALE beyond. Nothing is
labelled LIVE on the strength of month-old evidence.

## Warnings

Computed per locality, shown before the numbers:

- **LOW DATA CONFIDENCE** — confidence under 45%.
- **HISTORICALLY POPULAR, CURRENTLY QUIET** — high attention, thin live event
  and community evidence. This is the reputation trap the product exists to
  catch.
- **STRONG INFRASTRUCTURE BUT WEAK COMMUNITY** — coworking exists, current
  social evidence does not.
- **EVENT ACTIVITY DOMINATED BY ONE ORGANIZER** — one organiser behind nearly
  everything listed.
- **ACTIVITY RAPIDLY COOLING** — attention well below the previous window.
- **VERY ACTIVE BUT HIGHLY DISPERSED** — scores well, but the evidence forms no
  walkable hub.
- **NO CLEAR CONCENTRATED HOTSPOT** — scores well, but no contiguous cluster
  emerged.

## Region roll-ups

A region never reports only a mean. It reports mean, median, maximum locality,
population-weighted and evidence-weighted scores, the count of hot localities,
the active-locality percentage, a concentration ratio and its single top
locality — so a country with one very hot city and a quiet hinterland reads as
exactly that, and the hotspot is never averaged away.
