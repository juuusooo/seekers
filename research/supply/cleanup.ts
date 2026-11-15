/** Lists (default) or deletes (--delete) this key's unfinished practice worlds: frees the practice slots after a run
 * of server.ts was stopped by hand. Never touches a ranking run or the final.
 *   node research/supply/cleanup.ts [--delete] [--kit kit-supply] */
import { parseArgs } from "node:util"
import { fileURLToPath, pathToFileURL } from "node:url"
import { dirname, resolve } from "node:path"
const { values: a } = parseArgs({ options: { kit: { type: "string", default: "kit-supply" }, delete: { type: "boolean" } } })
const here = dirname(fileURLToPath(import.meta.url))
const { Client } = await import(pathToFileURL(resolve(here, "..", "..", a.kit!, "core", "spread.ts")).href)
const client = new Client()
const open = (await client.worlds()).filter((w: any) => w.kind === "practice" && !w.ended && w.season === null && w.boardRun === null)
console.log(`${open.length} unfinished practice worlds`)
if (a.delete) for (const w of open) await client.world(w.worldId).delete().then(() => console.log("deleted", w.worldId), (e: Error) => console.log("not deleted", w.worldId, String(e.message).slice(0, 100)))
