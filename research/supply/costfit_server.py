"""Refits the realized-cost trees on rows of our own server weeks (rows.ts -> out/rows_server.jsonl) and writes the
refits next to the shipped trees: kit-supply/core/data/cost_alt.json, heads mean1, mean2, ... (knob costAlt).
  <venv python> costfit_server.py [--write]
Held out: every fourth seed. Also scores the shipped trees (kit-supply/core/data/cost.json) on the same held-out rows."""
import json, os, sys
import numpy as np, lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(HERE, "..", "..", "kit-supply", "core", "data")
rows = [json.loads(l) for l in open(os.path.join(HERE, "out", "rows_server.jsonl")) if l.strip()]
X = np.array([r["x"] for r in rows]); typ = np.array([r["typ"] for r in rows], float)
y = np.minimum(np.array([r["y"] for r in rows]), 4.0)   # the shipped recipe's cap
seed = np.array([r["seed"] for r in rows])
test = np.array([int(s.rsplit("-", 1)[1]) % 4 == 0 for s in seed])
P = dict(objective="regression", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
MONO = [0] * X.shape[1]
for k, s in {7: 1, 8: 1, 22: 1, 18: -1, 16: -1, 29: 1, 30: -1}.items(): MONO[k] = s
BIG = dict(learning_rate=0.03, num_leaves=31, max_depth=7, min_data_in_leaf=100)
def fit(mask, w=None, mono=False, rounds=300, **kw):
    p = {**P, **kw}
    if mono: p["monotone_constraints"] = MONO
    return lgb.train(p, lgb.Dataset(X[mask], y[mask], weight=None if w is None else w[mask]), rounds)
RECIPES = [  # head number, name, maker
    (1, "R0 shipped recipe, refitted", lambda m: fit(m)),
    (2, "R3 weights + monotone", lambda m: fit(m, w=typ, mono=True)),
    (3, "R6 bigger trees", lambda m: fit(m, rounds=600, **BIG)),
    (4, "R8 bigger + weights + monotone", lambda m: fit(m, w=typ, mono=True, rounds=600, **BIG)),
]
def nested(model):
    def node(n):
        if "leaf_value" in n: return {"v": round(n["leaf_value"], 6)}
        assert n["decision_type"] == "<="
        return {"f": n["split_feature"], "t": n["threshold"], "l": node(n["left_child"]), "r": node(n["right_child"])}
    return {"base": 0.0, "trees": [node(t["tree_structure"]) for t in model.dump_model()["tree_info"]]}
def walk(head, Xs):
    out = np.full(len(Xs), head["base"], float)
    for i, x in enumerate(Xs):
        s = 0.0
        for n in head["trees"]:
            while "v" not in n: n = n["l"] if x[n["f"]] <= n["t"] else n["r"]
            s += n["v"]
        out[i] += s
    return out
r2 = lambda pred, t, w=None: 1 - np.average((t - pred) ** 2, weights=w) / np.average((t - np.average(t, weights=w)) ** 2, weights=w)
def decile(pred, t):
    q = np.quantile(pred, np.linspace(0, 1, 11)); return " ".join(f"{pred[(pred >= q[i]) & (pred <= q[i + 1])].mean():.2f}/{t[(pred >= q[i]) & (pred <= q[i + 1])].mean():.2f}" for i in (0, 4, 9))
print(f"rows {len(y)}, worlds {len({r['world'] for r in rows})}, seeds {len(set(seed))}; cost mean {y.mean():.3f} sd {y.std():.3f}; held out {test.sum()} rows")
plan = np.polyval(np.polyfit(X[~test, 29], y[~test], 1), X[test, 29])
print(f"  {'plan fee alone':34s} R2 {r2(plan, y[test]):.3f}")
shipped = json.load(open(os.path.join(KIT, "cost.json")))["heads"]["mean"]
ps = walk(shipped, X[test])
print(f"  {'shipped trees (BEST6-8 weeks)':34s} R2 {r2(ps, y[test]):.3f}, weighted by typical fee {r2(ps, y[test], typ[test]):.3f}, mean predicted {ps.mean():.3f} vs actual {y[test].mean():.3f}; lowest / middle / top tenth predicted/actual {decile(ps, y[test])}")
heads = {}
for k, name, make in RECIPES:
    pred = make(~test).predict(X[test])
    print(f"  {name:34s} R2 {r2(pred, y[test]):.3f}, weighted by typical fee {r2(pred, y[test], typ[test]):.3f}, mean predicted {pred.mean():.3f}; lowest / middle / top tenth {decile(pred, y[test])}")
    if "--write" in sys.argv: heads[f"mean{k}"] = nested(make(np.ones(len(y), bool)))
if heads:
    json.dump({"rows": len(y), "heads": heads}, open(os.path.join(KIT, "cost_alt.json"), "w"), separators=(",", ":"))
    print("wrote kit-supply/core/data/cost_alt.json:", ", ".join(f"costAlt={k} = {name}" for k, name, _ in RECIPES))
