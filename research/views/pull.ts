// Read-only: saves the event stream and driver list of every ended level 8 practice world of the three normal keys.
// bun research/views/pull.ts   → runs/events/<worldId>.events.json.gz, .drivers.json.gz  (skips files that exist)
import { existsSync, mkdirSync, writeFileSync } from "node:fs"
import { Client } from "../../kit-best/core/spread.ts"
const OUT = new URL("../../runs/events/", import.meta.url).pathname
mkdirSync(OUT, { recursive: true })
const get = async (c: Client, path: string) => {
  for (let i = 0; i < 6; i++) {
    const r = await fetch(c.url + path, { headers: { authorization: `Bearer ${c.key}` }, signal: AbortSignal.timeout(60000) }).catch(() => null)
    if (r?.status === 200) return new Uint8Array(await r.arrayBuffer())
    if (r && r.status !== 429 && r.status < 500) return null
    await Bun.sleep(500 * (i + 1))
  }
  return null
}
let done = 0, fail = 0
await Promise.all(["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"].map(async (name) => {
  const c = new Client({ key: process.env[name]! })
  const ws = (await c.worlds()).filter((w) => w.level === 8 && w.ended && w.kind === "practice" && w.season === null).reverse()
  let next = 0
  await Promise.all(Array.from({ length: 3 }, async () => {
    while (next < ws.length) {
      const id = ws[next++]!.worldId
      for (const what of ["events", "drivers"]) {
        const file = `${OUT}${id}.${what}.json.gz`
        if (existsSync(file)) continue
        const body = await get(c, `/v1/worlds/${id}/${what}${what === "events" ? "?after=-1" : ""}`)
        if (body) writeFileSync(file, Bun.gzipSync(body)); else fail++
      }
      if (++done % 500 === 0) console.log(new Date().toISOString(), "worlds", done, "failed reads", fail)
    }
  }))
}))
console.log("done", done, "failed reads", fail)
