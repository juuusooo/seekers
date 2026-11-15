# final_safety: log

## 15 Nov 00:52 · open
- **Hypothesis:** Both live finals: our on time is the lowest of the top 10 (96.8%, 92.8%) and BEST13/14 lose 3 to 6% of fresh weeks to the 90% line. openTilt=0 gave +0.5 to +0.8 points of on time on 5 older week sets for -60 to -260 margin, never tested on BEST14. A safety set (openTilt 0 or 0.12, feeLate 1, dueCapPer 0.09) lifts mean on time by 0.5 points or more and the scored margin (unranked = 0) is not lower
- **Base, seeds, metric:** kit-safe = copy of kit-best BEST14, knobs only; server fresh sf-1..32 same weeks (tag sf1): base, t0, t12, t0+feeLate 1, t0+dueCapPer 0.09, dueCapPer 0.09; then the best on 32 more fresh weeks; margin diff ± SE, mean and worst on time, weeks under 92% and 90%, scored margin
- **Kill criteria:** mean on time gain under 0.4 point, or margin under -300 with no ranked week gained
- **What I did:**
- **Result / verdict:**
- **Next:**

### Note from the on_time session, 15 Nov 01:58 Helsinki
- kit-safe was replaced at 01:53 by this session by mistake (same folder name picked at the same minute). It is kit-best BEST14 plus
  `longUp` / `longH` (default off): all sf1 variants play as planned. 24 weeks of the first sweep were lost and restarted by its owner.
- Added on the same seeds (tag sf1, sf-1..32): `long10` (longUp 0.1), `long20` (0.2), `long10t0` (longUp 0.1 + openTilt 0).
  Why: drives of 4 to 8 hours are 18% of the orders and 45% of the lates (300 recorded weeks, on_time study).
- on_time screen ot1 (arrival buffer, evening raise, 22 h window for late cars) shows no on-time gain at 10 of 16 weeks.

### Screen sf1 (server, fresh sf-1..32, same weeks, kit-safe = BEST14), 15 Nov 01:12
Base 18,183, 27/31 ranked (4 weeks under 90%), worst on time 88.5%, mean 94.7%, orders 431.

| Variant | Diff ± SE | Better/worse | Ranked | Worst | Mean on time | Scored diff (unranked = 0) |
|---|---|---|---|---|---|---|
| t0 (openTilt=0) | +264 ± 134 | 15/14 | 29/29 | 90.1% | 95.8% | +2,322 |
| t12 (openTilt=0.12) | +442 ± 178 | 18/13 | 30/31 | 89.7% | 95.3% | +1,950 |
| t0 + dueCapPer 0.09 | +71 ± 132 | 14/17 | 30/31 | 89.9% | 95.8% | +1,511 |
| t0 + feeLate 1 | -138 ± 134 | 12/19 | 30/31 | 89.7% | 95.8% | +1,420 |
| dueCapPer 0.09 | -2 ± 98 | 11/15 | 27/31 | 89.0% | 94.9% | -83 |

openTilt off: +1.1 points of on time, no margin lost, 4 unranked weeks saved. Best of 5 on one set: proof on new weeks
sg-1..40 (tag sg1): base, t0, t12 on BEST14, and base, t0 on BEST13 (pLane=0).
Other sessions added rows with the same tag sf1 (long10, long20, d11, d18, f1, flu15): not part of this study.

### Note, 15 Nov 02:20 Helsinki (00:20 UTC): kit-best changed under running sweeps
- On the user's instruction `openTilt` is now 0 by default in kit-best and kit-final (BEST15, ledger row `best15`).
- kit-safe was NOT changed: its defaults are still BEST14, so sf1 / sg1 weeks played from kit-safe are not affected.
- Any sweep that plays "base" from kit-best (or a copy made after 02:20) now plays BEST15. For a BEST14 base pass `openTilt=0.25`.
- Numbers at shipping: sf1 t0 +264 ± 134, on time +1.08 ± 0.24, 29/29 vs 27/31 ranked; sg1 t0 (25 weeks) -48 ± 138, +0.81 ± 0.22, 25/25 vs 26/29.

### Proof sg1 (server, fresh sg-1..40, same weeks, kit-safe), 15 Nov 01:32
BEST14 base 18,345, 36/40 ranked, worst 86.4%, mean on time 95.2%. BEST13 base (pLane=0) 18,181, 38/40, mean 95.3%.

| Variant | Diff ± SE | Better/worse | Ranked | Worst | Mean on time | Scored diff |
|---|---|---|---|---|---|---|
| BEST14 + openTilt 0 | +93 ± 126 | 21/19 | 39/40 | 88.6% | 96.1% | +1,479 |
| BEST14 + openTilt 0.12 | +179 ± 136 | 24/16 | 38/40 | 88.6% | 95.7% | +939 |
| BEST13 + openTilt 0 (vs BEST13) | +26 ± 129 | 20/20 | 39/40 vs 38/40 | 88.9% | 95.9% | +642 |

Pooled sf1 + sg1 on BEST14 (about 70 weeks): openTilt 0: margin +165 ± 92 (36/33), on time +0.98 ± 0.15 points,
ranked 68 vs 61 of 69, scored +1,833 ± 665. openTilt 0.12: margin +293 ± 109 (42/29), on time +0.57 ± 0.14, ranked 68 vs 63
of 71, scored +1,381 ± 541. 0.12 against 0 on the same 70 weeks: margin +120 ± 102, on time -0.42 ± 0.12, ranked 67 vs 69,
scored -422 ± 416.
