"""by_class.py: late share and failed visits per note class for each variant of a kit-notes bench tag.
Run from Bahn-Spread/ after pull_mine.ts: python research/notes/by_class.py "nt1 " """
import json, sys, os, collections
sys.path.insert(0, "research/notes")
import build
from classes import truth, late

tag = sys.argv[1]
rows = []
for line in open("runs/bench.jsonl"):
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("kit") == "kit-notes" and str(r.get("variant", "")).startswith(tag):
        rows.append(r)
build.BENCH.update({r["worldId"]: r for r in rows})
S = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
W = collections.Counter()
for r in rows:
    f = f"runs/events/{r['worldId']}.events.json.gz"
    if not os.path.exists(f):
        continue
    v = r["variant"][len(tag):]
    W[v] += 1
    for o in build.week(f):
        if o["cancelled"]:
            continue
        c = truth(o)
        k = "no_note" if o["note"] is None else (sorted(c)[0] if c else "harmless")
        for key in (k, "ALL"):
            s = S[v][key]
            s["n"] += 1
            s["late"] += late(o)
            s["fails"] += len(o["fails"])
            s["price"] += o["price"]
print(dict(W))
for k in ["ALL", "pickup_hours", "delivery_hours", "deadline", "plates", "manual", "ready_later", "payment", "harmless", "no_note"]:
    print(k)
    for v in sorted(W):
        s = S[v][k]
        if s["n"]:
            print(f"   {v:8} orders/wk {s['n']/W[v]:6.1f}  price {s['price']/s['n']/100:5.0f}  late {100*s['late']/s['n']:5.1f}%  late/wk {s['late']/W[v]:5.2f}  failed visits/wk {s['fails']/W[v]:5.2f}")
