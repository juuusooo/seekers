"""Do drivers take our gigs for less on some days? Recorded server weeks (out/worlds/*.json.gz, fetched by rows.ts).
  python feeday.py [variant]        variant: only weeks of that label in server/su1.jsonl (default: all)
Observational: we set the fees, so a day's fee level mixes what drivers accept with how we posted. The second table
holds the fee level fixed: of the views at a given fee (x typical fee), how many end in a booking by that driver."""
import collections, glob, gzip, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
want = sys.argv[1] if len(sys.argv) > 1 else None
label = {}
for f in glob.glob(os.path.join(HERE, "server", "*.jsonl")):
    for l in open(f):
        if l.strip():
            r = json.loads(l); label[r["worldId"]] = r["variant"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon2", "Tue2", "Wed2"]
day = lambda t: DAYS[min(9, int(t // 1440))]
by_start = collections.defaultdict(lambda: collections.defaultdict(list))   # day the driver set off
by_book = collections.defaultdict(lambda: collections.defaultdict(list))    # day the driver booked
views = collections.defaultdict(lambda: [0, 0])                             # (view day, fee bin) -> [views, bookings]
BINS = [(0, 0.8, "under 0.8"), (0.8, 0.95, "0.8-0.95"), (0.95, 1.1, "0.95-1.1"), (1.1, 1.3, "1.1-1.3"), (1.3, 9, "over 1.3")]
worlds = 0
for f in glob.glob(os.path.join(HERE, "out", "worlds", "*.json.gz")):
    wid = os.path.basename(f)[:-8]
    if want and label.get(wid) != want: continue
    d = json.load(gzip.open(f)); ev = d["events"] if isinstance(d["events"], list) else d["events"]["events"]
    worlds += 1
    typ = {e["request"]["id"]: e["request"]["referenceFeeCents"] for e in ev if e["kind"] == "price_request"}
    gigs = {g["id"]: g for g in d["snap"]["gigs"]}
    gtyp = {}
    for g in gigs.values():
        cars = [(s["orderId"], s["leg"]) for s in g["stops"] if s["kind"] == "pickup"]
        # a request's typical fee covers all its legs: a gig carries its share
        legs = collections.Counter(o for o, _ in cars)
        gtyp[g["id"]] = sum(typ.get(o, 0) for o in legs)  # one-leg requests: exact; trade-ins in one gig: the whole fee
    fee_at = lambda g, t: max((s["feeCents"] for s in g["schedule"] if s["at"] <= t), default=g["schedule"][0]["feeCents"])
    booked = {}   # gig -> (at, driver, fee) of the booking that held
    started = {}
    for e in ev:
        k = e["kind"]
        if k == "gig_booked": booked[e["gigId"]] = (e["at"], e["driverId"], e["feeCents"])
        elif k == "gig_started": started[e["gigId"]] = e["at"]
    books = {(g, b[1]) for g, b in booked.items()}
    for g, (at, drv, fee) in booked.items():
        if g not in started or not gtyp.get(g): continue
        gig = gigs[g]; ratio = fee / gtyp[g]; first = gig["schedule"][0]["feeCents"]
        rec = dict(ratio=ratio, at_open=1.0 if fee <= first else 0.0, open=first / gtyp[g], wait=at - gig["postedAt"])
        for table, key in ((by_start, day(started[g])), (by_book, day(at))):
            for name, v in rec.items(): table[key][name].append(v)
    seen = set()
    for e in ev:
        if e["kind"] != "gig_viewed": continue
        g = gigs.get(e["gigId"])
        if not g or not gtyp.get(g["id"]) or (g["id"], e["driverId"]) in seen: continue
        seen.add((g["id"], e["driverId"]))   # a driver's first look at a gig
        r = fee_at(g, e["at"]) / gtyp[g["id"]]
        b = next(name for lo, hi, name in BINS if lo <= r < hi)
        cell = views[(day(e["at"]), b)]; cell[0] += 1; cell[1] += (g["id"], e["driverId"]) in books
print(f"{worlds} weeks" + (f" of variant {want}" if want else ""))
for title, table in (("By the day the driver set off", by_start), ("By the day the driver booked", by_book)):
    print(f"\n{title}\n{'day':5} {'gigs/wk':>8} {'fee paid':>9} {'opening':>8} {'at opening':>10} {'median wait h':>13}")
    for dn in DAYS:
        t = table.get(dn)
        if not t or len(t["ratio"]) < 30: continue
        print(f"{dn:5} {len(t['ratio']) / worlds:8.1f} {st.mean(t['ratio']):9.3f} {st.mean(t['open']):8.3f} {100 * st.mean(t['at_open']):9.1f}% {st.median(t['wait']) / 60:13.1f}")
print("\nFirst looks that end in a booking by that driver, by the fee on screen (x typical fee) and the day of the look")
print(f"{'day':5} " + " ".join(f"{name:>18}" for _, _, name in BINS))
for dn in DAYS[:8]:
    cells = [views.get((dn, name)) for _, _, name in BINS]
    if not any(cells): continue
    print(f"{dn:5} " + " ".join(f"{(100 * c[1] / c[0] if c and c[0] >= 200 else float('nan')):6.2f}% of {c[0] if c else 0:7d}" for c in cells))
