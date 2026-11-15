#!/bin/bash
# Read-only: events, drivers, reveal, snapshot of every ended level 8 practice world of the three normal keys → runs/events/.
# curl with a hard timeout per request; skips files that exist.   bash research/views/pull.sh
cd "$(dirname "$0")/../.." || exit 1
set -a; . ./.env; set +a
mkdir -p runs/events
one() {
  name=$1; id=$2; what=$3
  out="runs/events/$id.$what.json.gz"
  [ -s "$out" ] && return
  case $what in events) path="/events?after=-1";; drivers) path="/drivers";; reveal) path="/reveal";; snapshot) path="";; esac
  for try in 1 2 3 4; do
    if curl -sf -m 90 -H "authorization: Bearer ${!name}" "$SPREAD_URL/v1/worlds/$id$path" | gzip > "$out.tmp" && [ "$(stat -c %s "$out.tmp")" -gt 100 ]; then mv "$out.tmp" "$out"; return; fi
    sleep "$try"
  done
  rm -f "$out.tmp"; echo "failed $id $what" >> runs/events_pull_failed.log
}
export -f one
for name in SPREAD_KEY SPREAD_KEY_2 SPREAD_KEY_OFFICIAL; do
  curl -sf -m 60 -H "authorization: Bearer ${!name}" "$SPREAD_URL/v1/worlds" |
    /root/system/venv/bin/python -c "
import json,sys
for w in reversed(json.load(sys.stdin)):
    if w['level']==8 and w['ended'] and w['kind']=='practice' and w['season'] is None:
        for what in ('reveal','snapshot','events','drivers'): print('$name', w['worldId'], what)"
done | shuf | xargs -P 10 -L 1 bash -c 'one "$@"' _
echo "done $(ls runs/events | wc -l) files"
