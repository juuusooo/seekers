/**
 * algo.ts — every decision of the system that played the final (BEST16, level 8).
 *
 * One idea drives everything: for every car, the booking model (model.ts) estimates THE FEE AT WHICH A DRIVER
 * TAKES IT IN TIME. From that estimate:
 *
 *   quote()  which requests to take and at what price: the price with the highest
 *            chance to win × (price − expected fee − capacity cost)
 *   fees()   the fee schedule of a gig: the opening fee and raises with the lowest expected cost
 *   pair()   two cars for one driver: the schedule of a two-car gig
 *   learn()  this week's competitor price level, learned from our own wins and losses
 *
 * The engine (engine.ts) does the mechanics and calls these four. Every rule and number is listed in plain
 * words in LOGIC.csv. Change a value without editing code: bun run.ts --seed s1 --set capLam=5
 */
import type { Ctx, DeskEvent, FeeJob, FeeStep, PairJob, PriceRequest, Prices } from "./core/engine.ts"
import { lastSlot, notedHours, readNote } from "./core/notes.ts"
import { existsSync, readFileSync } from "node:fs"
import { gigX, loadModel, plan, reqX, winBase, winChance } from "./core/model.ts"
import { COST, costPredict, costRow } from "./core/cost.ts"
import type { CostIn } from "./core/cost.ts"

const HOUR = 60
const DAY = 24 * HOUR
const MODEL = loadModel()

// BEST5: the competitor's price as a number to learn. ln(price it takes to win, x list) = fixed parts (price.json:
// lane, towns, hour, dealer, trust, fitted on 22M quotes of ended practice worlds) + this week's parts, learned from
// our own answers by an online filter: the week level, one level per weekday, and (optional) dealers and towns.
type PriceData = { c: number; b: number[]; lane: number[]; pick: number[]; del: number[]; hour: number[]; dealer: number[]; places: string[] }
const PRICE_FILE = new URL("./core/data/price.json", import.meta.url)
const PRICE: PriceData | null = existsSync(PRICE_FILE) ? JSON.parse(readFileSync(PRICE_FILE, "utf8")) : null
const N_DEALER = PRICE?.dealer.length ?? 0
const N_BASE = 66 + N_DEALER // week, 5 weekdays, dealers, 30 pickup towns, 30 delivery towns
const N_STATE = N_BASE + 900 // + one level per lane (pickup x delivery town) this week (pLane); allocated only when pLane > 0

type Quoted = { g: number; h: number[]; lm: number; place?: string }
function priceParts(req: PriceRequest, ctx: Ctx, p: Params): { g: number; h: number[] } {
  const P = PRICE!
  const a = P.places.indexOf(req.legs[0]!.pickup.placeId), b = P.places.indexOf(req.legs[0]!.delivery.placeId)
  const dealer = Math.min(N_DEALER - 1, Number(req.dealerId.slice(1)) || 0)
  const hour = Math.min(18, Math.max(7, Math.floor((req.arrivedAt % DAY) / HOUR)))
  const drive = req.legs.reduce((sum, leg) => sum + ctx.drive(leg.pickup.placeId, leg.delivery.placeId), 0)
  const d = ctx.dealer(req.dealerId)
  const g = P.c + P.b[0]! * Math.log1p(0.01 * d.trust) + P.b[1]! * (drive / 600) + P.b[2]! * (req.legs.length - 1) + P.b[3]! * (req.options.length - 1)
    + P.lane[a * 30 + b]! + P.pick[a]! + P.del[b]! + P.hour[hour]! + P.dealer[dealer]! + (MODEL!.win.coef.lates! * d.lates) / Math.abs(MODEL!.win.coef.ln_m!)
  const h = [0, 1 + Math.min(4, Math.floor(req.arrivedAt / DAY)), 6 + dealer, 6 + N_DEALER + a, 36 + N_DEALER + b]
  // The competitor's price on a lane sits at its own level each week (SD about 9% of price) and 64% of requests come on
  // a lane already asked this week: single cars get one more level, per lane.
  if (p.pLane > 0 && req.legs.length === 1) h.push(N_BASE + a * 30 + b)
  return { g, h }
}
function priceState(ctx: Ctx, p: Params): { x: number[]; P: number[][] } {
  if (!ctx.memory.pf) {
    const sd = (i: number) => (i === 0 ? p.pWeek : i < 6 ? p.pDay : i < 6 + N_DEALER ? p.pDealer : i < N_BASE ? p.pTown : p.pLane)
    const n = p.pLane > 0 ? N_STATE : N_BASE
    ctx.memory.pf = { x: new Array(n).fill(0), P: Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? sd(i) ** 2 : 0))) }
  }
  return ctx.memory.pf
}

