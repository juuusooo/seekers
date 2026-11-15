# Denoise the typical fee

## 14 Nov 03:15 · is the typical fee noisy? (`kit-max/an/typ.py`, 30 base weeks, 25k one-leg requests)
- ln(typical) on route minutes, km, pickup and delivery town: R² 0.957, residual SD 0.144.
- Booked fee / typical by residual: -15% or less 1.10, around 0 0.96, +15% or more 0.88. Slope of ln(fee/typ) on
  the residual: -0.56. So drivers ignore about half the noise in our data (we open at multiples of the noisy fee).
- Win share: 30% when residual > +10% (we think the car is dear to move and price high), 39% otherwise.

## 14 Nov 03:30 · lane table (`kit-max/an/fit_typ.py` → `kit-max/typ.json`)
- 557k one-leg requests from 570 practice worlds (all bench seeds except m- and h-). 899 lanes, median 219 per lane.
- Residual SD 0.128. Private pickup +1.8%, others ~0. Trade-ins: typical = 0.50 x sum of the two legs (SD 0.21).

## Knob `typW` (engine3.ts, `denoise()`)
typical used everywhere = raw^(1 - typW) x prediction^typW, lanes seen 5+ times. 0 = off.

## 14 Nov 03:40 · on best, m-1..47 (variants `m1 typ100`, `m1 typ50`)
| typW | vs base | ± | better/worse | z | ranked (base) | worst on time | orders |
|---|---|---|---|---|---|---|---|
| 1 | +401 | 122 | 32/15 | +483 | 45/47 (44/47) | 89.9% | 378 (369) |
| 0.5 | +208 | 101 | 29/18 | +884 | 47/47 (44/47) | 90.7% | 376 |
Verdict: real gain (3.3 SE at typW=1). More orders at the same margin per order. Next: proof on h- seeds,
typW 0.75, and on top of other winners.

## 14 Nov 03:55 · booking model refit on the denoised fee (`kit-max/learn/fit.py`, `an/denoise_journals.py`)
- Same 160 kit-03 exploration weeks, each post's typical fee replaced by the lane prediction → `kit-max/model_d.json`.
- Unseen weeks log loss 0.2856 (raw fee 0.2873). Fee slope below 1.0 x: odds x1.79 per +0.1 (raw 1.68).
- Live test queued: `SPREAD_MODEL=model_d.json` + `typW=1`, variant `m1 T+modelD`.

## 14 Nov 04:12 · booking model refit on exploration + our own T weeks (`model_dj.json`)
- 160 exploration weeks (denoised) + 48 T weeks j-1..48 (journals). Unseen-week log loss 0.2270 (constant 0.3632).
- Live test queued: `m1 T+modelDJ` on m-1..48 vs T.

## 14 Nov 04:32 · proof on h-1..48 (never used before)
- base 14,614 (44/47 ranked), T 14,902 (43/46): +195 ± 128, better 30 / worse 16, z +100.
- With m-1..48 (+403 ± 119): about +300 ± 90 over 94 weeks. Adopted as new best: `kit-max/BEST2.cfg`.
- Split test (m-): the gain comes from the gig-fee side (fees only -74 ± 139 vs T; price only -462 ± 122 vs T).
