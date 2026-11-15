# Plan: a local copy of the Spread world (level 8), 100 to 1,000 times faster

Written 14 Nov 12:40 CET. Status 14:05: built and validated, see `sim/README.md` (16/17 clear effects, correlation 0.93, about 63x faster).

## Why it is slow today (measured 14 Nov, one practice week, kit-best)

| Part | Time | Share |
|---|---|---|
| `advance` calls to the server | 1,651 calls x 42 ms = 69.8 s | 75% |
| `actions` calls (quotes, posts, reprices) | 508 calls x 44 ms = 22.1 s | 24% |
| Our algorithm (quote + fees) | 0.8 s | 1% |
| Week total (24 weeks running in parallel) | 93.6 s; alone about 22 s | |

Throughput now: 13 to 15 weeks a minute on 24 practice worlds (3 keys x 8). The algorithm is not the problem:
99% of the time is waiting for the server. A local world removes all 2,160 round trips.

## Target speed

| Stage | Per week, one core | 32 cores | vs today (0.23 weeks/s) |
|---|---|---|---|
| Local world in TypeScript, algorithm unchanged | about 1 s (0.8 s is our algorithm) | about 30 weeks/s | about 130x |
| + faster fee planner (plan() is the hot loop: cache by gig features, prune the open x raise grid) | about 0.2 s | about 150 weeks/s | about 650x |
| + Rust port of world and algorithm | about 0.02 s | about 1,500 weeks/s | about 6,500x (only if needed) |

A full 48-week A/B test would take about 2 to 10 seconds instead of 10 minutes; a 1,000-candidate search
about 30 minutes instead of a week.

## GPU: no

- There is no GPU in this machine (nvidia-smi absent; 32 CPU threads, 124 GB RAM).
- Even with one, the world is a poor fit: an event-driven simulation with branching per request, per driver and per
  gig, variable event counts, and a decision algorithm full of conditions. GPUs need the same arithmetic on large
  fixed-size arrays. Rewriting the world and the algorithm as array code (JAX-style, many weeks in lockstep) is a
  multi-day rewrite and would drift from the real algorithm.
- Weeks are independent, so running one week per CPU core already scales perfectly. 32 cores x 0.2 s is enough.
- A GPU would only help the calibration step (fitting the driver and dealer models on millions of rows), and CPU
  fits that in minutes too.

## What "accurate" means, and how we prove it

A copy is only useful if it ranks ideas the way the server does. Two gates, both measured before we trust it:

1. **Level gate.** The current best on the local world vs the server on the same seeds (we have 48 to 64 server
   weeks per seed set): mean margin within 5%, per-week correlation over 0.8, orders and on-time share within 3%.
2. **Ranking gate (the one that matters).** We already measured about 60 A/B differences on the server on the same
   seeds. The local world must reproduce them:
   big ones (flat fees -1,364 to -4,389; delayed posting -1,228 / -6,345; refit model -1,123; no same-day -1,990;
   capacity pricing +601 to +730; denoised fee +403) with the right sign and roughly the right size, and the many
   near-zero ones as near zero. Target: sign agreement on all effects over 300 a week, rank correlation over 0.7.

Until both gates pass, local results are hints only. After they pass: screen locally, prove the top few on the
server (as today), always.

## How the copy is built: replay what we know, model what we do not

The world has four parts. Two can be copied exactly from data we already have; two must be modelled.

| Part | How | Data we have |
|---|---|---|
| **Requests** (dealers, times, cars, options, list prices, typical fees, notes) | **Replay exactly** per seed: the same seed gives every team the same requests | Events of 570+ played worlds (`runs/km/harvest_req.jsonl`, 568k requests), more on demand |
| **What notes and cars really do** (ready later, closed sites, plates, hours, EV charge) | Replay per order from the reveals of played weeks; for unplayed orders draw from fitted shares | Reveals of every world we played (`world.reveal()`) |
| **Dealers and competitor** (who wins a quote) | Model: competitor price = list x lane x day x week level x noise, dealer picks by value of speed; trust +1%/order (rules), competitor reacts each morning to our win share per dealer | 1.0M quotes with outcomes (model.json fit), fork probes with exact thresholds (kit-09, 415 requests), our journals |
| **Drivers** (who books, when, at what fee, drops) | Model, from the rules: roster (exact per world), who works each day, a cost per gig (drive + trip to pickup + ticket home + extras), books when fee - cost beats the day's other options and the expected value of waiting; learns our raises; drops more when the fee only just pays | 160 random-fee exploration weeks (kit-03: the cleanest data), 3,000+ journal weeks with every post, reprice, view and booking, reveals with every view and the fee seen |

Rules that are exact (no model needed): deadlines, refunds by lateness, release fees, failed-visit costs, fines,
pairs (12-hour limit), deadline warnings 3 hours before the last pickup time, the ledger.

## Steps

| # | Step | Gate / output | Effort |
|---|---|---|---|
| 0 | Local `World` class with the same API as `core/spread.ts` (advance, act, snapshot, score, roster, events), event queue, ledger, deterministic random numbers. `core/engine.ts` and `algo.ts` run unchanged against it | One week plays end to end in-process | 2 to 3 h |
| 1 | Request replay from recorded worlds + note/car truth from reveals | Same requests as the server for any recorded seed | 1 to 2 h |
| 2 | Dealer + competitor model, fitted on the quote data | Win rate by price bin, by trust, by day matches server journals within 2 points | 2 to 4 h |
| 3 | Driver model, fitted on exploration weeks + journals (likelihood fit of a few parameters per mechanism) | Booking curve (share booked within 1 h, 6 h, before warning) by fee multiple and lead time matches within 3 points; drops 12 to 13% | 4 to 8 h |
| 4 | Events: outage, flu, bulk order, price war, snow; visits failing; order changes and cancellations | Their weekly counts match reveals | 2 h |
| 5 | Validation: level gate and ranking gate on the stored A/B results | Pass/fail report | 1 to 2 h |
| 6 | Speed: 32 worker processes; profile and cache plan() | Over 100 weeks/s | 1 to 2 h |
| 7 | Use: big searches locally (thousands of configs, new policies), prove the top 3 on the server | New candidates for kit-best | ongoing |

Total to a validated copy: about 13 to 23 hours of work. The final is Sunday 08:00 Helsinki (07:00 CET); it can be
done in time only if steps 3 and 5 go smoothly.

## Risks

- **Drivers are the hard part and the part that matters most.** Our biggest gain (capacity pricing) came from
  driver scarcity. A driver model that gets capacity wrong will rank capacity ideas wrong. The ranking gate exists
  for this; if it fails, the copy is only good for coarse screening.
- **Hidden rules we have not seen** (exact waiting logic, belief fading speed, competitor reaction steps). Calibrate
  the effect, not the mechanism, and keep checking against the server.
- **Overfitting to the copy.** A search over thousands of configs will find quirks of our model. Every local winner
  must be proved on server seeds never used (the rule we already follow).
- **Cheaper alternative if time runs out:** steps 0 to 2 only (requests replayed, dealers modelled, drivers taken
  from a simple fitted booking hazard per gig-hour, the same model the algorithm uses). That copy is fast and
  good at pricing questions, weak at driver questions.