// kit-out: the outage as a hidden state. Every week the competitor is down in one region (a town and the places within
// 80 km, straight line) for one working day, 08:00 to 18:00; dealers there buy from a backup about 30% dearer. Today's
// answers are scored under "no outage today" and under "the outage is around town c" for each of the 30 towns; the
// share of belief on regions that hold a pickup is the chance that this request sees the backup's price.
const NEAR_FILE = new URL("./core/data/near80.json", import.meta.url)
const NEAR80: Record<string, string[]> = existsSync(NEAR_FILE) ? JSON.parse(readFileSync(NEAR_FILE, "utf8")) : {}
const TOWNS = Object.keys(NEAR80)
type OutAnswer = { g: number; h: number[]; lm: number; won: number; place: string }
type OutState = { day: number; seen: boolean; seenWar: boolean; prior: number[]; answers: OutAnswer[]; asked: Record<string, number>; post: number[] }
function outState(ctx: Ctx, p: Params): OutState {
  const day = Math.floor(ctx.now / DAY)
  const o: OutState = (ctx.memory.out ??= { day: -1, seen: false, seenWar: false, prior: [], answers: [], asked: {}, post: [] })
  if (o.day !== day) {
    if (o.day >= 0 && o.post.length > 0 && 1 - o.post[0]! - o.post[1]! > 0.9) o.seen = true // it happened: not again this week
    if (o.day >= 0 && o.post.length > 0 && o.post[1]! > 0.9) o.seenWar = true
    let today = o.seen || day > 4 ? 0 : Math.min(p.outPriorMax, 1 / (5 - day))
    // The price war: one working day without an outage, the competitor 20% cheaper everywhere.
    let war = !(p.warBayes > 0) || o.seenWar || day > 4 ? 0 : Math.min(p.outPriorMax, 1 / (5 - day))
    if (today + war > 0.9) [today, war] = [(today * 0.9) / (today + war), (war * 0.9) / (today + war)]
    const weight = TOWNS.map((c) => 1 + NEAR80[c]!.reduce((sum, t) => sum + (o.asked[t] ?? 0), 0)) // busy regions go down more often
    const total = weight.reduce((a, b) => a + b, 0)
    o.day = day
    o.prior = [1 - today - war, war, ...weight.map((w) => (today * w) / total)]
    o.answers = []
    o.post = o.prior.slice()
  }
  return o
}
/** Belief over (none, town 1..30) from today's answers, read against the price filter as it stands now. */
function outUpdate(o: OutState, st: { x: number[] }, p: Params): void {
  const lnK = Math.log(p.outageK), lnW = Math.log(p.warK), clip = (v: number) => Math.min(0.92, Math.max(0.08, v))
  const lw = o.prior.map((v) => Math.log(v + 1e-12))
  for (const a of o.answers) {
    const z = a.g + a.h.reduce((sum, i) => sum + st.x[i]!, 0) - a.lm
    const p0 = clip(1 / (1 + Math.exp(-z / p.pS))), p1 = clip(1 / (1 + Math.exp(-(z + lnK) / p.pS)))
    const pw = clip(1 / (1 + Math.exp(-(z + lnW) / p.pS)))
    const l0 = Math.log(a.won ? p0 : 1 - p0), l1 = Math.log(a.won ? p1 : 1 - p1)
    lw[0]! += l0
    lw[1]! += Math.log(a.won ? pw : 1 - pw)
    for (let c = 0; c < TOWNS.length; c++) lw[c + 2]! += NEAR80[TOWNS[c]!]!.includes(a.place) ? l1 : l0
  }
  const top = Math.max(...lw), e = lw.map((v) => Math.exp(v - top)), total = e.reduce((a, b) => a + b, 0)
  o.post = e.map((v) => v / total)
}
const outShare = (o: OutState, place: string) => TOWNS.reduce((sum, c, i) => sum + (NEAR80[c]!.includes(place) ? o.post[i + 2]! : 0), 0)

