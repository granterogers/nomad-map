"""Generate DATA_SOURCES.md and HANDOVER.md from the live audit + registry."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import read_json

DOCS = os.path.join(common.ROOT, "docs")

INTRO = """# Data sources

Every source below was **tested from this environment**, not assumed. Status
values are what the probe actually returned, and the probe is re-runnable:
`python3 pipeline/probe_sources.py`.

- **ACTIVE** — reachable anonymously and contributing evidence.
- **OPTIONAL** — reachable, but the useful data sits behind a credential, a
  login wall or terms that forbid automated collection. Contribution: zero.
- **BLOCKED** — refused automated access from here (401/403/404/429).
  Contribution: zero.
- **REJECTED** — reachable but unusable for this purpose, or a control probe.

Nothing here bypasses a login, a CAPTCHA, an anti-bot system, a paywall or any
access control. Where a platform publishes schema.org structured data on public
pages for indexing, that public markup is what is read, and robots.txt is
respected — Meetup's `/find/` path is not disallowed; its `/files/`, `/fb/`,
`/preview/`, `/n/*` and calendar feed paths are, and are not touched.

"""


def main():
    audit = read_json("source_audit.json", {"results": []})["results"]
    reg = read_json("source_registry.json", {})
    eco = read_json("ecosystem.json", {})
    att = read_json("attention.json", {})
    evs = read_json("events.json", {"places": {}})
    comm = read_json("community.json", {"places": {}})
    sc = read_json("scored.json", {"localities": []})

    lines = [INTRO]
    lines.append("## Sources currently contributing evidence\n")
    lines.append("| Source | Domain | Type | Access | Reliability | Coverage |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(reg.values(), key=lambda x: -(x.get("coverage") or 0)):
        if not (r.get("success_count") or r.get("coverage")):
            continue
        lines.append(f'| {r.get("source_name", r["source_id"])} | `{r.get("domain","")}` | '
                     f'{r.get("source_type","")} | {r.get("access_method","")} | '
                     f'{round(r["reliability"]*100) if r.get("reliability") is not None else 100}% | '
                     f'{(r.get("coverage") or 0):,} |')

    lines.append("\n### What each contributes\n")
    lines.append(f"- **OpenStreetMap planet via QLever** — "
                 f"{sum(eco.get('global_object_counts', {}).values()):,} matching objects worldwide, "
                 f"{sum(len(v['venues']) for v in eco.get('places', {}).values()):,} attributed to "
                 f"{len(eco.get('places', {})):,} localities. This is the only source with true "
                 f"point precision everywhere, so it is what makes sub-city hotspots possible.")
    lines.append(f"- **Wikimedia hourly pageview dumps** — dated daily series for "
                 f"{len(att.get('places', {})):,} places over "
                 f"{att.get('recent_window_days',0)+att.get('prior_window_days',0)} days "
                 f"({att.get('files_ok',0)}/{att.get('files_attempted',0)} hourly files streamed). "
                 f"Supplies current attention and real momentum.")
    ne = sum(len(v["events"]) for v in evs["places"].values())
    lines.append(f"- **Meetup + Luma public listings** — {ne:,} schema.org Event objects across "
                 f"{len(evs['places']):,} localities, with organiser and venue.")
    lines.append(f"- **Reddit / Mastodon / Lemmy / Hacker News** — "
                 f"{comm.get('posts_scanned',0):,} recent public posts scanned, attributed to "
                 f"{len(comm.get('places', {})):,} localities at city precision.")
    lines.append("- **GeoNames + Wikidata** — the place universe and the "
                 "GeoNames↔Wikipedia crosswalk that lets attention attach to places.")

    lines.append("\n## Full audit\n")
    by = defaultdict(list)
    for a in audit:
        by[a["status"]].append(a)
    for st in ("ACTIVE", "OPTIONAL", "BLOCKED", "REJECTED"):
        rows = sorted(by.get(st, []), key=lambda r: (r["family"], r["source"]))
        if not rows:
            continue
        lines.append(f"\n### {st} ({len(rows)})\n")
        lines.append("| Source | Family | HTTP | Credential | Note |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append(f'| {r["source"]} | {r["family"]} | {r.get("http") or "—"} | '
                         f'{"yes" if r["credential_required"] else "no"} | {r.get("notes","")} |')

    lines.append("""
## Architecture changes forced by source testing

**Overpass → QLever.** The ecosystem layer originally queried Overpass per
candidate city. `overpass-api.de` began returning 504s, and independently the
session's egress relay closes tunnels that go ~6–7 s without bytes — which is
precisely how Overpass behaves while planning a query. Measured throughput:
~1 successful query per minute, against a need for thousands. QLever's
OSM-planet SPARQL endpoint answers planet-wide queries in 1–3 s and is
credential-free. The switch was also a product upgrade: instead of inspecting
only a pre-chosen candidate list, every matching object on Earth is retrieved,
so a hotspot can emerge anywhere. `overpass.openstreetmap.fr` was verified as a
working fallback (5/5 successes at ~1.8 s).

**Wikimedia REST API → Wikimedia dumps.** Every Wikimedia API host returns 429
for this environment's shared egress IP. The static dump server is not blocked,
so the attention layer stream-filters hourly pageview files without storing
them. The capability was preserved rather than dropped.

**Reddit JSON/OAuth → Reddit Atom.** The JSON and OAuth APIs return 403. The
public `.rss` feeds do not, so the adapter parses Atom.

## Sources deliberately not used

Google Places, Google Trends, Foursquare, Instagram, Facebook Groups and Events,
TikTok, WhatsApp, X, LinkedIn, InterNations, Couchsurfing, Nomads.com, AirDNA
and Coworker.com all require credentials, a login, payment, or forbid automated
collection. Each is listed in the audit, contributes exactly zero, and is shown
in the UI as contributing zero — per place, in the source-coverage panel. The
product's strength is multi-source corroboration; no single proprietary provider
determines whether it works.
""")
    open(os.path.join(DOCS, "DATA_SOURCES.md"), "w").write("\n".join(lines) + "\n")
    print("wrote docs/DATA_SOURCES.md")


if __name__ == "__main__":
    main()
