# Automatic coordinate search of the main knobs

Tool: `kit-max/tune.py TAG CFG N PREFIX` (resumable; state `runs/km/tune_TAG.json`, log `runs/km/tune_TAG.log`).
For each of 22 knobs: one step down and up, same seeds as the incumbent. Accept the best when its gain is over
2 SE and 100 EUR and it keeps the ranked weeks (at most one fewer). Up to 3 passes.

## Run o2 (started 14 Nov 04:02)
- Start: `kit-max/T.cfg` (best model + `typW=1`, every tuned knob written out). Seeds t-1..32 (new, only for tuning).
- Accepted values must then be proved on h- seeds against T.

## o2 stopped 14 Nov 04:40 (after 6 knobs: markupMin, hardPrice, minBookChance, hardChance, capPerDriver, dueCapPer)
Nothing accepted. Closest: dueCapPer 0.10 +124 ± 64, markupMin 1.34 +115 ± 167.

## Run o3 (started 14 Nov 04:50)
- Start `kit-max/C.cfg` (= BEST3 with every knob written out), seeds t-1..32, capLam added to the knob list.

## Random local search rs1 (started 14 Nov 05:34)
- `kit-max/rls.py`: each round 4 candidates, each moving 3 random knobs one step; accept over 2 SE. Start C.cfg, seeds s-1..32, 30 rounds.

- 14 Nov 06:02: rls.py split bug (tune.py was reformatted) made rs1 run the one-knob tuner instead, on s-1..32. Kept it as
  a replication of o3 on other seeds. Fixed rls.py (asserts the split). Lesson: on t- seeds hardPrice 0.1 was -54 ± 111,
  on s- seeds +273 ± 112 (accepted by rs1): a 2-SE rule on 32 weeks still lets noise through. Prove on h- before adopting.

## 14 Nov 06:09 · proof of accepted changes on h-1..48 vs C
- dueCapPer 0.10: +194 ± 71 (32/16), ranked 46/48 vs 47/48. With o3 on t- (+151 ± 67): real. Adopted → BEST4.cfg.
- hardPrice 0.1 (rs1 on s-): -134 ± 104. Rejected. rs1 stopped.
## Random local search rs2 (started 14 Nov 06:10) from C4.cfg (= BEST4 written out), s-1..32, fixed script.

## 14 Nov 07:02 · rs2 picks fail the proof (h-1..48 vs BEST4)
- capLam 3 + markupMax 1.8 + lateFee 1 (accepted, +432 ± 163 on s-): -196 ± 118.
- pairTop 1.45 + minBookChance 0.93 + minProfit 0.05 (+364 ± 111 on s-): +56 ± 125.
Picking the best of 4 noisy candidates at 2 SE on 32 weeks selects luck. rs3: 48 weeks, accept over 2.5 SE and 150 EUR.

## 14 Nov 08:48 · o3 finished
Pass 0 accepted dueCapPer 0.10 only (proved on h-), pass 1 accepted nothing. FINAL = BEST4.

## Run o4 (started 14 Nov 09:08): strict tuner `tune_strict.py` (2.5 SE, 120 EUR, 2 passes), 64 weeks per step, seeds u-1..64, from C4.cfg (= BEST4).