// BEST9: realized cost (research/real_cost). What orders like this one ended up costing on 399 played server weeks
// (fees with raises, refunds, failed visits, undelivered cars), from trees on the inputs of core/cost.ts
// (core/data/cost.json, 156k won orders). costW blends it with the plan's expected fee; costUp leans the estimate
// toward its 80th percentile. costW = 0 plays BEST8.
function realCost(req: PriceRequest, ctx: Ctx, p: Params, plan: { fee: number }, input: CostIn): number {
  if (!(p.costW > 0) || !COST) return plan.fee
  const x = costRow(ctx, req, input)
  const mean = costPredict("mean", x)
  const est = mean + p.costUp * Math.max(0, costPredict("q80", x) - mean)
  return (1 - p.costW) * plan.fee + p.costW * est * req.referenceFeeCents
}

// ─── PARAMETERS (the values of the best model; LOGIC.csv explains each one) ──────────────────
export const PARAMS = {
  // Which options to sell
  minBookChance: 0.95, // sell at the normal price only if a driver books before the last pickup time with this chance
  hardChance: 0.82, /* BEST16 (was 0.85) */ //    between this and minBookChance: still sell, but `hardPrice` dearer
  hardPrice: 0.2, //      price rise (× list) for such a hard option
  costW: 1.25, /* BEST16 (was 1) */ //            weight of the realized-cost trees in the cost of the price choice (BEST9; 0 = plan fee only, BEST8)
  costUp: 0, //           lean of that estimate toward its 80th percentile (0 = the mean)
  minProfit: 0.1, //      the price must be at least (1 + this) × the expected fee
  minSlackH: 3, //        the deadline must leave this many hours beyond the drive
  capPerDriver: 3, //     a pickup town is "full" when our undelivered orders from it reach this × drivers living near it
  dueCapPer: 0.1, //      a deadline day (Mon to Fri) is "full" at this × the week's drivers of our orders due that day
  fullPrice: 0.25, //     a full town or full day is not declined but priced this much higher (× list)
  // Price (multiples of the list price)
  markupMin: 1.28, //     lowest price the search may choose
  markupMax: 2, //        highest
  capLam: 4, //           capacity cost: EUR per driver-hour (drive hours + capConst), subtracted in the price choice
  capConst: 1, //         hours a driver spends beyond the wheel (to the pickup, home)
  pairBack: 0.05, //      price cut (× list) for a request that completes a round trip with an open gig of ours
  outage: 0.3, //         price rise (× list) where the competitor is down (we win far more than expected near a pickup today)
  outageN: 6, //          … judged on at least this many of today's answers within 80 km of the pickup
  outageGap: 0.3, //      … whose share won beats the win model by this much
  worldN: 300, //         the week's price level is learned from our last this-many answers
  // Driver fees (multiples of the gig's typical fee)
  lateCost: 4, //         what a gig without a driver costs, in the search for the cheapest schedule
  openMin: 0.706, //      lowest opening fee the search may choose (BEST6, was 0.6)
  openMax: 1.6, //        highest
  raiseMax: 0.2, //       highest raise per hour
  steps: 4, /* BEST16 (was 5) */ //            number of hourly raises
  rampTop: 1.45, /* BEST16 (was 1.6) */ //        a gig still open `rampWindowH` before its last pickup time climbs hourly to this
  rampWindowH: 10, //     … starting this many hours before the last pickup time, ending 3 hours before it
  steepOpen: 1.3, //      after a deadline warning: first fee …
  steepStep: 0.15, //     … then this much more every half hour, 4 times
  lateFee: 0.832, //      once the last pickup time has passed (late anyway): back to this, +0.2 every 6 hours up to 2 (BEST6, was 1.2)
  // Two cars, one driver
  pairKm: 40, /* BEST16 (was 30) */ //          the first car's delivery within this many km of the second car's pickup
  pairSlackH: 6, //       … and this many hours to spare before the tighter last pickup time
  pairCap: 0.9, //        a two-car gig opens at most at this × the sum of the typical fees
  pairTop: 1.3, //        … and climbs to at most this before its deadline warning
  pairHoldH: 3, /* BEST16 (was 4) */ //        a two-car gig nobody booked after this many hours is taken apart (engine)
  // Dealer notes
  noteHours: 1, //        (BEST7) 1 = read the real site hours in the note: stop windows inside them (engine), price and fees count the shorter days
  hoursMinLeftH: 1.5, //  … a day's slot with less than this many hours left is skipped for the next day's (engine)
  pairFlags: 1, //        (BEST7) 1 = an order whose note says no plates or manual gearbox is not joined into a two-car gig (engine)
  // Typical fee (engine)
  // Competitor price learned by weekday (BEST5, 14 Nov: +419 ± 101 a week over BEST4 on 80 fresh weeks)
  priceLearn: 1, //       1 = prices from the online filter (BEST5); 0 = the win model of BEST4
  pS: 0.1, //             how sharp the dealer's choice is around the competitor's price (log price)
  pWeek: 0.05, //          how far a week's level can sit from the average (SD, log price)
  pDay: 0.14, //          … a weekday's level from the week's
  pDealer: 0, //          … a dealer's level this week (0 = not learned)
  pLane: 0.06, //         (BEST14; 0 = BEST13) … a lane's level this week (pickup x delivery town, single cars): one more level of the filter, added when the lane is first asked
  pTown: 0, //            … a pickup or delivery town's level this week (0 = not learned)
  // Price by deadline day (BEST8, 14 Nov): Monday deadlines have slack (no new requests that day), Friday is the tight day
  dueMon: -0.03, //       price shift (× list) for an option due on the next Monday or later
  dueFri: 0.08, //        … for an option due on Friday
  floorLvl: 1, //         (BEST10) the lowest price follows the learned competitor level: markupMin + this x (week + weekday level, log price) when that level is below average (0 = fixed floor, BEST9)
  openTilt: 0, //         (BEST15: 0 = no tilt, for on time; BEST11 to BEST14 played 0.25) fees by gig size: the normal schedule x (tiltRef EUR / typical fee)^this, between 0.67 and 1.5
  tiltRef: 60, //         … the typical fee (EUR a car) that keeps its fees: cheaper gigs get a higher multiple, dearer ones a lower
  outBayes: 1, //         (BEST12; 0 with outageK=0 = BEST11) 1 = the outage is a belief over regions from today's answers (replaces the outageN / outageGap rule); needs outageK
  warBayes: 0, //         (kit-out) 1 = the price-war day is one more state of that belief (competitor x warK everywhere)
  warK: 0.8, //           … the competitor's price on the price-war day, x its usual price
  warFloor: 0.2, //       … how far the price floor falls on a sure price-war day (x list)
  outPriorMax: 0.6, //    … the most belief an outage today gets before any answer (1 / working days left, capped)
  outageK: 1.2, //        (BEST12; proof value 1.2, handbook says 1.3) in a detected outage the dealer's other choice is a backup this many x the competitor's price: the win chance is read against that price (1.3 = the handbook; 0 = off, only the `outage` floor shift)
  floorTyp: 0, //         (kit-out) lower price floor for cars that are cheap to move: floor shift -this x (floorTypRef - typical fee / list price) when positive
  floorTypRef: 0.8, //    … the typical fee / list price below which the floor starts to fall
  feeMon: 1, //           fees by posting day: all planned fees x this for a gig posted on the first Monday
  feeMid: 1, //           … posted on Tuesday or Wednesday
  feeLate: 0.95, //       (BEST13; 1 = BEST12) … posted from Thursday on
  bookShift: 0.2, //      (BEST16; 0 = BEST15) the fee schedules assume drivers book a little sooner: added to the booking model's hourly logit in the fee plan
  bookQuote: 0, //        1 = that shift also counts in the price choice and in which options are sold (more orders, costs on time: not used)
  typMinN: 5, //          lanes seen fewer times than this in typ.json keep the dealer's typical fee
}
export type Params = typeof PARAMS

