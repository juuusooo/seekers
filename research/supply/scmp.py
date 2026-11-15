"""Paired comparison of server rows written by server.ts.
  python scmp.py TAG [BASE_LABEL]     rows: server/<TAG>.jsonl; only seeds that both the base and the variant played."""
import json, math, os, statistics as st, sys

tag = sys.argv[1]
base = sys.argv[2] if len(sys.argv) > 2 else "base"
rows = {}
HERE = os.path.dirname(os.path.abspath(__file__))
live = os.path.join(HERE, "out", "server", tag + ".jsonl")   # a run in progress writes here
for line in open(live if os.path.exists(live) else os.path.join(HERE, "server", tag + ".jsonl")):
    r = json.loads(line)
    rows.setdefault(r["variant"], {})[r["seed"]] = r
b = rows[base]
z = lambda r: r["margin"] if r["ranked"] else 0
se = lambda d: st.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0
print(f"{'variant':12} {'n':>3} {'margin':>7} {'diff':>6} {'±se':>4} {'b/w':>6} {'scored':>7} {'orders':>6} {'ranked':>6} {'onT%':>5} {'worst':>5}   base on the same weeks: margin, ranked, worst")
for name, v in rows.items():
    seeds = sorted(set(v) & set(b))
    if not seeds:
        continue
    d = [v[s]["margin"] - b[s]["margin"] for s in seeds]
    dz = [z(v[s]) - z(b[s]) for s in seeds]
    print(f"{name:12} {len(seeds):3d} {st.mean(v[s]['margin'] for s in seeds):7.0f} {st.mean(d):+6.0f} {se(d):4.0f} {sum(x > 0 for x in d):3d}/{sum(x < 0 for x in d):<3d}"
          f"{st.mean(dz):+7.0f} {st.mean(v[s]['won'] for s in seeds):6.0f} {sum(v[s]['ranked'] for s in seeds):3d}/{len(seeds):<3d}"
          f"{100 * st.mean(v[s]['onTime'] for s in seeds):5.1f} {100 * min(v[s]['onTime'] for s in seeds):5.1f}   "
          f"{st.mean(b[s]['margin'] for s in seeds):7.0f} {sum(b[s]['ranked'] for s in seeds):3d} {100 * min(b[s]['onTime'] for s in seeds):5.1f}")
