# Bahn-Spread research

The paper trail of every test, built like `/root/system/research/` (the `research-log` system).
Two jobs: never test an old idea twice by accident, and find new ideas in old results.
Level 8 unless said otherwise. Every session (any agent) follows the loop below without being asked.

## Files

| File | What | When to touch |
|---|---|---|
| `LEDGER.md` | The index: one table row per test or study, newest first. Research only | Start and end of every test (`log.py`) |
| `ACTIVITY.md` | Raw event log, one stamped line per action, append only. Also the place for everything that is not research | Written by `log.py`, never edited |
| `KNOWLEDGE.md` | What we believe now, one line each, with confidence | When a result changes a belief |
| `GOTCHAS.md` | Traps that already cost us | When one bites |
| `BACKLOG.md` | Ideas not yet tested, best first | Add freely; claim before starting; delete the row when tested |
| `<topic>/LOG.md` | Detail of one topic: plan, seeds, numbers, verdict | During the work |
| `archive/<topic>/` | Finished topics | `log.py archive TOPIC` |
| `log.py` | The helper that writes all of the above safely when several sessions run | Every step below |

Run it as `/root/system/venv/bin/python Bahn-Spread/research/log.py ...` (from the project folder).

## What goes in the ledger

Research only. A row needs a **question and a result** (or an open plan): a test of an idea, knob, model or
config, a proof run, a ranking round result, a measured fact about the game.

Not research, never a ledger row: folders moved or cleaned up, files or docs organised, tools written, bugs
and crashes fixed, replay or identity checks after a move, "started" or "running" notes for a job (use `open`
for a real study, nothing for a quick test). Log these with `log.py note "text"`: they go to `ACTIVITY.md` only.
If one piece of work has both, split it: the result in the ledger, the rest as a note.

## The loop

**1. Recall first.** Before any new test, search the trail:

```bash
log.py find requote            # every line on record holding the word (several words = all must match)
log.py topics                  # the topics so far, with how they ended
```

Try the idea's name, its knob name and a synonym. If there is prior work, stop and tell the user what was
done, on which base and seeds, the numbers and the verdict, then ask: extend, re-open, or go on anyway.
A `no-edge` row on an older base is not a reason to skip, it is a reason to say why the new base changes it.
Read `KNOWLEDGE.md` and `GOTCHAS.md` once at the start of a session. For new ideas, read the `parked`,
`inconclusive` and `ship-candidate` rows and the "Next" lines of the topic logs.

**2. Open (write the plan before the numbers exist).**

```bash
log.py open pooling "holding new orders 1 h forms more pairs, +200 a week" \
    "kit-best defaults, m-1..32 screen then h-1..48 proof, mean difference ± SE, ranked weeks" \
    "under 2 SE on m-, or fewer ranked weeks"
```

This creates `pooling/LOG.md` with the plan and puts an `open` row on the ledger, so other sessions see the
topic is taken. If the idea is in `BACKLOG.md`, put your session and time in its Claimed cell.
A 10 minute check needs no `open`: log it with `add` when done.

**3. Work.** Notes, commands and partial numbers go in `<topic>/LOG.md` under the open block.

**4. Close.**

```bash
log.py close pooling no-edge "pool=1 on kit-best, m-1..32: -40 ± 90 (15/17), 32/32 ranked, worst 91.2%" "drop"
log.py add fees fact "booked fee vs opening fee on kit-best, k-1..12: median 1.15 x" "fact"     # one-shot
```

The text holds: what, base, seeds, mean difference ± standard error, weeks better/worse, ranked weeks, worst
on-time share. Dead ends and failed runs are logged too: that is the point.

**5. Propagate.**
- `KNOWLEDGE.md`: add or change the one-line belief. An overturned belief moves to "Overturned" with the date.
- `GOTCHAS.md`: add the trap if one bit.
- `BACKLOG.md`: delete the tested row; add follow-ups worth testing.
- A topic that needs no more work: `log.py archive TOPIC`.

## Status words

| Status | Meaning |
|---|---|
| `open` | Running now, taken by a session |
| `shipped` | In the best model (`kit-best/` defaults) |
| `ship-candidate` | A gain on screening seeds, not yet proved on fresh seeds |
| `no-edge` | Lost, or no gain beyond noise |
| `inconclusive` | Too thin to tell |
| `parked` | Works but not worth it now; may come back |
| `fact` | A measurement, nothing to adopt |

## Test rules

- Compare on the same seeds against the current best (`kit-best/`, its defaults), at least 16 weeks, and give
  the mean difference ± standard error, weeks better/worse, ranked weeks, worst on-time share.
- Seeds: `m-` screening, `h-` proof (never used to choose anything). Older kits used `i-`, `n-`, `f-`, `q-`, `r-`.
- Never ranking runs (`--board`, `--final`) from test scripts. The approval key only with the team's explicit approval for one named run.
- Runner: `kit-best/tools/sweep.sh`, table: `kit-best/tools/cmp.py TAG` (run from kit-best/). Rows land in `runs/bench.jsonl` (kit `kit-best`).
- Work before 14 Nov 03:00 lives in the kits' `RESEARCH.md`; the ledger summarises it.

Old kits (kit-01 to kit-10, kit-cmb, kit-fc, kit-ideas, kit-max, kit-rq, kit-run1) were moved to `z-archive/` on 14 Nov; paths in older ledger rows like `kit-max/...` now live at `z-archive/kit-max/...`. The current best model is `kit-best/`; experiments run in `kit-lab/`.
