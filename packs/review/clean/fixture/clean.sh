#!/bin/sh
# Remove build outputs. BUILD_DIR defaults to ./build (relative to this script).
set -eu
cd "$(dirname "$0")"
BUILD_DIR=${BUILD_DIR:-build}
refuse() { echo "clean.sh: refusing to remove '$BUILD_DIR'" >&2; exit 2; }
case $BUILD_DIR in /*) refuse ;; esac
# Walk components without glob expansion; never traverse a symlink.
remaining=$BUILD_DIR
checked=.
while :; do
  component=${remaining%%/*}
  case $component in
    ..) refuse ;;
    "" | .) ;;
    *) checked=$checked/$component; [ ! -L "$checked" ] || refuse ;;
  esac
  case $remaining in
    */*) remaining=${remaining#*/} ;;
    *) break ;;
  esac
done
[ "$checked" != . ] || refuse
rm -rf -- "$checked"
mkdir -p -- "$checked"
