import json, math
from collections import Counter, defaultdict
D = "/home/user/nomad-map/data"
L = json.load(open(f"{D}/scored.json"))["localities"]
eco = json.load(open(f"{D}/ecosystem.json"))["places"]
gb = json.load(open(f"{D}/geobase.json"))
att = json.load(open(f"{D}/attention.json"))["places"]
comm = json.load(open(f"{D}/community.json"))["places"]
cc_name = {c: v["name"] for c, v in gb["countries"].items()}

# ---- 5. OSM mapping-completeness bias ----
print("=== 5. OSM COVERAGE BIAS: venues per 100k people, by country ===")
print("   (if OSM were mapped evenly, comparable countries would be comparable)")
pop_by_cc, ven_by_cc, cow_by_cc = Counter(), Counter(), Counter()
for rec in eco.values():
    cc = rec["cc"]
    pop_by_cc[cc] += rec["pop"]
    ven_by_cc[cc] += len(rec["venues"])
    cow_by_cc[cc] += sum(1 for v in rec["venues"] if v["kind"] in ("coworking","coworking_space","coliving"))
rows = []
for cc in pop_by_cc:
    if pop_by_cc[cc] < 3_000_000: continue
    per100k = ven_by_cc[cc] / (pop_by_cc[cc]/100_000)
    cw100k  = cow_by_cc[cc] / (pop_by_cc[cc]/100_000)
    rows.append((per100k, cw100k, cc, ven_by_cc[cc], pop_by_cc[cc]))
rows.sort(reverse=True)
print(f"\n  {'country':22} {'venues/100k':>11} {'coworking/100k':>15} {'venues':>9}")
for r in rows[:8]:
    print(f"  {cc_name.get(r[2],r[2])[:21]:22} {r[0]:>11.1f} {r[1]:>15.2f} {r[3]:>9,}")
print("  ...")
watch = ["TH","ID","VN","MX","CO","BR","IN","ZA","PT","DE","GB","NL","US","GE","AR"]
print(f"\n  {'country':22} {'venues/100k':>11} {'coworking/100k':>15} {'venues':>9}")
for cc in watch:
    if cc in pop_by_cc and pop_by_cc[cc] > 0:
        p = pop_by_cc[cc]/100_000
        print(f"  {cc_name.get(cc,cc)[:21]:22} {ven_by_cc[cc]/p:>11.1f} {cow_by_cc[cc]/p:>15.2f} {ven_by_cc[cc]:>9,}")
de = ven_by_cc["DE"]/(pop_by_cc["DE"]/100_000); th = ven_by_cc["TH"]/(pop_by_cc["TH"]/100_000)
print(f"\n  Germany maps {de/th:.1f}x more venues per person than Thailand.")
print("  Nobody believes Germany has 15x the cafes per head. This is MAPPING density,")
print("  not real density - and it flows straight into the score.")

# ---- 6. circularity in the event layer ----
print("\n=== 6. CIRCULARITY: how were event-scan targets chosen? ===")
have = {x["name"] for x in L if x["events_total"] > 0}
ranked = sorted(L, key=lambda z: -(z["parts"]["coworking_infra"]*0.4 + z["parts"]["nomad_presence"]*0.6))
top400 = {x["name"] for x in ranked[:400]}
overlap = len(have & top400)
print(f"  Event targets were picked from the ecosystem-derived score.")
print(f"  {overlap}/{len(have)} ({100*overlap/max(len(have),1):.0f}%) of event-covered places were already")
print(f"  in the top 400 by ecosystem score BEFORE events were fetched.")
print("  -> the event layer largely CONFIRMS the pre-existing ranking rather than")
print("     independently testing it. A hidden hotspot with no OSM footprint was")
print("     never given the chance to earn event points.")

# ---- 7. attribution error rates ----
print("\n=== 7. ATTRIBUTION RISK ===")
amb = sum(1 for a in att.values() if a.get("ambiguous_title"))
namematch = sum(1 for a in att.values() if a.get("title_match") == "name")
print(f"  Wikipedia titles attached : {len(att):,}")
print(f"    flagged ambiguous       : {amb:,} ({100*amb/len(att):.1f}%)")
print(f"    matched by NAME not by  : {namematch:,} ({100*namematch/len(att):.1f}%)")
print(f"    authoritative crosswalk")
print("    -> a name match is a guess that the bare title is about the biggest")
print("       claimant. Usually right, occasionally very wrong.")
mentions = sum(v["mentions"] for v in comm.values())
print(f"\n  Community mentions        : {mentions:,} across {len(comm):,} places")
one_src = sum(1 for v in comm.values() if v["unique_sources"] == 1)
print(f"    places whose community signal rests on ONE source: {one_src} "
      f"({100*one_src/len(comm):.0f}%)")
