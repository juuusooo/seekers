"""Local knob search on the fast sim copy (no server).

    /root/system/venv/bin/python research/sim_calib/search.py NAME ITER [BASE_SET]

(1+4) evolution: each round 4 candidates change 2 to 5 knobs of the current best; a candidate replaces the best
only if its paired gain on the search seeds is over 2 SE. Score per week = margin minus 2,000 per point of on time below 92.5% (the copy runs
about 1 point better on time than the server). Search seeds: m-1..48, h-1..48. Held out: k-1..64 (checked by
`check` mode, never used for choices).
    /root/system/venv/bin/python research/sim_calib/search.py NAME check     plays the best and the base on the held-out seeds
State: runs/lab/search_NAME.json. Rows: runs/sim_cal.jsonl, variants "NAME ...".
"""

import json
import os
import random
import statistics as st
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIMP = open(ROOT / os.environ["SIMFILE"]).read().strip()
NAME = sys.argv[1]
TRAIN = "m-1..48,h-1..48"
HOLD = "k-1..64"
STATE = ROOT / f"runs/lab/csearch_{NAME}.json"
OUT = ROOT / "runs/sim_cal.jsonl"

# knob: (low, high, integer?)  ranges around kit-best defaults
KNOBS = {
    "minBookChance": (0.88, 0.98, 0),
    "hardChance": (0.7, 0.93, 0),
    "hardPrice": (0.0, 0.4, 0),
    "minProfit": (0.0, 0.3, 0),
    "minSlackH": (1.5, 5, 0),
    "capPerDriver": (1.5, 5, 0),
    "dueCapPer": (0.06, 0.16, 0),
    "fullPrice": (0.1, 0.5, 0),
    "markupMin": (1.15, 1.4, 0),
    "markupMax": (1.6, 2.5, 0),
    "capLam": (1, 9, 0),
    "capConst": (0, 3, 0),
    "pairBack": (0, 0.15, 0),
    "outage": (0.1, 0.6, 0),
    "worldN": (100, 800, 1),
    "lateCost": (2, 7, 0),
    "openMin": (0.45, 0.8, 0),
    "openMax": (1.2, 2.0, 0),
    "raiseMax": (0.1, 0.3, 0),
    "steps": (3, 8, 1),
    "rampTop": (1.2, 2.0, 0),
    "rampWindowH": (5, 15, 0),
    "steepOpen": (1.1, 1.6, 0),
    "steepStep": (0.05, 0.25, 0),
    "lateFee": (0.8, 1.6, 0),
    "pairKm": (15, 50, 0),
    "pairSlackH": (3, 9, 0),
    "pairCap": (0.8, 1.0, 0),
    "pairTop": (1.1, 1.6, 0),
    "pairHoldH": (2, 7, 0),
    "pS": (0.05, 0.13, 0),
    "pWeek": (0.02, 0.1, 0),
    "pDay": (0.06, 0.25, 0),
    "dueMon": (-0.1, 0.04, 0),
    "dueFri": (0.0, 0.2, 0),
}


def play(variant, cfg, seeds):
    s = ",".join(f"{k}={v:.5g}" for k, v in cfg.items())
    args = ["bash", "sim/sweep.sh", seeds, variant, "--kit", "kit8", "--algo", "sim/cal/kit8/algo.ts", "--sim", SIMP] + (["--set", s] if s else [])
    subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        env={**__import__("os").environ, "RUN": "cal/run", "P": "30"},
    )
    rows = {}
    for l in open(OUT):
        if variant in l:
            r = json.loads(l)
            if r.get("variant") == variant:
                rows[r["seed"]] = r
    return rows


def score(r):
    # smooth on-time guard: minus 2,000 per point below 92.5% (the copy runs about 1 point better than the server)
    # an unranked week scores nothing (as in the final); smooth guard below 92.5% on top
    return (r["margin"] if r["onTime"] >= 0.9 else 0.0) - 200000 * max(0.0, 0.925 - r["onTime"])


