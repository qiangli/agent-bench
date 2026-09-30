#!/bin/sh
# Remove build outputs. BUILD_DIR defaults to ./build (relative to this script).
set -eu
cd "$(dirname "$0")"
BUILD_DIR=${BUILD_DIR:-build}
case $BUILD_DIR in
  "" | /* | . | .. | ../* | */.. | */../*) echo "clean.sh: refusing to remove '$BUILD_DIR'" >&2; exit 2 ;;
esac
rm -rf -- "$BUILD_DIR"
mkdir -p -- "$BUILD_DIR"
