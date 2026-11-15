# best16: log

## 15 Nov 07:11 · open
- **Hypothesis:** All three steps on BEST15 as one model (fee-only booking shift 0.2 + steps 4, rampTop 1.45, costW 1.25, hardChance 0.82 + pairKm 40, pairHoldH 3) gain about +830 a week over BEST15 when measured directly
- **Base, seeds, metric:** kit-b17 (frozen) with --set; base = BEST15 by overrides (bookShift=0,steps=5,rampTop=1.6,costW=1,hardChance=0.85), variant all = pairKm=40,pairHoldH=3; server fresh wp-1..96 same weeks, tag wp1, keys SPREAD_KEY_2 + SPREAD_KEY_OFFICIAL only (SPREAD_KEY is held for the final); mean diff ± SE, better/worse, ranked, worst and mean on time, scored (unranked = 0)
- **Kill criteria:** under 2 SE, or fewer ranked weeks than BEST15
- **What I did:**
- **Result / verdict:**
- **Next:**
