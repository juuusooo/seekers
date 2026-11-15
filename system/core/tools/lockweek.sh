#!/bin/bash
# Plays one practice week (core/week.ts) on a practice key with a free world. Shares the lock files in Bahn-Spread/runs/slots/
# with every other session, so tests never fight for a world. Practice only: week.ts cannot play ranking runs.
#   bash core/tools/lockweek.sh --seed m-1 [--set capLam=5] [--variant "tag label"] [--journal folder]
#   KEYS="SPREAD_KEY_2" bash core/tools/lockweek.sh ...   which keys it may use (default: the three practice keys)
KIT="$(cd "$(dirname "$0")/../.." && pwd)"   # kit-best
cd "$KIT" || exit 1
set -a; . ../.env; set +a
mkdir -p ../runs/slots
while true; do
  for name in $(shuf -e ${KEYS:-SPREAD_KEY SPREAD_KEY_2 SPREAD_KEY_OFFICIAL}); do
    for i in $(shuf -i 0-7); do
      exec 9> "../runs/slots/$name-$i.lock"
      if flock -n 9; then
        SPREAD_KEY="${!name}" bun core/week.ts "$@"
        exit $?
      fi
      exec 9>&-
    done
  done
  sleep 0.5
done
