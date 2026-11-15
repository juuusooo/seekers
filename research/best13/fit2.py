"""Refit of the realized-cost trees on BEST9+ server weeks (rows: research/best13/build2.ts -> runs/rc/rows2.*.jsonl).
Split by seed (same seed = same requests). Compares on held-out seeds: the old trees (kit-best cost.json), a refit
on the same 38 inputs (cost2.json), a refit with the week-so-far inputs (cost3.json).
  /root/system/venv/bin/python research/best13/fit2.py [--write]"""

import glob
import json
import re
import sys

import lightgbm as lgb
import numpy as np

KEYS = re.search(
    r"COST_KEYS = \[(.*?)\] as const", open("kit-b13/core/cost.ts").read(), re.S
).group(1)
KEYS = re.findall(r'"(\w+)"', KEYS)
N_OLD = 38
X, y, seed, variant = [], [], [], []
for f in sorted(glob.glob("runs/rc/rows2.*.jsonl")):
    for line in open(f):
        if line.strip():
            r = json.loads(line)
            X.append(r["x"])
            y.append(r["y"])
            seed.append(r["seed"])
            variant.append(r["variant"])
X = np.array(X, dtype=np.float32)
y = np.array(y)
seed = np.array(seed)
assert X.shape[1] == len(KEYS), (X.shape, len(KEYS))
print("rows", len(y), "seeds", len(set(seed)), "inputs", len(KEYS))
print(
    "cost y: mean %.3f sd %.3f median %.3f p90 %.3f | plan fee mean %.3f"
    % (
        y.mean(),
        y.std(),
        np.median(y),
        np.quantile(y, 0.9),
        X[:, KEYS.index("plan_fee")].mean(),
    )
)
yc = np.minimum(y, 4.0)
num = np.array([int(s.split("-")[1]) for s in seed])
te = num % 4 == 0
tr = ~te
P = dict(
    objective="regression",
    learning_rate=0.04,
    num_leaves=15,
    max_depth=5,
    min_data_in_leaf=200,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=5,
    verbosity=-1,
    seed=1,
    num_threads=16,
)


def fit(Xa, ya, rounds=300, **kw):
    return lgb.train({**P, **kw}, lgb.Dataset(Xa, ya), rounds)


def r2(pred, t):
    return 1 - ((t - pred) ** 2).sum() / ((t - t.mean()) ** 2).sum()


def old_predict(model, Xa):
    out = np.zeros(len(Xa))

    def walk(node, idx):
        if "v" in node:
            out[idx] += node["v"]
            return
        left = Xa[idx, node["f"]] <= node["t"]
        walk(node["l"], idx[left])
        walk(node["r"], idx[~left])

    for tree in model["trees"]:
        walk(tree, np.arange(len(Xa)))
    return out + model["base"]


old = json.load(open("kit-best/core/data/cost.json"))
p_old = old_predict(old["heads"]["mean"], X[te].astype(np.float64))
print(
    "held-out R2: old trees (BEST9..12)      %.4f   mean pred %.3f actual %.3f"
    % (r2(p_old, yc[te]), p_old.mean(), yc[te].mean())
)
m2 = fit(X[tr][:, :N_OLD], yc[tr])
p2 = m2.predict(X[te][:, :N_OLD])
print("held-out R2: refit, same 38 inputs      %.4f" % r2(p2, yc[te]))
m2b = fit(X[tr][:, :N_OLD], yc[tr], rounds=600, num_leaves=31, max_depth=7)
p2b = m2b.predict(X[te][:, :N_OLD])
print("held-out R2: refit 38, bigger trees     %.4f" % r2(p2b, yc[te]))
m3 = fit(X[tr], yc[tr])
p3 = m3.predict(X[te])
print("held-out R2: refit + week-so-far inputs %.4f" % r2(p3, yc[te]))
m3b = fit(X[tr], yc[tr], rounds=600, num_leaves=31, max_depth=7)
p3b = m3b.predict(X[te])
print("held-out R2: + week-so-far, bigger      %.4f" % r2(p3b, yc[te]))
for name, pred in (("old", p_old), ("refit38", p2), ("refit44", p3)):
    q = np.quantile(pred, np.linspace(0, 1, 11))
    print(
        name,
        "decile predicted / actual:",
        " ".join(
            "%.2f/%.2f"
            % (
                pred[(pred >= q[i]) & (pred <= q[i + 1])].mean(),
                yc[te][(pred >= q[i]) & (pred <= q[i + 1])].mean(),
            )
            for i in range(10)
        ),
    )
imp = sorted(zip(m3.feature_importance("gain"), KEYS), reverse=True)
tot = sum(g for g, _ in imp)
print(
    "gain share (44 inputs):",
    ", ".join("%s %.0f%%" % (k, 100 * g / tot) for g, k in imp[:16]),
)
# by weekday of the quote: where the week-so-far inputs help
wd = X[te][:, KEYS.index("weekday")]
for d in range(5):
    s = wd == d
    print(
        "  weekday %d  n=%6d  R2 old %.3f refit38 %.3f refit44 %.3f"
        % (
            d,
            s.sum(),
            r2(p_old[s], yc[te][s]),
            r2(p2[s], yc[te][s]),
            r2(p3[s], yc[te][s]),
        )
    )

if "--write" in sys.argv:

    def dump(model):
        d = model.dump_model()

        def node(n):
            if "leaf_value" in n:
                return {"v": round(n["leaf_value"], 6)}
            assert n["decision_type"] == "<="
            return {
                "f": n["split_feature"],
                "t": n["threshold"],
                "l": node(n["left_child"]),
                "r": node(n["right_child"]),
            }

        return {
            "base": 0.0,
            "trees": [node(t["tree_structure"]) for t in d["tree_info"]],
        }

    for name, cols in (("cost2", N_OLD), ("cost3", len(KEYS))):
        full = fit(X[:, :cols], yc)
        up = fit(X[:, :cols], yc, objective="quantile", alpha=0.8)
        out = {
            "keys": KEYS[:cols],
            "rows": len(y),
            "heads": {"mean": dump(full), "q80": dump(up)},
        }
        json.dump(
            out, open("kit-b13/core/data/%s.json" % name, "w"), separators=(",", ":")
        )
        chk = X[:50, :cols].astype(float)
        json.dump(
            {"x": chk.tolist(), "mean": full.predict(chk).tolist()},
            open("runs/rc/parity_%s.json" % name, "w"),
        )
        print("wrote kit-b13/core/data/%s.json" % name)
