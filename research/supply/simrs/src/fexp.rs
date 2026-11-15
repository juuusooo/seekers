//! exp() as glibc 2.39 computes it on a CPU with FMA (`__exp_fma`), written out so it can be inlined and several
//! calls can run side by side. Same table, same constants, same fused operations: the result is the same bits as
//! `f64::exp` (and as Math.exp in bun) on this kind of machine. `self_test` checks that at start; if it ever fails
//! (another libm, a CPU without FMA), `exp` falls back to the library call and nothing else changes.
use crate::exp_tab::TAB;
use std::sync::atomic::{AtomicBool, Ordering};

const INV_LN2_N: f64 = f64::from_bits(0x40671547652b82fe);
const SHIFT: f64 = f64::from_bits(0x4338000000000000);
const NEG_LN2_HI_N: f64 = f64::from_bits(0xbf762e42fefa0000);
const NEG_LN2_LO_N: f64 = f64::from_bits(0xbd0cf79abc9e3b3a);
const C2: f64 = f64::from_bits(0x3fdffffffffffdbd);
const C3: f64 = f64::from_bits(0x3fc555555555543c);
const C4: f64 = f64::from_bits(0x3fa55555cf172b91);
const C5: f64 = f64::from_bits(0x3f81111167a4d017);

static FAST: AtomicBool = AtomicBool::new(false);

#[inline(always)]
fn core(x: f64) -> f64 {
    let z = x.mul_add(INV_LN2_N, SHIFT);
    let ki = z.to_bits();
    let kd = z - SHIFT;
    let r = kd.mul_add(NEG_LN2_LO_N, kd.mul_add(NEG_LN2_HI_N, x));
    let idx = 2 * (ki & 127) as usize;
    let tail = f64::from_bits(TAB[idx]);
    let scale = f64::from_bits(TAB[idx + 1].wrapping_add(ki << 45));
    let r2 = r * r;
    let tmp = (r2 * r2).mul_add(r.mul_add(C5, C4), r.mul_add(C3, C2).mul_add(r2, tail + r));
    scale.mul_add(tmp, scale)
}
/// exp(x), bit-identical to the library's.
#[inline(always)]
pub fn exp(x: f64) -> f64 {
    // 2^-54 <= |x| < 512: the library's main path; everything else goes to the library
    let top = (x.to_bits() >> 52) & 0x7ff;
    if top.wrapping_sub(0x3c9) <= 0x3e && FAST.load(Ordering::Relaxed) { core(x) } else { x.exp() }
}
/// Compares the inline exp with the library's on a spread of inputs; turns the inline path on only if all agree.
pub fn self_test() -> bool {
    if !std::is_x86_feature_detected!("fma") { return false; }
    let mut s: u64 = 0x9E3779B97F4A7C15;
    let mut ok = true;
    for i in 0..200_000u32 {
        s ^= s << 13; s ^= s >> 7; s ^= s << 17;
        let u = (s >> 11) as f64 / (1u64 << 53) as f64;
        let x = match i % 4 { 0 => (u - 0.5) * 80.0, 1 => (u - 0.5) * 8.0, 2 => (u - 0.5) * 1000.0, _ => (u - 0.5) * 1e-3 };
        let top = (x.to_bits() >> 52) & 0x7ff;
        if top.wrapping_sub(0x3c9) <= 0x3e && core(x).to_bits() != x.exp().to_bits() { ok = false; break; }
    }
    FAST.store(ok, Ordering::Relaxed);
    ok
}

