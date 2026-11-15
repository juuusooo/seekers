"""Does the competitor's price depend on request features that the price model does not have?

    python research/best13/feat/fit.py [A|B]

Logit of won = a * ln(m) + bt * ln(1 + 0.01 trust) + bg * g_rest + features + (seed x weekday) levels.
g_rest = the fixed part of kit-best/core/data/price.json without its trust term (as priceParts in algo.ts).
Effect of a feature in log-price units = coefficient / |a|. Errors: 10 folds of seeds, mean and SD / sqrt(10)
(the same seed gives the same requests to every world, so the seed is the unit).
Rows as in research/views/preq.py: no late order yet for the dealer, one markup for all options, m < 3.
"""

import json
import sys
import numpy as np
import polars as pl
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

ROOT = "/root/system/z-sideprojects/junction-2026/Bahn-Spread"
OUT = f"{ROOT}/runs/rc/feat"
P = json.load(open(f"{ROOT}/kit-best/core/data/price.json"))
MAPP = [p["id"] for p in json.load(open(f"{ROOT}/raw/map.json"))["places"]]
TO = np.array(
    [P["places"].index(p) for p in MAPP]
)  # quotes.parquet town index -> price.json town index
ND = len(P["dealer"])


def load(sample):
    w = pl.read_parquet(f"{OUT}/worlds.parquet").filter(pl.col("sample") == sample)
    q = (
        pl.scan_parquet(f"{ROOT}/runs/quotes.parquet")
        .filter(pl.col("world").is_in(w["world"].to_list()))
        .collect()
    )
    d = q.join(pl.read_parquet(f"{OUT}/feat.parquet"), on=["world", "req"], how="inner")
    d = d.filter(
        (pl.col("lates") == 0)
        & (pl.col("m_max") / pl.col("m_min") < 1.005)
        & (pl.col("m_min") < 3)
    )
    a, b = TO[d["p_first"].to_numpy()], TO[d["p_last"].to_numpy()]
    hour = np.clip((d["at"].to_numpy() % 1440) // 60, 7, 18)
    dl = np.minimum(ND - 1, d["dealer"].str.slice(1).cast(pl.Int64).to_numpy())
    g = (
        P["c"]
        + P["b"][1] * d["drive"].to_numpy() / 600
        + P["b"][2] * (d["legs"].to_numpy() - 1)
        + P["b"][3] * (d["n_opt"].to_numpy() - 1)
        + np.array(P["lane"])[a * 30 + b]
        + np.array(P["pick"])[a]
        + np.array(P["del"])[b]
        + np.array(P["hour"])[hour]
        + np.array(P["dealer"])[dl]
    )
    return d.with_columns(
        pl.Series("g_rest", g),
        pl.Series("dl", dl),
        (pl.col("at") // 1440).alias("day"),
        (pl.col("seed").hash(3) % 10).alias("fold"),
    )


FEATS = {  # name -> expression (0/1 or scaled number)
    "premium car": pl.col("premium"),
    "electric car": pl.col("electric"),
    "private pickup address": pl.col("priv_pick"),
    "private delivery address": pl.col("priv_del"),
    "kinds: same_day only": (pl.col("kinds") == "same_day"),
    "kinds: next_day only": (pl.col("kinds") == "next_day"),
    "kinds: next + 3 days": (pl.col("kinds") == "next_day,within_3_days"),
    "kinds: same + next + 3 days": (
        pl.col("kinds") == "next_day,same_day,within_3_days"
    ),
    "deadline of cheapest option, per +24 h": (pl.col("h_dead_cheap") - 60) / 24,
    "pickup opens later (not at once)": (pl.col("h_pick_open") > 0),
    "pickup opens later, per +24 h": pl.col("h_pick_open") / 24,
    "in a batch": (pl.col("bsize") > 0),
    "batch size, per doubling": pl.when(pl.col("bsize") > 0)
    .then((pl.col("bsize") / 2).log(2))
    .otherwise(0),
    "note present": pl.col("note"),
    "typical fee / list, per +0.10": (pl.col("typ_rel") - 0.95) / 0.1,
    "ln(list price), per +1": pl.col("list_cheap").log() - 8.8,
}
BASE = ["ln_m", "ln_trust", "g_rest"]


def design(d, feats, fe_cols):
    X = np.column_stack(
        [
            np.log(d["m_min"].to_numpy()),
            np.log1p(0.01 * d["trust"].to_numpy()),
            d["g_rest"].to_numpy(),
        ]
        + [d.select(e.cast(pl.Float64)).to_series().to_numpy() for e in feats.values()]
    )
    blocks = [sp.csr_matrix(X)]
    for cols in fe_cols:
        k = (
            d.select(pl.struct(cols).rank("dense") - 1)
            .to_series()
            .to_numpy()
            .astype(np.int64)
        )
        blocks.append(
            sp.csr_matrix(
                (np.ones(len(k)), (np.arange(len(k)), k)),
                shape=(len(k), int(k.max()) + 1),
            )
        )
    return sp.hstack(blocks, format="csr"), X.shape[1]


def logit_fit(X, y, nx, ridge=1e-3, iters=30):
    """Newton steps on a sparse design; a small ridge on the level dummies only keeps all-won / all-lost cells finite."""
    pen = np.r_[np.zeros(nx), np.full(X.shape[1] - nx, ridge)]
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
        grad = X.T @ (y - p) - pen * beta
        H = (X.T @ sp.diags(p * (1 - p)) @ X + sp.diags(pen)).tocsc()
        step = spsolve(H, grad)
        beta += step
        if np.abs(step[:nx]).max() < 1e-7:
            break
    return beta, 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))


