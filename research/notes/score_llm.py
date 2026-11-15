"""score_llm.py: the model's blind labels (runs/notes/llm/out_*.jsonl) against the reveal truth (key.jsonl).
Run from Bahn-Spread/: python research/notes/score_llm.py [-v]"""
import json, glob, collections, sys

V = "-v" in sys.argv
key = {}
for line in open("runs/notes/llm/key.jsonl"):
    r = json.loads(line)
    key[r["nid"]] = r
lab = {}
for f in sorted(glob.glob("runs/notes/llm/out_*.jsonl")):
    for line in open(f):
        line = line.strip()
        if not line:
            continue
        try:
            x = json.loads(line)
            lab[x["id"]] = x
        except Exception:
            print("bad line", f, line[:80])
print("labelled", len(lab), "of", len(key))


def mins(s):
    if not s:
        return None
    h, m = s.split(":")
    return int(h) * 60 + int(m)


conf = collections.Counter()
S = collections.defaultdict(collections.Counter)
soft = collections.Counter()
softBy = collections.defaultdict(collections.Counter)
wrong = []
for nid, x in lab.items():
    r = key[nid]
    t, cls = r["truth"], r["cls"]
    eff = x.get("effect")
    eff = "harmless" if eff == "none" else eff
    also = x.get("also") or []
    conf[(cls, eff)] += 1
    s = S[cls]
    s["n"] += 1
    s["reader_ok"] += r["ok"]
    day0 = r["arrivedAt"] // 1440 * 1440
    hit = eff == cls
    s["effect"] += hit
    s["effect_or_also"] += hit or cls in also
    val = None
    if hit:
        if cls in ("ready_later", "payment", "deadline"):
            want = {"ready_later": t["readyAt"], "payment": t["releasedAt"], "deadline": t["noteDeadline"]}[cls]
            got = None if x.get("dayOffset") is None or mins(x.get("time")) is None else day0 + x["dayOffset"] * 1440 + mins(x["time"])
            val = got == want
        elif cls == "pickup_hours":
            val = mins(x.get("time")) == t["pickupHours"]["closes"] or (x.get("time") is None and mins(x.get("opens")) == t["pickupHours"]["opens"])
        elif cls == "delivery_hours":
            val = mins(x.get("time")) == t["deliveryHours"]["closes"] or (x.get("time") is None and mins(x.get("opens")) == t["deliveryHours"]["opens"])
        else:
            val = True
    s["full"] += bool(val)
    if not val:
        wrong.append((cls, eff, x, r))
    for tag in x.get("soft") or []:
        soft[tag] += 1
        softBy[cls][tag] += 1

print(f"\n{'truth class':15} {'n':>4} {'model effect':>12} {'+also':>6} {'effect+time':>11} {'reader':>7}")
for cls, s in sorted(S.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{cls:15} {s['n']:4d} {100*s['effect']/s['n']:11.1f}% {100*s['effect_or_also']/s['n']:5.1f}% {100*s['full']/s['n']:10.1f}% {100*s['reader_ok']/s['n']:6.1f}%")
print("\nconfusions (truth -> model), off the diagonal:")
for (a, b), v in conf.most_common():
    if a != b:
        print(f"  {a:15} -> {b:15} {v}")
print("\nsoft tags:", soft.most_common(40))
if V:
    for cls, eff, x, r in wrong[:400]:
        t = r["truth"]
        d = r["arrivedAt"] // 1440 * 1440
        rel = lambda v: None if v is None else f"d+{(v-d)//1440} {(v-d)%1440//60}:{(v-d)%60:02d}"
        print(f"[{cls} -> {eff} d{x.get('dayOffset')} {x.get('time')} o{x.get('opens')} also{x.get('also')}] {r['note']!r} | ready {rel(t['readyAt'])} rel {rel(t['releasedAt'])} dl {rel(t['noteDeadline'])} pH {r['pHours']['opens']//60 if r['pHours'] else None}-{r['pHours']['closes']/60 if r['pHours'] else None}=>{t['pickupHours']['opens']/60 if t['pickupHours'] else None}-{t['pickupHours']['closes']/60 if t['pickupHours'] else None} dH {r['dHours']['closes']/60 if r['dHours'] else None}=>{t['deliveryHours']['closes']/60 if t['deliveryHours'] else None} | {x.get('why')}")