// ─── 1. PRICES: which requests to take, at what price ──────────────────────────────────────
export function quote(req: PriceRequest, ctx: Ctx, p: Params): Prices | string {
  if (!MODEL) return "no model.json"
  // The dealer's note can say the car is ready later, or must arrive earlier (notes.ts, 99% right on the reveals).
  const read = readNote(req.note?.text, req.arrivedAt)
  const noteDl = read.deliverBy
  const stated = Math.max(req.arrivedAt, ...req.legs.map((leg) => leg.pickup.window.from))
  // A car that is ready a day or more later moves its deadline by the same days (weekends do not count).
  const moved = (deadline: number) => {
    let days = Math.max(0, Math.floor((read.readyFrom ?? 0) / DAY) - Math.floor(stated / DAY))
    let day = Math.floor(deadline / DAY)
    while (days > 0) { day++; if (day % 7 < 5) days-- }
    return day * DAY + (deadline % DAY)
  }
  const due = (option: { deadline: number }) => (noteDl !== null ? Math.min(moved(option.deadline), noteDl) : moved(option.deadline))
  const drive = req.legs.reduce((sum, leg) => sum + ctx.drive(leg.pickup.placeId, leg.delivery.placeId), 0)
  const ready = Math.max(stated, read.readyFrom ?? 0)
  // Real site hours from the note: the last pickup minute is the last one inside them that still arrives in time.
  const sites = p.noteHours > 0 ? notedHours(req.note?.text, req.legs) : null
  const lastPickup = (option: { deadline: number }) => (sites ? (lastSlot(sites.pickup, sites.delivery, drive, ready, due(option)) ?? -Infinity) : due(option) - drive)

  // Capacity rules: a full pickup town or a full deadline day is priced higher (fullPrice), not declined.
  const supply = Math.min(...req.legs.map((leg) => ctx.driversNear(leg.pickup.placeId)))
  const townFull = ctx.openFrom(req.legs[0]!.pickup.placeId) >= p.capPerDriver * supply
  const dueOn = new Map<number, number>()
  const dueCap = Math.round(p.dueCapPer * ctx.drivers.length)
  for (const order of ctx.orders.values()) dueOn.set(Math.floor(order.deadline / DAY), (dueOn.get(Math.floor(order.deadline / DAY)) ?? 0) + 1)
  const dayFull = (deadline: number) => {
    const day = Math.floor(deadline / DAY)
    return dueCap > 0 && day <= 4 && (dueOn.get(day) ?? 0) >= dueCap
  }

  // For each option: the cheapest fee schedule, its expected cost, and the chance a driver books in time.
  const gig = gigX(ctx, req.legs, req.referenceFeeCents, false)
  const options = req.options
    .filter((option) => lastPickup(option) - ready >= p.minSlackH * HOUR)
    .filter((option) => lastPickup(option) - ctx.now >= 0)
    .map((option) => ({ option, plan: plan(MODEL, gig, { now: ctx.now, typical: req.referenceFeeCents, lastPickupAt: lastPickup(option), readyAt: ready }, p.bookQuote > 0 ? p : { ...p, bookShift: 0 }) }))
    .map(({ option, plan }) => ({ option, plan, cost: realCost(req, ctx, p, plan, { due: due(option), ready, drive, kind: option.kind, plan, noteReady: read.readyFrom !== null, noteBy: noteDl !== null }) }))
    .filter(({ plan }) => plan.chance >= (p.hardPrice > 0 ? Math.min(p.minBookChance, p.hardChance) : p.minBookChance))
  if (options.length === 0) return "no option a driver would book in time"

  // One markup for the request: the highest chance to win × (price − expected fee − capacity cost).
  const list = options.reduce((sum, o) => sum + o.option.listPriceCents, 0) / options.length
  const fee = options.reduce((sum, o) => sum + o.cost, 0) / options.length
  const base = winBase(MODEL, reqX(ctx, req))
  const hourNow = Math.floor((ctx.now % DAY) / HOUR)
  const today = Math.floor(ctx.now / DAY) * DAY
  let shift = 0
  let outageOn = false
  if (townFull) shift += p.fullPrice
  // A car that rides back with an open gig of ours (its pickup where that car is delivered, its delivery where that
  // car starts) costs a driver no trip home: we can afford a lower price for it.
  if (req.legs.length === 1) {
    const leg = req.legs[0]!
    if (ctx.openSingles().some((o) => ctx.km(o.legs[0]!.delivery.placeId, leg.pickup.placeId) <= p.pairKm && ctx.km(leg.delivery.placeId, o.legs[0]!.pickup.placeId) <= p.pairKm)) shift -= p.pairBack
  }
  // Competitor outage: once a week it is down in one region for a working day. Today's answers near this pickup
  // beating the win model by outageGap means we are in it: price higher there.
  if (hourNow >= 8 && hourNow < 18 && !(p.outBayes > 0)) {
    const near = ((ctx.memory.answersAt ?? []) as { at: number; place: string; won: number; chance: number }[]).filter((a) => a.at >= today + 8 * HOUR && ctx.km(a.place, req.legs[0]!.pickup.placeId) <= 80)
    if (near.length >= p.outageN && near.reduce((sum, a) => sum + a.won - a.chance, 0) / near.length >= p.outageGap) { shift += p.outage; outageOn = true }
  }
  // Capacity cost: drivers are the bottleneck at level 8, so a car that holds a driver longer must earn more.
  const lamC = p.capLam * 100 * (drive / HOUR + p.capConst)
  let markup = p.markupMin
  let best = -Infinity
  // BEST5: the chance to win from the learned competitor price, with the filter's own doubt folded in.
  let chance = (m: number) => winChance(MODEL, base, m, ctx.memory.world ?? 0)
  const parts = p.priceLearn > 0 && PRICE ? priceParts(req, ctx, p) : null
  // kit-out: in an outage the dealers there buy from a backup about 30% dearer than the competitor: price against it,
  // and let the filter read the answer against it too (else the whole weekday level drifts up).
  if (parts && outageOn && p.outageK > 0) parts.g += Math.log(p.outageK)
  let share = 0, war = 0
  const pickupPlace = req.legs[0]!.pickup.placeId
  if (parts && p.outBayes > 0 && p.outageK > 0 && hourNow >= 8 && hourNow < 18 && TOWNS.length > 0) {
    const o = outState(ctx, p)
    o.asked[pickupPlace] = (o.asked[pickupPlace] ?? 0) + 1
    outUpdate(o, priceState(ctx, p), p)
    share = outShare(o, pickupPlace)
    war = o.post[1]!
    shift += p.outage * share - p.warFloor * war
  }
  if (parts) {
    const st = priceState(ctx, p)
    let mu = parts.g, v = 0
    for (const i of parts.h) { mu += st.x[i]!; for (const j of parts.h) v += st.P[i]![j]! }
    const scale = Math.sqrt(p.pS ** 2 + 0.37 * v)
    const lnK = share > 0 ? Math.log(p.outageK) : 0, lnW = war > 0 ? Math.log(p.warK) : 0
    chance = (m: number) => (1 - share - war) / (1 + Math.exp(-(mu - Math.log(m)) / scale)) + share / (1 + Math.exp(-(mu + lnK - Math.log(m)) / scale)) + war / (1 + Math.exp(-(mu + lnW - Math.log(m)) / scale))
  }
  // BEST10: in a cheap week or on a cheap day (price war) the fixed floor loses whole days: let it follow the level.
  if (parts && p.floorLvl > 0) {
    const st = priceState(ctx, p), level = st.x[0]! + st.x[parts.h[1]!]!
    if (level < 0) shift += Math.max(-0.2, p.floorLvl * level)
  }
  // kit-out: a car whose typical fee is small against its list price leaves a margin far below the usual floor.
  if (p.floorTyp > 0) shift -= p.floorTyp * Math.max(0, p.floorTypRef - req.referenceFeeCents / list)
  for (let m = p.markupMin + shift; m <= Math.max(p.markupMin, p.markupMax) + shift + 1e-9; m += 0.01) {
    const value = chance(m) * (m * list - fee - lamC)
    if (value > best) [best, markup] = [value, m]
  }

  const prices: Prices = {}
  for (const { option, plan, cost } of options) {
    const dueDay = Math.floor(due(option) / DAY)
    const byDay = dueDay >= 7 ? p.dueMon : dueDay === 4 ? p.dueFri : 0
    const price = Math.round(option.listPriceCents * (markup + byDay) * (dayFull(option.deadline) ? 1 + p.fullPrice : 1) * (plan.chance < p.minBookChance ? 1 + p.hardPrice : 1))
    if (price >= cost * (1 + p.minProfit)) prices[option.kind] = price
  }
  if (Object.keys(prices).length === 0) return "price does not cover the expected fee"
  // What we expected, so learn() can compare it with the dealer's answer.
  ;(ctx.memory.quoted ??= {})[req.id] = base + MODEL.win.coef.ln_m! * Math.log(markup)
  ;(ctx.memory.quotedPlace ??= {})[req.id] = req.legs[0]!.pickup.placeId
  if (parts) (ctx.memory.pq ??= {})[req.id] = { g: parts.g, h: parts.h, lm: Math.log(markup), place: p.outBayes > 0 && hourNow >= 8 && hourNow < 18 ? pickupPlace : undefined } satisfies Quoted
  return prices
}

