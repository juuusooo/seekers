# competitor: log

## 14 Nov 12:33 · open
- **Hypothesis:** the competitor's price is a fixed number per request and world (same seed, many variants: 89% of requests with wins and losses show every win below every loss once price is divided by 1+trust%, overlap median 0.9%). Its day part (SD 0.12 in log price) and dealer part (SD 0.12) are far larger than kit-best assumes; an online filter for week + day + dealer + town parts with a steeper win curve prices closer under the competitor
- **Base, seeds, metric:** offline: one-step-ahead log loss on held-out seeds (research/views/preq.py) vs week-level-only; live: kit copy with the filter vs kit-best defaults, same seeds, 16 weeks screen then 48 fresh, also on BEST3
- **Kill criteria:** no offline log loss gain over week-only, or live gain under 2 SE on fresh seeds
- **What I did:**
- **Result / verdict:**
- **Next:**

## 14 Nov 13:20 · offline evidence (research/views/decomp.py, preq.py; 2.59M quotes, 3,679 worlds, 272 seeds)
- Same request + seed across variants: 89% clean threshold after dividing price by 1+trust%; overlap median 0.9%.
- Parts of ln(competitor price / list), SD: lane 0.07 to 0.13 (fixed), week 0.03 to 0.08, weekday of a week 0.11 to 0.12,
  dealer of a week 0.09 to 0.14, pickup town 0.14, delivery town 0.12, dealer-day 0.14 (fits with other variants of the same seed).
- Live replay on 57 held-out seeds (678 worlds, one-step-ahead log loss): week only 0.5875; + day 0.5112 (s 0.10);
  + day + towns 0.4965; + dealer no gain. Sharper s (0.06, 0.045) is worse offline.
- Earlier `dayLearn` test used a prior SD of 0.15 in log odds (= 0.015 in log price); the measured day SD is 0.12 in log price.

## 14 Nov 14:05 · live screen, kit-price (kit-best + filter), px-1..32, bench tag `pl1`
| variant | vs base | ± | better/worse | ranked | worst on time | orders |
|---|---|---|---|---|---|---|
| base (kit-best) | 16,680 | | | 32/32 | 92.2% | 406 |
| day (pS 0.10) | +289 | 150 | 18/14 | 32/32 | 92.3% | 405 |
| day, markupMin 1.2 | +280 | 130 | 18/14 | 32/32 | 91.5% | 424 |
| day, pS 0.07 | +384 | 168 | 22/10 | 32/32 | 91.3% | 431 |
| day, pS 0.13 | -209 | 205 | 12/20 | 32/32 | 94.5% | 373 |
| day + towns (16 weeks) | +208 | 268 | 9/7 | 16/16 | 93.5% | 398 |
Lead, under 2.5 SE. Sharper wins more orders and cuts the on-time cushion. Proof next: py-1..48, tag `pl2`.

## 14 Nov 14:45 · PROOF on fresh seeds py-1..48, bench tag `pl2` (kit-price, base = kit-best defaults)
| variant | margin | vs base | ± | better/worse | z (unranked = 0) | ranked | worst on time | orders |
|---|---|---|---|---|---|---|---|---|
| base | 15,999 | | | | 14,017 | 42/48 | 85.4% | 407 |
| day, pS 0.10 | 16,505 | +506 | 136 | 32/16 | 14,785 (+768) | 43/48 | 87.1% | 404 |
| day, pS 0.07 | 16,489 | +490 | 145 | 33/15 | 14,420 (+403) | 42/48 | 86.3% | 432 |
| day, pS 0.05 | 16,142 | +143 | 194 | 29/19 | 13,884 (-133) | 41/48 | 83.9% | 447 |
pS 0.10 (the offline optimum, fixed before the proof) holds: +506 ± 136, no ranked week lost. Note: py seeds are hard on
on time for every variant (6 of 48 unranked on base). Next: second base BEST3 (dueCapPer 0.09), pz-1..32, tag `pl3`.
