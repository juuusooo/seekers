import { Client } from "../../kit-best/core/spread.ts"
const c = new Client({ key: process.env.SPREAD_KEY! })
const id = process.argv[2]!
for (const what of ["", "/reveal"]) {
  const r = await fetch(`${c.url}/v1/worlds/${id}${what}`, { headers: { authorization: `Bearer ${c.key}` } })
  const t = await r.text()
  console.log(what || "snapshot", r.status, t.length)
  if (r.status === 200) { const j = JSON.parse(t); for (const [k, v] of Object.entries(j)) console.log("  ", k, Array.isArray(v) ? `[${v.length}] ` + (JSON.stringify(v[0]) ?? "").slice(0, 600) : JSON.stringify(v).slice(0, 200)) }
}
