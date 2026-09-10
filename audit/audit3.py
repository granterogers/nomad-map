import json
from collections import Counter
D="/home/user/nomad-map/data"
L=json.load(open(f"{D}/scored.json"))["localities"]
eco=json.load(open(f"{D}/ecosystem.json"))["places"]
comm=json.load(open(f"{D}/community.json"))["places"]
byname={}
for x in L: byname.setdefault((x["name"],x["cc"]),x)

print("=== 8. FACE-VALIDITY CHECK: canonical nomad hubs vs big European cities ===")
print(f"{'place':22} {'score':>5} {'rank':>6} {'cowork objs':>11} {'events':>7} {'posts':>6}")
ranked=sorted(L,key=lambda z:-z["live_score"]); rk={ (x['name'],x['cc']):i+1 for i,x in enumerate(ranked)}
hubs=[("Chiang Mai","TH"),("Ubud","ID"),("Denpasar","ID"),("Da Nang","VN"),("Medellín","CO"),
      ("Tbilisi","GE"),("Bansko","BG"),("Chaniá","GR"),("Playa del Carmen","MX"),
      ("Las Palmas de Gran Canaria","ES"),("Ho Chi Minh City","VN"),("Mexico City","MX")]
euro=[("Amsterdam","NL"),("Berlin","DE"),("Brussels","BE"),("Milan","IT"),("Dublin","IE"),("Lisbon","PT")]
def line(k):
    x=byname.get(k)
    if not x: print(f"  {k[0][:21]:22} -- not in shipped set --"); return
    cw=sum(1 for v in eco.get(str(x['gid']),{}).get('venues',[]) if v['kind'] in ('coworking','coworking_space','coliving'))
    print(f"  {x['name'][:21]:22} {x['live_score']:>5} {rk[k]:>6} {cw:>11} {x['events_total']:>7} {x['community_posts']:>6}")
print("\n  -- widely-recognised nomad hubs --")
for k in hubs: line(k)
print("\n  -- large European cities --")
for k in euro: line(k)

print("\n=== 9. SPOT-CHECK: are the underlying objects real and relevant? ===")
x=byname[("Lisbon","PT")]
vs=eco[str(x["gid"])]["venues"]
named=[v for v in vs if v["name"] and v["kind"] in ("coworking","coworking_space","hackerspace","coliving")]
print(f"  Lisbon coworking/hackerspace objects with names ({len(named)} of {len(vs)} total venues):")
for v in named[:10]: print(f"    - {v['name'][:52]:54} [{v['kind']}] osm:{v['osm']}")
print(f"\n  Lisbon venue mix:")
for k,n in Counter(v['kind'] for v in vs).most_common(): print(f"    {k:20} {n:>5}")

print("\n=== 10. SPOT-CHECK: community name-matching false positives ===")
shown=0
for gid,v in comm.items():
    for s in v["samples"]:
        t=s["title"].lower()
        if s["matched"] not in t: continue
        if shown>=8: break
        print(f"    matched '{s['matched']}' <- [{s['channel']}] {s['title'][:78]}")
        shown+=1
    if shown>=8: break
