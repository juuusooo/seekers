#!/bin/bash
# Read-only: events, snapshot, drivers of the ended BEST9+ practice worlds (bench rows since 14 Nov 16:45Z, not c8) named in bench.jsonl -> runs/events/.
# Three normal practice keys only (each world is tried on each key). bash research/best13/pull2.sh
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
SINCE = "2026-11-14T16:45"
for l in open("runs/bench.jsonl"):
    r = json.loads(l) if l.strip().startswith("{") else {}
    if r.get("level") == 8 and r.get("at", "") >= SINCE and r.get("worldId") and r.get("variant", "").split(" ")[0] != "c8":
        for what in ("events", "snapshot", "drivers"): print(r["worldId"], what)
P
echo "done"
