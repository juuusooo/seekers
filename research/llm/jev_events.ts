// Can JEV tell the week's hidden events from win statistics? Three made-up days, each asked 5 times.
// bun research/llm/jev_events.ts
const rules =
  "Level 8 week. We quote prices against one competitor we never see. A model gives the expected number of wins. " +
  "Hidden events: PRICE WAR = on one working day the competitor is 20% cheaper everywhere 08:00-18:00, so we win far fewer than expected in every region. " +
  "OUTAGE = on one working day the competitor is down in one region (a town and 80 km around it), so we win far more than expected there only. " +
  "Normal noise: wins differ from expected by about one standard deviation, sqrt(expected x 0.6)."
const days: Record<string, unknown> = {
  war: { now: "Wed 11:30", today: { quotes: 41, won: 6, expectedWins: 19.5, byRegion: { south: "2 of 15 (exp 7.1)", west: "1 of 9 (exp 4.4)", north: "2 of 10 (exp 4.6)", east: "1 of 7 (exp 3.4)" } }, earlierDays: { Mon: "31 of 70 (exp 30.2)", Tue: "28 of 66 (exp 29.0)" } },
  normal: { now: "Wed 11:30", today: { quotes: 41, won: 17, expectedWins: 19.5, byRegion: { south: "7 of 15 (exp 7.1)", west: "3 of 9 (exp 4.4)", north: "4 of 10 (exp 4.6)", east: "3 of 7 (exp 3.4)" } }, earlierDays: { Mon: "31 of 70 (exp 30.2)", Tue: "28 of 66 (exp 29.0)" } },
  outage: { now: "Wed 11:30", today: { quotes: 41, won: 25, expectedWins: 19.5, byRegion: { south: "7 of 15 (exp 7.1)", west: "9 of 9 (exp 4.4)", north: "5 of 10 (exp 4.6)", east: "4 of 7 (exp 3.4)" } }, earlierDays: { Mon: "31 of 70 (exp 30.2)", Tue: "28 of 66 (exp 29.0)" } },
  weak_war: { now: "Wed 09:40", today: { quotes: 12, won: 2, expectedWins: 5.6, byRegion: { south: "1 of 5 (exp 2.3)", west: "0 of 3 (exp 1.4)", north: "1 of 2 (exp 0.9)", east: "0 of 2 (exp 1.0)" } }, earlierDays: { Mon: "31 of 70 (exp 30.2)", Tue: "28 of 66 (exp 29.0)" } },
}
async function ask(state: unknown) {
  const t = performance.now()
  const r = await fetch("https://openrouter.ai/api/alpha/decisions", {
    method: "POST",
    headers: { Authorization: "Bearer " + process.env.OPENROUTER_KEY, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "~typesafe/jev-latest",
      state: { rules, day: state },
      questions: {
        war: { type: "noul", instructions: "Probability that today is the price war day." },
        outage: { type: "noul", instructions: "Probability that the competitor has an outage today in one region." },
        where: { type: "choice", instructions: "If there is an outage today, in which region?", criteria: { south: "south", west: "west", north: "north", east: "east", none: "no outage today" } },
      },
    }),
  })
  const j = (await r.json()) as any
  return { ms: Math.round(performance.now() - t), war: j.answers?.war?.noul, outage: j.answers?.outage?.noul, where: j.answers?.where?.choice, err: r.status === 200 ? "" : JSON.stringify(j).slice(0, 200) }
}
for (const [name, state] of Object.entries(days)) {
  const rs = await Promise.all([0, 1, 2, 3, 4].map(() => ask(state)))
  console.log(name.padEnd(9), "war", rs.map((r) => r.war).join(" "), "| outage", rs.map((r) => r.outage).join(" "), "| where", rs.map((r) => r.where).join(" "), "| ms", rs.map((r) => r.ms).join(" "), rs[0]!.err)
}
