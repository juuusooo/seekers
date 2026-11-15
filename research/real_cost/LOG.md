# real_cost: log

## 14 Nov 16:56 · open
- **Hypothesis:** a realized-cost model (price minus final net per won order, from ledger lines; idea from the friend's Bahn-RL-lab tree hybrid) blended into the cost of the price choice beats the plan fee alone, about +100 to +300 a week
- **Base, seeds, metric:** fit on ended BEST6+ server weeks (sv, sn, b8, ia seeds; split by seed), check out-of-seed gain over plan fee; kit-cost = kit-best + knob costW (0 = BEST8, replay equal); local sim with orders flat, then server rc-1..16 on BEST8 and BEST7 same weeks, then 48 fresh: mean diff ± SE, weeks better, ranked, worst on time, scored
- **Kill criteria:** kill: cost model adds under 2% explained variance over plan fee out of seed, or server gain under 2 SE, or fewer ranked weeks
- **What I did:**
- **Result / verdict:**
- **Next:**

## 14 Nov 17:00 work notes
- Source of the idea: friend's `Bahn-RL-lab/transfer/strategy.ts` (BEST4 + LightGBM win / cost heads; +462 a week, 95% interval -608 to +1,320 on 6 weeks; unranked in round Saturday 15:00). Taken: the cost head only (label price minus final net over typical fee). Not taken: tree win head (BEST5 filter is better), floor 1.20, dropped town-full / outage shifts.
- Data: `pull.sh` (read-only, 3 practice keys) -> events, snapshot, drivers of 399 ended BEST6+ worlds (variants sv1 fee, sn1 best6/notes, b8 BEST8/BEST7, i3 base / mon / brake). `build.ts` replays events, inputs from `kit-cost/core/cost.ts` (38 inputs, same function as live) -> `runs/rc/rows.jsonl`, 156,312 won orders, 192 seeds.
- Fit (`fit.py`, held out = every 4th seed): cost mean 0.977 x typical (fees 0.938, plan fee 0.927), SD 0.47. Held-out R2: plan fee alone 0.06, trees on all inputs 0.27 (without plan inputs 0.27). Calibrated by decile; top decile actual 1.45 vs plan 1.01. Biggest inputs: ln typical fee 37%, plan fee 12%, drive hours, legs, slack.
- kit-cost = kit-best + `costW`, `costUp` (default 0). costW=0 replays BEST8 to the cent on 158 local weeks. TS trees = LightGBM within 1e-5.
- Local sim v4, 158 weeks (m, h, k; none used in the fit), vs BEST8 16,944: costW 0.25 +121 ± 42; 0.5 +296 ± 51; 0.75 +514 ± 55; 1.0 +661 ± 53 (139/19, orders 422 vs 409, all ranked, worst 93.0% vs 92.9%); 1.25 +807 ± 54; 1.5 +805 ± 64; costW 1 + capLam 5 (orders 401, below base) +445 ± 59; costW 1 + costUp 0.25 +452 ± 54; on BEST7 costW 1 +653 ± 62.
- Sim, more: per-option price by cost difference (costOpt 0.5 / 1 on costW 1): +603 ± 60 / +454 ± 61, worse than costW 1 alone (+661): knob stays 0.
- SERVER screen rc-1..16 (fresh, same weeks, tag rc1, kit-cost): BEST8 16,162; costW 0.5 +313 ± 174 (10/6); costW 1 +622 ± 178 (14/2), orders 406 vs 398, 16/16 ranked both, worst on time 92.8% vs 90.9%. On BEST7 (16,107): costW 1 +560 ± 169 (13/3), 16/16, worst 91.7% vs 91.5%.
- Proof started 17:30: rd-1..48, tag rc2: best8, costW 1, costW 1.25.
