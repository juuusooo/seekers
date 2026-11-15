"""Two checks.

    python research/best13/feat/pairs4.py [A|B]

1. Trust coefficient read without a model: the same request in two worlds with different trust, one win. x = how much
   dearer the high-trust world's markup was, as a share of d ln(1+0.01 trust). The high-trust world should win below
   the true coefficient and lose above it.
2. Same-lane residual correlation ACROSS seeds (a global lane table error) against within one world (a per-world lane level).
"""
import sys
import numpy as np, polars as pl
sys.path.insert(0, "/root/system/z-sideprojects/junction-2026/Bahn-Spread/research/best13/feat")
from fit import OUT, load

sample = sys.argv[1] if len(sys.argv) > 1 else "A"
d0 = load(sample)
d = d0.select("seed", "req", "world", "won", "trust", pl.col("m_min").log().alias("lm"), (pl.col("trust") * 0.01).log1p().alias("lt"))
pr = d.join(d, on=["seed", "req"], suffix="_lo").filter((pl.col("trust") >= pl.col("trust_lo") + 4) & (pl.col("won") != pl.col("won_lo")))
ratio = ((pr["lm"] - pr["lm_lo"]) / (pr["lt"] - pr["lt_lo"])).to_numpy(); y = pr["won"].to_numpy(); th = pr["trust"].to_numpy(); tl = pr["trust_lo"].to_numpy()
edges = np.arange(0.0, 1.61, 0.2)
print(f"1. sample {sample}: pairs with trust apart by 4 or more and one win: {len(y):,}")
print(f"   {'d ln m / d ln trust':34s}" + " ".join(f"{e:4.1f}+" for e in edges[:-1]))
for name, k in (("all", th >= 0), ("high trust <= 10", th <= 10), ("high trust 11-19", (th > 10) & (th < 20)), ("high trust >= 20", th >= 20), ("high >= 20, low <= 8", (th >= 20) & (tl <= 8))):
    cells = [(ratio >= e) & (ratio < e + 0.2) & k for e in edges[:-1]]
    print(f"   {name:22s} hi won: " + " ".join(f"{y[c].mean():5.2f}" if c.sum() >= 40 else "    ." for c in cells) + "   n: " + " ".join(f"{c.sum():d}" for c in cells))

r = pl.read_parquet(f"{OUT}/resid_{sample}.parquet").join(d0.select("world", "req", "p_first", "p_last"), on=["world", "req"])
r = r.filter(pl.col("p").is_between(0.03, 0.97)).with_columns(((pl.col("won") - pl.col("p")) / (pl.col("p") * (1 - pl.col("p"))).sqrt()).alias("z"), (pl.col("seed").hash(3) % 10).alias("fold"))
one = r.join(r.select("seed", "world").unique().group_by("seed").agg(pl.col("world").min()), on=["seed", "world"])  # one world per seed
def cross(df):
    g = df.group_by("p_first", "p_last", "seed").agg(pl.col("z").sum().alias("s"), pl.len().alias("n")).group_by("p_first", "p_last").agg(pl.col("s").sum().alias("S"), (pl.col("s") ** 2).sum().alias("S2"), pl.col("n").sum().alias("N"), (pl.col("n") ** 2).sum().alias("N2"))
    return float(((g["S"] ** 2 - g["S2"]).sum()) / ((g["N"] ** 2 - g["N2"]).sum()))
def within(df):
    g = df.group_by("p_first", "p_last", "seed").agg(pl.col("z").sum().alias("s"), (pl.col("z") ** 2).sum().alias("s2"), pl.len().alias("n"))
    return float((g["s"] ** 2 - g["s2"]).sum() / (g["n"] ** 2 - g["n"]).sum())
cs = np.array([cross(one.filter(pl.col("fold") != k)) for k in range(10)]); ws = np.array([within(one.filter(pl.col("fold") != k)) for k in range(10)])
jk = lambda v: (v.mean(), np.sqrt(9 / 10 * ((v - v.mean()) ** 2).sum()))
print(f"2. same lane, one world per seed (sample {sample}): corr within one world {within(one):.4f} +- {jk(ws)[1]:.4f}; across seeds {cross(one):.4f} +- {jk(cs)[1]:.4f}")
