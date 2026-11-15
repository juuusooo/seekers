"""Does the view state improve the hourly booking forecast? Baseline = the inputs of kit-best's booking model (model.ts)."""
import sys
import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.metrics import log_loss, roc_auc_score

d = pl.read_parquet("runs/gighours/part-*.parquet").filter(pl.col("typ") > 0)
d = d.with_columns(
    (pl.col("fee") / pl.col("typ")).alias("r"),
    ((pl.col("t") % 1440) // 60).alias("hour"), ((pl.col("t") // 1440) % 7).alias("dow"),
    (pl.col("world").hash() % 5).alias("fold"),
)
BASE = ["r", "nearP", "nearD", "nearP80", "nearD80", "drive", "cars", "privP", "privD", "premium", "typ", "hour", "dow", "age", "age0", "left", "wait", "urgent", "roster"]
VIEW = ["v_n", "v_drivers", "v_n_1h", "v_drivers_1h", "v_drivers_today", "v_passed", "v_repeat", "v_since", "v_maxfee_ratio", "v_firstfee_ratio", "v_drivers_exp", "v_passed_exp", "act30", "act80", "fresh30", "fresh80"]
tr, te = d.filter(pl.col("fold") != 0), d.filter(pl.col("fold") == 0)
print("train", tr.shape[0], "test", te.shape[0], "worlds", d["world"].n_unique(), "base rate", round(te["y"].mean(), 4))
P = dict(objective="binary", learning_rate=0.08, num_leaves=127, min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, verbose=-1, num_threads=24)
out = {}
for name, cols in [("base", BASE), ("base+views", BASE + VIEW)]:
    m = lgb.train(P, lgb.Dataset(tr.select(cols).to_numpy(), tr["y"].to_numpy(), feature_name=cols), 400)
    p = m.predict(te.select(cols).to_numpy())
    out[name] = p
    print(f"{name:11s} log loss {log_loss(te['y'].to_numpy(), p):.4f}  AUC {roc_auc_score(te['y'].to_numpy(), p):.4f}")
    if name != "base":
        imp = sorted(zip(m.feature_importance("gain"), cols), reverse=True)[:14]
        print("  top gain:", ", ".join(f"{c} {g/sum(i for i,_ in imp):.2f}" for g, c in imp))
y = te["y"].to_numpy()
print("constant  log loss", round(log_loss(y, np.full(len(y), tr["y"].mean())), 4))
# Where the gain is: by gig age.
age = te["age"].to_numpy()
for lo, hi in [(0, 1), (1, 121), (121, 361), (361, 10**6)]:
    k = (age >= lo) & (age < hi)
    print(f"age {lo}-{hi} min: n {k.sum()}, rate {y[k].mean():.3f}, base {log_loss(y[k], out['base'][k]):.4f}, +views {log_loss(y[k], out['base+views'][k]):.4f}")
