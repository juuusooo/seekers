/**
 * engine.ts — the mechanics. The decisions live in algo.ts; this file keeps the books and talks to the server.
 *
 * Built from the kit's starter. It keeps the starter's loops, bookkeeping, reposts, retries, note reader and
 * restart logic, and asks the algorithm for every decision that costs or earns money: prices and driver fees.
 * On top of the starter it:
 *   - replaces each request's typical fee by the lane-table prediction (typ.json): the dealer's typical fee
 *     carries about 13% noise that drivers ignore (denoise)
 *   - joins two one-car orders into one two-car gig (tryPair) and takes an unbooked pair apart after pairHoldH
 *   - reads "no plates" / "manual gearbox" in the note before the first visit (post)
 *   - reads "not ready before" / "must arrive by" in the note (notes.ts) for the gig's windows and fee timing
 *   - resets the fee of a gig whose last pickup time has passed (late anyway, so the urgent fee buys nothing)
 */
import { join, resolve } from "node:path"
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs"
import { Client, SpreadError, World } from "./spread.ts"
import type { Action, ActionResult, DeskEvent, DeskEventKind, DeskSnapshot, DriverProfile, FeeStep, Leg, Note, Order, Place, PostAction, PriceRequest, Score, StopRef, TimeWindow, WorldMap } from "./spread.ts"
import { gigX, reqX } from "./model.ts"
import { lastSlot, nextSlot, notedHours, readNote } from "./notes.ts"
export type { DeskEvent, DriverProfile, FeeStep, Leg, Order, Place, PriceRequest, Score } from "./spread.ts"

export const HOUR = 60
export const DAY = 24 * HOUR
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
/** The events that need an answer in practice. Views and account lines arrive with the next one. */
const WAKE_ON: DeskEventKind[] = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close", "delivered", "gig_dropped", "no_show"]

// ─── The contract between the engine and the algorithm (algo.ts) ───────────────────────────

/** Prices in cents by option kind. Leave an option out to not sell it. */
export type Prices = Partial<Record<"same_day" | "next_day" | "within_3_days", number>>
/** Single-car orders that one driver could move in one gig, in this order. */
export type PairJob = { orders: Order[]; typical: number; driveMin: number; joinKm: number; backKm: number; slackMin: number }
/** A gig that needs a fee schedule. `fee` is the gig's share of the request's typical fee, in cents;
 * `legs` are the positions in order.legs of the cars this gig carries. */
export type FeeJob = { order: Order; request: PriceRequest; fee: number; cars: number; legs: number[]; urgent: boolean }

/** What the algorithm can read. Everything is in world minutes and cents. */
export interface Ctx {
  readonly now: number
  readonly level: number
  /** Road minutes between two places (the map's planning minutes). */
  drive(from: string, to: string): number
  /** Straight-line km between two places. */
  km(from: string, to: string): number
  /** Drivers whose home is within `radiusKm` (default 30, the app's notification radius) of a place. */
  driversNear(placeId: string, radiusKm?: number): number
  /** Our won orders from this pickup place that still have an undelivered car. */
  openFrom(placeId: string): number
  /** Our one-car orders whose gig is open and not booked (candidates for a two-car gig). */
  openSingles(): Order[]
  /** Our record with a dealer this week: `trust` = on-time orders (a late one halves it, cap 25), `lates` = late orders. */
  dealer(dealerId: string): { trust: number; lates: number }
  readonly places: Place[]
  readonly drivers: DriverProfile[]
  readonly requests: ReadonlyMap<string, PriceRequest> // every request seen, by id
  readonly orders: ReadonlyMap<string, Order> // won and not cancelled, by id
  /** Free space for the algorithm's own state (estimates, counters). Empty at the start of each week. */
  readonly memory: Record<string, any>
}

export type Algo<P extends Record<string, number> = Record<string, number>> = {
  PARAMS: P
  quote(request: PriceRequest, ctx: Ctx, p: P): Prices | string
  fees(job: FeeJob, ctx: Ctx, p: P): FeeStep[]
  /** Two-car gigs: should these orders ride in one gig? Return its fee schedule, or null. `score` picks among partners. */
  pair(job: PairJob, ctx: Ctx, p: P): { schedule: FeeStep[]; score: number } | null
  learn(event: DeskEvent, ctx: Ctx, p: P): void
}

/** Loads an algorithm file, e.g. "algo.ts". */
export async function loadAlgo(path = new URL("../algo.ts", import.meta.url).pathname): Promise<Algo> {
  return (await import(resolve(path))) as Algo
}

/** The parameters: PARAMS of the algorithm, then the command line's overrides (unknown names are refused). */
export function paramsFor(algo: Algo, overrides: Record<string, number> = {}): Record<string, number> {
  for (const key of Object.keys(overrides)) if (!(key in algo.PARAMS)) throw new SpreadError(0, `Unknown parameter "${key}". Known: ${Object.keys(algo.PARAMS).join(", ")}`)
  return { ...algo.PARAMS, ...overrides } as Record<string, number>
}

/** Parses "capLam=5,markupMin=1.3" into { capLam: 5, markupMin: 1.3 }. */
export function parseSet(text: string | undefined): Record<string, number> {
  const out: Record<string, number> = {}
  for (const pair of (text ?? "").split(",").filter(Boolean)) {
    const [key, value] = pair.split("=")
    if (!key || value === undefined || Number.isNaN(Number(value))) throw new SpreadError(0, `--set expects key=number pairs, got "${pair}"`)
    out[key.trim()] = Number(value)
  }
  return out
}

