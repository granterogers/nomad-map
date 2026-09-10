"""Step 2 - Live attention layer (spec §18, §35).

The Wikimedia pageviews REST API is rate-limited to this environment's shared
egress IP (HTTP 429 on every host: wikimedia.org, api.wikimedia.org,
*.wikipedia.org). Rather than drop the capability, we take the credential-free
static dump server (dumps.wikimedia.org), which is reachable, and stream-filter
the hourly pageview files without ever storing them.

Result: a real, dated, per-place daily attention time series -> current
interest, momentum (recent window vs previous window) and freshness. No
reputation, no invented numbers.
"""
import gzip, io, os, sys, time, urllib.request, urllib.parse, json, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import write_json, read_json, register, note_result

BASE = "https://dumps.wikimedia.org/other/pageviews"
HOURS = [3, 9, 15, 21]          # 4 samples/day -> diurnal coverage at 1/6 the bandwidth
RECENT_DAYS = 14                # current window
PRIOR_DAYS = 14                 # comparison window for momentum
PROJECTS = {"en", "en.m"}


def norm(t: str) -> str:
    return t.replace(" ", "_")


def build_title_index():
    """Two candidate title sources per place, tracked separately:
      - 'xw'   : the Wikidata GeoNames->enwiki crosswalk (authoritative but has gaps:
                 it needs both P1566 and P1082 on the item, which many big cities lack)
      - 'name' : the place's own name as a title, accepted at fold time only when this
                 place is the largest global claimant of that name and is big enough
                 for the bare title to plausibly be about it.
    Ambiguity is resolved at fold time and always recorded on the output record."""
    gb = read_json("geobase.json")
    idx = {}
    for p in gb["places"]:
        w = p.get("wiki")
        if w:
            idx.setdefault(norm(w), []).append((p["gid"], "xw"))
        if p["pop"] >= 20000:
            for cand in {p["name"], p["ascii"]}:
                t = norm(cand)
                if t and t[0].isalpha() and len(t) >= 4:
                    idx.setdefault(t, []).append((p["gid"], "name"))
    return idx, gb


def stream_hour(day: str, hour: int, titles: set, out: dict, lock: threading.Lock):
    url = f"{BASE}/{day[:4]}/{day[:4]}-{day[4:6]}/pageviews-{day}-{hour:02d}0000.gz"
    req = urllib.request.Request(url, headers={"User-Agent": common.UA})
    got = 0
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for raw in io.TextIOWrapper(gz, encoding="utf-8", errors="replace"):
                    # format: "<project> <title> <count> <bytes>"
                    sp = raw.split(" ")
                    if len(sp) < 3 or sp[0] not in PROJECTS:
                        continue
                    t = sp[1]
                    if t not in titles:
                        continue
                    try:
                        c = int(sp[2])
                    except ValueError:
                        continue
                    with lock:
                        out.setdefault(t, {}).setdefault(day, 0)
                        out[t][day] += c
                    got += 1
    except Exception as e:
        note_result("wikimedia_pageview_dumps", False, f"{day}-{hour}: {type(e).__name__}: {e}")
        return None
    note_result("wikimedia_pageview_dumps", True)
    return got


def main():
    idx, gb = build_title_index()
    titles = set(idx)
    print(f"tracking {len(titles)} Wikipedia titles mapped to places")

    # Dumps land ~1h after the hour; start from 2 days ago to guarantee availability.
    end = datetime.now(timezone.utc).date() - timedelta(days=2)
    days = [(end - timedelta(days=i)).strftime("%Y%m%d")
            for i in range(RECENT_DAYS + PRIOR_DAYS)]
    jobs = [(d, h) for d in days for h in HOURS]
    print(f"streaming {len(jobs)} hourly dumps ({len(days)} days x {len(HOURS)} hours)")

    counts, lock = {}, threading.Lock()
    done = [0]

    def run(job):
        d, h = job
        r = stream_hour(d, h, titles, counts, lock)
        with lock:
            done[0] += 1
            if done[0] % 8 == 0:
                print(f"  {done[0]}/{len(jobs)} files, {len(counts)} titles seen", flush=True)
        return r

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(run, jobs))
    ok = sum(1 for r in results if r is not None)
    print(f"streamed {ok}/{len(jobs)} files in {time.time()-t0:.0f}s; "
          f"{len(counts)} titles with data")

    # Fold title series onto places (a title may map to >1 geonames id; the
    # attention is attributed to the most populous claimant only, and flagged.)
    gid_pop = {p["gid"]: p["pop"] for p in gb["places"]}
    gid_name = {p["gid"]: norm(p["name"]) for p in gb["places"]}

    # 1. each title goes to one place: exact self-name match first, then population
    claim = {}
    for t, cands in idx.items():
        if t not in counts:
            continue
        ranked = sorted(cands, key=lambda c: (
            0 if gid_name.get(c[0]) == t else 1,      # the place actually called this
            0 if c[1] == "xw" else 1,                 # then the authoritative crosswalk
            -gid_pop.get(c[0], 0)))                   # then the largest claimant
        gid, how = ranked[0]
        if how == "name" and gid_pop.get(gid, 0) < 20000:
            continue
        claim.setdefault(gid, []).append((t, how, len(cands)))

    # 2. each place keeps its single best title
    series = {}
    for gid, titles in claim.items():
        titles.sort(key=lambda x: (0 if gid_name.get(gid) == x[0] else 1,
                                   0 if x[1] == "xw" else 1,
                                   -sum(counts[x[0]].values())))
        t, how, ncand = titles[0]
        series[str(gid)] = {"title": t, "days": counts[t], "ambiguous": ncand > 1,
                            "match": how}

    recent = set(days[:RECENT_DAYS])
    prior = set(days[RECENT_DAYS:])
    out = {}
    for gid, rec in series.items():
        d = rec["days"]
        r = sum(v for k, v in d.items() if k in recent)
        p = sum(v for k, v in d.items() if k in prior)
        rd = len([k for k in d if k in recent])
        pd = len([k for k in d if k in prior])
        out[gid] = {
            "title": rec["title"],
            "recent_views": r, "prior_views": p,
            "recent_days_covered": rd, "prior_days_covered": pd,
            "daily_avg": round(r / max(rd, 1), 1),
            "momentum_ratio": round((r / max(rd, 1)) / max(p / max(pd, 1), 0.5), 3) if pd else None,
            "ambiguous_title": rec["ambiguous"], "title_match": rec.get("match", "xw"),
            "series": {k: v for k, v in sorted(d.items())},
        }

    write_json("attention.json", {
        "generated_at": common.iso(),
        "method": "Wikimedia hourly pageview dumps, stream-filtered",
        "sample_hours_utc": HOURS, "recent_window_days": RECENT_DAYS,
        "prior_window_days": PRIOR_DAYS,
        "files_ok": ok, "files_attempted": len(jobs),
        "window_end": days[0], "window_start": days[-1],
        "places": out,
    })
    register("wikimedia_pageview_dumps", source_name="Wikimedia hourly pageview dumps",
             domain="dumps.wikimedia.org", source_type="attention/momentum",
             access_method="anonymous static file streaming", credential_required=False,
             geographic_scope="global", coverage=len(out),
             freshness=f"{RECENT_DAYS}d window ending {days[0]}",
             terms_notes="CC0; REST pageviews API is 429-blocked for this egress IP")
    common.save_registry()
    print(f"wrote data/attention.json with {len(out)} places")


if __name__ == "__main__":
    main()
