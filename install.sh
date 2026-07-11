#!/bin/bash
set -euo pipefail

PLUGIN_NAME="ai-speech-to-text"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="/home/deck/homebrew/plugins/${PLUGIN_NAME}"
SETTINGS_DIR="/home/deck/homebrew/settings/${PLUGIN_NAME}"

run_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

run_user_systemctl() {
  local user="${SUDO_USER:-${USER:-deck}}"
  if [[ "${EUID}" -eq 0 && "${user}" != "root" ]]; then
    local uid
    uid="$(id -u "${user}")"
    sudo -u "${user}" XDG_RUNTIME_DIR="/run/user/${uid}" systemctl --user "$@"
  else
    systemctl --user "$@"
  fi
}

echo "Installing ${PLUGIN_NAME} to ${DEST_DIR}"
run_root mkdir -p "${DEST_DIR}"
mkdir -p "${SETTINGS_DIR}"

for required in plugin.json package.json main.py dist; do
  if [[ ! -e "${SRC_DIR}/${required}" ]]; then
    echo "Invalid plugin source dir: missing ${required}" >&2
    exit 1
  fi
done

EXISTING_PROFILES=""
if [[ -f "${SETTINGS_DIR}/transcription_profiles.json" ]]; then
  EXISTING_PROFILES="$(mktemp)"
  cp "${SETTINGS_DIR}/transcription_profiles.json" "${EXISTING_PROFILES}"
fi

# Install plugin payload, excluding dev artifacts that bloat installs.
run_root rsync -a --delete \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude '__pycache__/' \
  --exclude 'logs/' \
  "${SRC_DIR}/" "${DEST_DIR}/"

# Seed settings template if missing.
if [[ -f "${DEST_DIR}/config/transcription_profiles.json" && ! -f "${SETTINGS_DIR}/transcription_profiles.json" ]]; then
  cp -a "${DEST_DIR}/config/transcription_profiles.json" "${SETTINGS_DIR}/transcription_profiles.json"
fi

# If the settings file exists, merge API keys forward when the template changes.
if [[ -n "${EXISTING_PROFILES}" && -f "${SETTINGS_DIR}/transcription_profiles.json" ]]; then
  python3 - "${EXISTING_PROFILES}" "${SETTINGS_DIR}/transcription_profiles.json" <<'PY'
import json
import sys
from pathlib import Path

old_path = Path(sys.argv[1])
new_path = Path(sys.argv[2])

try:
    old_cfg = json.loads(old_path.read_text(encoding="utf-8"))
    new_cfg = json.loads(new_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

old_profiles = old_cfg.get("profiles", [])
new_profiles = new_cfg.get("profiles", [])
if not isinstance(old_profiles, list) or not isinstance(new_profiles, list):
    raise SystemExit(0)

def norm(v):
    return str(v or "").strip().lower()

old_by_name = {}
old_by_identity = {}
for p in old_profiles:
    if not isinstance(p, dict):
        continue
    key = str(p.get("api_key", "") or "").strip()
    if not key:
        continue
    name = str(p.get("name", "")).strip()
    if name:
        old_by_name[name] = key
    ident = (norm(p.get("provider")), norm(p.get("model")), norm(p.get("api_url")))
    if any(ident):
        old_by_identity[ident] = key

changed = False
for p in new_profiles:
    if not isinstance(p, dict):
        continue
    current = str(p.get("api_key", "") or "").strip()
    if current:
        continue
    name = str(p.get("name", "")).strip()
    ident = (norm(p.get("provider")), norm(p.get("model")), norm(p.get("api_url")))
    restored = old_by_name.get(name) or old_by_identity.get(ident)
    if restored:
        p["api_key"] = restored
        changed = True

if changed:
    new_cfg["profiles"] = new_profiles
    new_path.write_text(json.dumps(new_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
PY
  rm -f "${EXISTING_PROFILES}"
fi

echo "Restarting Decky Loader"
run_root systemctl restart plugin_loader.service

echo "Restarting Steam client"
run_user_systemctl restart app-steam@autostart.service

echo "Done. Plugin installed and services restarted."
