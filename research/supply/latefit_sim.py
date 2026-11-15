"""Sim copy of the lateness charge: fits P(late) on the sim's own rows (out/rows_<world>.jsonl) and writes a cost file
whose first head is the SHIPPED mean trees and whose second head is the lateness trees (knob lateW of the Rust copy).
  <venv python> latefit_sim.py v4|T"""
import json, os, sys
import numpy as np, lightgbm as lgb
world = sys.argv[1]; HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "out", f"rows_{world}.jsonl"))]
X = np.array([r["x"] for r in rows]); late = np.array([r["late"] for r in rows], float)
seed = np.array([r["seed"] for r in rows]); test = np.array([int(s.split("-")[1]) % 4 == 0 for s in seed])
P = dict(objective="binary", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
p = lgb.train(P, lgb.Dataset(X[~test], late[~test]), 300).predict(X[test]); order = np.argsort(-p); cum = np.cumsum(late[test][order]) / late[test].sum()
print(f"{world}: late {late.mean():.3f}; the riskiest 5% / 10% / 20% of held-out orders hold {cum[int(.05 * len(p))]:.0%} / {cum[int(.1 * len(p))]:.0%} / {cum[int(.2 * len(p))]:.0%} of the late ones")
m = lgb.train(P, lgb.Dataset(X, late), 300)
f, t, l, r, roots = [], [], [], [], []
def add(n):
    i = len(f); f.append(-1); t.append(0.0); l.append(0); r.append(0)
    if "leaf_value" in n: t[i] = n["leaf_value"]; return i
    f[i] = n["split_feature"]; t[i] = n["threshold"]; l[i] = add(n["left_child"]); r[i] = add(n["right_child"]); return i
for tree in m.dump_model()["tree_info"]: roots.append(add(tree["tree_structure"]))
shipped = json.load(open(os.path.join(HERE, "..", "..", "sim-experimental", "static.json")))["cost"]["mean"]
json.dump({"mean": shipped, "q80": {"base": 0.0, "f": f, "t": t, "l": l, "r": r, "roots": roots}}, open(os.path.join(HERE, "out", f"late_{world}.json"), "w"), separators=(",", ":"))
