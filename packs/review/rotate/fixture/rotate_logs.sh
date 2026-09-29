#!/bin/sh
# Keep only the newest KEEP rotated logs (app.log.*) in LOG_DIR.
set -eu
LOG_DIR=${LOG_DIR:-./logs}
KEEP=${KEEP:-5}

n=0
ls -1t "$LOG_DIR"/app.log.* 2>/dev/null | while read -r old; do
  n=$((n + 1))
  if [ "$n" -ge "$KEEP" ]; then
    rm -f -- "$old"
  fi
done
