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

## Two corrections applied before anything is scored

**Mapping-density normalisation.** A raw count of coworking spaces mostly
measures how thoroughly OpenStreetMap has been mapped in that region: France
records 4.06 mapped coworking spaces per 100,000 people, Indonesia 0.06. Every
infrastructure signal is therefore scored as a *share* of what OSM has mapped
locally, using a baseline of deliberately nomad-irrelevant civic tags
(pharmacies, fuel stations, supermarkets, banks, hairdressers, post boxes —
2.27 million objects). The share is shrunk toward the global rate with an
empirical-Bayes prior so a hamlet with one coworking space and two pharmacies
cannot outrank a real ecosystem. 70% of each infrastructure metric comes from
this share, 30% from absolute scale.

**Specificity weighting.** Weight now follows how much a tag actually says about
digital nomads, not how many of them OSM happens to contain. `sports_centre`
(208,006 objects) is weighted 0.0 and is not evidence at all; `community_centre`
(147,056 objects) is 0.05. Coworking, coliving and hackerspaces carry 2.0–3.0.
Before this change those two tags alone carried 49% of all evidence weight.

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

## Two scales

The same model is computed twice and the app toggles between them.

**Absolute** (default). Counts are raw, so a city with more events scores higher.
Large cities are favoured by construction — that is a true statement about
volume, and it is the better-validated of the two scales.

**Per capita.** Every count-based term is divided by population, shrunk by a
prior of 60,000 residents (`POP_PRIOR`) so a village with three events cannot
outrank a real ecosystem. Saturation constants are fitted from the 90th
percentile of the actual per-head distribution across ranked localities. The
scale-free components — momentum, confidence, and the mapping-density shares —
are identical in both views; only the count-based ones change.

**An honest caveat, measured rather than assumed.** Per capita scores *worse*
against the reference set (Spearman 0.09 vs 0.32, AUC 0.63 vs 0.79, 11 negative
controls in the top 30 vs 4). Dividing out population removes one bias but
amplifies another: mid-sized Western European cities show high detected events
per head largely because Meetup's own coverage is strongest there, and the
absolute scale was partly masking that with megacity volume. The per-capita view
is a genuinely useful exploratory lens — it surfaces places like Sliema and
Herceg Novi that absolute volume buries — but it is not a better ranking, and
the app says so in its Method tab.

H3 cell colouring does not change between scales: a cell measures the
concentration of evidence inside it, and there is no population figure at cell
resolution to divide by.

## The corroboration gate

A locality enters the **ranking** only if it has evidence from two or more
independent families, at least one of which is nomad-targeted:

| Family | Sources |
|---|---|
| infrastructure | OpenStreetMap venues |
| events | Meetup, Luma, coworking-space ICS/RSS feeds |
| community | Reddit, Mastodon, Lemmy, Hacker News |
| attention | Wikimedia pageview dumps |

Infrastructure plus general pageviews is *not* evidence that nomads are there —
it is evidence that a town exists and that people read about it. Places failing
the gate still render on the map with all their evidence, and carry an explicit
`NOT RANKED — INFRASTRUCTURE ONLY` warning, but they do not appear in the
rankings. This is the difference between "we observed things here" and "this is
a nomad destination".

## Region roll-ups

A region never reports only a mean. It reports mean, median, maximum locality,
population-weighted and evidence-weighted scores, the count of hot localities,
the active-locality percentage, a concentration ratio and its single top
locality — so a country with one very hot city and a quiet hinterland reads as
exactly that, and the hotspot is never averaged away.
