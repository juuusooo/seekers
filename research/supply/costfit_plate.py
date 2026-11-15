"""Adds the head `late` to kit-supply/core/data/cost_alt.json: trees for the chance that a won order ends late (raw
score; the algorithm takes the logistic). Used with the SHIPPED cost trees (knob lateW), so the cost model itself is
not refitted.   <venv python> costfit_plate.py"""
import json, os
import numpy as np, lightgbm as lgb
HERE = os.path.dirname(os.path.abspath(__file__)); KIT = os.path.join(HERE, "..", "..", "kit-supply", "core", "data")
rows = [json.loads(l) for l in open(os.path.join(HERE, "out", "rows_server.jsonl")) if l.strip()]
X = np.array([r["x"] for r in rows]); late = np.array([max(0, r["late"]) for r in rows], float)
seed = np.array([r["seed"] for r in rows]); test = np.array([int(s.rsplit("-", 1)[1]) % 4 == 0 for s in seed])
P = dict(objective="binary", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
m = lgb.train(P, lgb.Dataset(X[~test], late[~test]), 300); p = m.predict(X[test])
order = np.argsort(-p); cum = np.cumsum(late[test][order]) / late[test].sum()
print(f"held out: late {late[test].mean():.3f}, predicted {p.mean():.3f}; the riskiest 5% / 10% / 20% of orders hold {cum[int(.05 * len(p))]:.0%} / {cum[int(.1 * len(p))]:.0%} / {cum[int(.2 * len(p))]:.0%} of the late ones")
for q in (0.5, 0.9, 0.95, 0.99): print(f"  predicted chance at the {int(q * 100)}th percentile: {np.quantile(p, q):.3f}")
full = lgb.train(P, lgb.Dataset(X, late), 300)
def node(n):
    if "leaf_value" in n: return {"v": round(n["leaf_value"], 6)}
    return {"f": n["split_feature"], "t": n["threshold"], "l": node(n["left_child"]), "r": node(n["right_child"])}
head = {"base": 0.0, "trees": [node(t["tree_structure"]) for t in full.dump_model()["tree_info"]]}
# parity: the nested trees must give LightGBM's raw score
def walk(x):
    s = 0.0
    for n in head["trees"]:
        while "v" not in n: n = n["l"] if x[n["f"]] <= n["t"] else n["r"]
        s += n["v"]
    return s
raw = full.predict(X[:200], raw_score=True); print("largest difference to LightGBM's raw score on 200 rows: %.1e" % max(abs(walk(x) - r) for x, r in zip(X[:200], raw)))
alt = json.load(open(os.path.join(KIT, "cost_alt.json"))); alt["heads"]["late"] = head
json.dump(alt, open(os.path.join(KIT, "cost_alt.json"), "w"), separators=(",", ":")); print("heads now:", ", ".join(alt["heads"]))
