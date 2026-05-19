#!/bin/bash
set -euo pipefail

PLUGIN_DIR_NAME="${PLUGIN_DIR_NAME:-ai-speech-to-text}"
PLUGIN_DEST="/home/deck/homebrew/plugins/${PLUGIN_DIR_NAME}"
SETTINGS_DIR="/home/deck/homebrew/settings/${PLUGIN_DIR_NAME}"
LOG_DIR="/home/deck/homebrew/logs/${PLUGIN_DIR_NAME}"

PURGE_DATA="false"
if [[ "${1:-}" == "--purge-data" ]]; then
  PURGE_DATA="true"
fi

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

echo "Uninstalling ${PLUGIN_DIR_NAME}"
if [[ -d "$PLUGIN_DEST" ]]; then
  run_root rm -rf "$PLUGIN_DEST"
  echo "Removed plugin directory: $PLUGIN_DEST"
else
  echo "Plugin directory not found: $PLUGIN_DEST"
fi

if [[ "$PURGE_DATA" == "true" ]]; then
  rm -rf "$SETTINGS_DIR" "$LOG_DIR"
  echo "Removed settings/logs data."
else
  echo "Keeping settings/logs data."
  echo "Use '--purge-data' to remove:"
  echo "  $SETTINGS_DIR"
  echo "  $LOG_DIR"
fi

echo "Restarting Decky Loader"
run_root systemctl restart plugin_loader.service

echo "Restarting Steam client"
systemctl --user restart app-steam@autostart.service

echo "Done. ${PLUGIN_DIR_NAME} uninstalled."
