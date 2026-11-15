/** Requests (1 world per seed) from all level 8 practice worlds in bench.jsonl, excluding seed prefixes given.
 *   bun an/harvest_req.ts EXCLUDE_PREFIXES(comma) > ../runs/km/harvest_req.jsonl */
import { readFileSync } from "node:fs"
import { Client } from "../spread.ts"
const clients = ["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"].map((n) => new Client({ key: process.env[n] }))
const excl = (process.argv[2] ?? "").split(",").filter(Boolean)
const bySeed = new Map<string, string>()
for (const l of readFileSync(new URL("../../../runs/bench.jsonl", import.meta.url).pathname, "utf8").split("\n")) {
  if (!l) continue
  let r: any; try { r = JSON.parse(l) } catch { continue }
  if (r.level !== 8 || !r.seed || !r.worldId || excl.some((p: string) => r.seed.startsWith(p))) continue
  if (!bySeed.has(r.seed)) bySeed.set(r.seed, r.worldId)
}
console.error("seeds", bySeed.size)
const todo = [...bySeed]
async function one([seed, id]: [string, string]) {
  for (const c of clients) {
    try {
      let after = -1
      for (;;) {
        const page: any[] = await c.world(id).events(after, 5000)
        for (const e of page) if (e.kind === "price_request") {
          const r = e.request
          console.log(JSON.stringify({ seed, at: e.at, id: r.id, d: r.dealerId, typ: r.referenceFeeCents, legs: r.legs.map((l: any) => [l.pickup.placeId, l.delivery.placeId, l.pickup.privateAddress ? 1 : 0, l.delivery.privateAddress ? 1 : 0, l.car?.premium ? 1 : 0, l.car?.electric ? 1 : 0]), opts: r.options.map((o: any) => [o.kind, o.listPriceCents, o.deadline]) }))
        }
        if (page.length < 5000) return
        after = page.at(-1).seq
      }
    } catch {}
  }
}
const N = 6
await Promise.all(Array.from({ length: N }, async (_, k) => { for (let i = k; i < todo.length; i += N) await one(todo[i]!) }))
