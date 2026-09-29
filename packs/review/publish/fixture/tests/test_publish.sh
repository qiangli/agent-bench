#!/bin/sh
# Runs publish.sh against a stub curl; no network. Exit 0 = pass.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cat > "$tmp/curl" <<'EOF'
#!/bin/sh
# stub: record stdin (headers) and the argument list
cat > "$STUB_OUT.stdin"
printf '%s\n' "$*" > "$STUB_OUT.args"
EOF
chmod +x "$tmp/curl"
echo data > "$tmp/pkg.tgz"

STUB_OUT="$tmp/out" PATH="$tmp:$PATH" DEPLOY_TOKEN=test-token-not-real \
  sh "$here/publish.sh" "$tmp/pkg.tgz"

grep -q 'Authorization: Bearer test-token-not-real' "$tmp/out.stdin"
if grep -q test-token-not-real "$tmp/out.args"; then
  echo "FAIL: token visible on the curl command line" >&2
  exit 1
fi
if (unset DEPLOY_TOKEN; PATH="$tmp:$PATH" STUB_OUT="$tmp/out2" sh "$here/publish.sh" "$tmp/pkg.tgz") 2>/dev/null; then
  echo "FAIL: ran without DEPLOY_TOKEN" >&2
  exit 1
fi
echo "ok"
