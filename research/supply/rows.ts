/** Builds fit rows for the realized-cost trees from weeks played by server.ts (the same replay as
 * research/real_cost/build.ts, with kit-supply's cost.ts so the inputs are the ones the algorithm sees).
 *   node research/supply/rows.ts --tags su1[,ct1]        -> research/supply/out/rows_server.jsonl
 * Reads events, snapshot and driver list of each ended world (read-only). Key: SPREAD_KEY of the environment.
 * Raw answers are kept in out/worlds/ (gitignored), so a world is fetched once.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { gunzipSync, gzipSync } from "node:zlib"
import { parseArgs } from "node:util"
import { fileURLToPath, pathToFileURL } from "node:url"
import { dirname, resolve } from "node:path"

const { values: a } = parseArgs({ options: { tags: { type: "string" }, kit: { type: "string", default: "kit-supply" }, par: { type: "string", default: "4" } } })
const here = dirname(fileURLToPath(import.meta.url)), root = resolve(here, "..", ".."), kit = resolve(root, a.kit!)
const imp = (f: string) => import(pathToFileURL(resolve(kit, f)).href)
const { Client } = await imp("core/spread.ts")
const { PARAMS } = await imp("algo.ts")
const { costRow } = await imp("core/cost.ts")
const { gigX, loadModel, plan } = await imp("core/model.ts")
const { readNote } = await imp("core/notes.ts")
const MAP = JSON.parse(readFileSync(resolve(root, "raw", "map.json"), "utf8"))
const TYP = JSON.parse(readFileSync(resolve(kit, "core", "data", "typ.json"), "utf8"))
const MODEL = loadModel()!
const MIN = new Map<string, number>(MAP.roads.map((r: any) => [`${r.from}>${r.to}`, r.minutes]))
const PLACE = new Map<string, any>(MAP.places.map((p: any) => [p.id, p]))
const KM = new Map<string, number>()
const km = (x: string, y: string) => {
  const key = x + ">" + y
  let v = KM.get(key)
  if (v === undefined) {
    const p = PLACE.get(x), q = PLACE.get(y), r = Math.PI / 180
    if (!p || !q) v = Infinity
    else { const h = Math.sin(((q.lat - p.lat) * r) / 2) ** 2 + Math.cos(p.lat * r) * Math.cos(q.lat * r) * Math.sin(((q.lon - p.lon) * r) / 2) ** 2; v = 2 * 6371 * Math.asin(Math.sqrt(h)) }
    KM.set(key, v)
  }
  return v
}
function denoise(request: any): void {
  let pred = 0
  for (const leg of request.legs) {
    const key = `${leg.pickup.placeId}>${leg.delivery.placeId}`
    if ((TYP.n[key] ?? 0) < PARAMS.typMinN) return
    pred += Math.exp(TYP.lane[key] + TYP.privP * +leg.pickup.privateAddress + TYP.privD * +leg.delivery.privateAddress + TYP.prem * +leg.car.premium + TYP.elec * +leg.car.electric)
  }
  if (request.legs.length > 1) pred *= Math.exp(TYP.trade)
  request.typRaw = request.referenceFeeCents
  request.referenceFeeCents = Math.round(pred)
}
const DAY = 1440
const cache = resolve(here, "out", "worlds"); mkdirSync(cache, { recursive: true })
const client = new Client()
async function fetchWorld(id: string): Promise<{ events: any[]; snap: any; drivers: any[] }> {
  const file = resolve(cache, id + ".json.gz")
  if (existsSync(file)) return JSON.parse(gunzipSync(readFileSync(file)).toString())
  const w = client.world(id)
  const data = { events: await w.events(-1), snap: await w.snapshot(), drivers: await w.roster() }
  writeFileSync(file, gzipSync(JSON.stringify(data)))
  return data
}
function build(b: any, events: any[], snap: any, drivers: any[]): string[] {
  const out: string[] = []
  const gigOrders = new Map<string, string[]>()
  for (const g of snap.gigs) gigOrders.set(g.id, g.stops.filter((s: any) => s.kind === "pickup").map((s: any) => s.orderId))
  const near = new Map<string, number>()
  const orders = new Map<string, any>(), dealers = new Map<string, { trust: number; lates: number }>()
  const ctx: any = {
    now: 0, level: 8, places: MAP.places, drivers, orders, memory: {},
    drive: (x: string, c: string) => MIN.get(`${x}>${c}`) ?? 0, km,
    driversNear(place: string, radius = 30) { const key = place + "|" + radius; let n = near.get(key); if (n === undefined) { n = 0; for (const d of drivers) if (km(place, d.homePlaceId) <= radius) n++; near.set(key, n) } return n },
    openFrom(place: string) { let n = 0; for (const o of orders.values()) if (o.legs[0].pickup.placeId === place && o.deliveredAt.some((at: any) => at === null)) n++; return n },
    dealer: (id: string) => dealers.get(id) ?? { trust: 0, lates: 0 },
  }
  const rows = new Map<string, Record<string, number[]>>(), reqs = new Map<string, any>()
  const won = new Map<string, any>(), net = new Map<string, number>(), paid = new Map<string, number>(), cancelled = new Set<string>()
  for (const e of events) {
    ctx.now = e.at
    if (e.kind === "price_request") {
      const req = e.request
      denoise(req)
      reqs.set(req.id, req)
      const note = readNote(req.note?.text, req.arrivedAt)
      const stated = Math.max(req.arrivedAt, ...req.legs.map((l: any) => l.pickup.window.from))
      const moved = (deadline: number) => { let days = Math.max(0, Math.floor((note.readyFrom ?? 0) / DAY) - Math.floor(stated / DAY)), day = Math.floor(deadline / DAY); while (days > 0) { day++; if (day % 7 < 5) days-- } return day * DAY + (deadline % DAY) }
      const drive = req.legs.reduce((s: number, l: any) => s + ctx.drive(l.pickup.placeId, l.delivery.placeId), 0)
      const ready = Math.max(stated, note.readyFrom ?? 0), gig = gigX(ctx, req.legs, req.referenceFeeCents, false)
      const byOpt: Record<string, number[]> = {}
      for (const o of req.options) {
        const due = note.deliverBy !== null ? Math.min(moved(o.deadline), note.deliverBy) : moved(o.deadline)
        if (due - drive - ctx.now < 0) continue
        const pl = plan(MODEL, gig, { now: ctx.now, typical: req.referenceFeeCents, lastPickupAt: due - drive, readyAt: ready }, PARAMS)
        byOpt[o.kind] = costRow(ctx, req, { due, ready, drive, kind: o.kind, plan: pl, noteReady: note.readyFrom !== null, noteBy: note.deliverBy !== null })
      }
      rows.set(req.id, byOpt)
    } else if (e.kind === "order_won") { orders.set(e.order.id, e.order); won.set(e.order.id, { price: e.order.priceCents, option: e.order.option, at: e.at }) }
    else if (e.kind === "order_changed") { if (orders.has(e.order.id)) orders.set(e.order.id, e.order) }
    else if (e.kind === "order_cancelled") { orders.delete(e.orderId); cancelled.add(e.orderId) }
    else if (e.kind === "delivered") {
      const o = orders.get(e.orderId)
      if (o) {
        o.deliveredAt[e.leg] = e.at
        if (o.deliveredAt.every((t: any) => t !== null)) {
          const d = ctx.dealer(o.dealerId), late = Math.max(...o.deliveredAt) > o.deadline
          dealers.set(o.dealerId, late ? { trust: Math.floor(d.trust / 2), lates: d.lates + 1 } : { trust: Math.min(25, d.trust + 1), lates: d.lates })
          won.get(o.id).late = +late
        }
      }
    } else if (e.kind === "ledger") {
      const l = e.line
      const ids: string[] = l.orderId && l.kind !== "driver_fee" ? [l.orderId] : (l.gigId && gigOrders.get(l.gigId)) || (l.orderId ? [l.orderId] : [])
      for (const id of ids) {
        net.set(id, (net.get(id) ?? 0) + l.cents / ids.length)
        if (l.kind === "driver_fee") paid.set(id, (paid.get(id) ?? 0) - l.cents / ids.length)
      }
    }
  }
  for (const [id, w] of won) {
    if (cancelled.has(id)) continue
    const x = rows.get(id)?.[w.option], req = reqs.get(id)
    if (!x || !req) continue
    const typ = req.referenceFeeCents
    out.push(JSON.stringify({ world: b.worldId, seed: b.seed, variant: b.variant, y: (w.price - (net.get(id) ?? 0)) / typ, paid: (paid.get(id) ?? 0) / typ, late: w.late ?? -1, typ, price: w.price, x }))
  }
  return out
}
const played: any[] = []
for (const tag of a.tags!.split(",")) for (const l of readFileSync(resolve(here, "server", tag + ".jsonl"), "utf8").split("\n").filter(Boolean)) played.push(JSON.parse(l))
const all: string[] = []
let next = 0, failed = 0
async function worker() {
  while (next < played.length) {
    const b = played[next++]
    try { const d = await fetchWorld(b.worldId); all.push(...build(b, d.events, d.snap, d.drivers)) } catch (error) { failed++; console.error(b.worldId, String((error as Error)?.message ?? error).slice(0, 160)) }
  }
}
await Promise.all(Array.from({ length: Number(a.par) }, worker))
writeFileSync(resolve(here, "out", "rows_server.jsonl"), all.join("\n") + "\n")
console.log(`worlds ${played.length - failed} (${failed} failed), rows ${all.length}`)
