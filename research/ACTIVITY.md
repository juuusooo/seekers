2026-11-14T10:12Z juuso MIGRATE ledger bullets -> table, 104 rows; ACTIVITY.md started
2026-11-14T10:13Z juuso RECALL pool hits=1
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 11:20): kit-best organized: data/ (model.json, typ.json), docs/ (MODEL.txt, MODEL.pdf 10 pages, LOGIC.csv, PARAMS.csv, RESULTS.csv), tools/make_docs.py rebuilds the .txt and .pdf from the CSVs. Replay m-1..4 after the move: identical to the cent
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 11:06): kit-lab/ = working copy of kit-best for experiments (kit-best stays clean); kit-10 moved to z-archive (idle since 01:12).
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 10:40): housekeeping: old kits moved to `z-archive/` (kit-10 stays: another session works in it; kit-live stays: this session's folder).
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 10:30): new folder `kit-best/`: BEST4 cleaned up (algo 602 → 218 lines, engine 863 → 681, 45 switched-off experiments removed, best values as defaults), docs README.md, LOGIC.csv (35 rules), PARAMS.csv, RESULTS.csv, tools/. Replay check m-1..16: 16/16 weeks identical to kit-max BEST4 to the cent · starting point for the next round
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 08:57): final check started: old best, BEST4, C on 64 new weeks k-1..64
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 05:36): random local search rs1 started (3 knobs at a time, s-1..32, from C)
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 04:28): trust gain in the price `trustGain=0.3/0.6` (future value of +1 dealer trust) on T, m-1..32 · running
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 04:21): proof of T against the old best on h-1..48 started (variants `h1 base`, `h1 T`) · running
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 04:02): started automatic coordinate search o2 on t-1..32 from T · running
2026-11-14T00:00Z juuso NOTE moved from ledger (14 Nov 04:00): delayed posting `postLeadH=24/36` crashed (empty legs on posting); fixed with a guard, rerun as lead12b/lead24b · bug
2026-11-14T10:16Z juuso NOTE ledger cleaned: 10 non-research items moved to ACTIVITY.md, status info removed, log.py note added
2026-11-14T10:47Z juuso RECALL latency hits=0
2026-11-14T10:54Z juuso RECALL verda hits=0
2026-11-14T10:54Z juuso RECALL GPU hits=0
2026-11-14T11:07Z juuso RECALL llm hits=0
2026-11-14T11:07Z juuso RECALL LLM hits=0
2026-11-14T11:07Z juuso RECALL model hits=27
2026-11-14T11:07Z juuso RECALL claude hits=0
2026-11-14T11:12Z juuso RECALL driver hits=43
2026-11-14T11:12Z juuso RECALL clone hits=0
2026-11-14T11:12Z juuso RECALL emulator hits=0
2026-11-14T11:13Z juuso OPEN clone status=open
2026-11-14T11:13Z juuso LOG drivers status=fact
2026-11-14T11:15Z juuso RECALL view hits=5
2026-11-14T11:16Z juuso OPEN views status=open
2026-11-14T11:21Z juuso RECALL price+war hits=2
2026-11-14T11:21Z juuso RECALL war hits=7
2026-11-14T11:21Z juuso RECALL outage hits=3
2026-11-14T11:21Z juuso RECALL world+level hits=6
2026-11-14T11:21Z juuso RECALL worldN hits=2
2026-11-14T11:21Z juuso RECALL note hits=6
2026-11-14T11:21Z juuso RECALL hardPrice hits=7
2026-11-14T11:21Z juuso LOG tuning status=no-edge
2026-11-14T11:21Z juuso RECALL warGap hits=1
2026-11-14T11:21Z juuso LOG llm status=fact
2026-11-14T11:24Z juuso NOTE kit-llm/ created as a copy of kit-best/ (LLM decision kit; JEV over OpenRouter per request, Claude over ACP hourly). Probes in research/llm/
2026-11-14T11:25Z juuso RECALL night hits=1
2026-11-14T11:25Z juuso RECALL overnight hits=0
2026-11-14T11:25Z juuso RECALL morning hits=1
2026-11-14T11:25Z juuso RECALL ramp hits=8
2026-11-14T11:25Z juuso RECALL hazard hits=1
2026-11-14T11:25Z juuso RECALL calibrat hits=2
2026-11-14T11:33Z juuso CLOSE clone status=parked
2026-11-14T11:33Z juuso LOG views status=no-edge
2026-11-14T11:33Z juuso LOG views status=fact
2026-11-14T11:33Z juuso LOG booking_model status=fact
2026-11-14T11:33Z juuso OPEN competitor status=open
2026-11-14T11:34Z juuso OPEN llm status=open
2026-11-14T11:36Z juuso RECALL note hits=9
2026-11-14T11:36Z juuso RECALL note hits=9
2026-11-14T11:40Z juuso OPEN notes status=open
2026-11-14T11:50Z juuso CLOSE notes status=fact
2026-11-14T11:54Z juuso NOTE kit-price/ created (copy of kit-best + online competitor price filter in algo.ts, knob priceLearn, data core/data/price.json); smoke week px-1 ran
2026-11-14T11:55Z juuso RECALL hours hits=22
2026-11-14T11:55Z juuso RECALL pair+plates hits=4
2026-11-14T12:04Z juuso NOTE kit-llm: JEV dispatcher (llm=1/2), JEV supervisor (sup=1), Featherless provider (llmVia=1, DeepSeek V4.1 Flash thinking off, 0.70 s, holds 32 parallel, no probabilities), live-clock background quoting. Parity with llm off: m-1..6 equal kit-best to the cent. Screens on llm-1..16 running (variant s1 *)
2026-11-14T12:05Z juuso OPEN notes status=open
2026-11-14T12:08Z juuso RECALL final hits=7
2026-11-14T12:19Z juuso LOG testfinal status=fact
2026-11-14T12:55Z juuso CLOSE llm status=no-edge
2026-11-14T13:01Z juuso NOTE kit-final/ = kit-best + recorder (core/rec.ts, FINAL_REC=folder: wall-clock answer time per request, every action batch with results, every http call, stream events, journal). Recorder off and on: m-1 = 10,369.40, equal to kit-best to the cent. Launcher runs/testfinal_1114_2000/go.sh waits for 19:40 and plays the 20:00 test final on SPREAD_KEY (user asked), then pulls events, reveal, drivers, score.
2026-11-14T13:16Z juuso CLOSE competitor status=ship-candidate
2026-11-14T13:18Z juuso CLOSE notes status=ship-candidate
2026-11-14T13:32Z juuso LOG proof status=shipped
2026-11-14T13:32Z juuso LOG competitor status=inconclusive
2026-11-14T13:32Z juuso NOTE merged kit-price algo.ts + price.json into kit-best (BEST5 defaults); old algo saved as z-old-kits/kit-max/algo_kit-best_BEST4_1114.ts; BEST5.cfg written; kit-best README + ledger header + KNOWLEDGE updated
2026-11-14T13:43Z juuso LOG local_sim status=ship-candidate
2026-11-14T14:03Z juuso RECALL final hits=9
2026-11-14T14:03Z juuso RECALL thursday hits=2
2026-11-14T14:03Z juuso RECALL friday hits=2
2026-11-14T14:03Z juuso RECALL monday hits=3
2026-11-14T14:03Z juuso RECALL night hits=3
2026-11-14T14:03Z juuso RECALL outage hits=4
2026-11-14T14:03Z juuso RECALL price war hits=1
2026-11-14T14:03Z juuso RECALL triple hits=0
2026-11-14T14:03Z juuso RECALL three hits=4
2026-11-14T14:03Z juuso RECALL bookLearn hits=0
2026-11-14T14:03Z juuso RECALL booking level hits=0
2026-11-14T14:03Z juuso RECALL controller hits=0
2026-11-14T14:03Z juuso RECALL adaptive hits=0
2026-11-14T14:03Z juuso RECALL weekend hits=0
2026-11-14T14:03Z juuso RECALL saturday hits=4
2026-11-14T14:03Z juuso RECALL trade-in hits=2
2026-11-14T14:03Z juuso RECALL private hits=3
2026-11-14T14:03Z juuso RECALL within_3 hits=0
2026-11-14T14:04Z juuso LOG local_sim status=ship-candidate
2026-11-14T14:06Z juuso LOG fees status=fact
2026-11-14T14:09Z juuso NOTE kit-sim1/ created: kit-best (BEST5) + stacked local-sim winner (j1 search config + optSame=-0.05). Local 18,189 vs 16,338 (+1,851 ± 91, 151/158), orders +25%. Review sheet kit-sim1/SIM1.md. Not on the server yet.
2026-11-14T14:14Z juuso LOG competitor status=no-edge
2026-11-14T14:26Z juuso LOG local_sim status=ship-candidate
2026-11-14T14:27Z juuso NOTE kit-best promoted to BEST6 on the user's instruction: openMin 0.6 -> 0.706, lateFee 1.2 -> 0.832 (algo.ts defaults, README section, PARAMS.csv). BEST5 algo backup runs/lab/kit-best_algo_BEST5_backup.ts. sim/opt/kit/algo.ts synced to BEST6 (old: algo_best5.ts).
2026-11-14T14:30Z juuso NOTE kit-b6n/ created: kit-best BEST6 + note fixes from kit-notes (engine.ts, notes.ts copied; algo.ts 3-way merged, 13 lines), switches off by default, rows tagged kit-b6n. Replay switches off == BEST6 (16 local weeks). sim/run.ts: --kit loads a kit's own core/engine.ts + algo.ts; fixed --set being ignored for non kit-best kits.
2026-11-14T14:38Z juuso LOG notes status=ship-candidate
2026-11-14T14:39Z juuso NOTE kit-best promoted to BEST7 on the user's instruction: kit-b6n algo.ts + core/engine.ts + core/notes.ts, defaults noteHours=1,pairFlags=1 (README section, PARAMS.csv, ledger header). BEST6 backup runs/lab/kit-best_BEST6_backup/. Fast sim copy sim/opt stays BEST6 (no note fixes in its optimized engine).
2026-11-14T14:40Z juuso OPEN raise_teach status=open
2026-11-14T14:40Z juuso OPEN due_day status=open
2026-11-14T14:40Z juuso OPEN brake status=open
2026-11-14T14:44Z juuso RECALL BEST7 hits=8
2026-11-14T14:44Z juuso RECALL GPU hits=0
2026-11-14T14:46Z juuso RECALL calibrat hits=2
2026-11-14T14:46Z juuso RECALL sim1 hits=3
2026-11-14T14:56Z juuso OPEN sim_calib status=open
2026-11-14T14:58Z juuso NOTE kit-best promoted to BEST8 on the user's instruction: price by deadline day dueMon=-0.03, dueFri=0.08 (algo.ts PARAMS + 3 lines in quote, PARAMS.csv). BEST7 again: --set dueMon=0,dueFri=0 (replay equal to BEST7 on 8 local weeks; backup runs/lab/kit-best_algo_BEST7_backup.ts). kit-i135/ = idea kit (BEST7 copy + knobs teach, dueMon, dueFri, dueMonF, dueMid, todayPrice, brakeAt, quoteFrom, default off). Server comparison b8-1..48 (tags 'b8 BEST8' / 'b8 BEST7') running. sim/opt/kit not synced.
2026-11-14T15:10Z juuso CLOSE due_day status=ship-candidate
2026-11-14T15:10Z juuso CLOSE raise_teach status=no-edge
2026-11-14T15:10Z juuso CLOSE brake status=no-edge
2026-11-14T15:29Z juuso NOTE Ranking round started 14 Nov 16:29 on the user's instruction: level 8, BEST8 (frozen snapshot runs/board/kit-best8-snap of kit-best) on SPREAD_KEY_2 = team Seekers, 5 runs one after another (runs/board/play_best8_seekers_round.sh, output play_best8_seekers_round.out). First run world we8247c23d4327dec7400.
2026-11-14T15:31Z juuso LOG ranking status=fact
2026-11-14T15:46Z juuso RECALL tree hits=0
2026-11-14T15:46Z juuso RECALL lightgbm hits=1
2026-11-14T15:46Z juuso RECALL cost model hits=0
2026-11-14T15:46Z juuso RECALL realized hits=0
2026-11-14T15:46Z juuso RECALL upper hits=0
2026-11-14T15:46Z juuso RECALL quantile hits=0
2026-11-14T15:50Z juuso NOTE sim_calib: sim/cal/ (calibrated copy of sim/opt, own folder), research/sim_calib scripts, sv-1..48 exported to sim/data + sim/fit (server reads only, practice keys)
2026-11-14T15:56Z juuso RECALL ledger+cost hits=0
2026-11-14T15:56Z juuso OPEN real_cost status=open
2026-11-14T15:57Z juuso RECALL late hits=56
2026-11-14T16:01Z juuso RECALL dutch hits=0
2026-11-14T16:01Z juuso RECALL descend hits=0
2026-11-14T16:01Z juuso RECALL fees+fall hits=1
2026-11-14T16:01Z juuso RECALL open+high hits=2
2026-11-14T16:01Z juuso RECALL viewers hits=0
2026-11-14T16:01Z juuso RECALL booking+speed hits=0
2026-11-14T16:01Z juuso RECALL adaptive hits=0
2026-11-14T16:01Z juuso RECALL chain hits=2
2026-11-14T16:01Z juuso RECALL three-car hits=0
2026-11-14T16:01Z juuso RECALL direct+offer hits=3
2026-11-14T16:01Z juuso RECALL price+war hits=5
2026-11-14T16:01Z juuso RECALL steer hits=0
2026-11-14T16:01Z juuso RECALL within_3 hits=0
2026-11-14T16:01Z juuso RECALL near+the+delivery hits=1
2026-11-14T16:01Z juuso RECALL reacts hits=0
2026-11-14T16:01Z juuso RECALL win+share hits=6
2026-11-14T16:01Z juuso RECALL bulk hits=0
2026-11-14T16:01Z juuso RECALL saturday hits=5
2026-11-14T16:01Z juuso RECALL experienced hits=0
2026-11-14T16:01Z juuso RECALL drop hits=31
2026-11-14T16:02Z juuso NOTE kit-wild/ created = copy of kit-best BEST8 for wild idea screening (knobs default off), rows kit kit-wild, seeds wd-
2026-11-14T16:05Z juuso OPEN wild status=open
2026-11-14T16:11Z juuso RECALL bulk hits=0
2026-11-14T16:11Z juuso RECALL flu hits=0
2026-11-14T16:11Z juuso LOG bulk status=fact
2026-11-14T16:11Z juuso LOG drivers status=fact
2026-11-14T16:18Z juuso RECALL terminal hits=0
2026-11-14T16:18Z juuso RECALL additive hits=0
2026-11-14T16:25Z juuso NOTE BEST9: realized cost merged into kit-best defaults (costW=1; core/cost.ts, core/data/cost.json). Replay: kit-best = kit-cost costW=1 and kit-best --set costW=0 = BEST8, 158 local weeks to the cent. Backup runs/lab/kit-best_algo_BEST8_backup.ts. README, ledger header, KNOWLEDGE updated
2026-11-14T16:32Z juuso CLOSE real_cost status=shipped
2026-11-14T16:35Z juuso LOG fees status=no-edge
2026-11-14T16:35Z juuso LOG capacity status=no-edge
2026-11-14T16:35Z juuso LOG pairing status=no-edge
2026-11-14T16:35Z juuso LOG drivers status=fact
2026-11-14T16:35Z juuso CLOSE sim_calib status=no-edge
2026-11-14T16:36Z juuso NOTE sim_calib closed; 3 ideas from Uber Freight / surge papers added to BACKLOG
2026-11-14T17:10Z juuso CLOSE wild status=shipped
2026-11-14T17:10Z juuso NOTE kit-best is BEST10 (floorLvl=1 default; BEST9 backup runs/lab/kit-best_algo_BEST9_backup.ts; replay t10-1, t10-2 equal to kit-wild to the cent). kit-wild default floorLvl set to 1 too, so its base = BEST10
2026-11-14T17:13Z juuso RECALL second+look hits=0
2026-11-14T17:13Z juuso RECALL last-minute hits=0
2026-11-14T17:13Z juuso RECALL requote hits=6
2026-11-14T17:13Z juuso RECALL 7+minutes hits=5
2026-11-14T17:13Z juuso RECALL look hits=1
2026-11-14T17:15Z juuso NOTE viz/: live viewer of one practice week (bun viz/server.ts, http://127.0.0.1:7088, Start button, speed 1 to 100 world minutes a second). Plays kit-best unchanged through a watched advance call, practice only, uses the runs/slots locks; Stop deletes the world. Checked on seeds viz-check-1..3 (viz-check-1 full week: 19,012, 481 orders, 95.8% on time, ranked).
2026-11-14T17:15Z juuso OPEN look status=open
2026-11-14T17:16Z juuso OPEN wild2 status=open
2026-11-14T17:16Z juuso RECALL night hits=5
2026-11-14T17:16Z juuso RECALL pool hits=16
2026-11-14T17:16Z juuso RECALL bulk hits=5
2026-11-14T17:16Z juuso RECALL per-option hits=5
2026-11-14T17:16Z juuso RECALL calib hits=12
2026-11-14T17:16Z juuso RECALL hazard hits=3
2026-11-14T17:32Z juuso RECALL release hits=1
2026-11-14T17:32Z juuso RECALL driver_late hits=0
2026-11-14T17:32Z juuso RECALL repost hits=0
2026-11-14T17:32Z juuso RECALL notif hits=1
2026-11-14T17:32Z juuso RECALL withdraw hits=0
2026-11-14T17:32Z juuso RECALL offer hits=8
2026-11-14T17:32Z juuso RECALL audience hits=3
2026-11-14T17:33Z juuso RECALL replan hits=0
2026-11-14T17:33Z juuso RECALL drop hits=36
2026-11-14T17:35Z juuso CLOSE look status=no-edge
2026-11-14T17:35Z juuso LOG actions status=fact
2026-11-14T17:35Z juuso OPEN drop_replan status=open
2026-11-14T17:35Z juuso RECALL minBookChance hits=10
2026-11-14T17:35Z juuso RECALL hardChance hits=4
2026-11-14T17:35Z juuso RECALL hardPrice hits=9
2026-11-14T17:35Z juuso RECALL decline hits=9
2026-11-14T17:35Z juuso RECALL goodwill hits=0
2026-11-14T17:39Z juuso NOTE sim-experimental/: Rust port of the local world + kit-best desk (BEST10). Bit-identical to sim/ on 206 weeks (5.5M events, every desk decision; bash sim-experimental/check.sh). Speed vs sim/ same minute: one week one core 724 -> 18.3 ms (40x), 96 weeks 9.95 -> 0.19 s (52x), batch 10 variants x 144 weeks 920 weeks/s (95x). Added seeds rd-1..48 to sim/data + sim/fit (server BEST8/BEST9 proof weeks): sim BEST9-BEST8 +751 +/- 126 vs server +644 +/- 106, level +3.6%, corr 0.86. kit-best changes must be ported to src/desk.rs (README).
2026-11-14T17:44Z juuso RECALL grid hits=5
2026-11-14T17:44Z juuso RECALL joint hits=5
2026-11-14T17:44Z juuso RECALL search hits=29
2026-11-14T17:44Z juuso RECALL optuna hits=0
2026-11-14T17:45Z juuso OPEN fast_grid status=open
2026-11-14T17:45Z juuso CLOSE drop_replan status=no-edge
2026-11-14T17:48Z juuso LOG fees status=no-edge
2026-11-14T17:56Z juuso NOTE kit-final/ updated 19:56 Helsinki (user asked, before the 20:00 test final): now current kit-best (algo.ts of 19:53, core/, data with cost.json and price.json) + recorder only in core/run.ts (break and score records; the per-request and http recorder hooks of the old engine.ts / spread.ts are gone). Old kit-final (13:53 snapshot) in runs/lab/kit-final_1353_backup. go.sh restarted run.ts on the same final world f79ea25bd4dbcd5a391f1 before the start.
2026-11-14T17:58Z juuso NOTE kit-best is BEST11 on the user's instruction (openTilt=0.25, tiltRef=60; BEST10 = --set openTilt=0, backup runs/lab/kit-best_algo_BEST10_backup.ts; sim identity 158 weeks vs kit-wild variant 0 difference). Ranking round level 8 with snapshot runs/board/kit-best11-snap on SPREAD_KEY_2 (Seekers) started, user asked
2026-11-14T18:34Z juuso LOG testfinal status=fact
2026-11-14T18:38Z juuso LOG ranking status=fact
2026-11-14T18:51Z juuso RECALL best11 hits=2
2026-11-14T18:52Z juuso RECALL chain hits=3
2026-11-14T18:52Z juuso RECALL triple hits=0
2026-11-14T18:52Z juuso RECALL three+cars hits=1
2026-11-14T18:52Z juuso RECALL round+trip hits=0
2026-11-14T18:52Z juuso RECALL return hits=0
2026-11-14T18:52Z juuso RECALL 3-car hits=1
2026-11-14T18:56Z juuso RECALL outage hits=5
2026-11-14T18:59Z juuso RECALL floorTyp hits=0
2026-11-14T18:59Z juuso RECALL short lane hits=0
2026-11-14T18:59Z juuso OPEN live_outage status=open
2026-11-14T19:02Z juuso LOG fees status=inconclusive
2026-11-14T19:30Z juuso CLOSE fast_grid status=no-edge
2026-11-14T19:46Z juuso NOTE sim-experimental: more exact speed work (shared per-seed tables, rank-based cost trees, arena queue). Still bit-identical on 206 weeks (+ BEST8 set, mixed knob set, v5c world). Search batch 160 variants x 96 weeks: 1,259 weeks/s vs sim/ 11.6 weeks/s = 108x (five alternated rounds, 107 to 110); one 96-week sweep 0.19 s vs 8.28 s (44x); one week one core 13.9 vs 626 ms (45x).
2026-11-14T19:53Z juuso CLOSE live_outage status=ship-candidate
2026-11-14T19:56Z juuso OPEN live_war status=open
2026-11-14T19:57Z juuso NOTE kit-out/ = copy of kit-best BEST11 (14 Nov 21:10 Helsinki) + outage region belief (outBayes, outageK, outPriorMax; data core/data/near80.json), price-war state (warBayes, warK, warFloor, off), floorTyp (off). Defaults: outBayes=1, outageK=1.2 = BEST12 candidate; --set outBayes=0,outageK=0 = BEST11 to the cent (sim 158 weeks). Its week.ts still writes kit 'kit-best' into bench.jsonl: tags lo1, lp1, lq1. Not ported to sim-experimental/src/desk.rs. Charts of the 20:00 test final in runs/testfinal_1114_2000/*.png
2026-11-14T20:06Z juuso NOTE BEST12 shipped on the user's instruction (14 Nov 21:30 Helsinki): kit-out/algo.ts + core/data/near80.json copied into kit-best and kit-final (kit-final keeps its recorder run.ts). Backups runs/lab/kit-best_algo_BEST11_backup.ts and kit-final_algo_BEST11_backup.ts. Replay from kit-best: lp-1 18,253.17, lp-2 13,284.27 = kit-out rows to the cent; outBayes=0,outageK=0 on lp-1 = 17,495.48 = BEST11. No other session had weeks running from kit-best at the swap. Not ported to sim-experimental/src/desk.rs: the Rust sim still plays BEST11
2026-11-14T20:13Z juuso CLOSE live_war status=no-edge
2026-11-14T20:13Z juuso RECALL chain hits=4
2026-11-14T20:13Z juuso RECALL tree hits=8
2026-11-14T20:13Z juuso RECALL residual hits=5
2026-11-14T20:13Z juuso RECALL win model hits=6
2026-11-14T20:13Z juuso RECALL Juhus hits=16
2026-11-14T20:13Z juuso RECALL pooling hits=2
2026-11-14T20:13Z juuso RECALL cost-to-go hits=1
2026-11-14T20:13Z juuso RECALL capRoster hits=1
2026-11-14T20:13Z juuso RECALL live hits=53
2026-11-14T20:13Z juuso RECALL final hits=24
2026-11-14T20:13Z juuso RECALL board hits=11
2026-11-14T20:13Z juuso RECALL rank hits=142
2026-11-14T20:14Z juuso OPEN best13 status=open
2026-11-14T20:16Z juuso RECALL BEST12 hits=7
2026-11-14T20:25Z juuso LOG best13 status=no-edge
2026-11-14T20:28Z juuso RECALL juhus hits=16
2026-11-14T20:28Z juuso RECALL request day hits=0
2026-11-14T20:28Z juuso RECALL slack hits=12
2026-11-14T20:28Z juuso RECALL weekday hits=16
2026-11-14T20:28Z juuso RECALL overload hits=0
2026-11-14T20:28Z juuso RECALL open orders hits=1
2026-11-14T20:28Z juuso RECALL mix hits=4
2026-11-14T20:28Z juuso OPEN juhus_gap status=open
2026-11-14T20:32Z juuso NOTE kit-jg/ = copy of kit-best BEST12 (14 Nov 22:35 Helsinki) + knobs floorEarly, earlyDays, capEarly, capLate (default off = BEST12). Study scripts research/juhus_gap/{load,wins,cost}.py. Server screen jg-1..24 tag jg1 running (rows carry kit 'kit-best')
2026-11-14T20:33Z juuso RECALL dueCapPer hits=19
2026-11-14T20:33Z juuso RECALL minBookChance hits=10
2026-11-14T20:33Z juuso RECALL safety hits=5
2026-11-14T20:33Z juuso RECALL unranked hits=25
2026-11-14T20:36Z juuso RECALL forecast hits=5
2026-11-14T20:36Z juuso RECALL snow hits=2
2026-11-14T20:37Z juuso NOTE 10 more charts of the 20:00 test final: runs/testfinal_1114_2000/chart2_01..10_*.png, script charts2.py in the same folder (gap to 20k, win rate by price, arrival day funnel, fee vs wait, fee raise steps, late orders, margin by option and due day, pickup towns, cost share vs top 5, orders won per day)
2026-11-14T20:38Z juuso LOG live_war status=no-edge
2026-11-14T20:41Z juuso LOG best13 status=no-edge
2026-11-14T20:41Z juuso NOTE best13 session stopped at the usage limit (14 Nov 21:40 Helsinki). kit-b13 = kit-best BEST12 + knobs default off (sim 158 weeks identical): costV 2/3, pDD, ddTop, pLane, trustA, trustTau. Cost-tree refit on 2,087 BEST9+ worlds (897,535 rows, runs/rc/rows2.*.jsonl; research/best13/pull2.sh, build2.ts, fit2.py) was fitting when stopped: log runs/rc/fit2.log, output kit-b13/core/data/cost2.json and cost3.json. Not yet screened: costV=2, costV=3, pLane, trustA on the server. No BEST13 made; kit-best untouched
2026-11-14T20:42Z juuso RECALL overnight hits=0
2026-11-14T20:42Z juuso RECALL night hits=8
2026-11-14T20:42Z juuso RECALL weekend hits=1
2026-11-14T20:42Z juuso RECALL time of day hits=0
2026-11-14T20:42Z juuso RECALL monday hits=21
2026-11-14T20:42Z juuso RECALL withdrawn hits=0
2026-11-14T20:43Z juuso OPEN fee_day status=open
2026-11-14T20:43Z juuso RECALL forecast hits=5
2026-11-14T20:43Z juuso RECALL snow hits=2
2026-11-14T20:43Z juuso RECALL late refund hits=4
2026-11-14T20:43Z juuso RECALL tier hits=0
2026-11-14T20:44Z juuso RECALL flu hits=2
2026-11-14T20:44Z juuso RECALL mass drop hits=0
2026-11-14T20:44Z juuso RECALL midnight hits=0
2026-11-14T20:45Z juuso RECALL feeScale hits=4
2026-11-14T20:45Z juuso RECALL opening+fee hits=15
2026-11-14T20:45Z juuso RECALL openMin hits=6
2026-11-14T20:46Z juuso LOG flu status=fact
2026-11-14T20:52Z juuso OPEN flu13 status=open
2026-11-14T21:15Z juuso LOG best13 status=ship-candidate
2026-11-14T21:37Z juuso RECALL pDD hits=1
2026-11-14T21:37Z juuso RECALL by+day hits=36
2026-11-14T21:37Z juuso RECALL per+weekday hits=6
2026-11-14T21:37Z juuso RECALL request+day hits=20
2026-11-14T21:37Z juuso RECALL day+floor hits=15
2026-11-14T21:39Z juuso NOTE BEST13 shipped on the user's instruction (14 Nov 23:40 Helsinki), before the fe1 proof finished: feeLate=0.95 patched into kit-best/algo.ts and kit-final/algo.ts (knobs feeMon, feeMid, feeLate). Backup runs/lab/kit-best_algo_BEST12_backup.ts. Replay from kit-best: fe-1 23,452.87, fe-2 15,472.82 = kit-out l95 rows to the cent; feeLate=1 on fe-1 = 23,409.73 = BEST12. kit-out defaults still BEST12 (feeLate=1) until its fe1 weeks end. Not ported to the Rust sim
2026-11-14T22:07Z juuso NOTE kit-flu rebuilt from kit-best BEST13 (only fluN, fluSame added, default off); the fl1 screen algo with all flu knobs is runs/lab/kit-flu_algo_on_BEST12_fl1.ts
2026-11-14T22:09Z juuso CLOSE fee_day status=shipped
2026-11-14T22:10Z juuso RECALL juhus hits=28
2026-11-14T22:13Z juuso RECALL drop+rate hits=2
2026-11-14T22:13Z juuso RECALL drop+hazard hits=0
2026-11-14T22:13Z juuso RECALL drops hits=14
2026-11-14T22:13Z juuso RECALL surplus hits=0
2026-11-14T22:13Z juuso RECALL open+fee hits=47
2026-11-14T22:13Z juuso RECALL openMin hits=6
2026-11-14T22:13Z juuso RECALL flat hits=34
2026-11-14T22:15Z juuso NOTE Final restart safety (14 Nov, 00:30 Helsinki): playFinal in core/engine.ts of kit-best, kit-final and kit-out now saves the algorithm's learned state (price filter, outage belief, pending quotes; about 130 KB) to runs/final_state/<worldId>.json every 3 s and loads it before rejoin() after a restart; FINAL_STATE=off switches it off, FINAL_STATE=<folder> moves it; every step in try/catch. Reason: ranking run 4 of 19:38 was cut by a 502 and resumed with a cold filter (14,524), and the test final's run.ts restarted once before the start. Checked: JSON round trip of the real memory equal on sim weeks m-1, h-2; practice path unchanged (sim 158 weeks difference 0, server fe-2 15,472.82 to the cent). NOT tested: a real restart on the live clock (no test final left to try it on). Also: pairLate / urgLate / feeLate 0.93, 0.97 on BEST13 in the sim all flat (-41 to +29 ± 28), no server weeks played
2026-11-14T22:15Z juuso NOTE best13 session mistake, fixed (14 Nov 23:15 to 23:20 Helsinki): copied kit-b13 algo.ts + core/cost.ts over kit-best without seeing that another session had made kit-best BEST13 (feeLate=0.95) at 22:48. Restored within 5 minutes: kit-best/algo.ts = runs/lab/kit-best_algo_BEST13_backup.ts = kit-final/algo.ts (cmp equal), core/cost.ts back (cmp equal to kit-final). Any week started from kit-best between 23:15 and 23:20 played BEST12 + pLane 0.06 without feeLate: rows 'replay13' of that time are suspect. Lost: the original runs/lab/kit-best_algo_BEST12_backup.ts was overwritten; it is now the BEST13 file with feeLate=1 (plays BEST12). My lane file: runs/lab/kit-b13_algo_lane_on_BEST12.ts. kit-final was not touched
2026-11-14T22:17Z juuso OPEN fee_far status=open
2026-11-14T22:18Z juuso RECALL weekend hits=1
2026-11-14T22:19Z juuso RECALL snow hits=2
2026-11-14T22:19Z juuso RECALL forecast hits=5
2026-11-14T22:19Z juuso RECALL costUp hits=3
2026-11-14T22:19Z juuso RECALL same-day hits=20
2026-11-14T22:19Z juuso RECALL optSame hits=1
2026-11-14T22:19Z juuso RECALL same_day hits=0
2026-11-14T22:19Z juuso RECALL typical / list hits=1
2026-11-14T22:19Z juuso RECALL competitor+typical hits=1
2026-11-14T22:20Z juuso LOG juhus_gap status=fact
2026-11-14T22:20Z juuso NOTE juhus_gap second session: study only, scripts research/juhus_gap/s2_*.py, KNOWLEDGE + BACKLOG rows added; no kit touched, no game weeks
2026-11-14T22:20Z juuso RECALL controller hits=4
2026-11-14T22:20Z juuso RECALL booking+speed hits=5
2026-11-14T22:20Z juuso RECALL driver-side hits=2
2026-11-14T22:20Z juuso RECALL hazard+scale hits=2
2026-11-14T22:20Z juuso RECALL online hits=2
2026-11-14T22:20Z juuso RECALL week+level hits=47
2026-11-14T22:20Z juuso RECALL adapt hits=0
2026-11-14T22:27Z juuso LOG best13 status=ship-candidate
2026-11-14T22:27Z juuso LOG drv_learn status=no-edge
2026-11-14T22:29Z juuso OPEN roll_price status=open
2026-11-14T22:48Z juuso CLOSE fee_far status=no-edge
2026-11-14T22:51Z juuso NOTE BEST14 shipped on the user's instruction (14 Nov 23:55 Helsinki, before the 4-week replay check of the lazy lane states finished): kit-best/algo.ts = current BEST13 (feeLate=0.95) + pLane=0.06 (lane level of the week in the price filter, states added when a lane is first asked). BEST13 again: --set pLane=0; old file runs/lab/kit-best_algo_BEST13_backup.ts; copy of the new file runs/lab/kit-best_algo_BEST14.ts. kit-final NOT changed (still BEST13). Test kits kit-b13 (on BEST12), kit-b14 (on BEST13)
2026-11-14T22:56Z juuso CLOSE best13 status=shipped
2026-11-14T22:56Z juuso LOG ranking status=fact
2026-11-14T22:57Z juuso OPEN best14 status=open
2026-11-14T22:57Z juuso LOG best13 status=no-edge
2026-11-14T22:58Z juuso RECALL bookScale hits=0
2026-11-14T23:01Z juuso CLOSE best14 status=parked
2026-11-14T23:02Z juuso NOTE kit-final/algo.ts = BEST14 since 00:50 Helsinki 15 Nov (kit-b14 algo with pLane 0.06 as default; equal to kit-best BEST14 except one comment line; BEST13 backup runs/lab/kit-final_algo_BEST13_backup_0050.ts). Playing the 01:00 test final world fae00be02107709bff83f on SPREAD_KEY = Team Anonymous, runner restarted 00:50:58 before the start. runs/ was moved to junction-2026/runs at 00:57 while the runner was live: leaderboard feed lost 00:57 to 01:02; link Bahn-Spread/runs/testfinal_1115_0100 -> ../../runs/testfinal_1115_0100 added so the recorder and the data pull after the end find the folder
2026-11-14T23:38Z juuso RECALL stop+window hits=5
2026-11-14T23:38Z juuso RECALL buffer hits=0
2026-11-14T23:38Z juuso RECALL delivery+window hits=1
2026-11-14T23:38Z juuso RECALL safety+margin hits=1
2026-11-14T23:38Z juuso RECALL evening hits=4
2026-11-14T23:39Z juuso OPEN on_time status=open
2026-11-14T23:40Z juuso LOG book_shift status=ship-candidate
2026-11-14T23:47Z juuso RECALL live hits=76
2026-11-14T23:50Z juuso LOG testfinal status=fact
2026-11-14T23:51Z juuso RECALL dueCapPer hits=22
2026-11-14T23:51Z juuso RECALL minBookChance hits=11
2026-11-14T23:52Z juuso RECALL openTilt hits=14
2026-11-14T23:52Z juuso OPEN final_safety status=open
2026-11-14T23:52Z juuso RECALL long+drive hits=1
2026-11-14T23:52Z juuso RECALL longUp hits=0
2026-11-14T23:52Z juuso RECALL openTilt+0 hits=16
2026-11-14T23:52Z juuso RECALL dueCapPer hits=25
2026-11-14T23:53Z juuso NOTE kit-safe = copy of kit-best BEST14 + longUp / longH (price rise for drives of longH hours or more, default off): on-time safety screen os1
2026-11-14T23:53Z juuso NOTE kit-safe: at 01:53 Helsinki a second session replaced the folder (rm + copy of kit-best BEST14) seconds after final_safety created it; 24 weeks of the first sf1 sweep died with 'current working directory was deleted'. The folder now = kit-best BEST14 + longUp / longH (price rise for drives of longH hours or more, default off, so every sf1 variant plays as planned). Added to sf1 on the same seeds sf-1..32: long10 (longUp 0.1), long20 (0.2), long10t0 (longUp 0.1 + openTilt 0). Do not recreate kit-safe
2026-11-14T23:55Z juuso CLOSE on_time status=no-edge
2026-11-15T00:00Z juuso NOTE FINAL armed: systemd user timers junction-final (05:30 CET = 06:30 Helsinki, Restart=on-failure) and safety starts junction-final-b..e (07:25, 07:58, 08:28, 08:58 Helsinki; a second copy exits at once on the lock) run Bahn-Spread/final_1115/go.sh = kit-final (BEST14) with --final on SPREAD_KEY = Team Anonymous; state, recorder, feed and the data pull stay in final_1115/. Stop: systemctl --user stop 'junction-final*'. A model change in kit-final/algo.ts before 06:30 Helsinki is picked up by itself; after that: systemctl --user restart junction-final (before 07:30)
2026-11-15T00:03Z juuso RECALL dueCapPer hits=25
2026-11-15T00:03Z juuso RECALL surcharge hits=0
2026-11-15T00:03Z juuso NOTE Quick server screen started 15 Nov 02:05 Helsinki on the user's request: dueCapPer=0.18 + fullPrice=1 ('surcharge' read as fullPrice) on BEST14 from kit-best, seeds sf-1..16, tag sf1 labels d18f1, d18, f1; base = the sf1 base rows of final_safety (same seeds)
2026-11-15T00:04Z juuso NOTE Added to the quick sf1 screen (user's request, 15 Nov): d11 = dueCapPer=0.11 on BEST14, seeds sf-1..16, played on SPREAD_KEY_OFFICIAL only (KEYS=)
2026-11-15T00:10Z juuso NOTE kit-flu14/ = copy of kit-best BEST14 (15 Nov 02:20 Helsinki) + the flu knobs of kit-flu (fluN, fluSame, default off; 4 edits in algo.ts, engine untouched). Its week.ts writes kit 'kit-best' into bench.jsonl. Server screen on the user's request: sf-1..32 same weeks as the sf1 base, tag sf1 labels flu15 (fluN=6,fluSame=0.15) and fluoff (sf-1 only, identity check against the sf1 base row)
2026-11-15T00:11Z juuso LOG book_shift status=inconclusive
2026-11-15T00:16Z juuso LOG long_price status=no-edge
2026-11-15T00:24Z juuso LOG flu14 status=no-edge
2026-11-15T00:28Z juuso LOG best15 status=shipped
2026-11-15T00:29Z juuso NOTE BEST15 shipped 02:20 Helsinki: openTilt=0 default in kit-best and kit-final (replay sf-1 17,590.33 both); kit-safe unchanged (BEST14 defaults); backups runs/lab/kit-best_algo_BEST14_backup.ts and kit-final_algo_BEST14_backup_0220.ts
2026-11-15T00:30Z juuso NOTE sf1 d11 / d18 rows suspect: kit-best became BEST15 (openTilt=0) at 02:20:15 Helsinki while replays of 502-killed weeks were still starting from kit-best. Rows finished after 00:20Z (d11 sf-2, 8, 13, 16; d18 sf-16) may have played openTilt=0. Replayed from kit-flu14 (BEST14 pinned, flu off = BEST14 to the cent) under the same labels: later row wins in cmp.py
2026-11-15T00:32Z juuso NOTE Seekers level 8 ranking round scheduled on the user's request (15 Nov): systemd user timer junction-seekers-0305 fires 03:02 Helsinki, runs/board/play_best15_seekers_round.sh takes slot SPREAD_KEY_2-4, starts 03:05:00, 5 runs with BEST15 (runs/board/kit-best15-snap = kit-best at 02:35 Helsinki, openTilt=0). Output runs/board/play_best15_seekers_round.out. Cancel: systemctl --user stop junction-seekers-0305.timer
2026-11-15T00:32Z juuso LOG book_shift status=ship-candidate
2026-11-15T00:32Z juuso LOG day_cap status=no-edge
2026-11-15T00:33Z juuso CLOSE final_safety status=ship-candidate
2026-11-15T00:43Z juuso LOG book_shift status=no-edge
2026-11-15T00:48Z juuso LOG book_shift status=inconclusive
2026-11-15T00:49Z juuso OPEN wide15 status=open
2026-11-15T01:39Z juuso CLOSE wide15 status=no-edge
2026-11-15T01:40Z juuso RECALL maxList hits=0
2026-11-15T01:40Z juuso RECALL long haul hits=0
2026-11-15T01:40Z juuso OPEN decline_long status=open
2026-11-15T01:56Z juuso CLOSE decline_long status=no-edge
2026-11-15T02:07Z juuso LOG decline_long status=no-edge
2026-11-15T02:24Z juuso LOG book_shift status=ship-candidate
2026-11-15T02:36Z juuso LOG book_shift status=ship-candidate
2026-11-15T02:37Z juuso NOTE kit-b16/ = copy of kit-best BEST15 (15 Nov 04:45 Helsinki) + the fee-only booking shift (core/model.ts two lines; algo.ts: bookShift 0.2, bookQuote 0, one plan() call in quote()). BEST16 candidate, ready to copy into kit-best / kit-final on the user's word. Replay from kit-b16 on the server: wf-1 13,227.55 and wf-2 17,951.59 = the tested kit-out f20 rows to the cent; --set bookShift=0 on wf-1 = BEST15 12,690.11; --set bookShift=0.15 on wf-2 = 18,220.37 = the f15 row. kit-best and kit-final not touched
2026-11-15T03:01Z juuso LOG wide15 status=no-edge
2026-11-15T03:14Z juuso LOG book_shift status=ship-candidate
2026-11-15T03:34Z juuso LOG book_shift status=no-edge
2026-11-15T04:07Z juuso LOG wide15 status=ship-candidate
2026-11-15T04:07Z juuso NOTE kit-b17/ = kit-b16 (BEST15 + fee-only booking shift 0.2) + steps 4, rampTop 1.45, costW 1.25, hardChance 0.82: BEST17 candidate, replayed to the cent on wl-1, wl-2 (15 Nov 06:10 Helsinki). kit-best and kit-final untouched (BEST15, final armed)
2026-11-15T04:34Z juuso LOG wide15 status=no-edge
2026-11-15T05:02Z juuso LOG wide15 status=no-edge
2026-11-15T05:09Z juuso LOG wide15 status=ship-candidate
2026-11-15T06:10Z juuso RECALL b17 hits=5
2026-11-15T06:10Z juuso RECALL best16 hits=1
2026-11-15T06:11Z juuso OPEN best16 status=open
2026-11-15T06:16Z juuso CLOSE best16 status=ship-candidate
2026-11-15T06:16Z juuso NOTE kit-b18/ = copy of kit-b17 + pairKm 40, pairHoldH 3 as defaults = all three steps on BEST15 (BEST16 candidate of the best16 row). Replay on the server: wp-1 13,284.40 and wp-2 19,623.06 = the tested wp1 all rows to the cent. kit-best and kit-final not touched
2026-11-15T06:19Z juuso RECALL minProfit hits=2
2026-11-15T06:19Z juuso RECALL capConst hits=2
2026-11-15T06:19Z juuso RECALL pairBack hits=2
2026-11-15T06:19Z juuso RECALL costUp hits=6
2026-11-15T06:19Z juuso RECALL pairKm=50 hits=0
2026-11-15T06:19Z juuso RECALL minSlackH hits=4
2026-11-15T06:19Z juuso RECALL pDay hits=5
2026-11-15T06:19Z juuso RECALL outageK hits=24
2026-11-15T06:19Z juuso OPEN push20k status=open
2026-11-15T06:20Z juuso LOG best16 status=shipped
2026-11-15T06:20Z juuso LOG ranking status=fact
2026-11-15T06:34Z juuso CLOSE push20k status=no-edge
