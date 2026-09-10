"""Validity audit: does Nomad Radar measure digital-nomad activity,
or is it measuring something else that correlates with it?"""
import json, math, os, sys
from collections import Counter, defaultdict
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from step6_h3 import KIND_SPEC          # the weights the model ACTUALLY uses
D = os.path.join(ROOT, "data")
L = json.load(open(f"{D}/scored.json"))["localities"]
eco = json.load(open(f"{D}/ecosystem.json"))["places"]
att = json.load(open(f"{D}/attention.json"))["places"]
evs = json.load(open(f"{D}/events.json"))["places"]
comm = json.load(open(f"{D}/community.json"))["places"]

def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0]*len(v)
        i = 0
        while i < len(order):
            j = i
            while j+1 < len(order) and v[order[j+1]] == v[order[i]]: j += 1
            avg = (i+j)/2 + 1
            for k in range(i, j+1): r[order[k]] = avg
            i = j+1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs); mx = sum(rx)/n; my = sum(ry)/n
    num = sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry))
    return num/den if den else 0.0

# ---------- 1. what is the evidence actually made of ----------
NOMAD_SPECIFIC = {"coworking_space","coworking","coliving","hackerspace","apartment"}
NOMAD_ADJACENT = {"hostel","language_school","internet_cafe"}
GENERIC_URBAN  = {"cafe","community_centre","nightclub","bar","sports_centre","arts_centre","university"}

kind_w, kind_n = Counter(), Counter()
for rec in eco.values():
    for v in rec["venues"]:
        w = KIND_SPEC.get(v["kind"], (0.0, "social"))[0]
        kind_w[v["kind"]] += w; kind_n[v["kind"]] += 1
total_w = sum(kind_w.values())
print("=== 1. COMPOSITION OF THE ECOSYSTEM LAYER (effective weights) ===")
print(f"{'tag':20} {'objects':>9} {'weight':>10} {'% of weight':>11}  specificity")
for k, w in kind_w.most_common():
    tier = "NOMAD-SPECIFIC" if k in NOMAD_SPECIFIC else "adjacent" if k in NOMAD_ADJACENT else "generic urban"
    print(f"{k:20} {kind_n[k]:>9,} {w:>10,.0f} {100*w/total_w:>10.1f}%  {tier}")
ns = sum(w for k,w in kind_w.items() if k in NOMAD_SPECIFIC)
na = sum(w for k,w in kind_w.items() if k in NOMAD_ADJACENT)
gu = total_w - ns - na
print(f"\n  nomad-specific weight : {100*ns/total_w:5.1f}%")
print(f"  nomad-adjacent weight : {100*na/total_w:5.1f}%")
print(f"  generic-urban weight  : {100*gu/total_w:5.1f}%   <-- carries no nomad information on its own")

# ---------- 2. confound tests ----------
print("\n=== 2. IS THE SCORE JUST MEASURING CITY SIZE? (Spearman rank corr) ===")
sub = [x for x in L if x.get("ranked")] or [x for x in L if x["evidence_count"] >= 5]
print(f"  (evaluated over {len(sub):,} RANKED localities)")
pairs = {
  "live_score vs population":        ([x["live_score"] for x in sub], [x["pop"] for x in sub]),
  "live_score vs total venues":      ([x["live_score"] for x in sub], [x["venues"] for x in sub]),
  "live_score vs wiki attention":    ([x["live_score"] for x in sub], [x["daily_attention"] for x in sub]),
  "live_score vs coworking weight":  ([x["live_score"] for x in sub],
                                      [x["venue_families"].get("coworking",0) for x in sub]),
  "live_score vs events found":      ([x["live_score"] for x in sub], [x["events_total"] for x in sub]),
  "live_score vs community posts":   ([x["live_score"] for x in sub], [x["community_posts"] for x in sub]),
  "population vs wiki attention":    ([x["pop"] for x in sub], [x["daily_attention"] for x in sub]),
}
for name,(a,b) in pairs.items():
    print(f"  {name:34} rho = {spearman(a,b):+.3f}   (n={len(a):,})")

# ---------- 3. what drives the top of the ranking ----------
print("\n=== 3. TOP 15: WHERE DOES THE SCORE COME FROM? ===")
print(f"{'place':16} {'score':>5} {'evt':>4} {'comm':>5} {'cowork':>7} {'generic':>8}  {'evidence mix'}")
for x in sorted(L, key=lambda z:-z["live_score"])[:15]:
    fam = x["venue_families"]
    cw = fam.get("coworking",0); tot = sum(fam.values()) or 1
    gen = fam.get("social",0)+fam.get("community",0)
    print(f'{x["name"][:15]:16} {x["live_score"]:>5} {x["events_total"]:>4} '
          f'{x["community_posts"]:>5} {100*cw/tot:>6.0f}% {100*gen/tot:>7.0f}%  '
          f'{x["evidence_count"]} items / {x["unique_sources"]} sources')

# ---------- 4. coverage asymmetry ----------
print("\n=== 4. COVERAGE ASYMMETRY (the event layer only reached 361 places) ===")
have = [x for x in L if x["events_total"] > 0]
lack = [x for x in L if x["events_total"] == 0 and x["evidence_count"] >= 20]
def med(v): v=sorted(v); return v[len(v)//2] if v else 0
print(f"  places WITH event data : n={len(have):,}  median score {med([x['live_score'] for x in have])}"
      f"  max {max(x['live_score'] for x in have)}")
print(f"  places WITHOUT (>=20 ev): n={len(lack):,}  median score {med([x['live_score'] for x in lack])}"
      f"  max {max(x['live_score'] for x in lack)}")
print("  -> event_activity is 25% of the model. A place with no event coverage")
print("     cannot score above ~75 no matter how active it really is.")
