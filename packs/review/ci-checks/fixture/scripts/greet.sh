#!/bin/sh
# Print a greeting for $1.
printf 'hello, %s\n' "${1:-world}"
