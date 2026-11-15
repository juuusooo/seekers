# wild: log

## 14 Nov 17:05 · open
- **Hypothesis:** fast screen of wild ideas on BEST8 (kit-wild, knobs default off, replay b8-1,b8-2 equal to the cent): W1 falling fees (flash), W3 booking-speed price controller, W6 steer to slow options, W8 pair start town, W9 decline tight same-day; batch B: active drivers from views, 3-car chains, price-war detector, thrown quotes, offers to own finishing driver
- **Base, seeds, metric:** kit-wild = kit-best BEST8; screen server wd-1..12 same weeks, base + all variants; survivors wd-13..48 on BEST8 and BEST7; winners combined on 48 fresh; mean diff ± SE, weeks better, ranked, worst on time, plus one gauge per idea (fee/typical, orders, pairs booked, option mix)
- **Kill criteria:** screen: mean under +250, on time down over 1 point, one more unranked week, or its gauge does not move; confirm: under 2 SE on either base or fewer ranked weeks
- **What I did:**
- **Result / verdict:**
- **Next:**

### Screen a1 (server, wd-1..12, BEST8 base 16,848, 12/12 ranked, worst 93.3%), 14 Nov 18:18
| Variant | Diff ± SE | Better/worse | Orders | Gauge | Verdict |
|---|---|---|---|---|---|
| flash .9 (flashTop=0.9, 15 min) | -653 ± 267 | 2/10 | +1 | fee/typical 0.901 -> 0.931, pairs booked 70 -> 49 | dead |
| flash 1.05 | -3,078 ± 301 | 0/12 | -1 | fee/typical 1.021 | dead |
| steer a (optSlow=-0.05, optNext=-0.03) | +95 ± 118 | 7/5 | +11 | same-day share 0.45 -> 0.40 | dead (under +250) |
| steer b (optSlow=-0.1, optNext=-0.05) | -134 ± 173 | 5/7 | +22 | same-day share 0.36, lates 15.4 -> 16.8 | dead |
| same 5h (sameMinH=5) | +16 ± 130 | 4/8 | -2 | lates 15.4 -> 15.2 | dead |
| same 7h | -111 ± 215 | 5/7 | -7 | lates 13.6 | dead |
| pairNear 10 | -71 ± 117 | 6/5 | 0 | pairs booked 70.2 -> 69.8 | dead |
| ctl .3 (ctlK=0.3, ctlT=0.87, ctlMax=0.1) | +191 ± 94 | 10/2 | +2 | worst on time 93.9% | survivor |
| ctl .6 | +265 ± 170 | 8/4 | +5 | worst on time 94.4% | survivor |

Dead without server weeks: W2 active drivers from gig_viewed (669 recorded weeks: R2 of week margin on roster + Monday orders 0.314, with Monday distinct viewers 0.315); experienced-only audience against drops (260 weeks: experienced drop 12.8% of bookings vs 16.1%; orders with a drop 8.2% late vs 3.9%, all drops = 0.6 points of on time).

### Screen a1 batch 2 (server, same wd-1..12, BEST8 base 16,848), 14 Nov 18:33
| Variant | Diff ± SE | Better/worse | Orders | Worst on time | Verdict |
|---|---|---|---|---|---|
| ctl .6 T.84 (ctlK=0.6, ctlT=0.84) | +296 ± 131 | 9/3 | +8 | 94.1% | survivor |
| ctl 1 (ctlT=0.87) | -118 ± 195 | 7/5 | +3 | 93.4% | dead |
| ctl 1 T.9 | +175 ± 169 | 8/4 | +1 | 93.8% | dead |
| ctl 1.5 max .15 | +108 ± 183 | 9/3 | +8 | 93.6% | dead |
| war .1 (warCut=0.1, warN=10, warGap=0.15) | +141 ± 99 | 9/3 | +7 | 92.8% | weak |
| war .18 | +311 ± 152 | 8/4 | +12 | 92.9% | survivor |
| idle .05 (floorCut) | +94 ± 179 | 6/6 | 0 | 93.0% | dead |
| idle .1 | +115 ± 134 | 7/5 | +2 | 93.0% | dead |
| mon -.08 (dueMon) | -218 ± 216 | 5/7 | +10 | 93.3% | dead |

