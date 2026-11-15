"""Optuna search of the backlog curve on the local sim (Rust copy), both worlds.
  <venv python> optcurve.py [rounds=16] [batch=24]
Objective: mean over the two worlds (v4, T) of the gain over BEST10 on the search weeks m-1..48 + h-1..48, on the
smooth score (margin minus 3,000 EUR per point of on time under 93%). Then the best five by the search, the linear
rule and the base are played on the held-out weeks (k, rd, sv): only those numbers are a result."""
import json, os, sys
import optuna
from ab import play, table
from stage import WORLDS, SEARCH, HELD

HERE = os.path.dirname(os.path.abspath(__file__))
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 16
BATCH = int(sys.argv[2]) if len(sys.argv) > 2 else 24
optuna.logging.set_verbosity(optuna.logging.WARNING)

def suggest(t):
    return dict(curve=1, cDown=t.suggest_float("cDown", 0.0, 0.15), cLo=t.suggest_float("cLo", 0.01, 0.07), cSteep=t.suggest_float("cSteep", 1.0, 4.0),
                cDead=t.suggest_float("cDead", 0.0, 0.04), cSpan=t.suggest_float("cSpan", 0.005, 0.08), cPow=t.suggest_float("cPow", 0.5, 4.0), cCap=t.suggest_float("cCap", 0.1, 0.4))
setline = lambda name, p: name + " " + ",".join(f"{k}={v:.5g}" for k, v in p.items())
LINEAR = dict(backK=6, backAt=0.04, backDown=0.08)

def score(lines, seeds, tag):
    """name -> (pooled smooth gain, per-world rows of ab.table)"""
    vfile = os.path.join(HERE, "out", tag + ".txt"); open(vfile, "w").write("\n".join(["base"] + lines) + "\n")
    per = {}
    for wname, sim in WORLDS.items():
        rows = play(seeds, vfile, sim, f"{tag}_{wname}")
        per[wname] = {r["name"]: r for r in table(rows, "base")}
    return {n: (sum(per[w][n]["sdiff"] for w in per) / len(per), {w: per[w][n] for w in per}) for n in per["v4"]}

study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=1, multivariate=True, n_startup_trials=2 * BATCH))
study.enqueue_trial(dict(cDown=0.08, cLo=0.04, cSteep=3.0, cDead=0.0, cSpan=0.05, cPow=1.0, cCap=0.3))   # the linear rule as a curve
done = []
for rnd in range(ROUNDS):
    trials = [study.ask() for _ in range(BATCH)]
    params = [suggest(t) for t in trials]
    res = score([setline(f"t{t.number}", p) for t, p in zip(trials, params)], SEARCH, "opt")
    for t, p in zip(trials, params):
        v = res[f"t{t.number}"][0]; study.tell(t, v); done.append((v, t.number, p))
    best = max(done)
    print(f"round {rnd + 1}/{ROUNDS}: {len(done)} curves, best so far {best[0]:+.0f} (trial {best[1]})", flush=True)

done.sort(reverse=True)
top = done[:5]
print("\nSearch weeks: gain of the linear rule as a curve (trial 0): %+.0f" % next(v for v, n, _ in done if n == 0))
lines = [setline("linear", LINEAR)] + [setline(f"top{i + 1}_t{n}", p) for i, (v, n, p) in enumerate(top)]
# the middle of the ten best curves: less of a lucky pick than the single best
mid = {k: sum(p[k] for _, _, p in done[:10]) / 10 for k in top[0][2]}; mid["curve"] = 1
lines.append(setline("mid_of_top10", mid))
held = score(lines, HELD, "optheld"); srch = score(lines, SEARCH, "optsearch")
print(f"\n{'curve':16} {'search':>7} | {'held out':>8} {'v4 margin':>10} {'±':>4} {'T margin':>9} {'±':>4} {'T ranked':>8} {'T worst':>7}")
for l in lines:
    n = l.split()[0]; h = held[n]; a, b = h[1]["v4"], h[1]["T"]
    print(f"{n:16} {srch[n][0]:+7.0f} | {h[0]:+8.0f} {a['diff']:+10.0f} {a['se']:4.0f} {b['diff']:+9.0f} {b['se']:4.0f} {b['ranked']:8d} {b['worst']:7.1f}")
print("\nSettings:")
for l in lines: print(" ", l)
json.dump({"trials": [(v, n, p) for v, n, p in done], "lines": lines}, open(os.path.join(HERE, "variants", "optcurve.json"), "w"))
