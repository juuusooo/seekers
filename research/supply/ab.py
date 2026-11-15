"""Plays variants on the Rust copy of the local world and prints paired differences against the first variant.
  python ab.py SEEDS VARIANTS_FILE [--sim k=v,..] [--tag name]
VARIANTS_FILE: one 'name k=v,k=v' per line; the first line is the base. Rows are kept in out/<tag>.jsonl."""
import json, subprocess, sys, os, math, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.environ.get("SIMB", r"C:/Users/Juho/AppData/Local/Temp/claude/59aa90977088af63/13f7863a-fac9-44fc-a0b1-eb7fe6f109cb/scratchpad/target/release/sim-experimental.exe")
ROOT = os.path.join(HERE, "..", "..", "sim-experimental")
PEN = 3000.0  # smooth score: EUR a week per point of on time under 93%

def play(seeds, variants_file, sim="", tag="tmp"):
    out = os.path.join(HERE, "out", tag + ".jsonl")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out): os.remove(out)
    cmd = [B, "--root", ROOT, "--seeds", seeds, "--sets", variants_file, "--quiet", "--out", out]
    if sim: cmd += ["--sim", sim]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise SystemExit(r.stderr[-2000:])
    rows = {}
    for l in open(out):
        x = json.loads(l); rows.setdefault(x["variant"], {})[x["seed"]] = x
    return rows

def smooth(x): return x["margin"] - PEN * max(0.0, 93.0 - 100 * x["onTime"])

def table(rows, base, names=None):
    b = rows[base]; res = []
    for name in (names or rows):
        v = rows[name]; seeds = [s for s in b if s in v]
        d = [v[s]["margin"] - b[s]["margin"] for s in seeds]
        ds = [smooth(v[s]) - smooth(b[s]) for s in seeds]
        dz = [(v[s]["margin"] if v[s]["ranked"] else 0) - (b[s]["margin"] if b[s]["ranked"] else 0) for s in seeds]
        n = len(seeds); se = lambda a: (st.stdev(a) / math.sqrt(n)) if n > 1 else 0
        res.append(dict(name=name, n=n, margin=st.mean(v[s]["margin"] for s in seeds), diff=st.mean(d), se=se(d), better=sum(x > 0 for x in d), worse=sum(x < 0 for x in d),
                        sdiff=st.mean(ds), sse=se(ds), zdiff=st.mean(dz), orders=st.mean(v[s]["won"] for s in seeds), ranked=sum(v[s]["ranked"] for s in seeds),
                        ontime=100 * st.mean(v[s]["onTime"] for s in seeds), worst=100 * min(v[s]["onTime"] for s in seeds), set=v[seeds[0]]["set"]))
    return res

def show(res):
    print(f"{'variant':34} {'n':>3} {'margin':>7} {'diff':>6} {'±se':>5} {'b/w':>7} {'smooth':>7} {'±se':>5} {'scored':>7} {'orders':>6} {'rank':>4} {'onT%':>5} {'worst':>5}")
    for r in res:
        print(f"{r['name'][:34]:34} {r['n']:3d} {r['margin']:7.0f} {r['diff']:+6.0f} {r['se']:5.0f} {r['better']:3d}/{r['worse']:<3d} {r['sdiff']:+7.0f} {r['sse']:5.0f} {r['zdiff']:+7.0f} {r['orders']:6.1f} {r['ranked']:4d} {r['ontime']:5.1f} {r['worst']:5.1f}")

if __name__ == "__main__":
    a = sys.argv[1:]; sim = a[a.index("--sim") + 1] if "--sim" in a else ""; tag = a[a.index("--tag") + 1] if "--tag" in a else "tmp"
    rows = play(a[0], a[1], sim, tag); show(table(rows, next(iter(rows))))
