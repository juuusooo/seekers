# supply: driver-supply models instead of the fixed capacity steps

14 Nov, late evening. Local sim only (Rust copy, BEST10 port). No server weeks: this machine has no team key.
Not in `LEDGER.md` yet: `log.py` needs Linux (`fcntl`). Suggested row at the bottom.

## Question

Is the model too careful early in the week (drivers free) and too greedy late (drivers short)? Do models of driver
supply beat the fixed steps (`capPerDriver`, `dueCapPer`, `fullPrice`, constant `capLam`)?

## Prior work (recall)

Server, all no-edge: capacity cost rising through the week (`capWeekSlope`), scaled by town / busy day / own load /
roster, on-time brake on quotes, booking-speed price controller, idle-town floor cut, cheaper slow options.
New here: a regional ball, smooth curves, a quotient capacity cost, a price shift by request day, and a two-sided
live backlog rule (the old controller and brake only made the model pickier).

## Models (knobs in `simrs/src/desk.rs`, all off by default; off = BEST10 to the cent on 158 weeks)

| Tag | Knobs | Idea |
|---|---|---|
| W | `wkMon`, `wkTue`, `wkLate` | Price shift (x list) by the day the request arrives: greedier early, pickier late |
| B | `ballKm`, `ballIn`, `ballGauss` | Supply and our open orders counted in a ball around the pickup: full weight inside 30 km, linear or Gaussian fall-off |
| S | `smoothS`, `smoothAt` | Logistic curve in utilisation instead of the full-town and full-day steps |
| Q | `capU` | Capacity cost / (1 - capU x town utilisation), capped |
| L | `backK`, `backAt`, `backDown`, `backDueH` | Live backlog: price shift = backK x (our orders without a booked driver / roster - backAt), cuts allowed down to -backDown |
| C | old knobs only | Control: the tuned baseline gets the same search (floor, `capLam`, `dueCapPer`, `fullPrice`, `capPerDriver`) |

## Method

- Two worlds: v4 (default) and T (`--sim workPow=3.2`, a stand-in for v5c, whose parameter file is not in the repo:
  227 drivers book a week, 95.0% on time, late refunds 845). Final check also on T2 (`workBase=0.07,workGig=0.1,workPow=2`).
- Search weeks m-1..48 + h-1..48 (96). Held-out weeks k, rd, sv (158), never used to pick a value.
- Score for picking: margin minus 3,000 EUR per point of on time under 93%, mean of both worlds. Also reported:
  plain margin, scored (unranked week = 0), orders, ranked weeks, worst on time.
- 145 variants on the search weeks (`variants/s1.txt`, `variants/s2.txt`), then one pre-chosen setting per model and their
  combinations on the held-out weeks (`variants/s3.txt`), then the survivors on all 254 weeks in three worlds (`variants/s4.txt`).

## Results

Search weeks, best of each model (pooled smooth score, EUR a week):

| Model | Best on search weeks | Note |
|---|---|---|
| W | +153 ± 59 (`wkMon=-0.12,wkTue=-0.04`) | Monday cuts gain, pickier Thursday and Friday never gains (-54 to +3) |
| B | -13 ± 56 (best of 21) | The ball changes almost nothing: the full-town rule rarely binds |
| S | +25 ± 90 (`smoothS=0.2,smoothAt=1.6`); centred at 1: -95 to -1,069 | A curve centred on the old step prices up half-loaded towns and loses volume |
| Q | -108 ± 78 (best of 6) | Dead |
| L | +199 ± 70 (`backK=8,backAt=0.04,backDown=0.06`), plateau +100 to +190 | The gain needs the cut side; rise-only is about zero |
| C | +95 ± 70 (`markupMin=1.2`), +67 ± 61 (`dueCapPer=0.11`) | |

Held-out weeks (158), pre-chosen settings: L = `backK=6,backAt=0.04,backDown=0.08`, W = `wkMon=-0.10,wkTue=-0.04`.

