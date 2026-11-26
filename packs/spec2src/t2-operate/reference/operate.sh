#!/bin/sh
# The operate task with no model: every step is the code block of dag.md, as written.
set -eu
cd "$1"
unset PREFIX
: > report.txt

block() {
    awk -v step="$1" '
        /^### / { selected = ($0 == "### " step) }
        selected && /^```sh$/ { copying = 1; next }
        copying && /^```$/ { found = 1; exit }
        copying { print }
        END { if (!found) exit 1 }
    ' dag.md
}

step() {
    script=$(block "$1")
    status=0
    sh -c "$script" || status=$?
    printf '%s %s\n' "$1" "$status" >> report.txt
    return "$status"
}

step build
step test
step install

script=$(block serve)
sh -c "$script" > serve.log 2>&1 &
server=$!
trap 'kill -TERM "$server" 2>/dev/null || :' EXIT
trap 'exit 1' HUP INT TERM
sleep 2
kill -0 "$server"

export ARGS='add --id drill-1 --def examples/contact.json --json'
step run > answer.json
url=$(python3 -c 'import json; print(json.load(open("answer.json"))["url"])')
curl --noproxy '*' --fail --silent --show-error --max-time 10 --output page.html "$url"

step stop
status=0
wait "$server" || status=$?
printf 'serve %s\n' "$status" >> report.txt
trap - EXIT
