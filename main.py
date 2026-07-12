import json
import logging
import unicodedata
import base64
import fcntl
import os
import subprocess
import tempfile
import threading
import sys
import struct
import traceback
import shutil
import urllib.error
import urllib.request
import uuid
import ssl
from pathlib import Path

import decky_plugin  # type: ignore[import-not-found]

def _decky_settings_dir() -> Path:
    p = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR", "").strip()
    if p:
        return Path(p)
    return Path(os.path.expanduser("~/homebrew/settings/ai-speech-to-text"))


def _decky_log_file() -> str:
    log_dir = os.environ.get("DECKY_PLUGIN_LOG_DIR", "").strip()
    if log_dir:
        d = Path(log_dir)
    else:
        d = Path(os.path.expanduser("~/homebrew/logs/ai-speech-to-text"))
    d.mkdir(parents=True, exist_ok=True)
    return str(d / "ai-speech-to-text.log")


logging.basicConfig(
    filename=_decky_log_file(),
    format="AISpeechToText: %(asctime)s %(levelname)s %(message)s",
    filemode="a",
    force=True,
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

STEAM_DECK_BUTTON_OPTIONS = (
    "A", "B", "X", "Y",
    "L1", "R1", "L2", "R2", "L3", "R3",
    "L4", "R4", "L5", "R5",
    "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
    "SELECT", "START", "STEAM", "QAM",
    "LEFT_PAD_CLICK", "RIGHT_PAD_CLICK",
)
ENTER_MODE_OPTIONS = ("before", "after", "before_after", "none")

EV_SYN = 0
EV_KEY = 1
SYN_REPORT = 0
BUS_USB = 0x03
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
UI_DEV_SETUP = 0x405C5503

KEY_ESC = 1
KEY_1 = 2
KEY_2 = 3
KEY_3 = 4
KEY_4 = 5
KEY_5 = 6
KEY_6 = 7
KEY_7 = 8
KEY_8 = 9
KEY_9 = 10
KEY_0 = 11
KEY_MINUS = 12
KEY_EQUAL = 13
KEY_BACKSPACE = 14
KEY_TAB = 15
KEY_Q = 16
KEY_W = 17
KEY_E = 18
KEY_R = 19
KEY_T = 20
KEY_Y = 21
KEY_U = 22
KEY_I = 23
KEY_O = 24
KEY_P = 25
KEY_LEFTBRACE = 26
KEY_RIGHTBRACE = 27
KEY_ENTER = 28
KEY_LEFTCTRL = 29
KEY_A = 30
KEY_S = 31
KEY_D = 32
KEY_F = 33
KEY_G = 34
KEY_H = 35
KEY_J = 36
KEY_K = 37
KEY_L = 38
KEY_SEMICOLON = 39
KEY_APOSTROPHE = 40
KEY_GRAVE = 41
KEY_LEFTSHIFT = 42
KEY_BACKSLASH = 43
KEY_Z = 44
KEY_X = 45
KEY_C = 46
KEY_V = 47
KEY_B = 48
KEY_N = 49
KEY_M = 50
KEY_COMMA = 51
KEY_DOT = 52
KEY_SLASH = 53
KEY_RIGHTSHIFT = 54
KEY_F1 = 59
KEY_F2 = 60
KEY_F3 = 61
KEY_F4 = 62
KEY_F5 = 63
KEY_F6 = 64
KEY_F7 = 65
KEY_F8 = 66
KEY_F9 = 67
KEY_F10 = 68
KEY_LEFTALT = 56
KEY_SPACE = 57
KEY_F11 = 87
KEY_F12 = 88
KEY_RIGHTCTRL = 97
KEY_RIGHTALT = 100

LETTER_KEY_CODES = {
    "a": KEY_A, "b": KEY_B, "c": KEY_C, "d": KEY_D, "e": KEY_E, "f": KEY_F,
    "g": KEY_G, "h": KEY_H, "i": KEY_I, "j": KEY_J, "k": KEY_K, "l": KEY_L,
    "m": KEY_M, "n": KEY_N, "o": KEY_O, "p": KEY_P, "q": KEY_Q, "r": KEY_R,
    "s": KEY_S, "t": KEY_T, "u": KEY_U, "v": KEY_V, "w": KEY_W, "x": KEY_X,
    "y": KEY_Y, "z": KEY_Z,
}
DIGIT_KEY_CODES = {
    "1": KEY_1, "2": KEY_2, "3": KEY_3, "4": KEY_4, "5": KEY_5,
    "6": KEY_6, "7": KEY_7, "8": KEY_8, "9": KEY_9, "0": KEY_0,
}
TEXT_ENTRY_DEFAULT_PRE_KEY = "enter"
TEXT_ENTRY_DEFAULT_POST_KEY = "enter"
TEXT_ENTRY_KEY_ALIASES = {
    "return": "enter",
    "enter": "enter",
    "esc": "escape",
    "escape": "escape",
    "space": "space",
    "spacebar": "space",
    "tab": "tab",
    "slash": "/",
    "forwardslash": "/",
    "/": "/",
    "backslash": "\\",
    "\\": "\\",
    "minus": "-",
    "dash": "-",
    "-": "-",
    "period": ".",
    "dot": ".",
    ".": ".",
    "comma": ",",
    ",": ",",
    "semicolon": ";",
    ";": ";",
    "apostrophe": "'",
    "quote": "'",
    "'": "'",
    "grave": "`",
    "backtick": "`",
    "`": "`",
}
TEXT_ENTRY_NAMED_KEYS = {
    "enter": {"display": "Enter", "code": KEY_ENTER, "xdotool": "Return", "wtype": "Return"},
    "escape": {"display": "Esc", "code": KEY_ESC, "xdotool": "Escape", "wtype": "Escape"},
    "space": {"display": "Space", "code": KEY_SPACE, "xdotool": "space", "wtype": "space"},
    "tab": {"display": "Tab", "code": KEY_TAB, "xdotool": "Tab", "wtype": "Tab"},
    "/": {"display": "/", "code": KEY_SLASH, "xdotool": "slash", "wtype": "slash"},
    "\\": {"display": "\\", "code": KEY_BACKSLASH, "xdotool": "backslash", "wtype": "backslash"},
    "-": {"display": "-", "code": KEY_MINUS, "xdotool": "minus", "wtype": "minus"},
    ".": {"display": ".", "code": KEY_DOT, "xdotool": "period", "wtype": "period"},
    ",": {"display": ",", "code": KEY_COMMA, "xdotool": "comma", "wtype": "comma"},
    ";": {"display": ";", "code": KEY_SEMICOLON, "xdotool": "semicolon", "wtype": "semicolon"},
    "'": {"display": "'", "code": KEY_APOSTROPHE, "xdotool": "apostrophe", "wtype": "apostrophe"},
    "`": {"display": "`", "code": KEY_GRAVE, "xdotool": "grave", "wtype": "grave"},
}
for _idx, _code in enumerate((KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6, KEY_F7, KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12), start=1):
    TEXT_ENTRY_NAMED_KEYS[f"f{_idx}"] = {"display": f"F{_idx}", "code": _code, "xdotool": f"F{_idx}", "wtype": f"F{_idx}"}


def _normalize_enter_mode(mode):
    mode = str(mode or "before_after").strip().lower()
    return mode if mode in ENTER_MODE_OPTIONS else "before_after"


def _normalize_text_entry_key(value, default_key=TEXT_ENTRY_DEFAULT_POST_KEY):
    raw = str(value or "").strip().lower()
    if not raw:
        raw = default_key
    raw = TEXT_ENTRY_KEY_ALIASES.get(raw, raw)
    if len(raw) == 1 and raw in LETTER_KEY_CODES:
        return raw
    if raw in DIGIT_KEY_CODES:
        return raw
    if raw in TEXT_ENTRY_NAMED_KEYS:
        return raw
    fallback = TEXT_ENTRY_KEY_ALIASES.get(str(default_key or TEXT_ENTRY_DEFAULT_POST_KEY).strip().lower(), TEXT_ENTRY_DEFAULT_POST_KEY)
    return fallback if fallback in TEXT_ENTRY_NAMED_KEYS or fallback in LETTER_KEY_CODES or fallback in DIGIT_KEY_CODES else TEXT_ENTRY_DEFAULT_POST_KEY


def _text_entry_key_spec(value, default_key=TEXT_ENTRY_DEFAULT_POST_KEY):
    normalized = _normalize_text_entry_key(value, default_key)
    if normalized in LETTER_KEY_CODES:
        code = LETTER_KEY_CODES[normalized]
        return {"name": normalized, "display": normalized.upper(), "code": code, "xdotool": normalized, "wtype": normalized}
    if normalized in DIGIT_KEY_CODES:
        code = DIGIT_KEY_CODES[normalized]
        return {"name": normalized, "display": normalized, "code": code, "xdotool": normalized, "wtype": normalized}
    spec = dict(TEXT_ENTRY_NAMED_KEYS[normalized])
    spec["name"] = normalized
    return spec


def _install_runtime_exception_hooks():
    def _excepthook(exc_type, exc, tb):
        msg = "".join(traceback.format_exception(exc_type, exc, tb))
        logger.error("UNCAUGHT_EXCEPTION\n%s", msg)
        print(msg, file=sys.stderr, flush=True)

    def _thread_excepthook(args):
        msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        logger.error("UNCAUGHT_THREAD_EXCEPTION in %s\n%s", args.thread.name if args.thread else "unknown", msg)
        print(msg, file=sys.stderr, flush=True)

    sys.excepthook = _excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_excepthook


_install_runtime_exception_hooks()


class VoiceInputService:
    def __init__(self):
        self.config_dir = _decky_settings_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config"
        self.plugin_config_dir = self._plugin_dir() / "config"
        self.plugin_config_dir.mkdir(parents=True, exist_ok=True)
        self.transcription_profiles_file = self.config_dir / "transcription_profiles.json"
        self.openai_key_file = Path(os.path.expanduser("~/.config/voice-input/openai_api_key"))
        self.groq_key_file = Path(os.path.expanduser("~/.config/voice-input/groq_api_key"))
        self.api_key_file = Path(os.path.expanduser("~/.config/voice-input/api_key"))
        self.runtime_dir = Path("/tmp/ai-speech-to-text")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.audio_file = self.runtime_dir / "recording.wav"
        self.record_pid_file = self.runtime_dir / "record.pid"
        self.record_proc = None
        self.is_recording = False
        self.enabled = False
        self.lock = threading.Lock()
        self.last_text = ""
        self.last_error = ""
        self.last_method = ""
        self.enter_mode = "before_after"
        self.pre_key = TEXT_ENTRY_DEFAULT_PRE_KEY
        self.post_key = TEXT_ENTRY_DEFAULT_POST_KEY
        self.translate_to_english = False
        self.remote_play_typing = False
        self.transcription_provider = "grok"
        self.debug_logging = False
        self.active_app_id = ""
        self.active_app_name = ""
        self.clipboard_owner_proc = None
        self.clipboard_owner_tmp = None
        self.virtual_keyboard = None

    def _plugin_dir(self):
        return Path(os.environ.get("DECKY_PLUGIN_DIR") or Path(__file__).resolve().parent)

    def _tool_path(self, name: str):
        bundled = self._plugin_dir() / "bin" / name
        if bundled.exists():
            return str(bundled)
        return shutil.which(name) or f"/usr/bin/{name}"

    def close_virtual_keyboard(self):
        if self.virtual_keyboard is not None:
            try:
                fcntl.ioctl(self.virtual_keyboard, UI_DEV_DESTROY)
            except Exception:
                pass
            try:
                os.close(self.virtual_keyboard)
            except Exception:
                pass
            self.virtual_keyboard = None

    def ensure_virtual_keyboard(self):
        try:
            if self.virtual_keyboard is None:
                keys = [
                    *LETTER_KEY_CODES.values(),
                    KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9, KEY_0,
                    KEY_SPACE, KEY_ENTER, KEY_MINUS, KEY_EQUAL,
                    KEY_LEFTBRACE, KEY_RIGHTBRACE, KEY_BACKSLASH,
                    KEY_SEMICOLON, KEY_APOSTROPHE, KEY_GRAVE,
                    KEY_COMMA, KEY_DOT, KEY_SLASH,
                    KEY_ESC, KEY_TAB, KEY_BACKSPACE,
                    KEY_F1, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6,
                    KEY_F7, KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12,
                    KEY_LEFTSHIFT, KEY_RIGHTSHIFT,
                    KEY_LEFTCTRL, KEY_RIGHTCTRL,
                    KEY_LEFTALT, KEY_RIGHTALT,
                ]
                fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
                try:
                    fcntl.ioctl(fd, UI_SET_EVBIT, EV_KEY)
                    fcntl.ioctl(fd, UI_SET_EVBIT, EV_SYN)
                    for key_code in keys:
                        fcntl.ioctl(fd, UI_SET_KEYBIT, int(key_code))
                    name = b"AI Speech-to-Text Virtual Keyboard"
                    setup = struct.pack("HHHH80sI", BUS_USB, 0x1209, 0x0001, 1, name, 0)
                    fcntl.ioctl(fd, UI_DEV_SETUP, setup)
                    fcntl.ioctl(fd, UI_DEV_CREATE)
                except Exception:
                    os.close(fd)
                    raise
                self.virtual_keyboard = fd
                logger.info("virtual keyboard created via raw uinput")
                threading.Event().wait(0.5)
            return True
        except Exception:
            logger.exception("virtual keyboard creation failed")
            self.close_virtual_keyboard()
            return False

    def _virtual_keyboard_event(self, event_type, code, value):
        event = struct.pack("llHHi", 0, 0, int(event_type), int(code), int(value))
        os.write(self.virtual_keyboard, event)

    def _virtual_keyboard_syn(self):
        self._virtual_keyboard_event(EV_SYN, SYN_REPORT, 0)

    def _virtual_keyboard_key(self, key_code, shifted=False, hold=0.01):
        if self.virtual_keyboard is None and not self.ensure_virtual_keyboard():
            raise RuntimeError("Virtual keyboard is not available")
        if shifted:
            self._virtual_keyboard_event(EV_KEY, KEY_LEFTSHIFT, 1)
            self._virtual_keyboard_syn()
            threading.Event().wait(hold)
        self._virtual_keyboard_event(EV_KEY, key_code, 1)
        self._virtual_keyboard_syn()
        threading.Event().wait(hold)
        self._virtual_keyboard_event(EV_KEY, key_code, 0)
        self._virtual_keyboard_syn()
        if shifted:
            threading.Event().wait(hold)
            self._virtual_keyboard_event(EV_KEY, KEY_LEFTSHIFT, 0)
            self._virtual_keyboard_syn()
        threading.Event().wait(hold)

    def _runtime_env(self):
        env = os.environ.copy()
        uid = os.getuid()
        xdg = env.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
        gamescope_env = Path("/run/user/1000/gamescope-environment")
        if gamescope_env.exists():
            try:
                for raw_line in gamescope_env.read_text(errors="ignore").splitlines():
                    if "=" not in raw_line:
                        continue
                    key, value = raw_line.split("=", 1)
                    if key in {"DISPLAY", "XAUTHORITY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS", "LANG", "LC_CTYPE"} and value:
                        env[key] = value
                xdg = env.get("XDG_RUNTIME_DIR") or xdg
            except Exception:
                logger.exception("failed to read gamescope environment")
        env["XDG_RUNTIME_DIR"] = xdg
        env.setdefault("PIPEWIRE_RUNTIME_DIR", xdg)
        env.setdefault("WAYLAND_DISPLAY", "wayland-0")
        env.setdefault("DISPLAY", ":0")
        plugin_bin = self._plugin_dir() / "bin"
        env["PATH"] = f"{plugin_bin}:{env.get('PATH', '')}:/usr/bin:/bin:/usr/sbin:/sbin"
        # Force UTF-8 locale so clipboard paths preserve accents and Unicode.
        env.setdefault("LANG", "C.UTF-8")
        env.setdefault("LC_ALL", "C.UTF-8")
        env.setdefault("LC_CTYPE", "C.UTF-8")
        # Decky/PyInstaller may inject /tmp/_MEI* libraries that break system binaries.
        env.pop("LD_LIBRARY_PATH", None)
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        return env

    def _verbose(self, msg: str, *args):
        if self.debug_logging:
            logger.info(msg, *args)
        else:
            logger.debug(msg, *args)

    def stop_clipboard_owner(self):
        if self.clipboard_owner_proc is not None:
            try:
                if self.clipboard_owner_proc.poll() is None:
                    self.clipboard_owner_proc.terminate()
                    self.clipboard_owner_proc.wait(timeout=0.8)
            except Exception:
                try:
                    self.clipboard_owner_proc.kill()
                except Exception:
                    pass
            self.clipboard_owner_proc = None
        if self.clipboard_owner_tmp:
            try:
                os.remove(self.clipboard_owner_tmp)
            except Exception:
                pass
            self.clipboard_owner_tmp = None

    def _parse_shell_config(self, content: str):
        cfg = {}
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip().lower()
            value = v.strip().strip('"').strip("'")
            cfg[key] = value
        return cfg

    def _build_ssl_context(self):
        ctx = ssl.create_default_context()
        ca_candidates = [
            os.environ.get("SSL_CERT_FILE", ""),
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/cert.pem",
        ]
        try:
            import certifi  # type: ignore
            ca_candidates.insert(0, certifi.where())
        except Exception:
            pass
        for ca_file in ca_candidates:
            if ca_file and os.path.exists(ca_file):
                try:
                    ctx.load_verify_locations(cafile=ca_file)
                    logger.info("ssl context using cafile=%s", ca_file)
                    return ctx
                except Exception:
                    continue
        logger.warning("ssl context fallback to system defaults")
        return ctx

    def _default_transcription_profiles(self):
        return {
            "profiles": [
                {
                    "name": "Grok Whisper Large v3",
                    "provider": "grok",
                    "model": "whisper-large-v3",
                    "language": "auto",
                    "api_key": "",
                    "api_url": "https://api.groq.com/openai/v1/audio/transcriptions",
                },
                {
                    "name": "OpenAI Whisper-1",
                    "provider": "openai",
                    "model": "whisper-1",
                    "language": "auto",
                    "api_key": "",
                    "api_url": "https://api.openai.com/v1/audio/transcriptions",
                },
                {
                    "name": "OpenRouter Whisper Large v3 Turbo",
                    "provider": "openrouter",
                    "model": "openai/whisper-large-v3-turbo",
                    "language": "auto",
                    "api_key": "",
                    "api_url": "https://openrouter.ai/api/v1/audio/transcriptions",
                },
                {
                    "name": "OpenRouter Voxtral Mini Transcribe",
                    "provider": "openrouter",
                    "model": "mistralai/voxtral-mini-transcribe",
                    "language": "auto",
                    "api_key": "",
                    "api_url": "https://openrouter.ai/api/v1/audio/transcriptions",
                },
            ],
        }

    def _load_transcription_profiles_config(self):
        cfg = self._default_transcription_profiles()
        should_write_default = not self.transcription_profiles_file.exists()
        try:
            if self.transcription_profiles_file.exists():
                loaded = json.loads(self.transcription_profiles_file.read_text())
                if isinstance(loaded, dict):
                    if "profiles" in loaded:
                        cfg.update({k: v for k, v in loaded.items() if k in ("profiles",)})
        except Exception:
            logger.exception("transcription profiles load failed")
            should_write_default = True

        profiles = cfg.get("profiles", {})
        if isinstance(profiles, dict):
            profiles = list(profiles.values())
        if not isinstance(profiles, list) or not profiles:
            profiles = self._default_transcription_profiles()["profiles"]
        normalized = []
        for item in profiles:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            provider = str(item.get("provider", "")).strip().lower()
            if provider == "groq":
                provider = "grok"
            model = str(item.get("model", "")).strip() or "whisper-1"
            language = str(item.get("language", "")).strip().lower() or "auto"
            api_url = str(item.get("api_url", "")).strip()
            api_key = str(item.get("api_key", "")).strip()
            normalized.append({"name": name or f"{(provider or 'custom')}-{model}", "provider": provider, "model": model, "language": language, "api_key": api_key, "api_url": api_url})
        profiles = normalized or self._default_transcription_profiles()["profiles"]

        if should_write_default:
            try:
                self.transcription_profiles_file.parent.mkdir(parents=True, exist_ok=True)
                cfg["profiles"] = profiles
                self.transcription_profiles_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
            except Exception:
                logger.exception("transcription profiles write failed")

        cfg["profiles"] = profiles
        return cfg

    def _load_transcription_provider(self, profile_name: str = ""):
        cfg = self._load_transcription_profiles_config()
        profiles = cfg.get("profiles", {})
        selected_name = str(profile_name or "").strip()
        profile_cfg = None
        for p in profiles:
            if str(p.get("name", "")).strip() == selected_name:
                profile_cfg = p
                break
        if profile_cfg is None:
            profile_cfg = profiles[0] if profiles else {}
        provider = str(profile_cfg.get("provider", "")).strip().lower()
        if provider == "groq":
            provider = "grok"
        if not provider:
            provider = "custom"
        model = str(profile_cfg.get("model", "")).strip() or "whisper-1"
        api_url = str(profile_cfg.get("api_url", "") or "").strip()
        api_key = str(profile_cfg.get("api_key", "") or "").strip()
        language = str(profile_cfg.get("language", "") or "").strip().lower() or "auto"
        profile_name = str(profile_cfg.get("name", "")).strip() or f"{provider}-{model}"
        return {
            "active_profile": profile_name,
            "name": profile_name,
            "provider": provider,
            "model": model,
            "language": language,
            "api_url": api_url,
            "api_key": api_key,
        }

    def load_config(self):
        cfg = {
            "provider": "groq",
            "language": "auto",
            "openai_model": "whisper-1",
            "groq_model": "whisper-large-v3",
            "enter_on_done": True,
            "debug_logging": False,
        }
        if self.config_file.exists():
            try:
                parsed = self._parse_shell_config(self.config_file.read_text())
                cfg.update(parsed)
            except Exception:
                pass

        # Normalización de tipos/valores
        cfg["provider"] = str(cfg.get("provider", "groq")).lower()
        cfg["language"] = "auto"
        cfg["openai_model"] = str(cfg.get("openai_model", "whisper-1"))
        cfg["groq_model"] = str(cfg.get("groq_model", "whisper-large-v3"))
        if isinstance(cfg.get("enter_on_done"), str):
            cfg["enter_on_done"] = cfg["enter_on_done"] in ("1", "true", "yes", "on")
        if isinstance(cfg.get("debug_logging"), str):
            cfg["debug_logging"] = cfg["debug_logging"].strip().lower() in ("1", "true", "yes", "on")
        else:
            cfg["debug_logging"] = bool(cfg.get("debug_logging", False))
        return cfg

    def _get_api(self):
        cfg = self.load_config()
        tx = self._load_transcription_provider(self.transcription_provider)
        provider = tx.get("provider", "grok")
        model = tx.get("model", "")
        api_key = tx.get("api_key", "").strip()
        api_url = str(tx.get("api_url", "") or "").strip()
        if not api_url:
            raise RuntimeError("Missing api_url in transcription profile")
        if not model:
            raise RuntimeError("Missing model in transcription profile")
        if not api_key:
            raise RuntimeError("Missing api_key in transcription profile")
        return provider, api_url, model, api_key, cfg

    @staticmethod
    def _resolve_audio_endpoint(provider: str, api_url: str, translate_to_english: bool):
        normalized_url = api_url.rstrip("/")
        is_openrouter = (provider == "openrouter") or ("openrouter.ai" in normalized_url.lower())
        translation_url = normalized_url[:-len("/transcriptions")] + "/translations" if normalized_url.endswith("/transcriptions") else ""

        if translate_to_english:
            if is_openrouter or not translation_url:
                raise RuntimeError("The selected transcription endpoint does not support audio translation to English")
            return translation_url, True
        return api_url, False

    def _transcribe_request(self, language: str):
        provider, api_url, model, api_key, _cfg = self._get_api()
        api_url, translating = self._resolve_audio_endpoint(provider, api_url, self.translate_to_english)
        self._verbose(
            "audio request profile=%s provider=%s model=%s translating=%s url=%s",
            self.transcription_provider,
            provider,
            model,
            translating,
            api_url,
        )
        audio_bytes = self.audio_file.read_bytes()
        is_openrouter = (provider == "openrouter") or ("openrouter.ai" in api_url.lower())

        if is_openrouter:
            payload = {
                "model": model,
                "input_audio": {
                    "data": base64.b64encode(audio_bytes).decode("ascii"),
                    "format": "wav",
                },
            }
            if language and language != "auto" and not translating:
                payload["language"] = language
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                    "Accept": "application/json",
                    "User-Agent": "curl/8.7.1",
                },
                method="POST",
            )
        else:
            boundary = f"----AISpeechToText{uuid.uuid4().hex}"
            fields = [
                ("model", model),
                ("response_format", "json"),
            ]
            if language and language != "auto" and not translating:
                fields.append(("language", language))

            body = bytearray()
            for key, value in fields:
                body.extend(f"--{boundary}\r\n".encode("utf-8"))
                body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
                body.extend(str(value).encode("utf-8"))
                body.extend(b"\r\n")
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                b'Content-Disposition: form-data; name="file"; filename="recording.wav"\r\n'
                b"Content-Type: audio/wav\r\n\r\n"
            )
            body.extend(audio_bytes)
            body.extend(b"\r\n")
            body.extend(f"--{boundary}--\r\n".encode("utf-8"))
            multipart_body = bytes(body)
            req = urllib.request.Request(
                api_url,
                data=multipart_body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Content-Length": str(len(multipart_body)),
                    "Accept": "application/json",
                    "User-Agent": "curl/8.7.1",
                },
                method="POST",
            )
        try:
            with urllib.request.urlopen(req, timeout=30, context=self._build_ssl_context()) as resp:
                out = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {err_body[:220]}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Transcription request failed: {str(e)[:220]}")
        self._verbose("transcribe provider=%s response len=%s", provider, len(out))
        data = json.loads(out)
        err = data.get("error", {}).get("message")
        if err:
            raise RuntimeError(str(err))
        text = (data.get("text") or data.get("output_text") or "").strip()
        return text

    def start_recording(self):
        with self.lock:
            if self.is_recording:
                logger.info("start_recording ignored: already recording")
                return
            self.last_error = ""
            self.audio_file.unlink(missing_ok=True)
            # Prefer native WAV recording with arecord, then fall back to pw-record.
            candidates = []
            arecord_bin = self._tool_path("arecord")
            pwrecord_bin = self._tool_path("pw-record")
            preferred = os.environ.get("VOICE_INPUT_RECORDER", "").strip().lower()

            arec_cmd = [arecord_bin, "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav", str(self.audio_file)]
            pw_cmd = [pwrecord_bin, "--rate=16000", "--channels=1", str(self.audio_file)]

            if preferred == "pw-record":
                if os.path.exists(pwrecord_bin):
                    candidates.append(pw_cmd)
                if os.path.exists(arecord_bin):
                    candidates.append(arec_cmd)
            elif preferred == "arecord":
                if os.path.exists(arecord_bin):
                    candidates.append(arec_cmd)
                if os.path.exists(pwrecord_bin):
                    candidates.append(pw_cmd)
            else:
                if os.path.exists(arecord_bin):
                    candidates.append(arec_cmd)
                if os.path.exists(pwrecord_bin):
                    candidates.append(pw_cmd)

            if not candidates:
                raise RuntimeError("No recording backend available (arecord/pw-record)")

            started = None
            last_backend_error = ""
            for cmd in candidates:
                logger.info("start_recording trying cmd=%s", " ".join(cmd))
                env = self._runtime_env()
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True)
                # Make sure the recorder does not exit immediately.
                try:
                    p.wait(timeout=0.25)
                    out, err = p.communicate(timeout=0.2)
                    logger.warning(
                        "recorder exited early rc=%s cmd=%s stderr=%s stdout=%s",
                        p.returncode,
                        " ".join(cmd),
                        (err or "").strip()[:400],
                        (out or "").strip()[:200],
                    )
                    last_backend_error = (err or out or "").strip()
                    continue
                except subprocess.TimeoutExpired:
                    started = (p, cmd)
                    break

            if not started:
                self.last_error = f"Recorder failed to start: {(last_backend_error[:180] if last_backend_error else 'backend exited rc=1')}"
                raise RuntimeError("Recorder failed to start")

            p, cmd = started
            self.record_proc = p
            self.record_pid_file.write_text(str(p.pid))
            self.is_recording = True
            logger.info("start_recording active pid=%s cmd=%s", p.pid, " ".join(cmd))

    def stop_recording(self):
        with self.lock:
            if not self.is_recording:
                logger.info("stop_recording ignored: not recording")
                return ""
            if self.record_pid_file.exists():
                pid = int(self.record_pid_file.read_text().strip())
                logger.info("stop_recording pid=%s", pid)
                try:
                    os.kill(pid, 15)
                except Exception:
                    logger.exception("stop_recording kill failed")
                    pass

                # Give the WAV writer a short flush window, then force-kill if needed.
                try:
                    if self.record_proc is not None and self.record_proc.pid == pid:
                        self.record_proc.wait(timeout=1.5)
                except Exception:
                    try:
                        os.kill(pid, 9)
                    except Exception:
                        pass

                self.record_pid_file.unlink(missing_ok=True)
            self.record_proc = None
            self.is_recording = False
        logger.info("stop_recording -> transcribe")
        return self.transcribe_and_type()

    def transcribe_and_type(self):
        if not self.audio_file.exists() or self.audio_file.stat().st_size < 1000:
            logger.warning("transcribe skipped: missing/short audio file")
            self.last_error = "Audio missing or too short"
            return ""

        cfg = self.load_config()
        tx = self._load_transcription_provider(self.transcription_provider)
        language = str(tx.get("language", "auto") or "auto").lower()
        try:
            text = self._transcribe_request(language)
        except Exception as e:
            self.last_error = str(e)[:220]
            logger.exception("transcribe_and_type failed profile=%s", self.transcription_provider)
            raise
        logger.info("transcribe text len=%s", len(text))
        self.last_text = text
        if text:
            self.type_text(text, self.enter_mode)
            self.last_error = ""
        return text

    def type_text(self, text: str, enter_mode: str):
        self._verbose("type_text len=%s enter_mode=%s", len(text), enter_mode)
        entry_mode = _normalize_enter_mode(enter_mode)
        has_pre_key = entry_mode in ("before", "before_after")
        has_post_key = entry_mode in ("after", "before_after")
        pre_key = _text_entry_key_spec(getattr(self, "pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY), TEXT_ENTRY_DEFAULT_PRE_KEY)
        post_key = _text_entry_key_spec(getattr(self, "post_key", TEXT_ENTRY_DEFAULT_POST_KEY), TEXT_ENTRY_DEFAULT_POST_KEY)
        post_enter_delay = 0.35
        env = self._runtime_env()
        env["YDOTOOL_SOCKET"] = "/tmp/.ydotool_socket"
        ydotool = self._tool_path("ydotool")
        wtype = self._tool_path("wtype")
        xdotool = self._tool_path("xdotool")
        xsel = self._tool_path("xsel")
        wl_copy = self._tool_path("wl-copy")
        xclip = self._tool_path("xclip")
        qdbus = next((self._tool_path(name) for name in ("qdbus", "qdbus6", "qdbus-qt5") if os.path.exists(self._tool_path(name))), None)
        is_gamemode = os.environ.get("XDG_SESSION_TYPE", "").lower() in {"wayland", "gamescope"} or bool(os.environ.get("STEAM_GAME"))
        has_non_ascii = any(ord(ch) > 127 for ch in text)
        self._verbose(
            "type_text backends exists: ydotool=%s wtype=%s xdotool=%s socket=%s gamemode_hint=%s session=%s non_ascii=%s",
            os.path.exists(ydotool),
            os.path.exists(wtype),
            os.path.exists(xdotool),
            env.get("YDOTOOL_SOCKET"),
            is_gamemode,
            os.environ.get("XDG_SESSION_TYPE", ""),
            has_non_ascii,
        )

        def _press_key(key_spec: dict, label: str) -> bool:
            if self.remote_play_typing and self.ensure_virtual_keyboard():
                self._virtual_keyboard_key(key_spec["code"])
                logger.info("type_text %s-key %s via virtual keyboard", label, key_spec["name"])
                threading.Event().wait(0.05)
                return True
            if os.path.exists(ydotool):
                ydotool_codes = [f"{key_spec['code']}:1", f"{key_spec['code']}:0"]
                r = subprocess.run([ydotool, "key", *ydotool_codes], env=env, check=False)
                logger.info("type_text %s-key %s via ydotool rc=%s", label, key_spec["name"], r.returncode)
                if r.returncode == 0:
                    threading.Event().wait(0.05)
                    return True
            if os.path.exists(wtype):
                r = subprocess.run([wtype, "-k", key_spec["wtype"]], env=env, check=False)
                logger.info("type_text %s-key %s via wtype rc=%s", label, key_spec["name"], r.returncode)
                if r.returncode == 0:
                    threading.Event().wait(0.05)
                    return True
            if os.path.exists(xdotool):
                r = subprocess.run([xdotool, "key", key_spec["xdotool"]], env=env, check=False)
                logger.info("type_text %s-key %s via xdotool rc=%s", label, key_spec["name"], r.returncode)
                if r.returncode == 0:
                    threading.Event().wait(0.05)
                    return True
            return False

        def _pre_text_input() -> bool:
            if not has_pre_key:
                return True
            return _press_key(pre_key, "pre")

        def _delay_before_post_key(label: str):
            logger.info("type_text delaying post-key via %s seconds=%s", label, post_enter_delay)
            threading.Event().wait(post_enter_delay)

        def _post_text_input(label: str, prefer_backend: str = "") -> bool:
            if not has_post_key:
                return True
            _delay_before_post_key(label)
            if prefer_backend == "ydotool" and os.path.exists(ydotool):
                r = subprocess.run([ydotool, "key", f"{post_key['code']}:1", f"{post_key['code']}:0"], env=env, check=False)
                logger.info("type_text %s post-key via ydotool rc=%s", label, r.returncode)
                return r.returncode == 0
            if prefer_backend == "wtype" and os.path.exists(wtype):
                r = subprocess.run([wtype, "-k", post_key["wtype"]], env=env, check=False)
                logger.info("type_text %s post-key via wtype rc=%s", label, r.returncode)
                return r.returncode == 0
            if prefer_backend == "xdotool" and os.path.exists(xdotool):
                r = subprocess.run([xdotool, "key", post_key["xdotool"]], env=env, check=False)
                logger.info("type_text %s post-key via xdotool rc=%s", label, r.returncode)
                return r.returncode == 0
            if prefer_backend == "virtual":
                self._virtual_keyboard_key(post_key["code"])
                logger.info("type_text %s post-key via virtual keyboard", label)
                return True
            return _press_key(post_key, "post")

        def _try_ydotool() -> bool:
            if not os.path.exists(ydotool):
                return False
            logger.info("type_text backend=ydotool start")
            r1 = subprocess.run([ydotool, "type", "--", text], env=env, check=False)
            logger.info("type_text backend=ydotool type rc=%s", r1.returncode)
            if r1.returncode != 0:
                return False
            if has_post_key:
                if not _post_text_input("ydotool", "ydotool"):
                    return False
            self.last_method = "ydotool-type"
            return True

        def _try_wtype() -> bool:
            if not os.path.exists(wtype):
                return False
            logger.info("type_text backend=wtype start")
            r1 = subprocess.run([wtype, "--", text], env=env, check=False)
            logger.info("type_text backend=wtype type rc=%s", r1.returncode)
            if r1.returncode != 0:
                return False
            if has_post_key:
                if not _post_text_input("wtype", "wtype"):
                    return False
            self.last_method = "wtype-type"
            return True

        def _try_xdotool() -> bool:
            if not os.path.exists(xdotool):
                return False
            logger.info("type_text backend=xdotool start")

            def _type_unicode_char(ch: str) -> bool:
                codepoint = ord(ch)
                hex_code = format(codepoint, "x")
                seq = ["key", "ctrl+shift+u"] + list(hex_code) + ["space"]
                r = subprocess.run([xdotool] + seq, env=env, check=False)
                logger.info("type_text xdotool unicode char=%s hex=%s rc=%s", ch, hex_code, r.returncode)
                return r.returncode == 0

            if has_non_ascii:
                for ch in text:
                    if ord(ch) < 128:
                        r = subprocess.run([xdotool, "type", "--delay", "0", "--", ch], env=env, check=False)
                        if r.returncode != 0:
                            logger.info("type_text xdotool ascii char rc=%s", r.returncode)
                            return False
                    else:
                        if not _type_unicode_char(ch):
                            return False
                logger.info("type_text backend=xdotool unicode path rc=0")
            else:
                r1 = subprocess.run([xdotool, "type", "--delay", "0", "--", text], env=env, check=False)
                logger.info("type_text backend=xdotool type rc=%s", r1.returncode)
                if r1.returncode != 0:
                    return False
            if has_post_key:
                if not _post_text_input("xdotool", "xdotool"):
                    return False
            self.last_method = "xdotool-type"
            return True

        def _try_remote_play_es_es_xdotool() -> bool:
            if not os.path.exists(xdotool):
                return False
            logger.info("type_text backend=remote-play-es-es-xdotool start")

            special_keys = {
                "ñ": ["key", "semicolon"],
                "Ñ": ["key", "shift+semicolon"],
                "á": ["key", "apostrophe", "a"],
                "é": ["key", "apostrophe", "e"],
                "í": ["key", "apostrophe", "i"],
                "ó": ["key", "apostrophe", "o"],
                "ú": ["key", "apostrophe", "u"],
                "Á": ["key", "apostrophe", "shift+a"],
                "É": ["key", "apostrophe", "shift+e"],
                "Í": ["key", "apostrophe", "shift+i"],
                "Ó": ["key", "apostrophe", "shift+o"],
                "Ú": ["key", "apostrophe", "shift+u"],
                "ü": ["key", "shift+apostrophe", "u"],
                "Ü": ["key", "shift+apostrophe", "shift+u"],
                "¡": ["key", "equal"],
                "¿": ["key", "shift+equal"],
                "?": ["key", "shift+minus"],
            }

            def _flush(buffer: list[str]) -> bool:
                if not buffer:
                    return True
                chunk = "".join(buffer)
                buffer.clear()
                r = subprocess.run([xdotool, "type", "--delay", "0", "--", chunk], env=env, check=False)
                logger.info("type_text remote-play-es-es ascii chunk len=%s rc=%s", len(chunk), r.returncode)
                return r.returncode == 0

            buffer: list[str] = []
            for ch in text:
                seq = special_keys.get(ch)
                if seq:
                    if not _flush(buffer):
                        return False
                    r = subprocess.run([xdotool] + seq, env=env, check=False)
                    logger.info("type_text remote-play-es-es char=%s seq=%s rc=%s", ch, "+".join(seq[1:]), r.returncode)
                    if r.returncode != 0:
                        return False
                    threading.Event().wait(0.02)
                elif ord(ch) < 128:
                    buffer.append(ch)
                else:
                    normalized = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
                    buffer.append(normalized or "?")
            if not _flush(buffer):
                return False

            if has_post_key:
                if not _post_text_input("remote-play-es-es-xdotool", "xdotool"):
                    return False
            self.last_method = "remote-play-es-es-xdotool-type"
            return True

        def _try_remote_play_uinput_keyboard() -> bool:
            try:
                if not self.ensure_virtual_keyboard():
                    return False
                logger.info("type_text backend=remote-play-uinput-keyboard start")

                keymap = {
                    **{letter: (key_code, False) for letter, key_code in LETTER_KEY_CODES.items()},
                    **{letter.upper(): (key_code, True) for letter, key_code in LETTER_KEY_CODES.items()},
                    "1": (KEY_1, False), "2": (KEY_2, False), "3": (KEY_3, False),
                    "4": (KEY_4, False), "5": (KEY_5, False), "6": (KEY_6, False),
                    "7": (KEY_7, False), "8": (KEY_8, False), "9": (KEY_9, False),
                    "0": (KEY_0, False),
                    " ": (KEY_SPACE, False), ".": (KEY_DOT, False), ",": (KEY_COMMA, False),
                    "-": (KEY_MINUS, False), "_": (KEY_MINUS, True),
                    "?": (KEY_MINUS, True), "!": (KEY_EQUAL, False),
                    "¿": (KEY_EQUAL, True), "¡": (KEY_EQUAL, False),
                    ":": (KEY_DOT, True), ";": (KEY_COMMA, True),
                    "/": (KEY_7, True), "(": (KEY_8, True), ")": (KEY_9, True),
                }
                accent_map = {
                    "á": ("a", False), "é": ("e", False), "í": ("i", False), "ó": ("o", False), "ú": ("u", False),
                    "Á": ("a", True), "É": ("e", True), "Í": ("i", True), "Ó": ("o", True), "Ú": ("u", True),
                }

                def _press_char(ch: str) -> bool:
                    if ch in accent_map:
                        base, shifted = accent_map[ch]
                        self._virtual_keyboard_key(KEY_APOSTROPHE)
                        self._virtual_keyboard_key(LETTER_KEY_CODES[base], shifted)
                        return True
                    if ch == "ñ":
                        self._virtual_keyboard_key(KEY_SEMICOLON)
                        return True
                    if ch == "Ñ":
                        self._virtual_keyboard_key(KEY_SEMICOLON, True)
                        return True
                    if ch == "ü":
                        self._virtual_keyboard_key(KEY_APOSTROPHE, True)
                        self._virtual_keyboard_key(KEY_U)
                        return True
                    if ch == "Ü":
                        self._virtual_keyboard_key(KEY_APOSTROPHE, True)
                        self._virtual_keyboard_key(KEY_U, True)
                        return True
                    entry = keymap.get(ch)
                    if entry:
                        self._virtual_keyboard_key(entry[0], entry[1])
                        return True
                    normalized = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
                    for fallback in normalized or "?":
                        if not _press_char(fallback):
                            return False
                    return True

                for ch in text:
                    if not _press_char(ch):
                        return False
                if has_post_key:
                    if not _post_text_input("remote-play-uinput-keyboard", "virtual"):
                        return False
                self.last_method = "remote-play-uinput-keyboard"
                return True
            except Exception:
                logger.exception("type_text remote-play-uinput-keyboard failed")
                self.close_virtual_keyboard()
                return False

        def _try_clipboard_paste() -> bool:
            payload = text.encode("utf-8", errors="strict")
            copied = False

            def _paste_with_xdotool(label: str) -> bool:
                if not os.path.exists(xdotool):
                    return False
                threading.Event().wait(0.12)
                pv = subprocess.run([xdotool, "key", "--clearmodifiers", "ctrl+v"], env=env, check=False)
                logger.info("type_text paste via xdotool ctrl+v (%s) rc=%s", label, pv.returncode)
                if pv.returncode != 0:
                    pv = subprocess.run([xdotool, "key", "--clearmodifiers", "shift+Insert"], env=env, check=False)
                    logger.info("type_text paste via xdotool shift+insert (%s) rc=%s", label, pv.returncode)
                    if pv.returncode != 0:
                        return False
                if has_post_key:
                    _delay_before_post_key(label)
                    r2 = subprocess.run([xdotool, "key", "--clearmodifiers", post_key["xdotool"]], env=env, check=False)
                    logger.info("type_text post-key via xdotool (%s) rc=%s", label, r2.returncode)
                    if r2.returncode != 0:
                        return False
                self.last_method = label
                return True

            def _try_xclip_decky_clipboard_style(target: str = "") -> bool:
                if not (os.path.exists(xclip) and os.path.exists(xdotool)):
                    return False
                try:
                    self.stop_clipboard_owner()
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(payload)
                        tmp_path = tmp.name
                    os.chmod(tmp_path, 0o644)
                    self.clipboard_owner_tmp = tmp_path
                    label_target = target or "default"
                    cmd = [xclip, "-selection", "clipboard", "-loops", "0", "-quiet", "-i", tmp_path]
                    if target:
                        cmd = [xclip, "-selection", "clipboard", "-loops", "0", "-quiet", "-t", target, "-i", tmp_path]
                    logger.info("type_text clipboard=xclip-persistent target=%s display=%s start", label_target, env.get("DISPLAY"))
                    self.clipboard_owner_proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
                    threading.Event().wait(0.25)
                    owner_rc = self.clipboard_owner_proc.poll()
                    logger.info("type_text clipboard=xclip-persistent target=%s owner_rc=%s", label_target, owner_rc)
                    if owner_rc not in (None, 0):
                        self.stop_clipboard_owner()
                        return False
                    targets = subprocess.run(
                        [xclip, "-selection", "clipboard", "-t", "TARGETS", "-o"],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=2,
                        check=False,
                    )
                    logger.info(
                        "type_text clipboard=xclip-persistent target=%s targets_rc=%s targets=%s",
                        label_target,
                        targets.returncode,
                        (targets.stdout or "").replace("\n", " ")[:240],
                    )
                    if targets.returncode != 0:
                        self.stop_clipboard_owner()
                        return False
                    return _paste_with_xdotool(f"xclip-persistent-{label_target}+xdotool-paste")
                except subprocess.TimeoutExpired:
                    logger.warning("type_text xclip-persistent target=%s timed out", target or "default")
                    self.stop_clipboard_owner()
                    return False
                except Exception:
                    logger.exception("type_text xclip-persistent failed")
                    self.stop_clipboard_owner()
                    return False

            # Decky Clipboard style path: X11 clipboard on Gamescope's real DISPLAY.
            # Letting xclip publish default targets is usually most compatible with Proton/Wine.
            if _try_xclip_decky_clipboard_style():
                return True
            if _try_xclip_decky_clipboard_style("UTF8_STRING"):
                return True
            if _try_xclip_decky_clipboard_style("text/plain"):
                return True

            # Klipper path via qdbus + xdotool ctrl+v.
            if os.path.exists(xdotool) and qdbus:
                logger.info("type_text clipboard=qdbus-klipper start")
                cp = subprocess.run(
                    [qdbus, "org.kde.klipper", "/klipper", "setClipboardContents", text],
                    env=env,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("type_text clipboard=qdbus-klipper rc=%s", cp.returncode)
                if cp.returncode == 0:
                    if _paste_with_xdotool("qdbus-klipper+xdotool-paste"):
                        return True
            # Legacy X11 path: xclip/xsel + xdotool ctrl+v.
            if os.path.exists(xdotool) and os.path.exists(xclip):
                logger.info("type_text clipboard=xclip (X11 path) start")
                cp = subprocess.run(
                    [xclip, "-selection", "clipboard", "-in", "-target", "UTF8_STRING"],
                    input=payload,
                    text=False,
                    env=env,
                    check=False,
                )
                logger.info("type_text clipboard=xclip (X11 path) rc=%s", cp.returncode)
                if cp.returncode == 0:
                    if _paste_with_xdotool("xclip+xdotool-paste"):
                        return True

            if os.path.exists(xdotool) and os.path.exists(xsel):
                logger.info("type_text clipboard=xsel (X11 path) start")
                cp = subprocess.run(
                    [xsel, "--clipboard", "--input"],
                    input=payload,
                    text=False,
                    env=env,
                    check=False,
                )
                logger.info("type_text clipboard=xsel (X11 path) rc=%s", cp.returncode)
                if cp.returncode == 0:
                    if _paste_with_xdotool("xsel+xdotool-paste"):
                        return True

            if os.path.exists(wl_copy):
                logger.info("type_text clipboard=wl-copy start")
                cp = subprocess.run(
                    [wl_copy, "--type", "text/plain;charset=utf-8"],
                    input=payload,
                    text=False,
                    env=env,
                    check=False,
                )
                logger.info("type_text clipboard=wl-copy rc=%s", cp.returncode)
                copied = cp.returncode == 0
            if (not copied) and os.path.exists(xclip):
                logger.info("type_text clipboard=xclip start")
                cp = subprocess.run(
                    [xclip, "-selection", "clipboard", "-in", "-target", "UTF8_STRING"],
                    input=payload,
                    text=False,
                    env=env,
                    check=False,
                )
                logger.info("type_text clipboard=xclip rc=%s", cp.returncode)
                copied = cp.returncode == 0

            if not copied:
                return False

            # Soft verification: normalize Unicode and tolerate trailing newlines.
            # Some Wayland environments return clipboard text in NFD form.
            def _canon(s: str) -> str:
                return unicodedata.normalize("NFC", (s or "").rstrip("\r\n"))

            if os.path.exists(wl_copy):
                chk = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, env=env, check=False)
                if chk.returncode == 0:
                    pasted_text = chk.stdout or ""
                    logger.info("clipboard roundtrip wl-paste sample='%s'", pasted_text[:120])
                    if has_non_ascii and (_canon(pasted_text) != _canon(text)):
                        logger.warning("clipboard roundtrip mismatch (wl-paste), refusing degraded paste")
                        # No bloquear aquí: en GameMode hay apps que pegan bien aunque wl-paste no refleje exacto.
            elif os.path.exists(xclip):
                chk = subprocess.run(
                    [xclip, "-selection", "clipboard", "-out", "-target", "UTF8_STRING"],
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
                if chk.returncode == 0:
                    pasted_text = chk.stdout or ""
                    if has_non_ascii and (_canon(pasted_text) != _canon(text)):
                        logger.warning("clipboard roundtrip mismatch (xclip), refusing degraded paste")
                        # No bloquear aquí: intentar paste igualmente.

            # Try multiple paste shortcuts because some apps only accept one.
            if os.path.exists(ydotool):
                pv_ctrl_v = subprocess.run([ydotool, "key", "29:1", "47:1", "47:0", "29:0"], env=env, check=False)
                logger.info("type_text clipboard paste via ydotool ctrl+v rc=%s", pv_ctrl_v.returncode)
                pv_shift_ins = subprocess.run([ydotool, "key", "42:1", "110:1", "110:0", "42:0"], env=env, check=False)
                logger.info("type_text clipboard paste via ydotool shift+insert rc=%s", pv_shift_ins.returncode)
                if pv_ctrl_v.returncode != 0 and pv_shift_ins.returncode != 0:
                    return False
                if has_post_key:
                    if not _post_text_input("clipboard+ydotool", "ydotool"):
                        return False
                self.last_method = "clipboard+ydotool-paste"
                return True

            if os.path.exists(wtype):
                pv = subprocess.run([wtype, "-M", "ctrl", "v"], env=env, check=False)
                logger.info("type_text clipboard paste via wtype rc=%s", pv.returncode)
                if pv.returncode != 0:
                    pv2 = subprocess.run([wtype, "-M", "shift", "-k", "Insert"], env=env, check=False)
                    logger.info("type_text clipboard paste via wtype shift+insert rc=%s", pv2.returncode)
                    if pv2.returncode != 0:
                        pv3 = subprocess.run([wtype, "-M", "ctrl", "-M", "shift", "v"], env=env, check=False)
                        logger.info("type_text clipboard paste via wtype ctrl+shift+v rc=%s", pv3.returncode)
                        if pv3.returncode != 0:
                            return False
                if has_post_key:
                    if not _post_text_input("clipboard+wtype", "wtype"):
                        return False
                self.last_method = "clipboard+wtype-paste"
                return True

            return False

        try:
            if self.remote_play_typing:
                logger.info("type_text remote_play_typing enabled: clipboard disabled")
                _pre_text_input()
                if _try_remote_play_uinput_keyboard() or _try_remote_play_es_es_xdotool() or _try_ydotool() or _try_wtype() or _try_xdotool():
                    self.last_error = ""
                    return
                self.last_error = "Remote Play typing failed (xdotool/ydotool/wtype unavailable)"
                self.last_method = "remote-play-typing-failed"
                return
            _pre_text_input()
            # For accents and other non-ASCII characters, prefer clipboard insertion
            # to avoid keyboard layout degradation.
            if has_non_ascii:
                # Preferred path: direct Unicode injection with wtype, before clipboard.
                if _try_wtype():
                    self.last_error = ""
                    return
                if _try_clipboard_paste():
                    self.last_error = ""
                    return
                logger.warning("type_text non-ascii: clipboard paste failed, using typing fallback")
                if _try_ydotool() or _try_xdotool():
                    self.last_error = "Warning: non-ASCII fallback used (text may lose accents)"
                    if not self.last_method:
                        self.last_method = "fallback-non-ascii-typing"
                    return
                self.last_error = "Clipboard paste failed for non-ASCII text"
                self.last_method = "clipboard-failed-non-ascii"
                return
            # In Game Mode / Wayland, prefer ydotool and avoid silent false positives.
            if is_gamemode:
                if _try_ydotool():
                    self.last_error = ""
                    return
                logger.warning("type_text ydotool failed in GameMode hint, trying limited fallback")
                if _try_clipboard_paste() or _try_wtype() or _try_xdotool():
                    self.last_error = ""
                    return
            else:
                if _try_ydotool() or _try_clipboard_paste() or _try_wtype() or _try_xdotool():
                    self.last_error = ""
                    return

            self.last_error = "Typing backend failed or unavailable (ydotool/wtype/xdotool)"
            self.last_method = "failed-no-backend"
            logger.error("type_text failed: all backends failed or unavailable")
        except Exception as e:
            self.last_error = f"typing failed: {e}"
            self.last_method = "failed-exception"
            logger.exception("type_text failed")


class Plugin:
    service = VoiceInputService()
    state_file = str((service.runtime_dir / "ai_speech_to_text_state").resolve())
    pid_file = str((service.runtime_dir / "ai_speech_to_text_listener.pid").resolve())
    listener_process = None
    poll_thread = None
    poll_running = False
    listener_watch_thread = None
    listener_watch_running = False

    @staticmethod
    def _terminate_duplicate_instances():
        try:
            self_pid = os.getpid()
            script_path = str(Path(__file__).resolve())
            out = subprocess.check_output(["pgrep", "-f", script_path], text=True, stderr=subprocess.DEVNULL)
            pids = []
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pid = int(line)
                except Exception:
                    continue
                if pid != self_pid:
                    pids.append(pid)
            if not pids:
                return
            logger.warning("duplicate plugin instances detected: %s", pids)
            for pid in pids:
                try:
                    os.kill(pid, 15)
                except Exception:
                    pass
            threading.Event().wait(0.25)
            for pid in pids:
                try:
                    os.kill(pid, 9)
                except Exception:
                    pass
        except Exception:
            logger.exception("duplicate instance cleanup failed")

    @staticmethod
    def ensure_ydotoold():
        try:
            ydotoold = Plugin.service._tool_path("ydotoold")
            if subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return True
            # Attempt 1: direct startup.
            if os.path.exists(ydotoold):
                subprocess.Popen([ydotoold], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                return True
            # Attempt 2: passwordless sudo if NOPASSWD is configured.
            if os.path.exists(ydotoold):
                subprocess.Popen(["sudo", "-n", ydotoold], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return subprocess.run(["pgrep", "-x", "ydotoold"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        except Exception:
            return False

    @staticmethod
    def _button_cfg_file():
        return _decky_settings_dir() / "decky_button_config.json"

    @staticmethod
    def _load_button_cfg():
        cfg = {
            "version": 2,
            "enabled": False,
            "active_app_id": "",
            "active_app_name": "",
            "global": {
                "steam_deck_button": "L5",
                "enter_mode": "before_after",
                "pre_key": TEXT_ENTRY_DEFAULT_PRE_KEY,
                "post_key": TEXT_ENTRY_DEFAULT_POST_KEY,
                "translate_to_english": False,
                "remote_play_typing": False,
            },
            "profiles": {},
        }
        f = Plugin._button_cfg_file()
        try:
            if f.exists():
                loaded = json.loads(f.read_text())
                if isinstance(loaded, dict):
                    cfg = loaded
        except Exception:
            logger.exception("button config load failed")
        return Plugin._normalize_button_cfg(cfg)

    @staticmethod
    def _save_button_cfg(cfg):
        cfg = Plugin._normalize_button_cfg(cfg)
        f = Plugin._button_cfg_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

    @staticmethod
    def _default_profile():
        return {
            "steam_deck_button": "L5",
            "enter_mode": "before_after",
            "pre_key": TEXT_ENTRY_DEFAULT_PRE_KEY,
            "post_key": TEXT_ENTRY_DEFAULT_POST_KEY,
            "translate_to_english": False,
            "remote_play_typing": False,
            "transcription_profile": "Grok Whisper Large v3",
        }

    @staticmethod
    def _normalize_profile(profile):
        if not isinstance(profile, dict):
            profile = {}
        mode = _normalize_enter_mode(profile.get("enter_mode", "before_after"))
        translate_to_english = bool(profile.get("translate_to_english", profile.get("translation_mode") == "english"))
        normalized = {
            "steam_deck_button": Plugin._normalize_steam_deck_button(profile.get("steam_deck_button")),
            "enter_mode": mode,
            "pre_key": _normalize_text_entry_key(profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY), TEXT_ENTRY_DEFAULT_PRE_KEY),
            "post_key": _normalize_text_entry_key(profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY), TEXT_ENTRY_DEFAULT_POST_KEY),
            "translate_to_english": translate_to_english,
            "remote_play_typing": bool(profile.get("remote_play_typing", False)),
            "transcription_profile": str(profile.get("transcription_profile", "Grok Whisper Large v3") or "Grok Whisper Large v3"),
        }
        if "enabled" in profile:
            normalized["enabled"] = bool(profile.get("enabled", False))
        if profile.get("app_name"):
            normalized["app_name"] = str(profile.get("app_name", ""))[:160]
        return normalized

    @staticmethod
    def _normalize_button_cfg(cfg):
        if not isinstance(cfg, dict):
            cfg = {}
        global_profile = cfg.get("global", Plugin._default_profile())
        profiles = cfg.get("profiles", {})
        if not isinstance(profiles, dict):
            profiles = {}
        normalized_profiles = {}
        for app_id, profile in profiles.items():
            app_key = str(app_id or "").strip()
            if not app_key:
                continue
            normalized_profiles[app_key] = Plugin._normalize_profile(profile)
        return {
            "version": 2,
            "enabled": bool(cfg.get("enabled", False)),
            "active_app_id": str(cfg.get("active_app_id", "") or ""),
            "active_app_name": str(cfg.get("active_app_name", "") or ""),
            "global": Plugin._normalize_profile(global_profile),
            "profiles": normalized_profiles,
        }

    @staticmethod
    def _effective_profile(cfg, app_id=None):
        app_key = str(app_id if app_id is not None else cfg.get("active_app_id", "") or "").strip()
        if app_key and app_key in cfg.get("profiles", {}):
            profile = cfg["profiles"][app_key]
            return Plugin._normalize_profile(profile), True, app_key
        return Plugin._normalize_profile(cfg.get("global")), False, app_key

    @staticmethod
    def _effective_enabled(cfg, app_id=None):
        profile, has_profile, _app_key = Plugin._effective_profile(cfg, app_id)
        if has_profile and "enabled" in profile:
            return bool(profile.get("enabled", False))
        return bool(cfg.get("enabled", False))

    @staticmethod
    def _normalize_steam_deck_button(button):
        button = str(button or "L5").strip().upper()
        return button if button in STEAM_DECK_BUTTON_OPTIONS else "L5"

    @staticmethod
    def start_controller_listener():
        Plugin.stop_controller_listener()
        listener = Path(os.environ.get("DECKY_PLUGIN_DIR", ".")) / "controller_listener.py"
        if not listener.exists():
            logger.error("controller listener not found at %s", listener)
            return False
        env = os.environ.copy()
        # Do not force a fixed eventX path; SteamOS can change it between sessions.
        env.pop("VOICEINPUT_DEVICE_PATH", None)
        env["PYTHONUNBUFFERED"] = "1"
        listener_log = open(_decky_log_file(), "ab")
        try:
            Plugin.listener_process = subprocess.Popen(
                ["/usr/bin/python3", str(listener)],
                stdout=listener_log,
                stderr=subprocess.STDOUT,
                env=env,
            )
        finally:
            listener_log.close()
        threading.Event().wait(0.4)
        alive = Plugin.listener_process.poll() is None
        logger.info("listener started pid=%s alive=%s", getattr(Plugin.listener_process, "pid", None), alive)
        return alive

    @staticmethod
    def stop_controller_listener():
        if os.path.exists(Plugin.pid_file):
            try:
                os.kill(int(Path(Plugin.pid_file).read_text().strip()), 9)
            except Exception:
                pass
        if Plugin.listener_process is not None:
            try:
                Plugin.listener_process.kill()
            except Exception:
                pass
            Plugin.listener_process = None

    @staticmethod
    def _watch_listener():
        while Plugin.listener_watch_running:
            try:
                if Plugin.service.enabled:
                    p = Plugin.listener_process
                    if p is None or p.poll() is not None:
                        logger.warning("listener not running, restarting")
                        Plugin.start_controller_listener()
                threading.Event().wait(1.0)
            except Exception:
                logger.exception("listener watch failed")
                threading.Event().wait(1.0)

    @staticmethod
    def poll_button_state():
        last = False
        while Plugin.poll_running:
            try:
                if Plugin.service.enabled and os.path.exists(Plugin.state_file):
                    state = Path(Plugin.state_file).read_text().strip() == "1"
                    if state and not last:
                        Plugin.service.start_recording()
                    elif (not state) and last:
                        Plugin.service.stop_recording()
                    last = state
            except Exception:
                pass
            threading.Event().wait(0.05)

    async def _main(self):
        try:
            logger.info("AI Speech-to-Text initialized")
            Plugin._terminate_duplicate_instances()
            print("AISpeechToText: _main init", flush=True)
            ok = Plugin.ensure_ydotoold()
            logger.info("ensure_ydotoold=%s", ok)
            print(f"AISpeechToText: ensure_ydotoold={ok}", flush=True)
            cfg = Plugin._load_button_cfg()
            Plugin._save_button_cfg(cfg)
            runtime_cfg = Plugin.service.load_config()
            Plugin.service.debug_logging = bool(runtime_cfg.get("debug_logging", False))
            profile, _has_profile, _app_key = Plugin._effective_profile(cfg)
            Plugin.service.enabled = Plugin._effective_enabled(cfg)
            Plugin.service.enter_mode = profile.get("enter_mode", "before_after")
            Plugin.service.pre_key = profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
            Plugin.service.post_key = profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
            Plugin.service.translate_to_english = bool(profile.get("translate_to_english", False))
            Plugin.service.remote_play_typing = bool(profile.get("remote_play_typing", False))
            Plugin.service.transcription_provider = profile.get("transcription_profile", "Grok Whisper Large v3")
            Plugin.service.active_app_id = cfg.get("active_app_id", "")
            Plugin.service.active_app_name = cfg.get("active_app_name", "")
            virtual_keyboard_ready = Plugin.service.ensure_virtual_keyboard()
            logger.info("virtual keyboard ready=%s", virtual_keyboard_ready)
            started = True
            if Plugin.service.enabled:
                started = Plugin.start_controller_listener()
                logger.info("start_controller_listener=%s", started)
                print(f"AISpeechToText: start_controller_listener={started}", flush=True)
            Plugin.listener_watch_running = True
            Plugin.listener_watch_thread = threading.Thread(target=Plugin._watch_listener, daemon=True, name="ai-speech-listener-watch")
            Plugin.listener_watch_thread.start()
            Plugin.poll_running = True
            Plugin.poll_thread = threading.Thread(target=Plugin.poll_button_state, daemon=True, name="ai-speech-poll")
            Plugin.poll_thread.start()
        except Exception:
            logger.exception("_main failed")
            raise

    async def _unload(self):
        logger.info("AI Speech-to-Text unloaded")
        Plugin.listener_watch_running = False
        Plugin.poll_running = False
        Plugin.service.stop_clipboard_owner()
        Plugin.service.close_virtual_keyboard()
        Plugin.stop_controller_listener()

    async def set_enabled(self, enabled: bool):
        cfg = Plugin._load_button_cfg()
        _profile, has_profile, app_key = Plugin._effective_profile(cfg)
        if has_profile and app_key:
            cfg["profiles"][app_key]["enabled"] = bool(enabled)
        else:
            cfg["enabled"] = bool(enabled)
        Plugin._save_button_cfg(cfg)
        Plugin.service.enabled = Plugin._effective_enabled(cfg)
        if Plugin.service.enabled and (Plugin.listener_process is None or Plugin.listener_process.poll() is not None):
            Plugin.start_controller_listener()
        elif not Plugin.service.enabled:
            Plugin.stop_controller_listener()
        return {"success": True}

    async def get_status(self):
        cfg = Plugin._load_button_cfg()
        runtime_cfg = Plugin.service.load_config()
        Plugin.service.debug_logging = bool(runtime_cfg.get("debug_logging", False))
        profile, has_profile, app_key = Plugin._effective_profile(cfg)
        tx_cfg = Plugin.service._load_transcription_profiles_config()
        tx_active = Plugin.service._load_transcription_provider(profile.get("transcription_profile", "Grok Whisper Large v3"))
        tx_profiles = tx_cfg.get("profiles", [])
        if isinstance(tx_profiles, dict):
            tx_profiles = list(tx_profiles.values())
        if not isinstance(tx_profiles, list):
            tx_profiles = []
        return {
            "success": True,
            "recording": Plugin.service.is_recording,
            "enabled": Plugin._effective_enabled(cfg),
            "last_text": Plugin.service.last_text,
            "last_error": Plugin.service.last_error,
            "debug_logging": Plugin.service.debug_logging,
            "steam_deck_button": profile.get("steam_deck_button", "L5"),
            "enter_mode": profile.get("enter_mode", "before_after"),
            "pre_key": profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY),
            "post_key": profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY),
            "translate_to_english": bool(profile.get("translate_to_english", False)),
            "remote_play_typing": bool(profile.get("remote_play_typing", False)),
            "global": cfg["global"],
            "profile": profile,
            "profiles": cfg.get("profiles", {}),
            "has_game_profile": has_profile,
            "active_app_id": app_key,
            "active_app_name": cfg.get("active_app_name", ""),
            "transcription": {
                "active_profile": tx_active.get("active_profile", "Grok Whisper Large v3"),
                "profiles": tx_profiles,
            },
        }

    async def get_button_config(self):
        try:
            return {"success": True, "config": Plugin._load_button_cfg()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_steam_deck_button(self, button: str):
        try:
            cfg = Plugin._load_button_cfg()
            next_button = Plugin._normalize_steam_deck_button(button)
            _profile, has_profile, app_key = Plugin._effective_profile(cfg)
            if has_profile and app_key:
                cfg["profiles"][app_key]["steam_deck_button"] = next_button
            else:
                cfg["global"]["steam_deck_button"] = next_button
            Plugin._save_button_cfg(cfg)
            if Plugin.service.enabled:
                Plugin.start_controller_listener()
            else:
                Plugin.stop_controller_listener()
            return {"success": True, "steam_deck_button": next_button}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_enter_mode(self, enter_mode: str):
        try:
            mode = _normalize_enter_mode(enter_mode)
            cfg = Plugin._load_button_cfg()
            _profile, has_profile, app_key = Plugin._effective_profile(cfg)
            if has_profile and app_key:
                cfg["profiles"][app_key]["enter_mode"] = mode
            else:
                cfg["global"]["enter_mode"] = mode
            Plugin._save_button_cfg(cfg)
            Plugin.service.enabled = Plugin._effective_enabled(cfg)
            Plugin.service.enter_mode = mode
            active_profile, _has_profile, _app_key = Plugin._effective_profile(cfg)
            Plugin.service.pre_key = active_profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
            Plugin.service.post_key = active_profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
            Plugin.service.transcription_provider = active_profile.get("transcription_profile", "Grok Whisper Large v3")
            return {"success": True, "enter_mode": mode}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_text_entry_key(self, key_name: str = "", position: str = "pre"):
        try:
            key_field = "post_key" if str(position or "").strip().lower() == "post" else "pre_key"
            default_key = TEXT_ENTRY_DEFAULT_POST_KEY if key_field == "post_key" else TEXT_ENTRY_DEFAULT_PRE_KEY
            normalized_key = _normalize_text_entry_key(key_name, default_key)
            cfg = Plugin._load_button_cfg()
            _profile, has_profile, app_key = Plugin._effective_profile(cfg)
            if has_profile and app_key:
                cfg["profiles"][app_key][key_field] = normalized_key
            else:
                cfg["global"][key_field] = normalized_key
            Plugin._save_button_cfg(cfg)
            active_profile, _has_profile, _app_key = Plugin._effective_profile(cfg)
            Plugin.service.enter_mode = active_profile.get("enter_mode", "before_after")
            Plugin.service.pre_key = active_profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
            Plugin.service.post_key = active_profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
            return {"success": True, key_field: normalized_key}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_translate_to_english(self, enabled: bool):
        try:
            cfg = Plugin._load_button_cfg()
            _profile, has_profile, app_key = Plugin._effective_profile(cfg)
            if has_profile and app_key:
                cfg["profiles"][app_key]["translate_to_english"] = bool(enabled)
            else:
                cfg["global"]["translate_to_english"] = bool(enabled)
            Plugin._save_button_cfg(cfg)
            Plugin.service.translate_to_english = bool(enabled)
            return {"success": True, "translate_to_english": bool(enabled)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_remote_play_typing(self, enabled: bool):
        try:
            cfg = Plugin._load_button_cfg()
            _profile, has_profile, app_key = Plugin._effective_profile(cfg)
            if has_profile and app_key:
                cfg["profiles"][app_key]["remote_play_typing"] = bool(enabled)
            else:
                cfg["global"]["remote_play_typing"] = bool(enabled)
            Plugin._save_button_cfg(cfg)
            Plugin.service.remote_play_typing = bool(enabled)
            return {"success": True, "remote_play_typing": bool(enabled)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_active_game(self, app_id: str = "", app_name: str = ""):
        try:
            cfg = Plugin._load_button_cfg()
            app_key = str(app_id or "").strip()
            app_title = str(app_name or "").strip()[:160]
            if not app_key:
                # Ignore empty updates from frontend detection glitches.
                profile, has_profile, existing_key = Plugin._effective_profile(cfg)
                Plugin.service.enabled = Plugin._effective_enabled(cfg)
                Plugin.service.active_app_id = str(cfg.get("active_app_id", "") or "")
                Plugin.service.active_app_name = str(cfg.get("active_app_name", "") or "")
                Plugin.service.enter_mode = profile.get("enter_mode", "before_after")
                Plugin.service.pre_key = profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
                Plugin.service.post_key = profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
                Plugin.service.translate_to_english = bool(profile.get("translate_to_english", False))
                Plugin.service.remote_play_typing = bool(profile.get("remote_play_typing", False))
                Plugin.service.transcription_provider = profile.get("transcription_profile", "Grok Whisper Large v3")
                return {"success": True, "has_game_profile": has_profile, "profile": profile, "active_app_id": existing_key}
            previous_profile, _previous_has_profile, _previous_key = Plugin._effective_profile(cfg)
            cfg["active_app_id"] = app_key
            cfg["active_app_name"] = app_title
            Plugin._save_button_cfg(cfg)
            profile, has_profile, _app_key = Plugin._effective_profile(cfg)
            Plugin.service.enabled = Plugin._effective_enabled(cfg)
            Plugin.service.active_app_id = app_key
            Plugin.service.active_app_name = app_title
            Plugin.service.enter_mode = profile.get("enter_mode", "before_after")
            Plugin.service.pre_key = profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
            Plugin.service.post_key = profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
            Plugin.service.translate_to_english = bool(profile.get("translate_to_english", False))
            Plugin.service.remote_play_typing = bool(profile.get("remote_play_typing", False))
            Plugin.service.transcription_provider = profile.get("transcription_profile", "Grok Whisper Large v3")
            if Plugin.service.enabled:
                if profile.get("steam_deck_button") != previous_profile.get("steam_deck_button"):
                    Plugin.start_controller_listener()
            else:
                Plugin.stop_controller_listener()
            return {"success": True, "has_game_profile": has_profile, "profile": profile}
        except Exception as e:
            logger.exception("set_active_game failed")
            return {"success": False, "error": str(e)}

    async def set_game_profile_enabled(self, app_id: str = "", app_name: str = "", enabled: bool = True):
        try:
            cfg = Plugin._load_button_cfg()
            app_key = str(app_id or "").strip()
            if not app_key:
                return {"success": False, "error": "No active game appid"}
            if enabled:
                if app_key not in cfg["profiles"]:
                    base_profile, _has_profile, _profile_key = Plugin._effective_profile(cfg, app_key)
                    cfg["profiles"][app_key] = dict(base_profile)
                if app_name:
                    cfg["profiles"][app_key]["app_name"] = str(app_name or "").strip()[:160]
            else:
                cfg["profiles"].pop(app_key, None)
            cfg["active_app_id"] = app_key
            cfg["active_app_name"] = str(app_name or "").strip()[:160]
            Plugin._save_button_cfg(cfg)
            profile, has_profile, _profile_key = Plugin._effective_profile(cfg)
            Plugin.service.enabled = Plugin._effective_enabled(cfg)
            Plugin.service.active_app_id = app_key
            Plugin.service.active_app_name = cfg["active_app_name"]
            Plugin.service.enter_mode = profile.get("enter_mode", "before_after")
            Plugin.service.pre_key = profile.get("pre_key", TEXT_ENTRY_DEFAULT_PRE_KEY)
            Plugin.service.post_key = profile.get("post_key", TEXT_ENTRY_DEFAULT_POST_KEY)
            Plugin.service.translate_to_english = bool(profile.get("translate_to_english", False))
            Plugin.service.remote_play_typing = bool(profile.get("remote_play_typing", False))
            Plugin.service.transcription_provider = profile.get("transcription_profile", "Grok Whisper Large v3")
            if Plugin.service.enabled:
                Plugin.start_controller_listener()
            else:
                Plugin.stop_controller_listener()
            return {"success": True, "has_game_profile": has_profile, "profile": profile}
        except Exception as e:
            logger.exception("set_game_profile_enabled failed")
            return {"success": False, "error": str(e)}

    async def set_transcription_profile(self, profile_name: str = ""):
        try:
            cfg = Plugin.service._load_transcription_profiles_config()
            tx_profiles = cfg.get("profiles", {})
            next_profile = str(profile_name or "").strip()
            names = [str(p.get("name", "")).strip() for p in tx_profiles if isinstance(p, dict)]
            if next_profile not in names:
                return {"success": False, "error": f"Transcription profile not found: {next_profile}"}
            btn_cfg = Plugin._load_button_cfg()
            _current, has_profile, app_key = Plugin._effective_profile(btn_cfg)
            if has_profile and app_key:
                btn_cfg["profiles"][app_key]["transcription_profile"] = next_profile
            else:
                btn_cfg["global"]["transcription_profile"] = next_profile
            Plugin._save_button_cfg(btn_cfg)
            effective, _has_profile, _app_key = Plugin._effective_profile(btn_cfg)
            Plugin.service.enabled = Plugin._effective_enabled(btn_cfg)
            Plugin.service.transcription_provider = effective.get("transcription_profile", "Grok Whisper Large v3")
            return {"success": True, "transcription_profile": Plugin.service.transcription_provider}
        except Exception as e:
            logger.exception("set_transcription_profile failed")
            return {"success": False, "error": str(e)}

    async def start_recording(self):
        try:
            Plugin.service.start_recording()
            return {"success": True}
        except Exception as e:
            logger.exception("start_recording failed")
            return {"success": False, "error": str(e)}

    async def stop_recording(self):
        try:
            text = Plugin.service.stop_recording()
            return {"success": True, "text": text}
        except Exception as e:
            logger.exception("stop_recording failed profile=%s", Plugin.service.transcription_provider)
            return {"success": False, "error": str(e)}

    async def frontend_log(self, level: str = "info", message: str = ""):
        try:
            lvl = (level or "info").lower()
            if lvl == "error":
                logger.error("FRONTEND %s", message)
            elif lvl == "warn":
                logger.warning("FRONTEND %s", message)
            else:
                if Plugin.service.debug_logging:
                    logger.info("FRONTEND %s", message)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_debug_logging(self, enabled: bool = False):
        try:
            cfg = Plugin.service.load_config()
            cfg["debug_logging"] = bool(enabled)
            lines = [
                f'provider="{cfg.get("provider", "groq")}"',
                'language="auto"',
                f'openai_model="{cfg.get("openai_model", "whisper-1")}"',
                f'groq_model="{cfg.get("groq_model", "whisper-large-v3")}"',
                f'enter_on_done={"true" if bool(cfg.get("enter_on_done", True)) else "false"}',
                f'debug_logging={"true" if bool(cfg.get("debug_logging", False)) else "false"}',
            ]
            Plugin.service.config_file.parent.mkdir(parents=True, exist_ok=True)
            Plugin.service.config_file.write_text("\n".join(lines) + "\n")
            Plugin.service.debug_logging = bool(enabled)
            return {"success": True, "debug_logging": Plugin.service.debug_logging}
        except Exception as e:
            logger.exception("set_debug_logging failed")
            return {"success": False, "error": str(e)}
