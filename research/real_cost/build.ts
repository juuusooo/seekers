// Builds the fit rows of the realized-cost model from ended server weeks (runs/events, read-only files).
//   bun research/real_cost/build.ts  → runs/rc/rows.jsonl   (one row per won, not cancelled order)
// Replays each week's events through a small copy of the desk's books, so every input is what the algorithm
// could read at quote time (kit-cost/core/cost.ts costRow, the same function the algorithm calls).
import { existsSync, readFileSync, writeFileSync } from "node:fs"
import { gunzipSync } from "node:zlib"
import { PARAMS } from "../../kit-cost/algo.ts"
import { costRow } from "../../kit-cost/core/cost.ts"
import { gigX, loadModel, plan } from "../../kit-cost/core/model.ts"
import { readNote } from "../../kit-cost/core/notes.ts"

const ROOT = new URL("../../", import.meta.url).pathname
const MAP = JSON.parse(readFileSync(ROOT + "raw/map.json", "utf8"))
const TYP = JSON.parse(readFileSync(ROOT + "kit-cost/core/data/typ.json", "utf8"))
const MODEL = loadModel()!
const MIN = new Map<string, number>(MAP.roads.map((r: any) => [`${r.from}>${r.to}`, r.minutes]))
const PLACE = new Map<string, any>(MAP.places.map((p: any) => [p.id, p]))
const KM = new Map<string, number>()
const km = (a: string, b: string) => {
  const key = a + ">" + b
  let v = KM.get(key)
  if (v === undefined) {
    const p = PLACE.get(a), q = PLACE.get(b), r = Math.PI / 180
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
const read = (id: string, what: string) => JSON.parse(gunzipSync(readFileSync(`${ROOT}runs/events/${id}.${what}.json.gz`)).toString())
const DAY = 1440

const keep = new Set(["sv1 fee", "sn1 best6", "sn1 notes", "b8 BEST8", "b8 BEST7", "i3 base", "i3 mon -.03 fri +.08", "i3 mon -.03", "i3 brake .93"])
const out: string[] = []
let worlds = 0
for (const line of readFileSync(ROOT + "runs/bench.jsonl", "utf8").split("\n")) {
  if (!line) continue
  const b = JSON.parse(line)
  if (!keep.has(b.variant) || !["events", "snapshot", "drivers"].every((w) => existsSync(`${ROOT}runs/events/${b.worldId}.${w}.json.gz`))) continue
  let events: any[], snap: any, drivers: any[]
  try { events = read(b.worldId, "events"); snap = read(b.worldId, "snapshot"); drivers = read(b.worldId, "drivers") } catch { continue }
  if (!Array.isArray(events)) events = (events as any).events
  if (!Array.isArray(drivers)) drivers = (drivers as any).drivers
  const gigOrders = new Map<string, string[]>()
  for (const g of snap.gigs) gigOrders.set(g.id, g.stops.filter((s: any) => s.kind === "pickup").map((s: any) => s.orderId))
  const near = new Map<string, number>()
  const orders = new Map<string, any>(), dealers = new Map<string, { trust: number; lates: number }>()
  const ctx: any = {
    now: 0, level: 8, places: MAP.places, drivers, orders, memory: {},
    drive: (a: string, c: string) => MIN.get(`${a}>${c}`) ?? 0, km,
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
      let ids: string[] = l.orderId && l.kind !== "driver_fee" ? [l.orderId] : (l.gigId && gigOrders.get(l.gigId)) || (l.orderId ? [l.orderId] : [])
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
    const typ = req.referenceFeeCents, list = req.options.find((o: any) => o.kind === w.option).listPriceCents
    out.push(JSON.stringify({ world: b.worldId, seed: b.seed, variant: b.variant, id, y: (w.price - (net.get(id) ?? 0)) / typ, paid: (paid.get(id) ?? 0) / typ, late: w.late ?? -1, m: w.price / list, typ, price: w.price, x }))
  }
  if (++worlds % 25 === 0) console.log("worlds", worlds, "rows", out.length)
}
writeFileSync(ROOT + "runs/rc/rows.jsonl", out.join("\n") + "\n")
console.log("done: worlds", worlds, "rows", out.length)
