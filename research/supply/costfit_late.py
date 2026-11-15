"""Adds lateness-charged heads to kit-supply/core/data/cost_alt.json (heads 1-4 stay as they are).
A late order's cost label gets LAM x its typical fee on top: the refund is in the label already; the extra stands for
what the refund does not count (the dealer's trust halved, the week's 90% rule).   <venv python> costfit_late.py"""
import json, os
import numpy as np, lightgbm as lgb
HERE = os.path.dirname(os.path.abspath(__file__)); KIT = os.path.join(HERE, "..", "..", "kit-supply", "core", "data")
rows = [json.loads(l) for l in open(os.path.join(HERE, "out", "rows_server.jsonl")) if l.strip()]
X = np.array([r["x"] for r in rows]); y = np.minimum(np.array([r["y"] for r in rows]), 4.0); late = np.array([max(0, r["late"]) for r in rows], float)
seed = np.array([r["seed"] for r in rows]); test = np.array([int(s.rsplit("-", 1)[1]) % 4 == 0 for s in seed])
P = dict(objective="regression", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
def nested(model):
    def node(n):
        if "leaf_value" in n: return {"v": round(n["leaf_value"], 6)}
        return {"f": n["split_feature"], "t": n["threshold"], "l": node(n["left_child"]), "r": node(n["right_child"])}
    return {"base": 0.0, "trees": [node(t["tree_structure"]) for t in model.dump_model()["tree_info"]]}
alt = json.load(open(os.path.join(KIT, "cost_alt.json")))
print(f"late orders {late.mean():.3%} of {len(y)}; late orders' cost {y[late > 0].mean():.2f} x typical, on time {y[late == 0].mean():.2f}")
pl = lgb.train({**P, "objective": "binary"}, lgb.Dataset(X[~test], late[~test]), 300).predict(X[test])
q = np.quantile(pl, [0.5, 0.9, 0.99]); print(f"chance of late, held out: mean predicted {pl.mean():.3f}, actual {late[test].mean():.3f}; top tenth predicted {pl[pl >= q[1]].mean():.3f} actual {late[test][pl >= q[1]].mean():.3f}; top 1% {pl[pl >= q[2]].mean():.3f} actual {late[test][pl >= q[2]].mean():.3f}")
for k, lam in ((5, 0.5), (6, 1.0), (7, 2.0)):
    t = y + lam * late
    pred = lgb.train(P, lgb.Dataset(X[~test], t[~test]), 300).predict(X[test])
    base = lgb.train(P, lgb.Dataset(X[~test], y[~test]), 300).predict(X[test])
    d = pred - base
    print(f"  costAlt={k}: late order + {lam} x typical; predicted cost rises by {d.mean():.3f} on average, {np.quantile(d, .9):.3f} at the 90th percentile, {np.quantile(d, .99):.3f} at the 99th")
    alt["heads"][f"mean{k}"] = nested(lgb.train(P, lgb.Dataset(X, t), 300))
json.dump(alt, open(os.path.join(KIT, "cost_alt.json"), "w"), separators=(",", ":"))
print("heads now:", ", ".join(alt["heads"]))
