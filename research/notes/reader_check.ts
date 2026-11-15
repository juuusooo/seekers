// reader_check.ts: kit-best's note reader and note flags against the reveal truth, per truth class.
// Run from Bahn-Spread/: bun research/notes/reader_check.ts   (reads runs/notes/orders.jsonl, writes runs/notes/labelled.jsonl)
import { readNote } from "../../kit-best/core/notes.ts"
import { createReadStream, writeFileSync } from "node:fs"
import { createInterface } from "node:readline"
const NOTE_PLATES = /kilv|kilp|kiilp|rekkar|plate|skylt|unregist|oregistr/i
const NOTE_MANUAL = /manua|mnual|mnaua|mannua|manul|käsivaiht|kasivaiht|stick|manuell|växel|vaxel|ei automaatti|no automatic|not automatic|inte automat/i
const stat: Record<string, Record<string, number>> = {}
const add = (k: string, f: string) => { (stat[k] ??= {})[f] = (stat[k]![f] ?? 0) + 1 }
const out: string[] = []
for await (const line of createInterface({ input: createReadStream("runs/notes/orders.jsonl") })) {
  const o = JSON.parse(line)
  if (o.level !== 8 || !o.note || o.cancelled) continue
  const t = o.legs[0].truth, leg = o.legs[0]
  const cls = t.releasedAt !== null ? "payment" : t.readyAt > leg.from ? "ready_later" : JSON.stringify(t.pickupHours) !== JSON.stringify(leg.pHours) ? "pickup_hours"
    : JSON.stringify(t.deliveryHours) !== JSON.stringify(leg.dHours) ? "delivery_hours" : t.manualGearbox ? "manual" : t.needsPlates ? "plates" : t.summerTyres ? "tyres" : t.noteDeadline !== null ? "deadline" : "harmless"
  const r = readNote(o.note, o.arrivedAt)
  const plates = NOTE_PLATES.test(o.note), manual = NOTE_MANUAL.test(o.note)
  let ok = true
  if (cls === "payment") ok = r.readyFrom === t.releasedAt
  else if (cls === "ready_later") ok = r.readyFrom === t.readyAt
  else if (r.readyFrom !== null && r.readyFrom > leg.from) ok = false
  if (cls === "deadline") ok = r.deliverBy === t.noteDeadline
  else if (r.deliverBy !== null && r.deliverBy < o.wonDeadline) ok = false
  if ((cls === "plates") !== plates || (cls === "manual") !== manual) ok = false
  add(cls, "n"); if (ok) add(cls, "ok")
  if (r.readyFrom !== null && r.readyFrom > leg.from && cls !== "payment" && cls !== "ready_later") add(cls, "falseReady")
  if (r.deliverBy !== null && r.deliverBy < o.wonDeadline && cls !== "deadline") add(cls, "falseBy")
  if (plates && cls !== "plates") add(cls, "falsePlates")
  if (manual && cls !== "manual") add(cls, "falseManual")
  out.push(JSON.stringify({ world: o.world, id: o.id, cls, ok, note: o.note, lang: o.lang, arrivedAt: o.arrivedAt, from: leg.from, optDeadline: o.optDeadline, wonDeadline: o.wonDeadline, pHours: leg.pHours, dHours: leg.dHours, truth: t, read: r, plates, manual, fails: o.fails }))
}
writeFileSync("runs/notes/labelled.jsonl", out.join("\n") + "\n")
for (const [k, s] of Object.entries(stat).sort((a, b) => b[1].n! - a[1].n!)) console.log(k.padEnd(16), String(s.n).padStart(7), "reader right", ((100 * (s.ok ?? 0)) / s.n!).toFixed(2) + "%", JSON.stringify({ ...s, n: undefined, ok: undefined }))
