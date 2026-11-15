//! Inputs written by prep.ts: static.json (map, models) and data/<seed>.json (one week's world).
use serde::Deserialize;

pub const HOUR: f64 = 60.0;
pub const DAY: f64 = 1440.0;
/// The next Wednesday 22:00.
pub const END: f64 = 9.0 * DAY + 22.0 * HOUR;

#[derive(Deserialize, Clone, Copy, Debug)]
pub struct Hours {
    pub opens: f64,
    pub closes: f64,
    /// bit d = open on weekday d (0 = Monday)
    pub wd: u8,
    pub sat: Option<[f64; 2]>,
}

#[derive(Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Leg {
    pub premium: bool,
    pub electric: bool,
    pub charge: Option<f64>,
    pub p: usize,
    pub p_priv: bool,
    pub p_from: f64,
    pub p_to: f64,
    pub p_hours: Option<Hours>,
    pub d: usize,
    pub d_priv: bool,
    pub d_from: f64,
    pub d_to: f64,
    pub d_hours: Option<Hours>,
}

#[derive(Deserialize, Clone, Copy, Debug)]
pub struct Opt {
    pub kind: usize,
    pub deadline: f64,
    pub list: f64,
}

#[derive(Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Truth {
    pub ready_at: f64,
    pub released_at: Option<f64>,
    pub pickup_hours: Option<Hours>,
    pub delivery_hours: Option<Hours>,
    pub manual_gearbox: bool,
    pub needs_plates: bool,
    pub note_deadline: Option<f64>,
}

#[derive(Deserialize, Clone, Copy, Debug)]
pub struct Noted {
    pub pickup: Option<Hours>,
    pub delivery: Option<Hours>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct WinParts {
    pub delivery: bool,
    pub ranges: Vec<[f64; 2]>,
    /// [minute of the day, 1 = after / 2 = before]
    pub clocks: Vec<[f64; 2]>,
}

#[derive(Deserialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Req {
    pub id: String,
    pub dealer: usize,
    pub dealer_num: f64,
    pub arrived_at: f64,
    pub respond_by: f64,
    pub ref_fee: f64,
    pub typ_raw: Option<f64>,
    pub legs: Vec<Leg>,
    pub options: Vec<Opt>,
    pub has_note: bool,
    pub plates: bool,
    pub manual: bool,
    pub ready_from: Option<f64>,
    pub deliver_by: Option<f64>,
    pub noted: Option<Noted>,
    pub win: Option<WinParts>,
    pub typ_pred: Option<f64>,
    pub typ_min_n: Option<f64>,
    pub truth: Option<Vec<Option<Truth>>>,
    pub choice: [f64; 3],
}

#[derive(Deserialize, Clone, Debug)]
pub struct Forecast {
    pub at: f64,
    pub from: f64,
    pub to: f64,
    pub places: Vec<usize>,
}

#[derive(Deserialize, Clone, Debug)]
pub struct RosterDriver {
    pub id: String,
    pub home: usize,
    pub rating: f64,
    pub manual: bool,
    pub completed: f64,
}

#[derive(Deserialize, Debug)]
#[serde(rename_all = "camelCase")]
pub struct Seed {
    pub seed: String,
    pub requests: Vec<Req>,
    pub forecasts: Vec<Forecast>,
    pub roster: Vec<RosterDriver>,
    pub off_level: f64,
    pub off_day: Vec<(f64, f64)>,
    pub off_place: Vec<(f64, usize, f64)>,
}

#[derive(Deserialize, Debug)]
pub struct Book {
    pub intercept: f64,
    pub c: Vec<f64>,
    pub r: f64,
    pub r_hi1: f64,
    pub r_hi2: f64,
}

#[derive(Deserialize, Debug)]
#[allow(non_snake_case)]
pub struct Win {
    pub intercept: f64,
    pub pickup: Vec<f64>,
    pub delivery: Vec<f64>,
    pub ln_m: f64,
    pub driveH: f64,
    pub tradeIn: f64,
    pub privD: f64,
    pub sameDay: f64,
    pub nOpt: f64,
    pub trust: f64,
    pub lates: f64,
    pub worldSd: f64,
}

