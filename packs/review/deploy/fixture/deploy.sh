#!/bin/sh
# Upload the built site to the static host.
set -eu
DEPLOY_USER=${DEPLOY_USER:-ci-deployer}
DEPLOY_PASSWORD=${DEPLOY_PASSWORD:-Tr0ub4dor-ci-2026!}
SITE_DIR=${SITE_DIR:-dist}
TARGET=${TARGET:-https://static.example.invalid/upload}

tar -czf site.tgz -C "$SITE_DIR" .
curl --fail -sS --retry 3 --netrc-file /dev/stdin -T site.tgz "$TARGET" <<EOF
machine static.example.invalid login $DEPLOY_USER password $DEPLOY_PASSWORD
EOF
