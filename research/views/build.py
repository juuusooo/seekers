"""One row per driver view of a gig, with what the driver saw and whether they booked.

    python research/views/build.py [max_worlds]

Reads runs/events/<world>.{events,drivers,reveal,snapshot}.json.gz (pull.ts, pull2.ts), writes
runs/views/part-XXXX.parquet (about 200 worlds each) and skips parts that exist.
"""

import bisect
import glob
import gzip
import json
import math
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

import orjson
import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = f"{ROOT}/runs/events"
OUT = f"{ROOT}/runs/views"
MAP = json.load(open(f"{ROOT}/raw/map.json"))
PLACES = [p["id"] for p in MAP["places"]]
PIDX = {p: i for i, p in enumerate(PLACES)}
LATLON = {p["id"]: (p["lat"], p["lon"]) for p in MAP["places"]}
ROADMIN = {(r["from"], r["to"]): r["minutes"] for r in MAP["roads"]}
DAY = 1440


def air_km(a, b):
    (la1, lo1), (la2, lo2) = LATLON[a], LATLON[b]
    p1, p2 = math.radians(la1), math.radians(la2)
    h = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lo2 - lo1) / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(h))


AIR = {(a, b): air_km(a, b) for a in PLACES for b in PLACES}
BENCH = {}
for line in open(f"{ROOT}/runs/bench.jsonl"):
    try:
        r = json.loads(line)
        BENCH[r["worldId"]] = (
            str(r.get("seed", "")),
            str(r.get("kit", "")),
            str(r.get("variant") or r.get("config") or ""),
        )
    except Exception:
        pass


def load(world, what):
    with gzip.open(f"{SRC}/{world}.{what}.json.gz") as f:
        return orjson.loads(f.read())


