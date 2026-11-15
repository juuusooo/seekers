"""build.py: one row per won order of the recorded weeks (runs/events), with its note and the reveal truth.
Out: runs/notes/orders.jsonl. Run from Bahn-Spread/: python research/notes/build.py [weeks]"""
import gzip, json, glob, random, sys, collections
from multiprocessing import Pool

BENCH = {}
for line in open("runs/bench.jsonl"):
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("worldId"):
        BENCH[r["worldId"]] = r


def week(path):
    w = path.split("/")[-1].split(".")[0]
    try:
        ev = json.load(gzip.open(path))
        reveal = json.load(gzip.open(path.replace(".events", ".reveal")))
        snap = json.load(gzip.open(path.replace(".events", ".snapshot")))
    except Exception:
        return []
    b = BENCH.get(w, {})
    req, fails, won, cancelled = {}, collections.defaultdict(list), {}, set()
    for e in ev:
        k = e.get("kind")
        if k == "price_request":
            req[e["request"]["id"]] = e["request"]
        elif k == "visit_failed":
            fails[e["orderId"]].append(e["reason"])
        elif k == "order_won":
            won[e["order"]["id"]] = e["order"]
        elif k == "order_cancelled":
            cancelled.add(e.get("orderId") or e.get("order", {}).get("id"))
    final = {o["id"]: o for o in snap["orders"]}
    rows = []
    for o in reveal["orders"]:
        oid = o["orderId"]
        r, wo, fo = req.get(oid), won.get(oid), final.get(oid)
        if not r or not wo:
            continue
        note = r.get("note")
        legs = []
        for leg, t in zip(r["legs"], o["legs"]):
            legs.append({"from": leg["pickup"]["window"]["from"], "pHours": leg["pickup"]["hours"], "dHours": leg["delivery"]["hours"],
                         "privP": leg["pickup"]["privateAddress"], "privD": leg["delivery"]["privateAddress"], "truth": t})
        opt = next((x for x in r["options"] if x["kind"] == wo["option"]), None)
        rows.append({"world": w, "kit": b.get("kit") or b.get("config"), "variant": b.get("variant"), "benchAt": b.get("at"), "level": b.get("level"),
                     "weekOnTime": b.get("onTime"), "id": oid, "dealer": r["dealerId"], "arrivedAt": r["arrivedAt"],
                     "note": note["text"] if note else None, "lang": note["language"] if note else None, "option": wo["option"],
                     "optDeadline": opt["deadline"] if opt else None, "wonDeadline": wo["deadline"], "finalDeadline": fo["deadline"] if fo else None,
                     "price": wo["priceCents"], "ref": r["referenceFeeCents"], "cancelled": oid in cancelled, "fails": fails.get(oid, []), "legs": legs})
    return rows


if __name__ == "__main__":
    files = sorted(glob.glob("runs/events/*.events.json.gz"))
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(files)
    random.seed(7)
    files = random.sample(files, min(n, len(files)))
    with Pool(12) as pool, open("runs/notes/orders.jsonl", "w") as out:
        weeks = orders = 0
        for rows in pool.imap_unordered(week, files, chunksize=8):
            if rows:
                weeks += 1
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                orders += 1
    print("weeks", weeks, "orders", orders)
