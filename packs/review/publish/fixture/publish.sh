#!/bin/sh
# Publish a release archive to the package index.
# Usage: DEPLOY_TOKEN=... publish.sh ARCHIVE
set -eu
: "${DEPLOY_TOKEN:?DEPLOY_TOKEN must be set}"
INDEX_URL=${INDEX_URL:-https://packages.example.invalid/upload}
archive=$1
[ -f "$archive" ] || { echo "publish.sh: no such archive: $archive" >&2; exit 2; }

# Pass the header on stdin, keeping it out of curl arguments and environment.
printf 'Authorization: Bearer %s\n' "$DEPLOY_TOKEN" |
  (unset DEPLOY_TOKEN; exec curl --fail -sS -H @- --data-binary @"$archive" "$INDEX_URL")
