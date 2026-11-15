"""Is kit-best's booking model (model.json) calibrated on recent played weeks, segment by segment?
Predicted = model.json hourly chance (load input left at 0); actual = booked in the hour. First open span only."""
import json, sys
import numpy as np, polars as pl
m = json.load(open("kit-best/core/data/model.json"))["book"]; c = m["coef"]
T = json.load(open("kit-best/core/data/typ.json"))
places = [p["id"] for p in json.load(open("raw/map.json"))["places"]]
lane = np.full((30, 30), np.nan)
for k, v in T["lane"].items():
    a, b = k.split(">")
    if T["n"].get(k, 0) >= 5: lane[places.index(a), places.index(b)] = v
d = pl.read_parquet("runs/gighours/part-*.parquet").filter((pl.col("span") == 0) & (pl.col("typ") > 0) & pl.col("kit").is_in(["kit-best", "kit-lab", "kit-max"]))
ln = lane[d["p_first"].to_numpy(), d["p_last"].to_numpy()] + T["privP"] * d["privP"].to_numpy() + T["privD"] * d["privD"].to_numpy() + T["prem"] * d["premium"].to_numpy()
typ = np.where((d["cars"].to_numpy() == 1) & ~np.isnan(ln), np.exp(ln), d["typ"].to_numpy())
t = d["t"].to_numpy(); hour = (t % 1440) // 60; dow = (t // 1440) % 7
left = np.clip(d["left"].to_numpy() / 60, 0, 96); r = d["fee"].to_numpy() / typ; dh = d["drive"].to_numpy() / 60
z = (m["intercept"] + c["ln_nearP"] * np.log1p(d["nearP"].to_numpy()) + c["ln_nearD"] * np.log1p(d["nearD"].to_numpy()) + c["ln_nearP80"] * np.log1p(d["nearP80"].to_numpy()) + c["ln_nearD80"] * np.log1p(d["nearD80"].to_numpy())
     + c["driveH"] * dh + c["long"] * (dh >= 5) + c["cars2"] * (d["cars"].to_numpy() > 1) + c["privP"] * d["privP"].to_numpy() + c["privD"] * d["privD"].to_numpy() + c["premium"] * d["premium"].to_numpy()
     + c["ln_typ"] * np.log(np.maximum(1, typ / 100)) + c["night"] * ((hour >= 23) | (hour < 7)) + c["morning"] * ((hour >= 7) & (hour < 10)) + c["evening"] * ((hour >= 16) & (hour < 20)) + c["late"] * ((hour >= 20) & (hour < 23))
     + c["sat"] * (dow == 5) + c["sun"] * (dow == 6) + c["ln_age"] * np.log1p(np.maximum(0, d["age"].to_numpy()) / 60) + c["ln_left"] * np.log1p(left) + c["tight"] * (left < 3) + c["ln_wait"] * np.log1p(np.maximum(0, d["wait"].to_numpy()) / 60) + c["urgent"] * d["urgent"].to_numpy()
     + c["r"] * r + c["r_hi1"] * np.maximum(0, r - 1) + c["r_hi2"] * np.maximum(0, r - 1.4))
p = 1 / (1 + np.exp(-z)); y = d["y"].to_numpy()
d = d.with_columns(pl.Series("p", p), pl.Series("r", r), pl.Series("hour", hour), pl.Series("dow", dow), pl.Series("dh", dh), pl.Series("lefth", left), pl.Series("ageh", d["age"].to_numpy() / 60))
print("rows", len(y), "worlds", d["world"].n_unique(), "actual", y.mean().round(4), "predicted", p.mean().round(4))
def tab(name, expr):
    g = d.with_columns(expr.alias("b")).group_by("b").agg(pl.len().alias("n"), pl.col("y").mean().round(3).alias("actual"), pl.col("p").mean().round(3).alias("pred"), pl.col("r").mean().round(2).alias("r")).sort("b").with_columns((pl.col("actual") / pl.col("pred")).round(2).alias("ratio"))
    print(name); print("\n".join(f"  {str(b):>12} n {n:>8} actual {a:.3f} pred {q:.3f} ratio {x:.2f} r {rr}" for b, n, a, q, rr, x in g.iter_rows()))
cut = lambda col, br: pl.col(col).cut(br, left_closed=True)
tab("age h", cut("ageh", [0.01, 1.01, 2.01, 4.01, 8.01, 24]))
tab("hour", cut("hour", [7, 10, 13, 16, 20, 23]))
tab("day", pl.col("dow"))
tab("fee r", cut("r", [0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4, 1.6]))
tab("drive h", cut("dh", [0.5, 1, 2, 3, 5, 8]))
tab("left h", cut("lefth", [3, 6, 12, 24, 48]))
tab("cars", pl.col("cars")); tab("privP", pl.col("privP")); tab("privD", pl.col("privD")); tab("premium", pl.col("premium"))
tab("nearP", cut("nearP", [5, 15, 40, 100, 200])); tab("nearD", cut("nearD", [5, 15, 40, 100, 200]))
tab("roster", cut("roster", [650, 720, 790, 860]))
