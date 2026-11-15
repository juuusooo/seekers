// Read-only probe: how many ended practice worlds each normal key still holds, and whether their events can be read.
import { Client } from "../../kit-best/core/spread.ts"
for (const name of ["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"]) {
  const key = process.env[name]
  if (!key) { console.log(name, "not set"); continue }
  const c = new Client({ key })
  const ws = await c.worlds()
  const l8 = ws.filter((w) => w.level === 8 && w.ended && w.kind === "practice" && w.season === null)
  console.log(name, "worlds", ws.length, "ended L8 practice", l8.length, "not ended", ws.filter((w) => !w.ended).length)
  if (l8.length) {
    const id = l8[l8.length - 1]!.worldId
    const t = performance.now()
    const r = await fetch(`${c.url}/v1/worlds/${id}/events?after=-1`, { headers: { authorization: `Bearer ${c.key}` } })
    const body = await r.text()
    console.log("  ", id, "events status", r.status, "bytes", body.length, "ms", Math.round(performance.now() - t), "views", (body.match(/gig_viewed/g) ?? []).length)
  }
}
