"""Knob search from BEST8 on TWO local worlds at once (no server): v4 (right on fees, wrong on load) and v5c (right on
load, weaker on fees). A candidate is accepted only if it gains on both.

    /root/system/venv/bin/python research/sim_calib/search2.py NAME ITER [BASE_SET]
    /root/system/venv/bin/python research/sim_calib/search2.py NAME check        held-out k-1..64
(1+4) evolution, 2 to 5 knobs a candidate. Score per week = margin if on time >= 90% else 0, minus 2,000 per point under
92.5%. Accept: mean of the two worlds' paired gains over 2 SE and over 50, and a gain over 0.5 SE in each world.
Search seeds m-1..48, h-1..48. State: runs/lab/csearch_NAME.json. Rows: runs/sim_cal.jsonl, variants "NAME ...".
"""
import json, os, random, statistics as st, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = sys.argv[1]
TRAIN, HOLD = "m-1..48,h-1..48", "k-1..64"
STATE = ROOT / f"runs/lab/csearch_{NAME}.json"
OUT = ROOT / "runs/sim_cal.jsonl"
WORLDS = {"v4": "", "v5": open(ROOT / "runs/lab/v5c.sim").read().strip()}
KNOBS = {  # knob: (low, high, integer)
    "minBookChance": (0.88, 0.98, 0), "hardChance": (0.7, 0.93, 0), "hardPrice": (0.0, 0.4, 0), "minProfit": (0.0, 0.3, 0),
    "minSlackH": (1.5, 5, 0), "capPerDriver": (1.5, 5, 0), "dueCapPer": (0.06, 0.16, 0), "fullPrice": (0.1, 0.5, 0),
    "markupMin": (1.15, 1.4, 0), "markupMax": (1.6, 2.5, 0), "capLam": (1, 9, 0), "capConst": (0, 3, 0), "pairBack": (0, 0.15, 0),
    "outage": (0.1, 0.6, 0), "worldN": (100, 800, 1), "lateCost": (2, 7, 0), "openMin": (0.55, 0.85, 0), "openMax": (1.2, 2.0, 0),
    "raiseMax": (0.1, 0.3, 0), "steps": (3, 8, 1), "rampTop": (1.2, 2.0, 0), "rampWindowH": (5, 15, 0), "steepOpen": (1.1, 1.6, 0),
    "steepStep": (0.05, 0.25, 0), "lateFee": (0.7, 1.4, 0), "pairKm": (15, 50, 0), "pairSlackH": (3, 9, 0), "pairCap": (0.8, 1.0, 0),
    "pairTop": (1.1, 1.6, 0), "pairHoldH": (2, 7, 0), "pS": (0.06, 0.13, 0), "pWeek": (0.02, 0.1, 0), "pDay": (0.06, 0.25, 0),
    "dueMon": (-0.1, 0.04, 0), "dueFri": (0.0, 0.2, 0),
}


def play(variant, cfg, seeds):
    s = ",".join(f"{k}={v:.5g}" for k, v in cfg.items())
    for w, simp in WORLDS.items():
        args = ["bash", "sim/sweep.sh", seeds, f"{variant} {w}", "--kit", "kit8", "--algo", "sim/cal/kit8/algo.ts"] + (["--sim", simp] if simp else []) + (["--set", s] if s else [])
        subprocess.run(args, cwd=ROOT, capture_output=True, env={**os.environ, "RUN": "cal/run", "P": "30"})
    rows = {w: {} for w in WORLDS}
    for l in open(OUT):
        if f'"{variant} ' in l:
            r = json.loads(l)
            w = r["variant"].rsplit(" ", 1)[1]
            if r["variant"] == f"{variant} {w}": rows[w][r["seed"]] = {k: r[k] for k in ("margin", "onTime", "won")}
    return rows


SMOOTH = os.environ.get("SMOOTH") == "1"  # 1 = no cliff at 90% (less noise): margin minus 3,000 per point under 93%
def score(r): return r["margin"] - 300000 * max(0.0, 0.93 - r["onTime"]) if SMOOTH else (r["margin"] if r["onTime"] >= 0.9 else 0.0) - 200000 * max(0.0, 0.925 - r["onTime"])


