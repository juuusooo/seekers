"""World drift and the live correction: trees fitted in one driver market, played in another, with and without resK.
  python costdrift.py"""
import os, json, subprocess
from ab import B, ROOT, HERE, table, show
SEEDS = "k-1..64,rd-1..48,sv-1..48"
def run(rows, name, cost, sim, sets=""):
    out = os.path.join(HERE, "out", "cd_tmp.jsonl")
    if os.path.exists(out): os.remove(out)
    cmd = [B, "--root", ROOT, "--seeds", SEEDS, "--variant", name, "--quiet", "--out", out] + (["--cost", os.path.join(HERE, "out", cost)] if cost else []) + (["--sim", sim] if sim else []) + (["--set", sets] if sets else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr[-1500:])
    for l in open(out):
        x = json.loads(l); rows.setdefault(name, {})[x["seed"]] = x
for title, sim, own, other in (("world T (tight): trees fitted in v4 vs trees fitted in T", "workPow=3.2", "cost_T_R0.json", "cost_v4_R0.json"), ("world v4: trees fitted in T vs trees fitted in v4", "", "cost_v4_R0.json", "cost_T_R0.json")):
    rows = {}
    run(rows, "other-world trees", other, sim)
    for k in (0.5, 1.0, 1.5): run(rows, f"other + resK {k}", other, sim, f"resK={k}")
    run(rows, "other + resK 1 resN 10", other, sim, "resK=1,resN=10")
    run(rows, "own-world trees", own, sim)
    run(rows, "own + resK 1", own, sim, "resK=1")
    run(rows, "shipped (server) trees", None, sim)
    run(rows, "shipped + resK 1", None, sim, "resK=1")
    print("==", title); show(table(rows, "other-world trees"))
