"""Request features that are not in the price model, one row per (world, req). Offline, reads reveal files only.

    python research/best13/feat/extract.py      -> runs/rc/feat/feat.parquet (+ worlds.parquet with the sample split)

Seeds are split at random in two halves (A, B); up to 7 worlds per seed. The same seed gives the same requests
to every world, so the seed is the unit for all errors.
"""

import gzip
import os
import random
from collections import Counter
from multiprocessing import Pool
import orjson
import polars as pl

ROOT = "/root/system/z-sideprojects/junction-2026/Bahn-Spread"
SRC, OUT = f"{ROOT}/runs/events", f"{ROOT}/runs/rc/feat"
PER_SEED = 7


def one(world):
    try:
        reveal = orjson.loads(gzip.open(f"{SRC}/{world}.reveal.json.gz").read())
    except Exception:
        return []
    reqs = [r["request"] for r in reveal["requests"]]
    size = Counter(r["batchId"] for r in reqs if r.get("batchId"))
    rows = []
    for rq in reqs:
        legs, opts, at = rq["legs"], rq["options"], rq["arrivedAt"]
        kinds = {o["kind"] for o in opts}
        cheap = min(opts, key=lambda o: o["listPriceCents"])
        charge = [
            l["car"].get("chargePercent")
            for l in legs
            if l["car"].get("chargePercent") is not None
        ]
        note = rq.get("note") or None
        rows.append(
            (
                world,
                rq["id"],
                rq.get("batchId") or "",
                size.get(rq.get("batchId"), 0),
                int(any(l["car"]["premium"] for l in legs)),
                int(any(l["car"]["electric"] for l in legs)),
                int(any(l["pickup"]["privateAddress"] for l in legs)),
                int(any(l["delivery"]["privateAddress"] for l in legs)),
                int("same_day" in kinds),
                int("next_day" in kinds),
                int(bool(kinds - {"same_day", "next_day"})),
                ",".join(sorted(kinds)),
                (cheap["deadline"] - at) / 60,
                (min(o["deadline"] for o in opts) - at) / 60,
                (max(o["deadline"] for o in opts) - at) / 60,
                (legs[0]["pickup"]["window"]["from"] - at) / 60,
                (
                    legs[0]["pickup"]["window"]["to"]
                    - legs[0]["pickup"]["window"]["from"]
                )
                / 60,
                int(note is not None),
                (note or {}).get("language", ""),
                rq["referenceFeeCents"] / cheap["listPriceCents"],
                rq["respondBy"] - at,
                min(charge) if charge else -1.0,
                cheap["listPriceCents"],
                cheap["kind"],
            )
        )
    return rows


COLS = [
    "world",
    "req",
    "batch",
    "bsize",
    "premium",
    "electric",
    "priv_pick",
    "priv_del",
    "k_same",
    "k_next",
    "k_other",
    "kinds",
    "h_dead_cheap",
    "h_dead_min",
    "h_dead_max",
    "h_pick_open",
    "h_pick_len",
    "note",
    "note_lang",
    "typ_rel",
    "respond_min",
    "charge",
    "list_cheap",
    "kind_cheap",
]
if __name__ == "__main__":
    have = {f.split(".")[0] for f in os.listdir(SRC) if f.endswith(".reveal.json.gz")}
    w = (
        pl.scan_parquet(f"{ROOT}/runs/quotes.parquet")
        .select("world", "seed")
        .unique()
        .collect()
        .filter(pl.col("world").is_in(list(have)))
        .sort("seed", "world")
    )
    rnd = random.Random(7)
    seeds = sorted(w["seed"].unique())
    rnd.shuffle(seeds)
    half = {s: ("A" if i % 2 == 0 else "B") for i, s in enumerate(seeds)}
    pick = []
    for (s,), g in w.group_by("seed", maintain_order=True):
        ws = g["world"].to_list()
        rnd.shuffle(ws)
        pick += [(x, s, half[s]) for x in ws[:PER_SEED]]
    wd = pl.DataFrame(pick, schema=["world", "seed", "sample"], orient="row")
    wd.write_parquet(f"{OUT}/worlds.parquet")
    print(wd.group_by("sample").agg(pl.len(), pl.col("seed").n_unique()))
    with Pool(28) as p:
        rows = [
            x
            for r in p.imap_unordered(one, wd["world"].to_list(), chunksize=20)
            for x in r
        ]
    d = pl.DataFrame(rows, schema=COLS, orient="row", infer_schema_length=None)
    d.write_parquet(f"{OUT}/feat.parquet")
    print(d.shape)
    print(
        d.select(
            pl.exclude("world", "req", "batch", "kinds", "note_lang", "kind_cheap")
        ).describe()
    )
    print(d.group_by("kinds").len().sort("len", descending=True))
    print(d.group_by("respond_min").len().sort("len", descending=True).head(8))
    print(d.group_by("bsize").len().sort("bsize").head(12))
    print(d.group_by("note_lang").len())
