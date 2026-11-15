# Knowledge: what we believe now

## Where we are (14 Nov 09:00)
- Best now: **BEST16** (15 Nov 08:20) = BEST15 + fee-only booking shift 0.2 + steps 4, rampTop 1.45, costW 1.25, hardChance 0.82 + pairKm 40, pairHoldH 3: +515 ± 80 a week on 96 fresh server weeks, on time -0.4 points. In kit-best and kit-final (the final plays it).
- Before: **BEST15** (15 Nov 02:20) = BEST14 + `openTilt=0`. The model for the final: on time +0.8 to +1.1 points and no week under 90% in 54 fresh server weeks (BEST14: 7 of 60), margin flat. In kit-best and kit-final. BEST14 = BEST13 + lane level (`pLane=0.06`, about +300 a week).
- Best now: **BEST9** (14 Nov 17:45) = BEST8 + realized cost in the price choice (`costW=1`); see the ledger header. Before: **BEST8** (14 Nov 16:20) = BEST7 + price by deadline day; see the ledger header. Earlier text: **BEST5** = `kit-best/` defaults (14 Nov 15:35) = BEST4 + competitor price learned by weekday. +419 ± 101 a week over BEST4 on 80 fresh weeks (px, py), +544 ± 117 on BEST3 (pz). BEST4 again: `--set priceLearn=0`.
  BEST4 was about 15,640 a week over 208 fresh weeks (m, h, j, k).
  Gains so far: denoised typical fee (+200 to +400), capacity pricing (+600), day cap 0.10 (+190), weekday price learning (+420).
- The tuned config has converged: two coordinate passes and three random searches found nothing that survives fresh weeks.
- 20,000 a week was not reached. Shipped 14 Nov: weekday price learning (BEST5).

One line per belief. Confidence: HIGH = confirmed on fresh weeks, MED = one solid test, LOW = weak.
When a belief is overturned, move it to the bottom with the date and what killed it.

## Money
- Margin per week is about revenue 40k minus driver fees 24k minus refunds 0.8k; fees are the biggest lever (0.1 x typical = 2.5k a week). MED (baseline)
- The typical fee carries per-request noise, SD about 0.13 in log, that drivers mostly ignore: the booked fee moves with only 44% of it. HIGH (typ_denoise)
- Only 38% of our gigs book at the opening fee; the median booking is at 1.15 x the opening fee. Drivers wait for our raises. MED (honest_fees)

- Paying drivers from a lane-table typical fee instead of the noisy one (`typW=1`) earns about +200 to +400 a week; the gain is on the fee side, not the price side. HIGH (typ_denoise: m +403 ± 119, h +195 ± 128)
- A model refitted on our own policy weeks plays much worse (-1,100); a better log loss is not more margin. HIGH (typ_denoise)

- The booking model's fee plan is calibrated: posting every planned fee 5% higher loses 290 a week, 10% higher 720, 5% lower is even. HIGH (14 Nov feeScale)
- The tuned config sits on a broad plateau: one-knob and 3-knob moves are within noise; picks that pass 2 to 3 SE on one seed set fail on fresh weeks. HIGH (tuning)

## Prices
- Drivers are the binding constraint: 43% of quotes sat on the price floor. A lower floor (1.28) plus a capacity cost of about 4 EUR per driver-hour (drive hours + 1) in the price choice earns +600 to +800 a week and keeps weeks ranked. HIGH (capacity: m +730 ± 206, h +601 ± 165)
- Win odds fall about 10% per 1% of price; the competitor's level is 1.26 to 1.54 x list and differs every week. HIGH (kit-03 MODEL_REPORT)
- Buying dealer trust loses money, whether by lower prices (court, invest, trustGain), late-risk pricing (trustRisk) or dearer fees for trusted dealers (trustLate). D01's trust averages 14.5 of 25 at its requests (0.7 on Monday, 22 by Thursday) because trust counts only on delivery. HIGH (kit-ideas, kit-06, 14 Nov)
- Lane tables of the competitor price do not earn, even when they improve the forecast. MED (kit-09)
- Requoting one minute before the dealer decides earns nothing measurable (+65 ± 104 over 48 weeks). MED (requote)

- The competitor's price is a fixed number per request and world (same seed, many variants: 89% clean win/loss threshold). Its weekday level swings 12% (SD, log price) inside a week; learning one level per weekday from our own answers with that prior earns about +450 a week (py +506 ± 136, BEST3 pz +544 ± 117). Dealer levels add nothing; town levels unproven. HIGH (competitor, kit-price)