// ─── Denoised typical fee ──────────────────────────────────────────────────────────────────
// typ.json: ln(typical fee) = lane + private-pickup/delivery + premium + electric terms, fitted on 557k one-leg
// requests of 570 practice worlds (core/tools/fit_typ.py). A trade-in's typical fee is 0.50 × the sum of its legs.
// The dealer's typical fee is replaced by this prediction everywhere (prices, gig fees, pairs).
const TYP: { lane: Record<string, number>; n: Record<string, number>; privP: number; privD: number; prem: number; elec: number; trade: number } = JSON.parse(readFileSync(new URL("./data/typ.json", import.meta.url), "utf8"))
function denoise(request: PriceRequest, p: Record<string, number>): void {
  if ((request as any).typRaw !== undefined) return
  let pred = 0
  for (const leg of request.legs) {
    const key = `${leg.pickup.placeId}>${leg.delivery.placeId}`
    if ((TYP.n[key] ?? 0) < p.typMinN!) return // a lane we have seen too rarely keeps the dealer's number
    pred += Math.exp(TYP.lane[key]! + TYP.privP * +leg.pickup.privateAddress + TYP.privD * +leg.delivery.privateAddress + TYP.prem * +leg.car.premium + TYP.elec * +leg.car.electric)
  }
  if (request.legs.length > 1) pred *= Math.exp(TYP.trade)
  ;(request as any).typRaw = request.referenceFeeCents
  request.referenceFeeCents = Math.round(pred)
}

// ─── The desk: memory, mechanics, and the bridge to the algorithm ──────────────────────────

type Retry = { pickupFrom: number; manualLicence: boolean; plates: boolean }
// Words in dealer notes (Finnish, Swedish, English, with their usual typos). Measured on 4,500 notes of won cars:
// plates 91 of 91 found, no false alarm; manual gearbox 129 of 129, no false alarm.
const NOTE_PLATES = /kilv|kilp|kiilp|rekkar|plate|skylt|unregist|oregistr/i
const NOTE_MANUAL = /manua|mnual|mnaua|mannua|manul|käsivaiht|kasivaiht|stick|manuell|växel|vaxel|ei automaatti|no automatic|not automatic|inte automat/i
const FIRST_TRY: Retry = { pickupFrom: 0, manualLicence: false, plates: false }

export class Desk implements Ctx {
  now: number
  readonly outbox: Action[] = []
  readonly requests = new Map<string, PriceRequest>()
  readonly orders = new Map<string, Order>()
  readonly legGigs = new Map<string, Map<number, string>>() // order id -> leg -> the gig that carries the leg
  readonly booked = new Set<string>() // the gigs that a driver holds now
  readonly posts = new Map<string, PostAction>() // gig id -> the post that made it
  readonly urgent = new Set<string>() // the orders whose deadline warning has come
  readonly solo = new Set<string>() // orders that go alone from now on (a pair expired, was dropped or got urgent)
  readonly memory: Record<string, any> = {}
  readonly stats = { quoted: 0, declined: 0, why: {} as Record<string, number> }
  /** The week for analysis scripts: every quote, post, reprice and booking, with the model's inputs. */
  readonly journal: Record<string, unknown>[] = []
  readonly dealers = new Map<string, { trust: number; lates: number }>()
  readonly places: Place[]
  readonly #minutes = new Map<string, number>()
  readonly #placeById = new Map<string, Place>()
  readonly #near = new Map<string, number>()
  /** Timers: [minute, order id]. When an order's last pickup time passes with a gig still open, its fee is set again. */
  readonly timers: [number, string][] = []
  /** Two-car gigs that no driver booked are taken apart at this minute: [minute, gig id]. */
  readonly pairTimers: [number, string][] = []
  /** Orders whose note sets an earlier deadline: their urgent fees start 3 hours before the note's last pickup time. */
  readonly noteTimers: [number, string][] = []

  readonly world: World
  readonly level: number
  readonly algo: Algo
  readonly p: Record<string, number>
  readonly drivers: DriverProfile[]

  constructor(world: World, level: number, now: number, algo: Algo, p: Record<string, number>, map: WorldMap, drivers: DriverProfile[]) {
    this.world = world
    this.level = level
    this.algo = algo
    this.p = p
    this.drivers = drivers
    this.now = now
    this.places = map.places
    for (const road of map.roads) this.#minutes.set(`${road.from}>${road.to}`, road.minutes)
    for (const place of map.places) this.#placeById.set(place.id, place)
  }

  // ── Ctx ──
  drive(from: string, to: string): number {
    return this.#minutes.get(`${from}>${to}`) ?? 0
  }
  km(from: string, to: string): number {
    const a = this.#placeById.get(from), b = this.#placeById.get(to)
    return a && b ? haversine(a, b) : Infinity
  }
  driversNear(placeId: string, radiusKm = 30): number {
    const key = `${placeId}|${radiusKm}`
    let n = this.#near.get(key)
    if (n === undefined) {
      n = 0
      for (const d of this.drivers) if (this.km(placeId, d.homePlaceId) <= radiusKm) n++
      this.#near.set(key, n)
    }
    return n
  }
  openFrom(placeId: string): number {
    let n = 0
    for (const order of this.orders.values()) if (order.legs[0]!.pickup.placeId === placeId && order.deliveredAt.some((at) => at === null)) n++
    return n
  }
  openSingles(): Order[] {
    const out: Order[] = []
    for (const [gigId, action] of this.posts) {
      if (this.booked.has(gigId) || !this.isLive(gigId) || this.isPair(gigId)) continue
      const order = this.orders.get(action.stops[0]!.orderId)
      if (order && order.legs.length === 1 && !this.urgent.has(order.id) && !this.solo.has(order.id)) out.push(order)
    }
    return out
  }
  dealer(dealerId: string): { trust: number; lates: number } {
    return this.dealers.get(dealerId) ?? { trust: 0, lates: 0 }
  }