def effects(d, feats, fe_cols):
    X, nx = design(d, feats, fe_cols)
    beta, p = logit_fit(X, d["won"].to_numpy().astype(float), nx)
    a = abs(beta[0])
    return np.r_[beta[0], beta[1] / a, beta[2] / a, beta[3:nx] / a], p


def folds(d, feats, fe_cols, label):
    full, p = effects(d, feats, fe_cols)
    per = np.array(
        [effects(d.filter(pl.col("fold") == k), feats, fe_cols)[0] for k in range(10)]
    )
    mean, se = per.mean(0), per.std(0, ddof=1) / np.sqrt(10)
    names = [
        "ln(m) coefficient (logit)",
        "trust coefficient (x ln(1+0.01 trust))",
        "g_rest coefficient",
    ] + list(feats)
    print(
        f"\n== {label}: rows {d.shape[0]:,}, worlds {d['world'].n_unique()}, seeds {d['seed'].n_unique()}, won {d['won'].mean():.3f}"
    )
    print(f"{'term':46s} {'share':>6s} {'all':>8s} {'folds':>8s} {'SE':>7s} {'t':>6s}")
    out = {}
    for i, n in enumerate(names):
        share = (
            float(d.select((feats[n].cast(pl.Float64) != 0).mean()).item())
            if n in feats
            else float("nan")
        )
        scale = 1 if i < 3 else 100  # features in percent of price
        print(
            f"{n:46s} {share:6.3f} {full[i] * scale:8.3f} {mean[i] * scale:8.3f} {se[i] * scale:7.3f} {mean[i] / se[i]:6.1f}"
        )
        out[n] = dict(
            share=share, all=full[i] * scale, mean=mean[i] * scale, se=se[i] * scale
        )
    return out, p


if __name__ == "__main__":
    sample = sys.argv[1] if len(sys.argv) > 1 else "A"
    d = load(sample)
    res = {}
    res["main"], p = folds(
        d, FEATS, [["seed", "day"]], f"sample {sample}, seed x weekday levels"
    )
    d.select(
        "world", "seed", "req", "dealer", "day", "at", "batch", "bsize", "won"
    ).with_columns(pl.Series("p", p)).write_parquet(f"{OUT}/resid_{sample}.parquet")
    res["one at a time"] = {}
    print(
        "\n== each feature alone (with ln m, trust, g_rest, seed x weekday), percent of price"
    )
    for n, e in FEATS.items():
        r = effects(d, {n: e}, [["seed", "day"]])[0]
        res["one at a time"][n] = r[3] * 100
        print(f"{n:46s} {r[3] * 100:8.3f}")
    res["dealer"], _ = folds(
        d,
        FEATS,
        [["seed", "day"], ["seed", "dl"]],
        f"sample {sample}, seed x weekday + seed x dealer levels",
    )
    one = d.filter(pl.col("n_opt") == 1)
    res["one option"], _ = folds(
        one,
        {k: v for k, v in FEATS.items() if "+ 3 days" not in k},
        [["seed", "day"]],
        f"sample {sample}, single-option requests only",
    )
    res["no features"], _ = folds(
        d, {}, [["seed", "day"]], f"sample {sample}, no features"
    )
    json.dump(res, open(f"{OUT}/fit_{sample}.json", "w"), indent=1)
