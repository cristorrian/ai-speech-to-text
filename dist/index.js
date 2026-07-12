(function (deckyFrontendLib, React) {
  'use strict';

  function _interopDefaultLegacy (e) { return e && typeof e === 'object' && 'default' in e ? e : { 'default': e }; }

  var React__default = /*#__PURE__*/_interopDefaultLegacy(React);

  var DefaultContext = {
    color: undefined,
    size: undefined,
    className: undefined,
    style: undefined,
    attr: undefined
  };
  var IconContext = React__default["default"].createContext && React__default["default"].createContext(DefaultContext);

  var __assign = window && window.__assign || function () {
    __assign = Object.assign || function (t) {
      for (var s, i = 1, n = arguments.length; i < n; i++) {
        s = arguments[i];
        for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
      }
      return t;
    };
    return __assign.apply(this, arguments);
  };
  var __rest = window && window.__rest || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0) t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function") for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
      if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i])) t[p[i]] = s[p[i]];
    }
    return t;
  };
  function Tree2Element(tree) {
    return tree && tree.map(function (node, i) {
      return React__default["default"].createElement(node.tag, __assign({
        key: i
      }, node.attr), Tree2Element(node.child));
    });
  }
  function GenIcon(data) {
    // eslint-disable-next-line react/display-name
    return function (props) {
      return React__default["default"].createElement(IconBase, __assign({
        attr: __assign({}, data.attr)
      }, props), Tree2Element(data.child));
    };
  }
  function IconBase(props) {
    var elem = function (conf) {
      var attr = props.attr,
        size = props.size,
        title = props.title,
        svgProps = __rest(props, ["attr", "size", "title"]);
      var computedSize = size || conf.size || "1em";
      var className;
      if (conf.className) className = conf.className;
      if (props.className) className = (className ? className + " " : "") + props.className;
      return React__default["default"].createElement("svg", __assign({
        stroke: "currentColor",
        fill: "currentColor",
        strokeWidth: "0"
      }, conf.attr, attr, svgProps, {
        className: className,
        style: __assign(__assign({
          color: props.color || conf.color
        }, conf.style), props.style),
        height: computedSize,
        width: computedSize,
        xmlns: "http://www.w3.org/2000/svg"
      }), title && React__default["default"].createElement("title", null, title), props.children);
    };
    return IconContext !== undefined ? React__default["default"].createElement(IconContext.Consumer, null, function (conf) {
      return elem(conf);
    }) : elem(DefaultContext);
  }

  // THIS FILE IS AUTO GENERATED
  function FaMicrophone (props) {
    return GenIcon({"tag":"svg","attr":{"viewBox":"0 0 352 512"},"child":[{"tag":"path","attr":{"d":"M176 352c53.02 0 96-42.98 96-96V96c0-53.02-42.98-96-96-96S80 42.98 80 96v160c0 53.02 42.98 96 96 96zm160-160h-16c-8.84 0-16 7.16-16 16v48c0 74.8-64.49 134.82-140.79 127.38C96.71 376.89 48 317.11 48 250.3V208c0-8.84-7.16-16-16-16H16c-8.84 0-16 7.16-16 16v40.16c0 89.64 63.97 169.55 152 181.69V464H96c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16h-56v-33.77C285.71 418.47 352 344.9 352 256v-48c0-8.84-7.16-16-16-16z"}}]})(props);
  }

  const STEAM_DECK_BUTTONS = [
      "A", "B", "X", "Y",
      "L1", "R1", "L2", "R2", "L3", "R3",
      "L4", "R4", "L5", "R5",
      "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
      "SELECT", "START", "STEAM", "QAM",
      "LEFT_PAD_CLICK", "RIGHT_PAD_CLICK",
  ];
  const STEAM_DECK_BUTTON_LABELS = {
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
  const normalizeSteamDeckButton = (next) => STEAM_DECK_BUTTONS.includes(next) ? next : "L5";
  const getActiveGame = async () => {
      try {
          const router = deckyFrontendLib.Router;
          const running = Array.isArray(router?.RunningApps) ? router.RunningApps : [];
          const app = router?.MainRunningApp ||
              running[0] ||
              router?.AppStore?.m_selectedApp ||
              router?.AppStore?.m_currentApp;
          let appId = app?.appid ? String(app.appid) : "";
          let appName = app?.display_name ? String(app.display_name) : "";
          // Fallback to SteamClient APIs when Router fields are unavailable.
          if (!appId) {
              const apps = window?.SteamClient?.Apps;
              try {
                  const current = await apps?.GetCurrentGame?.();
                  if (current?.appid)
                      appId = String(current.appid);
                  if (current?.display_name)
                      appName = String(current.display_name);
              }
              catch {
                  // no-op
              }
              try {
                  const focus = await apps?.GetGamepadFocusedApp?.();
                  if (!appId && focus?.appid)
                      appId = String(focus.appid);
                  if (!appName && focus?.display_name)
                      appName = String(focus.display_name);
              }
              catch {
                  // no-op
              }
          }
          // Final fallback: parse app id from URL path/hash.
          if (!appId) {
              const raw = `${window.location?.pathname || ""} ${window.location?.hash || ""} ${window.location?.href || ""}`;
              const m = raw.match(/(?:app|game)\/(\d{2,})/i);
              if (m?.[1])
                  appId = m[1];
          }
          return { appId, appName };
      }
      catch {
          return { appId: "", appName: "" };
      }
  };
  function Content({ serverAPI }) {
      const [recording, setRecording] = React.useState(false);
      const [enabled, setEnabled] = React.useState(false);
      const [steamDeckButton, setSteamDeckButton] = React.useState("L5");
      const [lastError, setLastError] = React.useState("");
      const [lastText, setLastText] = React.useState("");
      const [enterMode, setEnterMode] = React.useState("before_after");
      const [preKey, setPreKey] = React.useState("enter");
      const [postKey, setPostKey] = React.useState("enter");
      const [translateToEnglish, setTranslateToEnglish] = React.useState(false);
      const [remotePlayTyping, setRemotePlayTyping] = React.useState(false);
      const [activeAppId, setActiveAppId] = React.useState("");
      const [activeAppName, setActiveAppName] = React.useState("");
      const [hasGameProfile, setHasGameProfile] = React.useState(false);
      const [statusText, setStatusText] = React.useState("Ready");
      const [showKeyGuide, setShowKeyGuide] = React.useState(false);
      const [activeTranscriptionProfile, setActiveTranscriptionProfile] = React.useState("Grok Whisper Large v3");
      const [transcriptionProfileOptions, setTranscriptionProfileOptions] = React.useState([]);
      const lastKnownAppRef = React.useRef("");
      const editingKeyRef = React.useRef("");
      const dirtyKeysRef = React.useRef({ pre: false, post: false });
      const syncActiveGame = async () => {
          const { appId, appName } = await getActiveGame();
          const signature = `${appId}:${appName}`;
          if (signature === lastKnownAppRef.current)
              return;
          lastKnownAppRef.current = signature;
          await serverAPI.callPluginMethod("set_active_game", { app_id: appId, app_name: appName });
      };
      const updateSteamDeckButton = async (next) => {
          await serverAPI.callPluginMethod("set_steam_deck_button", { button: normalizeSteamDeckButton(next) });
          await refresh();
      };
      const flog = async (level, message) => {
          try {
              await serverAPI.callPluginMethod("frontend_log", { level, message });
          }
          catch {
              // no-op
          }
      };
      const refresh = async () => {
          try {
              await syncActiveGame();
              const st = await serverAPI.callPluginMethod("get_status", {});
              if (st?.success) {
                  setRecording(!!st.result.recording);
                  setEnabled(!!st.result.enabled);
                  setSteamDeckButton(normalizeSteamDeckButton(String(st.result.steam_deck_button || "L5")));
                  setEnterMode(String(st.result.enter_mode || "before_after"));
                  if (editingKeyRef.current !== "pre" && !dirtyKeysRef.current.pre)
                      setPreKey(String(st.result.pre_key || "enter"));
                  if (editingKeyRef.current !== "post" && !dirtyKeysRef.current.post)
                      setPostKey(String(st.result.post_key || "enter"));
                  setTranslateToEnglish(!!st.result.translate_to_english);
                  setRemotePlayTyping(!!st.result.remote_play_typing);
                  setActiveAppId(String(st.result.active_app_id || ""));
                  setActiveAppName(String(st.result.active_app_name || ""));
                  setHasGameProfile(!!st.result.has_game_profile);
                  setLastError(String(st.result.last_error || ""));
                  setLastText(String(st.result.last_text || ""));
                  const tx = st.result.transcription || {};
                  const profiles = Array.isArray(tx.profiles) ? tx.profiles : [];
                  const nextOptions = profiles.map((entry) => {
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
                  }
                  else if (st.result.last_error) {
                      setStatusText("Error");
                  }
                  else if (st.result.last_text) {
                      setStatusText("Text sent");
                  }
                  else {
                      setStatusText("Ready");
                  }
              }
              else {
                  await flog("warn", `get_status unsuccessful: ${JSON.stringify(st)}`);
              }
          }
          catch (e) {
              await flog("error", `refresh exception: ${String(e)}`);
          }
      };
      React.useEffect(() => {
          refresh();
          const t = setInterval(refresh, 2000);
          return () => clearInterval(t);
      }, []);
      const enableGameProfile = async (enabled) => {
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
      const saveTextEntryKey = async (position, keyName) => {
          if (!keyName.trim()) {
              return;
          }
          const result = await serverAPI.callPluginMethod("set_text_entry_key", { position, key_name: keyName });
          dirtyKeysRef.current[position] = false;
          editingKeyRef.current = "";
          const savedKey = String(result?.result?.[position === "pre" ? "pre_key" : "post_key"] || keyName);
          if (position === "pre")
              setPreKey(savedKey);
          if (position === "post")
              setPostKey(savedKey);
      };
      if (showKeyGuide) {
          return (React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "Key guide" },
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setShowKeyGuide(false) }, "Back")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text }, "Type key names directly in the text fields.")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text }, "Special keys: Enter, Esc, Space, Tab.")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text }, "Function keys: F1, F2, F3 ... F12.")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text }, "Letters and numbers: A-Z and 0-9.")),
              React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
                  React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text }, "Symbols: /, \\, -, ., comma (,), semicolon (;), apostrophe ('), grave (`)."))));
      }
      return (React__default["default"].createElement(deckyFrontendLib.PanelSection, { title: "AI Speech-to-Text" },
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Enabled", checked: enabled, onChange: async (v) => {
                      await serverAPI.callPluginMethod("set_enabled", { enabled: v });
                      await refresh();
                  } })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text },
                  "Status: ",
                  statusText)),
          lastError ? (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text, style: { color: "#ff6b6b" } },
                  "Error: ",
                  lastError))) : null,
          lastText ? (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text },
                  "Last text: ",
                  lastText))) : null,
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text },
                  "PTT: hold ",
                  steamDeckButton,
                  " to record")),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text },
                  "Game: ",
                  activeAppName || (activeAppId ? activeAppId : "none"))),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Profile for this game", checked: hasGameProfile, onChange: enableGameProfile })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Text },
                  "Editing: ",
                  editingLabel)),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Provider / model", layout: "below", rgOptions: transcriptionProfileOptions, selectedOption: activeTranscriptionProfile, onChange: async (option) => {
                      await serverAPI.callPluginMethod("set_transcription_profile", { profile_name: String(option.data) });
                      await refresh();
                  } })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Enter mode", layout: "below", rgOptions: ENTER_MODE_OPTIONS, selectedOption: enterMode, onChange: async (option) => {
                      await serverAPI.callPluginMethod("set_enter_mode", { enter_mode: String(option.data) });
                      await refresh();
                  } })),
          showPreKey ? (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.TextField, { label: "Key before text", description: "Focus this field to open the Steam virtual keyboard. It saves when focus leaves the field.", value: preKey, onFocus: () => {
                      editingKeyRef.current = "pre";
                  }, onChange: (event) => {
                      dirtyKeysRef.current.pre = true;
                      setPreKey(event.currentTarget.value);
                  }, onBlur: async () => {
                      if (dirtyKeysRef.current.pre) {
                          await saveTextEntryKey("pre", preKey);
                      }
                      editingKeyRef.current = "";
                  } }))) : null,
          showPostKey ? (React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.TextField, { label: "Key after text", description: "Focus this field to open the Steam virtual keyboard. It saves when focus leaves the field.", value: postKey, onFocus: () => {
                      editingKeyRef.current = "post";
                  }, onChange: (event) => {
                      dirtyKeysRef.current.post = true;
                      setPostKey(event.currentTarget.value);
                  }, onBlur: async () => {
                      if (dirtyKeysRef.current.post) {
                          await saveTextEntryKey("post", postKey);
                      }
                      editingKeyRef.current = "";
                  } }))) : null,
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: () => setShowKeyGuide(true) }, "Key guide")),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Translate to English", checked: translateToEnglish, onChange: async (enabled) => {
                      await serverAPI.callPluginMethod("set_translate_to_english", { enabled });
                      await refresh();
                  } })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ToggleField, { label: "Remote Play typing", description: "Types text as keyboard events without using the clipboard.", checked: remotePlayTyping, onChange: async (enabled) => {
                      await serverAPI.callPluginMethod("set_remote_play_typing", { enabled });
                      await refresh();
                  } })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.DropdownItem, { label: "Steam Deck button", layout: "below", rgOptions: STEAM_DECK_BUTTON_OPTIONS, selectedOption: steamDeckButton, onChange: async (option) => {
                      await updateSteamDeckButton(String(option.data));
                  } })),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: async () => {
                      await serverAPI.callPluginMethod("start_recording", {});
                      await refresh();
                  } }, "Start recording")),
          React__default["default"].createElement(deckyFrontendLib.PanelSectionRow, null,
              React__default["default"].createElement(deckyFrontendLib.ButtonItem, { layout: "below", onClick: async () => {
                      await serverAPI.callPluginMethod("stop_recording", {});
                      await refresh();
                  } }, "Stop and transcribe"))));
  }
  var index = deckyFrontendLib.definePlugin((serverAPI) => {
      let lastKnownApp = "";
      const syncActiveGame = async () => {
          try {
              const { appId, appName } = await getActiveGame();
              const signature = `${appId}:${appName}`;
              if (signature === lastKnownApp)
                  return;
              lastKnownApp = signature;
              await serverAPI.callPluginMethod("set_active_game", { app_id: appId, app_name: appName });
          }
          catch {
              // no-op
          }
      };
      syncActiveGame();
      const gameSyncTimer = window.setInterval(syncActiveGame, 2000);
      return {
          title: React__default["default"].createElement("div", { className: deckyFrontendLib.staticClasses.Title }, "AI Speech-to-Text"),
          content: React__default["default"].createElement(Content, { serverAPI: serverAPI }),
          icon: React__default["default"].createElement(FaMicrophone, null),
          onDismount() {
              window.clearInterval(gameSyncTimer);
          }
      };
  });

  return index;

})(DFL, SP_REACT);
