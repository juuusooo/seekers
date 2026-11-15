"""Runs a variants file on both local worlds (v4 and the tight world T) and prints one pooled table.
  python stage.py SEEDS VARIANTS_FILE TAG [top N]"""
import sys, math, json, os
from ab import play, table
WORLDS = {"v4": "", "T": "workPow=3.2"}
SEARCH = "m-1..48,h-1..48"
HELD = "k-1..64,rd-1..48,sv-1..48"
def run(seeds, vfile, tag):
    out = {}
    for wname, sim in WORLDS.items():
        rows = play(seeds, vfile, sim, f"{tag}_{wname}")
        base = next(iter(rows))
        out[wname] = {r["name"]: r for r in table(rows, base)}
    return out
def pooled(out):
    res = []
    for name in out["v4"]:
        a, b = out["v4"][name], out["T"][name]
        d = (a["sdiff"] + b["sdiff"]) / 2; se = math.sqrt(a["sse"] ** 2 + b["sse"] ** 2) / 2
        res.append((name, d, se, a, b))
    return res
def show(res, top=None):
    print(f"{'variant':40} | {'pooled':>6} {'±se':>4} {'t':>5} | {'v4 diff':>7} {'±se':>4} {'ord':>5} {'rk':>3} {'worst':>5} | {'T diff':>7} {'±se':>4} {'smooth':>6} {'scored':>6} {'ord':>5} {'rk':>3} {'onT':>5} {'worst':>5}")
    for name, d, se, a, b in (res[:top] if top else res):
        t = d / se if se else 0
        print(f"{name[:40]:40} | {d:+6.0f} {se:4.0f} {t:+5.1f} | {a['diff']:+7.0f} {a['se']:4.0f} {a['orders']:5.0f} {a['ranked']:3d} {a['worst']:5.1f} | {b['diff']:+7.0f} {b['se']:4.0f} {b['sdiff']:+6.0f} {b['zdiff']:+6.0f} {b['orders']:5.0f} {b['ranked']:3d} {b['ontime']:5.1f} {b['worst']:5.1f}")
if __name__ == "__main__":
    seeds = {"search": SEARCH, "held": HELD}.get(sys.argv[1], sys.argv[1])
    out = run(seeds, sys.argv[2], sys.argv[3]); res = pooled(out)
    json.dump([(n, d, se, a, b) for n, d, se, a, b in res], open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", sys.argv[3] + ".json"), "w"))
    if len(sys.argv) > 4: res = [res[0]] + sorted(res[1:], key=lambda r: -r[1])
    show(res, int(sys.argv[4]) if len(sys.argv) > 4 else None)
