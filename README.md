# Seekers: Every car is a trade

Bahn Spread · Junction 2026 · level 8

We are technical finance students. We treated dispatch as a trading desk: every dealer request is a trade priced against a hidden competitor, every gig is an order for driver time that must fill before its deadline.

**Final:** €19,975 margin, 95.4% on time, 432 orders. **Practice:** €18,738 a week on 96 fresh weeks, 95 of 96 ranked.

## The core rule

For each request, quote the markup *m* (1.28 to 2.0 × list price) with the highest expected profit:

```
P(win | m) × ( m × list − expected cost − €4 × (drive h + 1) )
```

- `P(win | m)`: the competitor's price level, learned live from our own wins and losses (online filter by week, weekday and lane, plus a belief over which region has its outage today).
- `expected cost`: what the car will really cost, from realized-cost trees trained on 156,000 won orders.
- `€4 × (drive h + 1)`: the price of driver time, because drivers are the bottleneck at level 8.

Once won, the car is posted as a gig with a fee schedule: open at ≥ 0.706 × typical fee, ramp to 1.45 × before the last pickup time, back to 0.83 × once the car is late anyway.

## Top 3 rules (each measured on fresh weeks, same seeds with and without)

| Inefficiency found | Fix | Result |
|---|---|---|
| The planned fee predicts almost none of the real cost (R² 0.06) | Realized-cost trees in the price (R² 0.27) | +€644 ± 106 a week, 48 weeks |
| Driver hours cost nothing in the price; 43% of quotes sat on the floor | €4 per driver-hour, floor 1.38 → 1.28 | +€601 ± 165 a week, 48 weeks |
| Only 38% of gigs book at the opening fee; paying up once late buys nothing | Fee schedule 0.706 → 1.45 → 0.83 | +€530 ± 116 a week, 48 weeks |

## Folders

| Folder | What |
|---|---|
| `system/` | The system that played the final (BEST16). Every decision and value is in `system/algo.ts`; `system/docs/MODEL.txt` explains every rule. |
| `research/` | Every test we ran: `LEDGER.md` (one row per test, numbers and verdict), `KNOWLEDGE.md` (what we believe now), topic logs. |
| `presentation/` | `Seekers.pdf` (slides), `slides.html`, `PITCH.md`. |

## Run it

TypeScript, [Bun](https://bun.sh), no dependencies.

```sh
cd system
export SPREAD_URL=https://spread.bahnexpress.com SPREAD_KEY=<team key> SPREAD_KEY_OFFICIAL=<team key>
bun core/run.ts --seed my-test-1     # one practice week, level 8
bun core/run.ts --final              # the final: waits, joins, plays to the end
```

In the final it rebuilds its orders and gigs from the server after a restart and reloads its learned state (saved every few seconds).
