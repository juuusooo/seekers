//! sim-experimental: the local Spread level 8 world and our desk in Rust.
//!   sim-experimental --seeds m-1..48,h-1..48 [--set k=v,..] [--sim k=v,..] [--variant name] [--out file.jsonl]
//!                    [--threads N] [--trace dir] [--quiet]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
mod data;
mod desk;
mod exp_tab;
mod fexp;
mod prof;
mod world;
use data::*;
use rayon::prelude::*;
use std::io::Write;
use std::path::PathBuf;
use std::time::Instant;

/// Seconds on a steady clock (the original used the Linux thread CPU clock; this copy also builds on Windows).
fn cpu_now() -> f64 {
    static START: std::sync::OnceLock<Instant> = std::sync::OnceLock::new();
    START.get_or_init(Instant::now).elapsed().as_secs_f64()
}

fn expand(seeds: &str) -> Vec<String> {
    let mut out = Vec::new();
    for s in seeds.split(',').filter(|s| !s.is_empty()) {
        if let Some((pre, range)) = s.rsplit_once('-') {
            if let Some((a, b)) = range.split_once("..") {
                if let (Ok(a), Ok(b)) = (a.parse::<u32>(), b.parse::<u32>()) {
                    for i in a..=b { out.push(format!("{pre}-{i}")); }
                    continue;
                }
            }
        }
        out.push(s.to_string());
    }
    out
}
fn parse_set(text: &str) -> Vec<(String, f64)> {
    text.split(',').filter(|s| !s.is_empty()).map(|kv| {
        let (k, v) = kv.split_once('=').unwrap_or_else(|| panic!("expects key=number pairs, got \"{kv}\""));
        (k.trim().to_string(), v.trim().parse::<f64>().unwrap_or_else(|_| panic!("expects key=number pairs, got \"{kv}\"")))
    }).collect()
}
fn jnum(x: f64) -> String {
    if x.is_finite() { format!("{}", x) } else { "null".into() }
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut opt = std::collections::HashMap::<String, String>::new();
    let mut i = 0;
    while i < args.len() {
        let k = args[i].trim_start_matches("--").to_string();
        if k == "quiet" || k == "print-params" || k == "no-fast-exp" { opt.insert(k, "1".into()); i += 1; } else { opt.insert(k, args.get(i + 1).cloned().unwrap_or_default()); i += 2; }
    }
    let fast_exp = fexp::self_test();
    let fast8 = fexp::self_test8();
    if opt.contains_key("exp-test") { println!("eight-wide exp on: {fast8}"); }
    if opt.contains_key("exp-test") {
        // a long comparison of the inline exp with the library's, and their speed
        let n: u64 = opt["exp-test"].parse().unwrap_or(100_000_000);
        let (mut s, mut bad) = (88172645463325252u64, 0u64);
        let mut xs = vec![0.0f64; 4096];
        let (mut t_lib, mut t_fast) = (0.0, 0.0);
        let (mut a, mut b) = (0.0f64, 0.0f64);
        for _ in 0..n / 4096 {
            for x in xs.iter_mut() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; *x = ((s >> 11) as f64 / (1u64 << 53) as f64 - 0.5) * if s & 1 == 0 { 60.0 } else { 6.0 }; }
            let t = Instant::now(); for &x in &xs { a += x.exp(); } t_lib += t.elapsed().as_secs_f64();
            let t = Instant::now(); for &x in &xs { b += fexp::exp(x); } t_fast += t.elapsed().as_secs_f64();
            for &x in &xs { if x.exp().to_bits() != fexp::exp(x).to_bits() { bad += 1; } }
        }
        println!("inline exp on: {fast_exp}; {} inputs, {bad} differ; library {:.2} ns, inline {:.2} ns a call ({})", n / 4096 * 4096, t_lib * 1e9 / n as f64, t_fast * 1e9 / n as f64, a == b);
        return;
    }
    if opt.contains_key("print-params") {
        let p = desk::P::default();
        let s = world::SimP::default();
        println!("{:?}\n{:?}", p, s);
        return;
    }
    let root = PathBuf::from(opt.get("root").cloned().unwrap_or_else(|| {
        let exe = std::env::current_exe().unwrap();
        exe.parent().unwrap().parent().unwrap().parent().unwrap().to_string_lossy().into_owned()
    }));
    let mut st: Static = serde_json::from_slice(&std::fs::read(root.join("static.json")).expect("static.json: run `bun prep.ts` first")).unwrap();
    if let Some(file) = opt.get("cost") { st.cost = serde_json::from_slice(&std::fs::read(file).expect("--cost file")).unwrap(); }
    st.fast_mean = FastTrees::build(&st.cost.mean);
    st.fast_q80 = FastTrees::build(&st.cost.q80);
    st.bin_mean = BinTrees::build(&st.cost.mean);
    st.bin_q80 = BinTrees::build(&st.cost.q80);
    let st = st;
    // variants: --set (one, named by --variant) or --sets FILE with one "name k=v,k=v" per line (data is loaded once)
    let obj = |kv: &[(String, f64)]| format!("{{{}}}", kv.iter().map(|(k, v)| format!("\"{k}\":{}", jnum(*v))).collect::<Vec<_>>().join(","));
    let make = |name: &str, text: &str| {
        let mut p = desk::P::default();
        let set = parse_set(text);
        for (k, v) in &set { if !p.set(k, *v) { panic!("Unknown parameter \"{k}\". Known: {}", desk::P::names().join(", ")); } }
        (name.to_string(), p, obj(&set))
    };
    let variants: Vec<(String, desk::P, String)> = match opt.get("sets") {
        Some(file) => std::fs::read_to_string(file).expect("--sets file").lines().filter(|l| !l.trim().is_empty()).map(|l| { let (n, t) = l.trim().split_once(char::is_whitespace).unwrap_or((l.trim(), "")); make(n, t.trim()) }).collect(),
        None => vec![make(opt.get("variant").map_or("base", |s| s), opt.get("set").map_or("", |s| s))],
    };
    let mut sp = world::SimP::default();
    let sim = parse_set(opt.get("sim").map_or("", |s| s));
    for (k, v) in &sim { if !sp.set(k, *v) { panic!("Unknown sim parameter \"{k}\". Known: {}", world::SimP::names().join(", ")); } }
    let seeds = expand(opt.get("seeds").map_or("", |s| s));
    let trace = opt.get("trace").map(PathBuf::from);
    if let Some(n) = opt.get("threads") { rayon::ThreadPoolBuilder::new().num_threads(n.parse().unwrap()).build_global().unwrap(); }
    let quiet = opt.contains_key("quiet");
    let sim_json = obj(&sim);
    let t_all = Instant::now();
    let loaded: Vec<(String, Seed, world::SeedPre)> = seeds.par_iter().filter_map(|seed| {
        let path = root.join("data").join(format!("{seed}.json"));
        let Ok(bytes) = std::fs::read(&path) else { eprintln!("no data for {seed}"); return None };
        let data: Seed = serde_json::from_slice(&bytes).unwrap();
        let pre = world::SeedPre::new(&st, &data, &sp);
        Some((seed.clone(), data, pre))
    }).collect();
    let t_load = t_all.elapsed().as_secs_f64();
    // seed by seed: a core plays the variants of one week one after the other, with that week's data at hand
    let jobs: Vec<(usize, usize)> = (0..loaded.len()).flat_map(|s| (0..variants.len()).map(move |v| (v, s))).collect();
    let rows: Vec<Option<(String, f64, String)>> = jobs.par_iter().map(|&(vi, si)| {
        let (seed, data) = (&loaded[si].0, &loaded[si].1);
        let (variant, p, set_json) = (&variants[vi].0, &variants[vi].1, &variants[vi].2);
        let t0 = cpu_now();
        let mut w = world::World::new(&st, data, &loaded[si].2, sp.clone(), trace.is_some());
        let mut d = desk::Desk::new(&st, data, p.clone(), trace.is_some());
        d.play(&mut w);
        w.close();
        let s = w.score();
        let mut dump = String::new();
        if opt.contains_key("rows") {
            let xs = d.dump_x.borrow();
            let mut last: std::collections::HashMap<(usize, usize), usize> = std::collections::HashMap::new();
            for (k, r) in xs.iter().enumerate() { last.insert((r.0, r.1), k); }
            for &i in &w.order_list {
                let o = w.orders[i].as_ref().unwrap();
                let Some(&k) = last.get(&(i, o.option)) else { continue };
                let x: Vec<String> = xs[k].2.iter().map(|v| jnum(*v)).collect();
                dump.push_str(&format!("{{\"seed\":\"{seed}\",\"variant\":\"{variant}\",\"typ\":{},\"price\":{},\"fee\":{},\"tail\":{},\"late\":{},\"x\":[{}]}}
", jnum(w.ref_fee[i]), jnum(o.price), jnum(w.o_fee[i]), jnum(w.o_tail[i]), w.o_late[i] as u8, x.join(",")));
            }
        }
        let ms = (cpu_now() - t0) * 1000.0;
        if let Some(dir) = &trace {
            let mut ev = w.trace.take().unwrap();
            ev.push_str(&format!("score {} {} {} {}\n", world::num(s.margin_cents), s.won, s.on_time, d.n_declined));
            std::fs::write(dir.join(format!("{seed}.events.rs.txt")), ev).unwrap();
            std::fs::write(dir.join(format!("{seed}.journal.rs.txt")), d.journal.take().unwrap()).unwrap();
        }
        let stats: Vec<String> = (0..world::N_STAT).filter(|&k| w.touched[k]).map(|k| format!("\"{}\":{}", world::stat_name(k), jround(w.stats[k]))).collect();
        let row = format!(
            "{{\"kit\":\"sim-rs\",\"level\":8,\"variant\":\"{variant}\",\"seed\":\"{seed}\",\"margin\":{},\"onTime\":{},\"won\":{},\"ranked\":{},\"declined\":{},\"ms\":{:.2},\"stats\":{{{}}},\"sim\":{sim_json},\"set\":{set_json}}}",
            jnum(s.margin_cents / 100.0), jnum(s.on_time), s.won, s.ranked, d.n_declined, ms, stats.join(",")
        );
        if !quiet { println!("{seed} margin {} orders {} on time {:.1}% {:.2} ms", jround(s.margin_cents / 100.0), s.won, 100.0 * s.on_time, ms); }
        Some((row, ms, dump))
    }).collect();
    let wall = t_all.elapsed().as_secs_f64();
    let done: Vec<&(String, f64, String)> = rows.iter().flatten().collect();
    if let Some(file) = opt.get("rows") { let mut f = std::fs::File::create(file).unwrap(); for r in &done { f.write_all(r.2.as_bytes()).unwrap(); } }
    if let Some(out) = opt.get("out") {
        let mut f = std::fs::OpenOptions::new().create(true).append(true).open(out).unwrap();
        let mut buf = String::new();
        for (row, _, _) in &done { buf.push_str(row); buf.push('\n'); }
        f.write_all(buf.as_bytes()).unwrap();
    }
    #[cfg(feature = "prof")]
    prof::on::report(done.len() as f64);
    let cpu: f64 = done.iter().map(|r| r.1).sum();
    eprintln!("{} weeks in {:.3} s wall ({:.0} weeks/s; loading {:.3} s), {:.2} ms CPU a week (play only)", done.len(), wall, done.len() as f64 / wall, t_load, cpu / done.len().max(1) as f64);
}
