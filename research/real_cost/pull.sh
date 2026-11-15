#!/bin/bash
# Read-only: events, snapshot, drivers of the ended BEST6+ practice worlds named in bench.jsonl -> runs/events/.
# Three normal practice keys only (each world is tried on each key). bash research/real_cost/pull.sh
cd "$(dirname "$0")/../.." || exit 1
set -a; . ./.env; set +a
one() {
  id=$1; what=$2; out="runs/events/$id.$what.json.gz"
  [ -s "$out" ] && return
  case $what in events) path="/events?after=-1";; drivers) path="/drivers";; snapshot) path="";; esac
  for name in SPREAD_KEY SPREAD_KEY_2 SPREAD_KEY_OFFICIAL; do
    for try in 1 2; do
      if curl -sf -m 90 -H "authorization: Bearer ${!name}" "$SPREAD_URL/v1/worlds/$id$path" | gzip > "$out.tmp.$$" && [ "$(stat -c %s "$out.tmp.$$")" -gt 100 ]; then mv "$out.tmp.$$" "$out"; return; fi
      sleep 0.2
    done
  done
  rm -f "$out.tmp.$$"; echo "failed $id $what" >> runs/rc/pull_failed.log
}
export -f one
/root/system/venv/bin/python - <<'P' | shuf | xargs -P 16 -L 1 bash -c 'one "$@"' _
import json
keep = ("sv1 fee", "sn1 best6", "sn1 notes", "b8 BEST8", "b8 BEST7", "i3 base", "i3 mon -.03 fri +.08", "i3 mon -.03", "i3 brake .93")
for l in open("runs/bench.jsonl"):
    r = json.loads(l)
    if r.get("variant") in keep and r.get("worldId"):
        for what in ("events", "snapshot", "drivers"): print(r["worldId"], what)
P
echo "done"
