# juhus_gap: log

## 14 Nov 21:28 · open
- **Hypothesis:** Juhus beats us by about 2,500 a week on the same weeks with driver cost 60.7 vs 66.3 EUR an order (20:00 test final). Split the gap into car mix vs cheaper drivers from the public feed + reveal, find where our cost goes by day, then a price shape by request day / deadline slack / load that closes part of it: +500 or more a week on BEST12
- **Base, seeds, metric:** study: runs/testfinal_1114_2000 (feed, reveal, events), local; knobs in own kit copy of kit-best BEST12 (default off); server fresh seeds 16 same weeks screen on BEST12 and BEST11, survivors 48 fresh; mean diff ± SE, better/worse, ranked, worst on time, orders, cost per order
- **Kill criteria:** screen under +200 or fewer ranked weeks; proof under 2 SE on either base
- **What I did:**
- **Result / verdict:**
- **Next:**

## Work notes (14 Nov, 22:00 to 22:40 Helsinki)

Data: `runs/testfinal_1114_2000/` (feed 1,037 running frames about 7 world minutes apart, reveal, our events). Scripts
`load.py`, `wins.py`, `cost.py` here. Feed facts checked on our own team: `wonOrders` steps at `respondBy` (438 of 438),
revenue and driver fee both book at the gig's last delivery.

**Per order, whole week:** Juhus 469 orders, revenue 102.5, cost 60.7; us 431, 105.8, 66.3. Same total driver money
(28,475 vs 28,576), 38 more cars.

**Who wins what (interval counts, least squares; small cells are noisy: our own premium cell reads 0.54 vs true 0.34):**
- By request day (219 / 204 / 221 / 207 / 179 requests): Juhus 0.51, 0.49, 0.34, 0.55, 0.42; us 0.37, 0.48, 0.31, 0.57,
  0.40. The whole order gap is Monday: about 112 vs 82.
- Monday by our quote: at 1.26 x list or less (73 requests) we won 48%, Juhus 81% (26 labelled). Half our Monday quotes
  sat on the floor (median 1.295). Juhus prices under our floor on a cheap Monday.
- Wednesday (price-war day): we quoted 1.26 or less on 94 requests, won 34%, Juhus 26%.
- All top teams but us avoid premium cars and list prices over 200.

**Our cost by segment (fee / raw typical fee, net per order):**
- By day won: Mon 0.862 (net 33.5), Tue 0.869 (38.2), Wed 0.914 (27.7, drops 0.39 an order), Thu 0.946 (57.7 at
  1.67 x list), Fri 0.939 (33.5).
- Gigs by day posted: opening fee 0.80 x typical every day Mon to Wed, booked fee 0.87 / 0.89 / 0.94 / 0.99 / 0.99;
  booked at the opening fee 64 / 60 / 44 / 46 / 52%.
- Won Wednesday, delivered Thursday (38 orders): fee 0.96, 0.58 drops an order, cost share 72%, net 25.8.
- Thursday outage orders are the best of the week (net 57 to 83): not an overload to avoid.
- Dropped once: fee 1.085 x typical and 7.4 EUR refunds vs 0.876 and 1.1 (66 orders, about 1,300 a week).

**Cost share by delivery day (feed):** biggest gap is Friday deliveries (revenue 14k): us 60.9%, Juhus 53.0% (about
1,100 of the 2,550); Saturday 71.7 vs 57.4, Thursday 69.0 vs 62.9; Tuesday we are better (57.7 vs 62.3).

**Read:** Juhus takes more cars on Monday (and Tuesday) at prices under our floor, when drivers book at the opening
fee, and pays less from Thursday on. Mix vs fee cannot be split cleanly: the feed labels are biased toward dear cars
(our own typical fee per order reads 75.9 vs true 70.1).

**Knobs (kit-jg, default off):** `floorEarly` (floor and search range lower for requests arriving on the first
`earlyDays` days), `capEarly` / `capLate` (capacity cost x on early / later days).
Server screen jg-1..24, tag jg1: base, markupMin 1.22 (backlog lead +704 ± 192 on 12 weeks), floorEarly 0.06 / 0.10,
capEarly 0.5, floorEarly 0.06 + capEarly 0.5, capLate 1.5.

