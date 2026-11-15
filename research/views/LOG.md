# views: log

## 14 Nov 12:16 · open
- **Hypothesis:** live gig_viewed events (per driver id, never used for fees) carry the booking decision: 92% of bookings happen at the driver's first view, so a per-view acceptance model (fee, driver, gig, time) fitted on the views of all ended practice worlds beats the gig-hour booking model, and fees set from it earn more
- **Base, seeds, metric:** data: events + drivers of about 22,600 ended level 8 practice worlds on the 3 normal keys (read-only pull to runs/events/); fit on seeds outside m-, h-, k-; then live on kit-best defaults vs view-model fees, same seeds, at least 16 weeks screen then 48 fresh
- **Kill criteria:** per-view model adds no out-of-week log loss over the gig-hour model, or live gain under 2 SE on fresh seeds
- **What I did:**
- **Result / verdict:**
- **Next:**
