"""Same car (seed + request) under different opening fees: does a higher opening fee cost more or less in the end?
Within-car regression of total cost (fee paid + late refund, x typical) on ln(opening fee x typical), by segment."""
import numpy as np, polars as pl
d = pl.read_parquet("runs/orders.parquet").filter((pl.col("cars0") == 1) & (pl.col("r0") > 0.3) & (pl.col("r0") < 2.5) & pl.col("kit").is_in(["kit-best", "kit-lab", "kit-max"]))
d = d.with_columns(((pl.col("paid") + pl.col("refund")) / pl.col("typ")).alias("cost"), (pl.col("paid") / pl.col("typ")).alias("fee"), (pl.col("refund") / pl.col("typ")).alias("ref"), pl.col("r0").log().alias("lr"),
                   ((pl.col("posted") % 1440) // 60).alias("hour"), (pl.col("posted") // 1440).alias("day"), (pl.col("drive") / 60).alias("dh"), (pl.col("left") / 60).alias("lefth"))
g = ["seed", "order"]
d = d.with_columns(pl.len().over(g).alias("n"), pl.col("lr").std().over(g).alias("sd")).filter((pl.col("n") >= 4) & (pl.col("sd") > 0.02))
for c in ["cost", "fee", "ref", "lr", "on_time"]: d = d.with_columns((pl.col(c) - pl.col(c).mean().over(g)).alias(c + "_d"))
print("cars", d.select(pl.struct(g).n_unique()).item(), "rows", d.shape[0], "mean opening", round(d["r0"].mean(), 3), "within-car SD of ln opening", round(d["lr_d"].std(), 3), "mean cost", round(d["cost"].mean(), 3), "fee", round(d["fee"].mean(), 3), "refund", round(d["ref"].mean(), 3), "typ EUR", round(d["typ"].mean() / 100, 1))
def slope(df):
    x = df["lr_d"].to_numpy(); out = []
    for c in ["cost_d", "fee_d", "ref_d", "on_time_d"]:
        y = df[c].to_numpy(); b = (x @ y) / (x @ x); e = y - b * x; out += [b, np.sqrt((x * x * e * e).sum()) / (x @ x)]
    return out
def tab(name, expr):
    print(name)
    for (b,), df in sorted(d.with_columns(expr.alias("b")).group_by("b"), key=lambda t: str(t[0][0])):
        if df.shape[0] < 3000: continue
        s = slope(df)
        print(f"  {str(b):>12} n {df.shape[0]:>7} opening {df['r0'].mean():.2f} cost {df['cost'].mean():.2f} | +10% opening → cost {s[0]*0.1*100:+.2f} ± {s[1]*0.1*100:.2f} % of typical (fee {s[2]*10:+.2f}, refund {s[4]*10:+.2f}), on time {s[6]*10:+.2f} ± {s[7]*10:.2f} pts")
s = slope(d); print(f"ALL: +10% opening → cost {s[0]*10:+.2f} ± {s[1]*10:.2f} % of typical (fee {s[2]*10:+.2f}, refund {s[4]*10:+.2f}), on time {s[6]*10:+.2f} pts")
cut = lambda col, br: pl.col(col).cut(br, left_closed=True)
tab("opening fee", cut("r0", [0.65, 0.75, 0.85, 0.95, 1.1])); tab("drive h", cut("dh", [0.5, 1, 2, 3, 5, 8])); tab("posted hour", cut("hour", [10, 12, 14, 16, 18]))
tab("day", pl.col("day")); tab("hours to last pickup", cut("lefth", [4, 8, 16, 30, 54])); tab("drivers near pickup", cut("nearP", [5, 15, 40, 100, 200])); tab("drivers near delivery", cut("nearD", [5, 15, 40, 100, 200]))
tab("private delivery", pl.col("privD")); tab("premium", pl.col("premium")); tab("option", pl.col("option")); tab("roster", cut("roster", [650, 720, 790, 860]))
