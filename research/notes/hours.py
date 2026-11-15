"""hours.py: prototype reader of site hours in dealer notes (the class kit-best's reader skips), scored on the reveal.
readHours(note, statedPickup, statedDelivery) -> real opens/closes of each site when the note makes them tighter.
Run from Bahn-Spread/: python research/notes/hours.py [-v]"""
import json, re, sys, collections

WORDS = [(r"yhdeksä|yhdeksää|\bnio\b|\bnine\b", 9), (r"kymmen|\btio\b|\bten\b", 10), (r"yksitoista|yhde[a-zä]*toista|\belva\b|eleven", 11),
         (r"kaksitoista|kahde[a-zä]*toi|kahteentoista|\btolv\b|twelve|\bnoon\b", 12), (r"yhdeltä|yhteen|\byhden\b|\byksi\b|\bett\b|\bone\b", 13),
         (r"kahdelta|kahteen|\bkahden\b|\bkaksi\b|\bkahta\b|\btvå\b|\btwo\b", 14), (r"kolmelta|kolmeen|\bkolmen\b|\bkolmea?\b|\btre\b|\bthree\b", 15),
         (r"neljältä|neljään|\bneljän\b|\bneljää?\b|\bfyra\b|\bfour\b", 16), (r"viideltä|viiteen|\bviiden\b|\bviisi\b|viittä|\bfem\b|\bfive\b", 17)]
T = r"(\d{1,2})(?:[.:](\d{2}))?(?::?(?:stä|sta|ään|aan|een|n))?\s*(am|pm)?"
RANGE = re.compile(T + r"\s*(?:[-–]|to\b|till\b)\s*" + T.replace("(am|pm)?", "(am|pm|noon)?") + r"|" + T + r"\s*[-–]\s*(noon)")
FI_RANGE = re.compile(r"(\d{1,2}):?(?:stä|sta)\s+(\d{1,2})(?:[.:](\d{2}))?:?(?:ään|aan|een)")
ONE = re.compile(r"\b" + T + r"\b")
DENIED = re.compile(r"\(?\b(?:ei|not|inte|ej)\s+(?:klo\.?|kl\.?|kello|at|klockan)?\s*\d{1,2}(?:[.:]\d{2})?\s*(?:am|pm)?\s*\)?")
DELIVERY = re.compile(r"vast+a+n?ot|vastaanot|kohde|kohtee|kohtes|peril|preil|perl+[aä]|toimitusos|receiv|recieiv|destin|detin|mottag|leverans|drop.?off")
PICKUP = re.compile(r"hämtas|hamtas|hakea|\bshop\b|liike|meillä|onnistuu|auki|kiinni|aukiolo|avoinna|\bopen|clos|öppet|oppet|öppettid|stäng|stang|nouto|noud|haettava|\bhaku\b|collect|pick.?up|hämtning|hamtning|ketään|ketaan|nobody|luovutu|utlämning|utlamning|täällä|taalla|sulke")
SHUT = re.compile(r"pick.?up (?:by|no later)|haku viim|nouto viim|hämtas senast|hämtning senast|ingen|onnistuu|auki|kiinni|aukiolo|avoinna|\bopen|clos|öppet|oppet|öppettid|stäng|stang|sulke|ketään|ketaan|nobody|asti|saakka|until|\btill\b|luovutuks|utlämning|utlamning|vastaanot|receiving|mottagning|\bonly\b|\bvain\b|ennen|before|före|innan")
DEADLINE = re.compile(r"viim|mennessä|mennessa|menessä|\bby\b|latest|no later|senast|måste|maste|must|hakemaan|hämtar|picks it up|silloin")
ARRIVE = re.compile(r"peril|perl+[aä]|toimitus(?!os)|destin|arriv|framme|på plats|pa plats|deliver|oltava|hakemaan|hämtar|picks it up|there")
READY = re.compile(r"från|fran\b|no pickup|before that|valmis|vlamis|valmii|ready|klar\b|alkaen|alken|aikaisintaan|vasta\b|tidigast|först|forst|earliest|not before|\bfrom\b|maksu|payment|pays|betal|huolto|workshop|verkstad|pesu")


def clock(h, m, ap):
    h, m = int(h), int(m or 0)
    if ap == "pm" and h < 12:
        h += 12
    return h * 60 + m if h <= 24 and m < 60 else None


def last_time(text):
    best, at = None, -1
    for m in ONE.finditer(text):
        v = clock(m.group(1), m.group(2), m.group(3))
        if v is not None and m.start() > at:
            best, at = v, m.start()
    for pat, hour in WORDS:
        m = re.search(pat, text)
        if m and m.start() > at:
            half = re.search(r"(puoli|puolta|half|halv)\s*$", text[:m.start()])
            best, at = hour * 60 - (30 if half else 0), m.start()
    return best


LEXICON = ["vastaanotto", "vastaanottava", "vastaanottaja", "vastaanotot", "perillä", "destination", "receiving", "mottagaren", "mottagning", "aukioloajat", "haettava",
           "pickup", "closes", "kiinni", "sulkee", "noudettavissa", "hämtning", "öppettider", "luovutuksia", "utlämning", "kohde", "collect", "before", "stänger", "toimitusosoite", "betalning", "valmis", "korjaus", "correction"]
SPELL = {}


def dist(a, b):
    d = [[i] + [0] * len(b) for i in range(len(a) + 1)]
    d[0] = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[-1][-1]


def spell(m):
    w = m.group(0)
    if len(w) < 5:
        return w
    if w not in SPELL:
        SPELL[w] = w
        if w not in LEXICON:
            for x in LEXICON:
                if abs(len(x) - len(w)) <= 2 and dist(w, x) <= (2 if len(x) >= 9 else 1):
                    SPELL[w] = x
                    break
    return SPELL[w]


