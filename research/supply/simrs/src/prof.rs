//! Coarse section timers (CPU time-stamp counter) and call counts, compiled in only with `--features prof`.
#[cfg(feature = "prof")]
pub mod on {
    use std::sync::atomic::{AtomicU64, Ordering::Relaxed};
    pub const NAMES: [&str; 24] = ["advance", "quote", "learn", "win", "plan", "cost_trees", "open_singles", "look_hourly", "feasible", "try_pair", "timers", "decide", "post", "look_notify", "markup", "looks", "book", "pickup", "deliver", "warn", "handle", "queue", "fees", "x"];
    pub static T: [AtomicU64; 24] = [const { AtomicU64::new(0) }; 24];
    pub static N: [AtomicU64; 24] = [const { AtomicU64::new(0) }; 24];
    #[inline(always)]
    pub fn tsc() -> u64 { unsafe { core::arch::x86_64::_rdtsc() } }
    pub struct Guard(pub usize, pub u64);
    impl Drop for Guard {
        #[inline(always)]
        fn drop(&mut self) { T[self.0].fetch_add(tsc() - self.1, Relaxed); N[self.0].fetch_add(1, Relaxed); }
    }
    pub fn report(weeks: f64) {
        let t0 = std::time::Instant::now(); let c0 = tsc();
        std::thread::sleep(std::time::Duration::from_millis(20));
        let ns_per_tick = t0.elapsed().as_nanos() as f64 / (tsc() - c0) as f64;
        for i in 0..24 { let (t, n) = (T[i].load(Relaxed) as f64 * ns_per_tick, N[i].load(Relaxed) as f64); if n > 0.0 { eprintln!("{:14} {:8.3} ms/week {:10.0} calls/week {:8.0} ns/call", NAMES[i], t / 1e6 / weeks, n / weeks, t / n); } }
    }
}
#[macro_export]
macro_rules! prof {
    ($i:expr) => {
        #[cfg(feature = "prof")]
        let _g = $crate::prof::on::Guard($i, $crate::prof::on::tsc());
    };
}
