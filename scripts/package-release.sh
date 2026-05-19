#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_DIR_NAME="ai-speech-to-text"
OUT_DIR="$ROOT_DIR/release"

VERSION="$(
  sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT_DIR/package.json" | head -n 1
)"
if [[ -z "$VERSION" ]]; then
  echo "Unable to read version from package.json" >&2
  exit 1
fi
ZIP_NAME="${PLUGIN_DIR_NAME}-v${VERSION}.zip"

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT

mkdir -p "$STAGE_DIR/$PLUGIN_DIR_NAME"
mkdir -p "$OUT_DIR"

copy_path() {
  local rel="$1"
  if [[ -e "$ROOT_DIR/$rel" ]]; then
    cp -a "$ROOT_DIR/$rel" "$STAGE_DIR/$PLUGIN_DIR_NAME/"
  fi
}

# Runtime-required files
copy_path "plugin.json"
copy_path "package.json"
copy_path "main.py"
copy_path "controller_listener.py"
copy_path "LICENSE"
copy_path "README.md"
copy_path "dist"
copy_path "bin"
copy_path "py_modules"
copy_path "config"
copy_path "logs"

# Drop bytecode caches from packaged output.
find "$STAGE_DIR/$PLUGIN_DIR_NAME" -type d -name "__pycache__" -prune -exec rm -rf {} +

(
  cd "$STAGE_DIR"
  zip -r "$OUT_DIR/$ZIP_NAME" "$PLUGIN_DIR_NAME" >/dev/null
)

echo "Created: $OUT_DIR/$ZIP_NAME"
