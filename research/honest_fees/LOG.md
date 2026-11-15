# Honest fees: open where we will pay, do not raise

Why: only 38% of gigs book at the opening fee, the median at 1.15 x it. The rules say drivers learn how far our
fees rise and wait for it. A schedule that never rises should teach them not to wait.
Old test `flatDays` (kit-09) lost 1,570, but it took the flat fee from the booking model, which was fitted on
drivers who expect raises.

Knob `flatOpen` (algo3.ts, kit-max): open at flatOpen x typical, no planned raises; the early ramp (10 h before the
last pickup time) and the urgent fees stay. Pairs keep their plan. Built 14 Nov 03:35, not tested yet.

## 14 Nov 03:50 · on best, m-1..32
- `flatOpen=1`: -1,364 ± 189, better 3 / worse 28, 27/31 ranked. `flatOpen=1.15`: -4,389 ± 238, 0/32 better.
- Verdict: drop. Flat fees lose badly even at 1.0 x typical: the planned low opening plus raises books cheaper.

## 14 Nov 04:00 · lower flat fees, m-1..28
- `flatOpen=0.85`: +115 ± 198, 17/28 ranked, worst 87.4%. `flatOpen=0.9`: -346 ± 197, 18/26 ranked.
- Verdict: drop flat fees entirely. Cheap flat fees leave cars without drivers; dear ones overpay.
