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
from collections import defaultdict
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))
import common
from common import write_json, read_json, register, note_result

BASE = "https://dumps.wikimedia.org/other/pageviews"
HOURS = [3, 9, 15, 21]          # 4 samples/day -> diurnal coverage at 1/6 the bandwidth
RECENT_DAYS = 14                # current window
PRIOR_DAYS = 14                 # comparison window for momentum
BASE_PROJECTS = {"en", "en.m"}


def norm(t: str) -> str:
    return t.replace(" ", "_")


def build_title_index():
    """Index keyed by "<project> <title>" so a place's attention is the sum of
    what English readers AND its own language's readers actually looked at.

    Measuring English Wikipedia alone structurally under-counted every place
    whose readers do not read English Wikipedia - the single largest source of
    geographic bias in the attention layer. Same dump files, wider filter,
    no extra bandwidth.

    Two candidate title sources per place, tracked separately:
      - 'xw'   : the Wikidata GeoNames->enwiki crosswalk (authoritative but has gaps:
                 it needs both P1566 and P1082 on the item, which many big cities lack)
      - 'name' : the place's own name as a title, accepted at fold time only when this
                 place is the largest global claimant of that name and is big enough
                 for the bare title to plausibly be about it.
    Ambiguity is resolved at fold time and always recorded on the output record."""
    gb = read_json("geobase.json")
    local = (read_json("locallang.json", {}) or {}).get("places", {})
    idx, projects = {}, set(BASE_PROJECTS)
    for p in gb["places"]:
        w = p.get("wiki")
        if w:
            for pr in ("en", "en.m"):
                idx.setdefault(f"{pr} {norm(w)}", []).append((p["gid"], "xw"))
        loc = local.get(str(p["gid"]))
        if loc:
            lang, title = loc
            for pr in (lang, f"{lang}.m"):
                projects.add(pr)
                idx.setdefault(f"{pr} {norm(title)}", []).append((p["gid"], "local"))
        if p["pop"] >= 20000:
            for cand in {p["name"], p["ascii"]}:
                t = norm(cand)
                if t and t[0].isalpha() and len(t) >= 4:
                    for pr in ("en", "en.m"):
                        idx.setdefault(f"{pr} {t}", []).append((p["gid"], "name"))
    print(f"  tracking {len(projects)} Wikipedia projects")
    return idx, gb, projects


def stream_hour(day: str, hour: int, keys: set, projects: set, out: dict,
                lock: threading.Lock):
    url = f"{BASE}/{day[:4]}/{day[:4]}-{day[4:6]}/pageviews-{day}-{hour:02d}0000.gz"
    req = urllib.request.Request(url, headers={"User-Agent": common.UA})
    got = 0
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            with gzip.GzipFile(fileobj=resp) as gz:
                for raw in io.TextIOWrapper(gz, encoding="utf-8", errors="replace"):
                    # format: "<project> <title> <count> <bytes>"
                    sp = raw.split(" ")
                    if len(sp) < 3 or sp[0] not in projects:
                        continue
                    k = sp[0] + " " + sp[1]
                    if k not in keys:
                        continue
                    try:
                        c = int(sp[2])
                    except ValueError:
                        continue
                    with lock:
                        out.setdefault(k, {}).setdefault(day, 0)
                        out[k][day] += c
                    got += 1
    except Exception as e:
        note_result("wikimedia_pageview_dumps", False, f"{day}-{hour}: {type(e).__name__}: {e}")
        return None
    note_result("wikimedia_pageview_dumps", True)
    return got


def main():
    idx, gb, projects = build_title_index()
    keys = set(idx)
    print(f"tracking {len(keys):,} project/title pairs mapped to places")

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
        r = stream_hour(d, h, keys, projects, counts, lock)
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

    # 1. each project/title key goes to one place
    claim = defaultdict(list)
    for k, cands in idx.items():
        if k not in counts:
            continue
        proj, t = k.split(" ", 1)
        ranked = sorted(cands, key=lambda c: (
            0 if gid_name.get(c[0]) == t else 1,      # the place actually called this
            0 if c[1] in ("xw", "local") else 1,      # then an authoritative sitelink
            -gid_pop.get(c[0], 0)))                   # then the largest claimant
        gid, how = ranked[0]
        if how == "name" and gid_pop.get(gid, 0) < 20000:
            continue
        claim[gid].append((k, proj, how, len(cands)))

    # 2. a place's attention is the SUM across the projects that describe it,
    #    English plus its own language, deduplicated by project.
    series = {}
    for gid, keylist in claim.items():
        best_per_proj = {}
        for k, proj, how, ncand in keylist:
            tot = sum(counts[k].values())
            if proj not in best_per_proj or tot > best_per_proj[proj][1]:
                best_per_proj[proj] = (k, tot, how, ncand)
        merged, projs, hows, amb = defaultdict(int), [], set(), False
        for proj, (k, tot, how, ncand) in best_per_proj.items():
            projs.append(proj)
            hows.add(how)
            amb = amb or ncand > 1
            for d, v in counts[k].items():
                merged[d] += v
        primary = max(best_per_proj.items(), key=lambda kv: kv[1][1])
        series[str(gid)] = {"title": primary[1][0].split(" ", 1)[1],
                            "days": dict(merged), "ambiguous": amb,
                            "match": "local" if "local" in hows else
                                     ("xw" if "xw" in hows else "name"),
                            "projects": sorted(projs)}

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
            "projects": rec.get("projects", []),
            "series": {k: v for k, v in sorted(d.items())},
        }

    write_json("attention.json", {
        "generated_at": common.iso(),
        "method": "Wikimedia hourly pageview dumps, stream-filtered",
        "sample_hours_utc": HOURS, "recent_window_days": RECENT_DAYS,
        "prior_window_days": PRIOR_DAYS,
        "files_ok": ok, "files_attempted": len(jobs),
        # Recorded so the in-app validity report can state how wide the
        # language coverage actually is rather than asserting it.
        "projects_tracked": len(projects), "title_pairs": len(keys),
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
