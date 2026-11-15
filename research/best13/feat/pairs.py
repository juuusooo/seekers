"""(a) Trust coefficient from the same request seen by several worlds of one seed (same request, other markup and trust).
(b) Do requests of one batch win or lose together beyond the model?

    python research/best13/feat/pairs.py [A|B]

(a) Pairs of worlds on one (seed, request) where exactly one won: P(first won) = sigmoid(a * d ln m + bt * d ln(1+0.01 trust)).
    Everything fixed per request (lane, dealer, day, features) cancels. Trust coefficient = bt / |a|. Errors: 10 seed folds.
(b) Pearson residuals of the main fit (fit.py): mean product over pairs in one batch, against pairs of the same
    world, dealer and day that are not in one batch.
"""

import sys
import numpy as np
import polars as pl

sys.path.insert(
    0, "/root/system/z-sideprojects/junction-2026/Bahn-Spread/research/best13/feat"
)
from fit import OUT, load


def newton(X, y, iters=40):
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        step = np.linalg.solve(
            (X * (p * (1 - p))[:, None]).T @ X + 1e-9 * np.eye(len(b)), X.T @ (y - p)
        )
        b += step
        if np.abs(step).max() < 1e-8:
            break
    return b


def trust_pairs(d):
    d = d.select(
        "seed",
        "req",
        "world",
        "fold",
        "won",
        pl.col("m_min").log().alias("lm"),
        (pl.col("trust") * 0.01).log1p().alias("lt"),
        "trust",
    )
    pr = d.join(d, on=["seed", "req"], suffix="_2").filter(
        (pl.col("world") < pl.col("world_2")) & (pl.col("won") != pl.col("won_2"))
    )
    X = np.column_stack(
        [(pr["lm"] - pr["lm_2"]).to_numpy(), (pr["lt"] - pr["lt_2"]).to_numpy()]
    )
    y = pr["won"].to_numpy().astype(float)
    f = pr["fold"].to_numpy()
    print(
        f"\n(a) pairs with one win: {len(y):,} on {pr.select(pl.struct('seed', 'req').n_unique()).item():,} requests; SD of d ln m {X[:, 0].std():.3f}, of d ln trust {X[:, 1].std():.3f}"
    )
    for name, keep in (
        ("all pairs", np.ones(len(y), bool)),
        (
            "pairs with |d trust| >= 5",
            np.abs((pr["trust"] - pr["trust_2"]).to_numpy()) >= 5,
        ),
    ):
        b = newton(X[keep], y[keep])
        per = np.array(
            [newton(X[keep & (f == k)], y[keep & (f == k)]) for k in range(10)]
        )
        t = per[:, 1] / -per[:, 0]
        print(
            f"  {name:28s} n {keep.sum():,}: ln m coef {b[0]:.1f} (folds {per[:, 0].mean():.1f} +- {per[:, 0].std(ddof=1) / 10**0.5:.1f}), trust coef {b[1] / -b[0]:.3f} (folds {t.mean():.3f} +- {t.std(ddof=1) / 10**0.5:.3f})"
        )
    # is the competitor's price one fixed number per (seed, request)? Then the winner of such a pair never has the higher net price.
    for tc in (0.85, 1.0):
        net = X[:, 0] - tc * X[:, 1]
        hi = np.where(y == 1, net, -net)  # winner's net ln price minus loser's
        print(
            f"  trust coef {tc}: winner has the higher net price in {np.mean(hi > 0):.3f} of pairs; by gap size:",
            " ".join(f">{g}: {np.mean(hi > g):.4f}" for g in (0.01, 0.03, 0.06, 0.1)),
        )


def batch(sample):
    r = pl.read_parquet(f"{OUT}/resid_{sample}.parquet").with_columns(
        (
            (pl.col("won") - pl.col("p")) / (pl.col("p") * (1 - pl.col("p"))).sqrt()
        ).alias("z"),
        (pl.col("p") * (1 - pl.col("p"))).alias("v"),
    )
    r = r.filter(pl.col("p").is_between(0.03, 0.97)).with_columns(
        (pl.col("seed").hash(3) % 10).alias("fold")
    )

    def pairs(keys, cond):
        j = r.join(r, on=keys, suffix="_2").filter(
            (pl.col("req") < pl.col("req_2")) & cond
        )
        g = (
            j.group_by("fold")
            .agg((pl.col("z") * pl.col("z_2")).mean().alias("c"), pl.len())
            .sort("fold")
        )
        return (
            float((j["z"] * j["z_2"]).mean()),
            g["c"].to_numpy(),
            j.shape[0],
            float((j["at"] - j["at_2"]).abs().mean()),
        )

    inb = r.filter(pl.col("batch") != "")
    print(
        f"\n(b) residual correlation of pairs, sample {sample} (mean p(1-p) {r['v'].mean():.3f})"
    )
    rows = {}
    j0 = r.join(r, on=["world", "dealer", "day"], suffix="_2").filter(
        pl.col("req") < pl.col("req_2")
    )
    sets = {
        "same batch": j0.filter(
            (pl.col("batch") != "") & (pl.col("batch") == pl.col("batch_2"))
        ),
        "same world, dealer, day, other batch or none": j0.filter(
            (pl.col("batch") != pl.col("batch_2")) | (pl.col("batch") == "")
        ),
        "same, and within 30 min": j0.filter(
            ((pl.col("batch") != pl.col("batch_2")) | (pl.col("batch") == ""))
            & ((pl.col("at") - pl.col("at_2")).abs() <= 30)
        ),
    }
    for name, j in sets.items():
        c = (
            j.group_by("fold")
            .agg((pl.col("z") * pl.col("z_2")).mean().alias("c"))
            .sort("fold")["c"]
            .to_numpy()
        )
        rows[name] = c
        print(
            f"  {name:46s} pairs {j.shape[0]:>10,}  corr {float((j['z'] * j['z_2']).mean()):.4f}  folds {c.mean():.4f} +- {c.std(ddof=1) / 10**0.5:.4f}  mean gap {float((j['at'] - j['at_2']).abs().mean()):.0f} min"
        )
    for ctl in list(rows)[1:]:
        diff = rows["same batch"] - rows[ctl]
        print(
            f"  same batch minus [{ctl}]: {diff.mean():.4f} +- {diff.std(ddof=1) / 10**0.5:.4f}"
        )
    sb = sets["same batch"]
    gap = (sb["at"] - sb["at_2"]).abs()
    print("  same-batch pairs (all same dealer by construction): same arrival minute", float((gap == 0).mean()), " over 15 min apart", float((gap > 15).mean()))


if __name__ == "__main__":
    sample = sys.argv[1] if len(sys.argv) > 1 else "A"
    trust_pairs(load(sample))
    batch(sample)
