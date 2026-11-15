// JEV latency, rate limit and repeatability probe. bun research/llm/jev_probe.ts N PARALLEL
const N = Number(process.argv[2] ?? 200)
const PAR = Number(process.argv[3] ?? 8)
let seed = 12345
const rnd = () => {
  seed = (seed * 1103515245 + 12345) % 2147483648
  return seed / 2147483648
}
const towns = ["Helsinki", "Tampere", "Oulu", "Turku", "Kuopio", "Vaasa", "Lahti", "Joensuu", "Rovaniemi", "Pori"]
const notes = ["", "", "Auto valmis vasta huomenna klo 10", "Bilen måste vara framme senast torsdag kl 14", "Keys at the front desk", "Maksu ensin, luovutus ylihuomenna puoli kolme", "Kiitos!"]
const MARKUPS = [1.28, 1.34, 1.4, 1.48, 1.58]
const KEYS = ["m_1_28", "m_1_34", "m_1_40", "m_1_48", "m_1_58", "decline"]
const criteria = { m_1_28: "cheapest candidate", m_1_34: "second", m_1_40: "middle", m_1_48: "fourth", m_1_58: "dearest candidate", decline: "do not take this car" }

function card(i: number) {
  const list = 200 + Math.round(rnd() * 400)
  const fee = Math.round(list * (0.55 + rnd() * 0.25))
  const cap = 10 + Math.round(rnd() * 30)
  const peak = 1.28 + rnd() * 0.3 // where the win curve bends: the best candidate moves between cards
  const candidates: Record<string, unknown> = {}
  const ev: number[] = []
  MARKUPS.forEach((m, k) => {
    const win = 1 / (1 + Math.exp((m - peak) * 14))
    const profit = Math.round(win * (m * list - fee - cap))
    ev.push(profit)
    candidates[KEYS[k]!] = { priceEur: Math.round(m * list), winChance: Number(win.toFixed(2)), expectedProfitEur: profit }
  })
  const state = {
    request: { id: "R" + i, dealer: "D0" + (1 + Math.floor(rnd() * 8)), lane: towns[Math.floor(rnd() * 10)] + " -> " + towns[Math.floor(rnd() * 10)], driveHours: Number((1 + rnd() * 7).toFixed(1)), listPriceEur: list, typicalFeeEur: Math.round(fee * 0.95), note: notes[Math.floor(rnd() * notes.length)] },
    model: { expectedFeeEur: fee, bookChance: Number((0.85 + rnd() * 0.14).toFixed(2)), capacityCostEur: cap, dealerTrust: Math.floor(rnd() * 25) },
    candidates,
    load: { ordersDueThatDay: Math.floor(rnd() * 40), dayCap: 34, driversNearPickup: Math.floor(rnd() * 12), openOrdersFromTown: Math.floor(rnd() * 20) },
  }
  return { best: ev.indexOf(Math.max(...ev)), state }
}

type Answer = { ms: number; status: number; pick?: string; conf?: number; tok: number; cost: number; err: string }
async function ask(state: unknown): Promise<Answer> {
  const t = performance.now()
  try {
    const r = await fetch("https://openrouter.ai/api/alpha/decisions", {
      method: "POST",
      signal: AbortSignal.timeout(10000),
      headers: { Authorization: "Bearer " + process.env.OPENROUTER_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ model: "~typesafe/jev-latest", state, questions: { pick: { type: "choice", instructions: "You are a car transport dispatcher in a driver shortage. Pick the price that earns the most this week while keeping at least 90% of orders on time.", criteria } } }),
    })
    const j = (await r.json()) as any
    return { ms: performance.now() - t, status: r.status, pick: j.answers?.pick?.choice, conf: j.answers?.pick?.confidence, tok: j.usage?.input_tokens ?? 0, cost: j.usage?.cost ?? 0, err: r.status === 200 ? "" : JSON.stringify(j).slice(0, 200) }
  } catch (e) {
    return { ms: performance.now() - t, status: 0, tok: 0, cost: 0, err: String(e).slice(0, 120) }
  }
}

const cards = Array.from({ length: N }, (_, i) => card(i))
const out: Answer[] = new Array(N)
let next = 0
const t0 = performance.now()
await Promise.all(
  Array.from({ length: PAR }, async () => {
    while (next < N) {
      const i = next++
      out[i] = await ask(cards[i]!.state)
    }
  }),
)
const wall = (performance.now() - t0) / 1000
const okIdx = out.map((o, i) => (o.status === 200 ? i : -1)).filter((i) => i >= 0)
const ms = okIdx.map((i) => out[i]!.ms).sort((a, b) => a - b)
const q = (p: number) => Math.round(ms[Math.min(ms.length - 1, Math.floor(p * ms.length))] ?? 0)
const agree = okIdx.filter((i) => KEYS.indexOf(out[i]!.pick ?? "") === cards[i]!.best).length
const picks: Record<string, number> = {}
const bests: Record<string, number> = {}
for (const i of okIdx) picks[out[i]!.pick ?? "?"] = (picks[out[i]!.pick ?? "?"] ?? 0) + 1
for (const c of cards) bests[KEYS[c.best]!] = (bests[KEYS[c.best]!] ?? 0) + 1
const sum = (f: (o: Answer) => number) => okIdx.reduce((s, i) => s + f(out[i]!), 0)
console.log("N " + N + " parallel " + PAR + ": ok " + okIdx.length + ", wall " + wall.toFixed(1) + " s (" + (N / wall).toFixed(1) + "/s), ms p50 " + q(0.5) + " p90 " + q(0.9) + " p95 " + q(0.95) + " p99 " + q(0.99) + " max " + Math.round(ms.at(-1) ?? 0))
console.log("tokens in " + Math.round(sum((o) => o.tok) / okIdx.length) + " avg, cost total $" + sum((o) => o.cost).toFixed(4))
console.log("pick = max expected profit: " + agree + "/" + okIdx.length + ", mean confidence " + (sum((o) => o.conf ?? 0) / okIdx.length).toFixed(2))
console.log("picks", JSON.stringify(picks), "true best", JSON.stringify(bests))
const errs = out.filter((o) => o.status !== 200)
if (errs.length) console.log("errors " + errs.length, errs.slice(0, 3).map((e) => e.status + " " + e.err))
const again = await Promise.all(cards.slice(0, 20).map((c) => ask(c.state)))
console.log("repeat of 20: same pick " + again.filter((a, i) => a.pick === out[i]!.pick).length + ", same confidence " + again.filter((a, i) => a.conf === out[i]!.conf).length)
