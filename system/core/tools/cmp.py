"""Paired comparison of kit-max variants on the same seeds.
python3 core/tools/cmp.py TAG [BASE_LABEL]      (variants "TAG label"; base label default "base")
Margin = every week counted. z = unranked week counts 0."""

import collections
import json
import statistics as s
import sys

tag = sys.argv[1]
base_label = sys.argv[2] if len(sys.argv) > 2 else "base"
g = collections.defaultdict(dict)
from pathlib import Path

for line in open(Path(__file__).resolve().parents[3] / "runs" / "bench.jsonl"):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if (
        r.get("kit") == "kit-best"
        and r.get("level") == 8
        and str(r.get("variant", "")).startswith(tag + " ")
    ):
        g[r["variant"][len(tag) + 1 :]][r["seed"]] = r

z = lambda r: r["margin"] if r["ranked"] else 0
se = lambda d: s.stdev(d) / len(d) ** 0.5 if len(d) > 1 else 0
b = g.get(base_label, {})
print(
    f"{'variant':26s} {'n':>3s} {'margin':>7s} {'z':>7s} {'d':>6s} {'±':>4s} {'dz':>6s} {'b/w':>6s} {'ranked':>7s} {'worst':>6s} {'mean':>6s} {'orders':>6s}"
)
for v in sorted(g, key=lambda v: (v != base_label, v)):
    k = sorted(set(g[v]) & set(b)) if b and v != base_label else sorted(g[v])
    if not k:
        continue
    rows = [g[v][x] for x in k]
    m = s.mean(r["margin"] for r in rows)
    mz = s.mean(map(z, rows))
    if b and v != base_label:
        d = [g[v][x]["margin"] - b[x]["margin"] for x in k]
        dz = [z(g[v][x]) - z(b[x]) for x in k]
        cmp_ = f"{s.mean(d):+6.0f} {se(d):4.0f} {s.mean(dz):+6.0f} {sum(x > 0 for x in d):2d}/{sum(x < 0 for x in d):<3d}"
    else:
        cmp_ = f"{'':6s} {'':4s} {'':6s} {'':6s}"
    print(
        f"{v:26s} {len(k):3d} {m:7,.0f} {mz:7,.0f} {cmp_} {sum(r['ranked'] for r in rows):3d}/{len(k):<3d} {min(r['onTime'] for r in rows):6.1%} {s.mean(r['onTime'] for r in rows):6.1%} {s.mean(r['won'] for r in rows):6.0f}"
    )
