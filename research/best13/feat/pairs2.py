"""Follow-ups to pairs.py.

    python research/best13/feat/pairs2.py [A|B]

1. Is the competitor's price one fixed number per (seed, request)? Pairs of worlds with the same trust.
2. Shape of the trust effect: a free level per trust band, from pairs of worlds on one request.
3. Batch effect against a tighter control: same world, dealer, day AND same pickup and delivery town, not one batch.
"""
import sys
import numpy as np, polars as pl
sys.path.insert(0, "/root/system/z-sideprojects/junction-2026/Bahn-Spread/research/best13/feat")
from fit import OUT, ROOT, load
from pairs import newton

sample = sys.argv[1] if len(sys.argv) > 1 else "A"
d0 = load(sample)
d = d0.select("seed", "req", "world", "fold", "won", "trust", pl.col("m_min").log().alias("lm"))
pr = d.join(d, on=["seed", "req"], suffix="_2").filter((pl.col("world") < pl.col("world_2")) & (pl.col("won") != pl.col("won_2")))
y = pr["won"].to_numpy().astype(float); f = pr["fold"].to_numpy(); dlm = (pr["lm"] - pr["lm_2"]).to_numpy(); t1, t2 = pr["trust"].to_numpy(), pr["trust_2"].to_numpy()
same = t1 == t2
hi = np.where(y == 1, dlm, -dlm)[same]
print(f"1. sample {sample}: pairs with equal trust and one win: {same.sum():,}. Winner has the HIGHER markup in {np.mean(hi > 0):.4f}; by more than 1% {np.mean(hi > 0.01):.4f}, 3% {np.mean(hi > 0.03):.4f}, 10% {np.mean(hi > 0.1):.4f}")
b = newton(dlm[same][:, None], y[same]); print(f"   ln m slope within a request (equal trust): {b[0]:.0f}  -> scale s = {-1 / b[0]:.4f} (cross-request fit: about 0.089)")
allp = d.join(d, on=["seed", "req"], suffix="_2").filter((pl.col("world") < pl.col("world_2")) & (pl.col("trust") == pl.col("trust_2")) & ((pl.col("lm") - pl.col("lm_2")).abs() < 0.002))
print(f"   pairs with equal trust and markup within 0.2%: {allp.shape[0]:,}, same outcome in {float((allp['won'] == allp['won_2']).mean()):.4f}")

BANDS = [0, 1, 3, 6, 10, 15, 20, 25, 26]
def onehot(t): return np.stack([((t >= BANDS[i]) & (t < BANDS[i + 1])).astype(float) for i in range(1, len(BANDS) - 1)], 1)
X = np.column_stack([dlm, onehot(t1) - onehot(t2)])
def shape(k): bb = newton(X[k], y[k]); return bb[1:] / -bb[0]
full = shape(np.ones(len(y), bool)); per = np.array([shape(f == k) for k in range(10)])
print("2. trust effect by band (ln price against trust 0), from pairs of worlds on one request")
print(f"   {'trust':>8s} {'effect':>8s} {'SE':>7s} {'1.00 x':>8s} {'0.85 x':>8s} {'implied coef':>13s}")
for i in range(len(BANDS) - 2):
    lo, hi_ = BANDS[i + 1], BANDS[i + 2] - 1
    tt = np.r_[t1, t2]; mid = float(np.log1p(0.01 * tt[(tt >= lo) & (tt <= hi_)]).mean())
    print(f"   {lo:>3d}-{hi_:<4d} {per[:, i].mean():8.4f} {per[:, i].std(ddof=1) / 10 ** .5:7.4f} {mid:8.4f} {0.85 * mid:8.4f} {per[:, i].mean() / mid:13.3f}")

r = pl.read_parquet(f"{OUT}/resid_{sample}.parquet").join(d0.select("world", "req", "p_first", "p_last", "trust", "m_min"), on=["world", "req"])
r = r.filter(pl.col("p").is_between(0.03, 0.97)).with_columns(((pl.col("won") - pl.col("p")) / (pl.col("p") * (1 - pl.col("p"))).sqrt()).alias("z"), (pl.col("seed").hash(3) % 10).alias("fold"))
j0 = r.join(r, on=["world", "dealer", "day"], suffix="_2").filter(pl.col("req") < pl.col("req_2"))
notb = (pl.col("batch") != pl.col("batch_2")) | (pl.col("batch") == "")
lane = (pl.col("p_first") == pl.col("p_first_2")) & (pl.col("p_last") == pl.col("p_last_2"))
sets = {"same batch": j0.filter(~notb), "same batch, same lane": j0.filter(~notb & lane), "same batch, other lane": j0.filter(~notb & ~lane),
        "not one batch, same lane": j0.filter(notb & lane), "not one batch, same pickup town": j0.filter(notb & (pl.col("p_first") == pl.col("p_first_2"))),
        "not one batch, any": j0.filter(notb)}
vbar = float((r["p"] * (1 - r["p"])).mean()); a = 11.2
print(f"3. residual correlation of request pairs in one world, dealer and day (sample {sample})")
for name, j in sets.items():
    c = j.group_by("fold").agg((pl.col("z") * pl.col("z_2")).mean().alias("c")).sort("fold")["c"].to_numpy()
    m = c.mean(); print(f"   {name:34s} pairs {j.shape[0]:>10,}  corr {m:.4f} +- {c.std(ddof=1) / 10 ** .5:.4f}  both won or both lost {float((j['won'] == j['won_2']).mean()):.3f}  shared SD about {100 * np.sqrt(max(m, 0) / vbar) / a:.1f}% of price")
sb = sets["same batch"]; print("   same batch: share of pairs on the same lane", round(float(sb.select(lane.mean()).item()), 3), " same markup (0.5%)", round(float(((sb["m_min"] / sb["m_min_2"]).log().abs() < 0.005).mean()), 3))
