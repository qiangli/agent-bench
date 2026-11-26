#!/bin/sh
# Lifecycle end-to-end test for notepad. No model.
#
#   lifecycle.sh SPEC_DAG FOLDER [REPORT]
#
# Runs every step of the spec's dag.md, as written, on a fresh copy of FOLDER
# with a fresh HOME: build, test, install, serve, run, stop. The step text
# always comes from SPEC_DAG, never from a dag.md inside FOLDER. Around the
# steps it checks the service: the health endpoint answers after serve, the
# installed command works, the page of a new note answers 200, and after stop
# the page no longer answers and the serve process has ended.
#
# Every step and check is run even when an earlier one failed. REPORT gets one
# line "NAME STATUS" per step and check (0 is a pass) and a last line
# "verdict PASS" or "verdict FAIL". Exit 0 only on PASS.
set -u

dag=$(CDPATH= cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")
src=$(CDPATH= cd -- "$2" && pwd) || exit 2
[ -f "$dag" ] || { echo "lifecycle: no dag: $1" >&2; exit 2; }

top=$(mktemp -d "${TMPDIR:-/tmp}/lifecycle.XXXXXX")
report=${3:-$top/report.txt}
work=$top/work
mkdir -p "$work" "$top/home" "$top/prefix"
cp -R "$src"/. "$work"/
: > "$report"
logs=$top/logs
mkdir -p "$logs"

export HOME="$top/home"
unset DISPLAY WAYLAND_DISPLAY PREFIX ARGS
ADDR=127.0.0.1:${LIFECYCLE_PORT:-18295}
DATA=$top/data
export ADDR DATA
STEP_TIMEOUT=${LIFECYCLE_STEP_TIMEOUT:-1800}
fail=0

block() {
    awk -v step="$1" '
        /^### / { selected = ($0 == "### " step) }
        selected && /^```sh$/ { copying = 1; next }
        copying && /^```$/ { found = 1; exit }
        copying { print }
        END { if (!found) exit 1 }
    ' "$dag"
}

record() {
    printf '%s %s\n' "$1" "$2" >> "$report"
    [ "$2" = 0 ] || fail=1
}

limited() {
    if command -v timeout >/dev/null 2>&1; then timeout "$STEP_TIMEOUT" "$@"; else "$@"; fi
}

# step NAME: run the code block of NAME from the spec's dag.md in the work folder.
step() {
    status=0
    if script=$(block "$1"); then
        (cd "$work" && limited sh -c "$script") > "$logs/$1.out" 2> "$logs/$1.err" < /dev/null || status=$?
    else
        echo "no code block for step $1 in the spec's dag.md" > "$logs/$1.err"
        status=127
    fi
    record "$1" "$status"
}

page_code() {
    curl --noproxy '*' --silent --max-time 10 --output /dev/null --write-out '%{http_code}' "$1" 2>/dev/null
}

step build
step test

export PREFIX="$top/prefix"
step install
unset PREFIX

# serve: in the background, as the spec's block, then wait for the health endpoint.
server=
if script=$(block serve); then
    (cd "$work" && exec sh -c "$script") > "$logs/serve.out" 2> "$logs/serve.err" < /dev/null &
    server=$!
fi
up=1
n=0
while [ "$n" -lt 100 ]; do
    if [ "$(page_code "http://$ADDR/healthz")" = 200 ]; then up=0; break; fi
    sleep 0.2
    n=$((n + 1))
done
record serve-up "$up"

# run: the spec's block creates a note; its answer names the page.
export ARGS="--addr $ADDR --data $DATA add --id lifecycle-1 --title Lifecycle --body hello --json"
step run
unset ARGS
url=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["url"])' "$logs/run.out" 2>/dev/null) || url=
case "$url" in http://*) ;; *) url= ;; esac

# installed: the installed command reads the note back.
status=0
"$top/prefix/bin/notepad" --addr "$ADDR" --data "$DATA" show lifecycle-1 --json > "$logs/installed.out" 2> "$logs/installed.err" < /dev/null || status=$?
[ "$status" != 0 ] || grep -q '"body":"hello"' "$logs/installed.out" || status=1
record installed "$status"

# page: the page of the note answers 200.
status=1
[ -z "$url" ] || [ "$(page_code "$url")" != 200 ] || status=0
record page "$status"

step stop

# page-down: nothing answers at the address any more.
status=0
code=$(page_code "${url:-http://$ADDR/healthz}")
[ "$code" = 000 ] || status=1
record page-down "$status"

# serve-exit: the serve process has ended (its exit status is free).
status=1
if [ -n "$server" ]; then
    n=0
    while [ "$n" -lt 50 ]; do
        kill -0 "$server" 2>/dev/null || { status=0; break; }
        sleep 0.1
        n=$((n + 1))
    done
    [ "$status" = 0 ] || kill -KILL "$server" 2>/dev/null
    wait "$server" 2>/dev/null
fi
record serve-exit "$status"

if [ "$fail" = 0 ]; then echo "verdict PASS" >> "$report"; else echo "verdict FAIL" >> "$report"; fi
cat "$report"
echo "logs: $logs"
[ "$fail" = 0 ]