// ── eight at a time (AVX-512): the same operations per lane ──
static FAST8: AtomicBool = AtomicBool::new(false);
#[cfg(target_arch = "x86_64")]
mod v {
    use super::*;
    use std::arch::x86_64::*;
    #[target_feature(enable = "avx512f,avx512dq,fma")]
    pub unsafe fn exp8(x: __m512d) -> __m512d {
        let shift = _mm512_set1_pd(SHIFT);
        let z = _mm512_fmadd_pd(x, _mm512_set1_pd(INV_LN2_N), shift);
        let ki = _mm512_castpd_si512(z);
        let kd = _mm512_sub_pd(z, shift);
        let r = _mm512_fmadd_pd(kd, _mm512_set1_pd(NEG_LN2_LO_N), _mm512_fmadd_pd(kd, _mm512_set1_pd(NEG_LN2_HI_N), x));
        let idx = _mm512_slli_epi64::<1>(_mm512_and_si512(ki, _mm512_set1_epi64(127)));
        let tail = _mm512_i64gather_pd::<8>(idx, TAB.as_ptr() as *const f64);
        let sb = _mm512_i64gather_epi64::<8>(idx, TAB.as_ptr().add(1) as *const i64);
        let scale = _mm512_castsi512_pd(_mm512_add_epi64(sb, _mm512_slli_epi64::<45>(ki)));
        let r2 = _mm512_mul_pd(r, r);
        let tmp = _mm512_fmadd_pd(
            _mm512_mul_pd(r2, r2),
            _mm512_fmadd_pd(r, _mm512_set1_pd(C5), _mm512_set1_pd(C4)),
            _mm512_fmadd_pd(_mm512_fmadd_pd(r, _mm512_set1_pd(C3), _mm512_set1_pd(C2)), r2, _mm512_add_pd(tail, r)),
        );
        _mm512_fmadd_pd(scale, tmp, scale)
    }
    /// out[0..8] = 1 / (1 + exp(-(a[i] + b[i]))); false (nothing written) when a lane is outside exp's main path.
    #[target_feature(enable = "avx512f,avx512dq,fma")]
    pub unsafe fn sigmoid_sum8(a: *const f64, b: *const f64, out: *mut f64) -> bool {
        let one = _mm512_set1_pd(1.0);
        let x = _mm512_xor_pd(_mm512_add_pd(_mm512_loadu_pd(a), _mm512_loadu_pd(b)), _mm512_set1_pd(-0.0));
        let top = _mm512_and_si512(_mm512_srli_epi64::<52>(_mm512_castpd_si512(x)), _mm512_set1_epi64(0x7ff));
        if _mm512_cmple_epu64_mask(_mm512_sub_epi64(top, _mm512_set1_epi64(0x3c9)), _mm512_set1_epi64(0x3e)) != 0xff { return false; }
        _mm512_storeu_pd(out, _mm512_div_pd(one, _mm512_add_pd(one, exp8(x))));
        true
    }
    /// out[i] = 1 / (1 + exp(-(z[i] + w))), each lane with the operations of the scalar expression.
    #[target_feature(enable = "avx512f,avx512dq,fma")]
    pub unsafe fn sigmoid_shift(z: &[f64], w: f64, out: &mut [f64]) {
        let n = z.len();
        let (one, wv) = (_mm512_set1_pd(1.0), _mm512_set1_pd(w));
        let sign = _mm512_set1_pd(-0.0);
        let mut i = 0;
        while i + 8 <= n {
            let a = _mm512_xor_pd(_mm512_add_pd(_mm512_loadu_pd(z.as_ptr().add(i)), wv), sign);
            // the main path of exp needs 2^-54 <= |a| < 512 in every lane
            let top = _mm512_and_si512(_mm512_srli_epi64::<52>(_mm512_castpd_si512(a)), _mm512_set1_epi64(0x7ff));
            let ok = _mm512_cmple_epu64_mask(_mm512_sub_epi64(top, _mm512_set1_epi64(0x3c9)), _mm512_set1_epi64(0x3e));
            if ok == 0xff {
                _mm512_storeu_pd(out.as_mut_ptr().add(i), _mm512_div_pd(one, _mm512_add_pd(one, exp8(a))));
            } else {
                for j in i..i + 8 { out[j] = 1.0 / (1.0 + super::exp(-(z[j] + w))); }
            }
            i += 8;
        }
        while i < n { out[i] = 1.0 / (1.0 + super::exp(-(z[i] + w))); i += 1; }
    }
}
/// out[i] = 1 / (1 + exp(-(z[i] + w))), bit-identical to the scalar expression.
#[inline]
pub fn sigmoid_shift(z: &[f64], w: f64, out: &mut [f64]) {
    #[cfg(target_arch = "x86_64")]
    if FAST8.load(Ordering::Relaxed) {
        unsafe { v::sigmoid_shift(z, w, out) };
        return;
    }
    for i in 0..z.len() { out[i] = 1.0 / (1.0 + exp(-(z[i] + w))); }
}
/// Checks the eight-wide path against the library on a spread of inputs; turns it on only if all agree.
pub fn self_test8() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        if !FAST.load(Ordering::Relaxed) || !std::is_x86_feature_detected!("avx512f") || !std::is_x86_feature_detected!("avx512dq") { return false; }
        let mut s: u64 = 0x2545F4914F6CDD1D;
        let mut z = vec![0.0f64; 4099];
        let mut ok = true;
        for round in 0..40 {
            for x in z.iter_mut() { s ^= s << 13; s ^= s >> 7; s ^= s << 17; *x = ((s >> 11) as f64 / (1u64 << 53) as f64 - 0.5) * [60.0, 6.0, 1200.0, 1e-3][round % 4]; }
            if round == 7 { z[5] = 0.0; z[77] = f64::INFINITY; z[100] = f64::NAN; z[200] = -800.0; z[300] = 800.0; }
            let w = (round as f64 - 20.0) * 0.173;
            let mut out = vec![0.0f64; z.len()];
            unsafe { v::sigmoid_shift(&z, w, &mut out) };
            for i in 0..z.len() { if out[i].to_bits() != (1.0 / (1.0 + (-(z[i] + w)).exp())).to_bits() { ok = false; } }
        }
        FAST8.store(ok, Ordering::Relaxed);
        return ok;
    }
    #[allow(unreachable_code)]
    false
}

