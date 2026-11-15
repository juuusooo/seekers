"""Two-load calibration of the local world's driver side (sim/cal) against the sv1 server weeks.

    /root/system/venv/bin/python research/sim_calib/calib.py NAME ITER        (from Bahn-Spread/)

Fit seeds sv-1..24, two configs on the same weeks: BEST5 (low load) and kit-sim1 (+23% orders). Targets per config are the
server means on the same seeds (research/sim_calib/sv_server.json). Held out, never read here: sv-25..48.
Search: (1+4) evolution strategy. State: runs/lab/cal_NAME.json (resumable).
"""
import json, math, os, random, statistics as st, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME, ITER = sys.argv[1], int(sys.argv[2])
LO, HI = 1, 24
seeds = [f"sv-{i}" for i in range(LO, HI + 1)]
STATE = ROOT / f"runs/lab/cal_{NAME}.json"
OUT = ROOT / "runs/sim_cal.jsonl"
SRV = json.load(open(ROOT / "research/sim_calib/sv_server.json"))
CFG = {"best5": "sim/cal/kit/algo_best5.ts", "sim1": "sim/cal/kit/algo_sim1.ts"}

PARAMS = {  # name: (v4 value, low, high, integer)
    "F": (1.763, 1.0, 3.0, 0), "outMu": (2569.57, 100.0, 8000.0, 0), "outSd": (1.0346, 0.2, 3.0, 0),
    "wait": (0.1647, 0.0, 2.0, 0), "workBase": (0.0866, 0.005, 0.3, 0), "workGig": (0.1199, 0.02, 0.3, 0),
    "workSat": (0.35, 0.05, 1.0, 0), "lookPerH": (0.236, 0.05, 1.0, 0), "dropBase": (0.0133, 0.0, 0.2, 0),
    "dropThin": (0.2263, 0.0, 1.0, 0), "dropHold": (0.1424, 0.0, 0.8, 0), "knowWeek": (0.4787, 0.0, 1.0, 0),
    "homeMu": (16.141, 13.0, 23.0, 0), "homeSd": (0.9528, 0.3, 4.0, 0), "maxDriveMu": (10.8543, 1.5, 12.0, 0),
    "maxDriveSd": (0.8473, 0.1, 1.0, 0), "notifyP": (0.8065, 0.1, 1.0, 0), "notifyDelay": (92.706, 1.0, 180.0, 0),
    "maxGigs": (2, 1, 5, 1), "busyMin": (600, 60, 900, 0), "evening": (0.25, 0.0, 1.0, 0),
    "dealerShift": (-0.05, -0.4, 0.4, 0), "choiceAlpha": (10, 2, 40, 0), "workPow": (1, 0.5, 4, 0),
}
ADD = ("wait", "dropBase", "dropThin", "dropHold", "knowWeek", "dealerShift", "evening")


def feats(r):
    s, won = r["stats"], max(1, r["won"])
    rev = max(1.0, s.get("L_revenue", 0))
    g = lambda k: s.get(k, 0)
    return {
        "margin": r["margin"], "won": r["won"], "onTime": r["onTime"], "under90": 1.0 * (r["onTime"] < 0.9),
        "feeShare": -g("L_driver_fee") / rev, "lateShare": -g("L_late_refund") / rev,
        "undShare": -g("L_undelivered_penalty") / rev, "revPer": rev / won,
        "drops": g("drops") / max(1, g("bookings")), "warn": g("warnings") / won, "bookers": g("bookers"),
        "sameShare": g("n_same_day") / won, "lateSame": g("late_same_day") / max(1, g("n_same_day")),
        "lateNext": g("late_next_day") / max(1, g("n_next_day")),
    }


# scale of one "unit of error" per feature; rel = relative to the server mean
SCALE = {"margin": ("rel", 0.025), "won": ("rel", 0.03), "onTime": ("abs", 0.007), "under90": ("abs", 0.08),
         "feeShare": ("abs", 0.012), "lateShare": ("abs", 0.004), "undShare": ("abs", 0.006), "revPer": ("rel", 0.03),
         "drops": ("abs", 0.03), "warn": ("abs", 0.03), "bookers": ("rel", 0.06), "sameShare": ("abs", 0.05),
         "lateSame": ("abs", 0.015), "lateNext": ("abs", 0.012)}
TGT = {c: {k: st.mean(feats(SRV[f"sv1 {c}|{s}"])[k] for s in seeds) for k in SCALE} for c in CFG}
OLD = {"atOpen": 0.372, "book60": 0.394, "book360": 0.759}  # booking speed on the base config (journals, v3 targets)


def run(variant, p):
    sim = ",".join(f"{k}={v:.6g}" for k, v in p.items())
    for c, algo in CFG.items():
        subprocess.run(["bash", "sim/sweep.sh", f"sv-{LO}..{HI}", f"{variant} {c}", "--algo", algo, "--sim", sim], cwd=ROOT, capture_output=True, env={**os.environ, "RUN": "cal/run", "P": "24"})
    rows = {c: {} for c in CFG}
    for l in open(OUT):
        if f'"{variant} ' in l:
            r = json.loads(l)
            c = r["variant"].rsplit(" ", 1)[1]
            if r["variant"] == f"{variant} {c}": rows[c][r["seed"]] = r
    return rows


