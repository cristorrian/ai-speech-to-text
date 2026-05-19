# AI Speech-to-Text 🎙️

AI Speech-to-Text is a Decky Loader plugin for Steam Deck that records voice, sends the audio to a configurable AI transcription endpoint, and inserts the resulting text into the active game or app.

It is designed for push-to-talk use in Gaming Mode, with per-game profiles for button combos, Enter behavior, and transcription provider/model selection.

## Features ✨

- Push-to-talk recording from a two-button controller combo.
- Manual recording controls from the Decky sidebar.
- Per-game profiles, with global defaults.
- Configurable transcription profiles from JSON.
- OpenAI-compatible transcription endpoint support.
- Built-in examples for Groq, OpenAI, and OpenRouter endpoints.
- Optional `language` per transcription profile, with `auto` as the default.
- Unicode-friendly text insertion through clipboard-based paste paths.
- Bundled command-line tools under `bin/` to reduce external dependencies.
- Vendored `evdev` Python module under `py_modules/` for controller input.

## Installation 📦

Official install method: one-click desktop launcher.

### Install in Desktop Mode 🖱️

Use `Install AI Speech-to-Text.desktop` from this repository.

- Double-click the file in Desktop Mode.
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
- `language`: Optional. Use `auto` to let the provider detect the spoken language.
- `api_key`: Required. Used as a Bearer token.
- `api_url`: Required. The transcription endpoint URL.

The backend is dynamic: it does not hard-code provider routing. It sends the request to the `api_url` defined in the selected profile.

Most providers use OpenAI-compatible multipart uploads. OpenRouter is handled automatically with JSON + base64 `input_audio`.

### Recommended Provider for Free Usage

For free-tier usage, the recommended provider is **Groq** (`whisper-large-v3` or `whisper-large-v3-turbo`) because it offers generous STT limits on free accounts and is typically faster in real-time plugin workflows compared with other providers.

Current Groq free-tier STT limits for these models:

- `20 RPM` (requests per minute)
- `2,000 RPD` (requests per day)
- `7,200 ASH` (audio seconds per hour, equal to 2 hours/hour)
- `28,800 ASD` (audio seconds per day, equal to 8 hours/day)

Official reference:

- https://console.groq.com/docs/rate-limits

## Using The Plugin 🎮

Open **AI Speech-to-Text** from Decky.

### Main Toggle 🔘

Enable or disable the plugin with **Enabled**.

`Enabled` follows the active scope:

- Global when no per-game profile is active.
- Per-game when a game profile is active.

When enabled, the controller listener starts and watches for the selected push-to-talk combo.

### Push-To-Talk 🎤

The plugin uses two buttons as a push-to-talk combo:

- Hold both buttons to start recording.
- Release either button to stop recording.
- The plugin transcribes the recording and inserts the text.

Available buttons:

```text
L1, R1, L2, R2, L3, R3, A, B, X, Y, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT
```

### Provider / Model 🤖

The **Provider / model** dropdown lists the profiles from `/home/deck/homebrew/settings/ai-speech-to-text/transcription_profiles.json`.

Selecting a profile changes the transcription endpoint/model used by the current global or per-game profile.

### Enter Mode ⌨️

The **Enter mode** dropdown controls whether the plugin presses Enter around inserted text:

- `Enter before and after`: presses Enter before inserting text, then presses Enter again after paste.
- `Enter only at end`: inserts text, then presses Enter.
- `No automatic Enter`: inserts text only.

This is useful because different games handle chat boxes differently.

## Per-Game Profiles 🕹️

The plugin automatically detects the active Steam app when possible.

Use **Profile for this game** to create a profile for the current game. Once enabled, these settings are saved separately for that game:

- Enabled
- Button 1
- Button 2
- Provider / model
- Enter mode

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

The controller listener uses vendored Python `evdev` from `py_modules/`.

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
sudo cp -r /path/to/ai-speech-to-text /home/deck/homebrew/plugins/ai-speech-to-text
sudo systemctl restart plugin_loader.service
systemctl --user restart app-steam@autostart.service
```

Project layout:

```text
main.py                         Backend, recording, transcription, insertion
controller_listener.py          Controller push-to-talk listener
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