  // ── Events ──
  async handle(event: DeskEvent): Promise<void> {
    if (event.kind === "price_request") denoise(event.request, this.p)
    this.algo.learn(event, this, this.p)
    if (event.kind === "order_won") this.journal.push({ k: "won", id: event.order.id, opt: event.order.option })
    else if (event.kind === "order_lost") this.journal.push({ k: "lost", id: event.requestId })
    else if (event.kind === "gig_booked") this.journal.push({ k: "book", gig: event.gigId, at: event.at, fee: event.feeCents })
    else if (event.kind === "gig_dropped" || event.kind === "no_show") this.journal.push({ k: "drop", gig: event.gigId, at: event.at })
    else if (event.kind === "gig_expired") this.journal.push({ k: "exp", gig: event.gigId, at: event.at })
    if (event.kind === "price_request") this.quote(event.request)
    else if (event.kind === "order_won") await this.win(event.order)
    else if (event.kind === "order_changed") await this.change(event.order)
    else if (event.kind === "order_cancelled") {
      for (const books of [this.orders, this.legGigs]) books.delete(event.orderId)
      for (const gig of event.gigs ?? []) if (gig.outcome === "withdrawn" && this.isPair(gig.gigId)) await this.split(gig.gigId, false)
    }
    else if (event.kind === "visit_failed") await this.retry(event.orderId, event.leg, event.reason)
    else if (event.kind === "gig_expired") this.repost(event.gigId)
    else if (event.kind === "deadline_close") {
      if (this.p.lateFee! > 0) this.timers.push([event.lastPickupAt + 1, event.orderId])
      await this.raise(event.orderId)
    } else if (event.kind === "gig_booked") this.booked.add(event.gigId)
    else if (event.kind === "gig_dropped" || event.kind === "no_show") {
      this.booked.delete(event.gigId)
      if (this.isPair(event.gigId) && this.isLive(event.gigId)) await this.split(event.gigId, true)
    }
    else if (event.kind === "delivered") this.delivered(event.orderId, event.leg, event.at)
  }

  /** Asks the algorithm for prices. A decline is a quote far above list from level 4 (losing is free,
   * silence costs goodwill), and no quote at levels 1–3 (where every quote wins). */
  quote(request: PriceRequest): void {
    this.requests.set(request.id, request)
    const answer = this.algo.quote(request, this, this.p)
    const prices = typeof answer === "string" ? {} : Object.fromEntries(Object.entries(answer).filter(([, v]) => v !== undefined).map(([k, v]) => [k, Math.round(v!)]))
    if (Object.keys(prices).length > 0) {
      const quoted = request.options.find((option) => prices[option.kind] !== undefined)
      if (quoted) this.journal.push({ k: "quote", id: request.id, at: this.now, m: prices[quoted.kind]! / quoted.listPriceCents, x: reqX(this, request) })
      this.stats.quoted++
      this.outbox.push({ type: "quote", requestId: request.id, prices })
      return
    }
    const why = typeof answer === "string" ? answer : "no prices"
    this.stats.declined++
    this.stats.why[why] = (this.stats.why[why] ?? 0) + 1
    const first = request.options[0]!
    if (this.level >= 4) this.outbox.push({ type: "quote", requestId: request.id, prices: { [first.kind]: first.listPriceCents * 10 } })
  }

  /** Asks the algorithm for a fee schedule for some of the order's cars. Level 1 takes one fee only. */
  feesFor(order: Order, legs: number[]): FeeStep[] {
    const request = this.requests.get(order.id)!
    const cars = legs.length
    const fee = (request.referenceFeeCents * cars) / order.legs.length
    const schedule = this.algo.fees({ order, request, fee, cars, legs, urgent: this.urgent.has(order.id) }, this, this.p)
    return this.level === 1 ? schedule.slice(0, 1) : schedule
  }

  nextTimer(): number {
    return Math.min(this.timers.reduce((min, [at]) => Math.min(min, at), Infinity), this.pairTimers.reduce((min, [at]) => Math.min(min, at), Infinity), this.noteTimers.reduce((min, [at]) => Math.min(min, at), Infinity))
  }
  async fireTimers(): Promise<void> {
    for (let i = this.noteTimers.length - 1; i >= 0; i--) {
      const [at, orderId] = this.noteTimers[i]!
      if (at > this.now) continue
      this.noteTimers.splice(i, 1)
      const order = this.orders.get(orderId)
      if (order && !this.urgent.has(orderId) && this.gigsOf(orderId).some((gigId) => !this.booked.has(gigId))) {
        this.journal.push({ k: "note_warn", order: orderId, at: this.now })
        await this.raise(orderId)
      }
    }
    for (let i = this.pairTimers.length - 1; i >= 0; i--) {
      const [at, gigId] = this.pairTimers[i]!
      if (at > this.now) continue
      this.pairTimers.splice(i, 1)
      if (this.isPair(gigId) && this.isLive(gigId) && !this.booked.has(gigId)) {
        this.journal.push({ k: "pair_timeout", gig: gigId, at: this.now })
        await this.split(gigId, true)
      }
    }
    for (let i = this.timers.length - 1; i >= 0; i--) {
      const [at, orderId] = this.timers[i]!
      if (at > this.now) continue
      this.timers.splice(i, 1)
      const order = this.orders.get(orderId)
      if (!order || order.lastPickupAt > this.now) continue
      for (const gigId of this.gigsOf(orderId)) {
        if (!this.booked.has(gigId) && this.posts.has(gigId) && !this.isPair(gigId)) this.outbox.push({ type: "reprice", gigId, schedule: this.feesFor(order, legsOf(this.posts.get(gigId)!)) })
      }
    }
  }

  delivered(orderId: string, leg: number, at: number): void {
    this.legGigs.get(orderId)?.delete(leg)
    const order = this.orders.get(orderId)
    if (!order) return
    order.deliveredAt[leg] = at
    if (order.deliveredAt.every((time) => time !== null)) this.record(order)
  }

