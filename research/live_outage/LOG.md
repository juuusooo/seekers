# live_outage: log

## 14 Nov 19:59 · open
- **Hypothesis:** Test final live data (14 Nov 20:00): Thursday was an outage in the Helsinki region (108 requests, we won 79% at 1.61 x list at the fixed 1.58 floor, wins held to 1.9); Juhus won fewer there and paid 7 points less of revenue on Friday deliveries. Pricing against the backup (competitor x 1.3) in a detected outage earns +200 or more a week and eases the Friday load. Second: Juhus wins 46% of cars with typical fee under 0.7 x list (78 a week), we 20%: a lower floor for cheap-to-move cars
- **Base, seeds, metric:** kit-out = kit-best BEST11 + outageK, floorTyp (default off); server fresh seeds lo-1..16 screen same weeks (base, outageK 1.3, floorTyp 0.5, both), then 36+ fresh weeks on BEST11 and BEST10 for survivors; mean diff ± SE, better/worse, ranked, worst on time, orders
- **Kill criteria:** screen under +150 or fewer ranked weeks; proof under 2 SE
- **What I did:**
- **Result / verdict:**
- **Next:**

## Work notes (14 Nov, late evening)

Data: `runs/testfinal_1114_2000/` (our events, reveal, snapshot; public leaderboard feed every 2 s). In the final every
team plays its own copy with the same requests, so the feed gives more than the scores:

- **Which requests another team won.** A team's `wonOrders` rises at a request's `respondBy`. Check on our own team:
  393 of 1,030 requests get an exact label from the feed, 99.5% right. Juhus: 369 labelled.
- **Cost share by delivery day** (revenue minus margin, over revenue, from the feed): us Tue 57.7, Wed 58.4, Thu 69.0,
  Fri 60.9, Sat 71.7, next Mon 64.3%; Juhus 62.3, 57.9, 62.9, 53.0, 57.4, 61.6%. We are cheaper early and dearer
  from Thursday on. Whole week 62.6% vs 59.2%.
- **Win rate by day** (requests 219 / 204 / 221 / 207 / 179): us 37, 48, 31, 57, 40%; Juhus 50, 49, 36, 49, 44%.
- **Thursday was the outage, Helsinki region** (pickups within 80 km: 108 requests, we won 79% at a median 1.61 x list;
  outside 38%). Our quotes sat on the fixed floor 1.28 + 0.30 = 1.58 (next day 1.55, same day 1.66). Wins by price that
  day: 1.56 to 1.7 75%, 1.7 to 1.9 84%, 1.9 to 2.2 38%, above 0%. We won 118 orders that day (Juhus 102), then had
  30 to 57 orders without a driver on Thursday and Friday and 10 late orders due Thursday.
- **Stored server quotes (23.9M, 940 seeds):** in outage town-days the win rate stays about 0.80 up to 1.2 x that day's
  competitor level, 0.60 at 1.25 to 1.30, 0.43 at 1.30 to 1.35 (normal days: 0.46 at 1.0 to 1.05, 0.15 at 1.2 to
  1.25). So the backup really sits near 1.3 x the competitor, and the best outage price is about 1.2 x the day level.
  The fixed floor 1.58 is right only in a week with a level near 1.3; the level's quartiles are 1.27 and 1.52.
- **Cheap-to-move cars** (typical fee under 0.7 x list, mostly Helsinki / Espoo / Vantaa, 78 requests): we won 20%,
  Juhus about 46%. On Monday we lost them at 1.20 to 1.24 x list, the floor. Practice weeks: orders with a typical fee
  under 20 EUR net 19 EUR each at a price of 38 EUR.
- **Not a lever:** premium cars (Juhus won 0 of 13 labelled, we 31%): our practice net is 36.5 vs 41.4 EUR an order,
  still positive.
- Rough level estimates from the feed (biased the same way for all teams): revenue / list us 1.30, Juhus 1.29; cost /
  typical fee us 0.86, Juhus 0.81, Progresful 0.79, Moonshot 0.77.

Knobs in `kit-out/` (copy of kit-best BEST11, both default off):
- `outageK`: in a detected outage the win chance is read against competitor x K (and the price filter learns against
  it, so the weekday level does not drift up). 1.3 = handbook.
- `floorTyp`, `floorTypRef`: floor shift -floorTyp x (floorTypRef - typical / list) when positive.

Local sim v4, 158 weeks (not a judge for the outage: its outage is a fitted offset on the old win model, no backup
seller): outageK 1.3 -126 ± 52, 1.2 -35 ± 49, floorTyp 0.5 +54 ± 38, 1.0 +49 ± 39, both -84 ± 52.

Server screen lo-1..32 (tag lo1, rows carry kit "kit-best" because week.ts writes that name): base, outageK=1.3,
floorTyp=0.5.

### Server screen 1 (lo-1..32, tag lo1, BEST11 base 17,194, 30/32 ranked, worst on time 85.9%, 421 orders)
- outageK=1.3 on the old detector (outageN / outageGap flag): +41 ± 92 (16/16), 30/32 ranked, orders 422. Fails the screen.
- floorTyp=0.5: -60 ± 113 (18/14), 30/32 ranked, orders 424. Dead.
- Why the outage price did little: the old flag is fuzzy. On the live Thursday it also fired outside the Helsinki
  region (median quote 1.58 on 86 requests outside it, 38% won): it looks at answers within 80 road km of the pickup,
  so it chains from town to town, and it measures against the old win model, so a dear day looks like an outage.
  A 30% dearer price on those false flags gives the gain back.

### Region belief (`outBayes=1`, needs `outageK`)
The outage as a hidden state: belief over "none today" and "around town c" (30 towns, straight-line 80 km sets in
`core/data/near80.json`), from today's answers scored against the price filter as it stands now. Prior for an outage
today: 1 / working days left, at most 0.6, none after a day that ended with belief over 0.9. The win chance is the
belief-weighted mix of the competitor's price and the backup's (x outageK); the filter learns against the expected
price. Off = kit-best to the cent (sim 158 weeks, difference 0).
Sim v4 (no backup seller in it, weak judge): K 1.3 +21 ± 61, K 1.2 +154 ± 51 (old flag with K 1.3: -126 ± 52).

### Server screen 2 (same lo-1..32 weeks, base 17,194, 30/32 ranked)
- outBayes=1, outageK=1.2: +238 ± 111 (20/12), ranked 29/32 vs 30, worst on time 88.0% vs 85.9%, orders 427 vs 421, z -126.
- outBayes=1, outageK=1.3: +119 ± 138 (20/12), ranked 30/32, worst 84.6%, orders 427, z +155.
- K 1.2 passes the +150 screen at 2.1 SE; picked on these weeks, so it needs fresh weeks. Proof started: lp-1..40
  (BEST11 base vs ob12) and lp-1..24 on BEST10 (openTilt=0), tag lp1.
