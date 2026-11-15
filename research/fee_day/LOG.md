# fee_day: log

## 14 Nov 21:43 · open
- **Hypothesis:** Fees by posting day: live final shows gigs posted Thu / Fri book at 0.99 x typical vs 0.87 on Monday; planned fees x feeLate from Thursday on (0.95 / 0.90) keep drivers from learning high raises late in the week
- **Base, seeds, metric:** kit-out defaults = BEST12; local sim 158 weeks then server fresh fd-1..32 same weeks: base, feeLate 0.95, feeLate 0.90; mean diff ± SE, ranked, worst on time
- **Kill criteria:** screen under +150 or fewer ranked weeks or lower worst on time
- **What I did:**
- **Result / verdict:**
- **Next:**

### Work notes (14 Nov 22:20)
Knobs in kit-out (default 1): feeMon / feeMid / feeLate = all planned fees of a one-order gig x this, by the day the
schedule is made (Monday / Tue-Wed / Thursday on). Pairs and urgent fees unchanged.
Local sim v4, 158 weeks on BEST12: feeMon 0.95 -7 ± 46, 1.05 -103 ± 43; feeMid 0.95 -34 ± 39, 1.05 -164 ± 46;
feeLate 0.95 +114 ± 29, 1.05 -245 ± 31, 1.10 -533 ± 35.
Server screen fd-1..32 (tag fd1), base BEST12 17,399, 28/32 ranked, worst on time 88.2%:
feeLate 0.95 +193 ± 56 (23/9), 28/32, worst 87.9%, mean on time 94.6 vs 94.7%, orders equal, z +167;
feeLate 0.90 +180 ± 75 (23/8, 31 weeks), 27/31 vs 27, worst 86.3%, mean on time 94.2%.
Proof started: fe-1..40 on BEST12 and fe-1..24 on BEST11 (outBayes=0,outageK=0), tag fe1.

### After the ship (sim only, 158 weeks, on BEST13)
pairLate 0.95 +29 ± 28, 0.90 +5 ± 27; urgLate 0.9 -1 ± 5, 1.1 -9 ± 4; feeLate 0.93 -4 ± 30, 0.97 -41 ± 30;
pairLate 0.95 + urgLate 0.9 +27 ± 28. Nothing to take to the server.