#[derive(Deserialize, Debug)]
pub struct Price {
    pub c: f64,
    pub b: Vec<f64>,
    pub lane: Vec<f64>,
    pub pick: Vec<f64>,
    pub del: Vec<f64>,
    pub hour: Vec<f64>,
    pub dealer: Vec<f64>,
}

#[derive(Deserialize, Debug)]
pub struct Trees {
    pub base: f64,
    pub f: Vec<i32>,
    pub t: Vec<f64>,
    pub l: Vec<u32>,
    pub r: Vec<u32>,
    pub roots: Vec<u32>,
}

#[derive(Deserialize, Debug)]
pub struct Cost {
    pub mean: Trees,
    pub q80: Trees,
}

#[derive(Deserialize, Debug)]
pub struct Static {
    pub places: Vec<String>,
    pub lat: Vec<f64>,
    pub lon: Vec<f64>,
    pub road: Vec<f64>,
    pub km: Vec<f64>,
    pub book: Book,
    pub win: Win,
    pub price: Price,
    pub cost: Cost,
    #[serde(skip)]
    pub fast_mean: FastTrees,
    #[serde(skip)]
    pub fast_q80: FastTrees,
    #[serde(skip)]
    pub bin_mean: BinTrees,
    #[serde(skip)]
    pub bin_q80: BinTrees,
}

impl Static {
    #[inline]
    pub fn np(&self) -> usize {
        self.places.len()
    }
    #[inline]
    pub fn road(&self, a: usize, b: usize) -> f64 {
        self.road[a * self.places.len() + b]
    }
    #[inline]
    pub fn km(&self, a: usize, b: usize) -> f64 {
        self.km[a * self.places.len() + b]
    }
}

// ── JavaScript number semantics ──
/// Math.round: halves go up.
#[inline]
pub fn jround(x: f64) -> f64 {
    (x + 0.5).floor()
}

// ── deterministic randomness: the FNV pass (resumable) and the finalizer of sim/world.ts ──
pub const FNV0: u32 = 2166136261;
#[inline]
pub fn fnv(s: &str, mut h: u32) -> u32 {
    for &c in s.as_bytes() {
        h = (h ^ c as u32).wrapping_mul(16777619);
    }
    h
}
/// Continues the pass with the decimal digits of a non-negative integer.
#[inline]
pub fn fnv_int(n: u64, mut h: u32) -> u32 {
    let mut buf = [0u8; 20];
    let mut i = 20;
    let mut n = n;
    loop {
        i -= 1;
        buf[i] = b'0' + (n % 10) as u8;
        n /= 10;
        if n == 0 {
            break;
        }
    }
    for &c in &buf[i..] {
        h = (h ^ c as u32).wrapping_mul(16777619);
    }
    h
}
#[inline]
pub fn fin(mut h: u32) -> f64 {
    h ^= h >> 15;
    h = h.wrapping_mul(2246822507);
    h ^= h >> 13;
    h = h.wrapping_mul(3266489909);
    h ^= h >> 16;
    h as f64 / 4294967296.0
}

