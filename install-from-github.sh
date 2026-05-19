#!/bin/bash
set -euo pipefail

REPO_OWNER="${REPO_OWNER:-cristorrian}"
REPO_NAME="${REPO_NAME:-ai-speech-to-text}"
REPO_REF="${REPO_REF:-main}"
PLUGIN_DIR_NAME="${PLUGIN_DIR_NAME:-ai-speech-to-text}"

PLUGIN_DEST="/home/deck/homebrew/plugins/${PLUGIN_DIR_NAME}"
SETTINGS_DIR="/home/deck/homebrew/settings/${PLUGIN_DIR_NAME}"
ZIP_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/${REPO_REF}.zip"

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

if command -v curl >/dev/null 2>&1; then
  DL_CMD="curl"
elif command -v wget >/dev/null 2>&1; then
  DL_CMD="wget"
else
  echo "Missing downloader. Install curl or wget." >&2
  exit 1
fi

if command -v unzip >/dev/null 2>&1; then
  EXTRACT_CMD="unzip"
elif command -v bsdtar >/dev/null 2>&1; then
  EXTRACT_CMD="bsdtar"
else
  echo "Missing extractor. Install unzip or bsdtar." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ZIP_PATH="${TMP_DIR}/plugin.zip"
SRC_DIR="${TMP_DIR}/src"
mkdir -p "$SRC_DIR"

echo "Downloading ${ZIP_URL}"
if [[ "$DL_CMD" == "curl" ]]; then
  curl -fL "$ZIP_URL" -o "$ZIP_PATH"
else
  wget -O "$ZIP_PATH" "$ZIP_URL"
fi

echo "Extracting plugin source"
if [[ "$EXTRACT_CMD" == "unzip" ]]; then
  unzip -q "$ZIP_PATH" -d "$SRC_DIR"
else
  bsdtar -xf "$ZIP_PATH" -C "$SRC_DIR"
fi

EXTRACTED_ROOT="$(find "$SRC_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "${EXTRACTED_ROOT:-}" ]]; then
  echo "Could not find extracted repository directory." >&2
  exit 1
fi

for required in plugin.json package.json main.py dist; do
  if [[ ! -e "${EXTRACTED_ROOT}/${required}" ]]; then
    echo "Invalid plugin package: missing ${required}" >&2
    exit 1
  fi
done

echo "Installing to ${PLUGIN_DEST}"
run_root mkdir -p /home/deck/homebrew/plugins
run_root rm -rf "$PLUGIN_DEST"
run_root mkdir -p "$PLUGIN_DEST"
run_root cp -a "${EXTRACTED_ROOT}/." "$PLUGIN_DEST/"

echo "Ensuring settings directory exists at ${SETTINGS_DIR}"
mkdir -p "$SETTINGS_DIR"

if [[ -f "${PLUGIN_DEST}/config/transcription_profiles.json" && ! -f "${SETTINGS_DIR}/transcription_profiles.json" ]]; then
  echo "Copying default transcription profile template to settings directory"
  cp -a "${PLUGIN_DEST}/config/transcription_profiles.json" "${SETTINGS_DIR}/transcription_profiles.json"
fi

echo "Restarting Decky Loader"
run_root systemctl restart plugin_loader.service

echo "Restarting Steam client"
systemctl --user restart app-steam@autostart.service

echo "Done. Plugin installed from ${REPO_OWNER}/${REPO_NAME}@${REPO_REF}."
