// Read-only: unfinished practice worlds per normal key whose clock does not move for 40 s (left behind by a killed run).
import { Client } from "../../kit-best/core/spread.ts"
for (const name of ["SPREAD_KEY", "SPREAD_KEY_2", "SPREAD_KEY_OFFICIAL"]) {
  const c = new Client({ key: process.env[name]! })
  const open = (await c.worlds()).filter((w) => !w.ended && w.kind === "practice" && w.season === null)
  const now1 = new Map<string, number>()
  for (const w of open) now1.set(w.worldId, ((await c.world(w.worldId).snapshot().catch(() => null)) as any)?.now ?? -1)
  await Bun.sleep(40000)
  const still = new Set((await c.worlds()).filter((w) => !w.ended).map((w) => w.worldId))
  const stuck: string[] = []
  for (const [id, n] of now1) if (still.has(id) && (((await c.world(id).snapshot().catch(() => null)) as any)?.now ?? -2) === n) stuck.push(`${id}@${n}`)
  console.log(name, "open", open.length, "not moving", stuck.join(" ") || "none")
}
