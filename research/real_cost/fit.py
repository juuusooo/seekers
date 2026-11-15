"""Fits the realized-cost trees on runs/rc/rows.jsonl (build.ts) and writes kit-cost/core/data/cost.json.
Split by seed (same seed = same requests). Reports out-of-seed error against the plan fee alone.
  /root/system/venv/bin/python research/real_cost/fit.py [--write]"""
import json, sys, re
import numpy as np, lightgbm as lgb

KEYS = re.search(r"COST_KEYS = \[(.*?)\] as const", open("kit-cost/core/cost.ts").read(), re.S).group(1)
KEYS = re.findall(r'"(\w+)"', KEYS)
rows = [json.loads(l) for l in open("runs/rc/rows.jsonl") if l.strip()]
X = np.array([r["x"] for r in rows]); y = np.array([r["y"] for r in rows]); paid = np.array([r["paid"] for r in rows])
seed = np.array([r["seed"] for r in rows])
assert X.shape[1] == len(KEYS)
print("rows", len(y), "worlds", len({r["world"] for r in rows}), "seeds", len(set(seed)))
print("cost y: mean %.3f sd %.3f median %.3f p90 %.3f | paid mean %.3f | plan fee mean %.3f | y>2: %.3f" % (y.mean(), y.std(), np.median(y), np.quantile(y, .9), paid.mean(), X[:, KEYS.index("plan_fee")].mean(), (y > 2).mean()))
yc = np.minimum(y, 4.0)  # an undelivered car costs its whole price: cap so a few orders do not steer the fit
num = np.array([int(s.split("-")[1]) for s in seed]); pre = np.array([s.split("-")[0] for s in seed])
test = (num % 4 == 0)  # every fourth seed of every prefix is held out
P = dict(objective="regression", learning_rate=0.04, num_leaves=15, max_depth=5, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5, verbosity=-1, seed=1, num_threads=8)
def fit(Xa, ya, obj="regression", rounds=300, **kw):
    return lgb.train({**P, "objective": obj, **kw}, lgb.Dataset(Xa, ya), rounds)
pf = X[:, [KEYS.index("plan_fee")]]
def r2(pred, t): return 1 - ((t - pred) ** 2).sum() / ((t - t.mean()) ** 2).sum()
tr, te = ~test, test
a, b = np.polyfit(pf[tr, 0], yc[tr], 1)
print("held-out R2: plan fee (linear) %.4f" % r2(a * pf[te, 0] + b, yc[te]))
m1 = fit(pf[tr], yc[tr]); print("held-out R2: plan fee (trees)  %.4f" % r2(m1.predict(pf[te]), yc[te]))
m = fit(X[tr], yc[tr]); pred = m.predict(X[te]); print("held-out R2: all inputs        %.4f" % r2(pred, yc[te]))
noplan = [i for i, k in enumerate(KEYS) if not k.startswith("plan_")]
m0 = fit(X[tr][:, noplan], yc[tr]); print("held-out R2: all but the plan  %.4f" % r2(m0.predict(X[te][:, noplan]), yc[te]))
mp = fit(X[tr], np.minimum(paid[tr], 4)); print("held-out R2 of fees paid only: plan linear %.4f, all inputs %.4f" % (r2(np.polyval(np.polyfit(pf[tr, 0], paid[tr], 1), pf[te, 0]), paid[te]), r2(mp.predict(X[te]), np.minimum(paid[te], 4))))
res = pred - pf[te, 0]
print("predicted cost minus plan fee, held out: mean %.3f sd %.3f, p10 %.3f p90 %.3f" % (res.mean(), res.std(), np.quantile(res, .1), np.quantile(res, .9)))
# calibration by decile of the prediction
q = np.quantile(pred, np.linspace(0, 1, 11)); print("decile: predicted / actual / plan fee")
for i in range(10):
    s = (pred >= q[i]) & (pred <= q[i + 1]); print("  %d  %.3f  %.3f  %.3f  n=%d" % (i, pred[s].mean(), yc[te][s].mean(), pf[te, 0][s].mean(), s.sum()))
imp = sorted(zip(m.feature_importance("gain"), KEYS), reverse=True); tot = sum(g for g, _ in imp)
print("gain share:", ", ".join("%s %.0f%%" % (k, 100 * g / tot) for g, k in imp[:14]))
if "--write" in sys.argv:
    def dump(model):
        d = model.dump_model()
        def node(n):
            if "leaf_value" in n: return {"v": round(n["leaf_value"], 6)}
            assert n["decision_type"] == "<=" and n.get("default_left", True) in (True, False)
            return {"f": n["split_feature"], "t": n["threshold"], "l": node(n["left_child"]), "r": node(n["right_child"])}
        return {"base": 0.0, "trees": [node(t["tree_structure"]) for t in d["tree_info"]]}
    full = fit(X, yc); up = fit(X, yc, obj="quantile", alpha=0.8)
    out = {"keys": KEYS, "rows": len(y), "heads": {"mean": dump(full), "q80": dump(up)}}
    json.dump(out, open("kit-cost/core/data/cost.json", "w"), separators=(",", ":"))
    chk = X[:50]; json.dump({"x": chk.tolist(), "mean": full.predict(chk).tolist(), "q80": up.predict(chk).tolist()}, open("runs/rc/parity.json", "w"))
    print("wrote kit-cost/core/data/cost.json")