- An LLM deciding each price around the model's price earns nothing: DeepSeek V4.1 Flash (Featherless) picks the model's price in 99% of requests (+2 ± 93), JEV moves 16% of them cheaper (+69 ± 237), an hourly JEV supervisor -18 ± 194; hiding the expected profit from the LLM loses (-223 ± 151). MED (llm, 16 weeks, one base)

## Drivers and on time
- A driver's completed gigs predict whether they book us (34+ gigs: 1.34 bookings a week each; 0-2 gigs: 0.09), but weighting driver counts by it neither improves the booking model nor margin. MED (14 Nov)
- Weekly margin follows how many drivers ever book our gigs (126 → 11k, 285 → 25.6k a week), not how many see them (95% view). MED (capacity)
- Time on the board matters: posting late (12 to 24 h before the last pickup) loses 1,200 to 6,300 a week and breaks on time. HIGH (14 Nov delayed posting)
- Flat fees lose at every level tried (0.85 to 1.15 x typical): cheap ones miss drivers, dear ones overpay. HIGH (honest_fees)
- About 1 week in 20 falls under 90% on time; weeks with over 0.55 orders per driver hold the failures. MED (kit-09)
- Friday-due orders hold 40% of lates; a cap on orders per deadline day keeps weeks ranked at small cost. HIGH (kit-ideas)
- Direct offers rarely work (0.2 to 5% accepted); they do not unlock cheap drivers. HIGH (kit-04, kit-07, kit-cmb)
- Two cars on one driver save fees; unbooked pairs must be split after 4 hours or a third go late. HIGH (kit-09)

- Extra volume costs lates, not fees: +23% orders (kit-sim1) adds 1,100 a week of late refunds and 52 deadline warnings on the server; same-day orders go from 6.3% to 10.5% late. About 200 drivers a week carry our gigs and a few veterans do 5 to 8 gigs each. HIGH (sim_calib, 48 server weeks x 2 loads)
- Two local sims, each right on one thing: v4 (`sim/opt`) on fee and posting changes, v5c (`sim/cal`, `--sim "$(cat runs/lab/v5c.sim)"`) on load and on time. Screen an idea on both; 240 knob candidates around BEST8 found nothing that gains in both. MED (sim_calib)

## Overturned

## Notes (14 Nov, [notes](notes/LOG.md))
- HIGH: 42.5% of won orders have a note; 70% of notes are harmless and a note has at most one real effect, the rest is decoy text. No soft hint (urgent, call first, keys, wheels) changes the late share.
- HIGH: the reader is 97 to 99% right on ready, payment, deadline, plates and manual. The unread class is site hours (3.7% of orders): pickup-hours orders 14% late with 27 `closed` visits per 100, delivery-hours orders 19% late.
- HIGH: hours with no site named mean the pickup site; delivery hours always name the destination.
- MED: a regex reader is enough (99.7 to 99.9% on hours); a model in the loop reads no better where it counts.
- 14 Nov: "Learning the competitor live beyond the week level earns nothing" (price_learning). Killed by competitor: that test gave the day level a prior 8x too small (0.15 in log odds = 0.015 in log price; measured 0.12).
- MED: reading site hours (one-day stop windows that roll, last pickup inside real hours) plus keeping plates / manual cars out of pairs: +208 ± 70 on kit-best (96 fresh weeks), +227 ± 89 on BEST3 (48); failed visits 3.5 → 0.6 a week. In `kit-notes/` (`noteHours=1,pairFlags=1`), not yet in kit-best.

## Deadline days and first-day fees (14 Nov, [due_day](due_day/LOG.md), [raise_teach](raise_teach/LOG.md), [brake](brake/LOG.md))
- MED: pricing by deadline day (Monday-due -0.03, Friday-due +0.08 x list) earns about +120 ± 63 a week on 96 server weeks, ranked weeks unchanged. In kit-best as BEST8. Dearer Tue to Thu deadlines or dearer due-today options lose.
- HIGH: the first day of play is 3 to 4 points of typical fee cheaper (Monday 0.83, Thursday of a Thursday-start week 0.845, Thursday of a full week 0.88). A penalty on raises in the fee plan does not harvest it (server +30 ± 123, sim negative).
- MED: an on-time brake on quotes (stop tight options when the projected on-time share is low) saves no week: -16 ± 32 on the server.
- FACT: a Thursday-start week (as the test final) earns about 6,900 over Thursday and Friday on practice worlds with BEST7 (24 weeks, 23 ranked).


