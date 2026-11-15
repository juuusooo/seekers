"""Paired sim results of the real_cost variants (runs/sim.jsonl, variants 'rc ...').  simcmp.py [BASE]"""
import json, statistics as st, sys
R = {}
for l in open("runs/sim.jsonl"):
    try: r = json.loads(l)
    except ValueError: continue
    if r.get("variant", "").startswith("lk "): R.setdefault(r["variant"], {})[r["seed"]] = r
b = R[sys.argv[1] if len(sys.argv) > 1 else "lk best10"]
for v, d in R.items():
    k = sorted(set(d) & set(b)); df = [d[s]["margin"] - b[s]["margin"] for s in k]
    se = st.stdev(df) / len(k) ** .5
    print(f"{v:18s} n={len(k)} margin {st.mean(d[s]['margin'] for s in k):8.0f} diff {st.mean(df):+7.0f} ± {se:4.0f} better {sum(x > 0 for x in df)}/{sum(x < 0 for x in df)} orders {st.mean(d[s]['won'] for s in k):.0f} ranked {sum(d[s]['ranked'] for s in k)} worst {min(d[s]['onTime'] for s in k):.3f}")
