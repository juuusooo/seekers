# Capacity: ration drivers by price, not by a flat floor

Why: 43% of quotes sit exactly at the price floor (`markupMin=1.38`) on T weeks. The floor is a blunt volume cap:
lower floors win more orders but break on time (drivers are the binding constraint at level 8).
Idea: lower the floor and charge each request a capacity cost per driver-hour in the price choice
(`capLam` EUR x (drive hours + 1)), so long drives that tie up a scarce driver need a higher price.

## 14 Nov 04:37 · on T (BEST2), m-1..32, vs T
| variant | vs T | ± | better/worse | z | ranked | worst on time | orders |
|---|---|---|---|---|---|---|---|
| floor 1.28 | +327 | 187 | 20/12 | +407 | 31/32 | 89.4% | 442 |
| floor 1.28 + capLam 4 | **+730** | 206 | 24/8 | +1,221 | 32/32 | 93.0% | 389 |
| floor 1.28 + capLam 8 | -584 | 327 | 9/23 | -93 | 32/32 | 93.0% | 305 |
| floor 1.38 + capLam 4 | +196 | 221 | 14/18 | +687 | 32/32 | 92.5% | 350 |
Next: grid around floor 1.20 to 1.28, capLam 3 to 6.

## 14 Nov 04:45 · grid on T, m-1..32, vs T
| floor | capLam | vs T | ± | better/worse | ranked | worst | orders |
|---|---|---|---|---|---|---|---|
| 1.20 | 5 | +781 | 236 | 24/8 | 32/32 | 92.8% | 388 |
| 1.24 | 4 | +729 | 217 | 23/9 | 32/32 | 91.5% | 400 |
| 1.24 | 5 | +567 | 240 | 23/9 | 32/32 | 91.7% | 379 |
| 1.28 | 3 | +784 | 222 | 23/9 | 32/32 | 93.0% | 405 |
| 1.28 | 4 | +730 | 206 | 24/8 | 32/32 | 93.0% | 389 |
| 1.28 | 5 | +722 | 204 | 21/11 | 32/32 | 92.4% | 372 |
| 1.28 | 6 | +371 | 274 | 20/12 | 32/32 | 93.2% | 350 |
A flat plateau (+570 to +780) for floor 1.20 to 1.28 and 3 to 5 EUR an hour, every variant 32/32 ranked.
Candidate C = floor 1.28 + capLam 4 (`kit-max/CAND3.cfg`). Proof on h-1..48 started. Scarcity scaling
(`capTownExp`, `capDayW`) on top of C started on m-1..32.

## 14 Nov 04:50 · PROOF on h-1..48 (never used to choose)
| variant | margin | vs T | ± | better/worse | ranked | worst | orders |
|---|---|---|---|---|---|---|---|
| old best | 14,675 | -204 | 123 | 16/32 | 45/48 | 87.5% | 370 |
| T | 14,880 | | | | 45/48 | 89.2% | 378 |
| C | 15,481 | +601 | 165 | 32/16 | 47/48 | 89.3% | 382 |
Adopted: `kit-max/BEST3.cfg`.

## 14 Nov 04:54 · scarcity scaling on C, m-1..32, vs C (`T fl128 lam4`)
| knob | vs C | ± | better/worse |
|---|---|---|---|
| capTownExp 0.5 | -79 | 146 | 17/15 |
| capTownExp 1 | -92 | 164 | 16/16 |
| capDayW 0.5 | -163 | 159 | 11/21 |
| capDayW 1 | -473 | 161 | 7/25 |
| capLoadW 0.5 | +180 | 142 | 15/17 |
| capLoadW 1 | -72 | 176 | 17/15 |
The plain cost per driver-hour is enough; the booking model's own load and supply inputs already carry the rest.

## 14 Nov 05:26 · where the money is under C (`an/orders_profit.ts`, `an/drivers_used.ts`, `an/when.ts`; mJ C = C on m-1..32 with journals)
- 393 orders/wk, 16,047/wk. Net per order rises with drive hours (18 at under 1 h to 75 at 6 h) but net per
  driver-hour (drive + 1) stays 10 to 14 EUR in every segment: the capacity cost evens it out.
- Short trips (< 1 h): fee 1.04 x typical (fixed costs of the trip), 18 EUR an order, 107 a week.
- Same-day 36 EUR an order (6.2% late), next-day 44 (4.4%), 3-day 48 (1.2%).
- 21 orders a week lose money, -746 in total.
- Drivers: roster 640 to 880, 95% view our gigs, 126 to 285 book (20 to 36%). Margin follows that count.
- Gig starts per week: Mon 12, Tue 49, Wed 56, Thu 69, Fri 86, Sat 18, next Mon 37; evenings almost none
  (sites close 18 to 20, so day-job drivers cannot help).
