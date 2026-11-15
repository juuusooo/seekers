/** Plays one week with the best model (algo.ts, its PARAMS are the best values).
 *
 *   bun core/run.ts --seed spread-1                 practice week, level 8 (prints every day)
 *   bun core/run.ts --seed spread-1 --set capLam=5  the same with one value changed
 *   bun core/run.ts --board                         a RANKING run (counts on the leaderboard; needs SPREAD_KEY_OFFICIAL)
 *   bun core/run.ts --final                         the final or a test final (live stream; needs SPREAD_KEY_OFFICIAL)
 * Run from system/. Practice uses SPREAD_KEY. Load keys first: set -a && source ../.env && set +a
 */
import { parseArgs } from "node:util"
import { Client, SpreadError, Unreachable, type World } from "./spread.ts"
import { rec } from "./rec.ts"
import { loadAlgo, nextFinal, paramsFor, parseSet, play, playFinal, playPractice, report } from "./engine.ts"

const { values: args } = parseArgs({
  options: {
    level: { type: "string", default: "8" },
    seed: { type: "string" },
    board: { type: "boolean" },
    final: { type: "boolean" },
    algo: { type: "string", default: new URL("../algo.ts", import.meta.url).pathname },
    set: { type: "string" },
  },
})

function exit(message: string): never {
  console.error(message)
  process.exit(1)
}

try {
  const level = Number(args.level)
  if (![1, 2, 3, 4, 5, 6, 7, 8].includes(level)) throw new SpreadError(0, "--level must be 1 to 8")
  const algo = await loadAlgo(args.algo)
  const overrides = parseSet(args.set)
  // Ranking runs and the final count: they are played with the official team's key, and only with it.
  const official = Boolean(args.board || args.final)
  if (official && !process.env.SPREAD_KEY_OFFICIAL) exit("A ranking run or the final needs SPREAD_KEY_OFFICIAL. It is not set, so nothing was played.")
  const client = new Client(official ? { key: process.env.SPREAD_KEY_OFFICIAL } : {})
  if (official) console.log(`Official team: ${((await (client as any).call("GET", "/v1/team")) as { team: { name: string } }).team.name}`)

  if (args.final) {
    let world: World | undefined
    process.once("SIGINT", () => exit("Stopped. The final keeps running without your system; start it again with --final."))
    // A server restart drops every connection: rebuild from the server and go on.
    while (true) {
      try {
        world ??= await nextFinal(client)
        console.log(`Final world ${world.id}, algorithm ${args.algo}.`)
        await playFinal(world, algo, overrides)
        break
      } catch (error) {
        if (!(error instanceof Unreachable)) throw error
        console.error(`spread: ${error.message}. Trying again in 5 seconds.`)
        rec({ k: "break", error: error.message })
        await new Promise((done) => setTimeout(done, 5000))
      }
    }
    const score = await world!.score()
    report("End", score)
    rec({ k: "score", world: world!.id, score })
  } else {
    console.log(`Algorithm ${args.algo}, level ${level}, params ${JSON.stringify(paramsFor(algo, overrides))}`)
    const kind = args.board ? "Ranking run" : "Practice world"
    let id = ""
    process.once("SIGINT", () => exit(`Stopped. ${kind} ${id} ${args.board ? "plays to its end without your system, and counts" : "is left unfinished; delete it to free its slot"}.`))
    const r = await play(client, level, algo, overrides, { seed: args.seed, board: args.board, quiet: false, onWorld: (w) => console.log(`${kind} ${(id = w)}`) })
    report("End", r.score)
    console.log(r.score.ranked ? "Ranked." : r.score.wonOrders === 0 ? "Not ranked: no order won." : "Not ranked: under 90% on time.")
    console.log(`Quoted ${r.stats.quoted}, declined ${r.stats.declined}: ${JSON.stringify(r.stats.why)}`)
  }
} catch (error) {
  if (error instanceof SpreadError) exit(`spread: ${error.message}`)
  throw error
}
void playPractice // re-exported for scripts that want the desk itself
