import json, math, re, unicodedata
from collections import Counter
D="/home/user/nomad-map/data"
L=json.load(open(f"{D}/scored.json"))["localities"]
eco=json.load(open(f"{D}/ecosystem.json"))["places"]
gb=json.load(open(f"{D}/geobase.json"))

# ---- 11. matcher structurally excludes short place names ----
print("=== 11. BUG: the community matcher drops any place name under 5 characters ===")
STOP={"of","most","best","why","san","new","one","are","for","the","and","but","not","you","mobile",
      "reading","bath","nice","split","hope","york","boston","paris","same","many","general","industry",
      "independence","liberty","cost","price","union","victoria","aurora","eight","normal","surprise",
      "enterprise","hot springs","riverside","lake","valley","or"}
def strip(s): return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
ranked=sorted(gb["places"],key=lambda p:-p["pop"])[:4000]
short=[p for p in ranked if len(strip(p["name"]).lower())<5]
stopped=[p for p in ranked if strip(p["name"]).lower() in STOP]
print(f"  Of the 4,000 places the matcher considers:")
print(f"    excluded for name length < 5 : {len(short):,}")
print(f"    excluded as a common word    : {len(stopped):,}")
notable=[p["name"] for p in short if p["name"] in
   ("Ubud","Goa","Hoi An","Nice","Rome","Lima","Bali","Baku","Riga","Oslo","Doha","Kiev","Cusco","Split","Porto","Pune","Xian","Graz","Bonn","Linz","Faro")]
print(f"    among them: {', '.join(sorted(set(notable))[:14])}")
print("  -> these places can NEVER receive a community mention. Their community")
print("     component is structurally 0, which is not the same as 'no discussion'.")
print("  Note 'Split', 'Nice', 'Reading', 'Bath', 'Paris' are also on the stop-word")
print("     list, so they are silenced too - a deliberate trade to avoid false hits.")

# ---- 12. counterfactual: score on nomad-specific evidence only ----
print("\n=== 12. COUNTERFACTUAL: rank on nomad-SPECIFIC evidence only ===")
print("   (coworking + coliving + hackerspace per capita, x events, x community;")
print("    generic urban infrastructure removed entirely)")
def sat(x,k): return 1-math.exp(-max(x,0)/k)
rows=[]
for x in L:
    rec=eco.get(str(x["gid"]))
    if not rec: continue
    cw=sum(1 for v in rec["venues"] if v["kind"] in ("coworking","coworking_space","coliving","hackerspace"))
    if x["pop"]<20000: continue
    per=cw/max(x["pop"]/100000,0.5)
    s=100*(0.45*sat(per,1.4)+0.30*sat(x["events_total"],12)+0.15*sat(x["community_posts"],2)
           +0.10*sat(cw,10))
    rows.append((s,x["name"],x["cc"],cw,round(per,2),x["events_total"],x["live_score"]))
rows.sort(reverse=True)
print(f"\n  {'place':22} {'new':>5} {'shipped':>8} {'cowork':>7} {'/100k':>7} {'events':>7}")
for r in rows[:18]:
    print(f"  {r[1][:21]:22} {r[0]:>5.0f} {r[6]:>8} {r[3]:>7} {r[4]:>7} {r[5]:>7}")
print("\n  Movement for the hubs the shipped index buries:")
pos={ (r[1],r[2]):i+1 for i,r in enumerate(rows)}
old=sorted(L,key=lambda z:-z["live_score"]); oldpos={(x["name"],x["cc"]):i+1 for i,x in enumerate(old)}
for k in [("Chiang Mai","TH"),("Ubud","ID"),("Bansko","BG"),("Tbilisi","GE"),("Medellín","CO"),
          ("Las Palmas de Gran Canaria","ES"),("Playa del Carmen","MX"),("Brussels","BE"),("Milan","IT")]:
    if k in pos and k in oldpos:
        arrow = "up" if pos[k]<oldpos[k] else "down"
        print(f"    {k[0][:26]:28} shipped #{oldpos[k]:<5} -> specificity-only #{pos[k]:<5} ({arrow})")
