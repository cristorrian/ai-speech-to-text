#!/usr/bin/env python3
import json
import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PY_MODULES_DIR = os.path.join(PLUGIN_DIR, "py_modules")
if os.path.isdir(PY_MODULES_DIR):
    sys.path.insert(0, PY_MODULES_DIR)

import evdev
from evdev import ecodes

RUNTIME_DIR = "/tmp/ai-speech-to-text"
os.makedirs(RUNTIME_DIR, exist_ok=True)
STATE_FILE = os.path.join(RUNTIME_DIR, "ai_speech_to_text_state")
PID_FILE = os.path.join(RUNTIME_DIR, "ai_speech_to_text_listener.pid")
CONFIG_FILE = os.path.join(PLUGIN_DIR, "config", "decky_button_config.json")

BUTTON_CODES = {
    "L1": [310],
    "R1": [311],
    # SteamOS/Steam Input can expose stick clicks as BTN_THUMB* on the virtual
    # XInput pad, or as SELECT/START on some profiles.
    "L3": [317, 314],
    "R3": [318, 315],
    "A": [304],
    "B": [305],
    "X": [307],
    "Y": [308],
    "DPAD_UP": [544],
    "DPAD_DOWN": [545],
    "DPAD_LEFT": [546],
    "DPAD_RIGHT": [547],
}

