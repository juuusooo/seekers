# fast_grid: log

## 14 Nov 18:45 · open
- **Hypothesis:** A wide knob search from BEST10 on the Rust sim (sim-experimental, 1,000 weeks/s) finds a setting that beats BEST10 in both sim worlds (v4 and calibrated v5c) and on held-out weeks
- **Base, seeds, metric:** base BEST10 (kit-best defaults); search seeds m-1..48,h-1..48 in both worlds; held out k (62 weeks) + rd-1..48 both worlds; score = margin minus 2,000 per point under 92.5% on time; then server proof fresh seeds vs BEST10 same weeks
- **Kill criteria:** kill: no candidate over 2 SE pooled on held-out weeks in both worlds with no drop in ranked weeks; server: under 2 SE or fewer ranked weeks
- **What I did:**
- **Result / verdict:**
- **Next:**
