"""Fit typ.json: ln(typical) = lane + privP + privD + prem + elec (one-leg requests); trade = mean ln(typ / sum of leg predictions)."""
import json, sys, numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
one = [r for r in rows if len(r["legs"]) == 1]
lanes = sorted({f"{r['legs'][0][0]}>{r['legs'][0][1]}" for r in one})
L = {l: i for i, l in enumerate(lanes)}
idx = np.array([L[f"{r['legs'][0][0]}>{r['legs'][0][1]}"] for r in one])
E = np.array([[r["legs"][0][2], r["legs"][0][3], r["legs"][0][4], r["legs"][0][5]] for r in one], float)
y = np.log([r["typ"] for r in one])
b = np.zeros(4)
for _ in range(40):
    s = np.bincount(idx, y - E @ b, len(lanes)); c = np.bincount(idx, None, len(lanes)); lane = s / np.maximum(c, 1)
    b, *_ = np.linalg.lstsq(E, y - lane[idx], rcond=None)
res = y - lane[idx] - E @ b
print(f"one-leg n={len(one)} lanes={len(lanes)} resSD={res.std():.4f} b(privP,privD,prem,elec)={np.round(b,4)} median n/lane={np.median(c):.0f}")
two = [r for r in rows if len(r["legs"]) == 2 and all(f"{l[0]}>{l[1]}" in L for l in r["legs"])]
pred = lambda l: np.exp(lane[L[f"{l[0]}>{l[1]}"]] + b[0] * l[2] + b[1] * l[3] + b[2] * l[4] + b[3] * l[5])
t = np.array([np.log(r["typ"] / sum(pred(l) for l in r["legs"])) for r in two])
print(f"two-leg n={len(two)} trade={t.mean():.4f} SD={t.std():.4f}")
json.dump({"lane": {k: round(float(lane[i]), 5) for k, i in L.items()}, "n": {k: int(c[i]) for k, i in L.items()}, "privP": float(b[0]), "privD": float(b[1]), "prem": float(b[2]), "elec": float(b[3]), "trade": float(t.mean())}, open(sys.argv[2], "w"))
