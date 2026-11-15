"""Can the competitor's price be learned live, inside one week? Global parts (lane table etc.) fitted on training seeds;
then each held-out world is replayed in time order with an online filter (week, day, dealer, pickup town, delivery
town) that sees only that world's own answers. One-step-ahead log loss vs a week-level-only filter (what kit-best does)."""
import sys
import numpy as np, polars as pl, torch
torch.manual_seed(0); torch.set_num_threads(24)
d = pl.read_parquet("runs/quotes.parquet").filter((pl.col("lates") == 0) & (pl.col("m_max") / pl.col("m_min") < 1.005) & (pl.col("m_min") < 3) & (pl.col("kit") != "kit-price") & ~pl.col("seed").str.contains("^p[w-z]-"))
d = d.with_columns((pl.col("at") // 1440).alias("day"), ((pl.col("at") % 1440) // 60).clip(7, 18).alias("hour"), (pl.col("p_first") * 30 + pl.col("p_last")).alias("lane"),
                   pl.col("dealer").str.slice(1).cast(pl.Int64).alias("dl"), (pl.col("seed").hash() % 5 == 0).alias("test"))
nD = int(d["dl"].max()) + 1
print("rows", d.shape[0], "dealers", d["dl"].n_unique(), "test seeds", d.filter("test")["seed"].n_unique(), "of", d["seed"].n_unique())
tr = d.filter(~pl.col("test"))
def code(df, *cols): return torch.tensor(df.select(pl.struct(cols).rank("dense") - 1).to_series().to_numpy().astype(np.int64))
def feats(df): return np.stack([np.log1p(0.01 * df["trust"].to_numpy()), df["drive"].to_numpy() / 600, df["legs"].to_numpy() - 1.0, df["n_opt"].to_numpy() - 1.0], 1).astype(np.float32)
G = {"lane": (torch.tensor(tr["lane"].to_numpy()), 900), "pick": (torch.tensor(tr["p_first"].to_numpy()), 30), "del": (torch.tensor(tr["p_last"].to_numpy()), 30), "hour": (torch.tensor(tr["hour"].to_numpy()), 24), "dealer": (torch.tensor(tr["dl"].to_numpy()), nD)}
def gfit(nuis, epochs=400):
    N = {k: code(tr, *c) for k, c in nuis.items()}
    g = {k: torch.zeros(n, requires_grad=True) for k, (_, n) in G.items()}
    u = {k: torch.zeros(int(v.max()) + 1, requires_grad=True) for k, v in N.items()}
    b = torch.zeros(4, requires_grad=True); c = torch.tensor(0.35, requires_grad=True); ls = torch.tensor(-2.5, requires_grad=True)
    X = torch.tensor(feats(tr)); lm = torch.tensor(tr["m_min"].log().to_numpy(), dtype=torch.float32); y = torch.tensor(tr["won"].to_numpy(), dtype=torch.float32)
    opt = torch.optim.Adam([*g.values(), *u.values(), b, c, ls], lr=0.02)
    for _ in range(epochs):
        opt.zero_grad()
        th = c + X @ b + sum(g[k][G[k][0]] for k in g) + sum(u[k][N[k]] for k in u)
        loss = torch.nn.functional.binary_cross_entropy_with_logits((th - lm) / ls.exp(), y) + (2.0 * sum((e ** 2).sum() for k, e in u.items() if k != "seed") + 2.0 * sum((e ** 2).sum() for e in g.values())) / len(y)
        loss.backward(); opt.step()
    return {k: v.detach().numpy() for k, v in g.items()}, b.detach().numpy(), float(c), float(ls.exp()), {k: float(v.std()) for k, v in u.items()}
import os, pickle
CACHE = "runs/price_fits2.pkl"
if os.path.exists(CACHE): full, week = pickle.load(open(CACHE, "rb"))
else:
  full = gfit({"seed": ["seed"], "day": ["seed", "day"], "dealer": ["seed", "dealer"], "pick": ["seed", "p_first"], "del": ["seed", "p_last"], "dealer_day": ["seed", "dealer", "day"]})
  week = gfit({"seed": ["seed"]}); pickle.dump((full, week), open(CACHE, "wb"))
print("global fit, all parts: s", round(full[3], 4), "SD", {k: round(v, 3) for k, v in full[4].items()}, "trust coef", full[1][0].round(2))
print("global fit, week only: s", round(week[3], 4), "SD", {k: round(v, 3) for k, v in week[4].items()})
np.savez("runs/price_global2.npz", **{"g_" + k: v for k, v in full[0].items()}, b=full[1], c=full[2], s=full[3])

te = d.filter("test").sort("world", "at")
GRID = [(f"day s{s_} wk{wk} dy{dy}", ["day"], s_, wk, dy, 0, 0) for s_ in (0.06, 0.08, 0.10) for wk in (0.05, 0.1) for dy in (0.08, 0.14, 0.22)]
GRID += [(f"day+dealer s{s_} dl{dl_}", ["day", "dealer"], s_, 0.1, 0.14, dl_, 0) for s_ in (0.08, 0.10) for dl_ in (0.03, 0.06)]
GRID += [(f"day+towns s{s_} tw{tw}", ["day", "pick"], s_, 0.1, 0.14, 0, tw) for s_ in (0.08, 0.10) for tw in (0.03, 0.06)]
def base(df, fit): 
    g, b, c, _, _ = fit
    return c + feats(df) @ b + g["lane"][df["lane"].to_numpy()] + g["pick"][df["p_first"].to_numpy()] + g["del"][df["p_last"].to_numpy()] + g["hour"][df["hour"].to_numpy()] + g["dealer"][df["dl"].to_numpy()]
def run(df, fit, s, sd, parts):
    """sd: prior SDs. parts: which states are on. Returns one-step-ahead win chances."""
    off = {"week": 0, "day": 1, "dealer": 6, "pick": 6 + nD, "del": 36 + nD}; n = 66 + nD
    var = np.zeros(n); var[0] = sd["week"] ** 2
    if "day" in parts: var[1:6] = sd["day"] ** 2
    if "dealer" in parts: var[6:6 + nD] = sd["dealer"] ** 2
    if "pick" in parts: var[6 + nD:36 + nD] = sd["pick"] ** 2; var[36 + nD:] = sd["del"] ** 2
    out = np.empty(df.shape[0]); k0 = 0
    gb = base(df, fit); lm = np.log(df["m_min"].to_numpy()); y = df["won"].to_numpy()
    day = np.minimum(4, df["day"].to_numpy()); dl = df["dl"].to_numpy(); pf = df["p_first"].to_numpy(); plast = df["p_last"].to_numpy(); at = df["at"].to_numpy()
    for w, grp in df.with_row_index("i").group_by("world", maintain_order=True):
        idx = grp["i"].to_numpy(); P = np.diag(var).copy(); x = np.zeros(n); pend = []
        for i in idx:
            # an answer comes 15 minutes after the request: apply answers that are in
            while pend and at[pend[0]] + 15 <= at[i]:
                j = pend.pop(0); h = [0, 1 + day[j], 6 + dl[j], 6 + nD + pf[j], 36 + nD + plast[j]]
                p = 1 / (1 + np.exp(-(gb[j] + x[h].sum() - lm[j]) / s)); wgt = p * (1 - p)
                Pa = P[:, h].sum(1) / s; den = 1 + wgt * Pa[h].sum() / s
                P -= np.outer(Pa, Pa) * (wgt / den); x += (P[:, h].sum(1) / s) * (y[j] - p)
            h = [0, 1 + day[i], 6 + dl[i], 6 + nD + pf[i], 36 + nD + plast[i]]
            mu = gb[i] + x[h].sum() - lm[i]; v = P[np.ix_(h, h)].sum()
            out[i] = 1 / (1 + np.exp(-mu / np.sqrt(s * s + 0.37 * v)))  # chance with the state's own uncertainty folded in
            pend.append(i)
    return out
def ll(p, y, k=None):
    p = np.clip(p, 1e-6, 1 - 1e-6); v = -(y * np.log(p) + (1 - y) * np.log(1 - p)); return v.mean() if k is None else v[k].mean()
y = te["won"].to_numpy(); print("test rows", len(y), "worlds", te["world"].n_unique(), "constant log loss", round(ll(np.full(len(y), y.mean()), y), 4))
SD = full[4]
res = {}
keep = te["world"].unique().sort().head(150); te = te.filter(pl.col("world").is_in(keep)); y = te["won"].to_numpy()
res["week only"] = run(te, week, week[3], {"week": week[4]["seed"]}, [])
for name, parts, s_, wk, dy, dl_, tw in GRID:
    res[name] = run(te, full, s_, {"week": wk, "day": dy, "dealer": dl_, "pick": tw, "del": tw}, parts)
n_in_day = te.with_columns(pl.int_range(pl.len()).over("world", "day").alias("k"))["k"].to_numpy()
for k, p in res.items():
    print(f"{k:30s} log loss {ll(p, y):.4f} | first 30 of a day {ll(p, y, n_in_day < 30):.4f} | later {ll(p, y, n_in_day >= 30):.4f}")
