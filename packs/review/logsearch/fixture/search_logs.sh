#!/bin/sh
# Usage: search_logs.sh PATTERN [DIR] [EXTRA_GREP_FLAGS]
# Print matching lines from the service logs. EXTRA_GREP_FLAGS lets callers
# pass options such as -i or -w through to grep.
set -eu
pattern=$1
dir=${2:-/var/log/service}
flags=${3:-}
eval "grep -rn $flags -e '$pattern' -- '$dir'"
