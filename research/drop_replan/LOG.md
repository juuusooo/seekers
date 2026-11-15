# drop_replan: log

## 14 Nov 18:35 · open
- **Hypothesis:** a one-car gig that a driver gave back reopens at the fee its old schedule shows now, often far above what it booked at (rebooked at +0.20 x typical, 39% within 10 minutes); a fresh fee plan at the drop saves fees, about +250 a week
- **Base, seeds, metric:** kit-look knob replanDrop=1 (engine: reprice with feesFor at gig_dropped / no_show, not urgent, not pairs); local sim 158 weeks vs BEST10: +257 ± 31 (130/28), orders 440 = 440, 158/158 ranked, worst on time 92.9% vs 93.7%; server dr-1..16 on BEST10 and BEST9 same weeks, then 48 fresh
- **Kill criteria:** kill: server under 2 SE on fresh weeks, or fewer ranked weeks, or worst on time clearly lower
- **What I did:**
- **Result / verdict:**
- **Next:**
