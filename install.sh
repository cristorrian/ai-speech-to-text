#!/bin/bash
set -euo pipefail

PLUGIN_NAME="ai-speech-to-text"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="/home/deck/homebrew/plugins/${PLUGIN_NAME}"

echo "Installing ${PLUGIN_NAME} to ${DEST_DIR}"
mkdir -p "${DEST_DIR}"

EXISTING_PROFILES=""
if [[ -f "${DEST_DIR}/config/transcription_profiles.json" ]]; then
  EXISTING_PROFILES="$(mktemp)"
  cp "${DEST_DIR}/config/transcription_profiles.json" "${EXISTING_PROFILES}"
fi

cp -r "${SRC_DIR}"/* "${DEST_DIR}/"

if [[ -n "${EXISTING_PROFILES}" && -f "${DEST_DIR}/config/transcription_profiles.json" ]]; then
  python3 - "${EXISTING_PROFILES}" "${DEST_DIR}/config/transcription_profiles.json" <<'PY'
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

echo "Done. Restart Decky Loader to load the plugin."
