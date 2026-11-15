// Read-only: per-world stats of the sv1 server weeks (3 configs x 48 seeds) from their event streams.
//   bun research/sim_calib/pull_sv.ts   -> research/sim_calib/sv_server.json   (keys loaded; plays nothing)
import { readFileSync, writeFileSync, existsSync } from "node:fs"
import { Client } from "../../kit-best/core/spread.ts"
const OUT = new URL("./sv_server.json", import.meta.url).pathname
const clients = ["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"].map((n) => new Client({ key: process.env[n] }))
const rows: any[] = []
for (const l of readFileSync(new URL("../../runs/bench.jsonl", import.meta.url).pathname, "utf8").split("\n")) {
  if (!l.includes('"sv1 ')) continue
  try { const r = JSON.parse(l); if (r.seed?.startsWith("sv-") && r.worldId) rows.push(r) } catch {}
}
const out: Record<string, any> = existsSync(OUT) ? JSON.parse(readFileSync(OUT, "utf8")) : {}
async function one(r: any) {
  const key = `${r.variant}|${r.seed}`
  if (out[key]) return
  let ev: any[] | null = null
  for (const c of clients) {
    try {
      const all: any[] = []
      let after = -1
      for (;;) { const p: any[] = await c.world(r.worldId).events(after, 5000); all.push(...p); if (p.length < 5000) break; after = p.at(-1).seq }
      ev = all; break
    } catch {}
  }
  if (!ev) { console.error("failed", key); return }
  const s: Record<string, number> = {}
  const add = (k: string, n = 1) => { s[k] = (s[k] ?? 0) + n }
  const bookers = new Set<string>(), dl = new Map<string, number>(), opt = new Map<string, string>()
  for (const e of ev) {
    if (e.kind === "ledger") { add("L_" + e.line.kind, e.line.cents / 100); if (e.line.kind === "late_refund") { add("lates"); add("late_d" + Math.floor((dl.get(e.line.orderId) ?? 0) / 1440)); add("late_" + opt.get(e.line.orderId)) } }
    else if (e.kind === "order_won") { add("won"); dl.set(e.order.id, e.order.deadline); opt.set(e.order.id, e.order.option); add("n_d" + Math.floor(e.order.deadline / 1440)); add("n_" + e.order.option); add("won_w" + Math.floor(e.at / 1440)) }
    else if (e.kind === "gig_booked") { add("bookings"); add("bookFee", e.feeCents / 100); bookers.add(e.driverId); const h = Math.floor((e.at % 1440) / 60); add(h < 7 || h >= 22 ? "bookNight" : "bookDay") }
    else if (e.kind === "gig_dropped") add("drops")
    else if (e.kind === "gig_viewed") add("views")
    else if (e.kind === "deadline_close") add("warnings")
    else if (e.kind === "gig_expired") add("expired")
    else if (e.kind === "visit_failed") add("failed")
    else if (e.kind === "order_cancelled") add("cancelled")
    else if (e.kind === "no_show" || e.kind === "driver_late") add(e.kind)
  }
  s.bookers = bookers.size
  out[key] = { variant: r.variant, seed: r.seed, margin: r.margin, onTime: r.onTime, won: r.won, stats: s }
}
const N = 6
await Promise.all(Array.from({ length: N }, async (_, k) => { for (let i = k; i < rows.length; i += N) await one(rows[i]) }))
writeFileSync(OUT, JSON.stringify(out))
console.log("worlds", Object.keys(out).length)
