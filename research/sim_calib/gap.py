"""Sim vs server on the sv seeds, per config.  python research/sim_calib/gap.py TAG [SEEDLO SEEDHI]"""
import json, statistics as st, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
tag = sys.argv[1]
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1, 48)
srv = json.load(open(R / "research/sim_calib/sv_server.json"))
sim = {}
for l in open(R / "runs/sim_cal.jsonl"):
    if f'"{tag} ' in l:
        r = json.loads(l)
        sim[(r["variant"].split(" ", 1)[1], r["seed"])] = r
seeds = [f"sv-{i}" for i in range(lo, hi + 1)]
KEYS = ["margin", "won", "onTime", "under90", "L_revenue", "L_driver_fee", "L_late_refund", "L_failed_visit", "L_undelivered_penalty", "feePerOrder", "revPerOrder", "bookings", "drops", "bookers", "warnings"]
def val(r, k):
    s = r["stats"]
    if k in ("margin", "won", "onTime"): return r[k]
    if k == "under90": return 1.0 * (r["onTime"] < 0.9)
    if k == "feePerOrder": return -s.get("L_driver_fee", 0) / max(1, r["won"])
    if k == "revPerOrder": return s.get("L_revenue", 0) / max(1, r["won"])
    return s.get(k, 0)
tab = {}
for cfg in ("best5", "fee", "sim1"):
    ks = [s for s in seeds if (cfg, s) in sim and f"sv1 {cfg}|{s}" in srv]
    tab[cfg] = {k: (st.mean(val(sim[(cfg, s)], k) for s in ks), st.mean(val(srv[f"sv1 {cfg}|{s}"], k) for s in ks)) for k in KEYS}
    tab[cfg]["n"] = len(ks)
    if len(ks) > 2:
        import numpy as np
        tab[cfg]["corr"] = float(np.corrcoef([sim[(cfg, s)]["margin"] for s in ks], [srv[f"sv1 {cfg}|{s}"]["margin"] for s in ks])[0, 1])
print(f"{tag} sv-{lo}..{hi}  n={[tab[c]['n'] for c in tab]}  week corr {[round(tab[c].get('corr',0),2) for c in tab]}")
print(f"{'':22s}" + "".join(f"{c+' sim':>11s}{'server':>9s}" for c in tab) + f"{'sim1-best5 sim':>16s}{'server':>9s}")
for k in KEYS:
    f = (lambda x: f"{x:,.3f}") if k in ("onTime", "under90") else (lambda x: f"{x:,.0f}") if abs(tab['best5'][k][1]) > 200 else (lambda x: f"{x:,.1f}")
    print(f"{k:22s}" + "".join(f"{f(tab[c][k][0]):>11s}{f(tab[c][k][1]):>9s}" for c in tab) + f"{f(tab['sim1'][k][0]-tab['best5'][k][0]):>16s}{f(tab['sim1'][k][1]-tab['best5'][k][1]):>9s}")
