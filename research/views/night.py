"""How much fee do raises add while nobody looks? Per booking: fee paid vs the fee shown when the gig was last viewed
without being booked, and vs the fee at 22:00 the evening before (bookings 05:00 to 10:00). Recent kit-best / kit-lab weeks."""
import bisect, glob, os, sys
from collections import defaultdict
from multiprocessing import Pool
import numpy as np
sys.path.insert(0, "research/views")
from build import BENCH, load, SRC

def one(world):
    try: events, reveal, snap = load(world, "events"), load(world, "reveal"), load(world, "snapshot")
    except Exception: return None
    gigs = {g["id"]: g for g in snap["gigs"]}
    req = {r["request"]["id"]: r["request"] for r in reveal["requests"]}
    gv = defaultdict(list)
    for v in reveal["views"]: gv[v["gigId"]].append((v["at"], v["feeCents"], v["driverId"]))
    for l in gv.values(): l.sort()
    out = defaultdict(float); first = set()
    hours = np.zeros((24, 3))
    for e in events:
        if e["kind"] != "gig_booked" or e["gigId"] in first: continue
        first.add(e["gigId"]); g = gigs.get(e["gigId"])
        if not g: continue
        at, fee = e["at"], e["feeCents"]
        typ = sum(req[o]["referenceFeeCents"] / len(req[o]["legs"]) for o in {s["orderId"] for s in g["stops"]} if o in req)
        V = [v for v in gv.get(g["id"], []) if v[0] <= at and v[2] != e["driverId"]]
        Vb = [v for v in gv.get(g["id"], []) if v[0] <= at and v[2] == e["driverId"]]
        h = (at % 1440) // 60
        hours[h] += (1, fee, typ)
        out["n"] += 1; out["fee"] += fee
        open_fee = g["schedule"][0]["feeCents"] if g["schedule"] else fee
        out["over_open"] += max(0, fee - open_fee)
        # fee when another driver last looked and passed; no earlier look = opening fee
        seen = max((v[1] for v in V), default=min(open_fee, fee))
        unseen = max(0, fee - max(seen, min(open_fee, fee)))
        out["unseen_raise"] += unseen; out["n_unseen"] += unseen > 0
        if 5 <= h < 10 and g["postedAt"] < (at // 1440) * 1440 - 120:
            eve = (at // 1440) * 1440 - 120  # 22:00 the evening before
            s = [x for x in g["schedule"] if x["at"] <= eve]
            if s:
                out["morning_n"] += 1; out["night_raise"] += max(0, fee - s[-1]["feeCents"]); out["morning_fee"] += fee
                out["night_views"] += sum(1 for v in V if eve <= v[0])
    return dict(out), hours

if __name__ == "__main__":
    worlds = sorted({os.path.basename(f).split(".")[0] for f in glob.glob(f"{SRC}/*.snapshot.json.gz")})
    worlds = [w for w in worlds if BENCH.get(w, ("", "", ""))[1] in ("kit-best", "kit-lab")][:600]
    with Pool(24) as p: res = [r for r in p.map(one, worlds) if r]
    n = len(res); tot = defaultdict(float); H = sum(r[1] for r in res)
    for r, _ in res:
        for k, v in r.items(): tot[k] += v
    e = lambda k: tot[k] / n / 100
    print(f"weeks {n}: bookings/wk {tot['n']/n:.0f}, fees paid at booking {e('fee'):.0f} EUR/wk")
    print(f"raise above opening fee: {e('over_open'):.0f} EUR/wk")
    print(f"raise nobody else had seen before the booker (fee above the highest fee any earlier viewer passed on): {e('unseen_raise'):.0f} EUR/wk on {tot['n_unseen']/n:.0f} bookings")
    print(f"morning bookings (05-10) of gigs posted before 22:00: {tot['morning_n']/n:.0f}/wk, fees {e('morning_fee'):.0f}, raised since 22:00 by {e('night_raise'):.0f} EUR/wk, other drivers' views in that night per booking {tot['night_views']/max(1,tot['morning_n']):.1f}")
    print("hour: bookings/wk, fee/typ")
    print(" ".join(f"{h}:{H[h,0]/n:.0f}/{H[h,1]/max(1,H[h,2]):.2f}" for h in range(24)))