  /** Counts a finished order for its dealer: on time builds trust, late halves it. */
  record(order: Order): void {
    const dealer = this.dealer(order.dealerId)
    const late = Math.max(...order.deliveredAt.map((time) => time ?? Infinity)) > order.deadline
    this.dealers.set(order.dealerId, late ? { trust: Math.floor(dealer.trust / 2), lates: dealer.lates + 1 } : { trust: Math.min(25, dealer.trust + 1), lates: dealer.lates })
  }

  async win(order: Order): Promise<void> {
    if (!this.requests.has(order.id) || this.orders.has(order.id)) return
    this.orders.set(order.id, order)
    // A note that moves the pickup or the deadline makes the car go alone, and the urgent fees start 3 hours before
    // the last pickup time that the NOTE allows (the world's warning counts the option's deadline).
    const read = this.noteOf(order.id)
    if (read && (read.readyFrom !== null || read.deliverBy !== null)) this.solo.add(order.id)
    if (read && read.deliverBy !== null) {
      const drive = order.legs.reduce((sum, leg) => sum + this.drive(leg.pickup.placeId, leg.delivery.placeId), 0)
      if (read.deliverBy - drive < order.lastPickupAt) this.noteTimers.push([Math.max(this.now + 1, read.deliverBy - drive - 3 * HOUR), order.id])
    }
    // Real site hours in the note (noteHours): the car goes alone, and the urgent fees start 3 hours before the last
    // pickup minute inside those hours.
    const sites = this.sitesOf(order)
    if (sites) {
      this.solo.add(order.id)
      const leg = order.legs[0]!
      const real = lastSlot(sites.pickup, sites.delivery, this.drive(leg.pickup.placeId, leg.delivery.placeId), this.now, order.deadline)
      if (real !== null && real < order.lastPickupAt) this.noteTimers.push([Math.max(this.now + 1, real - 3 * HOUR), order.id])
    }
    if (await this.tryPair(order)) return
    await this.post(order, undelivered(order))
  }
  /** The real site hours of a one-car order whose note changes them (off unless noteHours is set), with what stopsFor needs. */
  sitesOf(order: Order): Sites | undefined {
    if (!(this.p.noteHours! > 0)) return undefined
    const sites = notedHours(this.requests.get(order.id)?.note?.text, order.legs)
    const leg = order.legs[0]!
    return sites ? { ...sites, now: this.now, minLeft: this.p.hoursMinLeftH! * HOUR, drive: this.drive(leg.pickup.placeId, leg.delivery.placeId) } : undefined
  }
  noteOf(orderId: string): { readyFrom: number | null; deliverBy: number | null } | undefined {
    const request = this.requests.get(orderId)
    return request ? readNote(request.note?.text, request.arrivedAt) : undefined
  }

  /** The open one-car gigs of other orders, and whether `order` can ride with one of them. Posts the pair if the algorithm wants it. */
  async tryPair(order: Order): Promise<boolean> {
    if (this.level < 3 || order.legs.length !== 1) return false
    const noteText = this.requests.get(order.id)?.note?.text ?? ""
    if (this.p.pairFlags! > 0 && (NOTE_PLATES.test(noteText) || NOTE_MANUAL.test(noteText))) return false // a pair is posted without plates or licence
    if (this.sitesOf(order)) return false
    await this.send() // so every earlier post has its gig id
    let best: { gigId: string; chain: Order[]; schedule: FeeStep[]; score: number } | undefined
    for (const [gigId, action] of this.posts) {
      if (this.booked.has(gigId) || !this.isLive(gigId) || action.stops.some((stop) => stop.withPlates) || action.audience.manualLicence) continue
      const others = [...new Set(action.stops.map((stop) => stop.orderId))].map((id) => this.orders.get(id))
      if (others.length !== 1 || others.some((o) => !o || o.id === order.id || o.legs.length !== 1 || this.urgent.has(o.id) || this.solo.has(o.id))) continue
      for (const chain of [[order, ...(others as Order[])], [...(others as Order[]), order]]) {
        let drive = 0, slackMin = Infinity, typical = 0
        let t = this.now
        chain.forEach((o, k) => {
          const leg = o.legs[0]!
          if (k > 0) { const between = this.drive(chain[k - 1]!.legs[0]!.delivery.placeId, leg.pickup.placeId); drive += between; t += between }
          t = Math.max(t, leg.pickup.window.from)
          slackMin = Math.min(slackMin, o.lastPickupAt - t)
          const d = this.drive(leg.pickup.placeId, leg.delivery.placeId)
          drive += d
          t += d
          typical += this.requests.get(o.id)!.referenceFeeCents
        })
        if (drive > 12 * HOUR || slackMin < 0) continue // the rules: a multi-car gig plans at most 12 hours of driving
        const joinKm = this.km(chain[0]!.legs[0]!.delivery.placeId, chain[1]!.legs[0]!.pickup.placeId)
        const backKm = this.km(chain[1]!.legs[0]!.delivery.placeId, chain[0]!.legs[0]!.pickup.placeId)
        const answer = this.algo.pair({ orders: chain, typical, driveMin: drive, joinKm, backKm, slackMin }, this, this.p)
        if (answer && (!best || answer.score > best.score)) best = { gigId, chain, schedule: answer.schedule, score: answer.score }
      }
    }
    if (!best) return false
    const stops = best.chain.flatMap((o) => withoutWindows(stopsFor(o, [0], this.requests.get(o.id)!.note, FIRST_TRY, this.noteOf(o.id)), this.now))
    const audience = { experienced: best.chain.some((o) => o.legs[0]!.car.premium), manualLicence: false }
    const results = await this.world.act([{ type: "withdraw", gigId: best.gigId }])
    if (!results[0]?.ok) return false // a driver booked it in the same minute
    this.journal.push({ k: "wd", gig: best.gigId, at: this.now })
    const others = best.chain.filter((o) => o.id !== order.id)
    for (const o of others) this.legGigs.delete(o.id)
    const post: PostAction = { type: "post", stops, audience, schedule: best.schedule }
    const posted = await this.world.act([post])
    if (posted[0]?.ok) {
      this.readResults([post], posted)
      if (this.p.pairHoldH! > 0) this.pairTimers.push([Math.max(this.now + 30, this.now + this.p.pairHoldH! * HOUR), posted[0].id])
      this.journal.push({ k: "pair", gig: posted[0].id, orders: best.chain.map((o) => o.id), at: this.now, typ: best.chain.reduce((sum, o) => sum + this.requests.get(o.id)!.referenceFeeCents, 0) })
      return true
    }
    this.journal.push({ k: "pair_refused", orders: best.chain.map((o) => o.id), at: this.now, why: posted[0] && !posted[0].ok ? posted[0].reason : "" })
    for (const o of others) await this.post(o, undelivered(o))
    return false
  }

