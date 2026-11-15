# wild2: log

## 14 Nov 18:16 · open
- **Hypothesis:** second fast screen on BEST10 toward 20k: lower base floor with the level floor (markupMin 1.22 / 1.25), then sim-first knobs: booking-model hazard scale in the fee plan, night raise freeze, per-option price, order pooling for pairs, bulk-yard handling
- **Base, seeds, metric:** kit-wild = BEST10; local sim 158 weeks first (trust only where orders stay flat), server fresh f22-1..36 same weeks for floor, then 12-week screens and 36 fresh on BEST10 and BEST9; mean diff ± SE, better/worse, ranked, worst on time
- **Kill criteria:** sim under +150 or server screen under +250; confirm under 2 SE or fewer ranked weeks
- **What I did:**
- **Result / verdict:**
- **Next:**

### 14 Nov 19:20 to 19:50 (kit-wild = BEST10; sim v4 158 weeks m, h, k, base 17,935, orders 440, worst 93.7%)
| Idea (knob) | Local sim | Server, fresh weeks vs BEST10 | Verdict |
|---|---|---|---|
| base floor markupMin 1.22 / 1.25 with the level floor | +90 ± 48 / +46 ± 44 | f22-1..36 (base 17,559, 36/36): +118 ± 140 (22/14) / +73 ± 125 (17/19), 36/36, orders +6 / +3 | dead |
| nightHold (no raise 23:00 to 07:00) | +2 ± 3 | | dead |
| fineSteps 2 / 4 | -46 ± 36 / +13 ± 26 | | dead |
| raiseFlat .5 / 1 (raises in EUR of a 70 EUR gig) | +176 ± 43 / +189 ± 40 | | weak, not on server |
| openTilt .15 (schedule x (70 EUR / typical)^.15) | +596 ± 50 (135/23), orders +3, on time 97.4 -> 98.4% | tl-1..36 (base 17,887, 36/36, worst 91.7%, mean 96.4%): +47 ± 95 (17/19), 35/36 ranked, worst 89.9%, mean 96.1%, scored -570 | dead: sim wrong (sign of on time too) |
| openTilt .3 | +529 ± 63 | -292 ± 130 (12/24), 36/36, mean on time 95.6% | dead |
| openTilt .15, tiltRef 60 | +741 ± 49 | +272 ± 131 (21/15), 35/36 ranked, worst 89.6%, scored -309 | dead (an unranked week) |
| openTilt .25, tiltRef 60 | +881 ± 60 | +173 ± 125 (23/13), 36/36, worst 90.1%, mean 95.6% | dead |
| privUp .05, dowUp +-.03 | -13, -249 / +252 | | sim only; sim likes cheaper fees |
| bookShift -.3 / -.6 / +.3 (booking model logit in the fee plan) | -1,477 / -3,523 / +766 ± 94 (orders +23, on time -0.9) | b1 on bs-1..36 running | open |
Lesson: the sim's fee-side gains with flat orders did not carry (tilt +596 sim, +47 server; on time +1.0 point in the sim, -0.3 on the server). The sim under-prices lower fees for dear gigs.
