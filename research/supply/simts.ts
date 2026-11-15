/** The local world (sim/, TypeScript) with any kit, on Node and on Windows: the same loop as sim/run.ts.
 *   node research/supply/simts.ts --kit kit-s14 --seeds m-1..8 --variants FILE --out FILE [--sim k=v,..]
 * Variants file: one "label k=v,k=v" per line. One JSON row per week and variant is appended to --out.
 * Use simts.py to spread seeds over processes. The Rust copy (simrs) is 40 times faster but plays BEST10 only.
 */
import { appendFileSync, existsSync, readFileSync } from "node:fs"
import { parseArgs } from "node:util"
import { fileURLToPath, pathToFileURL } from "node:url"
import { dirname, resolve } from "node:path"

const { values: a } = parseArgs({ options: { kit: { type: "string", default: "kit-s14" }, seeds: { type: "string" }, variants: { type: "string" }, out: { type: "string" }, sim: { type: "string" }, world: { type: "string", default: "sim/opt/world.ts" } } })
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..")
const imp = (f: string) => import(pathToFileURL(resolve(root, f)).href)
const { SimWorld } = await imp(a.world!)
const { paramsFor, parseSet, playPractice } = await imp(`${a.kit}/core/engine.ts`)
const algo = await imp(`${a.kit}/algo.ts`)
const seeds: string[] = []
for (const s of a.seeds!.split(",")) { const m = s.match(/^(.*)-(\d+)\.\.(\d+)$/); if (m) for (let i = +m[2]!; i <= +m[3]!; i++) seeds.push(`${m[1]}-${i}`); else if (s) seeds.push(s) }
const variants = readFileSync(a.variants!, "utf8").split(/\r?\n/).filter((l) => l.trim()).map((l) => { const [label, set] = l.trim().split(/\s+/); return { label: label!, set: set ?? "" } })
const simP = parseSet(a.sim)
for (const seed of seeds) {
  const path = resolve(root, "sim", "data", seed + ".json")
  if (!existsSync(path)) continue
  const text = readFileSync(path, "utf8")
  const offs = resolve(root, "sim", "fit", seed + ".json")
  const fit = existsSync(offs) ? JSON.parse(readFileSync(offs, "utf8")) : {}
  for (const v of variants) {
    const data = Object.assign(JSON.parse(text), fit)   // the desk rewrites typical fees in place: a fresh copy per week
    const w = new SimWorld(data, simP)
    await playPractice(w as any, 8, algo, paramsFor(algo, parseSet(v.set)), true)
    w.close()
    const s = await w.score()
    appendFileSync(a.out!, JSON.stringify({ kit: a.kit, variant: v.label, seed, margin: s.marginCents / 100, onTime: s.onTimeShare, won: s.wonOrders, ranked: s.ranked, sim: simP, set: parseSet(v.set) }) + "\n")
  }
}
