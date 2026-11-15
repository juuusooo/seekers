/** RANKING RUNS (they count on the public practice rankings of the key's team and cannot be deleted or replayed).
 * Plays the next runs of the current ranking round at level 8 with a kit, one after the other.
 *   node research/supply/board.ts --yes --runs 5 [--kit kit-s14] [--set k=v,..]
 * Only on the user's explicit request, never from a test script. Key: SPREAD_KEY of the environment.
 * If the connection breaks mid-week, the same world is picked up again from the server (books rebuilt, the price
 * filter starts cold), because a ranking run that is left runs to its end without us and still counts.
 * Rows: research/supply/server/board.jsonl; world ids are written before the week starts.
 */
import { appendFileSync, mkdirSync } from "node:fs"
import { parseArgs } from "node:util"
import { fileURLToPath, pathToFileURL } from "node:url"
import { dirname, resolve } from "node:path"

const { values: a } = parseArgs({ options: { kit: { type: "string", default: "kit-s14" }, set: { type: "string" }, runs: { type: "string", default: "5" }, yes: { type: "boolean" }, label: { type: "string", default: "" } } })
if (!a.yes) { console.error("A ranking run counts on the leaderboard. Pass --yes to play."); process.exit(2) }
const here = dirname(fileURLToPath(import.meta.url)), kit = resolve(here, "..", "..", a.kit!)
const imp = (f: string) => import(pathToFileURL(resolve(kit, f)).href)
const { Client } = await imp("core/spread.ts")
const { Desk, DAY, paramsFor, parseSet } = await imp("core/engine.ts")
const algo = await imp("algo.ts")
const p = paramsFor(algo, parseSet(a.set))
const WAKE_ON = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close", "delivered", "gig_dropped", "no_show"]
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))
mkdirSync(resolve(here, "server"), { recursive: true })
const out = resolve(here, "server", "board.jsonl")
const client = new Client()

async function week(world: any): Promise<{ restarts: number }> {
  const [map, drivers] = await Promise.all([client.map(), world.roster()])
  let { now, endsAt } = await world.snapshot()
  let desk = new Desk(world, 8, now, algo, p, map, drivers)
  let restarts = 0
  while (desk.now < endsAt) {
    try {
      const day = Math.floor(desk.now / DAY)
      const actions = desk.outbox.splice(0)
      const step = await world.advance({ untilEvent: WAKE_ON, max: Math.min(endsAt, (day + 1) * DAY, Math.max(desk.now + 1, desk.nextTimer())), actions })
      desk.readResults(actions, step.results)
      desk.now = step.now
      for (const event of step.events) await desk.handle(event)
      await desk.fireTimers()
    } catch (error) {
      if (++restarts > 40) throw error
      console.error(`  connection or step error (${String((error as Error)?.message ?? error).slice(0, 120)}): picking the world up again, try ${restarts}`)
      for (;;) {
        try {
          await sleep(5000)
          const snapshot = await world.snapshot(), history = await world.events()
          desk = new Desk(world, 8, snapshot.now, algo, p, map, drivers)
          await desk.rejoin(snapshot, history)
          endsAt = snapshot.endsAt
          break
        } catch (again) { if (++restarts > 40) throw again }
      }
    }
  }
  return { restarts }
}

for (let i = 0; i < Number(a.runs); i++) {
  const world = await client.create(8, { board: true })
  appendFileSync(out, JSON.stringify({ at: new Date().toISOString(), event: "started", worldId: world.id, kit: a.kit, label: a.label, set: parseSet(a.set) }) + "\n")
  const t0 = Date.now()
  const { restarts } = await week(world)
  const s = await world.score()
  const row = { at: new Date().toISOString(), event: "played", worldId: world.id, kit: a.kit, label: a.label, set: parseSet(a.set), margin: s.marginCents / 100, onTime: s.onTimeShare, won: s.wonOrders, ranked: s.ranked, restarts, s: Math.round((Date.now() - t0) / 1000) }
  appendFileSync(out, JSON.stringify(row) + "\n")
  console.log(`ranking run ${i + 1}: margin ${Math.round(row.margin)} orders ${row.won} on time ${(100 * row.onTime).toFixed(1)}% ${row.ranked ? "ranked" : "NOT RANKED"} (${row.s}s, ${restarts} restarts)`)
}
console.log("done")