// ─── 2. DRIVER FEES: what to pay for a gig ─────────────────────────────────────────────────
// job.fee is the gig's share of the typical fee (cents). job.urgent is true after a deadline warning.
export function fees(job: FeeJob, ctx: Ctx, p: Params): FeeStep[] {
  // The note's own deadline, when it is earlier than the option's: the fees count down to it.
  const noted = readNote(job.request.note?.text, job.request.arrivedAt)
  const jobDrive = job.order.legs.reduce((sum, leg) => sum + ctx.drive(leg.pickup.placeId, leg.delivery.placeId), 0)
  let lastPickupAt = noted.deliverBy != null ? Math.min(job.order.lastPickupAt, noted.deliverBy - jobDrive) : job.order.lastPickupAt
  const sites = p.noteHours > 0 ? notedHours(job.request.note?.text, job.order.legs) : null
  if (sites) lastPickupAt = Math.min(lastPickupAt, lastSlot(sites.pickup, sites.delivery, jobDrive, job.order.legs[0]!.pickup.window.from, job.order.deadline) ?? lastPickupAt)
  const step = (k: number, every: number, open: number, raise: number) => ({ at: ctx.now + k * every, feeCents: Math.max(1, Math.round(job.fee * (open + k * raise))) })
  // Late anyway: paying more buys nothing, so go back to lateFee and climb slowly.
  if (job.urgent && p.lateFee > 0 && ctx.now >= lastPickupAt) return [0, 1, 2, 3, 4].map((k) => ({ at: ctx.now + k * 6 * HOUR, feeCents: Math.max(1, Math.round(job.fee * Math.min(Math.max(2, p.lateFee), p.lateFee + 0.2 * k))) }))
  // After a deadline warning: steepOpen, then +steepStep every half hour.
  if (job.urgent) return [0, 1, 2, 3, 4].map((k) => step(k, 30, p.steepOpen, p.steepStep))
  // Normal: the cheapest planned schedule, then the early ramp.
  const legs = job.legs.map((leg) => job.order.legs[leg]!)
  const schedule = plan(MODEL!, gigX(ctx, legs, job.fee, true), { now: ctx.now, typical: job.fee, lastPickupAt: lastPickupAt, readyAt: legs[0]!.pickup.window.from }, p).schedule
  const out0 = p.rampTop > 0 ? withRamp(schedule, job.fee, lastPickupAt, p) : schedule
  const dayNow = Math.floor(ctx.now / DAY), byDay = dayNow === 0 ? p.feeMon : dayNow <= 2 ? p.feeMid : p.feeLate
  const out = byDay === 1 ? out0 : out0.map((s) => ({ at: s.at, feeCents: Math.max(1, Math.round(s.feeCents * byDay)) }))
  if (p.openTilt === 0) return out
  // BEST11: a cheap gig costs a driver more per euro of typical fee than a dear one (realized-cost study).
  const tilt = Math.min(1.5, Math.max(0.67, ((p.tiltRef * 100 * job.cars) / job.fee) ** p.openTilt))
  const tilted = out.map((s) => ({ at: s.at, feeCents: Math.max(1, Math.round(s.feeCents * tilt)) }))
  for (let i = 1; i < tilted.length; i++) tilted[i]!.feeCents = Math.max(tilted[i]!.feeCents, tilted[i - 1]!.feeCents)
  return tilted
}