| Variant | Pooled smooth | v4 margin | T margin | T ranked (base 155) |
|---|---|---|---|---|
| L | +53 ± 64 | +31 ± 54 | +18 ± 60 | 156 |
| W | +71 ± 71 | +59 ± 54 | +69 ± 59 | 156 |
| C `dueCapPer=0.11` | +162 ± 36 | +168 ± 35 | +164 ± 38 | 155 |
| C `markupMin=1.2` | +75 ± 72 | +132 ± 53 | +105 ± 60 | 153 |
| L + W | +66 ± 73 | +84 ± 53 | -32 ± 58 | 157 |
| W + `dueCapPer=0.11` | +251 ± 66 | +219 ± 56 | +259 ± 50 | 156 |
| L + W + `dueCapPer=0.11` | +188 ± 86 | +268 ± 51 | +101 ± 69 | 155 |
| L, rises only | -12 ± 44 | +6 ± 36 | -119 ± 39 | 156 |
| B `ballKm=80,ballGauss=1` | +15 ± 53 | +19 ± 34 | +22 ± 42 | 156 |
| S `smoothS=0.2,smoothAt=1.6` | +152 ± 61 | +285 ± 54 | +204 ± 52 | 155, worst on time 89.2% |
| Q `capU=0.2` | -147 ± 68 | -131 ± 45 | -58 ± 49 | 154 |

All 254 weeks, margin difference a week (smooth score in brackets):

| Variant | v4 | T | T2 (scarce) | Orders (v4) |
|---|---|---|---|---|
| L | +56 ± 40 | +61 ± 44 (+155 ± 86) | -8 ± 48 (+257 ± 112) | +2 |
| W | +89 ± 41 | +140 ± 44 (+151 ± 89) | +27 ± 48 (-9 ± 105) | +4 |
| `dueCapPer=0.11` | +140 ± 26 | +148 ± 29 (+126 ± 57) | +128 ± 28 (+29 ± 72) | +3 |
| W + `dueCapPer=0.11` | +240 ± 41 | +267 ± 39 (+226 ± 88) | +164 ± 48 (+49 ± 116) | +7 |
| W + due + L | +253 ± 38 | +151 ± 51 (+99 ± 120) | +76 ± 48 (+262 ± 115) | +7 |
| W + due + S | +388 ± 43 | +311 ± 48 (+43 ± 117) | +263 ± 52 (+105 ± 105) | +10 |

## Verdict

- No supply model shows a gain that holds on the held-out weeks. L and W each fell from about +190 on the search
  weeks to +50 to +70 (under 1.1 SE): best-of-many picks, as GOTCHAS says.
- The ball (B) and the quotient cost (Q) are dead in the sim. The smooth curve (S) only gains when it is looser
  than the old step, which is more volume and a lower worst week.
- "Too careful on Monday" has weak support (W +89 ± 41 on 254 weeks in v4, +140 ± 44 in T, nothing in the scarce
  world). "Too greedy late" has none here: every pickier Thursday / Friday setting was flat or negative. The sim has
  no backup seller, so it cannot show the outage over-buy that BEST12 already targets.
- The most consistent candidate is W + `dueCapPer=0.11` (+164 to +267 margin in three worlds, 173 of 254 weeks
  better in v4). But `dueCapPer=0.11` is an old knob that the sim is known to overrate (looser cap = more orders;
  the server tuner kept 0.10), and under scarcity its gain vanishes once on time is priced in (+49 ± 116).
- L is the only variant that helps the on-time-priced score when drivers are scarce (+257 ± 112 in T2, fewer
  orders): a safety device, not a margin gain.

## Next

Server, same fresh weeks, 48 weeks, on BEST10 and on BEST12: (1) `wkMon=-0.10,wkTue=-0.04`; (2) the same with
`dueCapPer=0.11`; (3) L as safety. The knobs must first be ported to `algo.ts` (they exist only in the Rust copy).

