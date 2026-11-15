"""More follow-ups.

    python research/best13/feat/pairs3.py [A|B]

1. Trust effect read directly: the same request in a world with trust 0-1 and in a world with trust >= 20. Share of
   pairs (one win) where the high-trust world won, by how much dearer its markup was. The 50% point is the effect.
2. Is there a ceiling on the markup a dealer accepts, whatever the trust?
3. Residual correlation of pairs on the same lane in one world: same or other dealer, same or other day.
"""
import sys
import numpy as np, polars as pl
sys.path.insert(0, "/root/system/z-sideprojects/junction-2026/Bahn-Spread/research/best13/feat")
from fit import OUT, load

sample = sys.argv[1] if len(sys.argv) > 1 else "A"
d0 = load(sample)
d = d0.select("seed", "req", "world", "won", "trust", pl.col("m_min").log().alias("lm"))
for lo, hi, name in ((0, 1, "trust >= 20 against trust 0-1"), (0, 1, "trust 8-12 against trust 0-1")):
    a, b = (20, 25) if ">= 20" in name else (8, 12)
    pr = d.filter(pl.col("trust").is_between(a, b)).join(d.filter(pl.col("trust") <= hi), on=["seed", "req"], suffix="_lo").filter(pl.col("won") != pl.col("won_lo"))
    x = (pr["lm"] - pr["lm_lo"]).to_numpy(); y = pr["won"].to_numpy()
    ref = float(np.log1p(0.01 * pr["trust"].to_numpy()).mean() - np.log1p(0.01 * pr["trust_lo"].to_numpy()).mean())
    print(f"1. sample {sample}, {name}: {len(y):,} pairs on {pr['seed'].n_unique()} seeds; 1.00 x ln(1+0.01 t) = {ref:.3f}, 0.85 x = {0.85 * ref:.3f}")
    edges = np.arange(-0.02, 0.32, 0.02)
    print("   high-trust markup dearer by (ln):  " + " ".join(f"{e:5.2f}" for e in edges[:-1]))
    print("   share where the high-trust world won: " + " ".join(f"{y[(x >= e) & (x < e + 0.02)].mean():5.2f}" if ((x >= e) & (x < e + 0.02)).sum() > 30 else "    ." for e in edges[:-1]))
    print("   pairs:                              " + " ".join(f"{((x >= e) & (x < e + 0.02)).sum():5d}" for e in edges[:-1]))

w = d0.filter(pl.col("won") == 1)
print("2. markup of won quotes, upper tail, by trust:")
for lo, hi in ((0, 0), (1, 9), (10, 19), (20, 25)):
    s = w.filter(pl.col("trust").is_between(lo, hi))["m_min"]
    print(f"   trust {lo:>2d}-{hi:<2d} won {len(s):>8,}  q90 {s.quantile(0.9):.3f} q99 {s.quantile(0.99):.3f} q99.9 {s.quantile(0.999):.3f} max {s.max():.3f}")
q = d0.with_columns((pl.col("m_min") / (1 + 0.01 * pl.col("trust"))).alias("net"))
print("   win share by markup band (all trust):", " ".join(f"{lo:.1f}+: {q.filter(pl.col('m_min').is_between(lo, lo + 0.1, closed='left'))['won'].mean():.3f}" for lo in (1.3, 1.5, 1.7, 1.9, 2.1, 2.3)))

r = pl.read_parquet(f"{OUT}/resid_{sample}.parquet").join(d0.select("world", "req", "p_first", "p_last", "premium", "kinds"), on=["world", "req"])
r = r.filter(pl.col("p").is_between(0.03, 0.97)).with_columns(((pl.col("won") - pl.col("p")) / (pl.col("p") * (1 - pl.col("p"))).sqrt()).alias("z"), (pl.col("seed").hash(3) % 10).alias("fold"))
vbar = float((r["p"] * (1 - r["p"])).mean())
j0 = r.join(r, on=["world", "p_first", "p_last"], suffix="_2").filter(pl.col("req") < pl.col("req_2"))
sd, sy = pl.col("dealer") == pl.col("dealer_2"), pl.col("day") == pl.col("day_2")
print(f"3. residual correlation of pairs on the same lane in one world (sample {sample})")
for name, c_ in (("same dealer, same day", sd & sy), ("same dealer, other day", sd & ~sy), ("other dealer, same day", ~sd & sy), ("other dealer, other day", ~sd & ~sy)):
    j = j0.filter(c_); c = j.group_by("fold").agg((pl.col("z") * pl.col("z_2")).mean().alias("c")).sort("fold")["c"].to_numpy(); m = c.mean()
    print(f"   {name:26s} pairs {j.shape[0]:>10,}  corr {m:.4f} +- {c.std(ddof=1) / 10 ** .5:.4f}  shared SD about {100 * np.sqrt(max(m, 0) / vbar) / 11.2:.1f}% of price")
j = r.join(r, on=["world", "p_first"], suffix="_2").filter((pl.col("req") < pl.col("req_2")) & (pl.col("p_last") != pl.col("p_last_2")))
for name, c_ in (("same pickup town, other lane, same day", sy), ("same pickup town, other lane, other day", ~sy)):
    jj = j.filter(c_); c = jj.group_by("fold").agg((pl.col("z") * pl.col("z_2")).mean().alias("c")).sort("fold")["c"].to_numpy()
    print(f"   {name:40s} pairs {jj.shape[0]:>10,}  corr {c.mean():.4f} +- {c.std(ddof=1) / 10 ** .5:.4f}")
print("   share of requests whose lane was asked before in the same world:", round(float(r.sort("world", "at").with_columns(pl.int_range(pl.len()).over("world", "p_first", "p_last").alias("k")).select((pl.col("k") > 0).mean()).item()), 3))
