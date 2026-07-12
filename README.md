# AI Speech-to-Text 🎙️

AI Speech-to-Text is a Decky Loader plugin for Steam Deck that records voice, sends the audio to a configurable AI transcription endpoint, and inserts the resulting text into the active game or app.

It is designed for push-to-talk use in Gaming Mode, with per-game profiles for Steam Deck buttons, text insertion behavior, translation, Remote Play typing, and transcription provider/model selection.

## Features ✨

- Push-to-talk recording from Steam Deck controller buttons.
- Manual recording controls from the Decky sidebar.
- Per-game profiles, with global defaults.
- Configurable transcription profiles from JSON.
- Optional audio translation to English through compatible transcription endpoints.
- Remote Play typing mode that avoids clipboard-based paste.
- OpenAI-compatible transcription endpoint support.
- Built-in examples for Groq, OpenAI, and OpenRouter endpoints.
- Optional `language` per transcription profile, with `auto` as the default.
- Unicode-friendly text insertion through clipboard-based paste paths.
- Bundled command-line tools under `bin/` to reduce external dependencies.
- Low-level Steam Deck button detection through `/dev/hidraw`.

## Installation 📦

Official install method: one-click desktop launcher.

### Install in Desktop Mode 🖱️

Use `Install AI Speech-to-Text.desktop` from this repository.

- Double-click the file in Desktop Mode.
- If you downloaded it with Firefox and the filename ends in `.desktop.download`, rename it to end exactly in `.desktop` before running it.
- It downloads `install-from-github.sh` from this repo and runs it in a terminal.
- The script installs the plugin to `/home/deck/homebrew/plugins/ai-speech-to-text`, seeds default settings if missing, restarts Decky, and restarts Steam.
- It asks for sudo password when required.
- It does not overwrite an existing settings file if one is already present.

Template source used by the installer:

```text
/home/deck/homebrew/plugins/ai-speech-to-text/config/transcription_profiles.json
```

After install, configure your API keys in:
`/home/deck/homebrew/settings/ai-speech-to-text/transcription_profiles.json`

## Transcription Profiles 🧠

Provider and model definitions live in:

```text
/home/deck/homebrew/settings/ai-speech-to-text/transcription_profiles.json
```

The repository includes the same file as a template at:

```text
config/transcription_profiles.json
```

The template intentionally does not include API keys.

### JSON Format 📄

`profiles` is a list. Each item defines one selectable provider/model profile:

```json
{
  "profiles": [
    {
      "name": "Grok Whisper Large v3",
      "provider": "grok",
      "model": "whisper-large-v3",
      "language": "auto",
      "api_key": "YOUR_GROQ_API_KEY",
      "api_url": "https://api.groq.com/openai/v1/audio/transcriptions"
    },
    {
      "name": "OpenAI Whisper-1",
      "provider": "openai",
      "model": "whisper-1",
      "language": "auto",
      "api_key": "YOUR_OPENAI_API_KEY",
      "api_url": "https://api.openai.com/v1/audio/transcriptions"
    },
    {
      "name": "OpenRouter Whisper Large v3 Turbo",
      "provider": "openrouter",
      "model": "openai/whisper-large-v3-turbo",
      "language": "auto",
      "api_key": "YOUR_OPENROUTER_API_KEY",
      "api_url": "https://openrouter.ai/api/v1/audio/transcriptions"
    },
    {
      "name": "OpenRouter Voxtral Mini Transcribe",
      "provider": "openrouter",
      "model": "mistralai/voxtral-mini-transcribe",
      "language": "auto",
      "api_key": "YOUR_OPENROUTER_API_KEY",
      "api_url": "https://openrouter.ai/api/v1/audio/transcriptions"
    }
  ]
}
```

### Fields 🏷️

- `name`: Required. This is what appears in the plugin selector.
- `provider`: Optional label used in the UI and logs. It does not control routing.
- `model`: Required. Sent as the `model` form field.
- `language`: Optional. Use `auto` to let the provider detect the spoken language. This selects or hints the spoken language; it does not translate.
- `api_key`: Required. Used as a Bearer token.
- `api_url`: Required. The transcription endpoint URL.

The backend is dynamic: it does not hard-code provider routing. It sends the request to the `api_url` defined in the selected profile.

Most providers use OpenAI-compatible multipart uploads. OpenRouter is handled automatically with JSON + base64 `input_audio`.

