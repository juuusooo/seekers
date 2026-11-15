/** Plays ONE practice week and prints one JSON line (for optimisers that call it week by week).
 *
 *   bun core/week.ts --seed o-1 [--set capLam=5] [--variant name] [--journal folder]
 *
 * Appends the same row to ../runs/bench.jsonl. Practice only. If stopped, it deletes its world to free the slot.
 */
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"
import { parseArgs } from "node:util"
import { Client } from "./spread.ts"
import { loadAlgo, parseSet, play } from "./engine.ts"

const { values: args } = parseArgs({
  options: {
    level: { type: "string", default: "8" },
    seed: { type: "string" },
    algo: { type: "string", default: new URL("../algo.ts", import.meta.url).pathname },
    set: { type: "string" },
    variant: { type: "string" },
    at: { type: "string" },
    journal: { type: "string" }, // a folder: write the week's journal there (for learn/fit.py)
  },
})
if (!args.seed) throw new Error("--seed is required")
const level = Number(args.level)
const algo = await loadAlgo(args.algo)
const overrides = parseSet(args.set)
const client = new Client()
let id = ""
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.once(signal, async () => {
    if (id) await client.world(id).delete().catch(() => {})
    process.exit(130)
  })
}
const r = await play(client, level, algo, overrides, { seed: args.seed, onWorld: (w) => (id = w) })
const row = {
  at: args.at ?? new Date().toISOString(),
  kit: "kit-best",
  level,
  variant: args.variant ?? args.algo!.replace(/\.ts$/, "").replace(/^algos\//, ""),
  seed: args.seed,
  worldId: r.worldId,
  margin: r.score.marginCents / 100,
  onTime: r.score.onTimeShare,
  won: r.score.wonOrders,
  ranked: r.score.ranked,
  declined: r.stats.declined,
  why: r.stats.why,
  overrides,
}
if (args.journal) {
  mkdirSync(args.journal, { recursive: true })
  writeFileSync(`${args.journal}/${r.worldId}.jsonl`, [{ k: "week", worldId: r.worldId, seed: args.seed, level, algo: args.algo, margin: row.margin, onTime: row.onTime, won: row.won, params: r.params }, ...r.journal].map((line) => JSON.stringify(line)).join("\n") + "\n")
}
const RUNS = new URL("../../runs/", import.meta.url).pathname // Bahn-Spread/runs
mkdirSync(RUNS, { recursive: true })
appendFileSync(RUNS + "bench.jsonl", JSON.stringify(row) + "\n")
console.log(JSON.stringify(row))
