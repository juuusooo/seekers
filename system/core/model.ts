/**
 * model.ts — reads model.json (the numbers learned from played weeks) and answers two questions:
 *
 *   bookChance   "what is the chance a driver books this gig in the next hour, at this fee?"
 *   winChance    "what is the chance the dealer buys at this price?"
 *
 * No decision is taken here: algo.ts decides, this file only looks numbers up. Both models were fitted on
 * kit-03's played weeks (kit-03/learn/fit.py): booking on 160 random-fee weeks, win on 1,561 weeks of quotes.
 * The SAME functions build the inputs when the engine logs a week (for learning) and when the
 * algorithm decides, so what the model learned from and what it is asked about cannot drift apart.
 * `bun model.ts` checks this file against the numbers the fitter stored in model.json.
 */
import { existsSync, readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import type { Ctx, FeeStep, Leg, PriceRequest } from "./engine.ts"

const HOUR = 60
const DAY = 24 * HOUR

export type Model = {
  version: string
  /** Hourly booking chance: logistic weights by input name. */
  book: { intercept: number; coef: Record<string, number> }
  /** Chance to win a request: logistic weights, a weight per pickup and delivery town, and how much worlds differ. */
  win: { intercept: number; coef: Record<string, number>; pickup: Record<string, number>; delivery: Record<string, number>; worldSd: number }
  checks?: { book: { input: BookInput; chance: number }[]; win: { x: ReqX; markup: number; chance: number }[] }
}

export function loadModel(path = process.env.SPREAD_MODEL ?? resolve(dirname(fileURLToPath(import.meta.url)), "data", "model.json")): Model | null {
  return existsSync(path) ? (JSON.parse(readFileSync(path, "utf8")) as Model) : null
}

const sigmoid = (z: number) => 1 / (1 + Math.exp(-z))

// ─── 1. Gigs: will a driver book it? ───────────────────────────────────────────────────────

/** What we know about a gig when we post it. */
export type GigX = {
  nearP: number //    drivers living within 30 km of the first pickup (they get the notification)
  nearD: number //    drivers living within 30 km of the last delivery (they are home after the gig)
  nearP80: number //  the same within 80 km
  nearD80: number
  driveH: number //   hours at the wheel
  cars: number
  privP: number //    1 = a pickup at a private address
  privD: number
  premium: number //  1 = experienced drivers only
  load: number //     our other undelivered orders from this pickup town, per driver living near it
  typ: number //      the typical fee for this gig, in euros
}

export function gigX(ctx: Ctx, legs: Leg[], typicalCents: number, countsItself: boolean): GigX {
  const first = legs[0]!.pickup.placeId, last = legs[legs.length - 1]!.delivery.placeId
  const nearP = ctx.driversNear(first)
  return {
    nearP,
    nearD: ctx.driversNear(last),
    nearP80: ctx.driversNear(first, 80),
    nearD80: ctx.driversNear(last, 80),
    driveH: legs.reduce((sum, leg) => sum + ctx.drive(leg.pickup.placeId, leg.delivery.placeId), 0) / HOUR,
    cars: legs.length,
    privP: legs.some((leg) => leg.pickup.privateAddress) ? 1 : 0,
    privD: legs.some((leg) => leg.delivery.privateAddress) ? 1 : 0,
    premium: legs.some((leg) => leg.car.premium) ? 1 : 0,
    load: Math.max(0, ctx.openFrom(first) - (countsItself ? 1 : 0)) / Math.max(1, nearP),
    typ: typicalCents / 100,
  }
}

/** One gig in one hour: the gig, the fee as a multiple of the typical fee, and the clock. */
export type BookInput = { x: GigX; r: number; t: number; postedAt: number; lastPickupAt: number; readyAt: number; urgent: number }

/** The inputs of the booking model that do not depend on the fee. Mirrored in learn/fit.py. */
export function bookRow(i: Omit<BookInput, "r">): Record<string, number> {
  const { x, t } = i
  const hour = Math.floor((t % DAY) / HOUR)
  const day = Math.floor(t / DAY) % 7
  const left = Math.min(96, Math.max(0, (i.lastPickupAt - t) / HOUR))
  return {
    ln_nearP: Math.log1p(x.nearP),
    ln_nearD: Math.log1p(x.nearD),
    ln_nearP80: Math.log1p(x.nearP80),
    ln_nearD80: Math.log1p(x.nearD80),
    driveH: x.driveH,
    long: x.driveH >= 5 ? 1 : 0,
    cars2: x.cars > 1 ? 1 : 0,
    privP: x.privP,
    privD: x.privD,
    premium: x.premium,
    load: Math.min(3, x.load),
    ln_typ: Math.log(Math.max(1, x.typ)),
    night: hour >= 23 || hour < 7 ? 1 : 0,
    morning: hour >= 7 && hour < 10 ? 1 : 0,
    evening: hour >= 16 && hour < 20 ? 1 : 0,
    late: hour >= 20 && hour < 23 ? 1 : 0,
    sat: day === 5 ? 1 : 0,
    sun: day === 6 ? 1 : 0,
    ln_age: Math.log1p(Math.max(0, t - i.postedAt) / HOUR),
    ln_left: Math.log1p(left),
    tight: left < 3 ? 1 : 0,
    ln_wait: Math.log1p(Math.max(0, i.readyAt - t) / HOUR),
    urgent: i.urgent,
  }
}

/** The fee's own inputs: the multiple, and two bends so the curve can flatten above 1.0 and 1.4. */
const feeLogit = (m: Model, r: number) => m.book.coef.r! * r + m.book.coef.r_hi1! * Math.max(0, r - 1) + m.book.coef.r_hi2! * Math.max(0, r - 1.4)

const ROW_KEYS = ["ln_nearP", "ln_nearD", "ln_nearP80", "ln_nearD80", "driveH", "long", "cars2", "privP", "privD", "premium", "load", "ln_typ", "night", "morning", "evening", "late", "sat", "sun", "ln_age", "ln_left", "tight", "ln_wait", "urgent"] as const
const COEFS = new WeakMap<Model, number[]>()
/** Same as baseLogit(m, bookRow(...)), without building the row: the same terms added in the same order, so the
 * result is bit-identical. The fee planner calls it for every hour of every option (about 2.5 million times a week). */
function baseLogitFast(m: Model, x: GigX, t: number, postedAt: number, lastPickupAt: number, readyAt: number, urgent: number): number {
  let c = COEFS.get(m)
  if (!c) COEFS.set(m, (c = ROW_KEYS.map((k) => m.book.coef[k] ?? 0)))
  const hour = Math.floor((t % DAY) / HOUR)
  const day = Math.floor(t / DAY) % 7
  const left = Math.min(96, Math.max(0, (lastPickupAt - t) / HOUR))
  let z = m.book.intercept
  z += c[0]! * Math.log1p(x.nearP)
  z += c[1]! * Math.log1p(x.nearD)
  z += c[2]! * Math.log1p(x.nearP80)
  z += c[3]! * Math.log1p(x.nearD80)
  z += c[4]! * x.driveH
  z += c[5]! * (x.driveH >= 5 ? 1 : 0)
  z += c[6]! * (x.cars > 1 ? 1 : 0)
  z += c[7]! * x.privP
  z += c[8]! * x.privD
  z += c[9]! * x.premium
  z += c[10]! * Math.min(3, x.load)
  z += c[11]! * Math.log(Math.max(1, x.typ))
  z += c[12]! * (hour >= 23 || hour < 7 ? 1 : 0)
  z += c[13]! * (hour >= 7 && hour < 10 ? 1 : 0)
  z += c[14]! * (hour >= 16 && hour < 20 ? 1 : 0)
  z += c[15]! * (hour >= 20 && hour < 23 ? 1 : 0)
  z += c[16]! * (day === 5 ? 1 : 0)
  z += c[17]! * (day === 6 ? 1 : 0)
  z += c[18]! * Math.log1p(Math.max(0, t - postedAt) / HOUR)
  z += c[19]! * Math.log1p(left)
  z += c[20]! * (left < 3 ? 1 : 0)
  z += c[21]! * Math.log1p(Math.max(0, readyAt - t) / HOUR)
  z += c[22]! * urgent
  return z
}

function baseLogit(m: Model, row: Record<string, number>): number {
  let z = m.book.intercept
  for (const [name, value] of Object.entries(row)) z += (m.book.coef[name] ?? 0) * value
  return z
}

/** The chance that the gig is booked within the hour that starts at `t`. */
export function bookChance(m: Model, i: BookInput): number {
  return sigmoid(baseLogit(m, bookRow(i)) + feeLogit(m, i.r))
}

export type Plan = {
  schedule: FeeStep[]
  fee: number //     expected cost in cents: the fee we expect to pay + the risk of finding no driver
  chance: number //  the chance that a driver books before the last pickup time
  open: number //    the opening fee, × the typical fee
  raise: number //   the raise per hour, × the typical fee
}

/**
 * The cheapest fee schedule for a gig: tries every opening fee and raise, and for each one walks hour by
 * hour to the last pickup time, adding (chance it books this hour × fee then). What is left unbooked at
 * the end costs `lateCost` × the typical fee. Returns the schedule with the lowest expected cost.
 */
export function plan(m: Model, x: GigX, o: { now: number; typical: number; lastPickupAt: number; readyAt: number }, p: { lateCost: number; openMin: number; openMax: number; steps: number; raiseMax: number; bookShift?: number }): Plan {
  const hours = Math.min(72, Math.max(1, Math.ceil((o.lastPickupAt - o.now) / HOUR)))
  const base: number[] = []
  for (let k = 0; k < hours; k++) base.push(baseLogitFast(m, x, o.now + k * HOUR, o.now, o.lastPickupAt, o.readyAt, 0) + (p.bookShift ?? 0))
  let best = { cost: Infinity, chance: 0, open: p.openMax, raise: 0 }
  for (const raise of [0, 0.05, 0.1, 0.2]) {
    if (raise > p.raiseMax + 1e-9 || (raise > 0 && p.steps < 1)) continue
    for (let open = p.openMin; open <= Math.max(p.openMin, p.openMax) + 1e-9; open += 0.05) {
      let unbooked = 1, cost = 0
      for (let k = 0; k < hours; k++) {
        const r = open + raise * Math.min(k, p.steps)
        const chance = sigmoid(base[k]! + feeLogit(m, r))
        cost += unbooked * chance * r
        unbooked *= 1 - chance
      }
      cost += unbooked * p.lateCost
      if (cost < best.cost) best = { cost, chance: 1 - unbooked, open, raise }
    }
  }
  const steps = best.raise > 0 ? Math.round(p.steps) : 0
  const schedule = Array.from({ length: steps + 1 }, (_, k) => ({ at: o.now + k * HOUR, feeCents: Math.max(1, Math.round(o.typical * (best.open + k * best.raise))) }))
  return { schedule, fee: best.cost * o.typical, chance: best.chance, open: best.open, raise: best.raise }
}

// ─── 2. Requests: will the dealer buy? ─────────────────────────────────────────────────────

/** What we know about a request when we quote. */
export type ReqX = {
  pickup: string
  delivery: string
  driveH: number
  tradeIn: number
  privD: number
  sameDay: number // 1 = a same-day option is offered
  nOpt: number
  trust: number //   this dealer's on-time orders with us so far (level 8: +1% accepted price each, a late one halves it)
  lates: number //   this dealer's late orders with us so far
}

export function reqX(ctx: Ctx, req: PriceRequest): ReqX {
  const dealer = ctx.dealer(req.dealerId)
  return {
    pickup: req.legs[0]!.pickup.placeId,
    delivery: req.legs[0]!.delivery.placeId,
    driveH: req.legs.reduce((sum, leg) => sum + ctx.drive(leg.pickup.placeId, leg.delivery.placeId), 0) / HOUR,
    tradeIn: req.legs.length > 1 ? 1 : 0,
    privD: req.legs.some((leg) => leg.delivery.privateAddress) ? 1 : 0,
    sameDay: req.options.some((option) => option.kind === "same_day") ? 1 : 0,
    nOpt: req.options.length,
    trust: dealer.trust,
    lates: dealer.lates,
  }
}

/** Everything in the win model except the price and this world's price level. Mirrored in learn/fit.py. */
export function winBase(m: Model, x: ReqX): number {
  const c = m.win.coef
  return m.win.intercept + (m.win.pickup[x.pickup] ?? 0) + (m.win.delivery[x.delivery] ?? 0) + c.driveH! * x.driveH + c.tradeIn! * x.tradeIn + c.privD! * x.privD + c.sameDay! * x.sameDay + c.nOpt! * x.nOpt + c.trust! * x.trust + c.lates! * x.lates
}

/** The chance to win at `markup` × the list price. `world` = this week's price level, learned in algo.ts. */
export function winChance(m: Model, base: number, markup: number, world = 0): number {
  return sigmoid(base + m.win.coef.ln_m! * Math.log(markup) + world)
}

// ─── Self-check: `bun model.ts` compares this file with the numbers learn/fit.py wrote ──────
if (import.meta.main) {
  const m = loadModel()
  if (!m) throw new Error("no model.json: run learn/fit.py first")
  let worst = 0
  for (const c of m.checks?.book ?? []) worst = Math.max(worst, Math.abs(bookChance(m, c.input) - c.chance))
  for (const c of m.checks?.win ?? []) worst = Math.max(worst, Math.abs(winChance(m, winBase(m, c.x), c.markup) - c.chance))
  console.log(`model ${m.version}: ${m.checks?.book.length ?? 0} booking checks, ${m.checks?.win.length ?? 0} win checks, largest difference ${worst.toExponential(2)}`)
  if (!(worst < 1e-6)) throw new Error("model.ts and learn/fit.py disagree")
}