Half-way numbers (4 to 6 weeks) were +320 to +420 for war, idle and ctl 1.5 and shrank to +110 to +310 at 12 weeks: do not read partial tables.
14 Nov 18:36: kit-best became BEST9 (costW=1). kit-wild ported to BEST9 (old algo: runs/lab/kit-wild_algo_best8_wild.ts); replay rc-1, rc-2 = BEST9 and rc-1 costW=0 = BEST8 to the cent. Next: s9 (wd-1..12 on BEST9: floor 1.22 / 1.18, floorLvl .5 / 1, ctl, war), c9 (wd-13..48 on BEST9) and c8 (wd-13..48 on BEST8): base, ctl .6 T.84, war .18, both.

### Screen s9 (server, wd-1..12, BEST9 base 17,545, 12/12 ranked, worst 93.7%; BEST8 on the same weeks 16,848), 14 Nov 18:40
| Variant | Diff ± SE | Better/worse | Orders | Worst / mean on time | Verdict |
|---|---|---|---|---|---|
| ctl (ctlK=0.6, ctlT=0.84) | +242 ± 156 | 9/3 | +8 | 93.5% / 96.8% | weak |
| war (warCut=0.18) | +320 ± 164 | 10/2 | +11 | 92.9% / 96.6% | survivor |
| floor 1.22 (markupMin) | +135 ± 209 | 5/7 | +16 | 93.6% / 96.7% | dead |
| floor 1.18 | +336 ± 207 | 7/5 | +24 | 93.9% / 96.7% | noisy |
| lvl .5 (floorLvl: floor follows week + weekday competitor level when below average) | +321 ± 157 | 10/2 | +17 | 94.2% / 96.6% | survivor |
| lvl 1 | +573 ± 140 | 11/1 | +22 | 94.6% / 97.2% | lead |
Next: lvl 1 and lvl 1 + ctl on wd-13..48 (c9), lvl sizes and the upward side on wd-1..12 (s9), lvl 1 on BEST8 (c8).

### Confirm c9 (server, fresh wd-13..48, BEST9 base 17,047, 36/36 ranked, worst 90.8%), 14 Nov 18:52
| Variant | Diff ± SE | Better/worse | Orders | Ranked | Worst on time | Verdict |
|---|---|---|---|---|---|---|
| lvl 1 (floorLvl=1) | +303 ± 80 | 26/10 | +16 | 36/36 | 91.6% | passes |
| lvl 1 + ctl | +363 ± 90 | 29/7 | +19 | 36/36 | 91.5% | ctl adds +60, noise |
| ctl (ctlK=0.6, ctlT=0.84) | -107 ± 70 | 14/22 | +5 | 36/36 | 91.2% | dead |
| war (warCut=0.18) | +36 ± 69 | 25/11 | +10 | 36/36 | 90.8% | dead |
| ctl + war | +146 ± 86 | 22/14 | +15 | 36/36 | 91.1% | dead |
On BEST8 (c8, wd-13..48, base 16,541, 35/36 ranked, worst 89.0%): ctl +44 ± 92 (20/16), war +106 ± 79 (24/12), ctl + war -8 ± 108.

### Sizes of the level floor (s9, server wd-1..12 on BEST9, 12/12 ranked all)
lvl .5 +321 ± 157; lvl 1 +573 ± 140; lvl 1.5 +166 ± 190; lvl 2 +228 ± 171; lvl 1 + floorLvlUp .5 +573 ± 150; + up 1 +473 ± 242; lvl 1 + ctl +428 ± 200; lvl 1 + markupMin 1.22 +704 ± 192 (orders +29).

### Local sim v4 (158 weeks m, h, k; kit-wild defaults = kit-best to the cent; BEST9 17,605, orders 422, 158/158, worst 93.0%)
lvl .5 +275 ± 44; .75 +344 ± 50; 1 +330 ± 50 (115/43, orders +18, worst 93.7%); 1.25 +376 ± 49; 1.5 +441 ± 50; lvl 1 + up .5 +321 ± 52; lvl 1 + markupMin 1.22 +420 ± 57 (orders +25); lvl 1 + ctl +344 ± 52; lvl 1 + war +355 ± 52.
The sim prefers 1.5, the server 1.0 (sim overrates volume): BEST10 candidate = BEST9 + floorLvl=1. Proof p10 on fresh t10-1..48 running.
