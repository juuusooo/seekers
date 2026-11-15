"""Ranking gate: does the local world rank changes like the server?

    /root/system/venv/bin/python sim/rankgate.py run      plays every server-measured m1 variant on the local world
    /root/system/venv/bin/python sim/rankgate.py report   compares server and local differences, pair by pair

Server rows: runs/bench.jsonl, kit-max, variants "m1 <label>", exact config in each row's `overrides`.
Pairs: each label against its base on the same seeds (B4 ... vs B4, C ... vs C base, T... vs typ100, others vs base).
Local runs use the kit-max engine (all research knobs), variant "rg <label>" in runs/sim_cal.jsonl.
"""

import json
import statistics as st
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import os
ROOT = Path(__file__).resolve().parents[2]
SIMP = os.environ.get("SIMP", "")
RG = os.environ.get("RG", "rg")
SKIP = (
    "model",
    "dbg",
    "smoke",
    "verify",
    "lead24 ",
    "lead36",
)  # model swaps need another model file; lead24/36 crashed on the server
srv = defaultdict(dict)
cfg = {}
for l in open(ROOT / "runs/bench.jsonl"):
    try:
        r = json.loads(l)
    except ValueError:
        continue
    if r.get("kit") != "kit-max" or not str(r.get("variant", "")).startswith("m1 "):
        continue
    lab = r["variant"][3:]
    if any(s.strip() in lab for s in SKIP) or lab in ("lead24", "lead36"):
        continue
    srv[lab][r["seed"]] = r
    cfg.setdefault(lab, r.get("overrides") or {})


def base_of(lab):
    if lab.startswith("B4 "):
        return "B4"
    if lab.startswith("C ") and lab != "C base":
        return "C base"
    if lab.startswith("T") and lab != "typ100":
        return "typ100"
    return None if lab in ("base", "B4", "C base", "typ100") else "base"


pairs = [(base_of(l), l) for l in srv if base_of(l) and base_of(l) in srv]


def sim_rows(lab):
    out = {}
    for l in open(ROOT / "runs/sim_cal.jsonl"):
        if f'"{RG} ' not in l:
            continue
        r = json.loads(l)
        if r.get("variant") == f"{RG} {lab}":
            out[r["seed"]] = r
    return out


if sys.argv[1] == "run":
    need = sorted({p[0] for p in pairs} | {p[1] for p in pairs})
    for lab in need:
        have = sim_rows(lab)
        seeds = sorted(s for s in srv[lab] if s not in have)
        if not seeds:
            continue
        sset = ",".join(f"{k}={v}" for k, v in cfg[lab].items())
        args = [
            "bash",
            "sim/sweep.sh",
            ",".join(seeds),
            f"{RG} {lab}",
        ] + (["--set", sset] if sset else []) + (["--sim", SIMP] if SIMP else [])
        subprocess.run(args, cwd=ROOT, capture_output=True, env={**os.environ, "RUN": "cal/run_rg", "P": "24"})
        print("played", lab, len(seeds), flush=True)
else:
    out = []
    for b, v in pairs:
        sb, sv = sim_rows(b), sim_rows(v)
        k = sorted(set(srv[b]) & set(srv[v]) & set(sb) & set(sv))
        if len(k) < 10:
            continue
        ds = [srv[v][s]["margin"] - srv[b][s]["margin"] for s in k]
        dl = [sv[s]["margin"] - sb[s]["margin"] for s in k]
        se = st.stdev(ds) / len(ds) ** 0.5
        out.append(
            (v, b, len(k), st.mean(ds), se, st.mean(dl), st.stdev(dl) / len(dl) ** 0.5)
        )
    out.sort(key=lambda x: x[3])
    print(
        f"{'variant':24s} {'base':8s} {'n':>3s} {'server':>8s} {'± SE':>5s} {'local':>8s} {'± SE':>5s}  agree"
    )
    for v, b, n, d, se, l, sel in out:
        big = abs(d) > 300 and abs(d) > 2 * se
        ok = "yes" if (d > 0) == (l > 0) else "NO"
        print(
            f"{v:24s} {b:8s} {n:3d} {d:+8.0f} {se:5.0f} {l:+8.0f} {sel:5.0f}  {ok if big else '(' + ok + ')'}"
        )
    S = np.array([o[3] for o in out])
    L = np.array([o[5] for o in out])
    big = [o for o in out if abs(o[3]) > 300 and abs(o[3]) > 2 * o[4]]
    agree = sum((o[3] > 0) == (o[5] > 0) for o in big)
    rs = np.corrcoef(np.argsort(np.argsort(S)), np.argsort(np.argsort(L)))[0, 1]
    print(
        f"\npairs {len(out)}; clear server effects (>300 and >2 SE): {len(big)}, same sign locally: {agree}/{len(big)}"
    )
    print(
        f"Pearson corr of differences {np.corrcoef(S, L)[0, 1]:.2f}, Spearman rank corr {rs:.2f}"
    )
    print(
        f"mean |local - server| {np.mean(np.abs(L - S)):.0f} a week; on clear effects {np.mean([abs(o[5] - o[3]) for o in big]):.0f}"
    )