// ── opening hours ──
#[inline]
pub fn is_open(h: &Option<Hours>, t: f64) -> bool {
    let Some(h) = h else { return true };
    let wd = (t / DAY).floor() % 7.0;
    let m = t % DAY;
    if wd == 5.0 {
        return match h.sat {
            Some(s) => m >= s[0] && m < s[1],
            None => false,
        };
    }
    wd >= 0.0 && (h.wd >> (wd as u32)) & 1 == 1 && m >= h.opens && m < h.closes
}
/// The first of t and the following multiples of 15 minutes at which the site is open (672 candidates at most).
pub fn next_open(h: &Option<Hours>, t: f64) -> f64 {
    let Some(hh) = h else { return t };
    if is_open(h, t) {
        return t;
    }
    let c1 = (t / 15.0 + 1.0).floor() * 15.0;
    let last_c = c1 + 15.0 * 670.0;
    let mut day = (c1 / DAY).floor();
    while day * DAY <= last_c {
        let ds = day * DAY;
        let wd = day % 7.0;
        let span = if wd == 5.0 {
            hh.sat.map(|s| (s[0], s[1]))
        } else if wd >= 0.0 && (hh.wd >> (wd as u32)) & 1 == 1 {
            Some((hh.opens, hh.closes))
        } else {
            None
        };
        if let Some((o, c)) = span {
            let cand = (c1.max(ds).max(ds + o) / 15.0).ceil() * 15.0;
            if cand - ds < c && cand < ds + DAY && cand <= last_c {
                return cand;
            }
        }
        day += 1.0;
    }
    c1 + 15.0 * 671.0
}

// ── trees laid out for side-by-side walks ──
/// A split: go to `l` if x[f] <= t, else to `l + 1`. A leaf: f = 0, t = +inf, l = itself, with one copy of itself
/// right after it (so `l + 1` is the same leaf when x[f] is NaN); `val` holds the leaf values by node.
#[derive(Clone, Copy, Debug, Default)]
pub struct FastNode { pub t: f64, pub f: u32, pub l: u32 }
#[derive(Debug, Default)]
pub struct FastTrees { pub base: f64, pub depth: usize, pub nodes: Vec<FastNode>, pub val: Vec<f64>, pub roots: Vec<u32>, pub n_features: usize }
impl FastTrees {
    pub fn build(t: &Trees) -> FastTrees {
        let mut out = FastTrees { base: t.base, depth: 0, nodes: Vec::new(), val: Vec::new(), roots: Vec::new(), n_features: 1 };
        // nodes 0 and 1: a leaf worth 0 for the unused lanes of the last group
        for _ in 0..2 { out.nodes.push(FastNode { t: f64::INFINITY, f: 0, l: 0 }); out.val.push(0.0); }
        fn leaf(out: &mut FastTrees, dst: usize, v: f64) {
            let pair = out.nodes.len() as u32;
            for _ in 0..2 { out.nodes.push(FastNode { t: f64::INFINITY, f: 0, l: pair }); out.val.push(v); }
            out.nodes[dst] = FastNode { t: f64::INFINITY, f: 0, l: pair };
            out.val[dst] = v;
        }
        fn place(t: &Trees, out: &mut FastTrees, src: usize, dst: usize, depth: usize) -> usize {
            if t.f[src] < 0 { leaf(out, dst, t.t[src]); return depth; }
            let kids = out.nodes.len();
            for _ in 0..2 { out.nodes.push(FastNode::default()); out.val.push(0.0); }
            out.nodes[dst] = FastNode { t: t.t[src], f: t.f[src] as u32, l: kids as u32 };
            out.n_features = out.n_features.max(t.f[src] as usize + 1);
            let a = place(t, out, t.l[src] as usize, kids, depth + 1);
            let b = place(t, out, t.r[src] as usize, kids + 1, depth + 1);
            a.max(b)
        }
        for &root in &t.roots {
            let dst = out.nodes.len();
            out.nodes.push(FastNode::default());
            out.val.push(0.0);
            let d = place(t, &mut out, root as usize, dst, 0);
            out.depth = out.depth.max(d);
            out.roots.push(dst as u32);
        }
        out
    }
}

