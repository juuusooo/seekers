// The trees in TypeScript must give the numbers LightGBM gave (runs/rc/parity.json, written by fit.py --write).
import { readFileSync } from "node:fs"
import { costPredict } from "../../kit-cost/core/cost.ts"
const c = JSON.parse(readFileSync(new URL("../../runs/rc/parity.json", import.meta.url), "utf8"))
let worst = 0
c.x.forEach((x: number[], i: number) => { worst = Math.max(worst, Math.abs(costPredict("mean", x) - c.mean[i]), Math.abs(costPredict("q80", x) - c.q80[i])) })
console.log("largest difference", worst.toExponential(2))
