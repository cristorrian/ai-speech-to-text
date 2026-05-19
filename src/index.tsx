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
  Router
} from "decky-frontend-lib";
import React from "react";
import { FaMicrophone } from "react-icons/fa";
import { useEffect, useRef, useState } from "react";

const BUTTON_OPTIONS = ["L1", "R1", "L2", "R2", "L3", "R3", "A", "B", "X", "Y", "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"];
const DROPDOWN_OPTIONS = BUTTON_OPTIONS.map((button) => ({ data: button, label: button }));
const ENTER_MODE_OPTIONS = [
  { data: "pre_post", label: "Enter before and after" },
  { data: "post_only", label: "Enter only at end" },
  { data: "none", label: "No automatic Enter" },
];

const normalizeButtons = (next: string[]) => {
  const normalized = next.filter((button) => BUTTON_OPTIONS.includes(button));
  const first = normalized[0] || "L1";
  let second = normalized[1] || "R1";

  if (second === first) {
    second = BUTTON_OPTIONS.find((button) => button !== first) || "R1";
  }

  return [first, second];
};

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
  const [buttons, setButtons] = useState<string[]>(["L1", "R1"]);
  const [lastError, setLastError] = useState("");
  const [lastText, setLastText] = useState("");
  const [enterMode, setEnterMode] = useState("pre_post");
  const [activeAppId, setActiveAppId] = useState("");
  const [activeAppName, setActiveAppName] = useState("");
  const [hasGameProfile, setHasGameProfile] = useState(false);
  const [statusText, setStatusText] = useState("Ready");
  const [activeTranscriptionProfile, setActiveTranscriptionProfile] = useState("Grok Whisper Large v3");
  const [transcriptionProfileOptions, setTranscriptionProfileOptions] = useState<Array<{ data: string; label: string }>>([]);
  const lastKnownAppRef = useRef("");

  const syncActiveGame = async () => {
    const { appId, appName } = await getActiveGame();
    const signature = `${appId}:${appName}`;
    if (signature === lastKnownAppRef.current) return;
    lastKnownAppRef.current = signature;
    await serverAPI.callPluginMethod("set_active_game", { app_id: appId, app_name: appName });
  };

  const updateButtons = async (next: string[]) => {
    await serverAPI.callPluginMethod("set_button_config", { buttons: normalizeButtons(next) });
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
        if (Array.isArray(st.result.buttons)) setButtons(normalizeButtons(st.result.buttons));
        setEnterMode(String(st.result.enter_mode || "pre_post"));
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
        <div className={staticClasses.Text}>PTT: hold {buttons.join("+")} to record</div>
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
      <PanelSectionRow>
        <DropdownItem
          label="Button 1"
          layout="below"
          rgOptions={DROPDOWN_OPTIONS}
          selectedOption={buttons[0] || "L1"}
          onChange={async (option: SingleDropdownOption) => {
            await updateButtons([String(option.data), buttons[1] || "R1"]);
          }}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <DropdownItem
          label="Button 2"
          layout="below"
          rgOptions={DROPDOWN_OPTIONS}
          selectedOption={buttons[1] || "R1"}
          onChange={async (option: SingleDropdownOption) => {
            await updateButtons([buttons[0] || "L1", String(option.data)]);
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
