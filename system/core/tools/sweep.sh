#!/bin/bash
# Same-seed experiments on all practice worlds of the three practice keys (24 at a time). Never ranking.
#   bash core/tools/sweep.sh N PREFIX TAG "label|knob=value,..." "label2|..." ...   (START=k to begin at seed k, P=parallel)
# "label|" with nothing after the bar plays the model as it is. Rows: Bahn-Spread/runs/bench.jsonl, kit "kit-best",
# variant "<TAG> <label>". Compare with: python3 core/tools/cmp.py TAG [BASE_LABEL]
KIT="$(cd "$(dirname "$0")/../.." && pwd)"   # kit-best
cd "$KIT" || exit 1
N=$1; PREFIX=$2; TAG=$3; shift 3
for i in $(seq ${START:-1} "$N"); do for exp in "$@"; do echo "$exp|$i"; done; done |
  xargs -P ${P:-24} -I{} bash -c 'IFS="|" read -r label set i <<< "{}"; bash core/tools/lockweek.sh --seed '"$PREFIX"'-$i --variant "'"$TAG"' $label" ${set:+--set "$set"} > /dev/null 2>>../runs/kit-final-sweep.err'
echo "done $TAG"