  /** Takes a gig with cars of several orders apart: every order gets its own gig again. */
  async split(gigId: string, withdraw: boolean): Promise<void> {
    const action = this.posts.get(gigId)
    if (!action) return
    if (withdraw) {
      await this.send()
      const results = await this.world.act([{ type: "withdraw", gigId }])
      if (!results[0]?.ok) return
    }
    for (const orderId of new Set(action.stops.map((stop) => stop.orderId))) {
      const order = this.orders.get(orderId)
      const legs = this.legGigs.get(orderId)
      if (legs) for (const [leg, id] of legs) if (id === gigId) legs.delete(leg)
      this.solo.add(orderId)
      if (order && undelivered(order).length > 0 && this.gigsOf(orderId).length === 0) await this.post(order, undelivered(order))
    }
  }
  isPair(gigId: string): boolean {
    const action = this.posts.get(gigId)
    return !!action && new Set(action.stops.map((stop) => stop.orderId)).size > 1
  }
  isLive(gigId: string): boolean {
    const action = this.posts.get(gigId)
    return !!action && action.stops.some(({ orderId, leg }) => this.legGigs.get(orderId)?.get(leg) === gigId)
  }

  async change(order: Order): Promise<void> {
    if (!this.orders.has(order.id)) return
    this.orders.set(order.id, order)
    if (await this.withdraw(order.id)) await this.post(order, undelivered(order))
  }

  /** Posts a gig again when one of its windows ended before a driver booked it, without its own stop windows. */
  repost(gigId: string): void {
    const action = this.posts.get(gigId)
    if (!action || !action.stops.some(({ orderId, leg }) => this.legGigs.get(orderId)?.get(leg) === gigId)) return
    if (this.isPair(gigId)) { void this.split(gigId, false); return }
    for (const { orderId, leg } of action.stops) this.legGigs.get(orderId)?.delete(leg)
    const order = this.orders.get(action.stops[0]!.orderId)
    if (!order) return
    const sites = this.sitesOf(order)
    // With real site hours from the note, the next day's slot; else without its own stop windows.
    const stops = sites ? stopsFor(order, legsOf(action), this.requests.get(order.id)!.note, { pickupFrom: 0, manualLicence: action.audience.manualLicence, plates: action.stops.some((stop) => stop.withPlates) }, this.noteOf(order.id), sites) : withoutWindows(action.stops, Infinity)
    this.outbox.push({ ...action, stops, schedule: this.feesFor(order, legsOf(action)) })
  }

  /** After a deadline warning, the order's unbooked gigs get the algorithm's urgent fees (pairs are split first). */
  async raise(orderId: string): Promise<void> {
    const order = this.orders.get(orderId)
    if (!order) return
    this.urgent.add(orderId)
    await this.sendPostOf(orderId)
    for (const gigId of this.gigsOf(orderId)) if (this.isPair(gigId) && !this.booked.has(gigId)) await this.split(gigId, true)
    for (const gigId of this.gigsOf(orderId)) {
      if (this.isPair(gigId)) continue
      if (!this.booked.has(gigId)) this.outbox.push({ type: "reprice", gigId, schedule: this.feesFor(order, legsOf(this.posts.get(gigId)!)) })
    }
  }

  async retry(orderId: string, leg: number, reason: string): Promise<void> {
    const order = this.orders.get(orderId)
    if (!order) return
    this.legGigs.get(orderId)?.delete(leg)
    const carNotThere = reason === "not_ready" || reason === "closed"
    const pickupFrom = carNotThere ? retryFrom(order, this.requests.get(orderId)!, leg, this.now) : 0
    await this.post(order, [leg], { pickupFrom, manualLicence: reason === "licence", plates: reason === "no_plates" })
  }

  async post(order: Order, legs: number[], retry = FIRST_TRY): Promise<void> {
    // A premium car needs an experienced driver (the fine is €150 a car). The note often says what the first visit
    // would otherwise find out the hard way: no plates (bring transfer plates) or a manual gearbox (needs that licence).
    const text = this.requests.get(order.id)!.note?.text ?? ""
    if (text && (NOTE_PLATES.test(text) || NOTE_MANUAL.test(text))) retry = { ...retry, plates: retry.plates || NOTE_PLATES.test(text), manualLicence: retry.manualLicence || NOTE_MANUAL.test(text) }
    const audience = { experienced: order.legs.some((leg) => leg.car.premium), manualLicence: retry.manualLicence }
    const stops = withoutWindows(stopsFor(order, legs, this.requests.get(order.id)!.note, retry, this.noteOf(order.id), this.sitesOf(order)), this.now)
    this.outbox.push({ type: "post", stops, audience, schedule: this.feesFor(order, legs) })
    if (legs.length === 1) return
    // A trade-in over the 12-hour limit goes as one gig per car.
    await this.send()
    if (this.gigsOf(order.id).length === 0) for (const leg of legs) await this.post(order, [leg], retry)
  }

