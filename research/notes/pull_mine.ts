// pull_mine.ts: saves events, reveal and snapshot of the practice worlds of one bench tag (read-only, the three normal keys).
// set -a && source ./.env && set +a && bun research/notes/pull_mine.ts "nt1 "    → runs/events/<worldId>.*.json.gz
import { existsSync, readFileSync, writeFileSync } from "node:fs"
import { Client } from "../../kit-best/core/spread.ts"
const OUT = new URL("../../runs/events/", import.meta.url).pathname
const tag = process.argv[2]!
const ids = readFileSync(new URL("../../runs/bench.jsonl", import.meta.url).pathname, "utf8").split("\n").filter(Boolean).map((l) => { try { return JSON.parse(l) } catch { return {} } })
  .filter((r) => r.kit === "kit-notes" && String(r.variant ?? "").startsWith(tag)).map((r) => r.worldId as string)
const clients = ["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"].map((name) => new Client({ key: process.env[name]! }))
const get = async (c: Client, path: string) => {
  for (let i = 0; i < 6; i++) {
    const r = await fetch(c.url + path, { headers: { authorization: `Bearer ${c.key}` }, signal: AbortSignal.timeout(60000) }).catch(() => null)
    if (r?.status === 200) return new Uint8Array(await r.arrayBuffer())
    if (r && r.status !== 429 && r.status < 500) return null
    await Bun.sleep(500 * (i + 1))
  }
  return null
}
let next = 0, saved = 0, missing = 0
await Promise.all(Array.from({ length: 4 }, async () => {
  while (next < ids.length) {
    const id = ids[next++]!
    let owner: Client | undefined
    for (const [what, path] of [["events", "/events?after=-1"], ["reveal", "/reveal"], ["snapshot", ""]] as const) {
      const file = `${OUT}${id}.${what}.json.gz`
      if (existsSync(file)) continue
      let body: Uint8Array | null = null
      for (const c of owner ? [owner] : clients) { body = await get(c, `/v1/worlds/${id}${path}`); if (body) { owner = c; break } }
      if (body) { writeFileSync(file, Bun.gzipSync(body)); saved++ } else missing++
    }
  }
}))
console.log("worlds", ids.length, "files saved", saved, "missing", missing)
