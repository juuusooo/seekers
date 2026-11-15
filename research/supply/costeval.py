"""Plays the held-out weeks with each refitted cost file and compares with the shipped trees (same weeks).
  python costeval.py [SEEDS]      default: k, rd, sv (158 weeks never used in the fits)"""
import sys, os, glob, json, subprocess
from ab import B, ROOT, HERE, table, show
seeds = sys.argv[1] if len(sys.argv) > 1 else "k-1..64,rd-1..48,sv-1..48"
for world, sim in (("v4", ""), ("T", "workPow=3.2")):
    rows = {}
    files = [("shipped", None)] + [(os.path.basename(f)[len(f"cost_{world}_"):-5], f) for f in sorted(glob.glob(os.path.join(HERE, "out", f"cost_{world}_*.json")))]
    for name, f in files:
        out = os.path.join(HERE, "out", f"ce_{world}_{name}.jsonl")
        if os.path.exists(out): os.remove(out)
        cmd = [B, "--root", ROOT, "--seeds", seeds, "--variant", name, "--quiet", "--out", out] + (["--cost", f] if f else []) + (["--sim", sim] if sim else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stderr[-1500:])
        for l in open(out):
            x = json.loads(l); rows.setdefault(name, {})[x["seed"]] = x
    print(f"== world {world}: refit recipes against the shipped trees"); show(table(rows, "shipped"))
    print(f"-- the same against R0 (the shipped recipe refitted on this world's rows)"); show(table(rows, "R0", [n for n in rows if n != "shipped"]))
