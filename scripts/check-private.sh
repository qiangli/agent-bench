#!/usr/bin/env bash
# Fail if tracked files leak private system info: home/user paths, temp dirs,
# IPv4 addresses, e-mail addresses, or common token prefixes. Run before every
# commit; CONTRIBUTING.md explains the rules.
set -uo pipefail
cd "$(dirname "$0")/.."
pat='(/Users/|/home/[a-z]|/private/(tmp|var)|/var/folders/|C:\\Users\\|~/[A-Za-z]|([0-9]{1,3}\.){3}[0-9]{1,3}|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})'
files=$(git ls-files 2>/dev/null || find . -type f -not -path './.git/*' | sed 's#^\./##')
hits=$(printf '%s\n' $files | grep -v '^scripts/check-private.sh$' | xargs grep -nE "$pat" 2>/dev/null | grep -vE 'example\.(com|org|invalid)')
if [ -n "$hits" ]; then echo "private-info check FAILED:"; echo "$hits"; exit 1; fi
echo "private-info check ok"