// Raise early, not near the pickup: a gig nobody booked climbs hourly from its last planned fee to
// `rampTop` × typical, ending 3 hours before the last pickup time (when the deadline warning comes).
function withRamp(schedule: FeeStep[], typical: number, lastPickupAt: number, p: Params): FeeStep[] {
  const last = schedule.at(-1)!
  const end = lastPickupAt - 3 * HOUR
  const start = Math.max(last.at + HOUR, lastPickupAt - p.rampWindowH * HOUR)
  const top = Math.round(typical * p.rampTop)
  if (top <= last.feeCents || end < start) return schedule
  const n = Math.min(48 - schedule.length, Math.max(1, Math.floor((end - start) / HOUR) + 1))
  const ramp = Array.from({ length: n }, (_, k) => ({ at: start + k * HOUR, feeCents: Math.round(last.feeCents + ((top - last.feeCents) * (k + 1)) / n) }))
  return [...schedule, ...ramp]
}

// ─── 3. TWO-CAR GIGS: one driver pays one trip to the first pickup and one trip home ───────
export function pair(job: PairJob, ctx: Ctx, p: Params): { schedule: FeeStep[]; score: number } | null {
  if (!MODEL || job.orders.length !== 2) return null
  if (job.joinKm > p.pairKm || job.slackMin < p.pairSlackH * HOUR) return null
  const legs = job.orders.map((o) => o.legs[0]!)
  const lastPickupAt = ctx.now + job.slackMin
  const best = plan(MODEL, gigX(ctx, legs, job.typical, true), { now: ctx.now, typical: job.typical, lastPickupAt, readyAt: legs[0]!.pickup.window.from }, { ...p, openMax: Math.min(p.openMax, p.pairCap) })
  const cap = Math.round(job.typical * p.pairCap)
  const schedule = best.schedule.map((s) => ({ at: s.at, feeCents: Math.min(s.feeCents, cap) }))
  return { schedule: withRamp(schedule, job.typical, lastPickupAt, { ...p, rampTop: p.pairTop }), score: -job.joinKm - 0.5 * job.backKm }
}