## Rerun

```sh
cd Bahn-Spread/research/supply/simrs
CARGO_TARGET_DIR=<a folder outside the repo> cargo build --release      # sim-experimental/target is tracked: never build there
cd .. && SIMB=<that folder>/release/sim-experimental python stage.py search variants/s1.txt s1   # or: held
```

Variant lists and result tables are in `variants/`; raw rows go to `out/` (gitignored).

`simrs/` is a copy of `sim-experimental/src` (BEST10 port) with the knobs above and a clock call that also builds on
Windows. Data and `static.json` are read from `sim-experimental/`.

Suggested ledger row: `supply | no-edge | LOCAL SIM ONLY (Rust copy, BEST10, v4 + workPow 3.2). Driver-supply models
vs the fixed steps, search m,h (145 variants), held out k,rd,sv 158 weeks: backlog rule L +53 ± 64, Monday / Tuesday
price cut W +71 ± 71, ball -13 to +15, quotient capacity cost -147 ± 68, smooth curve gains only when looser.
W + dueCapPer 0.11 +251 ± 66 held out (254 weeks: v4 +240 ± 41, tight +267 ± 39, scarce +164 ± 48, on-time-priced
+49 ± 116) | nothing proven; server test of W and W + dueCapPer 0.11 is the open step`.

## Cost trees: refit recipes and a live correction (14 Nov, midnight, local sim only)

Question: can the realized-cost trees (BEST9, `core/data/cost.json`) be fitted better? The training rows of the shipped
trees (`runs/rc/rows.jsonl`) are not on this machine, so every recipe was fitted on rows from the local sim and judged
against the shipped recipe fitted on the same rows (R0). Tools: `simrs --rows` (one line per won order: the 38 inputs,
fees, other costs, late flag), `simrs --cost FILE` (other trees), `costfit.py`, `costeval.py`, `costdrift.py`.

- Rows: m, h seeds x 4 policies (base, floor 1.20, capLam 3, capLam 5), 169k orders per world. Judge: k, rd, sv (158 weeks).
- The sim's cost is far easier to predict than the server's (held-out R2 0.57 to 0.61 against 0.27): its drivers
  price a gig by a formula. Differences between recipes are the result here, not the level.

| Recipe (against R0, margin a week) | v4 | T | Note |
|---|---|---|---|
| R1 rows weighted by typical fee | +50 ± 41 | -4 ± 46 | |
| R2 monotone (load, open orders, due load up; slack, hours left down; plan fee up, plan chance down) | +6 ± 38 | +53 ± 38 | |
| R3 weights + monotone | +77 ± 45 | +40 ± 42 | pooled about +58 ± 31 |
| R4 two heads: fees + everything else | +26 ± 39 | -29 ± 41 | |
| R5 two heads + late order costs 0.5 / 1.0 x typical more | -80 ± 52 / -140 ± 56 | -96 ± 45 / -214 ± 50 | orders -7 to -17, on time +0.1 to +0.8 pt, worst week 94.3% -> 96.0% in T |
| R6 bigger trees (600, 31 leaves) | +82 ± 45 | +39 ± 43 | |
| R7 weights + monotone + late 0.5 | -63 ± 48 | -136 ± 47 | |

- Sim-fitted trees against the shipped (server-fitted) trees: +630 ± 71 (v4), +914 ± 90 (T). Not a forecast of a
  server refit: the sim-fitted trees know the sim's driver formula, the shipped ones know the server.
