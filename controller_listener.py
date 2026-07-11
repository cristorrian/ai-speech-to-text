#!/usr/bin/env python3
import json
import os
import select
import struct
import time

RUNTIME_DIR = "/tmp/ai-speech-to-text"
os.makedirs(RUNTIME_DIR, exist_ok=True)
STATE_FILE = os.path.join(RUNTIME_DIR, "ai_speech_to_text_state")
PID_FILE = os.path.join(RUNTIME_DIR, "ai_speech_to_text_listener.pid")
SETTINGS_DIR = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR", "").strip() or os.path.expanduser("~/homebrew/settings/ai-speech-to-text")
CONFIG_FILE = os.path.join(SETTINGS_DIR, "decky_button_config.json")

STEAM_DECK_BUTTON_OPTIONS = [
    "A", "B", "X", "Y",
    "L1", "R1", "L2", "R2", "L3", "R3",
    "L4", "R4", "L5", "R5",
    "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
    "SELECT", "START", "STEAM", "QAM",
    "LEFT_PAD_CLICK", "RIGHT_PAD_CLICK",
]
VALVE_VID = "28DE"
STEAM_DECK_PID = "1205"
HID_PACKET_SIZE = 64
HIDIOCSFEATURE = lambda size: 0xC0000000 | (size << 16) | (ord("H") << 8) | 0x06
ID_CLEAR_DIGITAL_MAPPINGS = 0x81
ID_SET_SETTINGS_VALUES = 0x87
SETTING_LEFT_TRACKPAD_MODE = 0x07
SETTING_RIGHT_TRACKPAD_MODE = 0x08
SETTING_STEAM_WATCHDOG_ENABLE = 0x2D
TRACKPAD_NONE = 0x07
BUTTONS_L = {
    "R2": 0x00000001,
    "L2": 0x00000002,
    "R1": 0x00000004,
    "L1": 0x00000008,
    "Y": 0x00000010,
    "B": 0x00000020,
    "X": 0x00000040,
    "A": 0x00000080,
    "DPAD_UP": 0x00000100,
    "DPAD_RIGHT": 0x00000200,
    "DPAD_LEFT": 0x00000400,
    "DPAD_DOWN": 0x00000800,
    "SELECT": 0x00001000,
    "STEAM": 0x00002000,
    "START": 0x00004000,
    "L5": 0x00008000,
    "R5": 0x00010000,
    "LEFT_PAD_CLICK": 0x00080000,
    "RIGHT_PAD_CLICK": 0x00100000,
    "L3": 0x00400000,
    "R3": 0x04000000,
}
BUTTONS_H = {
    "L4": 0x00000200,
    "R4": 0x00000400,
    "QAM": 0x00040000,
}


def normalize_steam_deck_button(button):
    button = str(button or "L5").strip().upper()
    return button if button in STEAM_DECK_BUTTON_OPTIONS else "L5"


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
                    return normalize_steam_deck_button(profile.get("steam_deck_button"))
                return normalize_steam_deck_button(cfg.get("steam_deck_button"))
        except Exception:
            pass
    return "L5"


def find_hidraw_device():
    candidates = []
    for idx in range(0, 16):
        path = f"/dev/hidraw{idx}"
        if not os.path.exists(path):
            continue
        uevent_path = f"/sys/class/hidraw/hidraw{idx}/device/uevent"
        try:
            with open(uevent_path, "r") as f:
                content = f.read().upper()
            if VALVE_VID in content and STEAM_DECK_PID in content:
                candidates.append((idx, path))
                print(f"Found Valve hidraw candidate: {path}", flush=True)
        except Exception as e:
            print(f"Cannot inspect {uevent_path}: {e}", flush=True)
    for idx, path in candidates:
        try:
            link_target = os.readlink(f"/sys/class/hidraw/hidraw{idx}")
            if ":1.2/" in link_target:
                print(f"Selected Steam Deck hidraw gamepad interface: {path}", flush=True)
                return path
        except Exception:
            pass
    if candidates:
        path = candidates[-1][1]
        print(f"Selected fallback Steam Deck hidraw interface: {path}", flush=True)
        return path
    return None


def send_feature_report(fd, data):
    try:
        import fcntl
        buf = bytes(data) + bytes(64 - len(data))
        fcntl.ioctl(fd, HIDIOCSFEATURE(64), buf)
        return True
    except Exception as e:
        print(f"Feature report failed: {e}", flush=True)
        return False


def open_hidraw_device():
    path = find_hidraw_device()
    if not path:
        return None, None
    try:
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        send_feature_report(fd, [ID_CLEAR_DIGITAL_MAPPINGS])
        send_feature_report(
            fd,
            [
                ID_SET_SETTINGS_VALUES,
                3,
                SETTING_LEFT_TRACKPAD_MODE, TRACKPAD_NONE,
                SETTING_RIGHT_TRACKPAD_MODE, TRACKPAD_NONE,
                SETTING_STEAM_WATCHDOG_ENABLE, 0,
            ],
        )
        print(f"Opened Steam Deck hidraw device: {path}", flush=True)
        return fd, path
    except Exception as e:
        print(f"Could not open Steam Deck hidraw device {path}: {e}", flush=True)
        return None, None


def steam_deck_button_pressed(data, button):
    if len(data) < 16:
        return False
    buttons_l = struct.unpack("<I", data[8:12])[0]
    buttons_h = struct.unpack("<I", data[12:16])[0]
    return bool((buttons_l & BUTTONS_L.get(button, 0)) or (buttons_h & BUTTONS_H.get(button, 0)))


def run_button_listener(button):
    active = False
    while True:
        fd, path = open_hidraw_device()
        if fd is None:
            print("No Steam Deck hidraw device found, retrying...", flush=True)
            time.sleep(1.0)
            continue
        try:
            print(f"Listening on Steam Deck button {button} via {path}", flush=True)
            while True:
                readable, _, _ = select.select([fd], [], [], 0.5)
                if not readable:
                    continue
                data = os.read(fd, HID_PACKET_SIZE)
                pressed = steam_deck_button_pressed(data, button)
                if pressed and not active:
                    active = True
                    print(f"Steam Deck button {button} active -> STATE=1", flush=True)
                    with open(STATE_FILE, "w") as f:
                        f.write("1")
                elif (not pressed) and active:
                    active = False
                    print(f"Steam Deck button {button} released -> STATE=0", flush=True)
                    with open(STATE_FILE, "w") as f:
                        f.write("0")
        except OSError as e:
            print(f"Steam Deck hidraw read failed ({e}), reconnecting...", flush=True)
            if active:
                active = False
                with open(STATE_FILE, "w") as f:
                    f.write("0")
            time.sleep(0.5)
        finally:
            try:
                os.close(fd)
            except Exception:
                pass


def main():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    with open(STATE_FILE, "w") as f:
        f.write("0")

    button = load_button_config()
    print(f"Configured Steam Deck button={button}", flush=True)
    try:
        run_button_listener(button)
    finally:
        for path in [STATE_FILE, PID_FILE]:
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == "__main__":
    main()
