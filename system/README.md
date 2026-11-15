# kit-best: the best model, cleaned up

Level 8 car-transport dispatcher for Bahn: Spread. This is the model that took **rank 4 of 48** in ranking round
"Saturday 09:00" as team **Edge101** (72,569 over 5 weeks), and the starting point for the next round of iterations.

It plays exactly like `z-old-kits/kit-max/BEST4.cfg`: 16 practice weeks replayed with this folder gave the same margin, orders
and on-time share to the cent. Everything switched off in earlier experiments is removed (algo 602 → 218 lines,
engine 863 → 681), and the best values are the defaults, so a plain run plays the best model.

## Results

| Test | Weeks | Old best (kit-run1) | This model | Difference a week | Ranked |
|---|---|---|---|---|---|
| Fresh seeds k-1..64 | 64 | 14,317 | 15,304 | **+987 ± 116** (better in 56 of 64) | 62/64 both |
| Untouched seeds h-1..48 | 48 | 14,675 | 15,674 | +999 | 45 → 46 of 48 |
| Ranking round Sat 09:00 (same 5 worlds) | 5 | 68,755 (rank 12) | 72,569 (rank 4) | +763 | 5/5 both |

All rows: `docs/MODEL.txt` (RESULTS). Every test ever run: `../research/LEDGER.md`.

## Quick start

```sh
cd Bahn-Spread/kit-best
set -a && source ../.env && set +a        # loads the keys; never print .env
bun core/run.ts --seed my-test-1          # one practice week, level 8, prints every day
bun core/run.ts --seed my-test-1 --set capLam=5,markupMin=1.3  # the same week with other values
bun core/model.ts                         # self-check of the two models
```

Ranking runs and the final: `bun core/run.ts --board` / `bun core/run.ts --final`. Both use `SPREAD_KEY_OFFICIAL` (the team
that key belongs to). The key `SPREAD_KEY_ONLY_USE_THIS_ON_APPROVAL` is only used with the team's explicit approval
for one named run, e.g. `SPREAD_KEY_OFFICIAL="$SPREAD_KEY_ONLY_USE_THIS_ON_APPROVAL" bun core/run.ts --board`.

## How it decides (one idea)

For every car, the booking model estimates **the fee at which a driver takes it in time**. That number drives everything:

```
price request ──► read note ──► for each delivery option: plan the cheapest fee schedule (booking model)
                                   │      → expected fee + chance a driver books before the last pickup time
                                   ▼
                 drop options with < 85% chance; 85–95% sell 0.2 × list dearer
                 full town / full deadline day → 0.25 × list dearer
                                   ▼
                 price = argmax  P(win | price) × (price − expected fee − 4 € × (drive h + 1))   from 1.28 to 2.0 × list
                         (shifted: −0.05 round trip, +0.3 competitor outage nearby)
                                   ▼
won ──► join an open one-car gig nearby as a two-car gig (split if unbooked after 4 h) or post alone
        fees: planned opening + hourly raises → early ramp to 1.6 × typical in the last 10 h
              → deadline warning: 1.3, +0.15 per 30 min → past last pickup: back to 1.2
every answer ──► relearn this week's competitor price level (last 300 answers)
```

**Docs (`docs/`):** `MODEL.txt` and `MODEL.pdf` (the whole model on a few pages: how it decides, all 35 rules, all
parameters, results), and `PARAMS.csv` (every tunable value with the alternatives already tested).

The three ideas that made this model better than the old best (kit-run1):

1. **Denoised typical fee** (`core/data/typ.json`, rule 1). The dealer's typical fee carries about 13% noise that drivers
   ignore. Gigs and prices use a lane-table prediction instead. +195 to +400 a week.
2. **Capacity pricing** (rules 11 and 12). Drivers are the bottleneck at level 8. A lower price floor (1.28 instead
   of 1.38) plus a cost of 4 EUR per driver-hour in the price choice ration drivers better. +601 a week.
3. **Day cap 0.10** (rule 10, was 0.09). +194 a week, one fewer ranked week in 48.

## Files

```
kit-best/
  algo.ts            EDIT HERE: every decision and every tunable value (PARAMS = the best values)
                       quote()  which requests to take and at what price
                       fees()   the driver fee schedule of a gig
                       pair()   two cars for one driver
                       learn()  this week's competitor price level
  README.md          this page
  docs/              MODEL.txt, MODEL.pdf (the whole model in plain words), PARAMS.csv (every value + what was tested)
  tsconfig.json      editor settings
  core/              the machinery: edit only when an idea cannot be written in algo.ts (see below)
    engine.ts          books, posting, two-car gigs, timers, retries, denoised typical fee, restart in the final
    run.ts             play one week: practice, --board or --final
    week.ts            one practice week + a row in Bahn-Spread/runs/bench.jsonl (used by the tools)
    model.ts           booking model and win model lookups (reads data/model.json)
    notes.ts           dealer-note reader (ready later / must arrive by)
    spread.ts types.ts the kit's API client (from the organisers)
    data/              model.json (the two models), typ.json (typical-fee lane table, 899 lanes)
    tools/             sweep.sh, lockweek.sh, cmp.py (testing); fit_typ.py, harvest_req.ts (how typ.json was built)
```

