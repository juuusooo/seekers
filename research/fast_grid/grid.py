"""Knob search from BEST10 on sim-experimental, two worlds at once (v4 and the calibrated v5c).
  python3 research/fast_grid/grid.py scan            one knob at a time, a grid per knob -> scan.json
  python3 research/fast_grid/grid.py search [ROUNDS] joint search from the scan's good moves -> search.json
  python3 research/fast_grid/grid.py hold FILE       held-out check of the candidates in FILE (k + rd weeks)
Score of a week = margin - 2,000 per point under 92.5% on time. A move counts only when it gains in both worlds.
"""
import json, os, random, statistics as st, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BIN = ROOT / "sim-experimental/target/release/sim-experimental"
V5 = (ROOT / "runs/lab/v5c.sim").read_text().strip()
SEARCH = "m-1..48,h-1..48"
HOLD = "k-1..10,k-12..54,k-56..64,rd-1..48"
WORLDS = {"v4": "", "v5": V5}

# knob: (low, high, step for rounding, is integer)
KNOBS = {
    "minBookChance": (0.85, 0.99, 0.005), "hardChance": (0.6, 0.95, 0.01), "hardPrice": (0, 0.5, 0.01), "costW": (0.5, 2.6, 0.05), "costUp": (0, 1.5, 0.05),
    "minProfit": (0, 0.4, 0.01), "minSlackH": (0, 6, 0.25), "capPerDriver": (1, 8, 0.25), "dueCapPer": (0.04, 0.3, 0.005), "fullPrice": (0, 0.6, 0.01),
    "markupMin": (1.15, 1.45, 0.005), "markupMax": (1.6, 2.6, 0.05), "capLam": (0, 10, 0.25), "capConst": (0, 4, 0.25), "pairBack": (0, 0.2, 0.01),
    "outage": (0, 0.6, 0.02), "outageN": (3, 12, 1), "outageGap": (0.1, 0.6, 0.02), "worldN": (100, 600, 25), "lateCost": (2, 8, 0.1),
    "openMin": (0.5, 0.95, 0.01), "openMax": (1.0, 2.2, 0.05), "raiseMax": (0, 0.2, 0.05), "steps": (1, 10, 1), "rampTop": (1.0, 2.4, 0.02),
    "rampWindowH": (4, 24, 0.5), "steepOpen": (1.0, 2.6, 0.02), "steepStep": (0.02, 0.4, 0.01), "lateFee": (0.3, 1.6, 0.02), "pairKm": (0, 80, 2),
    "pairSlackH": (1, 12, 0.5), "pairCap": (0.6, 1.2, 0.02), "pairTop": (0.9, 1.8, 0.02), "pairHoldH": (1, 12, 0.5), "hoursMinLeftH": (0.5, 4, 0.25),
    "pS": (0.04, 0.25, 0.005), "pWeek": (0.01, 0.2, 0.005), "pDay": (0.04, 0.4, 0.01), "pDealer": (0, 0.1, 0.01), "pTown": (0, 0.1, 0.01),
    "dueMon": (-0.12, 0.05, 0.005), "dueFri": (-0.05, 0.25, 0.005), "floorLvl": (0, 2.5, 0.05), "noteHours": (0, 1, 1), "pairFlags": (0, 1, 1),
}
DEF = {k: float(v) for k, v in (kv.split(": ") for kv in subprocess.run([BIN, "--print-params"], capture_output=True, text=True).stdout.splitlines()[0].split("{ ")[1].rstrip(" }").split(", "))}

def rnd(k, v):
    lo, hi, step = KNOBS[k]
    return round(min(hi, max(lo, round(v / step) * step)), 6)
def key(c): return ",".join(f"{k}={c[k]:g}" for k in sorted(c))

def run(cands, seeds=SEARCH):
    """cands: list of dicts (overrides). Returns per world: {index: {seed: (margin, onTime, ranked, won)}}."""
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        sets = Path(tmp) / "sets.txt"
        sets.write_text("".join(f"c{i} {key(c)}\n" for i, c in enumerate(cands)))
        for w, sim in WORLDS.items():
            f = Path(tmp) / f"{w}.jsonl"
            cmd = [str(BIN), "--seeds", seeds, "--sets", str(sets), "--quiet", "--out", str(f)] + (["--sim", sim] if sim else [])
            subprocess.run(cmd, check=True, capture_output=True)
            res = {}
            for l in open(f):
                r = json.loads(l)
                res.setdefault(int(r["variant"][1:]), {})[r["seed"]] = (r["margin"], r["onTime"], r["ranked"], r["won"])
            out[w] = res
    return out
def wk(x): return x[0] - 2000 * 100 * max(0.0, 0.925 - x[1])
def paired(a, b):
    """a, b: {seed: row}. Mean difference of the week score a - b with its SE."""
    d = [wk(a[s]) - wk(b[s]) for s in a]
    return st.mean(d), st.stdev(d) / len(d) ** 0.5
def summ(a):
    return {"margin": st.mean(x[0] for x in a.values()), "z": st.mean(x[0] if x[2] else 0 for x in a.values()), "ranked": sum(x[2] for x in a.values()), "n": len(a), "worst": min(x[1] for x in a.values()), "orders": st.mean(x[3] for x in a.values())}
def both(res, i, base=0):
    d = {w: paired(res[w][i], res[w][base]) for w in WORLDS}
    pooled = [wk(res[w][i][s]) - wk(res[w][base][s]) for w in WORLDS for s in res[w][i]]
    return d, (st.mean(pooled), st.stdev(pooled) / len(pooled) ** 0.5)

