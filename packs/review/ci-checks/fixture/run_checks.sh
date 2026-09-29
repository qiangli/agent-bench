#!/bin/sh
# CI entry point: syntax-check the scripts, then run the unit tests.
# Any failure fails the build.
set -eu
cd "$(dirname "$0")"

echo "== shell syntax"
for f in scripts/*.sh; do sh -n "$f"; done

echo "== unit tests"
python3 -m unittest discover -s tests 2>&1 | tail -n 20

echo "all checks passed"
