"""Paired server results (runs/bench.jsonl, kit-cost).  srvcmp.py TAG BASE_LABEL [VARIANT_LABEL ...]"""
import json, statistics as st, sys
tag, base = sys.argv[1], sys.argv[2]
R = {}
for l in open("runs/bench.jsonl"):
    try: r = json.loads(l)
    except ValueError: continue
    v = r.get("variant", "")
    if r.get("kit") == "kit-cost" and v.startswith(tag + " "): R.setdefault(v[len(tag) + 1:], {})[r["seed"]] = r
b = R[base]
for v, d in R.items():
    if len(sys.argv) > 3 and v not in sys.argv[2:]: continue
    k = sorted(set(d) & set(b)); df = [d[s]["margin"] - b[s]["margin"] for s in k]
    z = [d[s]["margin"] * d[s]["ranked"] - b[s]["margin"] * b[s]["ranked"] for s in k]
    se = st.stdev(df) / len(k) ** .5 if len(k) > 1 else 0
    print(f"{v:10s} vs {base}: n={len(k)} margin {st.mean(d[s]['margin'] for s in k):7.0f} diff {st.mean(df):+6.0f} ± {se:3.0f} better {sum(x > 0 for x in df)}/{sum(x < 0 for x in df)} scored diff {st.mean(z):+6.0f} orders {st.mean(d[s]['won'] for s in k):.0f} vs {st.mean(b[s]['won'] for s in k):.0f} ranked {sum(d[s]['ranked'] for s in k)} vs {sum(b[s]['ranked'] for s in k)} worst on time {min(d[s]['onTime'] for s in k):.3f} vs {min(b[s]['onTime'] for s in k):.3f} mean {st.mean(d[s]['onTime'] for s in k):.3f}")
