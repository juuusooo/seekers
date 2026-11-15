"""Refits the realized-cost trees on rows dumped by the local sim (simrs --rows) with several recipes and writes one
cost file per recipe (out/cost_<world>_<recipe>.json, the flat format of sim-experimental/static.json).
  <venv python> costfit.py v4|T
Label parts per won order, as multiples of the typical fee: fee (driver fees) and tail (refunds, failed visits, fines,
waiting, undelivered). The shipped recipe (research/real_cost/fit.py) is R0."""
import json, sys, os
import numpy as np, lightgbm as lgb
world = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "out", f"rows_{world}.jsonl"))]
X = np.array([r["x"] for r in rows]); typ = np.array([r["typ"] for r in rows])
fee = np.array([r["fee"] for r in rows]) / typ; tail = np.array([r["tail"] for r in rows]) / typ; late = np.array([r["late"] for r in rows], float)
y = np.minimum(fee + tail, 4.0)
seed = np.array([r["seed"] for r in rows]); test = np.array([int(s.split("-")[1]) % 4 == 0 for s in seed])
P = dict(objective="regression", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
MONO = [0] * X.shape[1]
for k, s in {7: 1, 8: 1, 22: 1, 18: -1, 16: -1, 29: 1, 30: -1}.items(): MONO[k] = s   # load, open_all, due_load up; slack, hours left down; plan fee up, plan chance down
def fit(mask, target, w=None, mono=False, rounds=300, **kw):
    p = {**P, **kw}
    if mono: p["monotone_constraints"] = MONO
    return lgb.train(p, lgb.Dataset(X[mask], target[mask], weight=None if w is None else w[mask]), rounds)
BIG = dict(learning_rate=0.03, num_leaves=31, max_depth=7, min_data_in_leaf=100)
RECIPES = {
    "R0": lambda m: [fit(m, y)],
    "R1w": lambda m: [fit(m, y, w=typ)],
    "R2mono": lambda m: [fit(m, y, mono=True)],
    "R3wmono": lambda m: [fit(m, y, w=typ, mono=True)],
    "R4two": lambda m: [fit(m, fee), fit(m, np.minimum(tail, 4.0))],
    "R5late05": lambda m: [fit(m, fee), fit(m, np.minimum(tail + 0.5 * late, 4.5))],
    "R5late10": lambda m: [fit(m, fee), fit(m, np.minimum(tail + 1.0 * late, 5.0))],
    "R6big": lambda m: [fit(m, y, rounds=600, **BIG)],
    "R7all": lambda m: [fit(m, fee, w=typ, mono=True), fit(m, np.minimum(tail + 0.5 * late, 4.5), w=typ)],
}
def flat(models):
    f, t, l, r, roots = [], [], [], [], []
    def add(n):
        i = len(f); f.append(-1); t.append(0.0); l.append(0); r.append(0)
        if "leaf_value" in n: t[i] = n["leaf_value"]; return i
        assert n["decision_type"] == "<="
        f[i] = n["split_feature"]; t[i] = n["threshold"]; l[i] = add(n["left_child"]); r[i] = add(n["right_child"]); return i
    for m in models:
        for tree in m.dump_model()["tree_info"]: roots.append(add(tree["tree_structure"]))
    return {"base": 0.0, "f": f, "t": t, "l": l, "r": r, "roots": roots}
r2 = lambda pred, t, w=None: 1 - np.average((t - pred) ** 2, weights=w) / np.average((t - np.average(t, weights=w)) ** 2, weights=w)
print(f"{world}: rows {len(y)}, cost mean {y.mean():.3f} sd {y.std():.3f}, fee {fee.mean():.3f}, tail {tail.mean():.3f}, late {late.mean():.3f}; plan fee alone R2 {r2(np.polyval(np.polyfit(X[~test, 29], y[~test], 1), X[test, 29]), y[test]):.3f}")
for name, make in RECIPES.items():
    pred = sum(m.predict(X[test]) for m in make(~test))
    full = flat(make(np.ones(len(y), bool)))
    json.dump({"mean": full, "q80": full}, open(os.path.join(HERE, "out", f"cost_{world}_{name}.json"), "w"), separators=(",", ":"))
    print(f"  {name:10s} held-out R2 of the realized cost {r2(pred, y[test]):.3f}, weighted by typical fee {r2(pred, y[test], typ[test]):.3f}, mean predicted {pred.mean():.3f}, trees {len(full['roots'])}")
