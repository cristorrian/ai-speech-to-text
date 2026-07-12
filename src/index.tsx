import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  staticClasses,
  ButtonItem,
  ToggleField,
  DropdownItem,
  SingleDropdownOption,
  TextField,
  Router
} from "decky-frontend-lib";
import React from "react";
import { FaMicrophone } from "react-icons/fa";
import { useEffect, useRef, useState } from "react";

const STEAM_DECK_BUTTONS = [
  "A", "B", "X", "Y",
  "L1", "R1", "L2", "R2", "L3", "R3",
  "L4", "R4", "L5", "R5",
  "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
  "SELECT", "START", "STEAM", "QAM",
  "LEFT_PAD_CLICK", "RIGHT_PAD_CLICK",
];
const STEAM_DECK_BUTTON_LABELS: Record<string, string> = {
  DPAD_UP: "D-Pad Up",
  DPAD_DOWN: "D-Pad Down",
  DPAD_LEFT: "D-Pad Left",
  DPAD_RIGHT: "D-Pad Right",
  LEFT_PAD_CLICK: "Left Pad Click",
  RIGHT_PAD_CLICK: "Right Pad Click",
};
const STEAM_DECK_BUTTON_OPTIONS = STEAM_DECK_BUTTONS.map((button) => ({ data: button, label: STEAM_DECK_BUTTON_LABELS[button] || button }));
const ENTER_MODE_OPTIONS = [
  { data: "before", label: "Key before text" },
  { data: "after", label: "Key after text" },
  { data: "before_after", label: "Key before and after" },
  { data: "none", label: "No key" },
];

const normalizeSteamDeckButton = (next: string) => STEAM_DECK_BUTTONS.includes(next) ? next : "L5";

const getActiveGame = async () => {
  try {
    const router: any = Router as any;
    const running = Array.isArray(router?.RunningApps) ? router.RunningApps : [];
    const app =
      router?.MainRunningApp ||
      running[0] ||
      router?.AppStore?.m_selectedApp ||
      router?.AppStore?.m_currentApp;

    let appId = app?.appid ? String(app.appid) : "";
    let appName = app?.display_name ? String(app.display_name) : "";

    // Fallback to SteamClient APIs when Router fields are unavailable.
    if (!appId) {
      const apps: any = (window as any)?.SteamClient?.Apps;
      try {
        const current = await apps?.GetCurrentGame?.();
        if (current?.appid) appId = String(current.appid);
        if (current?.display_name) appName = String(current.display_name);
      } catch {
        // no-op
      }
      try {
        const focus = await apps?.GetGamepadFocusedApp?.();
        if (!appId && focus?.appid) appId = String(focus.appid);
        if (!appName && focus?.display_name) appName = String(focus.display_name);
      } catch {
        // no-op
      }
    }

    // Final fallback: parse app id from URL path/hash.
    if (!appId) {
      const raw = `${window.location?.pathname || ""} ${window.location?.hash || ""} ${window.location?.href || ""}`;
      const m = raw.match(/(?:app|game)\/(\d{2,})/i);
      if (m?.[1]) appId = m[1];
    }
    return { appId, appName };
  } catch {
    return { appId: "", appName: "" };
  }
};

