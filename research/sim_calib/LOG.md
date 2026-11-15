# sim_calib: log

## 14 Nov 15:56 · open
- **Hypothesis:** The local sim's drivers absorb extra volume too cheaply (kit-sim1: sim +1,851, server +27, orders equal at +25%). Refit the driver side on sv-1..24 at two loads (BEST5 and kit-sim1 server weeks) so high load costs what it costs on the server, then rerun the joint knob search on the honest sim: kit-sim1-server-calibrated
- **Base, seeds, metric:** sim v4 -> v5; fit sv-1..24 (BEST5 + kit-sim1 + fee core server rows); held out: sv-25..48 both loads, m/h/k level gate, rankgate 87 variants, fee core effect; then joint search on m,h (held out k) from BEST7; server proof on fresh seeds 48 weeks vs BEST7 same weeks: margin diff ± SE, scored (unranked = 0), ranked, worst on time
- **Kill criteria:** kill: held-out sv-25..48 kit-sim1 minus BEST5 gap between sim and server still over 500, or rankgate worse than v4 (under 16/17 signs or corr under 0.90); kit: under 2 SE on the server or fewer ranked weeks
- **What I did:**
- **Result / verdict:**
- **Next:**

## Work notes (14 Nov, from 16:00)

Files: `sim/cal/` (own copy of `sim/opt`: `world.ts` + params `busyMin`, `workPow`; `kit/` = BEST5/6 copy, `kit8/` = kit-best snapshot 15:57 = BEST8;
`run.ts --kit kit8`, `run_rg.ts` = old kit-max on this world). Rows: `runs/sim_cal.jsonl`. Scripts here: `pull_sv.ts` (server stats of the
144 sv1 worlds from their events, `sv_server.json`), `gap.py` (sim vs server table), `calib.py` (two-load fit), `rankgate.py`, `search.py`.

**Gap of sim v4 on sv-1..48 (same weeks, sim / server).** kit-sim1 minus BEST5: margin +1,965 / +27; orders +97 / +95; on time +0.8 / -3.7 pt;
late refunds -154 / -1,114; deadline warnings +0.6 / +52; drops +4 / +23. Same-day orders late: 4.7% -> 3.2% in the sim, 6.3% -> 10.5% on the
server. Drivers with a booking a week (BEST5): 256 / 204. Volume is right; its cost is not.
Server driver load (23 recorded kit-best weeks): 194 drivers start a gig a week; 77% of driver-days hold 1 gig, 20.5% 2, 2% 3; weekly gigs by
ln(1+completed): under 4: 0.2 to 0.4; 4 to 5: 1.0; 5 to 6: 2.9; over 6: 5.5.

**Fits (fit sv-1..24 on BEST5 + kit-sim1 jointly, 14 targets per load + the difference; held out sv-25..48).**
| Fit | Loss | Held out: kit-sim1 minus BEST5, sim (server +183) | Fit weeks (server -130) | Note |
|---|---|---|---|---|
| v4 | 440 | +1,973 | +1,957 | |
| v5a (23 params) | 102 | +892 | +15 | maxGigs 1, 316 drivers a week vs 204: wrong structure |
| v5b (+workPow) | 129 | not run | -46 | stuck in the 1-gig basin |
| v5c (start: maxGigs 3, workPow 2, fewer drivers) | 76 | -293 | -516 | maxGigs 2, workPow 3.2, 195 drivers vs 204 |

v5c held out (sim / server): BEST5 margin 17,007 / 17,038 (week corr 0.93); on-time change under load -3.2 / -3.9 pt; late refunds added
-803 / -986; fee core gain +634 / +401 (fit weeks +299 / +658). Still off: weeks under 90% (kit-sim1 42% vs 25%, BEST5 12.5% vs 4%), fee per
order rises 3.1 under load vs 0.6. v5c params: `runs/lab/v5c.sim`.

Quick check on v5c44 (158 weeks m, h, k): BEST8 15,901 (147/158 ranked); BEST8 + old kit-sim1 knobs -274 ± 99, scored -2,167 (126/158
ranked); BEST7 +99 ± 56.

## Result (14 Nov 17:30)

**Ranking gate, v5c vs v4** (87 old server-measured variants, kit-max on `sim/cal/run_rg.ts`, `runs/lab/rankgate5c.txt`): clear effects same
sign 15/17 (v4 16/17), correlation of differences 0.81 (0.95), rank correlation 0.46 (0.67), mean gap on clear effects 689 (384). Worse
on: delayed posting -2,191 (server -6,345, v4 -4,735), no same-day -658 (-1,962, v4 -2,026), fee x1.10 -1,334 (-703, v4 -558). Fee x0.95
is wrong in both (+567 and +497, server +27). So v5c fails the gate set in the plan: it buys the load response with a worse fee and
same-day response. Use it only next to v4, never alone.

**Knob search from BEST8 on both worlds at once** (`search2.py`, seeds m-1..48 + h-1..48, accept = pooled gain over 2 SE and a gain in
each world): e1 (unranked week = 0) 80 candidates, 0 accepted; e2 (smooth on-time penalty, 3,000 per point under 93%) 160 candidates,
0 accepted, 3 gained in both worlds, none over 2 SE pooled. Best pooled: pairSlackH 4 + hardChance 0.881 +203 ± 104 (v4 -3 ± 61, v5c
+408 ± 197); rampTop 1.86 + steepStep 0.19 + pS 0.103 +196 ± 99 (v4 -59 ± 55, v5c +452 ± 193). No config to prove: no server weeks
played, no `kit-sim1-server-calibrated/` folder made.
