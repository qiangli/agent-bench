#!/usr/bin/env bash
# Validate every pytest-graded task: the untouched fixture must FAIL its grader
# and the reference solution must PASS it. Needs python3 with pytest.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
rc=0
for t in packs/*/*/task.yaml; do
  d=$(dirname "$t")
  grep -q 'type: pytest' "$t" || { echo "skip $d (not pytest)"; continue; }
  w=$(mktemp -d)
  cp -R "$d/fixture/." "$w/"; cp "$d"/grader/*.py "$w/"
  if (cd "$w" && "$PY" -m pytest -q -p no:cacheprovider >/dev/null 2>&1); then
    echo "FAIL $d: fixture already passes its grader"; rc=1
  fi
  cp -R "$d/reference/." "$w/"
  if (cd "$w" && "$PY" -m pytest -q -p no:cacheprovider >/dev/null 2>&1); then
    echo "ok   $d"
  else
    echo "FAIL $d: reference does not pass its grader"; rc=1
  fi
  rm -rf "$w"
done
exit $rc
