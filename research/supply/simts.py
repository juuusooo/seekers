"""Local tests on the CURRENT best model: plays a variants file with a kit (default kit-s14 = BEST14 + test knobs)
on the TypeScript local world, seeds spread over processes, and prints paired differences against the first variant.
  python simts.py VARIANTS_FILE [SEEDS] [--kit kit-s14] [--worlds v4,T] [--procs 10]
Worlds: v4 (the sim as calibrated), T (workPow=3.2, tight), T2 (scarce). Slower than the Rust copy (about 0.7 s a
week and process), but it is the real algo.ts: BEST14 with its outage belief, fee tilt, late fees and lane level."""
import json, os, subprocess, sys
from ab import table, show
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..", "..")
WORLDS = {"v4": "", "T": "workPow=3.2", "T2": "workBase=0.07,workGig=0.1,workPow=2"}
ALL = [f"{p}-{i}" for p, n in (("m", 48), ("h", 48), ("k", 64), ("rd", 48), ("sv", 48)) for i in range(1, n + 1)]

def expand(text):
    out = []
    for s in text.split(","):
        pre, _, rng = s.rpartition("-")
        if ".." in rng: a, b = rng.split(".."); out += [f"{pre}-{i}" for i in range(int(a), int(b) + 1)]
        elif s: out.append(s)
    return out

def play(vfile, seeds, kit="kit-s14", world="v4", procs=10, tag="ts"):
    out = os.path.join(HERE, "out", f"{tag}_{world}.jsonl")
    vfile = os.path.abspath(vfile)
    if os.path.exists(out): os.remove(out)
    seeds = [s for s in seeds if os.path.exists(os.path.join(ROOT, "sim", "data", s + ".json"))]
    jobs = []
    for g in range(procs):
        part = seeds[g::procs]
        if not part: continue
        cmd = ["node", "--disable-warning=ExperimentalWarning", os.path.join(HERE, "simts.ts"), "--kit", kit, "--seeds", ",".join(part), "--variants", vfile, "--out", out + f".{g}"]
        if WORLDS[world]: cmd += ["--sim", WORLDS[world]]
        jobs.append((subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True), out + f".{g}"))
    rows = {}
    for p, f in jobs:
        _, err = p.communicate()
        if p.returncode: raise SystemExit(err[-1500:])
        if os.path.exists(f):
            for l in open(f):
                x = json.loads(l); rows.setdefault(x["variant"], {})[x["seed"]] = x
            os.remove(f)
    json.dump(rows, open(out, "w"))
    return rows

if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    seeds = expand(pos[1]) if len(pos) > 1 else ALL
    for world in opt("--worlds", "v4,T").split(","):
        rows = play(pos[0], seeds, opt("--kit", "kit-s14"), world, int(opt("--procs", "10")))
        print(f"== {opt('--kit', 'kit-s14')}, world {world}, {len(next(iter(rows.values())))} weeks"); show(table(rows, next(iter(rows))))
