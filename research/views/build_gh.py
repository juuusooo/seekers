"""One row per open gig per hour: the fee, the gig, and the view state at the start of the hour; label = booked in the hour.

    python research/views/build_gh.py [max_worlds]

Reads runs/events/ (pull.ts, pull2.ts), writes runs/gighours/part-XXXX.parquet.
The fee of an hour is the gig's final schedule where it covers the hour, else the fee of the last view before it.
"""

import bisect
import glob
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

import polars as pl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import AIR, BENCH, DAY, PIDX, PLACES, ROADMIN, ROOT, SRC, load  # noqa: E402

OUT = f"{ROOT}/runs/gighours"
NEAR30 = {p: [q for q in PLACES if AIR[(q, p)] <= 30] for p in PLACES}
NEAR80 = {p: [q for q in PLACES if AIR[(q, p)] <= 80] for p in PLACES}


def world_rows(world):
    try:
        events, drivers, reveal, snap = (
            load(world, w) for w in ("events", "drivers", "reveal", "snapshot")
        )
    except Exception:
        return []
    seed, kit, variant = BENCH.get(world, ("", "", ""))
    home = {d["id"]: d["homePlaceId"] for d in drivers}
    done_gigs = {d["id"]: d["completedGigs"] for d in drivers}
    home_count = defaultdict(int)
    for d in drivers:
        home_count[d["homePlaceId"]] += 1
    n30 = {p: sum(home_count[q] for q in NEAR30[p]) for p in PLACES}
    n80 = {p: sum(home_count[q] for q in NEAR80[p]) for p in PLACES}
    req = {r["request"]["id"]: r["request"] for r in reveal["requests"]}
    orders = {o["id"]: o for o in snap["orders"]}
    gigs = {g["id"]: g for g in snap["gigs"]}

    booked, dropped, expired = defaultdict(list), defaultdict(list), {}
    won_at, warn_at = {}, defaultdict(list)
    for e in events:
        k = e["kind"]
        if k == "gig_booked":
            booked[e["gigId"]].append(e["at"])
        elif k == "gig_dropped":
            dropped[e["gigId"]].append(e["at"])
        elif k == "gig_expired":
            expired[e["gigId"]] = e["at"]
        elif k == "order_won":
            won_at[e["order"]["id"]] = e["at"]
        elif k == "deadline_close":
            warn_at[e["orderId"]].append(e["at"])

    views = sorted(reveal["views"], key=lambda v: v["at"])
    gv = defaultdict(list)  # gig -> [(at, driver, fee)]
    for v in views:
        gv[v["gigId"]].append((v["at"], v["driverId"], v["feeCents"]))
    # Drivers active on a day (viewed any of our gigs that day), by home town: sorted first-view minutes.
    first_today = {}
    for v in views:
        first_today.setdefault((v["driverId"], v["at"] // DAY), v["at"])
    active = defaultdict(list)  # (day, home) -> sorted minutes
    for (did, day), at in first_today.items():
        if did in home:
            active[(day, home[did])].append(at)
    for lst in active.values():
        lst.sort()
    # Bookers so far this week, by home town (drivers who take our gigs).
    order_posts = defaultdict(list)
    for g in gigs.values():
        for o in {s["orderId"] for s in g["stops"]}:
            order_posts[o].append(g["postedAt"])
    open_from = defaultdict(
        list
    )  # first pickup town -> [(posted, end)] of our gigs, for the load feature

    rows = []
    for gid, g in gigs.items():
        legs = [(s["orderId"], s["leg"]) for s in g["stops"] if s["kind"] == "pickup"]
        if not legs or any(o not in orders or o not in req for o, _ in legs):
            continue
        L = [orders[o]["legs"][k] for o, k in legs]
        stops = []
        for s in g["stops"]:
            leg = orders[s["orderId"]]["legs"][s["leg"]]
            stops.append(
                leg["pickup"]["placeId"]
                if s["kind"] == "pickup"
                else leg["delivery"]["placeId"]
            )
        first, last = stops[0], stops[-1]
        typ = sum(req[o]["referenceFeeCents"] / len(req[o]["legs"]) for o, _ in legs)
        drive = sum(ROADMIN[(a, b)] for a, b in zip(stops, stops[1:]))
        posted = g["postedAt"]
        age0 = min(min(order_posts[o]) for o, _ in legs)
        last_pickup = min(orders[o]["lastPickupAt"] or 10**6 for o, _ in legs)
        ready = max(l["pickup"]["window"]["from"] for l in L)
        V = gv.get(gid, [])
        vt = [v[0] for v in V]
        bk, dr = sorted(booked.get(gid, [])), sorted(dropped.get(gid, []))
        # Open intervals: posted → first booking; each drop → next booking; the last one ends when the gig left the app.
        later = [p for o, _ in legs for p in order_posts[o] if p > posted]
        gone = (
            min(
                [expired.get(gid, 10**9)]
                + later
                + [(vt[-1] + 1) if vt else posted + 60]
            )
            if g["status"] == "withdrawn"
            else 10**9
        )
        spans, start = [], posted
        for b in bk:
            if b >= start:
                spans.append((start, b, 1))
                nxt = [d for d in dr if d >= b]
                if not nxt:
                    start = None
                    break
                start = nxt[0]
        if start is not None and gone < 10**9 and gone > start:
            spans.append((start, gone, 0))
        sched = g["schedule"]
        s_at = [s["at"] for s in sched]
        warns = sorted(w for o, _ in legs for w in warn_at.get(o, []))
        for k_span, (a, b, ends_booked) in enumerate(spans):
            t = a
            while t < b or (t == a and ends_booked):
                i = bisect.bisect_left(vt, t)  # views before t
                if sched and t >= s_at[0]:
                    fee = sched[bisect.bisect_right(s_at, t) - 1]["feeCents"]
                elif i > 0:
                    fee = V[i - 1][2]
                else:
                    fee = 0
                if fee > 0:
                    seen = V[:i]
                    viewers = {v[1] for v in seen}
                    j = bisect.bisect_left(vt, t - 60)
                    last_h = seen[j:]
                    day = t // DAY
                    today_viewers = {v[1] for v in seen if v[0] // DAY == day}
                    passed = {
                        v[1] for v in seen if v[2] >= 0.97 * fee
                    }  # saw (about) this fee and did not book
                    act30 = sum(
                        bisect.bisect_left(active.get((day, q), ()), t)
                        for q in NEAR30[first]
                    )
                    act80 = sum(
                        bisect.bisect_left(active.get((day, q), ()), t)
                        for q in NEAR80[first]
                    )
                    tv30 = sum(1 for d in today_viewers if home.get(d) in NEAR30[first])
                    tv80 = sum(1 for d in today_viewers if home.get(d) in NEAR80[first])
                    rows.append(
                        (
                            world,
                            seed,
                            kit,
                            variant,
                            len(drivers),
                            gid,
                            t,
                            fee,
                            typ,
                            int(ends_booked and t <= b < t + 60),
                            k_span,
                            drive,
                            len(legs),
                            int(any(l["pickup"]["privateAddress"] for l in L)),
                            int(any(l["delivery"]["privateAddress"] for l in L)),
                            int(any(l["car"]["premium"] for l in L)),
                            PIDX[first],
                            PIDX[last],
                            n30[first],
                            n80[first],
                            n30[last],
                            n80[last],
                            t - posted,
                            t - age0,
                            last_pickup - t,
                            ready - t,
                            int(bool(warns) and warns[0] <= t),
                            len(seen),
                            len(viewers),
                            len(last_h),
                            len({v[1] for v in last_h}),
                            len(today_viewers),
                            len(passed),
                            len(seen) - len(viewers),
                            (t - vt[i - 1]) if i > 0 else -1,
                            (max(v[2] for v in seen) / fee) if seen else 0.0,
                            (seen[0][2] / fee) if seen else 0.0,
                            sum(1 for d in viewers if done_gigs.get(d, 0) >= 34),
                            sum(1 for d in passed if done_gigs.get(d, 0) >= 34),
                            act30,
                            act80,
                            act30 - tv30,
                            act80 - tv80,
                        )
                    )
                t += 60
    return rows


COLS = [
    "world",
    "seed",
    "kit",
    "variant",
    "roster",
    "gig",
    "t",
    "fee",
    "typ",
    "y",
    "span",
    "drive",
    "cars",
    "privP",
    "privD",
    "premium",
    "p_first",
    "p_last",
    "nearP",
    "nearP80",
    "nearD",
    "nearD80",
    "age",
    "age0",
    "left",
    "wait",
    "urgent",
    "v_n",
    "v_drivers",
    "v_n_1h",
    "v_drivers_1h",
    "v_drivers_today",
    "v_passed",
    "v_repeat",
    "v_since",
    "v_maxfee_ratio",
    "v_firstfee_ratio",
    "v_drivers_exp",
    "v_passed_exp",
    "act30",
    "act80",
    "fresh30",
    "fresh80",
]


def part(args):
    k, worlds = args
    rows = []
    for w in worlds:
        rows.extend(world_rows(w))
    if rows:
        pl.DataFrame(
            rows, schema=COLS, orient="row", infer_schema_length=None
        ).write_parquet(f"{OUT}/part-{k:04d}.parquet", compression="zstd")
    return len(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    have = defaultdict(set)
    for f in glob.glob(f"{SRC}/*.json.gz"):
        w, what = os.path.basename(f).split(".")[:2]
        have[w].add(what)
    done = (
        set(open(f"{OUT}/done.txt").read().split())
        if os.path.exists(f"{OUT}/done.txt")
        else set()
    )
    worlds = sorted(w for w, s in have.items() if len(s) == 4 and w not in done)
    if len(sys.argv) > 1:
        worlds = worlds[: int(sys.argv[1])]
    k0 = len(glob.glob(f"{OUT}/part-*.parquet"))
    jobs = [
        (k0 + i, worlds[j : j + 50]) for i, j in enumerate(range(0, len(worlds), 50))
    ]
    with Pool(24) as pool:
        n = sum(pool.imap_unordered(part, jobs))
    with open(f"{OUT}/done.txt", "a") as f:
        f.write("\n".join(worlds) + "\n")
    print("worlds", len(worlds), "rows", n)