mode = sys.argv[1]
if mode == "scan":
    cands = [{}]
    for k, (lo, hi, step) in KNOBS.items():
        n = 2 if hi - lo <= step else 9
        for j in range(n):
            v = rnd(k, lo + (hi - lo) * j / (n - 1))
            if v != DEF[k] and {k: v} not in cands: cands.append({k: v})
        for f in (0.9, 0.95, 1.05, 1.1):  # and close to the default
            v = rnd(k, DEF[k] * f)
            if v != DEF[k] and {k: v} not in cands: cands.append({k: v})
    res = run(cands)
    rows = []
    for i, c in enumerate(cands[1:], 1):
        d, p = both(res, i)
        rows.append({"set": c, "v4": d["v4"], "v5": d["v5"], "pooled": p, "ranked": [summ(res[w][i])["ranked"] for w in WORLDS], "orders": summ(res["v4"][i])["orders"] - summ(res["v4"][0])["orders"]})
    rows.sort(key=lambda r: -r["pooled"][0])
    json.dump({"base": {w: summ(res[w][0]) for w in WORLDS}, "rows": rows}, open(HERE / "scan.json", "w"), indent=0)
    print("base", {w: {k: round(v, 3) for k, v in summ(res[w][0]).items()} for w in WORLDS}, "candidates", len(cands))
    for r in rows[:40]: print(f"{r['pooled'][0]:+7.0f} ± {r['pooled'][1]:4.0f} | v4 {r['v4'][0]:+6.0f} ± {r['v4'][1]:4.0f} | v5 {r['v5'][0]:+6.0f} ± {r['v5'][1]:4.0f} | ranked {r['ranked']} orders {r['orders']:+.0f} | {key(r['set'])}")
elif mode == "search":
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    lam = int(os.environ.get("LAM", 160))
    scan = json.load(open(HERE / "scan.json"))
    # costW is frozen at 1: the sim likes 1.25 (+146) but the server said +31 ± 104 on rd-1..48 (real_cost log)
    FROZEN = set(os.environ.get("FROZEN", "costW").split(","))
    for k in FROZEN: KNOBS.pop(k, None)
    good = [r["set"] for r in scan["rows"] if not (set(r["set"]) & FROZEN) and r["v4"][0] > 0 and r["v5"][0] > 0 and r["pooled"][0] > r["pooled"][1]]
    print("good single moves:", len(good))
    random.seed(int(os.environ.get("SEED", 1)))
    best, log = {}, []
    for rd in range(rounds):
        cands = [dict(best)]
        while len(cands) < lam + 1:
            c = dict(best)
            r = random.random()
            if r < 0.4 and good:  # stack one to three of the scan's good moves
                for mv in random.sample(good, min(len(good), random.choice([1, 1, 2, 3]))): c.update(mv)
            else:  # nudge one to four knobs
                for k in random.sample(list(KNOBS), random.choice([1, 1, 2, 3, 4])):
                    lo, hi, step = KNOBS[k]
                    cur = c.get(k, DEF[k])
                    c[k] = rnd(k, cur + random.gauss(0, 0.12 * (hi - lo))) if hi - lo > step else rnd(k, 1 - cur)
            c = {k: v for k, v in c.items() if v != DEF[k]}
            if c not in cands: cands.append(c)
        res = run(cands)
        top, tp = None, None
        for i in range(1, len(cands)):
            d, p = both(res, i)
            ok = all(d[w][0] > 0 for w in WORLDS) and p[0] > 2 * p[1] and all(summ(res[w][i])["ranked"] >= summ(res[w][0])["ranked"] for w in WORLDS)
            if ok and (tp is None or p[0] > tp[0]): top, tp = i, p
        s = {w: summ(res[w][0]) for w in WORLDS}
        print(f"round {rd}: best so far v4 {s['v4']['margin']:,.0f} ({s['v4']['ranked']}/96) v5 {s['v5']['margin']:,.0f} ({s['v5']['ranked']}/96)" + (f" | accept {tp[0]:+.0f} ± {tp[1]:.0f}: {key(cands[top])}" if top else " | no move"), flush=True)
        if top: best = cands[top]
        log.append({"round": rd, "best": dict(best), "v4": s["v4"], "v5": s["v5"]})
        json.dump({"best": best, "log": log}, open(HERE / f"search{os.environ.get('SEED', 1)}.json", "w"), indent=0)
    print("FINAL", key(best))
elif mode == "hold":
    cands = [{}] + [c for c in json.load(open(sys.argv[2])) if c]
    for name, seeds in (("search weeks", SEARCH), ("HELD OUT", HOLD)):
        res = run(cands, seeds)
        print(name, {w: {k: round(v, 3) for k, v in summ(res[w][0]).items()} for w in WORLDS})
        for i in range(1, len(cands)):
            d, p = both(res, i)
            s4, s5 = summ(res["v4"][i]), summ(res["v5"][i])
            print(f"  {p[0]:+6.0f} ± {p[1]:3.0f} | v4 {d['v4'][0]:+6.0f} ± {d['v4'][1]:3.0f} margin {s4['margin']:,.0f} ranked {s4['ranked']}/{s4['n']} worst {100*s4['worst']:.1f}% | v5 {d['v5'][0]:+6.0f} ± {d['v5'][1]:3.0f} ranked {s5['ranked']}/{s5['n']} worst {100*s5['worst']:.1f}% | orders {s4['orders']:.0f} | {key(cands[i])}")
