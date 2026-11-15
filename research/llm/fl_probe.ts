// Featherless (OpenAI-compatible) probe: speed, parallel calls, and whether a one-letter answer with
// logprobs gives choice probabilities.   bun research/llm/fl_probe.ts MODEL [N] [PARALLEL] [extra JSON body]
const model = process.argv[2]!
const N = Number(process.argv[3] ?? 12)
const PAR = Number(process.argv[4] ?? 4)
const extra = process.argv[5] ? JSON.parse(process.argv[5]) : {}
const system =
  "You are the dispatcher of a car transport firm in Finland, in a week with a third of the usual drivers. " +
  "Dealers ask for a price; one competitor quotes too; the cheaper acceptable offer wins. For every car won we must find a freelance driver in time. " +
  "The week's score is the margin: prices of delivered cars minus driver fees minus refunds for late cars. " +
  "If fewer than 90% of the week's orders arrive on time, the whole week scores zero. " +
  "The card shows the model's numbers for this request and candidate prices. Choose the model's price unless the card gives a real reason. " +
  "Answer with ONE letter and nothing else: A = clearly cheaper, B = a little cheaper, C = the model's price, D = a little dearer, E = clearly dearer, F = decline the car."
function card(i: number) {
  const hot = i % 3 === 0 // every third card: we win far more than forecast near the pickup
  return {
    now: "Wed 11:" + String(10 + i).padStart(2, "0"),
    request: { dealer: "D0" + (1 + (i % 7)), cars: [{ from: "Tampere", to: "Oulu", readyAt: "Wed 12:00", privatePickup: false, privateDelivery: false, premium: false, electric: i % 4 === 0 }], driveHours: 5.9, note: i % 2 ? "Auto valmis vasta huomenna klo 10" : "", options: [{ kind: "next_day", deadline: "Thu 20:00", listPriceEur: 412, chanceDriverBooksInTime: 0.96, ordersDueThatDay: 20 + i, dayIsFullAt: 31 }] },
    model: { expectedDriverFeeEur: 281, typicalFeeEur: 268, capacityCostEur: 28, weekPriceLevel: 0.12, dealerOnTimeOrdersWithUs: 9, dealerLateOrdersWithUs: 0 },
    candidates: { A: { priceEur: 536, winChance: 0.71, expectedProfitEur: 161 }, B: { priceEur: 552, winChance: 0.66, expectedProfitEur: 160 }, C: { priceEur: 569, winChance: 0.61, expectedProfitEur: 159 }, D: { priceEur: 585, winChance: 0.55, expectedProfitEur: 152 }, E: { priceEur: 602, winChance: 0.49, expectedProfitEur: 144 } },
    today: { all: "19 won of 41, forecast 19.5", within80kmOfPickup: hot ? "9 won of 10, forecast 4.6" : "4 won of 10, forecast 4.6" },
    desk: { ordersFinished: 120, ofThemLate: 6, onTimeShare: 0.95, ordersWonSoFar: 210, gigsWithoutDriver: 31, ofThemUrgent: 3, driversWithin30kmOfPickup: 6, pickupTownFull: false, driversInWorld: 310 },
  }
}
async function ask(i: number) {
  const t = performance.now()
  try {
    const r = await fetch("https://api.featherless.ai/v1/chat/completions", {
      method: "POST",
      signal: AbortSignal.timeout(30000),
      headers: { Authorization: "Bearer " + process.env.FEATHERLESS_API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages: [{ role: "system", content: system }, { role: "user", content: JSON.stringify(card(i)) }], max_tokens: 4, temperature: 0, logprobs: true, top_logprobs: 8, ...extra }),
    })
    const j = (await r.json()) as any
    const choice = j.choices?.[0]
    const top = choice?.logprobs?.content?.[0]?.top_logprobs as { token: string; logprob: number }[] | undefined
    return { ms: Math.round(performance.now() - t), status: r.status, text: JSON.stringify(choice?.message?.content ?? "").slice(0, 30), reasoning: (choice?.message?.reasoning_content ?? choice?.message?.reasoning ?? "").length, probs: top ? top.slice(0, 4).map((x) => x.token.trim() + ":" + Math.exp(x.logprob).toFixed(2)).join(" ") : "no logprobs", tok: j.usage?.prompt_tokens, err: r.status === 200 ? "" : JSON.stringify(j).slice(0, 220) }
  } catch (e) {
    return { ms: Math.round(performance.now() - t), status: 0, text: "", reasoning: 0, probs: "", tok: 0, err: String(e).slice(0, 100) }
  }
}
const out: Awaited<ReturnType<typeof ask>>[] = new Array(N)
let next = 0
const t0 = performance.now()
await Promise.all(Array.from({ length: PAR }, async () => { while (next < N) { const i = next++; out[i] = await ask(i) } }))
const ok = out.filter((o) => o.status === 200)
const ms = ok.map((o) => o.ms).sort((a, b) => a - b)
console.log(model + " | parallel " + PAR + " | ok " + ok.length + "/" + N + " | wall " + ((performance.now() - t0) / 1000).toFixed(1) + " s | ms p50 " + (ms[Math.floor(ms.length / 2)] ?? "-") + " max " + (ms.at(-1) ?? "-") + " | tokens " + (ok[0]?.tok ?? "-"))
for (const o of out.slice(0, 4)) console.log("   " + o.status + " " + o.ms + " ms  text " + o.text + "  reasoning chars " + o.reasoning + "  " + o.probs + "  " + o.err)
const errs = out.filter((o) => o.status !== 200)
if (errs.length) console.log("   errors: " + [...new Set(errs.map((e) => e.status + " " + e.err))].slice(0, 2).join(" || "))
