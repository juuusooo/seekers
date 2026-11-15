/** Recorder for the final: with FINAL_REC=<folder> set, every line goes to <folder>/rec.jsonl with the wall clock.
 * Without it, nothing is written and nothing changes. A recorder error never reaches the desk. */
import { appendFileSync, mkdirSync, writeFileSync } from "node:fs"

const DIR = process.env.FINAL_REC
export const REC = Boolean(DIR)
if (DIR) try { mkdirSync(DIR, { recursive: true }) } catch {}
const arrived = new WeakMap<object, number>()

export function rec(line: Record<string, unknown>): void {
  if (!DIR) return
  try { appendFileSync(`${DIR}/rec.jsonl`, JSON.stringify({ t: Date.now(), ...line }) + "\n") } catch {}
}
export function recFile(name: string, body: unknown): void {
  if (!DIR) return
  try { writeFileSync(`${DIR}/${name}`, JSON.stringify(body)) } catch {}
}
/** Wall clock of a stream message when it came off the socket. */
export function stamp(message: object): void {
  if (DIR) arrived.set(message, Date.now())
}
export const stampOf = (message: object): number | undefined => arrived.get(message)
