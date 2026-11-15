"""One row per won order per world: how its first gig opened, what moving it cost in the end. → runs/orders.parquet
Same seed + same request id across worlds = the same car under different fee settings."""
import glob, os, sys
from collections import defaultdict
from multiprocessing import Pool
import polars as pl
sys.path.insert(0, "research/views")
from build import AIR, BENCH, PIDX, PLACES, ROADMIN, SRC, load

def one(world):
    try: reveal, snap, drivers = load(world, "reveal"), load(world, "snapshot"), load(world, "drivers")
    except Exception: return []
    seed, kit, variant = BENCH.get(world, ("", "", ""))
    if not seed: return []
    hc = defaultdict(int)
    for d in drivers: hc[d["homePlaceId"]] += 1
    near = {p: sum(n for h, n in hc.items() if AIR[(h, p)] <= 30) for p in PLACES}
    req = {r["request"]["id"]: r["request"] for r in reveal["requests"]}
    gigs_of = defaultdict(list)
    for g in snap["gigs"]:
        for o in {s["orderId"] for s in g["stops"]}: gigs_of[o].append(g)
    rows = []
    for o in snap["orders"]:
        r, gs = req.get(o["id"]), sorted(gigs_of.get(o["id"], []), key=lambda g: g["postedAt"])
        if not r or not gs or o["status"] == "cancelled" or len(o["legs"]) != 1: continue
        g0 = gs[0]; typ = r["referenceFeeCents"]
        if not g0["schedule"]: continue
        def share(g):  # this order's share of a gig's fee, by typical fee
            tot = sum(req[x]["referenceFeeCents"] for x in {s["orderId"] for s in g["stops"]} if x in req)
            return typ / tot if tot else 1.0
        cars0 = len({s["orderId"] for s in g0["stops"]})
        paid = sum(g["feeCents"] * share(g) for g in gs if g["status"] == "done")
        dl = o["deliveredAt"][0] if o.get("deliveredAt") else None
        price = o["priceCents"]; late_h = None if dl is None else (dl - o["deadline"]) / 60
        refund = 3 * price if dl is None else 0 if late_h <= 0 else 0.1 * price if late_h <= 2 else 0.25 * price if late_h <= 24 else 0.5 * price if late_h <= 96 else price
        s0 = g0["schedule"]; leg = o["legs"][0]; a, b = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        rows.append((world, seed, kit, variant, o["id"], len(drivers), typ, price, g0["postedAt"], cars0, s0[0]["feeCents"] * share(g0) / typ,
                     (s0[min(3, len(s0) - 1)]["feeCents"] - s0[0]["feeCents"]) * share(g0) / typ, len(gs), paid, refund, int(dl is not None and late_h <= 0), int(dl is None),
                     ROADMIN[(a, b)], PIDX[a], PIDX[b], near[a], near[b], int(leg["pickup"]["privateAddress"]), int(leg["delivery"]["privateAddress"]), int(leg["car"]["premium"]),
                     (o["lastPickupAt"] or 0) - g0["postedAt"], leg["pickup"]["window"]["from"] - g0["postedAt"], o["option"], o["deadline"]))
    return rows
COLS = ["world", "seed", "kit", "variant", "order", "roster", "typ", "price", "posted", "cars0", "r0", "raise3", "n_gigs", "paid", "refund", "on_time", "undelivered",
        "drive", "p_first", "p_last", "nearP", "nearD", "privP", "privD", "premium", "left", "wait", "option", "deadline"]
if __name__ == "__main__":
    have = defaultdict(set)
    for f in glob.glob(f"{SRC}/*.json.gz"):
        w, what = os.path.basename(f).split(".")[:2]; have[w].add(what)
    worlds = sorted(w for w, s in have.items() if {"reveal", "snapshot", "drivers"} <= s)
    with Pool(16) as p: rows = [x for r in p.imap_unordered(one, worlds, chunksize=20) for x in r]
    d = pl.DataFrame(rows, schema=COLS, orient="row", infer_schema_length=None); d.write_parquet("runs/orders.parquet")
    print(d.shape, d["world"].n_unique(), d["seed"].n_unique())