  gigsOf(orderId: string): string[] {
    return [...new Set(this.legGigs.get(orderId)?.values())]
  }

  carry(action: PostAction, gigId: string): void {
    for (const { orderId, leg } of action.stops) this.legGigs.set(orderId, (this.legGigs.get(orderId) ?? new Map()).set(leg, gigId))
    this.posts.set(gigId, action)
    const order = this.orders.get(action.stops[0]!.orderId), request = this.requests.get(action.stops[0]!.orderId)
    if (!order || !request) return
    const legs = legsOf(action)
    const orderIds = [...new Set(action.stops.map((stop) => stop.orderId))]
    const typical = orderIds.length > 1 ? orderIds.reduce((sum, id) => sum + (this.requests.get(id)?.referenceFeeCents ?? 0), 0) : (request.referenceFeeCents * legs.length) / order.legs.length
    const ready = action.stops[0]!.window?.from ?? order.legs[legs[0]!]!.pickup.window.from
    this.journal.push({ k: "post", gig: gigId, order: order.id, at: this.now, typ: typical, lp: order.lastPickupAt, ready, urgent: this.urgent.has(order.id) ? 1 : 0, sched: action.schedule, x: gigX(this, legs.map((leg) => order.legs[leg]!), typical, true) })
  }

  async withdraw(orderId: string): Promise<boolean> {
    await this.sendPostOf(orderId)
    const gigs = this.gigsOf(orderId)
    if (gigs.some((gigId) => this.booked.has(gigId))) return false
    for (const gigId of gigs.filter((id) => this.isPair(id))) await this.split(gigId, true) // the partner gets its own gig again
    for (const gigId of this.gigsOf(orderId)) this.outbox.push({ type: "withdraw", gigId })
    this.legGigs.delete(orderId)
    return true
  }

  async sendPostOf(orderId: string): Promise<void> {
    if (this.outbox.some((action) => action.type === "post" && action.stops[0]!.orderId === orderId)) await this.send()
  }

  async send(): Promise<void> {
    const actions = this.outbox.splice(0)
    if (actions.length > 0) this.readResults(actions, await this.world.act(actions))
  }

  readResults(actions: Action[], results: ActionResult[]): void {
    actions.forEach((action, i) => {
      if (action.type === "post" && results[i]?.ok) this.carry(action, results[i]!.id)
      else if (action.type === "reprice" && results[i]?.ok) this.journal.push({ k: "reprice", gig: action.gigId, at: this.now, sched: action.schedule })
      else if (action.type === "withdraw" && results[i]?.ok) this.journal.push({ k: "wd", gig: action.gigId, at: this.now })
    })
  }

  /** Rebuilds the books from the server after a restart in the final, then answers what was missed. */
  async rejoin(snapshot: DeskSnapshot, history: DeskEvent[]): Promise<void> {
    const posted = Map.groupBy(snapshot.gigs, (gig) => gig.stops[0]!.orderId)
    for (const gig of snapshot.gigs) if (["booked", "working", "done"].includes(gig.status)) this.booked.add(gig.id)
    for (const gig of snapshot.gigs) if (["open", "booked", "working"].includes(gig.status)) this.carry({ type: "post", stops: gig.stops, audience: gig.audience, schedule: gig.schedule }, gig.id)
    for (const event of history) {
      if (event.kind === "price_request") { denoise(event.request, this.p); this.requests.set(event.request.id, event.request) }
      if (event.kind === "deadline_close") this.urgent.add(event.orderId)
      this.algo.learn(event, this, this.p) // the algorithm rebuilds its own estimates too
    }
    for (const order of snapshot.orders) if (this.requests.has(order.id) && order.status !== "cancelled") this.orders.set(order.id, order)
    const finished = [...this.orders.values()].filter((order) => order.deliveredAt.every((time) => time !== null))
    for (const order of finished.sort((a, b) => Math.max(...(a.deliveredAt as number[])) - Math.max(...(b.deliveredAt as number[])))) this.record(order)
    for (const order of this.orders.values()) if (order.status === "waiting" && this.gigsOf(order.id).length === 0) await this.post(order, undelivered(order))
    for (const event of history) {
      const order = "orderId" in event ? this.orders.get(event.orderId) : undefined
      if (!order || event.kind !== "visit_failed" || order.deliveredAt[event.leg] !== null) continue
      const later = (posted.get(order.id) ?? []).filter((gig) => gig.postedAt >= event.at && gig.id !== event.gigId)
      if (!later.some((gig) => gig.stops.some((stop) => stop.leg === event.leg))) await this.retry(order.id, event.leg, event.reason)
    }
    for (const request of snapshot.openRequests) this.quote(request)
  }
}

// ─── Playing a week ────────────────────────────────────────────────────────────────────────

async function deskFor(world: World, level: number, now: number, algo: Algo, p: Record<string, number>): Promise<Desk> {
  const [map, drivers] = await Promise.all([world.client.map(), world.roster()])
  return new Desk(world, level, now, algo, p, map, drivers)
}

/** Practice or ranking run: steps from one event that needs an answer to the next. */
export async function playPractice(world: World, level: number, algo: Algo, p: Record<string, number>, quiet = false): Promise<Desk> {
  const { now, endsAt } = await world.snapshot()
  const desk = await deskFor(world, level, now, algo, p)
  while (desk.now < endsAt) {
    const day = Math.floor(desk.now / DAY)
    const actions = desk.outbox.splice(0)
    const step = await world.advance({ untilEvent: WAKE_ON, max: Math.min(endsAt, (day + 1) * DAY, Math.max(desk.now + 1, desk.nextTimer())), actions })
    desk.readResults(actions, step.results)
    desk.now = step.now
    for (const event of step.events) await desk.handle(event)
    await desk.fireTimers()
    if (!quiet && Math.floor(desk.now / DAY) > day) report(WEEKDAYS[day % 7]!, await world.score())
  }
  return desk
}