The bundled Groq profile is historically named `Grok Whisper Large v3` in existing installs. The `provider` label `grok` is accepted by the plugin and normalized internally for compatibility.

### Recommended Provider for Free Usage

For free-tier usage, **Groq** (`whisper-large-v3` or `whisper-large-v3-turbo`) is usually a good first option because it is fast for short push-to-talk recordings and publishes speech-to-text limits for free accounts.

Check the official rate-limit page before relying on a specific quota:
https://console.groq.com/docs/rate-limits

## Using The Plugin 🎮

Open **AI Speech-to-Text** from Decky.

### Main Toggle 🔘

Enable or disable the plugin with **Enabled**.

`Enabled` follows the active scope:

- Global when no per-game profile is active.
- Per-game when a game profile is active.

When enabled, the input listener starts and watches for the selected Steam Deck button.

### Push-To-Talk 🎤

The plugin reads the built-in controller directly through `/dev/hidraw`, so it can detect Steam Deck buttons in Gaming Mode without relying on Steam Input keyboard remaps.

- Hold the selected button to start recording.
- Release it to stop recording.
- The plugin transcribes the recording and inserts the text.

Available Steam Deck buttons:

```text
A, B, X, Y,
L1, R1, L2, R2, L3, R3,
L4, R4, L5, R5,
DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT,
SELECT, START, STEAM, QAM,
LEFT_PAD_CLICK, RIGHT_PAD_CLICK
```

`STEAM` and `QAM` can still open SteamOS overlays while being detected, so rear buttons or ordinary gamepad buttons are usually better PTT choices.

### Provider / Model 🤖

The **Provider / model** dropdown lists the profiles from `/home/deck/homebrew/settings/ai-speech-to-text/transcription_profiles.json`.

Selecting a profile changes the transcription endpoint/model used by the current global or per-game profile.

### Translation 🌐

The **Translate to English** checkbox controls audio translation and is disabled by default.

- Disabled: uses the configured transcription endpoint and preserves the spoken language.
- Enabled: changes a compatible `/audio/transcriptions` endpoint to `/audio/translations` and returns English text.
- If the selected endpoint cannot provide audio translation, the plugin reports an error instead of silently inserting untranslated text.

Changing `language` in a profile does not enable translation; it only tells the provider which language is being spoken. Audio translation endpoints currently translate speech to English. OpenRouter's dedicated transcription endpoint does not currently expose this translation mode.

### Remote Play Typing 🖥️

Enable **Remote Play typing** for games streamed from another PC.

Steam Remote Play forwards keyboard events but does not reliably synchronize the Steam Deck clipboard with the host PC. This mode disables clipboard paste and types the result as keyboard events instead.

For Windows hosts using the **Español (España)** keyboard layout, the plugin uses layout-aware key sequences for `ñ`, accented vowels, `ü`, `¿`, and `¡`. Other Unicode characters may still fall back to approximate ASCII.

### Enter Mode ⌨️

The **Enter mode** dropdown controls whether the plugin presses configurable keyboard keys around inserted text:

- `Key before text`: presses one configured key before inserting text.
- `Key after text`: inserts text, then presses one configured key.
- `Key before and after`: presses one configured key before inserting text, then one configured key after it.
- `No key`: inserts text only.

When a mode uses a key, the plugin shows a text field for that key. Focus the field in Gaming Mode to bring up the Steam virtual keyboard, then type a key name such as `T`, `Enter`, `/`, or `F1`.

Use **Key guide** in the plugin to open a separate guide panel with the supported key names. Press **Back** in that panel to return to the plugin settings. Special keys are written as `Enter`, `Esc`, `Space`, and `Tab`. Function keys are written as `F1` through `F12`. Letters and numbers can be typed directly. Supported symbols include `/`, `\`, `-`, `.`, `,`, `;`, `'`, and `` ` ``.

This is useful because different games handle chat boxes differently. For example, one game may use `T` before text and `Enter` after text, while another may only need `Enter` after text.

## Per-Game Profiles 🕹️

The plugin automatically detects the active Steam app when possible.

Use **Profile for this game** to create a profile for the current game. Once enabled, these settings are saved separately for that game:

- Enabled
- Steam Deck button
- Translate to English
- Remote Play typing
- Provider / model
- Enter mode
- Key before text
- Key after text