- Trees fitted in the other sim world play like trees fitted in their own (+30 ± 57 in T, +84 ± 49 in v4).
- Live correction (`resK`: add the mean of realized minus predicted cost of this week's delivered orders): the mean is
  below zero in every setting, because the orders delivered so far are the ones that booked early and cheaply. It
  lowers the cost, wins 10 to 20 more orders, gains in v4 (+167 ± 45) and loses in T (-131 ± 51). Biased as built.

Verdict: no recipe change is proven. Weights + monotone and bigger trees are small and positive in both worlds (under
2 SE); a lateness charge trades margin for on time; the live correction needs a version that counts orders still open.
Next: refit R0 / R3 / R6 on the real rows (and on BEST11+ weeks, whose fee tilt changed what cheap gigs cost) and play
them on the server.

## Price learner: prior and learning speed (15 Nov 00:30, local sim only)

Question: does the model lose Monday requests because it starts the week not knowing the competitor's level? Would a
better prior or faster early learning fix it? Knobs of the price filter (`pWeek`, `pDay`, `pS`), a start level
(`pMean`) and two sim-only oracles (`oraWeek`, `oraDay`: start at the week's true level, and at each weekday's).
All 254 weeks, both worlds (`variants/prior.txt`, table `variants/prior_table.txt`). Margin a week:

| Variant | v4 | T |
|---|---|---|
| Wider week prior `pWeek` 0.08 / 0.12 / 0.2 (faster learning) | +32 ± 34 / +88 ± 36 / +45 ± 40 | +56 ± 34 / 0 ± 40 / -1 ± 43 |
| Narrower `pWeek` 0.03 | +6 ± 27 | +12 ± 34 |
| Day prior `pDay` 0.10 / 0.20 / 0.28 | +18 / -5 / -48 | -11 / -9 / +24 |
| Sharper or flatter dealer choice `pS` 0.07 / 0.13 | +185 ± 50 (orders +36) / -479 ± 45 | -71 ± 54 / -238 ± 54 |
| Start level `pMean` -0.03 / -0.015 / +0.015 / +0.03 | +60 / -6 / +28 / +47 | +38 / +63 / -62 / -29 |
| Oracle: true week level from minute 0 | +31 ± 36 | +31 ± 40 |
| Oracle: true week and weekday levels | +47 ± 36 | +108 ± 43 |

- Weekly level across the 254 weeks: SD 0.064 in log price (the prior says 0.05); roster size does not predict it
  (correlation -0.08), so nothing seen at the start of the week gives a better starting point.
- Even knowing the week's level from the first minute is worth about +30 a week: the filter has it after the first
  hour of answers. Knowing every weekday's level in advance (not possible live) is worth +50 to +110.

Verdict: no edge. The start of the week is not a price-learning problem in the sim.

## SERVER: supply variants on BEST12 (15 Nov 00:33, su-1..48, tag su1)

kit-supply = kit-out (BEST12) + knobs `wkMon`, `wkTue`, `wkLate`, `backK`, `backAt`, `backDown`, `costAlt` (all off).
Key of Bahn-RL-lab, 8 practice worlds at a time, 336 weeks, none failed. Same fresh weeks for every variant.
Rows `server/su1.jsonl`, table `variants/su1_table.txt` (`python scmp.py su1`). Base 17,717, 431 orders, 45/48 ranked,
mean on time 95.2%, worst 87.5%.

| Variant | Difference a week | Better / worse | Scored (unranked = 0) | Orders | Ranked | Worst on time |
|---|---|---|---|---|---|---|
| `dueCapPer=0.11` | +201 ± 76 | 26 / 11 | +496 | 436 | 46/48 | 88.6% |
| W (`wkMon=-0.10,wkTue=-0.04`) + `dueCapPer=0.11` | +258 ± 107 | 32 / 16 | +273 | 440 | 45/48 | 88.3% |
| L (`backK=6,backAt=0.04,backDown=0.08`) | +162 ± 117 | 27 / 21 | +537 | 435 | 46/48 | 86.9% |
| W + `dueCapPer=0.11` + L | +153 ± 130 | 27 / 21 | -353 | 439 | 43/48 | 86.2% |
| W mild (`wkMon=-0.05,wkTue=-0.02`) | +96 ± 135 | 25 / 23 | -207 | 434 | 44/48 | 87.7% |
| W | -70 ± 119 | 25 / 23 | -306 | 435 | 44/48 | 87.8% |

Verdict: the Monday / Tuesday price cut is dead on the server (the sim said +89 to +140). `dueCapPer=0.11` is the one
gain over 2 SE (2.6 SE, one more ranked week); it is an old knob, last proved at 0.10 on BEST3. W adds nothing to it
beyond noise. The backlog rule L is +162 at 1.4 SE: not proven. Confirmation of `dueCapPer=0.11` on second fresh
seeds: ct-1..48 (tag ct1), running.

## Driver fees by day (15 Nov 00:35, 49 recorded BEST12 base weeks of su1, `feeday.py base`)

Question: do drivers take gigs for less on Friday and at the weekend? Observational (we set the fees).

| Day the driver booked | Gigs a week | Fee paid (x typical) | Booked at the opening fee | Median wait |
|---|---|---|---|---|
| Mon | 58.9 | 0.856 | 68.7% | 0.2 h |
| Tue | 68.1 | 0.907 | 56.5% | 0.6 h |
| Wed | 71.0 | 0.924 | 52.4% | 1.0 h |
| Thu | 77.3 | 0.928 | 52.3% | 0.9 h |
| Fri | 57.1 | 0.992 | 50.4% | 1.1 h |
| Sat | 18.0 | 1.084 | 2.2% | 14.1 h |
| Sun | 1.7 | 1.076 | 12.9% | 34.5 h |
| next Mon | 10.5 | 1.158 | 5.8% | 62.3 h |

First looks that end in a booking by that driver, at the same fee on screen: Mon 2.7% (fee under 0.8 x typical) to
7.8% (1.1 to 1.3), Tue to Thu 2.1 to 2.4% and 4.4 to 5.2%, Fri 1.4% and 2.8%, Sat 1.7% and 3.7%, Sun 0.6% and 2.3%.

Verdict: no. Friday and the weekend are the dearest days, and at the same fee a look on Friday is about half as likely
to become a booking as on Tuesday to Thursday. Monday is the cheapest day. Sunday has almost no bookings (1.7 a week).

## Cost trees refitted on real BEST12 weeks (15 Nov 00:36)

Rows from our own su1 weeks (`rows.ts`: 336 worlds, 146,390 won orders, same replay as research/real_cost/build.ts),
`costfit_server.py --write`, held out every fourth seed (36,390 rows):

| Trees | R2 of the realized cost | Mean predicted (actual 0.985) | Dearest tenth predicted / actual |
|---|---|---|---|
| Plan fee alone | 0.050 | | |
| Shipped (fitted on BEST6-8 weeks) | 0.260 | 0.952 | 1.36 / 1.49 |
| Shipped recipe refitted (costAlt=1) | 0.299 | 0.973 | 1.49 / 1.52 |
| Weights + monotone (2), bigger (3), both (4) | 0.292 to 0.297 | 0.970 to 0.972 | 1.48 to 1.50 / 1.50 to 1.52 |

The shipped trees still hold on BEST12 weeks (0.26 against 0.27 when they were fitted), but run 3% low on average and
9% low on the dearest tenth. A refit gains 0.04 of R2; the recipes do not differ. Refits are in
`kit-supply/core/data/cost_alt.json`. Server test on fresh seeds ct-1..48 (tag ct1), running: base, refit (costAlt=1),
refit big + weights + monotone (costAlt=4), `dueCapPer=0.11`, `dueCapPer=0.11` + refit.

## SERVER: day cap confirmation and refitted cost trees on BEST12 (15 Nov 01:47, ct-1..48, tag ct1)

240 weeks, none failed (the server or this machine stalled 01:00 to 01:30). Base 19,113, 449 orders, 48/48 ranked,
worst on time 91.0%. Table `variants/ct1_table.txt`.

| Variant | Difference a week | Better / worse | Scored | Orders | Ranked | Worst on time |
|---|---|---|---|---|---|---|
| `dueCapPer=0.11` | +87 ± 80 | 29 / 15 | +87 | 453 | 48/48 | 91.6% |
| refit (`costAlt=1`, shipped recipe on 146k BEST12 orders) | -220 ± 141 | 21 / 27 | -511 | 432 | 47/48 | 88.8% |
| refit big + weights + monotone (`costAlt=4`) | -298 ± 154 | 18 / 30 | -613 | 430 | 47/48 | 89.0% |
| `dueCapPer=0.11` + refit | -86 ± 165 | 25 / 23 | -376 | 435 | 47/48 | 88.8% |

- `dueCapPer=0.11` pooled with su1, 96 fresh weeks on BEST12: **+144 ± 55** (55 better, 26 worse), scored +291,
  ranked 94/96 against 93/96. Ship-candidate by the 2 SE rule (2.6 SE), on one base only.
- The refitted trees lose (about -250, 1.6 to 1.9 SE, 17 fewer orders, one ranked week lost) although they fit the
  held-out rows better (R2 0.30 against 0.26). Same lesson as the booking-model refits: rows from weeks played with
  the trees in the price choice are a selected sample. Dead; `costAlt` stays 0.

## Backlog curve by Optuna (15 Nov 00:58, local sim only, `optcurve.py`, log `variants/optcurve_log.txt`)

Free curve (`curve=1`: cut `cDown` at an empty board fading to 0 at backlog `cLo`, flat for `cDead`, then a rise to
`cCap` over `cSpan` with shape `cPow`). 384 TPE trials on m, h in both worlds, start = the linear rule. The five best
agree: cut 0.12 to 0.14, ending at backlog 0.06, almost no flat stretch, rise to 0.31 to 0.39 within 0.02 to 0.035,
shape 0.5 to 1.4 (not convex: a late, steep ramp). Held out k, rd, sv (158 weeks), pooled smooth score: linear +53,
best five +174, +194, +74, +157, +65 (search +273 to +296); margin +38 to +131 ± 55 in v4, -27 to +72 ± 56 in T.
Chosen for the server: the second best (`Lopt` in `variants/server3.txt`).

Running: cv-1..48 (tag cv1): base, L linear, L convex (`backPow=2`), Lopt, lateness charge 0.5 / 1.0 / 2.0
(`costAlt=5,6,7`: refits on the same rows with a late order's cost raised by that many x its typical fee).

## Day cap far higher, and with a lateness charge (15 Nov 01:58, local sim only, BEST10 port)

`variants/duehigh.txt` on all 254 weeks; `variants/local5.txt` on the 158 held-out weeks with the sim's own lateness
trees (`latefit_sim.py`, knob `lateW`: cost + lateW x P(late) x typical fee, on top of the shipped cost trees).

| Variant | v4 margin | T margin (ranked, base 251) | T2 margin (ranked, base 247) |
|---|---|---|---|
| `dueCapPer` 0.11 | +140 ± 26 | +148 ± 29 (251) | +128 ± 28 (246) |
| 0.13 | +263 ± 32 | +188 ± 31 (248) | +174 ± 34 (246) |
| 0.18 and every higher value (the cap no longer binds) | +278 ± 35 | +221 ± 35 (248) | +198 ± 38 (245) |

Held out, 158 weeks (ranked base 157 / 155 / 153):

| Variant | v4 | T | T2 |
|---|---|---|---|
| `lateW=1` | +195 ± 67 (157) | +456 ± 83 (157) | +603 ± 102 (157) |
| `lateW=2` | +41 ± 71 | +299 ± 110 | +597 ± 125 |
| `lateW=4` | -278 ± 80 | -168 ± 111 | +261 ± 130 |
| `dueCapPer=0.11` + `lateW=1` | +298 ± 70 (157) | +528 ± 87 (157) | +671 ± 105 (157) |
| `dueCapPer=0.18` + `lateW=1` | +402 ± 77 (157) | +599 ± 91 (157) | +707 ± 110 (157) |

The day cap is worth about 200 to 280 of margin and buys a few ranked weeks when drivers are short; past 0.18 it
does nothing. A lateness charge of 1 x P(late) gains in all three worlds, loses 13 to 24 orders, lifts on time 1 to 2
points and leaves no unranked week; with it the cap can go. Sim caveat: the sim's late orders are far easier to
predict (riskiest tenth holds about 80% of them, 52% on the server). Server: dw-1..24 on BEST14 (`kit-s14`),
`variants/server4.txt`.

## SERVER: backlog curves and lateness refits on BEST12 (15 Nov 02:14, cv-1..24, tag cv1, stopped at 24 seeds)

Base 16,343, 401 orders, 24/25 ranked, worst on time 89.1%. Table `variants/cv1_table.txt`.

| Variant | Difference a week | Better / worse | Orders | Ranked | Mean on time |
|---|---|---|---|---|---|
| L linear (`backK=6,backAt=0.04,backDown=0.08`) | +122 ± 130 | 16 / 9 | 405 | 23/25 | 95.2% |
| L convex (`backPow=2,backUp=0.08`) | +210 ± 150 | 18 / 7 | 405 | 24/25 | 95.3% |
| L Optuna curve | +152 ± 133 | 15 / 9 | 406 | 23/24 | 95.3% |
| lateness refit +0.5 / +1.0 / +2.0 x typical (`costAlt=5,6,7`) | -409 ± 170 / -491 ± 196 / -951 ± 294 | | 369 / 358 / 339 | 22/24, 24/24, 23/23 | 95.4 / 96.2 / 96.9% |

- Backlog rule, linear, pooled with su1: 73 weeks **+148 ± 89** (43 better, 30 worse): positive in both sets, 1.7 SE,
  ranked weeks unchanged. The three shapes do not differ (24 weeks cannot tell +122 from +210).
- Lateness inside a refitted cost tree: on time +1.2 to +1.9 points and every week ranked at +1.0 and +2.0, but
  400 to 950 a week dearer and 40 to 60 orders fewer. These heads are refits (the plain refit alone lost 220 to 300
  on ct1), so the charge and the refit are confounded: dead in this form. Next form: `lateW` (a separate P(late) head
  added to the SHIPPED trees), dw-1..24 on BEST14 (`kit-s14`, tag dw1), running.

## Test final 15 Nov 01:00 (BEST14 in kit-final, data runs/testfinal_1115_0100; read-only study)

Place 5 of 41 ranked: 13,170, 376 orders, 92.8% on time (lowest of the first 14; first HackandSeek 14,112 / 445 /
96.0%, Juhus 13,288 / 488 / 94.1%, tenth 11,509). Late refunds 1,795. Feed, end of week: revenue per order us 105.7
EUR, the four teams around us 86 to 95; cost per order 70.7 against 55 to 59. Orders won on Monday: 74, HackandSeek
105, Juhus 113. Our 25 late orders (cancelled ones left out): 20 had no driver booked at the last pickup time, median
23 h late; won Tue / Wed 10% late, Mon 1%; same-day 9% (148 of 376 orders); 5% late without a drop, 13% after one.
Wednesday was the flu day (23 drops 00:00 to 01:00).

## 111 ideas after the 01:00 test final (15 Nov 02:24, local sim only, BEST10 port)

`ideas_gen.py` -> `variants/ideas100.txt`, `ideas.py` -> `variants/ideas100_table.txt` (every idea: search weeks m, h and
held-out weeks k, rd, sv in three worlds). New sim knobs: `shortShift/shortH`, `longShift/longH`, `floorTyp`, `sdShift`,
`sdMinH`, `lateW`. Held out, margin a week (v4 / T / T2), ranked weeks of 158 (base 157 / 155 / 153):

| Family | Best of the family | Margin | Ranked | Verdict |
|---|---|---|---|---|
| Lateness charge | `lateW=1` | +195 / +456 / +603 | 157 / 157 / 157 | the one family that gains everywhere; 1 to 1.5 best, 2 gives margin back |
| Combos on it | `dueCapPer=0.18,lateW=1,capConst=0.5` | +664 / +760 / +879, orders +14 | 157 / 157 / 157 | best of all; without `lateW` the same capacity change loses ranked weeks |
| Day cap | 0.11 to 0.18 | +168 to +328 / +164 to +254 / +143 to +239 | 157 / 154-155 / 153-154 | margin, no safety |
| Short cars cheaper, long cars dearer, cheap-to-move floor | none | -90 to +90 | unchanged | steering the car mix by a price shift does nothing |
| Capacity charge (`capConst`, `capLam`) | `capConst=0.5` | +195 / +36 / -63, orders +20 | 157 / 154 / 152 | more orders, more late: only with the lateness charge |
| Same-day options | 0.03 cheaper | +277 / +207 / +223 | 157 / 155 / 154 | volume (the sim overrates it); dearer or cut-off: loses |
| Fees: early ramp 1.8 to 2.0, urgent start 1.5 | | -11 to +110 margin, on-time-priced +286 to +408 | 157 / 157 / 155-157 | on time, no margin; the server said the sim has the wrong sign on urgent fees |
| Opening fee, raises, cost of no driver, pairs, booking gate, floor, ceiling | | within noise or negative | | the tuned values hold |

Next server candidates: `lateW` 1 and 1.5; `dueCapPer=0.18,lateW=1`; the same with `capConst=0.5`.

## SERVER: day cap and lateness charge on BEST14 (15 Nov 02:42, dw-1..24, tag dw1, kit-s14)

kit-s14 = kit-best BEST14 + the test knobs (off = BEST14). `lateW`: cost + lateW x P(order ends late) x typical fee,
P from trees fitted on 146k orders of the su1 weeks (`costfit_plate.py`), on top of the SHIPPED cost trees.
168 weeks, none failed. Base 19,539, 443 orders, 24/24 ranked, mean on time 95.4%, worst 90.7%. `variants/dw1_table.txt`.

| Variant | Difference a week | Better / worse | Orders | Ranked | Mean on time | Worst on time |
|---|---|---|---|---|---|---|
| `dueCapPer=0.11` | +35 ± 121 | 8 / 10 | 446 | 23/24 | 95.4% | 88.9% |
| `dueCapPer=0.18` | +143 ± 143 | 9 / 9 | 450 | 23/24 | 95.1% | 89.9% |
| `lateW=1` | -437 ± 216 | 10 / 14 | 420 | 24/24 | 96.8% | 94.8% |
| `lateW=2` | -1,236 ± 275 | 3 / 21 | 402 | 24/24 | 97.3% | 95.0% |
| `dueCapPer=0.18,lateW=1` | -209 ± 215 | 13 / 11 | 425 | 24/24 | 96.8% | 93.6% |
| `dueCapPer=0.13,lateW=1` | -216 ± 216 | 13 / 11 | 425 | 24/24 | 96.8% | 93.6% |

- The lateness charge does on the server what it did in the sim for on time (+1.4 points, worst week +3 to +4
  points, 23 fewer orders) but it COSTS margin there (-437 ± 216 at 1) where the sim said +195 to +600. With a loose
  day cap about half comes back (-209 ± 215). It is insurance: about 1% of margin for 3 points of the worst week.
- The day cap alone on BEST14: +35 ± 121 at 0.11 (on BEST12 +144 ± 55 over 96 weeks), +143 ± 143 at 0.18, and
  each lost one ranked week of 24. Not a gain on BEST14 by this set.