// What the algorithm has learned this week (price filter, outage belief) is not in the server's events: the quotes we
// made are not there. In the final it is saved every few seconds, so a restart goes on with it instead of starting cold.
// FINAL_STATE=<folder> moves the files, FINAL_STATE=off switches this off. A failure here never reaches the desk.
const STATE_DIR = process.env.FINAL_STATE ?? new URL("../../runs/final_state/", import.meta.url).pathname
function saveMemory(worldId: string, desk: Desk): void {
  if (STATE_DIR === "off") return
  try {
    mkdirSync(STATE_DIR, { recursive: true })
    const file = join(STATE_DIR, `${worldId}.json`)
    writeFileSync(file + ".tmp", JSON.stringify({ now: desk.now, memory: desk.memory }))
    renameSync(file + ".tmp", file)
  } catch {}
}
function loadMemory(worldId: string, desk: Desk): boolean {
  if (STATE_DIR === "off") return false
  try {
    const saved = JSON.parse(readFileSync(join(STATE_DIR, `${worldId}.json`), "utf8")) as { now: number; memory: Record<string, any> }
    if (!(saved.now <= desk.now) || typeof saved.memory !== "object" || saved.memory === null) return false
    Object.assign(desk.memory, saved.memory)
    return true
  } catch { return false }
}

/** The final (or a test final): rebuild from the server, then answer the live stream. */
export async function playFinal(world: World, algo: Algo, overrides: Record<string, number>): Promise<void> {
  const history = await world.events()
  const snapshot = await world.snapshot()
  if (snapshot.now >= snapshot.endsAt) return
  const level = (await world.client.worlds()).find((s) => s.worldId === world.id)?.level ?? 8
  const desk = await deskFor(world, level, snapshot.now, algo, paramsFor(algo, overrides))
  // Loaded before the rebuild: rejoin() replays the answers, and those to quotes still waiting in the saved state count.
  if (loadMemory(world.id, desk)) console.log(`Learned state of this week loaded (${STATE_DIR}).`)
  await desk.rejoin(snapshot, history)
  await desk.send()
  let saved = Date.now()
  for await (const event of world.stream({ after: history.at(-1)?.seq ?? -1, idleMs: 1000 })) {
    const day = Math.floor(desk.now / DAY)
    desk.now = event === null ? (await world.client.final()).now : Math.max(desk.now, event.at)
    if (event !== null) await desk.handle(event)
    await desk.fireTimers()
    await desk.send()
    if (Date.now() - saved >= 3000) { saveMemory(world.id, desk); saved = Date.now() }
    if (Math.floor(desk.now / DAY) > day) report(WEEKDAYS[day % 7]!, await world.score())
    if (desk.now >= snapshot.endsAt) return
  }
}

/** Plays one whole practice week (or ranking run) and returns its score. Waits for a free practice slot. */
export async function play(client: Client, level: number, algo: Algo, overrides: Record<string, number> = {}, opts: { seed?: string; board?: boolean; quiet?: boolean; onWorld?: (id: string) => void } = {}) {
  const p = paramsFor(algo, overrides)
  let world: World | undefined
  while (!world) {
    world = await client.create(level as 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8, { seed: opts.seed, board: opts.board }).catch(async (error: unknown) => {
      if (error instanceof SpreadError && error.status === 409 && !opts.board) return sleep(5000).then(() => undefined)
      throw error
    })
  }
  opts.onWorld?.(world.id)
  try {
    const desk = await playPractice(world, level, algo, p, opts.quiet ?? true)
    return { worldId: world.id, params: p, score: await world.score(), stats: desk.stats, journal: desk.journal }
  } catch (error) {
    if (!opts.board) await world.delete().catch(() => {}) // a practice world left unfinished holds a slot
    throw error
  }
}

/** Your copy of the final that is set or runs now. Waits while none is set. */
export async function nextFinal(client: Client): Promise<World> {
  for (let said = false; ; said = true) {
    const set = await client.final().catch((error: unknown) => {
      if (error instanceof SpreadError && error.status === 404) return null
      throw error
    })
    const world = set ? client.world(set.worldId) : null
    if (world) {
      const snapshot = await world.snapshot()
      if (snapshot.now < snapshot.endsAt) return world
    }
    if (!said) console.log("No final is set. Waiting: the organisers set a test final 15 minutes before its start, and the final 30 minutes before.")
    await sleep(10_000)
  }
}

export function report(label: string, score: Score): void {
  const euros = (cents: number) => (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).padStart(11)
  const pct = (share: number, w: number) => `${(100 * share).toFixed(1)}%`.padStart(w)
  console.log(`${label.padEnd(9)}  margin €${euros(score.marginCents)}  revenue €${euros(score.revenueCents)}  ${String(score.wonOrders).padStart(4)} orders  ${pct(score.onTimeShare, 6)} on time  ${pct(score.undeliveredShare, 5)} not delivered`)
}

// ─── Mechanics shared with the kit's starter ───────────────────────────────────────────────

const sleep = (ms: number) => new Promise<void>((done) => setTimeout(done, ms))

function haversine(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180, dLat = (b.lat - a.lat) * r, dLon = (b.lon - a.lon) * r
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLon / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}

/** When to try a car again after it was not ready or the site was closed. */
function retryFrom(order: Order, request: PriceRequest, leg: number, now: number): number {
  const promised = request.options.find((option) => option.kind === order.option)?.deadline ?? order.deadline
  const delay = Math.max(0, order.deadline - promised)
  return Math.max(now + 2 * HOUR, order.legs[leg]!.pickup.window.from + delay)
}

