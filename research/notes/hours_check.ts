// hours_check.ts: the TypeScript hours reader (kit-notes/core/notes.ts) against the reveal truth, like hours.py.
// Run from Bahn-Spread/: bun research/notes/hours_check.ts
import { readHours } from "../../kit-notes/core/notes.ts"
import { createReadStream } from "node:fs"
import { createInterface } from "node:readline"
const stat: Record<string, { n: number; ok: number }> = {}
for await (const line of createInterface({ input: createReadStream("runs/notes/labelled.jsonl") })) {
  const r = JSON.parse(line), t = r.truth
  const h = readHours(r.note, r.pHours, r.dHours)
  const ok = (!r.pHours || ((h.pickupOpens ?? r.pHours.opens) === t.pickupHours.opens && (h.pickupCloses ?? r.pHours.closes) === t.pickupHours.closes)) &&
    (!r.dHours || ((h.deliveryOpens ?? r.dHours.opens) === t.deliveryHours.opens && (h.deliveryCloses ?? r.dHours.closes) === t.deliveryHours.closes))
  const s = (stat[r.cls] ??= { n: 0, ok: 0 }); s.n++; if (ok) s.ok++
}
for (const [k, s] of Object.entries(stat).sort((a, b) => b[1].n - a[1].n)) console.log(k.padEnd(16), String(s.n).padStart(7), ((100 * s.ok) / s.n).toFixed(2) + "%")
