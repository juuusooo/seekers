"""Plays variants/ideas100.txt on the local weeks in three worlds and prints the ideas by rank.
The cost file per world = shipped cost trees + the sim copy of the lateness trees (latefit_sim.py), so lateW works.
Search weeks m, h and held-out weeks k, rd, sv are shown side by side: an idea that is high on one and not on the
other is luck."""
import json, os, subprocess
from ab import B, ROOT, HERE, table
WORLDS = (("v4", "", "late_v4.json"), ("T", "workPow=3.2", "late_T.json"), ("T2", "workBase=0.07,workGig=0.1,workPow=2", "late_T.json"))
SEARCH = "m-1..48,h-1..48"; HELD = "k-1..64,rd-1..48,sv-1..48"
fam = {n: f for f, n, s in json.load(open(os.path.join(HERE, "variants", "ideas100.json")))}
def run(seeds):
    res = {}
    for w, sim, cost in WORLDS:
        out = os.path.join(HERE, "out", f"ideas_{w}.jsonl")
        if os.path.exists(out): os.remove(out)
        cmd = [B, "--root", ROOT, "--seeds", seeds, "--sets", os.path.join(HERE, "variants", "ideas100.txt"), "--quiet", "--out", out, "--cost", os.path.join(HERE, "out", cost)] + (["--sim", sim] if sim else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stderr[-1500:])
        rows = {}
        for l in open(out):
            x = json.loads(l); rows.setdefault(x["variant"], {})[x["seed"]] = x
        res[w] = {r["name"]: r for r in table(rows, "base")}
    return res
s, h = run(SEARCH), run(HELD)
def pooled(res, n, key): return sum(res[w][n][key] for w in res) / len(res)
names = [n for n in h["v4"] if n != "base"]
rank = sorted(names, key=lambda n: -pooled(h, n, "sdiff"))
b = {w: h[w]["base"] for w in h}
print(f"base, held out: margin v4 {b['v4']['margin']:.0f} / T {b['T']['margin']:.0f} / T2 {b['T2']['margin']:.0f}; ranked {b['v4']['ranked']} / {b['T']['ranked']} / {b['T2']['ranked']} of {b['v4']['n']}; orders {b['v4']['orders']:.0f}")
print(f"\n{'#':>3} {'idea':30} {'family':28} | {'search':>6} | {'HELD':>6} {'margin v4':>9} {'T':>6} {'T2':>6} | {'orders':>6} {'ranked v4/T/T2':>14} {'worst T2':>8}")
for i, n in enumerate(rank, 1):
    print(f"{i:3d} {n[:30]:30} {fam[n][:28]:28} | {pooled(s, n, 'sdiff'):+6.0f} | {pooled(h, n, 'sdiff'):+6.0f} {h['v4'][n]['diff']:+9.0f} {h['T'][n]['diff']:+6.0f} {h['T2'][n]['diff']:+6.0f} | {h['v4'][n]['orders'] - b['v4']['orders']:+6.0f} {h['v4'][n]['ranked']:4d}/{h['T'][n]['ranked']}/{h['T2'][n]['ranked']} {h['T2'][n]['worst']:8.1f}")
json.dump({"search": s, "held": h}, open(os.path.join(HERE, "out", "ideas_res.json"), "w"))