CALL = re.compile(r"(?:n\.?\s*)?(?:\d+\s*min\w*|tuntia|tnutia|tntia|an hour|en timme)?\s*(?:ennen|before|före|innan)\s+(?:noutoa|kuin|pickup|you|arrival|saapumista|perillä|ankomst|avfärd)")


def readHours(note, statedP, statedD):
    out = {"pickupOpens": None, "pickupCloses": None, "deliveryOpens": None, "deliveryCloses": None}
    if not note:
        return out
    text = re.sub(r"[a-zåäö]+", spell, note.lower()).replace("viim.", "viim ").replace("klo.", "klo ").replace("kl.", "kl ")
    text = re.sub(r"\d+\s*min\w*", " ", CALL.sub(" ", text))
    text = re.sub(r"(klo|kl|kello|klockan|at|by|until|before|ennen|viimeistään|senast|than)\s+([01]\d|2[0-3])([0-5]\d)\b", r"\1 \2:\3", text)
    last = None
    for raw in re.split(r"(?<!\d)\.(?!\d)|\.(?=\s|$)|!|\s/\s|;", text):
        c = DENIED.sub(" ", raw)
        fix = re.search(r"korjaus|korjus|eikun|ei kun|rättelse|rattelse|correct|sorry|siis|förlåt|forlat", c)
        site = "delivery" if DELIVERY.search(c) else "pickup" if PICKUP.search(c) else None
        if site is None and fix and last:
            site = last          # "..., eikun klo 14.30" in its own clause
        elif site is None:
            continue
        fr = FI_RANGE.search(c)
        r = None if fr else RANGE.search(c)
        if fr:
            opens, closes = clock(fr.group(1), None, None), clock(fr.group(2), fr.group(3), None)
        elif not r:
            # one time: a deadline at the destination, or a ready time, is not a closing time
            if not SHUT.search(c) and not (fix and last):
                last = None
                continue
            if DEADLINE.search(c) and ARRIVE.search(c) and not re.search(r"kiinni|clos|stäng|stang|ketään|nobody|asti|saakka|until|sulke", c):
                last = None
                continue
            if re.search(r"no pickup|before that|maksu|payment|betal", c):
                last = None
                continue
            if READY.search(c) and not re.search(r"kiinni|clos|stäng|stang|ketään|nobody|asti|saakka|until|sulke|ennen|before|ei enää|ingen|\bby\b", c):
                last = None
                continue
            opens, closes = None, last_time(c)
        else:
            g = r.groups()
            if g[6] is not None:   # "9 am-noon"
                opens, closes = clock(g[6], g[7], g[8]), 720
            else:
                closes = 720 if g[5] == "noon" else clock(g[3], g[4], g[5])
                opens = clock(g[0], g[1], g[2] or ("am" if g[5] == "pm" and int(g[0]) > int(g[3]) else g[5] if g[5] == "pm" and int(g[0]) < int(g[3]) and int(g[0]) < 8 else None))
            if fix:
                closes = last_time(c[r.end():]) or closes
        stated = statedD if site == "delivery" else statedP
        if stated is None or closes is None:
            continue
        key = "delivery" if site == "delivery" else "pickup"
        out[key + "Closes"] = closes if closes < stated["closes"] else None
        if opens is not None:
            out[key + "Opens"] = opens if opens > stated["opens"] else None
        last = site
    return out


if __name__ == "__main__":
    S = collections.defaultdict(collections.Counter)
    bad = collections.defaultdict(list)
    for line in open("runs/notes/labelled.jsonl"):
        r = json.loads(line)
        t, cls = r["truth"], r["cls"]
        h = readHours(r["note"], r["pHours"], r["dHours"])
        wantP = (t["pickupHours"]["opens"], t["pickupHours"]["closes"]) if t["pickupHours"] else None
        wantD = (t["deliveryHours"]["opens"], t["deliveryHours"]["closes"]) if t["deliveryHours"] else None
        gotP = (h["pickupOpens"] or r["pHours"]["opens"], h["pickupCloses"] or r["pHours"]["closes"]) if r["pHours"] else None
        gotD = (h["deliveryOpens"] or r["dHours"]["opens"], h["deliveryCloses"] or r["dHours"]["closes"]) if r["dHours"] else None
        ok = gotP == wantP and gotD == wantD
        closeOk = (gotP is None or gotP[1] == wantP[1]) and (gotD is None or gotD[1] == wantD[1])
        s = S[cls]
        s["n"] += 1
        s["ok"] += ok
        s["closeOk"] += closeOk
        if not ok and len(bad[cls]) < 4000:
            bad[cls].append((r["note"], gotP, wantP, gotD, wantD))
    tot = collections.Counter()
    for cls, s in sorted(S.items(), key=lambda kv: -kv[1]["n"]):
        print(f"{cls:15} {s['n']:7d} hours right {100*s['ok']/s['n']:6.2f}%   closing time right {100*s['closeOk']/s['n']:6.2f}%")
        tot.update(s)
    print(f"{'all notes':15} {tot['n']:7d} hours right {100*tot['ok']/tot['n']:6.2f}%   closing time right {100*tot['closeOk']/tot['n']:6.2f}%")
    if "-v" in sys.argv:
        import random
        random.seed(1)
        f = lambda v: None if v is None else f"{v[0]/60:g}-{v[1]/60:g}"
        for cls, rows in bad.items():
            print("\n==", cls, len(rows))
            for note, gp, wp, gd, wd in random.sample(rows, min(14, len(rows))):
                print(f"  {note!r}\n     pickup got {f(gp)} want {f(wp)} | delivery got {f(gd)} want {f(wd)}")