ORDPEN = float(__import__("os").environ.get("ORDPEN", "0"))  # EUR per extra order vs the base, same week


def diff(a, b):
    k = sorted(set(a) & set(b))
    # penalty only for orders above the start config's (never a reward for fewer orders)
    over = lambda r, s: max(0, r[s]["won"] - S0[s]["won"]) if s in S0 else 0
    d = [score(b[s]) - score(a[s]) - ORDPEN * (over(b, s) - over(a, s)) for s in k]
    return st.mean(d), st.stdev(d) / len(d) ** 0.5, sum(x > 0 for x in d), len(d)


def summary(r):
    v = list(r.values())
    return f"mean {st.mean(x['margin'] for x in v):,.0f} score {st.mean(score(x) for x in v):,.0f} ranked91 {sum(x['onTime'] >= 0.91 for x in v)}/{len(v)} worst {min(x['onTime'] for x in v):.3f}"


base = {}
if len(sys.argv) > 3:
    for kv in sys.argv[3].split(","):
        k, v = kv.split("=")
        base[k] = float(v)

if sys.argv[2] == "check":
    S = json.loads(STATE.read_text())
    b = play(f"{NAME} hold base", S["base"], HOLD)
    w = play(f"{NAME} hold best", S["best"], HOLD)
    m, se, nb, n = diff(b, w)
    print("best", json.dumps(S["best"]))
    print(f"held out {HOLD}: base {summary(b)} | best {summary(w)}")
    print(f"held out difference {m:+.0f} ± {se:.0f}, better {nb}/{n}")
    sys.exit()

ITER = int(sys.argv[2])
if STATE.exists():
    S = json.loads(STATE.read_text())
else:
    S = {"base": base, "best": dict(base), "it": 0, "log": []}
    S["bestRows"] = play(f"{NAME} it0", S["best"], TRAIN)
    S["startRows"] = S["bestRows"]
    print("start", summary(S["bestRows"]), flush=True)
rng = random.Random(7 + S["it"])
S0 = S.get("startRows", S["bestRows"])
defaults = json.loads(
    subprocess.run(
        [
            "bun",
            "-e",
            "const a=await import('./sim/cal/kit8/algo.ts');console.log(JSON.stringify(a.PARAMS))",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    or "{}"
)
while S["it"] < ITER:
    S["it"] += 1
    cands = []
    for j in range(4):
        c = dict(S["best"])
        for k in rng.sample(list(KNOBS), rng.randint(2, 5)):
            lo, hi, integer = KNOBS[k]
            cur = c.get(k, defaults.get(k, (lo + hi) / 2))
            v = cur + rng.gauss(0, 0.25) * (hi - lo)
            v = min(hi, max(lo, v))
            c[k] = round(v) if integer else (round(v * 4) / 4 if k.endswith("H") else round(v, 3))  # hours: whole minutes for the server
        rows = play(f"{NAME} it{S['it']}_{j}", c, TRAIN)
        m, se, nb, n = diff(S["bestRows"], rows)
        cands.append((m, se, nb, n, c, rows))
        print(
            f"it {S['it']}.{j} {m:+6.0f} ± {se:3.0f} ({nb}/{n}) {json.dumps({k: v for k, v in c.items() if S['best'].get(k) != v})}",
            flush=True,
        )
    m, se, nb, n, c, rows = max(cands, key=lambda x: x[0] - 2 * x[1])
    if m > 2 * se and m > 50:
        S["best"], S["bestRows"] = c, rows
        print(
            f"  NEW BEST {m:+.0f} ± {se:.0f}: {summary(rows)} {json.dumps(c)}",
            flush=True,
        )
    S["log"].append({"it": S["it"], "m": m, "se": se})
    STATE.write_text(json.dumps(S))
print("END best", json.dumps(S["best"]), summary(S["bestRows"]))
