#!/bin/sh
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
export ARGS='add --id drill-1 --def examples/contact.json --json'
step run > answer.json

script=$(block serve)
sh -c "$script" &
server=$!
stop_server() {
    kill -TERM "$server" 2>/dev/null || :
    status=0
    wait "$server" || status=$?
    printf 'serve %s\n' "$status" >> report.txt
}
trap stop_server EXIT
trap 'exit 1' HUP INT TERM
url=$(python3 -c 'import json; print(json.load(open("answer.json"))["url"])')
curl --noproxy '*' --fail --silent --show-error --max-time 10 --output page.html "$url"