When no per-game profile is active, the plugin edits the global settings.

Button/profile settings are stored in:

```text
/home/deck/homebrew/settings/ai-speech-to-text/decky_button_config.json
```

## Text Insertion 📝

The plugin tries several insertion methods to work across SteamOS, Gamescope, Proton/Wine games, and desktop apps.

For Unicode text, accents, inverted punctuation, and non-ASCII characters, it prefers clipboard-based insertion using bundled tools such as `xclip`, `xdotool`, `wtype`, and `wl-copy`.

This is why transcribed Spanish text with accents can work even when direct keyboard emulation would lose characters due to keyboard layout limitations.

## Bundled Tools 🧰

The plugin includes helper binaries under `bin/`:

```text
arecord
pw-record
xclip
xsel
xdotool
wtype
wl-copy
wl-paste
qdbus
qdbus6
qdbus-qt5
```

The backend prefers these bundled tools and falls back to system tools when needed.

The controller listener reads Steam Deck button state through `/dev/hidraw`.

## Logs 📜

The main plugin log writes to:

```text
/home/deck/homebrew/logs/ai-speech-to-text/ai-speech-to-text.log
```

Useful commands:

```bash
tail -f /home/deck/homebrew/logs/ai-speech-to-text/ai-speech-to-text.log
journalctl -u plugin_loader.service -n 200 --no-pager
```

The log includes:

- selected transcription profile
- provider label
- model
- API URL
- recorder backend
- insertion backend
- HTTP/transcription errors

Some low-level backend details are only shown when debug logging is enabled.

## Troubleshooting 🧪

### Restart services 🔄

Restart Decky Loader:

```bash
sudo systemctl restart plugin_loader.service
```

Restart Steam client if needed:

```bash
systemctl --user restart app-steam@autostart.service
```

### Basic checks 🔍

Check that the plugin path exists:

```text
/home/deck/homebrew/plugins/ai-speech-to-text
```

Check that button config and transcription profiles exist:

```text
/home/deck/homebrew/settings/ai-speech-to-text/decky_button_config.json
/home/deck/homebrew/settings/ai-speech-to-text/transcription_profiles.json
```

### Logs 📋

Follow plugin logs:

```bash
tail -f /home/deck/homebrew/logs/ai-speech-to-text/ai-speech-to-text.log
```

Follow plugin loader logs:

```bash
journalctl -u plugin_loader.service -n 200 --no-pager
```

## Uninstall 🗑️

Desktop one-click uninstall:

- Double-click `Uninstall AI Speech-to-Text.desktop`.
- It downloads and runs `uninstall.sh --purge-data`.
- This removes plugin files, settings, and logs, then restarts Decky and Steam.

Terminal uninstall:

```bash
./uninstall.sh
```

Terminal uninstall with full data purge:

```bash
./uninstall.sh --purge-data
```

Paths removed by `--purge-data`:

```text
/home/deck/homebrew/plugins/ai-speech-to-text
/home/deck/homebrew/settings/ai-speech-to-text
/home/deck/homebrew/logs/ai-speech-to-text
```

## Development 👨‍💻

Install frontend dependencies:

```bash
npm install
```

Build the frontend:

```bash
npm run build
```

Install or refresh the local Decky plugin copy:

```bash
./install.sh
```

The local installer excludes development artifacts such as `node_modules/`, preserves existing transcription API keys in the settings directory when possible, and restarts Decky plus Steam.

Project layout:

```text
main.py                         Backend, recording, transcription, insertion
controller_listener.py          Steam Deck button push-to-talk listener
src/index.tsx                   Decky frontend source
dist/index.js                   Built frontend loaded by Decky
config/transcription_profiles.json
bin/                            Bundled runtime tools
py_modules/                     Vendored Python modules
plugin.json                     Decky metadata
```

## Notes For Publishing 📌

- Do not commit real API keys.
- Keep `config/transcription_profiles.json` as a template with empty `api_key` values.
- `dist/index.js` should be committed so users do not need Node.js to install the plugin.
- `node_modules/` should not be committed; `package.json` and `package-lock.json` are enough for development.
- The `bin/` and `py_modules/` folders are intentionally included because the plugin is designed to be self-contained.

## Author 👤

- GitHub: [@cristorrian](https://github.com/cristorrian)