/// out[i] = 1 / (1 + exp(-(a[i] + b[i]))), bit-identical to the scalar expression.
#[inline]
pub fn sigmoid_sum(a: &[f64], b: &[f64], out: &mut [f64]) {
    let n = a.len();
    let mut i = 0;
    #[cfg(target_arch = "x86_64")]
    if FAST8.load(Ordering::Relaxed) {
        while i + 8 <= n {
            if !unsafe { v::sigmoid_sum8(a.as_ptr().add(i), b.as_ptr().add(i), out.as_mut_ptr().add(i)) } {
                for j in i..i + 8 { out[j] = 1.0 / (1.0 + exp(-(a[j] + b[j]))); }
            }
            i += 8;
        }
    }
    while i < n { out[i] = 1.0 / (1.0 + exp(-(a[i] + b[i]))); i += 1; }
}
pub fn has8() -> bool { FAST8.load(Ordering::Relaxed) }

#[cfg(target_arch = "x86_64")]
pub use v2::est8;
#[cfg(target_arch = "x86_64")]
mod v2 {
    use std::arch::x86_64::*;
    /// The fee planner's estimate for eight opening fees side by side (desk.rs plan): hour k uses the fee levels
    /// f/r[off0 + m min(k, s) ..+8] and e[k] = exp(-base logit). Returns false when all eight are out (their least
    /// possible cost is above `cut`).
    #[target_feature(enable = "avx512f,avx512dq,fma")]
    pub unsafe fn est8(e: &[f64], f: &[f64], r: &[f64], off0: usize, m: usize, s: usize, late: f64, cut: f64, out: &mut [f64; 8]) -> bool {
        let one = _mm512_set1_pd(1.0);
        let (latev, cutv) = (_mm512_set1_pd(late), _mm512_set1_pd(cut));
        let (mut cost, mut unb) = (_mm512_setzero_pd(), one);
        debug_assert!(off0 + m * s + 8 <= f.len() && f.len() == r.len());
        for k in 0..e.len() {
            let off = off0 + m * k.min(s);
            let (fs, rs) = (_mm512_loadu_pd(f.as_ptr().add(off)), _mm512_loadu_pd(r.as_ptr().add(off)));
            if k & 3 == 0 {
                let least = _mm512_fmadd_pd(unb, _mm512_min_pd(rs, latev), cost);
                if _mm512_cmp_pd_mask::<_CMP_LE_OQ>(least, cutv) == 0 { return false; }
            }
            let ch = _mm512_div_pd(one, _mm512_fmadd_pd(_mm512_set1_pd(*e.get_unchecked(k)), fs, one));
            cost = _mm512_fmadd_pd(_mm512_mul_pd(unb, ch), rs, cost);
            unb = _mm512_fnmadd_pd(unb, ch, unb);
        }
        _mm512_storeu_pd(out.as_mut_ptr(), _mm512_fmadd_pd(unb, latev, cost));
        true
    }
}