### Side checks while the screen runs (22:40 to 23:00)
- **Outage price factor, again (dead, no new test).** Thursday by our quote bucket: at 1.55 to 1.80 x list we won 71%,
  Juhus 58%; over 1.80 we 42%, Juhus 26%: Juhus prices the outage higher than we do. Stored quotes (`backup2.py`,
  217 seeds with an outage day, cells picked by their win rate so the level is biased up): the backup follows the
  week's level, not the list price (cheap weeks fall off at 1.8 x list, dear weeks hold 0.60 at 2.2). Server already
  said no to a higher factor on BEST12: outageK 1.25 -75 ± 86 (27 weeks, lq1), 1.3 -119 ± 110 (32 weeks, lo1).
- **Feed steps cannot be matched to requests** (`match.py`): prices are not on a 0.01 grid of the list price (our own
  unique matches: 0 of 6 right). Juhus's fee per order stays unknown; only cost share by delivery day is readable.
- **Fee tilt and on time (existing rows, same weeks, outage belief on):** openTilt 0 vs 0.25: -189 ± 134 (40 weeks,
  lp1 + ba1), on time mean 96.7 vs 96.1%, worst 93.1 / 94.2% vs 90.4 / 91.5%, weeks under 92%: 0 vs 2. BEST12 pooled
  (lo1, lp1, lq1, ba1, bb1): 124 of 128 weeks ranked (3.1% score nothing), 10 weeks under 92%.
- **Restart in the final:** `run.ts --final` rejoins by itself, but `rejoin()` cannot rebuild the price filter or the
  outage belief (the quotes we made are not in the events), so both start cold after a break.
- Note hours (`noteHours=1,pairFlags=1`) are already in kit-best since BEST7; the KNOWLEDGE line saying "not yet in
  kit-best" is stale.

## Second session (15 Nov 00:10 to 01:00 Helsinki): where the gap sits, from feed steps

Scripts `s2_*.py` here (they read / write pickles in that session's scratchpad: change the paths to rerun).
No game weeks played. Data: test final 20:00 feed + our events, public level 8 rankings, 794 recorded weeks.

- **Juhus is steady, not lucky.** Public level 8 rounds 9 and 10 (Saturday 21:00, Sunday 00:00): 21,085 and 20,516
  a week, 10 of 10 weeks ranked, on time 93 to 99%, 454 to 517 orders (mean 479). Next best 19,370 (MathNet1) and
  16,538 (upsala).
- **Not pairs.** Revenue books at each order's delivery, the fee at the gig's end, so revenue in a feed frame with no
  cost step = first car of a multi-car gig. Share of revenue: us 4.7%, Juhus 3.2%, eth 13.6%, akanegakirru 14.5%,
  bob-the-builders 0%.
- **Not Monday to Wednesday.** Cost share of deliveries by day, us vs Juhus: Tue 57.7 / 62.3, Wed 58.4 / 57.9,
  Thu 69.0 / 62.9, Fri 60.9 / 53.0, Sat 71.7 / 57.4, next Mon 64.3 / 61.6.
- **It is the dear tail from Thursday on.** Feed frames with a delivery whose cost is over 80% of its revenue:
  Thu 35% us vs 5% Juhus, Fri 26% vs 7%, Sat 31% vs 18%. Frames under 50%: Fri 25% vs 44%, Sat 8% vs 55%,
  next Mon 0% vs 21%. Whole week, cost / revenue per frame: median 0.642 vs 0.588, upper quartile 0.759 vs 0.675.
- **Our own tail (truth):** 224 orders booked at the opening fee pay 0.80 x typical (cost 55% of price). Raised: 122
  orders at 0.96 (1,745 EUR over the opening level). Dropped once or more: 67 at 1.07 (1,123). Late: 14 (999).
  Sum 3,950 a week; the gap to Juhus is 2,550, and Juhus's whole-week cost is about our opening level (0.81).
- **Thursday deliveries:** Juhus delivered 4,718 of revenue, we 6,005 (flu day, day after the price war), and ours
  cost 69%.
- **Dead here:** paying more to stop drops. 259,876 single-car bookings: drop share falls only from 13.9% (fee under
  0.7 x typical) to 4.7% (1.25 to 1.5), flu drops left out; a drop costs 0.20 x typical, so 0.1 more fee saves 0.003.
- **Fact, recorded weeks:** a gig booked on the day it is posted pays 0.90 to 0.97 x typical, one booked the next day
  1.12 to 1.26 (about 9 gigs a day roll over). Friday posts pay 1.10 (Monday 0.93); 18 a week book on Saturday at
  1.15 and 25% of those are dropped.
- Floor proof of the first session (jh1, 48 weeks, read from bench.jsonl): floorEarly 0.10 +49 ± 112, markupMin 1.22
  +76 ± 115 on BEST12: dead.
