# on_time: log

## 15 Nov 00:39 · open
- **Hypothesis:** Lates have three fixable causes (300 recorded weeks, 19.1 lates a week): drivers who arrive after the deadline though booked in time (5.9), gigs unbooked on the evening before their pickup day (12.6% late vs 2.3%), late cars delivered over 24 h late (6.4, 50% refund). Arrival buffer in the delivery window, an evening raise and a 22 h window for late cars: +1 point of on time or more at flat margin
- **Base, seeds, metric:** kit-ot = copy of kit-best BEST14, knobs default off; server fresh ot-1..16 same weeks screen (tag ot1): base, winBuf 45 / 60 / 90, winBuf 60 + winBufOff, eveTop 1.2 / 1.4, lateWinH 22, all three; survivors on 48 fresh weeks on BEST14 and BEST13 (pLane=0); mean on time, worst on time, ranked, margin diff ± SE, refunds
- **Kill criteria:** no gain in mean on time (under +0.5 point) or margin under -200
- **What I did:**
- **Result / verdict:**
- **Next:**
