"""How much of the competitor's price (the win threshold, x list) is each part? P(win) = sigmoid((ln threshold - ln price) / s),
ln threshold = sum of effects. Nested models, held-out log loss and the fitted sharpness s. Rows: runs/quotes.parquet."""
import sys
import numpy as np, polars as pl, torch
torch.manual_seed(0); torch.set_num_threads(24)
d = pl.read_parquet("runs/quotes.parquet").filter((pl.col("lates") == 0) & (pl.col("m_max") / pl.col("m_min") < 1.005) & (pl.col("m_min") < 3))
if len(sys.argv) > 1: d = d.filter(pl.col("kit").is_in(sys.argv[1].split(",")))
d = d.with_columns((pl.col("at") // 1440).alias("day"), ((pl.col("at") % 1440) // 60).alias("hour"), (pl.col("p_first") * 30 + pl.col("p_last")).alias("lane"))
def code(*cols):
    return torch.tensor(d.select(pl.struct(cols).rank("dense") - 1).to_series().to_numpy().astype(np.int64))
ids = {"seed": code("seed"), "lane": code("lane"), "seed_day": code("seed", "day"), "seed_dealer": code("seed", "dealer"), "seed_pick": code("seed", "p_first"), "seed_del": code("seed", "p_last"),
       "seed_lane": code("seed", "lane"), "seed_dealer_day": code("seed", "dealer", "day"), "seed_pick_day": code("seed", "p_first", "day"), "seed_req": code("seed", "req"), "dealer": code("dealer"), "hour": code("hour")}
lm = torch.tensor(d["m_min"].log().to_numpy(), dtype=torch.float32); y = torch.tensor(d["won"].to_numpy(), dtype=torch.float32)
X = torch.tensor(np.stack([np.log1p(0.01 * d["trust"].to_numpy()), d["drive"].to_numpy() / 600, d["legs"].to_numpy() - 1, d["n_opt"].to_numpy() - 1], 1), dtype=torch.float32)
n = len(y); test = torch.rand(n) < 0.2; tr = ~test
print("rows", n, "worlds", d["world"].n_unique(), "seeds", d["seed"].n_unique(), "won", round(float(y.mean()), 3), "mean price", round(float(lm.exp().mean()), 3))
def fit(names, wd=2.0, epochs=300):
    emb = {k: torch.zeros(int(ids[k].max()) + 1, requires_grad=True) for k in names}
    b = torch.zeros(4, requires_grad=True); c = torch.tensor(0.35, requires_grad=True); ls = torch.tensor(-2.5, requires_grad=True)
    opt = torch.optim.Adam([*emb.values(), b, c, ls], lr=0.02)
    def z(mask):
        th = c + X[mask] @ b
        for k in names: th = th + emb[k][ids[k][mask]]
        return (th - lm[mask]) / ls.exp()
    for _ in range(epochs):
        opt.zero_grad()
        loss = torch.nn.functional.binary_cross_entropy_with_logits(z(tr), y[tr]) + wd * sum((e ** 2).sum() for k, e in emb.items() if k != "seed") / tr.sum()
        loss.backward(); opt.step()
    with torch.no_grad():
        ll = float(torch.nn.functional.binary_cross_entropy_with_logits(z(test), y[test]))
        sd = {k: round(float(e.std()), 3) for k, e in emb.items()}
    return ll, float(ls.exp()), float(b[0]), sd
for names in [["seed"], ["seed", "lane"], ["seed", "lane", "seed_day"], ["seed", "lane", "seed_day", "seed_dealer"], ["seed", "lane", "seed_day", "seed_dealer", "seed_pick", "seed_del"],
              ["seed", "lane", "seed_day", "seed_dealer", "seed_pick", "seed_del", "seed_lane"], ["seed", "lane", "seed_day", "seed_dealer", "seed_pick", "seed_del", "seed_lane", "seed_dealer_day", "seed_pick_day"],
              ["seed", "lane", "seed_day", "seed_dealer", "seed_pick", "seed_del", "seed_lane", "seed_dealer_day", "seed_pick_day", "seed_req"]]:
    ll, s, bt, sd = fit(names)
    print(f"+{names[-1]:16s} held-out log loss {ll:.4f}  sharpness s {s:.4f} (win odds x{np.exp(-0.01/s):.2f} per +1% price)  trust coef {bt:.2f}  SD of parts {sd}")
