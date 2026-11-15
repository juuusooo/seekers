"""One row per price request per world: our quote (x list), the outcome, and the dealer's trust then. → runs/quotes.parquet"""
import glob, os, sys
from collections import defaultdict
from multiprocessing import Pool
import polars as pl
sys.path.insert(0, "research/views")
from build import BENCH, PIDX, ROADMIN, SRC, load

def one(world):
    try: reveal, snap = load(world, "reveal"), load(world, "snapshot")
    except Exception: return []
    seed, kit, variant = BENCH.get(world, ("", "", ""))
    if not seed: return []
    ev = defaultdict(list)  # dealer -> [(time, on time?)]
    for o in snap["orders"]:
        dl = [x for x in (o.get("deliveredAt") or []) if x is not None]
        if o["status"] == "delivered" and len(dl) == len(o["legs"]): ev[o["dealerId"]].append((max(dl), max(dl) <= o["deadline"]))
    for l in ev.values(): l.sort()
    rows = []
    for r in reveal["requests"]:
        q, rq = r["quote"], r["request"]
        if not q: continue
        trust = lates = 0
        for t, ok in ev.get(rq["dealerId"], ()):
            if t >= rq["arrivedAt"]: break
            if ok: trust = min(25, trust + 1)
            else: trust //= 2; lates += 1
        ms = {o["kind"]: q[o["kind"]] / o["listPriceCents"] for o in rq["options"] if q.get(o["kind"])}
        if not ms: continue
        legs = rq["legs"]
        rows.append((world, seed, kit, variant, rq["id"], rq["dealerId"], rq["arrivedAt"], PIDX[legs[0]["pickup"]["placeId"]], PIDX[legs[0]["delivery"]["placeId"]],
                     sum(ROADMIN[(l["pickup"]["placeId"], l["delivery"]["placeId"])] for l in legs), len(legs), len(rq["options"]), len(ms),
                     min(ms.values()), max(ms.values()), int(r["outcome"] == "won"), ms.get(r["option"] or "", 0.0), r["option"] or "", trust, lates,
                     sum(o["listPriceCents"] for o in rq["options"]) / len(rq["options"]), rq["referenceFeeCents"]))
    return rows
COLS = ["world", "seed", "kit", "variant", "req", "dealer", "at", "p_first", "p_last", "drive", "legs", "n_opt", "n_quoted", "m_min", "m_max", "won", "m_won", "option", "trust", "lates", "list", "typ"]
if __name__ == "__main__":
    worlds = sorted({os.path.basename(f).split(".")[0] for f in glob.glob(f"{SRC}/*.snapshot.json.gz")})
    with Pool(28) as p: rows = [x for r in p.imap_unordered(one, worlds, chunksize=20) for x in r]
    d = pl.DataFrame(rows, schema=COLS, orient="row", infer_schema_length=None); d.write_parquet("runs/quotes.parquet")
    print(d.shape, d["world"].n_unique(), d["seed"].n_unique(), "won", round(d["won"].mean(), 3))
