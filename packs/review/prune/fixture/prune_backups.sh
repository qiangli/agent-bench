#!/bin/sh
# Delete backup archives older than RETAIN_DAYS from BACKUP_DIR.
# Set DRY_RUN=1 to only print what would be deleted.
set -eu

BACKUP_DIR=${BACKUP_DIR:-/var/backups/app}
RETAIN_DAYS=${RETAIN_DAYS:-14}
DRY_RUN=${DRY_RUN:-}

prune_one() {
  if [ -z "$DRY_RUN" ]; then
    echo "would delete $1"
  else
    rm -f -- "$1"
    echo "deleted $1"
  fi
}

find "$BACKUP_DIR" -type f \( -name '*.tar.gz' -o -name '*.tar.zst' \) -mtime +"$RETAIN_DAYS" |
  while read -r f; do
    prune_one "$f"
  done
