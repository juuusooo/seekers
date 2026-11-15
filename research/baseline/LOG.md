# Baseline: the best model on fresh weeks

## 14 Nov 03:20 · best model, m-1..48
- Config: `kit-max/BEST.cfg` (kit-09 algo3 + noteRead, = kit-run1). Variant `m1 base`.
- 14,648 a week (z 13,987), 369 orders, mean on time 94.5%, worst 89.5%, 45/48 ranked.
- Money (10 weeks, `kit-max/an_money.ts`): revenue 39,834, driver fees 24,306 (0.949 x typical of won orders),
  refunds 776, failed visits 59, other 105. 1,033 requests, 357 won, 66 declined, 49 drops, 32 deadline warnings.
  D01: 319 requests, 131 won.
- Fee timing (journals, 22,002 bookings): 38% book at the opening fee, median booking 1.15 x opening,
  4.5% after a deadline warning. Minutes to booking: median 115, 75th percentile 429.
