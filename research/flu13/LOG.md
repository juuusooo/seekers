# flu13: log

## 14 Nov 21:52 · open
- **Hypothesis:** BEST13 from the test final leads: react to the flu day (6+ drops 00:00-01:00): dearer same-day options, markup shift, capacity cost, fees; plus night raise hold, higher outage floor shift, softer hard-option gate. Any one +200 a week or more ranked weeks
- **Base, seeds, metric:** kit-flu = copy of kit-best BEST12, knobs default off; server fresh fl-1..16 same weeks screen (tag fl1), survivors on 48 fresh weeks on BEST12 and BEST11 (outBayes=0,outageK=0); mean diff ± SE, better/worse, ranked, worst on time
- **Kill criteria:** screen under +200 and no gain in ranked weeks or worst on time; proof under 2 SE on either base
- **What I did:**
- **Result / verdict:**
- **Next:**

### Screen fl1 (server, fresh fl-1..16, same weeks, kit-flu on BEST12, 16 weeks per variant), 15 Nov 00:10
Base 18,189, 15/16 ranked, worst on time 88.0%, mean 94.7%, orders 430.

| Variant | Diff ± SE | Better/worse | Ranked | Worst | Orders |
|---|---|---|---|---|---|
| fs15 (fluN=6,fluSame=0.15) | +188 ± 156 | 9/3 | 15/16 | 88.0% | 430 |
| combo (fs15 + fluFee 1.1) | +77 ± 137 | 7/6 | 15/16 | 90.0% | 431 |
| ffee110 (fluFee=1.1) | +56 ± 108 | 6/7 | 15/16 | 88.3% | 430 |
| fs30 (fluSame=0.3) | +32 ± 97 | 7/5 | 15/16 | 89.7% | 429 |
| hard75 (hardChance=0.75) | -38 ± 123 | 7/9 | 15/16 | 87.2% | 431 |
| night (nightHold=1) | -117 ± 205 | 5/11 | 15/16 | 88.4% | 428 |
| fsh10 (fluShift=0.1) | -123 ± 50 | 3/10 | 15/16 | 89.3% | 428 |
| fcap2 (fluCap=2) | -180 ± 119 | 4/9 | 15/16 | 88.3% | 414 |
| out40 (outage=0.4) | -195 ± 207 | 10/6 | 14/16 | 88.0% | 428 |

All under the +200 line, no variant gains a ranked week. fs15 is the only one near it (1.2 SE, no dose response: fs30 is lower).
One check on fresh weeks on BEST13 and BEST12: fm-1..32, tag fm1 (kit-flu rebuilt from kit-best BEST13 with fluN / fluSame only;
old algo in runs/lab/kit-flu_algo_on_BEST12_fl1.ts).