def loss(rows):
    parts, info = {}, {}
    for c in CFG:
        if len(rows[c]) < len(seeds): return 1e9, {}
        f = {s: feats(rows[c][s]) for s in seeds}
        for k, (kind, sc) in SCALE.items():
            m, t = st.mean(f[s][k] for s in seeds), TGT[c][k]
            e = (m / t - 1) if kind == "rel" else (m - t)
            parts[f"{c}.{k}"] = (e / sc) ** 2
            info[f"{c}.{k}"] = round(m, 4 if abs(m) < 5 else 1)
        per = st.mean(abs(rows[c][s]["margin"] - SRV[f"sv1 {c}|{s}"]["margin"]) for s in seeds) / TGT[c]["margin"]
        parts[f"{c}.per"] = (per / 0.12) ** 2
    # the difference between the loads is what the search will exploit: weigh it on its own
    dm = st.mean(rows["sim1"][s]["margin"] - rows["best5"][s]["margin"] for s in seeds)
    dt = st.mean(SRV[f"sv1 sim1|{s}"]["margin"] - SRV[f"sv1 best5|{s}"]["margin"] for s in seeds)
    parts["diff.margin"] = ((dm - dt) / 250) ** 2
    do = st.mean(rows["sim1"][s]["onTime"] - rows["best5"][s]["onTime"] for s in seeds)
    dto = st.mean(SRV[f"sv1 sim1|{s}"]["onTime"] - SRV[f"sv1 best5|{s}"]["onTime"] for s in seeds)
    parts["diff.onTime"] = ((do - dto) / 0.007) ** 2
    S = lambda k: st.mean(rows["best5"][s]["stats"].get(k, 0) for s in seeds)
    for k, t in OLD.items(): parts["old." + k] = ((S("bookAtOpen" if k == "atOpen" else k) / max(1, S("bookings")) - t) / 0.07) ** 2
    info["diff.margin"], info["diff.onTime"] = round(dm), round(do, 4)
    return sum(parts.values()), {"info": info, "top": sorted(((round(v, 1), k) for k, v in parts.items()), reverse=True)[:6]}


if sys.argv[2:] and len(sys.argv) > 3 and sys.argv[3] == "targets":
    print(json.dumps(TGT, indent=1)); sys.exit()
START = json.load(open(os.environ["START"]))["best"] if os.environ.get("START") else {}
state = json.loads(STATE.read_text()) if STATE.exists() else {"best": {k: START.get(k, v[0]) for k, v in PARAMS.items()}, "loss": None, "it": 0, "log": []}
if os.environ.get("EVAL") is not None:
    for i, ov in enumerate(os.environ["EVAL"].split(";")):
        c = dict(state["best"])
        for kv in filter(None, ov.split(",")):
            k, v = kv.split("="); c[k] = float(v)
        L, info = loss(run(f"{NAME}e{i}", c))
        I = info["info"]
        print(f"{L:7.1f} | {ov} | dm {I['diff.margin']} dOT {I['diff.onTime']} | b5 m {I['best5.margin']:.0f} ot {I['best5.onTime']} bookers {I['best5.bookers']} drops {I['best5.drops']} warn {I['best5.warn']} | s1 m {I['sim1.margin']:.0f} ot {I['sim1.onTime']} bookers {I['sim1.bookers']} warn {I['sim1.warn']} u90 {I['sim1.under90']} | {info['top'][:3]}", flush=True)
    sys.exit()
if state["loss"] is None:
    state["loss"], info = loss(run(f"{NAME}0", state["best"]))
    print("start", round(state["loss"], 1), json.dumps(info), flush=True)
    state["start"] = {"loss": state["loss"], "info": info}
rng = random.Random(11 + state["it"])
while state["it"] < ITER:
    state["it"] += 1
    sigma = 0.25 if state["it"] < 60 else 0.12
    best_c = None
    for j in range(4):
        c = {}
        for k, (s0, lo, hi, integer) in PARAMS.items():
            v = state["best"][k]
            if rng.random() < 0.35:
                if integer: v = v + rng.choice((-1, 1))
                elif k in ADD and rng.random() < 0.3: v += rng.gauss(0, 0.05)
                else: v = v * math.exp(rng.gauss(0, sigma))
            c[k] = min(hi, max(lo, v))
        L, info = loss(run(f"{NAME}{state['it']}_{j}", c))
        if best_c is None or L < best_c[0]: best_c = (L, c, info)
    L, c, info = best_c
    state["log"].append({"it": state["it"], "loss": L})
    if L < state["loss"]:
        state["loss"], state["best"], state["bestInfo"] = L, c, info
        print(f"it {state['it']} NEW {L:.1f} {json.dumps(info['top'])} dm {info['info']['diff.margin']} {json.dumps({k: round(v, 4) for k, v in c.items()})}", flush=True)
    else:
        print(f"it {state['it']} {L:.1f} (best {state['loss']:.1f})", flush=True)
    STATE.write_text(json.dumps(state, indent=1))
print("BEST", json.dumps(state["best"]))