// ─── 4. LEARNING: this week's competitor price level ────────────────────────────────────────
// The competitor is 26% to 54% above list, different every week, and we never see its prices. Each win or loss
// tells a little: winning more than the model expected means this world is expensive, so `world` rises and quote()
// prices higher. It starts at 0 (an average week) and uses the last `worldN` answers.
export function learn(event: DeskEvent, ctx: Ctx, p: Params): void {
  if (!MODEL || (event.kind !== "order_won" && event.kind !== "order_lost")) return
  const id = event.kind === "order_won" ? event.order.id : event.requestId
  // BEST5: one filter step per answer (a logistic observation of the competitor's price).
  const q: Quoted | undefined = ctx.memory.pq?.[id]
  if (q && p.priceLearn > 0) {
    delete ctx.memory.pq[id]
    const st = priceState(ctx, p), won = event.kind === "order_won" ? 1 : 0
    // kit-out: the answer first moves the outage belief; the filter then reads it against the expected price there.
    if (q.place && p.outBayes > 0 && p.outageK > 0) {
      const o = outState(ctx, p)
      o.answers.push({ g: q.g, h: q.h, lm: q.lm, won, place: q.place })
      outUpdate(o, st, p)
      q.g += outShare(o, q.place) * Math.log(p.outageK) + o.post[1]! * Math.log(p.warK)
    }
    const col = (P: number[][]) => P.map((row) => q.h.reduce((sum, j) => sum + row[j]!, 0) / p.pS)
    const chance = 1 / (1 + Math.exp(-(q.g + q.h.reduce((sum, i) => sum + st.x[i]!, 0) - q.lm) / p.pS))
    const w = chance * (1 - chance), Pa = col(st.P)
    const k = w / (1 + (w * q.h.reduce((sum, i) => sum + Pa[i]!, 0)) / p.pS)
    const n = st.x.length
    for (let i = 0; i < n; i++) if (Pa[i] !== 0) for (let j = 0; j < n; j++) if (Pa[j] !== 0) st.P[i]![j]! -= Pa[i]! * Pa[j]! * k
    const gain = col(st.P)
    for (let i = 0; i < n; i++) st.x[i]! += gain[i]! * (won - chance)
  }
  const expected = ctx.memory.quoted?.[id]
  if (expected === undefined) return
  delete ctx.memory.quoted[id]
  // For the outage rule: each answer with where it was and what the model expected.
  ;(ctx.memory.answersAt ??= []).push({ at: ctx.now, place: ctx.memory.quotedPlace[id], won: event.kind === "order_won" ? 1 : 0, chance: 1 / (1 + Math.exp(-(expected + (ctx.memory.world ?? 0)))) })
  const answers: [number, number][] = (ctx.memory.answers ??= [])
  answers.push([expected, event.kind === "order_won" ? 1 : 0])
  while (answers.length > p.worldN) answers.shift()
  // One-number logistic fit (4 Newton steps) with a prior: weeks differ by MODEL.win.worldSd in log odds.
  const prior = 1 / MODEL.win.worldSd ** 2
  let w = ctx.memory.world ?? 0
  for (let i = 0; i < 4; i++) {
    let slope = -w * prior, curve = prior
    for (const [z, won] of answers) {
      const chance = 1 / (1 + Math.exp(-(z + w)))
      slope += won - chance
      curve += chance * (1 - chance)
    }
    w += slope / curve
  }
  ctx.memory.world = w
}
