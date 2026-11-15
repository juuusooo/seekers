// One JEV call: learn the answer shape and timing. Run: bun research/llm/jev1.ts (after loading .env)
const state = {
  request: { dealer: "D03", lane: "Tampere -> Oulu", driveHours: 5.9, listPriceEur: 412, typicalFeeEur: 268, note: "Auto valmis vasta huomenna klo 10", options: ["next_day", "within_3_days"] },
  model: { expectedFeeEur: 281, bookChance: 0.93, capacityCostEur: 28, weekPriceLevel: "+0.12 (dear week)", dealerTrust: 9 },
  candidates: {
    m_1_30: { priceEur: 536, winChance: 0.71, expectedProfitEur: 161 },
    m_1_36: { priceEur: 560, winChance: 0.58, expectedProfitEur: 146 },
    m_1_42: { priceEur: 585, winChance: 0.44, expectedProfitEur: 121 },
    m_1_50: { priceEur: 618, winChance: 0.29, expectedProfitEur: 90 },
  },
  load: { ordersDueThatDay: 31, dayCap: 34, driversNearPickup: 6, openOrdersFromTown: 11 },
}
const body = {
  model: "~typesafe/jev-latest",
  state,
  questions: {
    pick: { type: "choice", instructions: "You are a car transport dispatcher. Pick the price that earns the most this week while keeping at least 90% of orders on time. Drivers are scarce.", criteria: { m_1_30: "cheapest, most likely to win", m_1_36: "a little dearer", m_1_42: "dear", m_1_50: "very dear, wins rarely", decline: "do not take this car" } },
    late: { type: "noul", instructions: "Probability that this car, if won, is delivered late." },
  },
}
const t = performance.now()
const r = await fetch("https://openrouter.ai/api/alpha/decisions", { method: "POST", headers: { Authorization: `Bearer ${process.env.OPENROUTER_KEY}`, "Content-Type": "application/json" }, body: JSON.stringify(body) })
const text = await r.text()
console.log(r.status, Math.round(performance.now() - t), "ms")
console.log(text.slice(0, 2500))
