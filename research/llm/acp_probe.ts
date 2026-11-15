// Claude over ACP (Agent Client Protocol): start-up time and time per decision.
// bun research/llm/acp_probe.ts [model] [turns]     model: haiku | sonnet | opus (empty = the login's default)
import { spawn } from "node:child_process"
import { mkdirSync } from "node:fs"

const model = process.argv[2] ?? ""
const turns = Number(process.argv[3] ?? 6)
const cwd = "/tmp/claude-1002/-root-system-z-sideprojects-junction-2026/98d17027-e711-4e1a-bcfb-b7113e5cc20f/scratchpad/acp-empty"
mkdirSync(cwd, { recursive: true })

const t0 = performance.now()
const since = () => Math.round(performance.now() - t0)
const env = { ...process.env }
if (model) env.ANTHROPIC_MODEL = model
const child = spawn("npx", ["-y", "@agentclientprotocol/claude-agent-acp@0.107.0"], { cwd, env, stdio: ["pipe", "pipe", "pipe"] })
let errText = ""
child.stderr.on("data", (d) => (errText += String(d)))

let nextId = 1
const waiting = new Map<number, (m: any) => void>()
let text = ""
let firstChunkAt = 0
let buffer = ""
child.stdout.on("data", (d) => {
  buffer += String(d)
  let nl: number
  while ((nl = buffer.indexOf("\n")) >= 0) {
    const line = buffer.slice(0, nl).trim()
    buffer = buffer.slice(nl + 1)
    if (!line) continue
    let m: any
    try { m = JSON.parse(line) } catch { continue }
    if (m.id !== undefined && (m.result !== undefined || m.error !== undefined) && waiting.has(m.id)) {
      waiting.get(m.id)!(m)
      waiting.delete(m.id)
    } else if (m.method === "session/update") {
      const u = m.params?.update
      if (u?.sessionUpdate === "agent_message_chunk" && u.content?.type === "text") {
        if (!firstChunkAt) firstChunkAt = performance.now()
        text += u.content.text
      }
    } else if (m.method === "session/request_permission") {
      // The probe never lets the agent use a tool.
      child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: m.id, result: { outcome: { outcome: "cancelled" } } }) + "\n")
    } else if (m.id !== undefined && m.method) {
      child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id: m.id, error: { code: -32601, message: "not supported" } }) + "\n")
    }
  }
})
function call(method: string, params: unknown, timeoutMs = 120000): Promise<any> {
  const id = nextId++
  return new Promise((done, fail) => {
    const timer = setTimeout(() => fail(new Error(method + " timed out. stderr: " + errText.slice(-400))), timeoutMs)
    waiting.set(id, (m) => {
      clearTimeout(timer)
      if (m.error) fail(new Error(method + ": " + JSON.stringify(m.error).slice(0, 400)))
      else done(m.result)
    })
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n")
  })
}

try {
  const init = await call("initialize", { protocolVersion: 1, clientCapabilities: { fs: { readTextFile: false, writeTextFile: false }, terminal: false } })
  console.log("initialize " + since() + " ms, agent " + JSON.stringify(init.agentInfo ?? {}))
  const session = await call("session/new", { cwd, mcpServers: [] })
  console.log("session/new " + since() + " ms, models " + JSON.stringify(session.models ?? {}).slice(0, 500))
  const week = (hour: number) =>
    "You supervise a car transport dispatcher for one simulated week. Answer with ONE line of JSON and nothing else, no tools: " +
    '{"priceShift": number from -0.10 to 0.10, "priceWar": true|false, "tighten": true|false, "why": "max 12 words"}.\n' +
    "State at Wed " + hour + ":00: quotes today 41, won 9 (model expected 19.5). Mon won 31 of 70 (expected 30.2). Tue won 28 of 66 (expected 29.0). " +
    "On time so far 93.1% (minimum 90%). Orders due Fri 36, cap 34. Open gigs without a driver 12, of which 3 within 6 h of last pickup. Drivers 310."
  const ms: number[] = []
  const first: number[] = []
  for (let k = 0; k < turns; k++) {
    text = ""
    firstChunkAt = 0
    const t = performance.now()
    const r = await call("session/prompt", { sessionId: session.sessionId, prompt: [{ type: "text", text: week(10 + k) }] })
    ms.push(Math.round(performance.now() - t))
    first.push(firstChunkAt ? Math.round(firstChunkAt - t) : -1)
    console.log("turn " + k + ": " + ms[k] + " ms (first text " + first[k] + " ms), stop " + r.stopReason + ", answer " + text.trim().slice(0, 200))
  }
  const sorted = [...ms.slice(1)].sort((a, b) => a - b)
  console.log("model " + (model || "default") + ": first turn " + ms[0] + " ms, later turns median " + sorted[Math.floor(sorted.length / 2)] + " ms, max " + sorted.at(-1) + " ms")
} catch (e) {
  console.log("FAILED: " + String(e).slice(0, 900))
} finally {
  child.kill()
}