function Content({ serverAPI }: { serverAPI: ServerAPI }) {
  const [recording, setRecording] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [steamDeckButton, setSteamDeckButton] = useState("L5");
  const [lastError, setLastError] = useState("");
  const [lastText, setLastText] = useState("");
  const [enterMode, setEnterMode] = useState("before_after");
  const [preKey, setPreKey] = useState("enter");
  const [postKey, setPostKey] = useState("enter");
  const [translateToEnglish, setTranslateToEnglish] = useState(false);
  const [remotePlayTyping, setRemotePlayTyping] = useState(false);
  const [activeAppId, setActiveAppId] = useState("");
  const [activeAppName, setActiveAppName] = useState("");
  const [hasGameProfile, setHasGameProfile] = useState(false);
  const [statusText, setStatusText] = useState("Ready");
  const [showKeyGuide, setShowKeyGuide] = useState(false);
  const [activeTranscriptionProfile, setActiveTranscriptionProfile] = useState("Grok Whisper Large v3");
  const [transcriptionProfileOptions, setTranscriptionProfileOptions] = useState<Array<{ data: string; label: string }>>([]);
  const lastKnownAppRef = useRef("");
  const editingKeyRef = useRef<"pre" | "post" | "">("");
  const dirtyKeysRef = useRef<{ pre: boolean; post: boolean }>({ pre: false, post: false });

  const syncActiveGame = async () => {
    const { appId, appName } = await getActiveGame();
    const signature = `${appId}:${appName}`;
    if (signature === lastKnownAppRef.current) return;
    lastKnownAppRef.current = signature;
    await serverAPI.callPluginMethod("set_active_game", { app_id: appId, app_name: appName });
  };

  const updateSteamDeckButton = async (next: string) => {
    await serverAPI.callPluginMethod("set_steam_deck_button", { button: normalizeSteamDeckButton(next) });
    await refresh();
  };

  const flog = async (level: "info" | "warn" | "error", message: string) => {
    try {
      await serverAPI.callPluginMethod("frontend_log", { level, message });
    } catch {
      // no-op
    }
  };

  const refresh = async () => {
    try {
      await syncActiveGame();
      const st: any = await serverAPI.callPluginMethod("get_status", {});
      if (st?.success) {
        setRecording(!!st.result.recording);
        setEnabled(!!st.result.enabled);
        setSteamDeckButton(normalizeSteamDeckButton(String(st.result.steam_deck_button || "L5")));
        setEnterMode(String(st.result.enter_mode || "before_after"));
        if (editingKeyRef.current !== "pre" && !dirtyKeysRef.current.pre) setPreKey(String(st.result.pre_key || "enter"));
        if (editingKeyRef.current !== "post" && !dirtyKeysRef.current.post) setPostKey(String(st.result.post_key || "enter"));
        setTranslateToEnglish(!!st.result.translate_to_english);
        setRemotePlayTyping(!!st.result.remote_play_typing);
        setActiveAppId(String(st.result.active_app_id || ""));
        setActiveAppName(String(st.result.active_app_name || ""));
        setHasGameProfile(!!st.result.has_game_profile);
        setLastError(String(st.result.last_error || ""));
        setLastText(String(st.result.last_text || ""));
        const tx = st.result.transcription || {};
        const profiles = Array.isArray(tx.profiles) ? tx.profiles : [];
        const nextOptions = profiles.map((entry: any) => {
          const name = String(entry?.name || "");
          const provider = String(entry.provider || "");
          const model = String(entry.model || "");
          const detail = [provider, model].filter(Boolean).join(" · ");
          return { data: name, label: detail ? `${name} (${detail})` : name };
        });
        setTranscriptionProfileOptions(nextOptions);
        setActiveTranscriptionProfile(String(tx.active_profile || "Grok Whisper Large v3"));

        if (st.result.recording) {
          setStatusText("Recording");
        } else if (st.result.last_error) {
          setStatusText("Error");
        } else if (st.result.last_text) {
          setStatusText("Text sent");
        } else {
          setStatusText("Ready");
        }
      } else {
        await flog("warn", `get_status unsuccessful: ${JSON.stringify(st)}`);
      }
    } catch (e: any) {
      await flog("error", `refresh exception: ${String(e)}`);
    }
  };

  useEffect(() => {
    refresh();
      const t = setInterval(refresh, 2000);
      return () => clearInterval(t);
  }, []);

  const enableGameProfile = async (enabled: boolean) => {
    const { appId, appName } = await getActiveGame();
    if (!appId) {
      await flog("warn", "game profile toggle ignored: no active game");
      await refresh();
      return;
    }
    await serverAPI.callPluginMethod("set_game_profile_enabled", {
      app_id: appId,
      app_name: appName,
      enabled
    });
    lastKnownAppRef.current = "";
    await refresh();
  };

  const editingLabel = activeAppId && hasGameProfile ? `profile for ${activeAppName || activeAppId}` : "global settings";
  const showPreKey = enterMode === "before" || enterMode === "before_after";
  const showPostKey = enterMode === "after" || enterMode === "before_after";

  const saveTextEntryKey = async (position: "pre" | "post", keyName: string) => {
    if (!keyName.trim()) {
      return;
    }
    const result: any = await serverAPI.callPluginMethod("set_text_entry_key", { position, key_name: keyName });
    dirtyKeysRef.current[position] = false;
    editingKeyRef.current = "";
    const savedKey = String(result?.result?.[position === "pre" ? "pre_key" : "post_key"] || keyName);
    if (position === "pre") setPreKey(savedKey);
    if (position === "post") setPostKey(savedKey);
  };

  if (showKeyGuide) {
    return (
      <PanelSection title="Key guide">
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => setShowKeyGuide(false)}
          >
            Back
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <div className={staticClasses.Text}>Type key names directly in the text fields.</div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div className={staticClasses.Text}>Special keys: Enter, Esc, Space, Tab.</div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div className={staticClasses.Text}>Function keys: F1, F2, F3 ... F12.</div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div className={staticClasses.Text}>Letters and numbers: A-Z and 0-9.</div>
        </PanelSectionRow>
        <PanelSectionRow>
          <div className={staticClasses.Text}>Symbols: /, \, -, ., comma (,), semicolon (;), apostrophe ('), grave (`).</div>
        </PanelSectionRow>
      </PanelSection>
    );
  }

  return (
    <PanelSection title="AI Speech-to-Text">
      <PanelSectionRow>
        <ToggleField
          label="Enabled"
          checked={enabled}
          onChange={async (v) => {
            await serverAPI.callPluginMethod("set_enabled", { enabled: v });
            await refresh();
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <div className={staticClasses.Text}>Status: {statusText}</div>
      </PanelSectionRow>
      {lastError ? (
        <PanelSectionRow>
          <div className={staticClasses.Text} style={{ color: "#ff6b6b" }}>Error: {lastError}</div>
        </PanelSectionRow>
      ) : null}
      {lastText ? (
        <PanelSectionRow>
          <div className={staticClasses.Text}>Last text: {lastText}</div>
        </PanelSectionRow>
      ) : null}
      <PanelSectionRow>
        <div className={staticClasses.Text}>PTT: hold {steamDeckButton} to record</div>
      </PanelSectionRow>
      <PanelSectionRow>
        <div className={staticClasses.Text}>Game: {activeAppName || (activeAppId ? activeAppId : "none")}</div>
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Profile for this game"
          checked={hasGameProfile}
          onChange={enableGameProfile}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <div className={staticClasses.Text}>Editing: {editingLabel}</div>
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          label="Provider / model"
          layout="below"
          rgOptions={transcriptionProfileOptions}
          selectedOption={activeTranscriptionProfile}
          onChange={async (option: SingleDropdownOption) => {
            await serverAPI.callPluginMethod("set_transcription_profile", { profile_name: String(option.data) });
            await refresh();
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          label="Enter mode"
          layout="below"
          rgOptions={ENTER_MODE_OPTIONS}
          selectedOption={enterMode}
          onChange={async (option: SingleDropdownOption) => {
            await serverAPI.callPluginMethod("set_enter_mode", { enter_mode: String(option.data) });
            await refresh();
          }}
        />
      </PanelSectionRow>
      {showPreKey ? (
        <PanelSectionRow>
          <TextField
            label="Key before text"
            description="Focus this field to open the Steam virtual keyboard. It saves when focus leaves the field."
            value={preKey}
            onFocus={() => {
              editingKeyRef.current = "pre";
            }}
            onChange={(event) => {
              dirtyKeysRef.current.pre = true;
              setPreKey(event.currentTarget.value);
            }}
            onBlur={async () => {
              if (dirtyKeysRef.current.pre) {
                await saveTextEntryKey("pre", preKey);
              }
              editingKeyRef.current = "";
            }}
          />
        </PanelSectionRow>
      ) : null}
      {showPostKey ? (
        <PanelSectionRow>
          <TextField
            label="Key after text"
            description="Focus this field to open the Steam virtual keyboard. It saves when focus leaves the field."
            value={postKey}
            onFocus={() => {
              editingKeyRef.current = "post";
            }}
            onChange={(event) => {
              dirtyKeysRef.current.post = true;
              setPostKey(event.currentTarget.value);
            }}
            onBlur={async () => {
              if (dirtyKeysRef.current.post) {
                await saveTextEntryKey("post", postKey);
              }
              editingKeyRef.current = "";
            }}
          />
        </PanelSectionRow>
      ) : null}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={() => setShowKeyGuide(true)}
        >
          Key guide
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Translate to English"
          checked={translateToEnglish}
          onChange={async (enabled) => {
            await serverAPI.callPluginMethod("set_translate_to_english", { enabled });
            await refresh();
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Remote Play typing"
          description="Types text as keyboard events without using the clipboard."
          checked={remotePlayTyping}
          onChange={async (enabled) => {
            await serverAPI.callPluginMethod("set_remote_play_typing", { enabled });
            await refresh();
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          label="Steam Deck button"
          layout="below"
          rgOptions={STEAM_DECK_BUTTON_OPTIONS}
          selectedOption={steamDeckButton}
          onChange={async (option: SingleDropdownOption) => {
            await updateSteamDeckButton(String(option.data));
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={async () => {
            await serverAPI.callPluginMethod("start_recording", {});
            await refresh();
          }}
        >
          Start recording
        </ButtonItem>
      </PanelSectionRow>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={async () => {
            await serverAPI.callPluginMethod("stop_recording", {});
            await refresh();
          }}
        >
          Stop and transcribe
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}

export default definePlugin((serverAPI: ServerAPI) => {
  let lastKnownApp = "";

  const syncActiveGame = async () => {
    try {
      const { appId, appName } = await getActiveGame();
      const signature = `${appId}:${appName}`;
      if (signature === lastKnownApp) return;
      lastKnownApp = signature;
      await serverAPI.callPluginMethod("set_active_game", { app_id: appId, app_name: appName });
    } catch {
      // no-op
    }
  };
  syncActiveGame();
  const gameSyncTimer = window.setInterval(syncActiveGame, 2000);

  return {
    title: <div className={staticClasses.Title}>AI Speech-to-Text</div>,
    content: <Content serverAPI={serverAPI} />,
    icon: <FaMicrophone />,
    onDismount() {
      window.clearInterval(gameSyncTimer);
    }
  };
});