def diff(a, b):
    """paired gain of b over a: pooled (mean of the two worlds per week) and per world"""
    out = {}
    k = sorted(set.intersection(*[set(a[w]) & set(b[w]) for w in WORLDS]))
    per = {w: [score(b[w][s]) - score(a[w][s]) for s in k] for w in WORLDS}
    pooled = [st.mean(per[w][i] for w in WORLDS) for i in range(len(k))]
    se = lambda d: st.stdev(d) / len(d) ** 0.5
    return st.mean(pooled), se(pooled), {w: (st.mean(per[w]), se(per[w])) for w in WORLDS}, len(k)


def summary(rows):
    return " | ".join(f"{w}: margin {st.mean(x['margin'] for x in r.values()):,.0f} score {st.mean(score(x) for x in r.values()):,.0f} orders {st.mean(x['won'] for x in r.values()):.0f} ranked {sum(x['onTime'] >= 0.9 for x in r.values())}/{len(r)} worst {min(x['onTime'] for x in r.values()):.3f}" for w, r in rows.items())


def fmt(m, se, per): return f"{m:+6.0f} ± {se:3.0f} [" + ", ".join(f"{w} {per[w][0]:+.0f} ± {per[w][1]:.0f}" for w in per) + "]"


base = {}
if len(sys.argv) > 3:
    for kv in sys.argv[3].split(","):
        k, v = kv.split("="); base[k] = float(v)
if sys.argv[2] == "check":
    S = json.loads(STATE.read_text())
    b, w = play(f"{NAME} hold base", S["base"], HOLD), play(f"{NAME} hold best", S["best"], HOLD)
    m, se, per, n = diff(b, w)
    print("best", ",".join(f"{k}={v}" for k, v in S["best"].items()))
    print("held out base:", summary(b)); print("held out best:", summary(w))
    print(f"held out {HOLD} n={n}: {fmt(m, se, per)}")
    sys.exit()
ITER = int(sys.argv[2])
if STATE.exists(): S = json.loads(STATE.read_text())
else:
    S = {"base": base, "best": dict(base), "it": 0, "log": []}
    S["bestRows"] = play(f"{NAME} it0", S["best"], TRAIN)
    print("start", summary(S["bestRows"]), flush=True)
rng = random.Random(7 + S["it"])
defaults = json.loads(subprocess.run(["bun", "-e", "const a=await import('./sim/cal/kit8/algo.ts');console.log(JSON.stringify(a.PARAMS))"], cwd=ROOT, capture_output=True, text=True).stdout or "{}")
while S["it"] < ITER:
    S["it"] += 1
    cands = []
    for j in range(4):
        c = dict(S["best"])
        for k in rng.sample(list(KNOBS), rng.randint(2, 5)):
            lo, hi, integer = KNOBS[k]
            cur = c.get(k, defaults.get(k, (lo + hi) / 2))
            v = min(hi, max(lo, cur + rng.gauss(0, 0.2) * (hi - lo)))
            c[k] = round(v) if integer else (round(v * 4) / 4 if k.endswith("H") else round(v, 3))  # hours: whole minutes for the server
        rows = play(f"{NAME} it{S['it']}_{j}", c, TRAIN)
        m, se, per, n = diff(S["bestRows"], rows)
        ok = m > 2 * se and m > 50 and all(per[w][0] > 0.5 * per[w][1] for w in per)
        cands.append((m - 2 * se if ok else -1e9, m, se, per, c, rows, ok))
        print(f"it {S['it']}.{j} {'OK ' if ok else '   '}{fmt(m, se, per)} {json.dumps({k: v for k, v in c.items() if S['best'].get(k) != v})}", flush=True)
    _, m, se, per, c, rows, ok = max(cands, key=lambda x: x[0])
    if ok:
        S["best"], S["bestRows"] = c, rows
        print(f"  NEW BEST {fmt(m, se, per)}: {summary(rows)}\n  {json.dumps(c)}", flush=True)
    S["log"].append({"it": S["it"], "m": m, "se": se, "ok": ok})
    STATE.write_text(json.dumps(S))
print("END best", ",".join(f"{k}={v}" for k, v in S["best"].items())); print(summary(S["bestRows"]))
