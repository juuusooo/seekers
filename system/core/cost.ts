/**
 * cost.ts — the realized-cost model (research/real_cost). One row of inputs per request and delivery option, all
 * known when we quote. The SAME function builds the rows of the fit (research/real_cost/build.ts, from ended
 * server weeks) and the rows the algorithm asks about, so the two cannot drift apart.
 * The model (data/cost.json, gradient-boosted trees fitted by research/real_cost/fit.py) answers: what does an
 * order like this end up costing, as a multiple of its typical fee? Cost = price minus the order's final net:
 * driver fees with raises, late refunds, failed visits, fines, and the whole price of a car never delivered.
 */
import { existsSync, readFileSync } from "node:fs"
import type { Ctx, PriceRequest } from "./engine.ts"

const HOUR = 60, DAY = 24 * HOUR

export const COST_KEYS = ["driveH", "ln_typ", "raw_typ", "nearP", "nearD", "nearP80", "nearD80", "load", "open_all", "privP", "privD", "premium", "electric", "legs",
  "n_opt", "opt", "leftH", "waitH", "slackH", "hour", "weekday", "due_day", "due_load", "chain_in", "chain_out", "trust", "lates", "note_ready", "note_by",
  "plan_fee", "plan_chance", "plan_open", "plan_raise", "p_lat", "p_lon", "d_lat", "d_lon", "roster"] as const

export type CostIn = { due: number; ready: number; drive: number; kind: string; plan: { fee: number; chance: number; open: number; raise: number }; noteReady: boolean; noteBy: boolean }

export function costRow(ctx: Ctx, req: PriceRequest, o: CostIn): number[] {
  const first = req.legs[0]!, last = req.legs[req.legs.length - 1]!
  const pick = first.pickup.placeId, del = last.delivery.placeId
  const nearP = ctx.driversNear(pick)
  const typ = Math.max(1, req.referenceFeeCents)
  const dueDay = Math.floor(o.due / DAY)
  let dueLoad = 0, chainIn = 0, chainOut = 0, openAll = 0
  for (const order of ctx.orders.values()) {
    if (Math.floor(order.deadline / DAY) === dueDay) dueLoad++
    if (!order.deliveredAt.some((at) => at === null)) continue
    openAll++
    if (order.legs.length !== 1) continue
    if (ctx.km(order.legs[0]!.delivery.placeId, pick) <= 30) chainIn++
    if (ctx.km(del, order.legs[0]!.pickup.placeId) <= 30) chainOut++
  }
  const dealer = ctx.dealer(req.dealerId)
  const place = (id: string) => ctx.places.find((p) => p.id === id) ?? { lat: 0, lon: 0 }
  const a = place(pick), b = place(del)
  const roster = Math.max(1, ctx.drivers.length)
  return [
    o.drive / HOUR, Math.log(typ / 100), Number((req as any).typRaw ?? typ) / typ, nearP, ctx.driversNear(del), ctx.driversNear(pick, 80), ctx.driversNear(del, 80),
    ctx.openFrom(pick) / Math.max(1, nearP), openAll / roster, +req.legs.some((l) => l.pickup.privateAddress), +req.legs.some((l) => l.delivery.privateAddress),
    +req.legs.some((l) => l.car.premium), +req.legs.some((l) => l.car.electric), req.legs.length,
    req.options.length, o.kind === "same_day" ? 0 : o.kind === "next_day" ? 1 : 2, (o.due - o.drive - ctx.now) / HOUR, Math.max(0, o.ready - ctx.now) / HOUR, (o.due - o.ready - o.drive) / HOUR,
    Math.floor((ctx.now % DAY) / HOUR), Math.floor(ctx.now / DAY) % 7, Math.min(8, dueDay), dueLoad / roster, chainIn, chainOut, dealer.trust, dealer.lates, +o.noteReady, +o.noteBy,
    o.plan.fee / typ, o.plan.chance, o.plan.open, o.plan.raise, a.lat, a.lon, b.lat, b.lon, roster,
  ]
}

// ─── The trees (LightGBM dump: nested nodes with numeric "<=" splits) ───────────────────────
type Node = { f?: number; t?: number; l?: Node; r?: Node; v?: number }
export type CostModel = { keys: string[]; heads: Record<string, { base: number; trees: Node[] }> }
const FILE = new URL("./data/cost.json", import.meta.url)
export const COST: CostModel | null = existsSync(process.env.SPREAD_COST ?? FILE) ? JSON.parse(readFileSync(process.env.SPREAD_COST ?? FILE, "utf8")) : null
if (COST && JSON.stringify(COST.keys) !== JSON.stringify(COST_KEYS)) throw new Error("cost.json was fitted on other inputs than cost.ts builds")

export function costPredict(head: string, x: number[]): number {
  const h = COST!.heads[head]!
  let sum = h.base
  for (let node of h.trees) {
    while (node.v === undefined) node = x[node.f!]! <= node.t! ? node.l! : node.r!
    sum += node.v
  }
  return sum
}