const undelivered = (order: Order): number[] => order.legs.map((_, leg) => leg).filter((leg) => order.deliveredAt[leg] === null)
const legsOf = (action: PostAction): number[] => [...new Set(action.stops.filter((stop) => stop.kind === "pickup").map((stop) => stop.leg))]
const withoutWindows = (stops: StopRef[], before: number): StopRef[] => stops.map((stop) => (stop.window && stop.window.to < before ? { ...stop, window: undefined } : stop))

/** A pickup and a delivery for each leg; a charging stop for an EV under 30%; windows narrowed by the note. */
type Sites = { pickup: Leg["pickup"]["hours"]; delivery: Leg["delivery"]["hours"]; now: number; minLeft: number; drive: number }
function stopsFor(order: Order, legs: number[], note: Note | null, retry: Retry, read?: { readyFrom: number | null; deliverBy: number | null }, sites?: Sites): StopRef[] {
  return legs.flatMap((leg): StopRef[] => {
    const { car, pickup, delivery } = order.legs[leg]!
    if (sites) {
      // Real site hours from the note: one day's slot at a time. The gig expires when the slot ends and is posted
      // again with the next day's, so no driver plans a visit in the hours the request wrongly shows open.
      const lowCharge = car.electric && car.chargePercent !== null && car.chargePercent < 30
      const travel = sites.drive + (retry.plates ? 30 : 0) + (lowCharge ? 40 : 0)
      const start = Math.max(sites.now, pickup.window.from, retry.pickupFrom, read?.readyFrom ?? 0)
      let slot = nextSlot(sites.pickup, sites.delivery, travel, start, sites.minLeft)
      if (slot && pickup.privateAddress) slot = slot.to < pickup.window.from || slot.from > pickup.window.to ? null : { from: Math.max(slot.from, pickup.window.from), to: Math.min(slot.to, pickup.window.to) }
      if (slot) {
        const first: StopRef = { orderId: order.id, leg, kind: "pickup", withPlates: retry.plates, withCharging: lowCharge }
        const second: StopRef = { orderId: order.id, leg, kind: "delivery" }
        return [pickup.privateAddress ? first : { ...first, window: slot }, sites.delivery ? { ...second, window: { from: Math.max(slot.from + travel, delivery.window.from), to: slot.to + travel } } : second]
      }
    }
    const noted = windowFromNote(note, pickup.window, "pickup")
    const start = Math.max(noted.from, retry.pickupFrom, read?.readyFrom ?? 0)
    const pickupWindow = { from: start, to: Math.max(noted.to, start) }
    const deliveryBase = { from: delivery.window.from, to: Math.max(delivery.window.from, order.deadline) }
    const kitWindow = windowFromNote(note, deliveryBase, "delivery")
    const deliveryWindow = read?.deliverBy != null && read.deliverBy > kitWindow.from ? { from: kitWindow.from, to: Math.min(kitWindow.to, read.deliverBy) } : kitWindow
    const lowBattery = car.electric && car.chargePercent !== null && car.chargePercent < 30
    const first: StopRef = { orderId: order.id, leg, kind: "pickup", withPlates: retry.plates, withCharging: lowBattery }
    const second: StopRef = { orderId: order.id, leg, kind: "delivery" }
    return [narrower(first, pickupWindow, pickup.window), narrower(second, deliveryWindow, deliveryBase)]
  })
}

const narrower = (stop: StopRef, window: TimeWindow, base: TimeWindow): StopRef => (window.from > base.from || window.to < base.to ? { ...stop, window } : stop)

// The kit's keyword note reader: clock times near "after/before" words, and opening-hour ranges.
const AFTER = /jälkeen|alkaen|aikaisintaan|\bafter\b|\bfrom\b|earliest|not before|ei ennen|valmis|\bready\b|efter|tidigast|inte före|klar/
const BEFORE = /ennen|mennessä|viim|\bbefore\b|\bby\b|latest|före|senast/
const DELIVERY = /toimit|perillä|perille|vastaanot|kohde|deliver|arrive|destination|receiv|leverera|leverans|framme|mottag/
const CLOCK = /(?:klo|kl\.?)\s*(\d{1,2})(?:[.:](\d{2}))?|\b(\d{1,2})[.:](\d{2})\b/g
const RANGE = /\b(\d{1,2})(?:[.:](\d{2}))?\s*[-–]\s*(\d{1,2})(?:[.:](\d{2}))?\b/g

function windowFromNote(note: Note | null, window: TimeWindow, stop: "pickup" | "delivery"): TimeWindow {
  if (!note) return window
  let text = note.text.toLowerCase()
  if (DELIVERY.test(text) !== (stop === "delivery")) return window
  const minutes = (hour: number, minute: number): number | null => (hour > 24 || minute > 59 ? null : hour * HOUR + minute)
  const dayStart = (t: number) => Math.floor(t / DAY) * DAY
  let { from, to } = window
  for (const match of text.matchAll(RANGE)) {
    const opens = minutes(Number(match[1]), Number(match[2] ?? 0))
    const closes = minutes(Number(match[3]), Number(match[4] ?? 0))
    if (opens === null || closes === null || opens >= closes) continue
    from = Math.max(from, dayStart(from) + opens)
    to = Math.min(to, dayStart(to) + closes)
  }
  text = text.replace(RANGE, " ")
  for (const match of text.matchAll(CLOCK)) {
    const m = minutes(Number(match[1] ?? match[3]), Number(match[2] ?? match[4] ?? 0))
    if (m === null) continue
    const time = dayStart(window.from) + m
    const around = text.slice(Math.max(0, match.index - 16), match.index + match[0].length + 16)
    if (AFTER.test(around)) from = Math.max(from, time)
    else if (BEFORE.test(around)) to = Math.min(to, time)
  }
  return from <= to ? { from, to } : window
}
