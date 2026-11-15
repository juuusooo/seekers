/** Plays practice weeks of kit-supply on the server: every variant on the same seeds, a few worlds at a time.
 *   node research/supply/server.ts --seeds su-1..48 --tag su1 --variants research/supply/variants/server1.txt [--par 6] [--kit kit-supply]
 * Variants file: one "label k=v,k=v" per line ("label" alone = the kit as it is). Practice only: never a ranking run.
 * Rows: research/supply/server/<tag>.jsonl (a finished seed + label is not played again). Key: SPREAD_KEY of the environment.
 * --dry loads the kit and lists the weeks without contacting the server.
 */
import { appendFileSync, copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs"
import { parseArgs } from "node:util"
import { fileURLToPath, pathToFileURL } from "node:url"
import { dirname, resolve } from "node:path"

const { values: a } = parseArgs({ options: { seeds: { type: "string" }, tag: { type: "string" }, variants: { type: "string" }, par: { type: "string", default: "6" }, kit: { type: "string", default: "kit-supply" }, dry: { type: "boolean" } } })
const here = dirname(fileURLToPath(import.meta.url))
const kit = resolve(here, "..", "..", a.kit!)
const { Client } = await import(pathToFileURL(resolve(kit, "core", "spread.ts")).href)
const { parseSet, paramsFor, play } = await import(pathToFileURL(resolve(kit, "core", "engine.ts")).href)
const algo = await import(pathToFileURL(resolve(kit, "algo.ts")).href)
const seeds: string[] = []
for (const s of a.seeds!.split(",")) { const m = s.match(/^(.*)-(\d+)\.\.(\d+)$/); if (m) for (let i = +m[2]!; i <= +m[3]!; i++) seeds.push(`${m[1]}-${i}`); else seeds.push(s) }
const variants = readFileSync(a.variants!, "utf8").split(/\r?\n/).filter((l) => l.trim()).map((l) => { const [label, set] = l.trim().split(/\s+/); return { label: label!, set: set ?? "" } })
for (const v of variants) paramsFor(algo, parseSet(v.set)) // unknown knob names stop the run here
// rows are written to out/server/ (gitignored) while the run goes, and copied to server/ (tracked) when it ends:
// a tracked file that grows every few seconds makes the team auto-sync fail its rebase
const dir = resolve(here, "out", "server"); mkdirSync(dir, { recursive: true }); mkdirSync(resolve(here, "server"), { recursive: true })
const out = resolve(dir, a.tag + ".jsonl")
if (!existsSync(out) && existsSync(resolve(here, "server", a.tag + ".jsonl"))) copyFileSync(resolve(here, "server", a.tag + ".jsonl"), out)
const done = new Set<string>()
if (existsSync(out)) for (const l of readFileSync(out, "utf8").split("\n").filter(Boolean)) { const r = JSON.parse(l); done.add(r.seed + "|" + r.variant) }
const jobs = seeds.flatMap((seed) => variants.map((v) => ({ seed, ...v }))).filter((j) => !done.has(j.seed + "|" + j.label))
console.log(`${jobs.length} weeks to play (${done.size} done), ${a.par} at a time, kit ${a.kit}`)
if (a.dry) process.exit(0)
const client = new Client()
let next = 0, failed = 0
async function worker() {
  while (next < jobs.length) {
    if (existsSync(resolve(dir, a.tag + ".stop"))) return // touch out/server/<tag>.stop: weeks in play finish, no new one starts
    const job = jobs[next++]!
    for (let attempt = 1; ; attempt++) {
      try {
        const t0 = Date.now()
        const r = await play(client, 8, algo, parseSet(job.set), { seed: job.seed })
        const row = { at: new Date().toISOString(), kit: a.kit, tag: a.tag, variant: job.label, seed: job.seed, worldId: r.worldId, margin: r.score.marginCents / 100, onTime: r.score.onTimeShare, won: r.score.wonOrders, ranked: r.score.ranked, declined: r.stats.declined, set: parseSet(job.set), s: Math.round((Date.now() - t0) / 1000) }
        appendFileSync(out, JSON.stringify(row) + "\n")
        console.log(`${job.seed} ${job.label} margin ${Math.round(row.margin)} orders ${row.won} on time ${(100 * row.onTime).toFixed(1)}% ${row.s}s`)
        break
      } catch (error) {
        console.error(`${job.seed} ${job.label} attempt ${attempt}: ${String((error as Error)?.message ?? error).slice(0, 200)}`)
        if (attempt >= 3) { failed++; break }
        await new Promise((r) => setTimeout(r, 5000))
      }
    }
  }
}
await Promise.all(Array.from({ length: Number(a.par) }, worker))
if (existsSync(out)) copyFileSync(out, resolve(here, "server", a.tag + ".jsonl"))
console.log(`done ${a.tag}${failed ? `, ${failed} weeks failed` : ""}`)