All commands work from any folder; the examples assume you are in `kit-best/`.

## Editing core files: when and how

**Default: change only `algo.ts`.** A new pricing rule, a new fee rule, a new capacity rule, a new value: all of it
goes into `quote()`, `fees()`, `pair()`, `learn()` and `PARAMS`. The algorithm can read everything the engine knows
through `ctx` (drivers, places, our orders, dealer trust, open gigs, `ctx.memory` for its own state).

**Edit `core/` only when the idea needs something `algo.ts` cannot do.** Over the 45 ideas tested so far, about one
in five needed it:

| You want to | File |
|---|---|
| React to an event the algorithm does not see yet (a drop, a view, a failed visit) or add a timer | `core/engine.ts` (`handle()`, `fireTimers()`) |
| Change how gigs are posted, joined into pairs, split, reposted or retried | `core/engine.ts` (`post()`, `tryPair()`, `split()`, `repost()`, `retry()`) |
| Change what the algorithm can read (a new `ctx` method) | `core/engine.ts` (`Ctx` and `Desk`) |
| Change how the typical fee is replaced | `core/engine.ts` (`denoise()`) and `core/data/typ.json` |
| Read more from dealer notes | `core/notes.ts` |
| Use a refitted model | `core/data/model.json` (`core/model.ts` only if the model's inputs change) |
| Change the API client | never: `core/spread.ts` and `core/types.ts` come from the organisers' kit |

**How:**

1. Add a parameter to `PARAMS` in `algo.ts` with its "off" value (for example `myIdea: 0`) and read it in the core
   file as `this.p.myIdea`. With the parameter off, the code must play exactly as before.
2. Check that nothing changed with the idea off: replay 16 weeks and compare to the cent with the last rows
   (worlds are deterministic, so any difference is a bug):
   ```sh
   bash core/tools/sweep.sh 16 m check "best|"
   python3 core/tools/cmp.py check best      # margins must equal earlier rows of the same seeds (e.g. variant "verify best")
   ```
3. Test the idea switched on (next section), and prove it on fresh seeds before making it the default.
4. A new `data/model.json` or `data/typ.json` must be fitted on seeds other than the test seeds, and must win on
   fresh weeks, not only in log loss: our two model refits predicted better and played worse (-1,100 a week).
5. Write the result as one line in `../research/LEDGER.md`, and update `docs/` if a rule or value changes.

## How to test an idea (the rules that kept us honest)

```sh
bash core/tools/sweep.sh 48 m mytest "base|" "idea|capLam=5"   # 48 seeds, base and idea on the same weeks
python3 core/tools/cmp.py mytest base                           # difference ± SE, better/worse, ranked weeks
```

- Same seeds for base and idea (worlds are deterministic: same seed and actions give the same week to the cent).
- At least 48 weeks: one week swings by ±2,500, so smaller tests mostly measure luck.
- Prove a winner on seeds never used to choose it (we used `h-` and `k-`). Searches that took the best of several
  candidates at 2 SE on 32 weeks failed on fresh weeks every time.
- Report mean margin, unranked weeks as 0 too, ranked weeks and the worst on-time share.
- Write each result as one line in `../research/LEDGER.md`.

To add a new idea: give it a parameter in `PARAMS` set to "off" (so the default plays the best model), test it as
above, and keep the code only if it survives the proof.

## What did not work (so nobody repeats it blindly)

Requote before the dealer decides, flat fees, delayed posting, direct offers (early, chain, rescue), buying dealer
trust (cheaper prices, risk pricing, dearer fees for trusted dealers), learning the competitor live beyond the week
level (day, dealer, place, lane-shape), competitor lane tables, refitting the booking model on our own weeks
(-1,100), per-lane booking offsets, driver counts weighted by completed gigs, per-option prices, same-day premium,
capacity cost scaled by town, day, load, roster or weekday. Details and numbers: `../research/LEDGER.md`,
lessons: `../research/KNOWLEDGE.md` and `../research/GOTCHAS.md`.

Open lead: the biggest dealer's trust count averages only 14.5 of 25 at its requests (0.7 on Monday) because trust
counts only on delivery; the three ways tried to build it faster all lost money.
