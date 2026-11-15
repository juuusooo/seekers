"""classes.py: truth class of each won order's note (from the reveal), share and cost proxies per class.
Run from Bahn-Spread/: python research/notes/classes.py"""
import json, collections

DAY = 1440


def truth(o):
    """What the world changed for this order, read from the reveal."""
    c = set()
    for leg in o["legs"]:
        t = leg["truth"]
        if t["releasedAt"] is not None:
            c.add("payment")
        elif t["readyAt"] > leg["from"]:
            c.add("ready_later")
        if t["pickupHours"] != leg["pHours"]:
            c.add("pickup_hours")
        if t["deliveryHours"] != leg["dHours"]:
            c.add("delivery_hours")
        if t["manualGearbox"]:
            c.add("manual")
        if t["needsPlates"]:
            c.add("plates")
        if t["summerTyres"]:
            c.add("tyres")
        if t["noteDeadline"] is not None:
            c.add("deadline")
    return c


def late(o):
    due = o["finalDeadline"] or o["wonDeadline"]
    for leg in o["legs"]:
        t = leg["truth"]
        d = min(due, t["noteDeadline"]) if t["noteDeadline"] is not None else due
        if t.get("deliveredAt") is None or t["deliveredAt"] > d:
            return True
    return False


if __name__ == "__main__":
    S = collections.defaultdict(lambda: collections.Counter())
    combos = collections.Counter()
    n = 0
    for line in open("runs/notes/orders.jsonl"):
        o = json.loads(line)
        if o["level"] != 8 or o["cancelled"]:
            continue
        n += 1
        c = truth(o)
        keys = (["no_note"] if o["note"] is None else ["note_any"] + (sorted(c) if c else ["note_harmless"]))
        if o["note"] is None and c:
            keys.append("no_note_but_effect:" + "+".join(sorted(c)))
        if o["note"]:
            combos["+".join(sorted(c)) or "harmless"] += 1
        for k in keys:
            s = S[k]
            s["n"] += 1
            s["late"] += late(o)
            s["fail"] += len(o["fails"])
            for r in o["fails"]:
                s["f_" + r] += 1
    print("orders", n)
    print(f"{'class':38} {'n':>8} {'share':>7} {'late':>6} {'fails/100':>9}  reasons per 100")
    for k, s in sorted(S.items(), key=lambda kv: -kv[1]["n"]):
        rs = " ".join(f"{r[2:]}={100*v/s['n']:.1f}" for r, v in s.items() if r.startswith("f_"))
        print(f"{k:38} {s['n']:8d} {100*s['n']/n:6.2f}% {100*s['late']/s['n']:5.1f}% {100*s['fail']/s['n']:9.1f}  {rs}")
    print("\ncombos (of orders with a note):")
    tot = sum(combos.values())
    for k, v in combos.most_common(30):
        print(f"  {k:45} {v:7d} {100*v/tot:5.1f}%")
