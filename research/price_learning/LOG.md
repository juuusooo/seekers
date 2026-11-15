# Learn the competitor faster: day and dealer offsets

Rules: the competitor's price = list x lane x day factor (new each day) x week level x small noise; it also cuts
prices for dealers where we win most and raises them where we win few. The model learns one week level from the
last 300 answers.

Knobs (algo3.ts, kit-max): `dayLearn` = prior SD of today's offset, `dealerLearn` = prior SD of a dealer's offset
(its last `dealerN` answers). 0 = off. Built 14 Nov 03:35, not tested yet.

## 14 Nov 03:50 · on best, m-1..32
| knob | vs base | ± | better/worse | ranked |
|---|---|---|---|---|
| dayLearn=0.15 | +193 | 93 | 20/12 | 31/32 |
| dayLearn=0.3 | +3 | 168 | 17/15 | 31/32 |
| dealerLearn=0.2 | +166 | 96 | 23/8 | 30/31 |
| dealerLearn=0.4 | +67 | 126 | 18/13 | 31/31 |
Small gains at the low settings. Next: on top of typW=1, alone and together (m-1..48).

## 14 Nov 04:00 · on top of typW=1 (T), m-1..45
| variant | vs base | ± | better/worse | ranked |
|---|---|---|---|---|
| T alone (typ100) | +403 | 119 | 33/15 | 46/48 |
| T + dayLearn 0.15 | +428 | 133 | 30/14 | 42/44 |
| T + dealerLearn 0.2 | +380 | 127 | 33/14 | 47/47 |
| T + both | +422 | 142 | 30/15 | 45/45 |
| T + both + trustRisk 0.5 | +420 | 150 | 30/15 | 44/45 |
Verdict: nothing beyond T. The small gains on the old base were mostly the same thing T fixes, or noise.
Next: place offsets (`placeLearn`) and lane-shape slope (`shapeLearn`), built 05:00.