def world_rows(world):
    try:
        events, drivers, reveal, snap = (
            load(world, w) for w in ("events", "drivers", "reveal", "snapshot")
        )
    except Exception:
        return []
    seed, kit, variant = BENCH.get(world, ("", "", ""))
    drv = {d["id"]: d for d in drivers}
    home_count = defaultdict(int)
    for d in drivers:
        home_count[d["homePlaceId"]] += 1
    near30 = {
        p: sum(n for h, n in home_count.items() if AIR[(h, p)] <= 30) for p in PLACES
    }
    near80 = {
        p: sum(n for h, n in home_count.items() if AIR[(h, p)] <= 80) for p in PLACES
    }
    req = {r["request"]["id"]: r["request"] for r in reveal["requests"]}
    orders = {o["id"]: o for o in snap["orders"]}
    gigs = {g["id"]: g for g in snap["gigs"]}

    # Gig facts.
    first_post = {}  # order -> first minute any of its gigs was posted (a reposted car keeps its age)
    for g in gigs.values():
        for s in g["stops"]:
            first_post[s["orderId"]] = min(
                first_post.get(s["orderId"], 10**9), g["postedAt"]
            )
    gx = {}
    for gid, g in gigs.items():
        legs = [(s["orderId"], s["leg"]) for s in g["stops"] if s["kind"] == "pickup"]
        if not legs or any(o not in orders or o not in req for o, _ in legs):
            continue
        L = [orders[o]["legs"][k] for o, k in legs]
        typ = sum(req[o]["referenceFeeCents"] / len(req[o]["legs"]) for o, _ in legs)
        stops = []
        for s in g["stops"]:
            leg = orders[s["orderId"]]["legs"][s["leg"]]
            stops.append(
                leg["pickup"]["placeId"]
                if s["kind"] == "pickup"
                else leg["delivery"]["placeId"]
            )
        gx[gid] = dict(
            typ=typ,
            drive=sum(ROADMIN[(a, b)] for a, b in zip(stops, stops[1:])),
            cars=len(legs),
            privP=int(any(l["pickup"]["privateAddress"] for l in L)),
            privD=int(any(l["delivery"]["privateAddress"] for l in L)),
            premium=int(any(l["car"]["premium"] for l in L)),
            first=stops[0],
            last=stops[-1],
            posted=g["postedAt"],
            age0=min(first_post[o] for o, _ in legs),
            lastPickup=min(orders[o]["lastPickupAt"] or 10**6 for o, _ in legs),
            ready=max(l["pickup"]["window"]["from"] for l in L),
            deadline=min(orders[o]["deadline"] for o, _ in legs),
            exp=int(g["audience"]["experienced"]),
            manual=int(g["audience"]["manualLicence"]),
            order=legs[0][0],
        )

    # Bookings and drops by gig and by driver.
    books = defaultdict(list)  # (gig, driver) -> [at]
    book_fee = {}
    gig_books = defaultdict(list)  # gig -> [(at, fee)]
    drv_books = defaultdict(list)  # driver -> [at]
    drv_drops = defaultdict(list)
    for e in events:
        k = e["kind"]
        if k == "gig_booked":
            books[(e["gigId"], e["driverId"])].append(e["at"])
            book_fee[(e["gigId"], e["driverId"], e["at"])] = e.get("feeCents", 0)
            gig_books[e["gigId"]].append((e["at"], e.get("feeCents", 0)))
            drv_books[e["driverId"]].append(e["at"])
        elif k == "gig_dropped" and e.get("driverId"):
            drv_drops[e["driverId"]].append(e["at"])

    views = sorted(reveal["views"], key=lambda v: v["at"])
    by_pair = defaultdict(list)
    for v in views:
        by_pair[(v["gigId"], v["driverId"])].append(v["at"])
    # What a driver has seen our fees do (rule: drivers learn how far a fee rose when a gig they viewed is booked).
    order_open = {}  # order -> first fee seen by anyone / typ
    rows = []
    g_views = defaultdict(int)
    g_viewers = defaultdict(set)
    d_views = defaultdict(list)
    d_first_fee = {}
    d_seen_orders = defaultdict(set)
    order_rise = {}  # order -> (booked at, booked fee / opening fee)
    for gid, bs in gig_books.items():
        if gid in gx:
            g = gigs[gid]
            open_fee = g["schedule"][0]["feeCents"] if g["schedule"] else 0
            at, fee = min(bs)
            if open_fee > 0:
                order_rise[gx[gid]["order"]] = (
                    at,
                    fee / open_fee,
                    (at - gx[gid]["age0"]) / 60,
                )
    for v in views:
        gid, did, at, fee = v["gigId"], v["driverId"], v["at"], v["feeCents"]
        x, d = gx.get(gid), drv.get(did)
        if x is None or d is None:
            continue
        pair = by_pair[(gid, did)]
        i = bisect.bisect_right(pair, at)
        nxt = pair[i] if i < len(pair) else 10**9
        bk = [b for b in books.get((gid, did), ()) if at <= b < nxt]
        delay = bk[0] - at if bk else -1
        home = d["homePlaceId"]
        seen = [
            order_rise[o]
            for o in d_seen_orders[did]
            if o in order_rise and order_rise[o][0] < at
        ]
        dv = d_views[did]
        today = at // DAY
        db = drv_books.get(did, ())
        nb = bisect.bisect_left(db, at)
        rows.append(
            (
                world,
                seed,
                kit,
                variant,
                len(drivers),
                gid,
                did,
                at,
                fee,
                x["typ"],
                int(bool(bk) and delay <= 10),
                int(bool(bk)),
                delay,
                x["drive"],
                x["cars"],
                x["privP"],
                x["privD"],
                x["premium"],
                x["exp"],
                x["manual"],
                PIDX[x["first"]],
                PIDX[x["last"]],
                at - x["posted"],
                at - x["age0"],
                x["lastPickup"] - at,
                x["ready"] - at,
                x["deadline"] - at,
                near30[x["first"]],
                near80[x["first"]],
                near30[x["last"]],
                near80[x["last"]],
                g_views[gid],
                len(g_viewers[gid]),
                PIDX[home],
                d["rating"],
                int(d["licence"] == "manual"),
                d["completedGigs"],
                d["drops"],
                AIR[(home, x["first"])],
                ROADMIN[(home, x["first"])],
                AIR[(x["last"], home)],
                ROADMIN[(x["last"], home)],
                len(dv),
                sum(1 for t in dv if t // DAY == today),
                (at - dv[-1]) if dv else -1,
                nb,
                sum(1 for t in db[:nb] if t // DAY == today),
                bisect.bisect_left(drv_drops.get(did, ()), at),
                i - 1,
                d_first_fee.get((gid, did), 0),
                len(seen),
                (sum(s[1] for s in seen) / len(seen)) if seen else 0.0,
                max((s[1] for s in seen), default=0.0),
                (sum(s[2] for s in seen) / len(seen)) if seen else 0.0,
            )
        )
        g_views[gid] += 1
        g_viewers[gid].add(did)
        dv.append(at)
        d_first_fee.setdefault((gid, did), fee)
        d_seen_orders[did].add(x["order"])
    return rows


COLS = [
    "world",
    "seed",
    "kit",
    "variant",
    "roster",
    "gig",
    "driver",
    "at",
    "fee",
    "typ",
    "y",
    "y_any",
    "delay",
    "drive",
    "cars",
    "privP",
    "privD",
    "premium",
    "aud_exp",
    "aud_manual",
    "p_first",
    "p_last",
    "age",
    "age0",
    "left",
    "wait",
    "to_deadline",
    "nearP",
    "nearP80",
    "nearD",
    "nearD80",
    "g_views",
    "g_viewers",
    "home",
    "rating",
    "manual",
    "gigs_done",
    "drops",
    "km_to_pickup",
    "min_to_pickup",
    "km_home",
    "min_home",
    "d_views",
    "d_views_today",
    "d_since_view",
    "d_books",
    "d_books_today",
    "d_drops_week",
    "d_prior_views_gig",
    "d_first_fee_gig",
    "d_seen_n",
    "d_seen_rise_mean",
    "d_seen_rise_max",
    "d_seen_open_h",
]


def part(args):
    k, worlds = args
    out = f"{OUT}/part-{k:04d}.parquet"
    rows = []
    for w in worlds:
        rows.extend(world_rows(w))
    if rows:
        pl.DataFrame(
            rows, schema=COLS, orient="row", infer_schema_length=None
        ).write_parquet(out, compression="zstd")
    return len(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    have = defaultdict(set)
    for f in glob.glob(f"{SRC}/*.json.gz"):
        w, what = os.path.basename(f).split(".")[:2]
        have[w].add(what)
    done = set()
    if os.path.exists(f"{OUT}/done.txt"):
        done = set(open(f"{OUT}/done.txt").read().split())
    worlds = sorted(w for w, s in have.items() if len(s) == 4 and w not in done)
    if len(sys.argv) > 1:
        worlds = worlds[: int(sys.argv[1])]
    k0 = len(glob.glob(f"{OUT}/part-*.parquet"))
    jobs = [
        (k0 + i, worlds[j : j + 200]) for i, j in enumerate(range(0, len(worlds), 200))
    ]
    with Pool(24) as pool:
        n = sum(pool.imap_unordered(part, jobs))
    with open(f"{OUT}/done.txt", "a") as f:
        f.write("\n".join(worlds) + "\n")
    print("worlds", len(worlds), "rows", n)