## Realized cost, bulk order, driver activity (14 Nov, [real_cost](real_cost/LOG.md))
- HIGH (server proof rd-1..48: +644 ± 106, 38/10, 48/48 ranked; blend 1.25 no better): the plan's expected fee is a poor guide to what an order ends up costing (held-out R2 0.06). Trees on quote-time inputs reach 0.27; using their cost in the price choice (`costW=1`) earns about +600 a week on BEST8 and BEST7 with orders nearly flat (server rc-1..16 +622 ± 178, +560 ± 169; sim +661 ± 53). In kit-best as BEST9. Biggest input: the size of the typical fee (cheap gigs cost more per euro of typical fee).
- MED (sim only): leaning the cost toward its 80th percentile (the friend's setting) and pricing each option by its own cost both do worse than the plain mean with one markup.
- FACT: the bulk order (35 cars, one yard, one dealer, Mon to Thu) costs us about 4 EUR an order more and is 1.6 points later than single requests on 12 orders won: a pool of about 50 a week.
- MED: counts of drivers who view our gigs follow our own load, not driver supply; they give no flu or scarcity signal.
- MED (recorded weeks, 400 worlds; no policy test yet): the flu day does show, in drops: 6 or more booked gigs dropped between 00:00 and 01:00 (normal days 0 to 2). On such days 9.4% of the orders due that day go late vs 4.3%, and we win as many orders as on a normal day. (flu, 14 Nov)

## Wild screen (14 Nov evening, [wild](wild/LOG.md), kit-wild)
- HIGH: opening a gig high and repricing down after 15 minutes loses 650 to 3,100 a week: the first viewers book at the high fee. Fees that fall do not pay inside one week.
- MED: cheaper slow options (within 3 days, next day) buy 10 to 20 orders a week that go late; dropping tight same-day options saves 2 lates and no margin; a deeper Monday-due discount (-0.08) loses.
- MED: live driver counts from gig_viewed add nothing beyond roster size and Monday orders; experienced-only audiences cannot pay (drop 12.8% vs 16.1%, a quarter of the supply).
- HIGH: a price floor that follows the learned competitor level (floorLvl=1, down only) earns about +220 a week (84 fresh server weeks +222 ± 58, BEST8 +216 ± 107, sim +330 ± 50) with 3 to 4% more orders and ranked weeks unchanged. In kit-best as BEST10.
- MED: a booking-speed price controller and a price-war floor cut both passed a 12-week screen (+240 to +320) and failed on 36 fresh weeks (-107 ± 70, +36 ± 69). A 12-week screen at 2 SE is a filter, not a result.
- MED: looking at a request again before the dealer decides earns nothing on BEST10: last minute +34 ± 160, plus a second look 7 minutes in +145 ± 173 (16 server weeks), sim 158 weeks -48 to +58 over 11 variants. (look)
- MED: a gig rebooked after a drop costs +0.20 x typical (507 EUR a week), but a fresh lower fee plan at the drop does not recover it on the server (+74 ± 94, +14 ± 115). The free release after `driver_late` is worth 3 EUR a week (0.17 events). (drop_replan, actions)

## Live test final and the outage (14 Nov night, [live_outage](live_outage/LOG.md), kit-out)
- HIGH: the outage is worth pricing as a hidden state. A belief over "none today" and "around town c" (30 towns, 80 km straight line) from today's answers, with the win chance mixed between the competitor's price and the backup's (x 1.2), earns about +350 a week: fresh server weeks +430 ± 144 on BEST11 (40 weeks, 31/9), +401 ± 124 on BEST10 (24), screen +238 ± 111 (32); ranked weeks unchanged. In kit-best as BEST12 (14 Nov 21:30), also in kit-final.
- HIGH: the old outage flag (answers within 80 road km, against the old win model) is fuzzy: on the live Thursday it fired outside the region too. The backup price on that flag earns nothing (+41 ± 92).
- FACT: stored server quotes: in outage town-days the win rate holds about 0.80 up to 1.2 x the day's competitor level and is 0.43 at 1.30 to 1.35: the backup sits near 1.3 x, the best price near 1.2 x.
- FACT: in the final every team plays the same requests, so the public feed shows which requests another team won (99.5% right on our own team for 38% of requests) and each team's cost share by day. Juhus: cost 59.2% of revenue vs our 62.6%; we are cheaper than Juhus on Tuesday and dearer from Thursday on. Top teams pay about 5 to 10% less per typical fee than we do; how is not known.
- MED: a lower price floor for cars that are cheap to move (typical fee under 0.8 x list) earns nothing (server -60 ± 113, sim -15 to -88), though Juhus wins 46% of them and we 20%.
- LOW: premium cars are not worth declining (net 36.5 vs 41.4 EUR an order on 28 practice weeks).
- HIGH: planned fees x 0.95 for gigs posted from Thursday on (`feeLate=0.95`) earn about +170 a week with orders equal: server fresh weeks +168 ± 45 on BEST12 (40), +156 ± 65 on BEST11 (24), screen +193 ± 56 (32); ranked weeks unchanged, on time 0.2 points lower. x 0.90 gains no more and costs on time. Early-day fee changes are flat in the sim. In kit-best as BEST13. (fee_day)
- MED: the price-war day as a state of the outage belief earns nothing (-172 ± 138, 32 server weeks); outageK 1.15 / 1.25 are worse than 1.2. (live_war)
- MED (15 Nov, juhus_gap second session, one final week + 10 public weeks): Juhus's lead (20.5k to 21k a week, 479 orders) is not pairs and not Monday to Wednesday. It is the dear tail from Thursday on: deliveries costing over 80% of their price are 26 to 35% of ours on Thu / Fri and 5 to 7% of Juhus's. Our orders booked at the opening fee cost 0.80 x typical, about Juhus's whole-week level; raises, drops and lates add 3,950 a week on top.
- HIGH (259,876 recorded bookings): a higher fee does not buy off drops (13.9% dropped under 0.7 x typical, 4.7% at 1.25 to 1.5; a drop costs 0.20 x typical).
- MED (700 recorded server weeks + both sims, no server test): the driver fee level of a week is learnable but small: SD 0.039 in log fee between weeks, Monday and Tuesday predict Wednesday to Friday with slope 0.39 (about 1.5% of fees); a pickup town's level inside a week does not persist. A live learner on it (cost or fees) earns nothing in the sims; fees that chase the level feed back on themselves. (drv_learn, 15 Nov)
- HIGH (15 Nov, final_safety, 70 fresh server weeks on BEST14, 40 on BEST13): the fee tilt (`openTilt=0.25`, BEST11) costs about 1 point of on time and earns nothing on BEST14: with `openTilt=0` margin +165 ± 92, on time +0.98 ± 0.15 points, ranked 68 vs 61 of 69 weeks, scored (unranked = 0) +1,833 ± 665. `openTilt=0.12` sits between (margin +293 ± 109, on time +0.57, 68 vs 63 of 71). Tighter `dueCapPer` 0.09 and `feeLate=1` add nothing on top. BEST14 itself loses 8 to 13% of fresh weeks to the 90% line on these sets.
- FACT (two live test finals, 14 Nov 20:00 BEST11 and 15 Nov 01:00 BEST14): place 6 of 75 (17,041, 96.8% on time) and place 5 of 41 (13,170, 92.8%). Week level moves all teams together (first place 19.6k then 14.1k), so judge a live week by the gap to the top, not by the margin. Our on-time share was the lowest or second lowest of the top 10 in both; the flu day (18 and 23 gigs dropped 00:00 to 01:00) starts the lates, yet only 3 of 14 and 6 of 25 late orders sat on a gig dropped in that hour: most lates are orders won on the flu day and the day before. (testfinal)
- MED: after `feeLate`, more fee cuts by time left to the last pickup earn nothing safe (server 32 weeks: x 0.95 over 36 h +73 ± 119; over 60 h +280 ± 131 with a ranked week lost). Lane learning + far fees on BEST13: -67 ± 149 (27 weeks). (fee_far)

## Lane level and the BEST13 screen (14 Nov late, [best13](best13/LOG.md), kit-b13, kit-b14)
- HIGH: the competitor's price has a level per lane and week (same-lane requests of one world correlate 0.18, SD about 9% of price; 64% of requests come on a lane already asked that week). One more filter level per lane (pLane=0.06) earns about +300 a week: BEST12 + BEST13 96 fresh server weeks +303 ± 83, ranked 95 vs 92; sizes 0.09 / 0.12 no better. In kit-best as BEST14.
- MED: no request feature moves the competitor's price by 2% (premium, electric, private address, batch, note, option kinds, typical fee / list: all under 1.2%, two samples of 1.5M quotes). Trust flattens toward 25 (+13 to 15% at 25, the model says +19%), but a flattening trust curve earns nothing on the server (-32 ± 112).
- MED: more data does not improve the realized-cost trees: refit on 897,535 orders (BEST9+ weeks) held-out R2 0.265 vs 0.247, server +144 ± 260 alone and nothing on top of the lane level; week-so-far inputs add nothing (0.266).
- MED: dead on BEST12 (16 server weeks each): dealer x weekday levels, town levels, pS 0.085, pairSlackH 2.5 / 4, lateFee 0.6, openTilt 0, price-war state, outageK 1.15 / 1.25.
- MED: the lane level of the week (`pLane=0.06`) is not proven: +428 ± 155 and +243 ± 131 on two fresh sets, -337 ± 129 on a third (st-1..32, kit-b13 itself, BEST12), pooled 96 weeks about +110 ± 85; on BEST13 -157 ± 151. Three 32-week sets of one knob can disagree by 700. (best13, 14 Nov night)

## On time (15 Nov, [on_time](on_time/LOG.md))
- FACT (300 recorded weeks, 19.1 lates a week): no driver before the last pickup time 8.2; booked in time but late 5.9; dropped 3.2; dealer changed the order 2.8 (22% of changed orders late). Drives of 4 to 8 hours are 18% of the orders and 45% of the lates. A gig unbooked at 20:00 on the evening before its pickup day is 12.6% late, a booked one 2.3%. Refunds 1,037 a week, 539 of it from cars over 24 hours late.
- MED (server, 16 fresh weeks on BEST14): an arrival buffer in the delivery window (45 to 90 minutes), a fee raise on the evening before the pickup day and a 22 hour delivery window for late cars do not lift on time (best +0.13 ± 0.25 points); the buffer at 45 minutes and the late window cost on time.
- HIGH: the fee tilt by gig size (`openTilt`, in BEST11 to BEST14) costs on time: without it +0.8 to +1.1 points on two fresh sets on BEST14 (and +0.5 to +0.8 on 5 older sets), margin flat. BEST14 fell under 90% in 7 of 60 fresh weeks. For a one-week final play `openTilt=0` (BEST15). (best15, final_safety, 15 Nov)
- MED: `bookShift=0.1` (the fee plan expects drivers to book a little sooner) earns about +220 a week with 7 more orders and 0.5 points less on time: BEST14 +218 ± 73 (98 fresh server weeks, ranked equal), BEST15 +247 ± 148 (33 weeks, one ranked week lost), BEST13 +217 ± 196. 0.15 and more lose ranked weeks. A margin lever that spends on-time safety; not in kit-best. (book_shift, 15 Nov)
- HIGH: on BEST15, 13 one-knob moves (ramp, steep, late fee, floor, hard options, day cap, capacity cost, cost blend, pairs) are all within noise on 48 + 64 fresh server weeks; two that passed 2 SE on the screen (rampTop 1.3, minBookChance 0.93) gave +19 and +7 on fresh weeks. `bookShift=0.1` is real margin (+340 over 145 weeks) but about 2 weeks in 100 turn unranked: a wash once an unranked week counts zero. (wide15, 15 Nov)
- HIGH: long hauls (list price over 160 or 200 EUR) and premium cars are profitable for us: declining them loses 160 to 840 a week on BEST15 (48 fresh server weeks) for 0.1 to 1.1 points of on time. Pricing long hauls higher changes nothing. (decline_long, 15 Nov)
- HIGH: the booking shift in the fee schedules only (`bookShift` with `bookQuote=0`) earns margin with orders unchanged on BEST15: 0.2 +273 ± 75 (96 fresh server weeks, 95/96 ranked vs 96) and +379 ± 99 (64 weeks, 64/64); 0.15 +152 ± 71 (96/96, worst week better); 0.3 no more than 0.2. The booking model is a little too pessimistic about how fast drivers book. In kit-out, not in kit-best. (book_shift, 15 Nov)
- HIGH: around BEST15 three steps hold on fresh server weeks, each on top of the one before: fee-only booking shift 0.2 (+320 ± 50, 224 weeks), then steps 4 + rampTop 1.45 + costW 1.25 + hardChance 0.82 together (+306 ± 59, 192 weeks; alone each is noise, steps 4 carries it), then pairKm 40 + pairHoldH 3 (+213 ± 70, 96 weeks). Kits kit-b16, kit-b17; none in kit-best as of the final. Single-knob screens after each step found nothing else. As ONE model against BEST15 (kit-b18): +515 ± 80 on 96 fresh weeks (wp), ranked 95/96 both, on time -0.40 ± 0.12 points, weeks under 92% on time 6 vs 3: the steps add up to about +500, not +830. (wide15, book_shift, best16, 15 Nov)