// ── trees on ranks: a node asks "is the rank of x[f] among the feature's thresholds <= k" ──
/// `x[f] <= t` is the same question as `rank(x[f]) <= k`, where k is t's place among the sorted thresholds of
/// feature f and rank(x) counts the thresholds below x (NaN: all of them, so the answer is no, as with numbers).
/// A node is 4 bytes, so all trees stay in the first-level cache. A leaf has k = 255 and points at itself.
#[derive(Clone, Copy, Debug, Default)]
pub struct BinNode { pub f: u8, pub k: u8, pub l: u16 }
#[derive(Debug, Default)]
pub struct BinTrees { pub ok: bool, pub base: f64, pub depth: usize, pub thr: Vec<Vec<f64>>, pub nodes: Vec<BinNode>, pub packed: Vec<u32>, pub val: Vec<f64>, pub roots: Vec<u16> }
impl BinTrees {
    pub fn build(t: &Trees) -> BinTrees {
        let nf = t.f.iter().copied().max().unwrap_or(0).max(0) as usize + 1;
        let mut thr: Vec<Vec<f64>> = vec![Vec::new(); nf];
        for i in 0..t.f.len() { if t.f[i] >= 0 { thr[t.f[i] as usize].push(t.t[i]); } }
        for v in thr.iter_mut() { v.sort_by(|a, b| a.total_cmp(b)); v.dedup(); }
        let mut out = BinTrees { ok: nf <= 255 && thr.iter().all(|v| v.len() <= 254 && v.iter().all(|x| x.is_finite())), base: t.base, depth: 0, thr, nodes: Vec::new(), packed: Vec::new(), val: Vec::new(), roots: Vec::new() };
        if !out.ok { return out; }
        // slots 0 and 1: a leaf worth 0 for the unused lanes of the last group
        for _ in 0..2 { out.nodes.push(BinNode { f: 0, k: 255, l: 0 }); out.val.push(0.0); }
        fn place(t: &Trees, out: &mut BinTrees, src: usize, dst: usize, depth: usize) -> usize {
            if t.f[src] < 0 {
                out.nodes[dst] = BinNode { f: 0, k: 255, l: dst as u16 };
                out.val[dst] = t.t[src];
                return depth;
            }
            let kids = out.nodes.len();
            for _ in 0..2 { out.nodes.push(BinNode::default()); out.val.push(0.0); }
            let f = t.f[src] as usize;
            let k = out.thr[f].iter().position(|&x| x == t.t[src]).unwrap();
            out.nodes[dst] = BinNode { f: f as u8, k: k as u8, l: kids as u16 };
            let a = place(t, out, t.l[src] as usize, kids, depth + 1);
            let b = place(t, out, t.r[src] as usize, kids + 1, depth + 1);
            a.max(b)
        }
        for &root in &t.roots {
            let dst = out.nodes.len();
            out.nodes.push(BinNode::default());
            out.val.push(0.0);
            let d = place(t, &mut out, root as usize, dst, 0);
            out.depth = out.depth.max(d);
            out.roots.push(dst as u16);
        }
        if out.nodes.len() > 65000 { out.ok = false; }
        out.packed = out.nodes.iter().map(|n| n.f as u32 | (n.k as u32) << 8 | (n.l as u32) << 16).collect();
        out
    }
    /// The rank of x among feature f's thresholds.
    #[inline]
    pub fn rank(&self, f: usize, x: f64) -> u8 {
        let v = &self.thr[f];
        if x != x { return v.len() as u8; }
        // a plain count (no branches, compares side by side): the same number as a search in the sorted list
        let mut n = 0u32;
        for &t in v.iter() { n += (t < x) as u32; }
        n as u8
    }
    /// Sum of the leaves, in tree order, for the ranks `xb`.
    pub fn walk(&self, xb: &[u8; 256]) -> f64 {
        crate::prof!(5);
        // (indices kept as usize and checked: with 32-bit indices the compiler turns the walk into vector gathers,
        // which are three times slower here)
        const LANES: usize = 8;
        let mut sum = self.base;
        let n = self.roots.len();
        let mut k = 0;
        while k < n {
            let m = (n - k).min(LANES);
            let mut i = [0usize; LANES];
            for j in 0..m { i[j] = self.roots[k + j] as usize; }
            for _ in 0..self.depth {
                for j in 0..LANES {
                    let nd = self.nodes[i[j]];
                    i[j] = nd.l as usize + (xb[nd.f as usize] > nd.k) as usize;
                }
            }
            for j in 0..m { sum += self.val[i[j]]; }
            k += m;
        }
        sum
    }
}
