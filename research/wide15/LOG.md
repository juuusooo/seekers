# wide15: log

## 15 Nov 01:49 · open
- **Hypothesis:** Wide one-knob screen on BEST15 while the practice slots are free: knobs with weak earlier leads (rampTop, lateFee, steepOpen, markupMin, hardPrice, hardChance, dueCapPer, capLam, pS, costW, minBookChance, pairCap, outage, bookShift); any that gains over 2 SE on 48 weeks goes to 96 fresh weeks
- **Base, seeds, metric:** kit-out with pLane=0.06,openTilt=0 = BEST15; server fresh wa-1..48 same weeks, tag wa1; mean diff ± SE, ranked, on time
- **Kill criteria:** screen under 2 SE or fewer ranked weeks; proof under 2 SE on fresh weeks
- **What I did:**
- **Result / verdict:**
- **Next:**

### Screen wa-1..48 (tag wa1), base BEST15 19,047, 48/48 ranked, worst on time 92.3%, orders 433
bookShift 0.1 +440 ± 104 (39/9), 48/48, worst 91.7%, mean on time 96.2% vs 96.4%, orders 441;
minBookChance 0.93 +202 ± 103 (31/17), orders 438; rampTop 1.3 +150 ± 73 (32/16), 1.45 +104 ± 59 (31/17);
costW 1.25 +48 ± 90; hardChance 0.82 +43 ± 89; lateFee 0.6 +25 ± 53; capLam 4.5 +23 ± 98 (orders 420); pairCap 0.85 +19 ± 51;
steepOpen 1.15 -12 ± 53; markupMin 1.24 -18 ± 88; hardPrice 0.14 -40 ± 90; dueCapPer 0.11 -42 ± 65; pS 0.085 -171 ± 110.
All 48/48 ranked. Combination test on fresh wb-1..64 (tag wb1): base, bs1, bs1 + rampTop 1.3, bs1 + minBookChance 0.93, all three.