TRIGGER_AXES = {"L2": 2, "R2": 5}
TRIGGER_BUTTONS = {"L2": 312, "R2": 313}
TRIGGER_THRESHOLD = 128
BUTTON_OPTIONS = ["L1", "R1", "L2", "R2", "L3", "R3", "A", "B", "X", "Y", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"]


def normalize_buttons(buttons):
    if not isinstance(buttons, list):
        buttons = []
    normalized = [button for button in buttons if button in BUTTON_OPTIONS]
    first = normalized[0] if len(normalized) > 0 else "L1"
    second = normalized[1] if len(normalized) > 1 else "R1"
    if second == first:
        second = next((button for button in BUTTON_OPTIONS if button != first), "R1")
    return [first, second]


def _has_gamepad_keys(caps):
    if ecodes.EV_KEY not in caps:
        return False
    keys = caps[ecodes.EV_KEY]
    needed = [304, 305, 307, 308, 310, 311, 312, 313, 314, 315, 316, 317, 318]
    return any(code in keys for code in needed)


def _has_trigger_axes(caps):
    if ecodes.EV_ABS not in caps:
        return False
    axes = caps[ecodes.EV_ABS]
    axis_codes = [a[0] if isinstance(a, tuple) else a for a in axes]
    return (2 in axis_codes) or (5 in axis_codes)


def load_button_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                if isinstance(cfg.get("global"), dict):
                    app_id = str(cfg.get("active_app_id", "") or "")
                    profiles = cfg.get("profiles", {}) if isinstance(cfg.get("profiles"), dict) else {}
                    profile = profiles.get(app_id) if app_id else None
                    if not isinstance(profile, dict):
                        profile = cfg.get("global", {})
                    buttons = profile.get("buttons", ["L1", "R1"])
                else:
                    buttons = cfg.get("buttons", ["L1", "R1"])
                return normalize_buttons(buttons)
        except Exception:
            pass
    return ["L1", "R1"]


def find_gamepad():
    candidates = []
    preferred_path = os.environ.get("VOICEINPUT_DEVICE_PATH", "").strip()
    if preferred_path:
        try:
            d = evdev.InputDevice(preferred_path)
            print(f"Using forced device path: {preferred_path} ({d.name})", flush=True)
            return d
        except Exception as e:
            print(f"Forced device path failed: {preferred_path} ({e})", flush=True)

    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
            name = d.name.lower()
            caps = d.capabilities()
            has_buttons = _has_gamepad_keys(caps)
            has_triggers = _has_trigger_axes(caps)
            print(
                f"Device scan: path={path} name='{d.name}' has_buttons={has_buttons} has_triggers={has_triggers}",
                flush=True,
            )
            if has_buttons or has_triggers:
                score = 0
                if any(k in name for k in ["steam deck", "valve", "xbox", "x-box", "gamepad", "controller"]):
                    score += 10
                if has_buttons:
                    score += 4
                if has_triggers:
                    score += 2
                # Prefer event nodes often associated with active controller instances in game mode
                if path.endswith("event10") or path.endswith("event12") or path.endswith("event18"):
                    score += 1
                candidates.append((score, path, d.name, d))
                if score >= 12:
                    print(f"Selected preferred gamepad: {path} {d.name}", flush=True)
                    return d
        except Exception:
            pass
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        score, path, dev_name, dev = candidates[0]
        print(f"Candidates ranked: {[{'score': c[0], 'path': c[1], 'name': c[2]} for c in candidates[:6]]}", flush=True)
        print(f"Selected fallback gamepad: {path} {dev_name}", flush=True)
        return dev
    print("No compatible EV_KEY gamepad candidates found. Device scan:", flush=True)
    for path in evdev.list_devices():
        try:
            d = evdev.InputDevice(path)
            print(f"  - {path}: {d.name}", flush=True)
        except Exception:
            pass

    # Fallback final: intentar abrir /dev/input/event* por orden
    for idx in range(0, 32):
        ev_path = f"/dev/input/event{idx}"
        if not os.path.exists(ev_path):
            continue
        try:
            d = evdev.InputDevice(ev_path)
            caps = d.capabilities()
            if _has_gamepad_keys(caps) or _has_trigger_axes(caps):
                    print(f"Selected event fallback: {ev_path} {d.name}", flush=True)
                    return d
        except Exception as e:
            print(f"Event fallback failed for {ev_path}: {e}", flush=True)
    return None


def build_button_info(buttons):
    info = []
    for name in buttons:
        is_trigger = name in TRIGGER_AXES
        codes = [TRIGGER_AXES.get(name)] if is_trigger else BUTTON_CODES.get(name)
        if not codes or codes[0] is None:
            print(f"Invalid button: {name}", flush=True)
            sys.exit(1)
        info.append({
            "name": name,
            "is_trigger": is_trigger,
            "codes": codes,
            "code": codes[0],
            "digital_code": TRIGGER_BUTTONS.get(name),
            "pressed": False,
        })
    return info


def main():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    with open(STATE_FILE, "w") as f:
        f.write("0")

    buttons = load_button_config()
    info = build_button_info(buttons)

    print(f"Configured combo buttons={buttons}", flush=True)

    active = False
    try:
        while True:
            dev = find_gamepad()
            if not dev:
                print("No gamepad found, retrying...", flush=True)
                import time
                time.sleep(1.0)
                continue

            print(f"Listening on device: {dev.path} {dev.name}", flush=True)
            try:
                for event in dev.read_loop():
                    changed = False
                    if event.type == ecodes.EV_KEY:
                        for b in info:
                            if (not b["is_trigger"]) and event.code in b["codes"]:
                                b["pressed"] = event.value == 1
                                changed = True
                                print(f"EV_KEY {b['name']} code={event.code} value={event.value} pressed={b['pressed']}", flush=True)
                            elif b["is_trigger"] and b["digital_code"] and event.code == b["digital_code"]:
                                b["pressed"] = event.value == 1
                                changed = True
                                print(f"EV_KEY(trigger-digital) {b['name']} code={event.code} value={event.value} pressed={b['pressed']}", flush=True)
                    elif event.type == ecodes.EV_ABS:
                        for b in info:
                            if b["is_trigger"] and event.code == b["code"]:
                                b["pressed"] = abs(event.value) > TRIGGER_THRESHOLD
                                changed = True
                                print(
                                    f"EV_ABS {b['name']} axis={event.code} value={event.value} threshold={TRIGGER_THRESHOLD} pressed={b['pressed']}",
                                    flush=True,
                                )

                    if changed:
                        now = all(b["pressed"] for b in info)
                        if now and not active:
                            active = True
                            print("Combo active -> STATE=1", flush=True)
                            with open(STATE_FILE, "w") as f:
                                f.write("1")
                        elif (not now) and active:
                            active = False
                            print("Combo released -> STATE=0", flush=True)
                            with open(STATE_FILE, "w") as f:
                                f.write("0")
            except OSError as e:
                print(f"Device read failed ({e}), re-scanning...", flush=True)
                for b in info:
                    b["pressed"] = False
                if active:
                    active = False
                    with open(STATE_FILE, "w") as f:
                        f.write("0")
                import time
                time.sleep(0.5)
                continue
    finally:
        for p in [STATE_FILE, PID_FILE]:
            try:
                os.remove(p)
            except Exception:
                pass


if __name__ == "__main__":
    main()
