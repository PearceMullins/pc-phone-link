const state = {
  token: null,
  connectCode: null,
  connectInFlight: false,
  pairingApprovalCode: null,
  pairingDeviceName: null,
  connectInfoPollTimer: null,
  connectInfoPollAttempts: 0,
  pairingPollTimer: null,
  selectedWindow: null,
  previousNonDesktopWindow: null,
  defaultDesktopHandled: false,
  windows: [],
  mouseSpeed: 2.5,
  tapMode: "left",
  controlMode: "touch",
  controlsHidden: false,
  bottomNavOptional: [],
  currentDestination: "viewer",
  recentWindowKeys: [],
  fitShape: "auto",
  trustedDevices: [],
  trustedDevicesLoading: false,
  phoneFitEnabled: false,
  pointerDown: false,
  dragActive: false,
  pointerId: null,
  startClientPoint: null,
  lastClientPoint: null,
  startSourcePoint: null,
  lastSourcePoint: null,
  directTouchDownSent: false,
  toastTimer: null,
  windowsRefreshTimer: null,
  hostReconnectTimer: null,
  hostReconnectAttempts: 0,
  authRequiredTimer: null,
  controlQueue: Promise.resolve(),
  moveRequestInFlight: false,
  pendingMovePayload: null,
  touchMoveScheduled: false,
  pendingTouchMovePayload: null,
  keyboardVisibilityTimer: null,
  keyboardComposerRequested: false,
  keyboardPanelHoldUntil: 0,
  keyboardViewportMaxHeight: 0,
  keyboardViewportOrientation: null,
  cameraScale: 1,
  cameraFocus: { x: 0.5, y: 0.5 },
  cameraTranslate: { x: 0, y: 0 },
  cursorPosition: { x: 0.5, y: 0.5, visible: false },
  typingAnchor: null,
  messageHistory: [],
  messageHistoryExpanded: false,
  followTyping: false,
  followMouse: false,
  activePointers: new Map(),
  twoFingerGesture: null,
  pendingTap: null,
  gestureStatusTimer: null,
  suppressPrimaryTapUp: false,
  installPrompt: null,
  followTypingLogBuffer: [],
  followTypingLogTimer: null,
  followTypingLogFlushInFlight: false,
  streamFps: 20,
  streamWidth: "auto",
  streamRefreshTimer: null,
  streamSocket: null,
  streamGeneration: 0,
  streamObjectUrl: null,
  streamSocketFailures: 0,
  streamParams: null,
  streamFallbackActive: false,
  voiceRecognition: null,
  voiceListening: false,
  voiceStarting: false,
  voiceBaseText: "",
  textScale: 100,
  confirmedTextScale: 100,
  pendingTextScaleValue: null,
  pendingTextScaleToast: false,
  textScaleApplyTimer: null,
  textScaleRequestInFlight: false,
  gestureDiagnosticsEnabled: true,
  gestureLogBuffer: [],
  gestureLogTimer: null,
  gestureLogFlushInFlight: false,
  gestureSessionId: "",
  currentGestureId: "",
  pointerType: "unknown",
  lastGestureMoveLoggedAt: 0,
  lastOutboundMoveLoggedAt: 0,
};

const TRACKPAD_BASE_SPEED = 2.8;
const FOLLOW_TYPING_MIN_SCALE = 1.6;
const FOLLOW_TYPING_LOG_BATCH_SIZE = 8;
const FOLLOW_TYPING_LOG_FLUSH_DELAY_MS = 1200;
const ACCESS_TOKEN_STORAGE_KEY = "pc-phone-link-token";
const PAIRING_DEVICE_NAME_STORAGE_KEY = "pc-phone-link-pairing-device-name";
const FIT_SHAPE_STORAGE_KEY = "pc-phone-link-fit-shape";
const CONTROL_MODE_STORAGE_KEY = "pc-phone-link-control-mode";
const BOTTOM_NAV_STORAGE_KEY = "pc-phone-link-bottom-nav";
const GESTURE_DIAGNOSTICS_STORAGE_KEY = "pc-phone-link-gesture-diagnostics";
const RECENT_WINDOWS_STORAGE_KEY = "pc-phone-link-recent-windows";
const STREAM_FPS_STORAGE_KEY = "pc-phone-link-stream-fps";
const STREAM_WIDTH_STORAGE_KEY = "pc-phone-link-stream-width";
const STREAM_WIDTH_OPTIONS = [1920, 1600, 1280, 960, 720, 480];
const MESSAGE_HISTORY_STORAGE_KEY = "pc-phone-link-message-history";
const MESSAGE_DRAFT_STORAGE_KEY = "pc-phone-link-message-draft";
const MAX_MESSAGE_HISTORY = 100;
const MAX_VISIBLE_MESSAGE_HISTORY = 12;
const KEYBOARD_VISIBLE_HEIGHT_DELTA = 140;
const KEYBOARD_VISIBLE_HEIGHT_RATIO = 0.18;
const DIRECT_TOUCH_DRAG_THRESHOLD = 7;
const DOUBLE_TAP_DELAY_MS = 320;
const DOUBLE_TAP_DISTANCE_PX = 28;
const TWO_FINGER_PINCH_THRESHOLD = 12;
const TWO_FINGER_SCROLL_HOLD_MS = 360;
const TWO_FINGER_HOLD_SLOP = 10;
const TWO_FINGER_SCROLL_START_THRESHOLD = 6;
const TWO_FINGER_TAP_MAX_MS = 260;
const TWO_FINGER_TAP_SLOP = 12;
const MAX_CAMERA_SCALE = 6;
const MAX_STREAM_FPS = 30;
const DEFAULT_STREAM_FPS = 20;
const MAX_STREAM_REQUEST_WIDTH = 1920;
const MAX_STREAM_DEVICE_PIXEL_RATIO = 2.5;
const STREAM_WIDTH_QUANTUM = 64;
const STREAM_REFRESH_DEBOUNCE_MS = 180;
const STREAM_SOCKET_MAX_FAILURES = 2;
const STREAM_RECONNECT_DELAY_MS = 600;
const AUTH_REQUIRED_MESSAGE = "Connect your phone to use PC Phone Link.";
const AUTH_REQUIRED_RECHECK_DELAY_MS = 500;
const MOBILE_SHELL_MEDIA = "(max-width: 899px), ((hover: none) and (pointer: coarse) and (max-width: 1366px))";
const DEFAULT_BOTTOM_NAV_OPTIONAL = ["desktop", "windows", "keyboard"];
const MANDATORY_BOTTOM_NAV = ["controls", "settings"];
const MAX_OPTIONAL_BOTTOM_NAV = 3;
const BOTTOM_NAV_CATALOG = Object.freeze({
  desktop: { label: "Full screen", icon: "▣" },
  windows: { label: "Windows", icon: "▤" },
  keyboard: { label: "Keyboard", icon: "⌨" },
  gestureHelp: { label: "Gestures", icon: "?" },
  rightClick: { label: "Right-click next tap", icon: "R" },
  doubleClick: { label: "Double-click next tap", icon: "2×" },
  fit: { label: "Fit", icon: "↔" },
  power: { label: "Power", icon: "⏻" },
  modeToggle: { label: "Input mode", icon: "◎" },
  controls: { label: "Controls", icon: "◎", mandatory: true },
  settings: { label: "Settings", icon: "⚙", mandatory: true },
});

const POWER_ACTIONS = {
  lock: { confirm: null, pending: "Locking the PC", done: "PC locked." },
  sleep: { confirm: null, pending: "Putting the PC to sleep", done: "Sleep requested." },
  restart: { confirm: "Restart the PC now?", pending: "Restarting the PC", done: "Restart requested." },
  shutdown: { confirm: "Shut down the PC now?", pending: "Shutting down the PC", done: "Shutdown requested." },
};

const FIT_SHAPES = {
  auto: { label: "Phone", aspect: null },
  "16-9": { label: "16:9", aspect: 16 / 9 },
  "16-10": { label: "16:10", aspect: 16 / 10 },
  "4-3": { label: "4:3", aspect: 4 / 3 },
  "1-1": { label: "Square", aspect: 1 },
  "3-4": { label: "Tall", aspect: 3 / 4 },
};

class AuthRequiredError extends Error {
  constructor(message = AUTH_REQUIRED_MESSAGE) {
    super(message);
    this.name = "AuthRequiredError";
    this.authRequired = true;
  }
}

const elements = {
  app: document.getElementById("app"),
  applyTextScale: document.getElementById("applyTextScale"),
  authPanel: document.getElementById("authPanel"),
  connectButton: document.getElementById("connectButton"),
  connectCodeDisplay: document.getElementById("connectCodeDisplay"),
  connectStatus: document.getElementById("connectStatus"),
  connectionStatus: document.getElementById("connectionStatus"),
  controlsPanel: document.getElementById("controlsPanel"),
  controlMode: document.getElementById("controlMode"),
  controlModeHelp: document.getElementById("controlModeHelp"),
  pairingApprovalCodeBlock: document.getElementById("pairingApprovalCodeBlock"),
  pairingApprovalCodeDisplay: document.getElementById("pairingApprovalCodeDisplay"),
  pairingDeviceName: document.getElementById("pairingDeviceName"),
  clearTextInput: document.getElementById("clearTextInput"),
  controlBar: document.getElementById("controlBar"),
  doubleClickMode: document.getElementById("doubleClickMode"),
  emptyState: document.getElementById("emptyState"),
  applyFitShape: document.getElementById("applyFitShape"),
  fitToggle: document.getElementById("fitToggle"),
  fitShape: document.getElementById("fitShape"),
  fitShapeValue: document.getElementById("fitShapeValue"),
  focusWindow: document.getElementById("focusWindow"),
  followMouse: document.getElementById("followMouse"),
  keyboardPanel: document.getElementById("keyboardPanel"),
  mobileNav: document.getElementById("mobileNav"),
  maximizeWindow: document.getElementById("maximizeWindow"),
  messageHistory: document.getElementById("messageHistory"),
  messageHistorySection: document.getElementById("messageHistorySection"),
  mouseSpeed: document.getElementById("mouseSpeed"),
  mouseSpeedValue: document.getElementById("mouseSpeedValue"),
  powerMenu: document.getElementById("powerMenu"),
  powerToggle: document.getElementById("powerToggle"),
  settingsPowerMenu: document.getElementById("settingsPowerMenu"),
  settingsPowerToggle: document.getElementById("settingsPowerToggle"),
  refreshWindows: document.getElementById("refreshWindows"),
  refreshTrustedDevices: document.getElementById("refreshTrustedDevices"),
  remoteView: document.getElementById("remoteView"),
  restoreWindow: document.getElementById("restoreWindow"),
  rightClickMode: document.getElementById("rightClickMode"),
  scrollDown: document.getElementById("scrollDown"),
  scrollUp: document.getElementById("scrollUp"),
  sendText: document.getElementById("sendText"),
  streamFps: document.getElementById("streamFps"),
  streamFpsValue: document.getElementById("streamFpsValue"),
  streamWidth: document.getElementById("streamWidth"),
  streamWidthValue: document.getElementById("streamWidthValue"),
  textScale: document.getElementById("textScale"),
  textScaleValue: document.getElementById("textScaleValue"),
  textLarger: document.getElementById("textLarger"),
  textForm: document.getElementById("textForm"),
  textInput: document.getElementById("textInput"),
  textSmaller: document.getElementById("textSmaller"),
  toast: document.getElementById("toast"),
  toggleControls: document.getElementById("toggleControls"),
  toggleKeyboard: document.getElementById("toggleKeyboard"),
  touchLayer: document.getElementById("touchLayer"),
  trustedDevices: document.getElementById("trustedDevices"),
  trustedDevicesStatus: document.getElementById("trustedDevicesStatus"),
  toggleMessageHistory: document.getElementById("toggleMessageHistory"),
  settingsPanel: document.getElementById("settingsPanel"),
  installApp: document.getElementById("installApp"),
  installCard: document.getElementById("installCard"),
  installStatus: document.getElementById("installStatus"),
  gestureHelp: document.getElementById("gestureHelp"),
  gestureHelpButton: document.getElementById("gestureHelpButton"),
  gestureStatus: document.getElementById("gestureStatus"),
  gestureDiagnostics: document.getElementById("gestureDiagnostics"),
  gestureLogPath: document.getElementById("gestureLogPath"),
  clearGestureLogs: document.getElementById("clearGestureLogs"),
  bottomNavEditor: document.getElementById("bottomNavEditor"),
  bottomNavAdd: document.getElementById("bottomNavAdd"),
  bottomNavAddButton: document.getElementById("bottomNavAddButton"),
  bottomNavReset: document.getElementById("bottomNavReset"),
  revealControls: document.getElementById("revealControls"),
  viewerShell: document.getElementById("viewerShell"),
  voiceInput: document.getElementById("voiceInput"),
  windowDrawer: document.getElementById("windowDrawer"),
  windowList: document.getElementById("windowList"),
};

function clampRatio(value) {
  return Math.max(0, Math.min(1, value));
}

function usesMobileShell() {
  return window.matchMedia(MOBILE_SHELL_MEDIA).matches;
}

function sanitizeBottomNavOptional(value) {
  if (!Array.isArray(value)) return [...DEFAULT_BOTTOM_NAV_OPTIONAL];
  const seen = new Set();
  return value.filter((id) => {
    if (typeof id !== "string" || seen.has(id) || MANDATORY_BOTTOM_NAV.includes(id)) return false;
    const item = BOTTOM_NAV_CATALOG[id];
    if (!item || item.mandatory) return false;
    seen.add(id);
    return true;
  }).slice(0, MAX_OPTIONAL_BOTTOM_NAV);
}

function loadBottomNavConfig() {
  const saved = window.localStorage.getItem(BOTTOM_NAV_STORAGE_KEY);
  if (saved === null) {
    state.bottomNavOptional = [...DEFAULT_BOTTOM_NAV_OPTIONAL];
  } else {
    try {
      const parsed = JSON.parse(saved);
      state.bottomNavOptional = sanitizeBottomNavOptional(parsed);
      if (JSON.stringify(parsed) !== JSON.stringify(state.bottomNavOptional)) {
        window.localStorage.setItem(BOTTOM_NAV_STORAGE_KEY, JSON.stringify(state.bottomNavOptional));
      }
    } catch {
      state.bottomNavOptional = [...DEFAULT_BOTTOM_NAV_OPTIONAL];
      window.localStorage.setItem(BOTTOM_NAV_STORAGE_KEY, JSON.stringify(state.bottomNavOptional));
    }
  }
  renderBottomNav();
  renderBottomNavEditor();
}

function saveBottomNavConfig(optionalItems) {
  state.bottomNavOptional = sanitizeBottomNavOptional(optionalItems);
  window.localStorage.setItem(BOTTOM_NAV_STORAGE_KEY, JSON.stringify(state.bottomNavOptional));
  logGestureDiagnostic("bottom-nav-config", {
    action: "save",
    pointer_count: state.bottomNavOptional.length,
    state: "updated",
  });
  renderBottomNav();
  renderBottomNavEditor();
}

function bottomNavItemState(id) {
  if (id === "desktop") return state.currentDestination === "viewer" && Boolean(state.selectedWindow?.is_desktop_capture);
  if (["windows", "keyboard", "controls", "settings"].includes(id)) return state.currentDestination === id;
  if (id === "rightClick") return state.tapMode === "right";
  if (id === "doubleClick") return state.tapMode === "double";
  if (id === "fit") return state.phoneFitEnabled;
  if (id === "power") return state.currentDestination === "settings" && elements.settingsPowerToggle?.getAttribute("aria-expanded") === "true";
  if (id === "gestureHelp") return Boolean(elements.gestureHelp?.open);
  return false;
}

function bottomNavLabel(id) {
  if (id === "modeToggle") return state.controlMode === "touch" ? "App touch" : "Mouse trackpad";
  return BOTTOM_NAV_CATALOG[id]?.label || id;
}

function renderBottomNav() {
  if (!elements.mobileNav) return;
  const ids = [...sanitizeBottomNavOptional(state.bottomNavOptional), ...MANDATORY_BOTTOM_NAV];
  elements.mobileNav.replaceChildren();
  elements.mobileNav.style.setProperty("--nav-count", String(ids.length));
  for (const id of ids) {
    const item = BOTTOM_NAV_CATALOG[id];
    if (!item) continue;
    const label = bottomNavLabel(id);
    const active = bottomNavItemState(id);
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.bottomAction = id;
    button.classList.toggle("active", active);
    button.setAttribute("aria-label", id === "modeToggle"
      ? `Input mode: ${label}. Tap to switch.`
      : label);
    button.setAttribute("aria-pressed", String(active));
    const icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = item.icon;
    const text = document.createElement("small");
    text.textContent = label;
    button.append(icon, text);
    elements.mobileNav.append(button);
  }
}

function createBottomNavEditorRow(id, index, mandatory = false) {
  const row = document.createElement("div");
  row.className = "bottom-nav-editor-row";
  row.dataset.shortcutId = id;
  const label = document.createElement("span");
  label.textContent = BOTTOM_NAV_CATALOG[id].label;
  const actions = document.createElement("div");
  actions.className = "bottom-nav-editor-actions";
  for (const [action, text] of [["up", "Up"], ["down", "Down"], ["remove", "Remove"]]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ghost-button compact-button";
    button.dataset.navEditorAction = action;
    button.dataset.shortcutId = id;
    button.textContent = text;
    button.disabled = mandatory || (action === "up" && index === 0)
      || (action === "down" && index === state.bottomNavOptional.length - 1);
    button.setAttribute("aria-label", `${text} ${BOTTOM_NAV_CATALOG[id].label}`);
    actions.append(button);
  }
  if (mandatory) {
    row.classList.add("mandatory");
    label.textContent += " (always shown)";
  }
  row.append(label, actions);
  return row;
}

function renderBottomNavEditor() {
  if (!elements.bottomNavEditor || !elements.bottomNavAdd) return;
  elements.bottomNavEditor.replaceChildren();
  state.bottomNavOptional.forEach((id, index) => {
    elements.bottomNavEditor.append(createBottomNavEditorRow(id, index));
  });
  MANDATORY_BOTTOM_NAV.forEach((id) => {
    elements.bottomNavEditor.append(createBottomNavEditorRow(id, -1, true));
  });
  elements.bottomNavAdd.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = state.bottomNavOptional.length >= MAX_OPTIONAL_BOTTOM_NAV
    ? "Remove a shortcut to add another"
    : "Choose shortcut";
  elements.bottomNavAdd.append(placeholder);
  Object.entries(BOTTOM_NAV_CATALOG).forEach(([id, item]) => {
    if (item.mandatory || state.bottomNavOptional.includes(id)) return;
    const option = document.createElement("option");
    option.value = id;
    option.textContent = item.label;
    elements.bottomNavAdd.append(option);
  });
  const atLimit = state.bottomNavOptional.length >= MAX_OPTIONAL_BOTTOM_NAV;
  elements.bottomNavAdd.disabled = atLimit;
  if (elements.bottomNavAddButton) elements.bottomNavAddButton.disabled = atLimit;
}

async function selectDesktopCapture() {
  if (state.currentDestination === "viewer" && state.selectedWindow?.is_desktop_capture) {
    let previous = state.previousNonDesktopWindow;
    state.previousNonDesktopWindow = null;
    if (previous) {
      const current = state.windows.find((windowInfo) => windowInfo.hwnd === previous.hwnd);
      previous = current || previous;
      try {
        await selectWindow(previous);
        logGestureDiagnostic("bottom-nav-action", { action: "desktop", result: "restored" });
        return;
      } catch {
        // Previous app may have closed while desktop capture was active.
      }
    }
    state.selectedWindow = null;
    resetViewer();
    openDestination("viewer");
    showToast("Full screen closed. Open Windows to choose an app.");
    logGestureDiagnostic("bottom-nav-action", { action: "desktop", result: "closed" });
    return;
  }
  if (state.selectedWindow && !state.selectedWindow.is_desktop_capture) {
    state.previousNonDesktopWindow = state.selectedWindow;
  } else {
    state.previousNonDesktopWindow = null;
  }
  let target = state.windows.find((windowInfo) => windowInfo.is_desktop_capture);
  if (!target) {
    try {
      await refreshWindows();
    } catch (error) {
      showToast(`Could not refresh Windows. ${error.message || "Try again."}`);
      return;
    }
    target = state.windows.find((windowInfo) => windowInfo.is_desktop_capture);
  }
  if (!target) {
    showToast("Full screen is unavailable. Open Windows, tap Refresh, then try again.");
    logGestureDiagnostic("bottom-nav-action", { action: "desktop", result: "unavailable" });
    return;
  }
  logGestureDiagnostic("bottom-nav-action", { action: "desktop", result: "selected" });
  await selectWindow(target);
}

async function maybeSelectDefaultDesktopCapture() {
  if (state.selectedWindow || state.defaultDesktopHandled) return;
  const target = state.windows.find((windowInfo) => windowInfo.is_desktop_capture);
  if (!target) return;
  state.defaultDesktopHandled = true;
  try {
    await selectWindow(target);
    logGestureDiagnostic("bottom-nav-action", { action: "desktop", result: "default" }, { immediate: true });
  } catch {
    state.defaultDesktopHandled = false;
  }
}

async function executeBottomNavAction(id) {
  logGestureDiagnostic("bottom-nav-action", { action: id, state: "invoked" });
  if (id === "desktop") return selectDesktopCapture();
  if (["windows", "keyboard", "controls", "settings"].includes(id)) {
    openDestination(id, { toggle: true });
    return;
  }
  if (id === "gestureHelp") {
    if (elements.gestureHelp?.open) elements.gestureHelp.close();
    else elements.gestureHelp?.showModal();
    renderBottomNav();
  } else if (id === "rightClick") {
    setTapMode(state.tapMode === "right" ? "left" : "right");
    showGestureStatus(state.tapMode === "right" ? "Right-click armed" : "Right-click canceled");
  } else if (id === "doubleClick") {
    setTapMode(state.tapMode === "double" ? "left" : "double");
    showGestureStatus(state.tapMode === "double" ? "Double-click armed" : "Double-click canceled");
  } else if (id === "fit") {
    await handleFitToggle();
  } else if (id === "power") {
    const powerOpen = state.currentDestination === "settings"
      && elements.settingsPowerToggle?.getAttribute("aria-expanded") === "true";
    if (powerOpen) {
      closePowerMenus();
      openDestination("viewer");
    } else {
      openDestination("settings");
      togglePowerMenu(true, "settings");
    }
  } else if (id === "modeToggle") {
    setControlMode(state.controlMode === "touch" ? "trackpad" : "touch");
    showGestureStatus(bottomNavLabel(id));
  }
  renderBottomNav();
}

function getViewportSize() {
  const viewport = window.visualViewport;
  return {
    width: Math.max(Math.round(viewport ? viewport.width : window.innerWidth), 320),
    height: Math.max(Math.round(viewport ? viewport.height : window.innerHeight), 320),
  };
}

function syncViewportLayout() {
  const viewport = window.visualViewport;
  const nextHeight = Math.max(Math.round(viewport ? viewport.height : window.innerHeight), 1);
  const nextOffsetTop = Math.max(Math.round(viewport ? viewport.offsetTop : 0), 0);
  document.documentElement.style.setProperty("--app-viewport-height", `${nextHeight}px`);
  document.documentElement.style.setProperty("--app-viewport-offset-top", `${nextOffsetTop}px`);
}

function getViewerFitSize() {
  const viewerRect = elements.viewerShell.getBoundingClientRect();
  const viewport = getViewportSize();
  const viewerWidth = Math.max(Math.round(viewerRect.width || 0), 0);
  const viewerHeight = Math.max(Math.round(viewerRect.height || 0), 0);

  if (viewerWidth >= 240 && viewerHeight >= 240) {
    return {
      width: viewerWidth,
      height: viewerHeight,
    };
  }

  return {
    width: Math.max(viewport.width, 240),
    height: Math.max(viewport.height, 240),
  };
}

function getSelectedFitShape() {
  return FIT_SHAPES[state.fitShape] || FIT_SHAPES.auto;
}

function getPhoneFitRequestSize(viewerSize = getViewerFitSize()) {
  const shape = getSelectedFitShape();
  if (!shape.aspect) {
    return viewerSize;
  }

  let width = Math.max(Math.round(viewerSize.width), 240);
  let height = Math.max(Math.round(width / shape.aspect), 240);
  const maxHeight = Math.max(Math.round(viewerSize.height), 240);
  if (height > maxHeight) {
    height = maxHeight;
    width = Math.max(Math.round(height * shape.aspect), 240);
  }

  return { width, height };
}

function syncFitShapeControls() {
  const shape = getSelectedFitShape();
  if (elements.fitShape) {
    elements.fitShape.value = state.fitShape;
  }
  if (elements.fitShapeValue) {
    elements.fitShapeValue.textContent = shape.label;
  }
  if (elements.applyFitShape) {
    const disabled = !state.selectedWindow || Boolean(state.selectedWindow?.is_desktop_capture);
    elements.applyFitShape.disabled = disabled;
  }
}

function setFitShape(value, { apply = false } = {}) {
  state.fitShape = FIT_SHAPES[value] ? value : "auto";
  window.localStorage.setItem(FIT_SHAPE_STORAGE_KEY, state.fitShape);
  syncFitShapeControls();
  if (apply && state.selectedWindow && !state.selectedWindow.is_desktop_capture) {
    applyPhoneFit("fit-shape-change").catch((error) => showToast(error.message));
  }
}

function syncControlMode() {
  if (elements.controlMode) {
    elements.controlMode.value = state.controlMode;
  }
  if (elements.controlModeHelp) {
    elements.controlModeHelp.textContent = state.controlMode === "touch"
      ? "Tap to click, double-tap to right-click, quick two-finger tap to double-click, one finger to pan viewer, hold two fingers until Scroll ready then hold one finger and drag the other to scroll, and pinch to zoom."
      : "Drag to move PC mouse, tap to click, and use controls below for scrolling and right-click.";
  }
  elements.viewerShell.classList.toggle("direct-touch-active", state.controlMode === "touch");
}

function setControlMode(value) {
  const nextMode = value === "trackpad" ? "trackpad" : "touch";
  if (nextMode !== state.controlMode) cancelPendingTap("mode-change");
  if (nextMode !== state.controlMode && (state.pointerDown || state.activePointers.size)) {
    releaseActiveTouches();
  }
  state.controlMode = nextMode;
  window.localStorage.setItem(CONTROL_MODE_STORAGE_KEY, state.controlMode);
  syncControlMode();
  renderBottomNav();
}

function clampStreamFps(value) {
  const nextValue = Number.parseInt(String(value), 10);
  if (!Number.isFinite(nextValue)) {
    return DEFAULT_STREAM_FPS;
  }
  return Math.max(1, Math.min(nextValue, MAX_STREAM_FPS));
}

function syncStreamFpsControl() {
  if (elements.streamFps) {
    elements.streamFps.value = String(state.streamFps);
  }
  if (elements.streamFpsValue) {
    elements.streamFpsValue.textContent = `${state.streamFps} fps`;
  }
}

function setStreamFps(value, { persist = false, refresh = false } = {}) {
  state.streamFps = clampStreamFps(value);
  if (persist) {
    window.localStorage.setItem(STREAM_FPS_STORAGE_KEY, String(state.streamFps));
  }
  syncStreamFpsControl();
  if (refresh) {
    scheduleStreamRefresh(0);
  }
}

function normalizeStreamWidth(value) {
  if (value === null || value === undefined || value === "auto") {
    return "auto";
  }
  const nextValue = Number.parseInt(String(value), 10);
  return STREAM_WIDTH_OPTIONS.includes(nextValue) ? nextValue : "auto";
}

function syncStreamWidthControl() {
  if (elements.streamWidth) {
    elements.streamWidth.value = String(state.streamWidth);
  }
  if (elements.streamWidthValue) {
    elements.streamWidthValue.textContent = state.streamWidth === "auto" ? "Auto" : `${state.streamWidth} px`;
  }
}

function setStreamWidth(value, { persist = false, refresh = false } = {}) {
  state.streamWidth = normalizeStreamWidth(value);
  if (persist) {
    window.localStorage.setItem(STREAM_WIDTH_STORAGE_KEY, String(state.streamWidth));
  }
  syncStreamWidthControl();
  if (refresh) {
    scheduleStreamRefresh(0);
  }
}

function getViewportOrientation() {
  const { width, height } = getViewportSize();
  return width >= height ? "landscape" : "portrait";
}

function getSourceSize() {
  if (state.selectedWindow?.bounds?.width && state.selectedWindow?.bounds?.height) {
    return {
      width: state.selectedWindow.bounds.width,
      height: state.selectedWindow.bounds.height,
    };
  }
  return {
    width: elements.viewerShell.clientWidth || 1,
    height: elements.viewerShell.clientHeight || 1,
  };
}

function getDisplayedImageRect() {
  const source = getSourceSize();
  const viewerWidth = elements.viewerShell.clientWidth || 1;
  const viewerHeight = elements.viewerShell.clientHeight || 1;
  const scale = Math.min(viewerWidth / source.width, viewerHeight / source.height);
  const width = source.width * scale;
  const height = source.height * scale;
  return {
    left: (viewerWidth - width) / 2,
    top: (viewerHeight - height) / 2,
    width,
    height,
  };
}

function viewerPointToSourceNormalized(clientX, clientY, { useCameraTransform = true } = {}) {
  const viewerRect = elements.viewerShell.getBoundingClientRect();
  const displayed = getDisplayedImageRect();
  let localX = clientX - viewerRect.left;
  let localY = clientY - viewerRect.top;

  if (useCameraTransform && state.cameraScale > 1) {
    localX = (localX - state.cameraTranslate.x) / state.cameraScale;
    localY = (localY - state.cameraTranslate.y) / state.cameraScale;
  }

  const normalizedX = (localX - displayed.left) / displayed.width;
  const normalizedY = (localY - displayed.top) / displayed.height;

  if (!Number.isFinite(normalizedX) || !Number.isFinite(normalizedY)) {
    return null;
  }
  if (normalizedX < 0 || normalizedX > 1 || normalizedY < 0 || normalizedY > 1) {
    return null;
  }

  return {
    x: clampRatio(normalizedX),
    y: clampRatio(normalizedY),
  };
}

function setCameraScale(nextScale) {
  const previousScale = state.cameraScale;
  const clampedScale = Math.max(1, Math.min(nextScale, MAX_CAMERA_SCALE));
  state.cameraScale = clampedScale < 1.15 ? 1 : clampedScale;
  applyCameraTransform();
  if (Math.abs(previousScale - state.cameraScale) >= 0.05) {
    scheduleStreamRefresh();
  }
}

function setCameraFocus(x, y) {
  state.cameraFocus = {
    x: clampRatio(x),
    y: clampRatio(y),
  };
  applyCameraTransform();
}

function panCameraByClientDelta(deltaX, deltaY) {
  if (state.cameraScale <= 1) return false;
  const displayed = getDisplayedImageRect();
  const width = Math.max(displayed.width * state.cameraScale, 1);
  const height = Math.max(displayed.height * state.cameraScale, 1);
  const previous = { ...state.cameraFocus };
  setCameraFocus(
    state.cameraFocus.x - (deltaX / width),
    state.cameraFocus.y - (deltaY / height),
  );
  return Math.abs(previous.x - state.cameraFocus.x) > 0.0001
    || Math.abs(previous.y - state.cameraFocus.y) > 0.0001;
}

function getTypingMetrics() {
  const bounds = state.selectedWindow?.bounds || {};
  const width = Math.max(Number(bounds.width) || 1280, 320);
  const height = Math.max(Number(bounds.height) || 720, 240);
  return {
    charWidth: Math.max(16 / width, 0.008),
    spaceWidth: Math.max(10 / width, 0.005),
    lineHeight: Math.max(30 / height, 0.032),
    minX: 0.04,
    maxX: 0.96,
    minY: 0.05,
    maxY: 0.95,
  };
}

function applyCameraTransform() {
  if (!state.selectedWindow) {
    state.cameraTranslate = { x: 0, y: 0 };
    elements.remoteView.style.transformOrigin = "0 0";
    elements.remoteView.style.transform = "none";
    return;
  }

  if (state.cameraScale === 1) {
    state.cameraTranslate = { x: 0, y: 0 };
    elements.remoteView.style.transformOrigin = "0 0";
    elements.remoteView.style.transform = "none";
    return;
  }

  const viewerWidth = elements.viewerShell.clientWidth || 1;
  const viewerHeight = elements.viewerShell.clientHeight || 1;
  const displayed = getDisplayedImageRect();
  const focusX = displayed.left + (displayed.width * state.cameraFocus.x);
  const focusY = displayed.top + (displayed.height * state.cameraFocus.y);
  const scale = state.cameraScale;

  let translateX = (viewerWidth / 2) - (focusX * scale);
  let translateY = (viewerHeight / 2) - (focusY * scale);

  const minTranslateX = viewerWidth - ((displayed.left + displayed.width) * scale);
  const maxTranslateX = -(displayed.left * scale);
  const minTranslateY = viewerHeight - ((displayed.top + displayed.height) * scale);
  const maxTranslateY = -(displayed.top * scale);

  if (minTranslateX <= maxTranslateX) {
    translateX = Math.min(maxTranslateX, Math.max(minTranslateX, translateX));
  } else {
    // Scaled content doesn't cover the viewer on this axis yet: keep it
    // centered instead of pinning the element to the viewer origin, which
    // pushed the letterboxed image off-center (fullscreen zoom stuck at top).
    translateX = (viewerWidth / 2) - ((displayed.left + (displayed.width / 2)) * scale);
  }

  if (minTranslateY <= maxTranslateY) {
    translateY = Math.min(maxTranslateY, Math.max(minTranslateY, translateY));
  } else {
    translateY = (viewerHeight / 2) - ((displayed.top + (displayed.height / 2)) * scale);
  }

  elements.remoteView.style.transformOrigin = "0 0";
  elements.remoteView.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
  state.cameraTranslate = { x: translateX, y: translateY };
}

function syncCameraToCursor() {
  if (!state.cursorPosition.visible) {
    return;
  }
  setCameraFocus(state.cursorPosition.x, state.cursorPosition.y);
}

function setTypingAnchorFromCursor(cursor = state.cursorPosition, reason = "cursor") {
  if (!cursor) {
    return;
  }

  const nextX = Number(cursor.x);
  const nextY = Number(cursor.y);
  const anchorX = clampRatio(Number.isFinite(nextX) ? nextX : state.cameraFocus.x);
  const anchorY = clampRatio(Number.isFinite(nextY) ? nextY : state.cameraFocus.y);
  state.typingAnchor = {
    x: anchorX,
    y: anchorY,
    lineStartX: Math.max(0.06, Math.min(anchorX, 0.18)),
  };
  queueFollowTypingLog("anchor-set", buildFollowTypingLogDetails({
    reason,
    source: cursor.visible ? "cursor" : "camera-focus",
  }));
  if (state.followTyping) {
    syncCameraToTypingAnchor();
  }
}

function syncCameraToTypingAnchor() {
  if (!state.followTyping || !state.typingAnchor) {
    return;
  }

  ensureFollowTypingZoom("typing-sync");
  if (state.cameraScale === 1) {
    return;
  }
  const metrics = getTypingMetrics();
  const leadX = Math.min(metrics.charWidth * 4, 0.08);
  const liftY = Math.min(metrics.lineHeight * 1.1, 0.045);
  setCameraFocus(
    clampRatio(state.typingAnchor.x + leadX),
    clampRatio(state.typingAnchor.y - liftY),
  );
}

function getCharacterAdvance(character, metrics) {
  if (character === " ") {
    return metrics.spaceWidth;
  }
  if ("il.,'!:;|".includes(character)) {
    return metrics.charWidth * 0.55;
  }
  if ("mwMW@#%&".includes(character)) {
    return metrics.charWidth * 1.35;
  }
  return metrics.charWidth;
}

function buildFollowTypingLogDetails(extra = {}) {
  return {
    selectedHwnd: state.selectedWindow?.hwnd ?? null,
    desktopCapture: Boolean(state.selectedWindow?.is_desktop_capture),
    cameraScale: Number(state.cameraScale.toFixed(2)),
    cursorVisible: Boolean(state.cursorPosition.visible),
    cursorX: Number(state.cursorPosition.x.toFixed(3)),
    cursorY: Number(state.cursorPosition.y.toFixed(3)),
    anchorX: state.typingAnchor ? Number(state.typingAnchor.x.toFixed(3)) : null,
    anchorY: state.typingAnchor ? Number(state.typingAnchor.y.toFixed(3)) : null,
    keyboardOpen: !elements.keyboardPanel.classList.contains("hidden"),
    ...extra,
  };
}

function scheduleFollowTypingLogFlush() {
  if (state.followTypingLogTimer || !state.followTypingLogBuffer.length) {
    return;
  }
  state.followTypingLogTimer = window.setTimeout(() => {
    state.followTypingLogTimer = null;
    flushFollowTypingLogs();
  }, FOLLOW_TYPING_LOG_FLUSH_DELAY_MS);
}

function queueFollowTypingLog(eventName, details = {}, { immediate = false, force = false } = {}) {
  if (!state.followTyping && !force) {
    return;
  }
  const entry = {
    event: eventName,
    at: new Date().toISOString(),
    details,
  };
  console.debug("[follow-typing]", eventName, details);
  state.followTypingLogBuffer.push(entry);
  if (immediate || state.followTypingLogBuffer.length >= FOLLOW_TYPING_LOG_BATCH_SIZE) {
    flushFollowTypingLogs();
    return;
  }
  scheduleFollowTypingLogFlush();
}

function flushFollowTypingLogs() {
  if (state.followTypingLogTimer) {
    window.clearTimeout(state.followTypingLogTimer);
    state.followTypingLogTimer = null;
  }
  if (!state.followTypingLogBuffer.length || !state.token || state.followTypingLogFlushInFlight) {
    return;
  }

  const entries = state.followTypingLogBuffer.splice(0, state.followTypingLogBuffer.length);
  state.followTypingLogFlushInFlight = true;
  fetch("/api/client-log", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Access-Token": state.token || "",
    },
    body: JSON.stringify({
      category: "follow-typing",
      entries,
    }),
  })
    .catch((error) => {
      console.warn("Failed to write follow-typing logs.", error);
      state.followTypingLogBuffer.unshift(...entries);
      if (state.followTypingLogBuffer.length > 40) {
        state.followTypingLogBuffer.length = 40;
      }
      scheduleFollowTypingLogFlush();
    })
    .finally(() => {
      state.followTypingLogFlushInFlight = false;
      if (state.followTypingLogBuffer.length) {
        scheduleFollowTypingLogFlush();
      }
    });
}

function writeClientLog(category, eventName, details = {}) {
  if (!state.token) {
    return;
  }

  const entry = {
    event: eventName,
    at: new Date().toISOString(),
    details,
  };
  console.debug(`[${category}]`, eventName, details);
  void fetch("/api/client-log", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Access-Token": state.token || "",
    },
    body: JSON.stringify({
      category,
      entries: [entry],
    }),
  }).catch((error) => {
    console.warn(`Failed to write ${category} logs.`, error);
  });
}

function diagnosticId(prefix) {
  if (window.crypto?.randomUUID) return `${prefix}-${window.crypto.randomUUID()}`;
  const random = window.crypto?.getRandomValues
    ? Array.from(window.crypto.getRandomValues(new Uint32Array(2)), (value) => value.toString(36)).join("")
    : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${random}`.slice(0, 80);
}

function safeGestureDetails(details = {}) {
  const allowed = new Set([
    "action", "control_mode", "delta", "delta_x", "delta_y", "duration_ms", "error_code", "error_type",
    "gesture", "gesture_id", "mode", "phase", "pointer_count", "pointer_type", "reason", "request_id",
    "result", "session_id", "state", "target", "x", "y",
  ]);
  const output = {};
  for (const [key, value] of Object.entries(details)) {
    if (!allowed.has(key) || value === undefined || value === null) continue;
    output[key] = typeof value === "string" ? value.slice(0, 120) : value;
  }
  return output;
}

function logGestureDiagnostic(eventName, details = {}, { immediate = false, force = false } = {}) {
  if (!state.gestureDiagnosticsEnabled && !force) return;
  const entry = {
    event: eventName,
    at: new Date().toISOString(),
    details: safeGestureDetails({
      session_id: state.gestureSessionId,
      gesture_id: state.currentGestureId,
      control_mode: state.controlMode,
      pointer_count: state.activePointers.size,
      pointer_type: state.pointerType,
      ...details,
    }),
  };
  state.gestureLogBuffer.push(entry);
  if (state.gestureLogBuffer.length > 80) state.gestureLogBuffer.splice(0, state.gestureLogBuffer.length - 80);
  if (immediate || state.gestureLogBuffer.length >= 20) {
    flushGestureDiagnostics();
    return;
  }
  if (!state.gestureLogTimer) {
    state.gestureLogTimer = window.setTimeout(() => {
      state.gestureLogTimer = null;
      flushGestureDiagnostics();
    }, 750);
  }
}

function flushGestureDiagnostics({ keepalive = false } = {}) {
  if (state.gestureLogTimer) {
    window.clearTimeout(state.gestureLogTimer);
    state.gestureLogTimer = null;
  }
  if (!state.token || !state.gestureLogBuffer.length || state.gestureLogFlushInFlight) return;
  const entries = state.gestureLogBuffer.splice(0, state.gestureLogBuffer.length);
  state.gestureLogFlushInFlight = true;
  fetch("/api/client-log", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Access-Token": state.token || "" },
    body: JSON.stringify({ category: "gesture", entries }),
    keepalive,
  })
    .catch(() => {
      state.gestureLogBuffer.unshift(...entries);
      if (state.gestureLogBuffer.length > 80) state.gestureLogBuffer.length = 80;
    })
    .finally(() => {
      state.gestureLogFlushInFlight = false;
      if (state.gestureLogBuffer.length) logGestureDiagnostic("flush-retry", { reason: "pending" });
    });
}

function summarizeWindowForLog(windowInfo) {
  if (!windowInfo) {
    return null;
  }

  return {
    hwnd: windowInfo.hwnd ?? null,
    title: windowInfo.title ?? null,
    processName: windowInfo.process_name ?? null,
    isMaximized: Boolean(windowInfo.is_maximized),
    isPhoneFit: Boolean(windowInfo.is_phone_fit),
    bounds: windowInfo.bounds ?? null,
  };
}

function buildPhoneFitLogDetails(extra = {}) {
  const viewport = getViewportSize();
  const viewerRect = elements.viewerShell.getBoundingClientRect();
  return {
    selectedWindow: summarizeWindowForLog(state.selectedWindow),
    screenWidth: Math.max(Math.round(window.screen?.width || 0), 0),
    screenHeight: Math.max(Math.round(window.screen?.height || 0), 0),
    viewportWidth: viewport.width,
    viewportHeight: viewport.height,
    viewerShellWidth: Math.max(Math.round(viewerRect.width), 0),
    viewerShellHeight: Math.max(Math.round(viewerRect.height), 0),
    orientation: getViewportOrientation(),
    fitShape: state.fitShape,
    fitButtonLabel: elements.fitToggle.textContent,
    phoneFitEnabled: state.phoneFitEnabled,
    keyboardOpen: !elements.keyboardPanel.classList.contains("hidden"),
    ...extra,
  };
}

function ensureFollowTypingZoom(reason) {
  if (!state.followTyping || state.cameraScale > 1) {
    return false;
  }

  setCameraScale(Math.max(state.cameraScale, FOLLOW_TYPING_MIN_SCALE));
  queueFollowTypingLog("auto-zoom", buildFollowTypingLogDetails({ reason }), { immediate: true });
  return true;
}

function nudgeCameraForTyping(text = "", direction = "forward") {
  if (!state.followTyping) {
    return;
  }

  ensureFollowTypingZoom("typing-nudge");
  if (!state.typingAnchor) {
    setTypingAnchorFromCursor(state.cursorPosition, "typing-nudge");
  }
  if (!state.typingAnchor) {
    queueFollowTypingLog("nudge-skipped", buildFollowTypingLogDetails({ reason: "missing-anchor", direction }), { immediate: true });
    return;
  }

  const metrics = getTypingMetrics();

  if (direction === "backward") {
    const retreatCount = Math.max(text.length || 1, 1);
    state.typingAnchor.x = Math.max(
      metrics.minX,
      state.typingAnchor.x - (metrics.charWidth * retreatCount),
    );
    syncCameraToTypingAnchor();
    queueFollowTypingLog("nudge-backward", buildFollowTypingLogDetails({ direction, textLength: retreatCount }));
    return;
  }

  if (direction === "newline") {
    state.typingAnchor.x = state.typingAnchor.lineStartX;
    state.typingAnchor.y = Math.min(metrics.maxY, state.typingAnchor.y + metrics.lineHeight);
    syncCameraToTypingAnchor();
    queueFollowTypingLog("nudge-newline", buildFollowTypingLogDetails({ direction }));
    return;
  }

  for (const character of text) {
    if (character === "\r") {
      continue;
    }
    if (character === "\n") {
      state.typingAnchor.x = state.typingAnchor.lineStartX;
      state.typingAnchor.y = Math.min(metrics.maxY, state.typingAnchor.y + metrics.lineHeight);
      continue;
    }

    state.typingAnchor.x += getCharacterAdvance(character, metrics);
    if (state.typingAnchor.x > metrics.maxX) {
      state.typingAnchor.x = state.typingAnchor.lineStartX;
      state.typingAnchor.y = Math.min(metrics.maxY, state.typingAnchor.y + metrics.lineHeight);
    }
  }

  state.typingAnchor.x = Math.min(Math.max(state.typingAnchor.x, metrics.minX), metrics.maxX);
  state.typingAnchor.y = Math.min(Math.max(state.typingAnchor.y, metrics.minY), metrics.maxY);
  syncCameraToTypingAnchor();
  queueFollowTypingLog("nudge-forward", buildFollowTypingLogDetails({ direction, textLength: text.length }));
}

function updateCursorPosition(cursor, { allowMouseFollow = false } = {}) {
  if (!cursor) {
    return;
  }

  const nextX = Number(cursor.x);
  const nextY = Number(cursor.y);

  state.cursorPosition = {
    x: clampRatio(Number.isFinite(nextX) ? nextX : 0.5),
    y: clampRatio(Number.isFinite(nextY) ? nextY : 0.5),
    visible: Boolean(cursor.visible),
  };

  if (state.followMouse && allowMouseFollow && state.cursorPosition.visible) {
    syncCameraToCursor();
  }
}

function loadViewerPreferences() {
  const savedMouseSpeed = Number.parseFloat(window.localStorage.getItem("pc-phone-link-mouse-speed") || "");
  if (Number.isFinite(savedMouseSpeed)) {
    state.mouseSpeed = Math.min(Math.max(savedMouseSpeed, 0.5), 8);
  }
  state.followTyping = false;
  window.localStorage.removeItem("pc-phone-link-follow-typing");
  state.followMouse = window.localStorage.getItem("pc-phone-link-follow-mouse") === "true";
  const savedFitShape = window.localStorage.getItem(FIT_SHAPE_STORAGE_KEY) || "auto";
  state.fitShape = FIT_SHAPES[savedFitShape] ? savedFitShape : "auto";
  const savedControlMode = window.localStorage.getItem(CONTROL_MODE_STORAGE_KEY) || "touch";
  state.controlMode = savedControlMode === "trackpad" ? "trackpad" : "touch";
  state.gestureDiagnosticsEnabled = window.localStorage.getItem(GESTURE_DIAGNOSTICS_STORAGE_KEY) !== "false";
  state.gestureSessionId = diagnosticId("session");
  const savedStreamFps = Number.parseInt(window.localStorage.getItem(STREAM_FPS_STORAGE_KEY) || "", 10);
  if (Number.isFinite(savedStreamFps)) {
    state.streamFps = clampStreamFps(savedStreamFps);
  }
  state.streamWidth = normalizeStreamWidth(window.localStorage.getItem(STREAM_WIDTH_STORAGE_KEY));
  try {
    const recent = JSON.parse(window.localStorage.getItem(RECENT_WINDOWS_STORAGE_KEY) || "[]");
    state.recentWindowKeys = Array.isArray(recent) ? recent.filter((key) => typeof key === "string").slice(0, 4) : [];
  } catch {
    state.recentWindowKeys = [];
  }

  if (elements.gestureDiagnostics) elements.gestureDiagnostics.checked = state.gestureDiagnosticsEnabled;
  if (elements.mouseSpeed) elements.mouseSpeed.value = String(state.mouseSpeed);
  if (elements.followMouse) elements.followMouse.checked = state.followMouse;
  updateMouseSpeedLabel();
  syncFitShapeControls();
  syncControlMode();
  syncStreamFpsControl();
  syncStreamWidthControl();
  syncTextScaleControl();
  loadBottomNavConfig();
}

function updateMouseSpeedLabel() {
  if (elements.mouseSpeedValue) elements.mouseSpeedValue.textContent = `${state.mouseSpeed.toFixed(2)}x`;
}

function clampTextScale(value) {
  const nextValue = Number.parseInt(String(value), 10);
  if (!Number.isFinite(nextValue)) {
    return 100;
  }
  return Math.max(100, Math.min(nextValue, 225));
}

function syncTextScaleControl() {
  elements.textScale.value = String(state.textScale);
  elements.textScaleValue.textContent = `${state.textScale}%`;
  if (elements.applyTextScale) {
    const hasPendingChange = state.textScale !== state.confirmedTextScale;
    elements.applyTextScale.disabled = state.textScaleRequestInFlight || !hasPendingChange;
    elements.applyTextScale.textContent = state.textScaleRequestInFlight ? "Applying..." : "Apply text size";
  }
}

function setTextScaleValue(value, { confirmed = false } = {}) {
  const nextValue = clampTextScale(value);
  state.textScale = nextValue;
  if (confirmed) {
    state.confirmedTextScale = nextValue;
    state.pendingTextScaleValue = null;
    state.pendingTextScaleToast = false;
  }
  syncTextScaleControl();
}

function autoResizeTextInput() {
  elements.textInput.style.height = "auto";
  elements.textInput.style.height = `${Math.max(elements.textInput.scrollHeight, 48)}px`;
}

function saveMessageDraft() {
  window.localStorage.setItem(MESSAGE_DRAFT_STORAGE_KEY, elements.textInput.value);
}

function clearComposerDraft({ keepFocus = true } = {}) {
  elements.textInput.value = "";
  saveMessageDraft();
  autoResizeTextInput();
  syncMessageHistoryVisibility();
  if (keepFocus) {
    elements.textInput.focus();
  }
}

function recallMessage(message) {
  elements.textInput.value = message;
  saveMessageDraft();
  autoResizeTextInput();
  syncMessageHistoryVisibility();
  elements.textInput.focus();
}

function syncMessageHistoryVisibility() {
  const hasHistory = state.messageHistory.length > 0;
  const showHistory = hasHistory && state.messageHistoryExpanded;
  elements.toggleMessageHistory.hidden = !hasHistory;
  elements.toggleMessageHistory.textContent = state.messageHistoryExpanded ? "Hide past messages" : "Show past messages";
  elements.messageHistorySection.hidden = !showHistory;
  elements.messageHistorySection.classList.toggle("hidden", !showHistory);
  elements.clearTextInput.disabled = elements.textInput.value.length === 0;
}

function renderMessageHistory() {
  elements.messageHistory.innerHTML = "";
  const visibleMessages = state.messageHistory.slice(0, MAX_VISIBLE_MESSAGE_HISTORY);
  if (!visibleMessages.length) {
    syncMessageHistoryVisibility();
    return;
  }

  for (const message of visibleMessages) {
    const item = document.createElement("div");
    item.className = "message-history-item";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.textContent = message;
    item.addEventListener("click", () => recallMessage(message));
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        recallMessage(message);
      }
    });
    elements.messageHistory.append(item);
  }
  syncMessageHistoryVisibility();
}

function rememberSentMessage(message) {
  const trimmed = message.trim();
  if (!trimmed) {
    return;
  }

  state.messageHistory.unshift(message);
  if (state.messageHistory.length > MAX_MESSAGE_HISTORY) {
    state.messageHistory.length = MAX_MESSAGE_HISTORY;
  }
  window.localStorage.setItem(MESSAGE_HISTORY_STORAGE_KEY, JSON.stringify(state.messageHistory));
  renderMessageHistory();
}

function loadMessageComposerState() {
  try {
    const storedHistory = JSON.parse(window.localStorage.getItem(MESSAGE_HISTORY_STORAGE_KEY) || "[]");
    if (Array.isArray(storedHistory)) {
      state.messageHistory = storedHistory.filter((entry) => typeof entry === "string" && entry.trim()).slice(0, MAX_MESSAGE_HISTORY);
    }
  } catch {
    state.messageHistory = [];
  }
  elements.textInput.value = window.localStorage.getItem(MESSAGE_DRAFT_STORAGE_KEY) || "";
  autoResizeTextInput();
  renderMessageHistory();
}

function normalizePairingDeviceName(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80);
}

function getUrlPairingDeviceName() {
  try {
    const params = new URLSearchParams(window.location.search);
    return normalizePairingDeviceName(params.get("device") || params.get("device_name"));
  } catch {
    return "";
  }
}

function guessPairingDeviceName() {
  const urlName = getUrlPairingDeviceName();
  if (urlName) {
    return urlName;
  }

  const storedName = window.localStorage.getItem(PAIRING_DEVICE_NAME_STORAGE_KEY);
  if (storedName && storedName.trim()) {
    return normalizePairingDeviceName(storedName);
  }

  const userAgent = navigator.userAgent || "";
  if (/iphone/i.test(userAgent)) {
    return "iPhone";
  }
  if (/ipad/i.test(userAgent)) {
    return "iPad";
  }
  if (/android/i.test(userAgent)) {
    return "Android phone";
  }
  return "This phone";
}

function syncPairingDeviceNameInput() {
  const deviceName = normalizePairingDeviceName(elements.pairingDeviceName?.value) || state.pairingDeviceName || guessPairingDeviceName();
  state.pairingDeviceName = deviceName;
  if (elements.pairingDeviceName && elements.pairingDeviceName.value !== deviceName) {
    elements.pairingDeviceName.value = deviceName;
  }
  return deviceName;
}

function getPairingDeviceName() {
  const deviceName = syncPairingDeviceNameInput();
  window.localStorage.setItem(PAIRING_DEVICE_NAME_STORAGE_KEY, deviceName);
  return deviceName;
}

const CONNECT_INFO_POLL_INTERVAL_MS = 1500;
const CONNECT_INFO_POLL_MAX_ATTEMPTS = 30;
const PAIRING_POLL_INTERVAL_MS = 1500;
const PAIRING_POLL_MAX_ATTEMPTS = 200;

function setConnectStatus(message) {
  elements.connectStatus.textContent = message || "Confirm the session code matches your PC, then tap Connect.";
}

function applyInjectedConnectCode() {
  const injectedCode = window.__PC_PHONE_LINK_CONNECT_CODE__;
  if (typeof injectedCode === "string" && injectedCode.trim()) {
    state.connectCode = injectedCode.trim();
    syncConnectControls();
    return true;
  }
  return false;
}

function stopConnectInfoPolling() {
  if (state.connectInfoPollTimer) {
    window.clearInterval(state.connectInfoPollTimer);
    state.connectInfoPollTimer = null;
  }
  state.connectInfoPollAttempts = 0;
}

function startConnectInfoPolling() {
  stopConnectInfoPolling();
  if (!elements.authPanel || elements.authPanel.classList.contains("hidden")) {
    return;
  }

  state.connectInfoPollTimer = window.setInterval(() => {
    if (!elements.authPanel || elements.authPanel.classList.contains("hidden")) {
      stopConnectInfoPolling();
      return;
    }

    state.connectInfoPollAttempts += 1;
    loadConnectInfo({ quiet: true }).then((loaded) => {
      if (loaded) {
        setConnectStatus("Confirm the session code matches your PC, then tap Connect.");
        stopConnectInfoPolling();
        return;
      }
      if (state.connectInfoPollAttempts >= CONNECT_INFO_POLL_MAX_ATTEMPTS) {
        stopConnectInfoPolling();
        setConnectStatus("Could not load the connect code. Refresh this page and try again.");
      }
    });
  }, CONNECT_INFO_POLL_INTERVAL_MS);
}

function syncConnectControls() {
  const code = state.connectCode || "----";
  const approvalCode = state.pairingApprovalCode || "";
  if (elements.connectCodeDisplay) {
    elements.connectCodeDisplay.textContent = code;
  }
  if (elements.pairingApprovalCodeBlock) {
    elements.pairingApprovalCodeBlock.hidden = !approvalCode;
  }
  if (elements.pairingApprovalCodeDisplay) {
    elements.pairingApprovalCodeDisplay.textContent = approvalCode || "----";
  }
  if (elements.connectButton) {
    elements.connectButton.disabled = state.connectInFlight || !state.connectCode;
    elements.connectButton.textContent = state.connectInFlight ? "Connecting..." : `Connect · ${code}`;
  }
}

async function loadConnectInfo({ quiet = false } = {}) {
  try {
    const response = await fetch("/api/connect-info");
    if (!response.ok) {
      throw new Error("Could not load the connect code from this PC.");
    }
    const payload = await response.json();
    state.connectCode = payload.connect_code || null;
    syncConnectControls();
    return Boolean(state.connectCode);
  } catch (error) {
    if (!quiet) {
      setConnectStatus(error.message || "Could not load the connect code from this PC.");
    }
    syncConnectControls();
    return false;
  }
}

async function finishPairing(accessToken) {
  stopConnectInfoPolling();
  stopPairingPolling();
  state.token = accessToken;
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
  elements.authPanel.classList.add("hidden");
  syncConnectControls();
  const connected = await bootstrap({ quiet: true });
  if (!connected) {
    elements.authPanel.classList.remove("hidden");
    beginConnectFlow();
  }
}

function setPairingApprovalCode(approvalCode) {
  state.pairingApprovalCode = String(approvalCode || "").trim();
  syncConnectControls();
}

async function waitForPcApproval(pairingId, deviceName, approvalCode = null) {
  stopPairingPolling();
  setPairingApprovalCode(approvalCode);
  const waitingLabel = deviceName
    ? `Waiting for PC approval of ${deviceName}. Match this access code on the PC.`
    : "Waiting for PC approval. Match this access code on the PC.";
  setConnectStatus(waitingLabel);
  for (let attempt = 0; attempt < PAIRING_POLL_MAX_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => window.setTimeout(resolve, PAIRING_POLL_INTERVAL_MS));
    const response = await fetch(`/api/pairing/${encodeURIComponent(pairingId)}`);
    if (response.status === 404) {
      throw new Error("That connection request expired. Try again.");
    }
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, "Connection failed."));
    }
    const payload = await response.json();
    if (payload.approval_code) {
      setPairingApprovalCode(payload.approval_code);
    }
    if (payload.status === "approved" && payload.access_token) {
      return payload.access_token;
    }
    if (payload.status === "expired") {
      throw new Error(payload.message || "That connection request expired. Try again.");
    }
    if (payload.message) {
      setConnectStatus(payload.message);
    }
  }
  throw new Error("Timed out waiting for PC approval. Ask the PC owner to approve your device and try again.");
}

function stopPairingPolling() {
  if (state.pairingPollTimer) {
    window.clearInterval(state.pairingPollTimer);
    state.pairingPollTimer = null;
  }
}

async function connectPhone() {
  if (state.connectInFlight) {
    return;
  }

  if (!state.connectCode) {
    showToast("Could not load the connect code from this PC.");
    beginConnectFlow();
    return;
  }

  state.connectInFlight = true;
  state.pairingApprovalCode = null;
  setConnectStatus("Connecting to this PC...");
  syncConnectControls();
  try {
    const deviceName = getPairingDeviceName();
    const response = await fetch("/api/pairing/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        device_name: deviceName,
        connect_code: state.connectCode,
      }),
    });
    if (response.status === 403) {
      throw new Error(await readErrorMessage(response, "Connect code did not match. Check the code on your PC."));
    }
    if (!response.ok) {
      throw new Error(await readErrorMessage(response, "Connection failed."));
    }
    const payload = await response.json();
    if (payload.approval_code) {
      setPairingApprovalCode(payload.approval_code);
    }
    if (payload.access_token) {
      await finishPairing(payload.access_token);
      showToast("Connected to your PC.");
      return;
    }
    if (payload.status === "pending" && payload.pairing_id) {
      const accessToken = await waitForPcApproval(payload.pairing_id, payload.device_name, payload.approval_code);
      await finishPairing(accessToken);
      showToast("Connected to your PC.");
      return;
    }
    throw new Error(payload.message || "Connection failed.");
  } catch (error) {
    setConnectStatus("Confirm the session code matches your PC, then tap Connect.");
    showToast(error.message || "Connection failed.");
    beginConnectFlow();
  } finally {
    state.connectInFlight = false;
    syncConnectControls();
  }
}

function beginConnectFlow({ statusMessage = null } = {}) {
  applyInjectedConnectCode();
  state.pairingApprovalCode = null;
  syncPairingDeviceNameInput();
  if (statusMessage) {
    setConnectStatus(statusMessage);
  } else if (!state.connectCode) {
    setConnectStatus("Loading connect code from your PC...");
  } else {
    setConnectStatus("Confirm the session code matches your PC, then tap Connect.");
  }
  void loadConnectInfo({ quiet: !state.connectCode });
  startConnectInfoPolling();
}

function isAuthRequiredError(error) {
  return Boolean(error?.authRequired || error?.name === "AuthRequiredError");
}

function clearAuthRequiredVerification() {
  if (state.authRequiredTimer) {
    window.clearTimeout(state.authRequiredTimer);
    state.authRequiredTimer = null;
  }
}

function showAuthRequiredScreen(message = AUTH_REQUIRED_MESSAGE) {
  clearAuthRequiredVerification();
  state.token = null;
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  elements.authPanel.classList.remove("hidden");
  beginConnectFlow({ statusMessage: message });
}

async function confirmStoredTokenRejected() {
  const token = state.token || window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (!token) {
    return true;
  }

  try {
    const response = await fetch("/api/info", {
      cache: "no-store",
      headers: { "X-Access-Token": token },
    });
    if (response.status === 401) {
      return true;
    }
    if (response.ok) {
      elements.authPanel.classList.add("hidden");
      return false;
    }
  } catch {
    return false;
  }

  return false;
}

function scheduleAuthRequiredVerification(message = AUTH_REQUIRED_MESSAGE, delay = AUTH_REQUIRED_RECHECK_DELAY_MS) {
  if (state.authRequiredTimer || !state.token) {
    return;
  }

  state.authRequiredTimer = window.setTimeout(async () => {
    state.authRequiredTimer = null;
    if (await confirmStoredTokenRejected()) {
      showAuthRequiredScreen(message);
    }
  }, delay);
}

function loadSavedToken() {
  const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (!token) {
    elements.authPanel.classList.remove("hidden");
    beginConnectFlow();
    return;
  }

  state.token = token;
  elements.authPanel.classList.add("hidden");
  bootstrap();
}

function clearHostReconnectPolling() {
  if (state.hostReconnectTimer) {
    window.clearTimeout(state.hostReconnectTimer);
    state.hostReconnectTimer = null;
  }
  state.hostReconnectAttempts = 0;
}

function scheduleHostReconnect() {
  if (state.hostReconnectTimer || !state.token) return;
  const delay = Math.min(1000 * (2 ** state.hostReconnectAttempts), 10000);
  setConnectionStatus("Reconnecting", false);
  state.hostReconnectTimer = window.setTimeout(async () => {
    state.hostReconnectTimer = null;
    state.hostReconnectAttempts += 1;
    await bootstrap({ quiet: true });
  }, delay);
}

async function bootstrap({ quiet = false } = {}) {
  setConnectionStatus("Connecting", false);
  try {
    const info = await apiFetch("/api/info");
    if (elements.gestureLogPath && info.gesture_log_path) elements.gestureLogPath.textContent = info.gesture_log_path;
    if (!window.localStorage.getItem(STREAM_FPS_STORAGE_KEY)) {
      state.streamFps = clampStreamFps(info.default_fps || state.streamFps);
      syncStreamFpsControl();
    }
    if (typeof info.text_scale === "number" && Number.isFinite(info.text_scale)) {
      setTextScaleValue(info.text_scale, { confirmed: true });
    }
    elements.authPanel.classList.add("hidden");
    await refreshWindows();
    await maybeSelectDefaultDesktopCapture();
    void refreshTrustedDevices({ quiet: true });
    scheduleWindowRefresh();
    clearHostReconnectPolling();
    clearAuthRequiredVerification();
    setConnectionStatus("Connected", true);
    logGestureDiagnostic("connection-state", { state: "connected", reason: quiet ? "reconnect" : "bootstrap" }, { immediate: true });
    return true;
  } catch (error) {
    if (isAuthRequiredError(error)) {
      scheduleAuthRequiredVerification(error.message || AUTH_REQUIRED_MESSAGE, 0);
    }
    if (!quiet && !isAuthRequiredError(error)) {
      showToast(error.message || "Connection failed.");
    }
    setConnectionStatus("Offline", false);
    logGestureDiagnostic("connection-state", { state: "offline", reason: isAuthRequiredError(error) ? "authentication" : "network" });
    if (!isAuthRequiredError(error)) scheduleHostReconnect();
    return false;
  }
}

function setConnectionStatus(label, connected) {
  if (!elements.connectionStatus) return;
  elements.connectionStatus.textContent = label;
  elements.connectionStatus.classList.toggle("connected", Boolean(connected));
}

function formatTrustedDeviceTime(value) {
  if (!value) {
    return "Never";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderTrustedDevices() {
  if (!elements.trustedDevices || !elements.trustedDevicesStatus) {
    return;
  }

  elements.trustedDevices.innerHTML = "";
  if (state.trustedDevicesLoading) {
    elements.trustedDevicesStatus.textContent = "Loading saved phones.";
    return;
  }

  if (!state.token) {
    elements.trustedDevicesStatus.textContent = "Pair this phone to load saved phones.";
    return;
  }

  if (!state.trustedDevices.length) {
    elements.trustedDevicesStatus.textContent = "No saved phones found.";
    return;
  }

  elements.trustedDevicesStatus.textContent = `${state.trustedDevices.length} saved phone${state.trustedDevices.length === 1 ? "" : "s"}.`;

  for (const device of state.trustedDevices) {
    const card = document.createElement("article");
    card.className = "trusted-device-card";
    if (device.is_current) {
      card.classList.add("current");
    }

    const title = document.createElement("div");
    title.className = "trusted-device-title";
    const name = document.createElement("strong");
    name.textContent = device.device_name || "This phone";
    title.append(name);
    if (device.is_current) {
      const current = document.createElement("span");
      current.textContent = "Current";
      title.append(current);
    }
    card.append(title);

    const meta = document.createElement("p");
    meta.className = "trusted-device-meta";
    meta.textContent = `Approved ${formatTrustedDeviceTime(device.approved_at)}. Last seen ${formatTrustedDeviceTime(device.last_seen_at)}.`;
    card.append(meta);

    const revokeButton = document.createElement("button");
    revokeButton.type = "button";
    revokeButton.className = "ghost-button";
    revokeButton.textContent = device.is_current ? "Delete this phone" : "Delete";
    revokeButton.addEventListener("click", () => deleteTrustedDevice(device));
    card.append(revokeButton);

    elements.trustedDevices.append(card);
  }
}

async function refreshTrustedDevices({ quiet = false } = {}) {
  if (!state.token) {
    state.trustedDevices = [];
    renderTrustedDevices();
    return;
  }

  state.trustedDevicesLoading = true;
  renderTrustedDevices();
  try {
    const response = await apiFetch("/api/trusted-devices");
    state.trustedDevices = Array.isArray(response.devices) ? response.devices : [];
  } catch (error) {
    if (!quiet) {
      showToast(error.message || "Saved phones could not load.");
    }
  } finally {
    state.trustedDevicesLoading = false;
    renderTrustedDevices();
  }
}

async function deleteTrustedDevice(device) {
  if (!device?.id) {
    return;
  }

  const prompt = device.is_current
    ? "Delete this saved phone connection? You will need to pair again."
    : `Delete ${device.device_name || "this phone"} from saved phones?`;
  if (!window.confirm(prompt)) {
    return;
  }

  const response = await apiFetch(`/api/trusted-devices/${encodeURIComponent(device.id)}`, {
    method: "DELETE",
  });
  if (response.revoked_current) {
    state.token = null;
    state.selectedWindow = null;
    state.windows = [];
    state.phoneFitEnabled = false;
    state.trustedDevices = [];
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    elements.authPanel.classList.remove("hidden");
    beginConnectFlow({
      statusMessage: "That saved connection was deleted. Connect this phone again.",
    });
    renderTrustedDevices();
    resetViewer();
    return;
  }

  await refreshTrustedDevices({ quiet: true });
  showToast("Saved phone deleted.");
}

function scheduleWindowRefresh() {
  if (state.windowsRefreshTimer) {
    window.clearInterval(state.windowsRefreshTimer);
  }
  state.windowsRefreshTimer = window.setInterval(() => {
    refreshWindows().catch(() => null);
  }, 5000);
}

async function apiFetch(path, options = {}) {
  const fetchOptions = { ...options };
  const retryAuth = fetchOptions.retryAuth !== false;
  delete fetchOptions.retryAuth;

  const headers = new Headers(fetchOptions.headers || {});
  headers.set("X-Access-Token", state.token || "");
  if (fetchOptions.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...fetchOptions,
    headers,
  });

  if (response.status === 401) {
    const message = await readErrorMessage(response, AUTH_REQUIRED_MESSAGE);
    if (retryAuth && state.token && !(await confirmStoredTokenRejected())) {
      return apiFetch(path, { ...options, retryAuth: false });
    }
    scheduleAuthRequiredVerification(message, 0);
    throw new AuthRequiredError(message);
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "Request failed."));
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

async function readErrorMessage(response, fallback = "Request failed.") {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const payload = await response.json();
      if (payload?.detail) {
        return payload.detail;
      }
      if (payload?.message) {
        return payload.message;
      }
    } catch {
      return response.statusText || fallback;
    }
  }

  try {
    const body = await response.text();
    if (body) {
      return body;
    }
  } catch {
    return response.statusText || fallback;
  }

  return response.statusText || fallback;
}

function queueControl(requestFactory) {
  state.controlQueue = state.controlQueue
    .catch(() => null)
    .then(() => requestFactory());
  return state.controlQueue;
}

function queueJsonPost(path, payload) {
  return queueControl(() => apiFetch(path, {
    method: "POST",
    body: JSON.stringify(payload),
  }));
}

function handlePointerResponse(response, action = "") {
  if (response?.cursor) {
    updateCursorPosition(response.cursor, { allowMouseFollow: action === "move_relative" });
    if (action === "click_current") {
      setTypingAnchorFromCursor(response.cursor);
    }
  }
  return response;
}

function updateSelectedWindow(windowInfo) {
  if (!windowInfo) {
    return;
  }

  if (!state.selectedWindow || state.selectedWindow.hwnd !== windowInfo.hwnd) {
    cancelPendingTap("selected-window-change");
    state.typingAnchor = null;
  }
  state.selectedWindow = windowInfo;
  state.phoneFitEnabled = Boolean(windowInfo.is_phone_fit);
  if (windowInfo.cursor) {
    updateCursorPosition(windowInfo.cursor);
  }
  syncPhoneFitButton();
  syncTargetActionButtons();
  syncControlMode();
  renderWindowList();
  applyCameraTransform();
}

function syncPhoneFitButton() {
  elements.fitToggle.classList.toggle("mode-active", state.phoneFitEnabled);
  elements.fitToggle.textContent = state.phoneFitEnabled ? "Maximize" : "Fit";
  elements.viewerShell.classList.toggle("phone-fit-active", state.phoneFitEnabled);
  renderBottomNav();
}

function syncTargetActionButtons() {
  const hasTarget = Boolean(state.selectedWindow);
  const isDesktopCapture = Boolean(state.selectedWindow?.is_desktop_capture);
  const windowOnlyDisabled = !hasTarget || isDesktopCapture;
  elements.fitToggle.disabled = windowOnlyDisabled;
  if (elements.toggleKeyboard) {
    elements.toggleKeyboard.disabled = !hasTarget;
  }
  syncFitShapeControls();
}

async function refreshWindows() {
  const data = await apiFetch("/api/windows");
  state.windows = data.windows || [];
  renderWindowList();

  if (!state.selectedWindow) {
    return;
  }

  const updated = state.windows.find((entry) => entry.hwnd === state.selectedWindow.hwnd);
  if (!updated) {
    state.selectedWindow = null;
    state.phoneFitEnabled = false;
    resetViewer();
    showToast("That app closed. Open Windows to move to something else.");
    return;
  }

  updateSelectedWindow(updated);
}

function renderWindowList() {
  elements.windowList.innerHTML = "";

  if (!state.windows.length) {
    const empty = document.createElement("p");
    empty.className = "eyebrow";
    empty.textContent = "No switchable windows were found.";
    elements.windowList.append(empty);
    return;
  }

  const recentIndex = (windowInfo) => state.recentWindowKeys.indexOf(getWindowRecentKey(windowInfo));
  const orderedWindows = [...state.windows].sort((first, second) => {
    const firstIndex = recentIndex(first);
    const secondIndex = recentIndex(second);
    if (firstIndex < 0 && secondIndex < 0) return 0;
    if (firstIndex < 0) return 1;
    if (secondIndex < 0) return -1;
    return firstIndex - secondIndex;
  });

  for (const windowInfo of orderedWindows) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "window-card";
    if (state.selectedWindow && state.selectedWindow.hwnd === windowInfo.hwnd) {
      button.classList.add("active");
    }

    const title = document.createElement("strong");
    title.textContent = windowInfo.title;
    button.append(title);

    const subtitle = document.createElement("span");
    const processName = windowInfo.process_name || "App";
    const markers = [];
    if (windowInfo.is_foreground) {
      markers.push("focused");
    }
    if (windowInfo.is_minimized) {
      markers.push("minimized");
    }
    if (recentIndex(windowInfo) >= 0) {
      markers.push("recent");
    }
    subtitle.textContent = markers.length ? `${processName} - ${markers.join(" - ")}` : processName;
    button.append(subtitle);

    button.addEventListener("click", () => {
      selectWindow(windowInfo).catch((error) => showToast(error.message));
    });

    elements.windowList.append(button);
  }
}

function getWindowRecentKey(windowInfo) {
  if (windowInfo.is_desktop_capture) return "desktop";
  return String(windowInfo.process_name || "app").trim().toLowerCase();
}

function rememberRecentWindow(windowInfo) {
  const key = getWindowRecentKey(windowInfo);
  state.recentWindowKeys = [key, ...state.recentWindowKeys.filter((entry) => entry !== key)].slice(0, 4);
  window.localStorage.setItem(RECENT_WINDOWS_STORAGE_KEY, JSON.stringify(state.recentWindowKeys));
}

async function selectWindow(windowInfo) {
  state.streamSocketFailures = 0;
  const response = await apiFetch(`/api/windows/${windowInfo.hwnd}/activate`, {
    method: "POST",
    body: JSON.stringify({ maximize: false }),
  });
  rememberRecentWindow(windowInfo);
  updateSelectedWindow(response.window || windowInfo);
  elements.emptyState.hidden = true;
  elements.remoteView.style.display = "block";
  refreshStream();
  openDestination("viewer");
  closeDrawerOnSmallScreens();
}

function getStreamRequestWidth() {
  if (state.streamWidth !== "auto") {
    return Math.min(Math.max(state.streamWidth, 360), MAX_STREAM_REQUEST_WIDTH);
  }
  const viewerRect = elements.viewerShell.getBoundingClientRect();
  const displayed = getDisplayedImageRect();
  const devicePixelRatio = Math.min(Math.max(window.devicePixelRatio || 1, 1), MAX_STREAM_DEVICE_PIXEL_RATIO);
  const zoomScale = Math.max(state.cameraScale || 1, 1);
  const visibleWidth = Math.max(displayed.width || 0, viewerRect.width || 0, 1);
  const requestedWidth = Math.round(visibleWidth * devicePixelRatio * zoomScale);
  const clampedWidth = Math.min(Math.max(requestedWidth, 360), MAX_STREAM_REQUEST_WIDTH);
  const quantizedWidth = Math.round(clampedWidth / STREAM_WIDTH_QUANTUM) * STREAM_WIDTH_QUANTUM;
  return Math.min(Math.max(quantizedWidth, 360), MAX_STREAM_REQUEST_WIDTH);
}

function scheduleStreamRefresh(delay = STREAM_REFRESH_DEBOUNCE_MS) {
  if (!state.selectedWindow) {
    return;
  }

  if (state.streamRefreshTimer) {
    window.clearTimeout(state.streamRefreshTimer);
  }
  state.streamRefreshTimer = window.setTimeout(() => {
    state.streamRefreshTimer = null;
    refreshStream();
  }, delay);
}

function getStreamParams() {
  return {
    hwnd: state.selectedWindow.hwnd,
    width: getStreamRequestWidth(),
    fps: clampStreamFps(state.streamFps),
  };
}

function streamParamsEqual(a, b) {
  return Boolean(a && b) && a.hwnd === b.hwnd && a.width === b.width && a.fps === b.fps;
}

function releaseStreamObjectUrl() {
  if (state.streamObjectUrl) {
    URL.revokeObjectURL(state.streamObjectUrl);
    state.streamObjectUrl = null;
  }
}

function revokeStreamObjectUrlAfterPaint(objectUrl) {
  if (!objectUrl) {
    return;
  }
  window.requestAnimationFrame(() => URL.revokeObjectURL(objectUrl));
}

function acknowledgeStreamFrame(socket, generation) {
  if (state.streamGeneration === generation && socket.readyState === WebSocket.OPEN) {
    socket.send("r");
  }
}

function closeStreamSocket() {
  state.streamGeneration += 1;
  const socket = state.streamSocket;
  state.streamSocket = null;
  if (!socket) {
    return;
  }
  socket.onopen = null;
  socket.onmessage = null;
  socket.onerror = null;
  socket.onclose = null;
  try {
    socket.close();
  } catch {
    // Sockets that never finished connecting can throw on close; ignore.
  }
}

function refreshStream() {
  if (!state.selectedWindow) {
    return;
  }

  if (state.streamRefreshTimer) {
    window.clearTimeout(state.streamRefreshTimer);
    state.streamRefreshTimer = null;
  }

  const params = getStreamParams();
  const socketAlive = state.streamSocket
    && (state.streamSocket.readyState === WebSocket.OPEN
      || state.streamSocket.readyState === WebSocket.CONNECTING);
  if (streamParamsEqual(state.streamParams, params) && (socketAlive || state.streamFallbackActive)) {
    applyCameraTransform();
    return;
  }

  state.streamParams = params;
  closeStreamSocket();
  if (state.streamSocketFailures >= STREAM_SOCKET_MAX_FAILURES) {
    startMjpegFallback(params);
    return;
  }
  openStreamSocket(params);
  applyCameraTransform();
}

function openStreamSocket(params) {
  const generation = state.streamGeneration;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socketUrl = `${protocol}://${window.location.host}/ws/stream`
    + `?token=${encodeURIComponent(state.token || "")}`
    + `&hwnd=${params.hwnd}&width=${params.width}&fps=${params.fps}`;

  let socket;
  try {
    socket = new WebSocket(socketUrl);
  } catch {
    state.streamSocketFailures += 1;
    startMjpegFallback(params);
    return;
  }

  socket.binaryType = "blob";
  state.streamSocket = socket;
  state.streamFallbackActive = false;
  let receivedFrame = false;

  socket.onmessage = (event) => {
    if (state.streamGeneration !== generation || !(event.data instanceof Blob)) {
      return;
    }
    if (!receivedFrame) {
      receivedFrame = true;
      state.streamSocketFailures = 0;
    }
    renderSocketFrame(event.data, socket, generation);
  };

  socket.onclose = () => {
    if (state.streamGeneration !== generation) {
      return;
    }
    state.streamSocket = null;
    if (!receivedFrame) {
      // The socket never delivered a frame: fall back to MJPEG right away.
      state.streamSocketFailures += 1;
      startMjpegFallback(params);
      return;
    }
    scheduleStreamRefresh(STREAM_RECONNECT_DELAY_MS);
  };
}

async function renderSocketFrame(frameBlob, socket, generation) {
  const objectUrl = URL.createObjectURL(frameBlob);
  const image = new Image();
  image.decoding = "async";
  const imageLoaded = new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = reject;
  });
  image.src = objectUrl;

  try {
    if (typeof image.decode === "function") {
      await image.decode();
    } else {
      await imageLoaded;
    }
  } catch {
    URL.revokeObjectURL(objectUrl);
    acknowledgeStreamFrame(socket, generation);
    return;
  }

  if (state.streamGeneration !== generation || socket.readyState !== WebSocket.OPEN) {
    URL.revokeObjectURL(objectUrl);
    return;
  }

  const previousUrl = state.streamObjectUrl;
  state.streamObjectUrl = objectUrl;
  elements.remoteView.src = objectUrl;
  if (previousUrl) {
    revokeStreamObjectUrlAfterPaint(previousUrl);
  }
  // Acknowledge only after the frame is decoded so the host adapts its pace
  // to what this phone can actually display, instead of queueing stale frames.
  acknowledgeStreamFrame(socket, generation);
}

function startMjpegFallback(params) {
  if (!state.selectedWindow) {
    return;
  }
  state.streamFallbackActive = true;
  releaseStreamObjectUrl();
  const streamUrl = `/api/windows/${params.hwnd}/stream?token=${encodeURIComponent(state.token)}`
    + `&width=${params.width}&fps=${params.fps}&t=${Date.now()}`;
  elements.remoteView.src = streamUrl;
  applyCameraTransform();
}

function resetViewer() {
  cancelPendingTap("viewer-reset");
  if (state.pointerDown || state.activePointers.size) releaseActiveTouches();
  closeStreamSocket();
  releaseStreamObjectUrl();
  state.streamParams = null;
  state.streamFallbackActive = false;
  elements.remoteView.removeAttribute("src");
  elements.remoteView.style.display = "none";
  elements.emptyState.hidden = false;
  state.typingAnchor = null;
  if (state.streamRefreshTimer) {
    window.clearTimeout(state.streamRefreshTimer);
    state.streamRefreshTimer = null;
  }
  closeKeyboardCapture();
  syncPhoneFitButton();
  syncTargetActionButtons();
  applyCameraTransform();
}

function closeDrawerOnSmallScreens() {
  if (usesMobileShell()) {
    elements.windowDrawer.classList.remove("open");
  }
}

function syncControlsVisibility() {
  elements.app.classList.toggle("controls-hidden", state.controlsHidden);
  elements.revealControls?.classList.toggle("hidden", !state.controlsHidden);
  if (elements.toggleControls) {
    elements.toggleControls.textContent = state.controlsHidden ? "Show controls" : "Hide controls";
    elements.toggleControls.setAttribute("aria-pressed", String(state.controlsHidden));
  }
}

function setControlsHidden(hidden) {
  state.controlsHidden = Boolean(hidden);
  if (state.controlsHidden) {
    togglePowerMenu(false);
    elements.windowDrawer.classList.remove("open");
  }
  syncControlsVisibility();
  applyCameraTransform();
  scheduleStreamRefresh();
}

function toggleControls() {
  setControlsHidden(!state.controlsHidden);
}

function setTapMode(mode) {
  if (mode !== "left") cancelPendingTap("explicit-tap-mode");
  state.tapMode = mode;
  if (elements.rightClickMode) {
    elements.rightClickMode.classList.toggle("mode-active", mode === "right");
  }
  if (elements.doubleClickMode) {
    elements.doubleClickMode.classList.toggle("mode-active", mode === "double");
  }
  renderBottomNav();
}

function openKeyboardCapture({ focusInput = true } = {}) {
  if (!elements.keyboardPanel.classList.contains("hidden")) {
    if (focusInput) {
      elements.textInput.focus();
    }
    return;
  }
  elements.keyboardPanel.classList.remove("hidden");
  if (elements.controlBar) {
    elements.controlBar.hidden = true;
  }
  elements.app.classList.add("composer-open");
  state.messageHistoryExpanded = false;
  syncMessageHistoryVisibility();
  syncVoiceInputButton();
  if (state.followTyping && state.selectedWindow) {
    ensureFollowTypingZoom("keyboard-open");
    if (!state.typingAnchor) {
      setTypingAnchorFromCursor(state.cursorPosition, "keyboard-open");
    } else {
      syncCameraToTypingAnchor();
    }
    queueFollowTypingLog("keyboard-open", buildFollowTypingLogDetails(), { immediate: true });
  }
  autoResizeTextInput();
  if (focusInput) {
    elements.textInput.focus();
  }
}

function closeKeyboardCapture({ blurInput = true } = {}) {
  if (elements.keyboardPanel.classList.contains("hidden")) {
    return;
  }
  if (state.voiceListening && state.voiceRecognition) {
    state.voiceRecognition.stop();
  }
  elements.keyboardPanel.classList.add("hidden");
  if (elements.controlBar) {
    elements.controlBar.hidden = false;
  }
  elements.app.classList.remove("composer-open");
  state.keyboardComposerRequested = false;
  state.messageHistoryExpanded = false;
  syncMessageHistoryVisibility();
  syncVoiceInputButton();
  if (blurInput) {
    elements.textInput.blur();
  }
  if (state.followTyping) {
    queueFollowTypingLog("keyboard-close", buildFollowTypingLogDetails(), { immediate: true });
  }
  state.typingAnchor = null;
}

function toggleKeyboardPanel() {
  if (!elements.keyboardPanel.classList.contains("hidden")) {
    closeKeyboardCapture();
    return;
  }
  state.keyboardComposerRequested = true;
  holdKeyboardCapture(2000);
  openKeyboardCapture();
}

function holdKeyboardCapture(duration = 700) {
  state.keyboardPanelHoldUntil = Math.max(state.keyboardPanelHoldUntil, Date.now() + duration);
}

function refocusComposerInput() {
  if (elements.keyboardPanel.classList.contains("hidden")) {
    return;
  }
  elements.textInput.focus({ preventScroll: true });
}

function isPhoneKeyboardVisible() {
  const { width, height } = getViewportSize();
  const orientation = width >= height ? "landscape" : "portrait";
  if (state.keyboardViewportOrientation !== orientation) {
    state.keyboardViewportOrientation = orientation;
    state.keyboardViewportMaxHeight = height;
  } else {
    state.keyboardViewportMaxHeight = Math.max(state.keyboardViewportMaxHeight || 0, height);
  }

  const baselineHeight = state.keyboardViewportMaxHeight || height;
  const heightDelta = Math.max(baselineHeight - height, 0);
  return heightDelta >= Math.max(KEYBOARD_VISIBLE_HEIGHT_DELTA, Math.round(baselineHeight * KEYBOARD_VISIBLE_HEIGHT_RATIO));
}

function syncKeyboardComposerVisibility() {
  const keyboardVisible = isPhoneKeyboardVisible();
  const activeElement = document.activeElement;
  const inputFocused = activeElement === elements.textInput;
  const panelInteractionActive = Boolean(activeElement && elements.keyboardPanel.contains(activeElement));
  const keyboardHoldActive = Date.now() < state.keyboardPanelHoldUntil;
  const keepComposerOpen = state.keyboardComposerRequested && (
    keyboardVisible
    || inputFocused
    || panelInteractionActive
    || keyboardHoldActive
    || state.voiceListening
    || state.messageHistoryExpanded
  );
  if (keepComposerOpen) {
    openKeyboardCapture({ focusInput: false });
  }
}

function scheduleKeyboardComposerSync(delay = 120) {
  window.clearTimeout(state.keyboardVisibilityTimer);
  state.keyboardVisibilityTimer = window.setTimeout(() => {
    syncKeyboardComposerVisibility();
  }, delay);
}

function toggleMessageHistoryPanel() {
  if (!state.messageHistory.length) {
    return;
  }
  holdKeyboardCapture();
  state.keyboardComposerRequested = true;
  state.messageHistoryExpanded = !state.messageHistoryExpanded;
  syncMessageHistoryVisibility();
  refocusComposerInput();
}

function composeVoiceTranscript(baseText, transcript) {
  const normalizedTranscript = String(transcript || "").trim();
  if (!normalizedTranscript) {
    return baseText;
  }
  if (!baseText) {
    return normalizedTranscript;
  }
  return /\s$/.test(baseText) ? `${baseText}${normalizedTranscript}` : `${baseText} ${normalizedTranscript}`;
}

function syncVoiceInputButton() {
  if (!elements.voiceInput) {
    return;
  }
  const active = state.voiceListening || state.voiceStarting;
  elements.voiceInput.textContent = state.voiceListening ? "Stop" : state.voiceStarting ? "Starting" : "Voice";
  elements.voiceInput.classList.toggle("voice-active", active);
  elements.voiceInput.setAttribute("aria-pressed", active ? "true" : "false");
  elements.voiceInput.disabled = state.voiceStarting;
}

async function queryMicrophonePermissionState() {
  if (!navigator.permissions?.query) {
    return null;
  }
  try {
    const permission = await navigator.permissions.query({ name: "microphone" });
    return permission?.state || null;
  } catch {
    return null;
  }
}

function stopMediaStream(stream) {
  if (!stream) {
    return;
  }
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

async function ensureVoicePermission() {
  const permissionState = await queryMicrophonePermissionState();
  if (permissionState === "denied") {
    return {
      ok: false,
      message: "Microphone permission is denied for this site. Allow microphone in your phone browser site settings, then refresh.",
    };
  }

  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    return { ok: true };
  }

  let stream = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    return { ok: true };
  } catch (error) {
    if (error?.name === "NotAllowedError") {
      return {
        ok: false,
        message: permissionState === "denied"
          ? "Microphone permission is denied for this site. Allow microphone in your phone browser site settings, then refresh."
          : "Microphone access was blocked. Allow microphone for this page in your phone browser, then try again.",
      };
    }
    if (error?.name === "NotFoundError") {
      return {
        ok: false,
        message: "No microphone was available on this phone.",
      };
    }
    if (error?.name === "NotReadableError") {
      return {
        ok: false,
        message: "The microphone is busy in another app right now.",
      };
    }
    if (error?.name === "SecurityError") {
      return {
        ok: false,
        message: "This phone browser blocked microphone access for this page.",
      };
    }
    return {
      ok: false,
      message: "Voice input could not access the microphone.",
    };
  } finally {
    stopMediaStream(stream);
  }
}

function ensureVoiceRecognition() {
  if (state.voiceRecognition) {
    return state.voiceRecognition;
  }

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    return null;
  }

  const recognition = new Recognition();
  recognition.lang = navigator.language || "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    state.voiceStarting = false;
    state.voiceListening = true;
    state.keyboardComposerRequested = true;
    holdKeyboardCapture(12000);
    syncVoiceInputButton();
  };

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results).map((result) => result[0].transcript).join("");
    elements.textInput.value = composeVoiceTranscript(state.voiceBaseText, transcript);
    saveMessageDraft();
    autoResizeTextInput();
    syncMessageHistoryVisibility();
  };

  recognition.onerror = (event) => {
    state.voiceStarting = false;
    state.voiceListening = false;
    syncVoiceInputButton();
    if (event.error === "aborted") {
      return;
    }
    if (event.error === "not-allowed") {
      showToast(
        window.isSecureContext
          ? "Voice input permission was blocked. Allow microphone for this site in your phone browser settings."
          : "This browser blocked web voice input on this page. Try allowing microphone for the site or use your keyboard mic.",
      );
      return;
    }
    if (event.error === "audio-capture") {
      showToast("No microphone was available for voice input.");
      return;
    }
    if (event.error === "no-speech") {
      showToast("No speech was detected.");
      return;
    }
    showToast("Voice input failed.");
  };

  recognition.onend = () => {
    state.voiceStarting = false;
    state.voiceListening = false;
    state.voiceBaseText = elements.textInput.value;
    syncVoiceInputButton();
  };

  state.voiceRecognition = recognition;
  return recognition;
}

async function toggleVoiceInput() {
  state.keyboardComposerRequested = true;
  holdKeyboardCapture(12000);
  openKeyboardCapture({ focusInput: false });
  refocusComposerInput();

  const recognition = ensureVoiceRecognition();
  if (!recognition) {
    showToast("Voice input is not available in this browser.");
    return;
  }

  if (state.voiceListening) {
    recognition.stop();
    return;
  }

  if (state.voiceStarting) {
    return;
  }

  const permissionCheck = await ensureVoicePermission();
  if (!permissionCheck.ok) {
    refocusComposerInput();
    showToast(permissionCheck.message);
    return;
  }

  state.voiceBaseText = elements.textInput.value;
  state.voiceStarting = true;
  syncVoiceInputButton();
  try {
    recognition.start();
  } catch (error) {
    state.voiceStarting = false;
    syncVoiceInputButton();
    if (error?.name === "InvalidStateError") {
      return;
    }
    if (error?.name === "NotAllowedError") {
      showToast(
        window.isSecureContext
          ? "Voice input permission was blocked. Allow microphone for this site in your phone browser settings."
          : "This browser blocked web voice input on this page. Try allowing microphone for the site or use your keyboard mic.",
      );
      return;
    }
    showToast("Voice input could not start.");
  }
}

function showToast(message) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden");
  state.toastTimer = window.setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 2500);
}

function pointerPath() {
  return `/api/windows/${state.selectedWindow.hwnd}/pointer`;
}

function flushPendingMove() {
  if (!state.pendingMovePayload || state.moveRequestInFlight || !state.selectedWindow) {
    return;
  }

  const payload = state.pendingMovePayload;
  state.pendingMovePayload = null;
  state.moveRequestInFlight = true;
  queueJsonPost(pointerPath(), payload)
    .then((response) => handlePointerResponse(response, payload.action))
    .catch((error) => showToast(error.message))
    .finally(() => {
      state.moveRequestInFlight = false;
      if (state.pendingMovePayload) {
        flushPendingMove();
      }
    });
}

function schedulePendingTouchMove() {
  if (state.touchMoveScheduled || !state.pendingTouchMovePayload || !state.selectedWindow) return;
  state.touchMoveScheduled = true;
  queueControl(async () => {
    const payload = state.pendingTouchMovePayload;
    state.pendingTouchMovePayload = null;
    if (!payload || !state.selectedWindow) return null;
    return apiFetch(pointerPath(), { method: "POST", body: JSON.stringify(payload) });
  })
    .catch(handlePointerError)
    .finally(() => {
      state.touchMoveScheduled = false;
      if (state.pendingTouchMovePayload) schedulePendingTouchMove();
    });
}

function sendPointer(action, payload = {}) {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }

  const requestId = diagnosticId("request");
  const requestPayload = {
    action,
    x: Number.isFinite(payload.x) ? payload.x : 0.5,
    y: Number.isFinite(payload.y) ? payload.y : 0.5,
    delta: payload.delta || 0,
    delta_x: payload.deltaX || 0,
    delta_y: payload.deltaY || 0,
    request_id: requestId,
    session_id: state.gestureSessionId,
    gesture_id: payload.gestureId || state.currentGestureId || diagnosticId("gesture"),
    control_mode: state.controlMode,
    pointer_count: state.activePointers.size,
    pointer_type: state.pointerType,
  };
  const outboundNow = Date.now();
  if (action !== "touch_move" || outboundNow - state.lastOutboundMoveLoggedAt >= 120) {
    if (action === "touch_move") state.lastOutboundMoveLoggedAt = outboundNow;
    logGestureDiagnostic("outbound-action", {
      request_id: requestId,
      gesture_id: requestPayload.gesture_id,
      action,
      x: requestPayload.x,
      y: requestPayload.y,
      delta: requestPayload.delta,
      delta_x: requestPayload.delta_x,
      delta_y: requestPayload.delta_y,
      state: "queued",
    });
  }

  if (action === "move_relative") {
    state.pendingMovePayload = requestPayload;
    flushPendingMove();
    return;
  }

  if (action === "touch_move") {
    state.pendingTouchMovePayload = requestPayload;
    schedulePendingTouchMove();
    return;
  }

  if (["touch_up", "touch_cancel"].includes(action) && state.pendingTouchMovePayload) {
    const pendingMove = state.pendingTouchMovePayload;
    state.pendingTouchMovePayload = null;
    queueJsonPost(pointerPath(), pendingMove)
      .then((response) => handlePointerResponse(response, pendingMove.action))
      .catch(handlePointerError);
  }

  queueJsonPost(pointerPath(), requestPayload)
    .then((response) => {
      logGestureDiagnostic("action-result", { request_id: requestId, action, result: "ok" });
      return handlePointerResponse(response, action);
    })
    .catch(handlePointerError);
}

function handlePointerError(error) {
  emergencyTouchCancel("request-error");
  cancelPendingTap("request-error");
  state.pendingTouchMovePayload = null;
  state.activePointers.clear();
  clearTwoFingerHoldTimer();
  state.twoFingerGesture = null;
  resetPrimaryPointerState();
  const detail = error?.message || "Pointer request failed.";
  logGestureDiagnostic("action-result", {
    error_type: error?.name || "Error",
    reason: /native touch|touch input|\[Errno \d+\]/i.test(detail) ? "native-touch" : "request",
    result: "failed",
  }, { immediate: true, force: true });
  const message = /native touch|touch input|\[Errno \d+\]/i.test(detail)
    ? `App touch stopped. Lift all fingers, then retry. ${detail}`
    : detail;
  showToast(message);
}

function getPointerDistance(first, second) {
  return window.PCPhoneLinkGestures.distance(first, second);
}

function getPointerMidpoint(first, second) {
  return window.PCPhoneLinkGestures.midpoint(first, second);
}

function haptic(pattern = 12) {
  if (navigator.vibrate) navigator.vibrate(pattern);
}

function showGestureStatus(label, duration = 700) {
  if (!elements.gestureStatus) return;
  window.clearTimeout(state.gestureStatusTimer);
  elements.gestureStatus.textContent = label;
  elements.gestureStatus.hidden = false;
  state.gestureStatusTimer = window.setTimeout(() => {
    elements.gestureStatus.hidden = true;
  }, duration);
}

function cancelPendingTap(reason) {
  const pending = state.pendingTap;
  if (!pending) return;
  window.clearTimeout(pending.timer);
  state.pendingTap = null;
  logGestureDiagnostic("gesture-state", {
    gesture: "double-tap",
    state: "canceled",
    reason,
  });
}

function dispatchPendingSingleTap(pending, reason) {
  if (state.pendingTap !== pending) return;
  window.clearTimeout(pending.timer);
  state.pendingTap = null;
  if (state.controlMode !== "touch" || state.selectedWindow?.hwnd !== pending.windowHwnd) {
    logGestureDiagnostic("gesture-state", {
      gesture: "double-tap",
      state: "canceled",
      reason: "target-changed",
    });
    return;
  }
  sendPointer("touch_tap", { ...pending.sourcePoint, gestureId: pending.gestureId });
  logGestureDiagnostic("gesture-classified", {
    gesture: "single-tap",
    state: "active",
    reason,
  });
  showGestureStatus("Tap");
}

function queueAppTouchTap(sourcePoint, clientPoint) {
  const now = Date.now();
  const pending = state.pendingTap;
  if (pending) {
    const elapsed = now - pending.completedAt;
    const distance = getPointerDistance(pending.clientPoint, clientPoint);
    if (elapsed <= DOUBLE_TAP_DELAY_MS && distance <= DOUBLE_TAP_DISTANCE_PX
      && pending.windowHwnd === state.selectedWindow?.hwnd) {
      window.clearTimeout(pending.timer);
      state.pendingTap = null;
      sendPointer("touch_hold", sourcePoint);
      logGestureDiagnostic("gesture-classified", {
        gesture: "double-tap-right-click",
        state: "active",
        delta: distance,
      }, { immediate: true });
      haptic([18, 35, 18]);
      showGestureStatus("Right-click");
      return;
    }
    dispatchPendingSingleTap(pending, elapsed > DOUBLE_TAP_DELAY_MS ? "late-second-tap" : "distant-second-tap");
  }

  const next = {
    sourcePoint: { ...sourcePoint },
    clientPoint: { ...clientPoint },
    completedAt: now,
    gestureId: state.currentGestureId,
    windowHwnd: state.selectedWindow?.hwnd,
    timer: null,
  };
  next.timer = window.setTimeout(() => dispatchPendingSingleTap(next, "double-tap-timeout"), DOUBLE_TAP_DELAY_MS);
  state.pendingTap = next;
  logGestureDiagnostic("gesture-state", { gesture: "double-tap", state: "candidate" });
}

function clearTwoFingerHoldTimer(gesture = state.twoFingerGesture) {
  if (gesture?.holdTimer) window.clearTimeout(gesture.holdTimer);
  if (gesture) gesture.holdTimer = null;
}

function scheduleTwoFingerScrollArm(gesture) {
  clearTwoFingerHoldTimer(gesture);
  gesture.holdTimer = window.setTimeout(() => {
    gesture.holdTimer = null;
    if (state.twoFingerGesture !== gesture || gesture.mode || !gesture.holdEligible) return;
    const first = state.activePointers.get(gesture.pointerIds[0]);
    const second = state.activePointers.get(gesture.pointerIds[1]);
    if (!first || !second) return;
    const motion = window.PCPhoneLinkGestures.twoFingerMotion(
      gesture.startA,
      gesture.startB,
      first,
      second,
    );
    if (motion.movementA > TWO_FINGER_HOLD_SLOP || motion.movementB > TWO_FINGER_HOLD_SLOP) {
      gesture.holdEligible = false;
      logGestureDiagnostic("gesture-state", { gesture: "two-finger-scroll", state: "disarmed", reason: "moved-before-hold" });
      return;
    }
    gesture.scrollArmed = true;
    gesture.armA = { ...first };
    gesture.armB = { ...second };
    haptic([12, 24, 12]);
    showGestureStatus("Scroll ready", 900);
    logGestureDiagnostic("gesture-state", { gesture: "two-finger-scroll", state: "armed" }, { immediate: true });
  }, TWO_FINGER_SCROLL_HOLD_MS);
}

function finishTwoFingerGesture({ canceled = false, recognizeTap = false } = {}) {
  const gesture = state.twoFingerGesture;
  let tapRecognized = false;
  clearTwoFingerHoldTimer(gesture);
  if (gesture?.mode === "scroll" && gesture.lastSourcePoint) {
    if (state.controlMode === "touch") sendPointer(canceled ? "touch_cancel" : "touch_up", gesture.lastSourcePoint);
  }
  if (gesture && recognizeTap && !canceled && state.controlMode === "touch"
    && gesture.tapEligible && !gesture.mode && !gesture.scrollArmed
    && Date.now() - gesture.startedAt <= TWO_FINGER_TAP_MAX_MS
    && gesture.maxMovementA <= TWO_FINGER_TAP_SLOP
    && gesture.maxMovementB <= TWO_FINGER_TAP_SLOP) {
    const first = gesture.endA || gesture.startA;
    const second = gesture.endB || gesture.startB;
    const midpoint = getPointerMidpoint(first, second);
    const sourcePoint = viewerPointToSourceNormalized(midpoint.x, midpoint.y);
    if (sourcePoint) {
      sendPointer("touch_double", sourcePoint);
      tapRecognized = true;
      haptic([16, 30, 16]);
      showGestureStatus("Double-click");
      logGestureDiagnostic("gesture-classified", {
        gesture: "two-finger-double-click",
        state: "active",
      }, { immediate: true });
    }
  }
  if (gesture && recognizeTap && !tapRecognized) {
    const elapsed = Date.now() - gesture.startedAt;
    const reason = elapsed > TWO_FINGER_TAP_MAX_MS
      ? "late"
      : Math.max(gesture.maxMovementA, gesture.maxMovementB) > TWO_FINGER_TAP_SLOP
        ? "moved"
        : "ineligible";
    logGestureDiagnostic("gesture-state", {
      gesture: "two-finger-double-click",
      state: "rejected",
      reason,
    });
  }
  if (gesture) gesture.pointerIds.forEach((pointerId) => state.activePointers.delete(pointerId));
  state.twoFingerGesture = null;
  resetPrimaryPointerState();
}

function resetPrimaryPointerState() {
  state.pointerDown = false;
  state.dragActive = false;
  state.pointerId = null;
  state.startClientPoint = null;
  state.lastClientPoint = null;
  state.startSourcePoint = null;
  state.lastSourcePoint = null;
  state.directTouchDownSent = false;
  state.suppressPrimaryTapUp = false;
  if (!state.activePointers.size) state.currentGestureId = "";
}

function getDirectTouchPoint(event) {
  return viewerPointToSourceNormalized(event.clientX, event.clientY)
    || state.lastSourcePoint
    || state.startSourcePoint;
}

function sendTapActionAtPoint(point) {
  if (!point) {
    return;
  }
  const action = state.controlMode === "touch"
    ? state.tapMode === "double"
      ? "touch_double"
      : state.tapMode === "right"
        ? "touch_hold"
        : "touch_tap"
    : state.tapMode === "double"
      ? "double"
      : state.tapMode === "right"
        ? "right_tap"
        : "tap";
  sendPointer(action, point);
}

function handlePointerDown(event) {
  if (state.activePointers.size === 0) state.currentGestureId = diagnosticId("gesture");
  state.pointerType = ["touch", "pen", "mouse"].includes(event.pointerType) ? event.pointerType : "unknown";
  state.activePointers.set(event.pointerId, {
    x: event.clientX,
    y: event.clientY,
  });
  logGestureDiagnostic("pointer-down", {
    phase: "down",
    x: clampRatio(event.clientX / Math.max(elements.touchLayer.clientWidth || window.innerWidth, 1)),
    y: clampRatio(event.clientY / Math.max(elements.touchLayer.clientHeight || window.innerHeight, 1)),
    state: "recognizing",
  });

  if (state.activePointers.size >= 2) {
    if (!state.selectedWindow) {
      return;
    }

    event.preventDefault();
    cancelPendingTap("two-finger-gesture");
    elements.touchLayer.setPointerCapture(event.pointerId);

    if (state.activePointers.size > 2) {
      if (state.twoFingerGesture) {
        state.twoFingerGesture.tapEligible = false;
        state.twoFingerGesture.holdEligible = false;
        clearTwoFingerHoldTimer(state.twoFingerGesture);
      }
      return;
    }

    const primaryId = state.pointerId !== null && state.activePointers.has(state.pointerId)
      ? state.pointerId
      : Array.from(state.activePointers.keys()).find((pointerId) => pointerId !== event.pointerId);
    const primaryPoint = state.activePointers.get(primaryId);
    state.twoFingerGesture = {
      pointerIds: [primaryId, event.pointerId],
      startA: { ...primaryPoint },
      startB: { x: event.clientX, y: event.clientY },
      mode: null,
      tapEligible: true,
      startedAt: Date.now(),
      releasedPointerIds: new Set(),
      endA: null,
      endB: null,
      maxMovementA: 0,
      maxMovementB: 0,
      holdEligible: true,
      holdTimer: null,
      scrollArmed: false,
      armA: null,
      armB: null,
      dragPointerId: null,
      startScale: state.cameraScale,
      startFocus: viewerPointToSourceNormalized(
        (primaryPoint.x + event.clientX) / 2,
        (primaryPoint.y + event.clientY) / 2,
      ) || state.cameraFocus,
      lastSourcePoint: null,
    };
    state.suppressPrimaryTapUp = true;
    scheduleTwoFingerScrollArm(state.twoFingerGesture);
    logGestureDiagnostic("gesture-state", { gesture: "two-finger", state: "candidate" });
    return;
  }

  if (!state.selectedWindow) {
    return;
  }

  event.preventDefault();
  state.pointerDown = true;
  state.dragActive = false;
  state.pointerId = event.pointerId;
  state.suppressPrimaryTapUp = false;
  state.startClientPoint = {
    x: event.clientX,
    y: event.clientY,
  };
  state.lastClientPoint = {
    x: event.clientX,
    y: event.clientY,
  };
  state.startSourcePoint = viewerPointToSourceNormalized(event.clientX, event.clientY);
  state.lastSourcePoint = state.startSourcePoint;
  state.directTouchDownSent = false;
  elements.touchLayer.setPointerCapture(event.pointerId);
}

function handlePointerMove(event) {
  if (state.activePointers.has(event.pointerId)) {
    state.activePointers.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
  }
  const now = Date.now();
  if (now - state.lastGestureMoveLoggedAt >= 120) {
    state.lastGestureMoveLoggedAt = now;
    logGestureDiagnostic("pointer-move", {
      phase: "move",
      x: clampRatio(event.clientX / Math.max(elements.touchLayer.clientWidth || window.innerWidth, 1)),
      y: clampRatio(event.clientY / Math.max(elements.touchLayer.clientHeight || window.innerHeight, 1)),
      state: state.twoFingerGesture?.mode || (state.dragActive ? "drag" : "candidate"),
    });
  }

  if (state.twoFingerGesture) {
    const gesture = state.twoFingerGesture;
    const first = state.activePointers.get(gesture.pointerIds[0]);
    const second = state.activePointers.get(gesture.pointerIds[1]);
    if (first) gesture.maxMovementA = Math.max(gesture.maxMovementA, getPointerDistance(gesture.startA, first));
    if (second) gesture.maxMovementB = Math.max(gesture.maxMovementB, getPointerDistance(gesture.startB, second));
    if (!first || !second) return;
    event.preventDefault();
    cancelPendingTap("two-finger-gesture");

    if (!gesture.mode) {
      const holdDrag = gesture.scrollArmed
        ? window.PCPhoneLinkGestures.isHoldAndDragScroll(
          gesture.armA,
          gesture.armB,
          first,
          second,
          TWO_FINGER_HOLD_SLOP,
          TWO_FINGER_SCROLL_START_THRESHOLD,
        )
        : { active: false, dragIndex: -1 };
      if (holdDrag.active) {
        gesture.mode = "scroll";
        gesture.dragPointerId = gesture.pointerIds[holdDrag.dragIndex];
      } else {
        const pinchMode = window.PCPhoneLinkGestures.classifyTwoFingerGesture(
          gesture.startA,
          gesture.startB,
          first,
          second,
          TWO_FINGER_PINCH_THRESHOLD,
        );
        if (pinchMode === "pinch") {
          gesture.mode = "pinch";
          clearTwoFingerHoldTimer(gesture);
        } else {
          if (gesture.holdEligible && !gesture.scrollArmed) {
            const motion = window.PCPhoneLinkGestures.twoFingerMotion(
              gesture.startA,
              gesture.startB,
              first,
              second,
            );
            if (motion.movementA > TWO_FINGER_HOLD_SLOP || motion.movementB > TWO_FINGER_HOLD_SLOP) {
              gesture.holdEligible = false;
              clearTwoFingerHoldTimer(gesture);
              logGestureDiagnostic("gesture-state", {
                gesture: "two-finger-scroll",
                state: "disarmed",
                reason: "moved-before-hold",
              });
            }
          }
          return;
        }
      }
      logGestureDiagnostic("gesture-classified", { gesture: gesture.mode, state: "active" }, { immediate: true });
      state.suppressPrimaryTapUp = true;
      if (gesture.mode === "pinch") {
        haptic();
        showGestureStatus("Zoom");
        setCameraFocus(gesture.startFocus.x, gesture.startFocus.y);
      } else {
        showGestureStatus("Scroll");
        const dragPoint = state.activePointers.get(gesture.dragPointerId) || first;
        const startSource = viewerPointToSourceNormalized(dragPoint.x, dragPoint.y);
        gesture.lastDragPoint = { ...dragPoint };
        gesture.lastSourcePoint = startSource;
        if (state.controlMode === "touch" && startSource) sendPointer("touch_down", startSource);
      }
    }

    if (gesture.mode === "pinch") {
      const startDistance = Math.max(getPointerDistance(gesture.startA, gesture.startB), 1);
      setCameraScale(gesture.startScale * (getPointerDistance(first, second) / startDistance));
      return;
    }

    const dragPoint = state.activePointers.get(gesture.dragPointerId)
      || (gesture.dragPointerId === gesture.pointerIds[0] ? first : second);
    if (state.controlMode === "touch") {
      const sourcePoint = viewerPointToSourceNormalized(dragPoint.x, dragPoint.y) || gesture.lastSourcePoint;
      if (sourcePoint) {
        gesture.lastSourcePoint = sourcePoint;
        sendPointer("touch_move", sourcePoint);
      }
    } else if (gesture.lastDragPoint) {
      const deltaY = dragPoint.y - gesture.lastDragPoint.y;
      if (Math.abs(deltaY) >= 1) sendPointer("wheel_current", { delta: Math.round(-deltaY * 8) });
    }
    gesture.lastDragPoint = { ...dragPoint };
    return;
  }

  if (!state.selectedWindow || !state.pointerDown || event.pointerId !== state.pointerId) {
    return;
  }

  event.preventDefault();
  const deltaX = event.clientX - state.lastClientPoint.x;
  const deltaY = event.clientY - state.lastClientPoint.y;
  const totalDeltaX = Math.abs(event.clientX - state.startClientPoint.x);
  const totalDeltaY = Math.abs(event.clientY - state.startClientPoint.y);

  if (Math.abs(deltaX) < 0.5 && Math.abs(deltaY) < 0.5) {
    return;
  }

  const dragThreshold = state.controlMode === "touch" ? DIRECT_TOUCH_DRAG_THRESHOLD : 4;
  const wasDragActive = state.dragActive;
  if (!state.dragActive && (totalDeltaX > dragThreshold || totalDeltaY > dragThreshold)) {
    state.dragActive = true;
    cancelPendingTap("drag");
    showGestureStatus(state.controlMode === "touch" ? "Pan viewer" : "Mouse move");
    logGestureDiagnostic(
      "gesture-classified",
      { gesture: state.controlMode === "touch" ? "one-finger-pan" : "mouse-move", state: "active" },
    );
  }

  state.lastClientPoint = {
    x: event.clientX,
    y: event.clientY,
  };

  if (state.controlMode === "touch") {
    if (state.dragActive) {
      const panDeltaX = wasDragActive ? deltaX : event.clientX - state.startClientPoint.x;
      const panDeltaY = wasDragActive ? deltaY : event.clientY - state.startClientPoint.y;
      const moved = panCameraByClientDelta(panDeltaX, panDeltaY);
      logGestureDiagnostic("viewer-pan", {
        gesture: "one-finger-pan",
        delta_x: panDeltaX,
        delta_y: panDeltaY,
        result: moved ? "moved" : "bounded",
      });
    }
    return;
  }

  sendPointer("move_relative", {
    deltaX: deltaX * state.mouseSpeed * TRACKPAD_BASE_SPEED,
    deltaY: deltaY * state.mouseSpeed * TRACKPAD_BASE_SPEED,
  });
}

function handlePointerUp(event) {
  logGestureDiagnostic("pointer-up", { phase: "up", state: "finishing" });

  if (state.twoFingerGesture && state.twoFingerGesture.pointerIds.includes(event.pointerId)) {
    event.preventDefault();
    const gesture = state.twoFingerGesture;
    const pointerIndex = gesture.pointerIds.indexOf(event.pointerId);
    const endPoint = { x: event.clientX, y: event.clientY };
    if (pointerIndex === 0) {
      gesture.endA = endPoint;
      gesture.maxMovementA = Math.max(gesture.maxMovementA, getPointerDistance(gesture.startA, endPoint));
    } else {
      gesture.endB = endPoint;
      gesture.maxMovementB = Math.max(gesture.maxMovementB, getPointerDistance(gesture.startB, endPoint));
    }
    state.activePointers.delete(event.pointerId);
    if (elements.touchLayer.hasPointerCapture(event.pointerId)) {
      elements.touchLayer.releasePointerCapture(event.pointerId);
    }
    if (gesture.mode || gesture.scrollArmed) {
      for (const pointerId of gesture.pointerIds) {
        if (elements.touchLayer.hasPointerCapture(pointerId)) elements.touchLayer.releasePointerCapture(pointerId);
      }
      finishTwoFingerGesture();
      return;
    }
    clearTwoFingerHoldTimer(gesture);
    gesture.holdEligible = false;
    gesture.releasedPointerIds.add(event.pointerId);
    if (gesture.releasedPointerIds.size === gesture.pointerIds.length) {
      finishTwoFingerGesture({ recognizeTap: true });
    }
    return;
  }

  state.activePointers.delete(event.pointerId);

  if (!state.selectedWindow || !state.pointerDown || event.pointerId !== state.pointerId) {
    return;
  }

  event.preventDefault();
  const didDrag = state.dragActive || state.suppressPrimaryTapUp;

  if (state.controlMode === "touch") {
    const point = getDirectTouchPoint(event);
    if (point) {
      state.lastSourcePoint = point;
    }
    if (state.directTouchDownSent) {
      const releasePoint = point || state.lastSourcePoint || state.startSourcePoint;
      if (releasePoint) {
        sendPointer("touch_up", releasePoint);
      }
    } else if (!didDrag) {
      if (state.tapMode === "left") {
        queueAppTouchTap(point, { x: event.clientX, y: event.clientY });
      } else {
        sendTapActionAtPoint(point);
        showGestureStatus(state.tapMode === "right" ? "Right-click" : "Double-click");
      }
    }

    if (state.tapMode !== "left") {
      setTapMode("left");
    }

    if (elements.touchLayer.hasPointerCapture(event.pointerId)) {
      elements.touchLayer.releasePointerCapture(event.pointerId);
    }

    resetPrimaryPointerState();
    return;
  }

  if (!didDrag) {
    const action = state.tapMode === "double"
      ? "double_current"
      : state.tapMode === "right"
        ? "right_click_current"
        : "click_current";
    sendPointer(action);
  }

  if (state.tapMode !== "left") {
    setTapMode("left");
  }

  if (elements.touchLayer.hasPointerCapture(event.pointerId)) {
    elements.touchLayer.releasePointerCapture(event.pointerId);
  }

  resetPrimaryPointerState();
}

function handlePointerCancel(event) {
  cancelPendingTap("pointer-cancel");
  logGestureDiagnostic("pointer-cancel", { phase: "cancel", reason: "browser", state: "reset" }, { immediate: true });
  if (state.twoFingerGesture && state.twoFingerGesture.pointerIds.includes(event.pointerId)) {
    state.activePointers.delete(event.pointerId);
    for (const pointerId of state.twoFingerGesture.pointerIds) {
      if (elements.touchLayer.hasPointerCapture(pointerId)) elements.touchLayer.releasePointerCapture(pointerId);
    }
    finishTwoFingerGesture({ canceled: true });
    return;
  }

  state.activePointers.delete(event.pointerId);

  if (state.controlMode === "touch" && state.directTouchDownSent) {
    const releasePoint = state.lastSourcePoint || state.startSourcePoint;
    if (releasePoint) {
      sendPointer("touch_cancel", releasePoint);
    }
  }

  if (elements.touchLayer.hasPointerCapture(event.pointerId)) {
    elements.touchLayer.releasePointerCapture(event.pointerId);
  }

  resetPrimaryPointerState();
}

async function focusSelectedWindow(maximize = false) {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }
  if (state.selectedWindow.is_desktop_capture) {
    showToast("Fullscreen is already showing the whole screen.");
    return;
  }

  const response = await apiFetch(`/api/windows/${state.selectedWindow.hwnd}/activate`, {
    method: "POST",
    body: JSON.stringify({ maximize }),
  });
  updateSelectedWindow(response.window || state.selectedWindow);
  refreshStream();
}

async function maximizeSelectedWindow() {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }
  if (state.selectedWindow.is_desktop_capture) {
    showToast("Fullscreen is already showing the whole screen.");
    return;
  }

  const response = await apiFetch(`/api/windows/${state.selectedWindow.hwnd}/maximize`, { method: "POST" });
  updateSelectedWindow(response.window || state.selectedWindow);
  refreshStream();
}

async function handleFitToggle() {
  if (state.phoneFitEnabled) {
    await maximizeSelectedWindow();
    return;
  }
  await applyPhoneFit();
}

async function restoreSelectedWindow() {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }
  if (state.selectedWindow.is_desktop_capture) {
    showToast("Fullscreen is already showing the whole screen.");
    return;
  }

  const response = await apiFetch(`/api/windows/${state.selectedWindow.hwnd}/restore`, { method: "POST" });
  updateSelectedWindow(response.window || state.selectedWindow);
  refreshStream();
}

async function applyPhoneFit(trigger = "manual") {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }
  if (state.selectedWindow.is_desktop_capture) {
    showToast("Phone Fit only works for app windows.");
    return;
  }

  const viewerSize = getViewerFitSize();
  const requestSize = getPhoneFitRequestSize(viewerSize);
  writeClientLog(
    "phone-fit",
    "phone-fit-request",
    buildPhoneFitLogDetails({
      trigger,
      viewerWidth: viewerSize.width,
      viewerHeight: viewerSize.height,
      requestedViewportWidth: requestSize.width,
      requestedViewportHeight: requestSize.height,
    }),
  );
  let response;
  try {
    response = await apiFetch(`/api/windows/${state.selectedWindow.hwnd}/phone-fit`, {
      method: "POST",
      body: JSON.stringify({
        viewport_width: requestSize.width,
        viewport_height: requestSize.height,
      }),
    });
  } catch (error) {
    writeClientLog(
      "phone-fit",
      "phone-fit-error",
      buildPhoneFitLogDetails({
        trigger,
        viewerWidth: viewerSize.width,
        viewerHeight: viewerSize.height,
        requestedViewportWidth: requestSize.width,
        requestedViewportHeight: requestSize.height,
        error: error.message,
      }),
    );
    throw error;
  }
  updateSelectedWindow(response.window || state.selectedWindow);
  writeClientLog(
    "phone-fit",
    "phone-fit-response",
    buildPhoneFitLogDetails({
      trigger,
        viewerWidth: viewerSize.width,
        viewerHeight: viewerSize.height,
        requestedViewportWidth: requestSize.width,
        requestedViewportHeight: requestSize.height,
      responseWindow: summarizeWindowForLog(response.window || state.selectedWindow),
    }),
  );
  state.phoneFitEnabled = true;
  syncPhoneFitButton();
  refreshStream();
}

async function requestTextSizeUpdate(
  action,
  {
    value = null,
    successMessage = null,
    unchangedMessage = null,
    showSuccessToast = true,
    showUnchangedToast = true,
  } = {},
) {
  let response;
  response = await apiFetch("/api/system/text-size", {
    method: "POST",
    body: JSON.stringify({ action, value }),
  });
  setTextScaleValue(response.text_scale, { confirmed: true });
  if (!response.changed) {
    if (showUnchangedToast && unchangedMessage) {
      showToast(typeof unchangedMessage === "function" ? unchangedMessage(response) : unchangedMessage);
    }
    return;
  }
  if (!showSuccessToast || !successMessage) {
    return;
  }
  const successPrefix = typeof successMessage === "function" ? successMessage(response) : successMessage;
  if (response.applied_immediately === false) {
    showToast(`${successPrefix} ${response.text_scale}%. Some apps may update after reopening.`);
    return;
  }
  showToast(`${successPrefix} ${response.text_scale}%.`);
}

async function makeTextLarger() {
  cancelPendingTextScaleApply();
  await requestTextSizeUpdate("larger", {
    successMessage: "Text size increased to",
    unchangedMessage: (response) => `Text is already at the largest size (${response.text_scale}%).`,
  });
}

async function makeTextSmaller() {
  cancelPendingTextScaleApply();
  await requestTextSizeUpdate("smaller", {
    successMessage: "Text size decreased to",
    unchangedMessage: (response) => `Text is already at the smallest size (${response.text_scale}%).`,
  });
}

function cancelPendingTextScaleApply() {
  state.textScaleApplyTimer = null;
  state.pendingTextScaleValue = null;
  state.pendingTextScaleToast = false;
  syncTextScaleControl();
}

async function flushPendingTextScaleApply() {
  if (state.textScaleRequestInFlight) {
    return;
  }

  const nextValue = state.pendingTextScaleValue;
  if (nextValue === null || nextValue === state.confirmedTextScale) {
    state.pendingTextScaleValue = null;
    syncTextScaleControl();
    return;
  }

  state.pendingTextScaleValue = null;
  const showSuccessToast = state.pendingTextScaleToast;
  state.pendingTextScaleToast = false;
  state.textScaleRequestInFlight = true;
  syncTextScaleControl();
  try {
    await requestTextSizeUpdate("set", {
      value: nextValue,
      successMessage: "Text size set to",
      unchangedMessage: (response) => `Text size is already ${response.text_scale}%.`,
      showSuccessToast,
      showUnchangedToast: showSuccessToast,
    });
  } catch (error) {
    setTextScaleValue(state.confirmedTextScale, { confirmed: true });
    showToast(error.message);
  } finally {
    state.textScaleRequestInFlight = false;
    syncTextScaleControl();
  }
}

function scheduleTextScaleApply(value, _delay = 0, { showSuccessToast = false } = {}) {
  const nextValue = clampTextScale(value);
  state.textScale = nextValue;
  state.pendingTextScaleValue = nextValue;
  state.pendingTextScaleToast = state.pendingTextScaleToast || showSuccessToast;
  syncTextScaleControl();
}

async function applySelectedTextScale() {
  await flushPendingTextScaleApply();
}

function sendWheel(delta) {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }

  sendPointer("wheel_current", { delta });
}

function closePowerMenus() {
  elements.powerMenu?.classList.add("hidden");
  elements.settingsPowerMenu?.classList.add("hidden");
  elements.powerToggle?.setAttribute("aria-expanded", "false");
  elements.settingsPowerToggle?.setAttribute("aria-expanded", "false");
}

function togglePowerMenu(force, source = "desktop") {
  const menu = source === "settings" ? elements.settingsPowerMenu : elements.powerMenu;
  const toggle = source === "settings" ? elements.settingsPowerToggle : elements.powerToggle;
  if (!menu || !toggle) return;
  const shouldShow = typeof force === "boolean" ? force : menu.classList.contains("hidden");
  closePowerMenus();
  if (shouldShow) {
    menu.classList.remove("hidden");
    toggle.setAttribute("aria-expanded", "true");
    if (source === "settings") {
      window.requestAnimationFrame(() => menu.scrollIntoView({ block: "nearest", inline: "nearest" }));
    }
  }
  renderBottomNav();
}

async function requestPowerAction(action) {
  const config = POWER_ACTIONS[action];
  if (!config) {
    return;
  }
  closePowerMenus();
  if (config.confirm && !window.confirm(config.confirm)) {
    return;
  }
  await apiFetch("/api/system/power", {
    method: "POST",
    body: JSON.stringify({ action }),
  });
  showToast(config.done);
}

function handleTextInput() {
  saveMessageDraft();
  autoResizeTextInput();
  syncMessageHistoryVisibility();
}

async function sendComposedText() {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }

  const message = elements.textInput.value;
  if (!message.trim()) {
    showToast("Type a message first.");
    return;
  }

  if (state.followTyping) {
    queueFollowTypingLog("send-message", buildFollowTypingLogDetails({
      textLength: message.length,
      lineCount: message.split(/\r?\n/).length,
    }), { immediate: true });
    nudgeCameraForTyping(message, "forward");
  }

  await queueJsonPost(`/api/windows/${state.selectedWindow.hwnd}/text`, {
    text: message,
  });
  await queueJsonPost(`/api/windows/${state.selectedWindow.hwnd}/key`, {
    key: "enter",
  });

  rememberSentMessage(message);
  clearComposerDraft();
  showToast("Message sent.");
}

async function sendSpecialKey(key) {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }
  holdKeyboardCapture();
  await queueJsonPost(`/api/windows/${state.selectedWindow.hwnd}/key`, { key });
  showGestureStatus(`Key: ${key}`);
}

function handleTextSubmit(event) {
  event.preventDefault();
  if (state.voiceListening && state.voiceRecognition) {
    state.voiceRecognition.stop();
  }
  sendComposedText().catch((error) => showToast(error.message));
}

function openDestination(destination, { toggle = false } = {}) {
  cancelPendingTap("navigation");
  const next = toggle && state.currentDestination === destination ? "viewer" : destination;
  if (next === "viewer" && state.currentDestination !== "viewer"
    && (state.pointerDown || state.activePointers.size || state.twoFingerGesture)) {
    releaseActiveTouches();
  }
  closePowerMenus();
  state.currentDestination = next;
  elements.windowDrawer.classList.remove("panel-open");
  elements.controlsPanel?.classList.remove("panel-open");
  elements.settingsPanel?.classList.remove("panel-open");
  if (next !== "keyboard" && !elements.keyboardPanel.classList.contains("hidden")) closeKeyboardCapture();

  if (next === "windows") {
    elements.windowDrawer.classList.add("open", "panel-open");
  } else if (next === "keyboard") {
    openKeyboardCapture({ focusInput: false });
  } else if (next === "controls") {
    elements.controlsPanel?.classList.add("panel-open");
  } else if (next === "settings") {
    elements.settingsPanel?.classList.add("panel-open");
  }

  document.querySelectorAll("[data-destination]").forEach((button) => {
    button.classList.toggle("active", button.dataset.destination === next);
  });
  renderBottomNav();
  if (history.replaceState) history.replaceState(null, "", `#${next}`);
}

function syncInstallUi() {
  if (!elements.installCard) return;
  const standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  if (standalone) {
    elements.installStatus.textContent = "Installed. Running in app mode.";
    elements.installApp.hidden = true;
    return;
  }
  if (!window.isSecureContext) {
    elements.installStatus.textContent = "This LAN HTTP page can be added as a home-screen shortcut where browser supports it. Full install, offline shell, and updates require trusted HTTPS.";
    elements.installApp.hidden = true;
    return;
  }
  elements.installApp.hidden = false;
  elements.installApp.disabled = !state.installPrompt;
  if (!state.installPrompt) {
    const isiOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    elements.installStatus.textContent = isiOS
      ? "In Safari, tap Share, then Add to Home Screen."
      : "Use browser menu, then Install app or Add to Home screen.";
  }
}

async function installApp() {
  if (!state.installPrompt) {
    syncInstallUi();
    showToast(elements.installStatus?.textContent || "Use browser menu to install.");
    return;
  }
  state.installPrompt.prompt();
  await state.installPrompt.userChoice;
  state.installPrompt = null;
  syncInstallUi();
}

function registerPwa() {
  syncInstallUi();
  if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
  navigator.serviceWorker.register("/sw.js").then((registration) => {
    registration.addEventListener("updatefound", () => {
      const worker = registration.installing;
      worker?.addEventListener("statechange", () => {
        if (worker.state === "installed" && navigator.serviceWorker.controller) showToast("App update ready. Reopen to use it.");
      });
    });
  }).catch(() => {});
}

if (elements.pairingDeviceName) {
  elements.pairingDeviceName.addEventListener("input", () => {
    state.pairingDeviceName = normalizePairingDeviceName(elements.pairingDeviceName.value);
  });
  elements.pairingDeviceName.addEventListener("change", () => {
    window.localStorage.setItem(PAIRING_DEVICE_NAME_STORAGE_KEY, syncPairingDeviceNameInput());
  });
}

elements.connectButton.addEventListener("click", () => connectPhone().catch((error) => showToast(error.message)));

if (elements.toggleControls) {
  elements.toggleControls.addEventListener("click", toggleControls);
}
elements.refreshWindows.addEventListener("click", () => refreshWindows().catch((error) => showToast(error.message)));
if (elements.focusWindow) {
  elements.focusWindow.addEventListener("click", () => focusSelectedWindow(false).catch((error) => showToast(error.message)));
}
if (elements.maximizeWindow) {
  elements.maximizeWindow.addEventListener("click", () => maximizeSelectedWindow().catch((error) => showToast(error.message)));
}
if (elements.textLarger) {
  elements.textLarger.addEventListener("click", () => makeTextLarger().catch((error) => showToast(error.message)));
}
if (elements.textSmaller) {
  elements.textSmaller.addEventListener("click", () => makeTextSmaller().catch((error) => showToast(error.message)));
}
if (elements.mouseSpeed) {
  elements.mouseSpeed.addEventListener("input", (event) => {
    const nextValue = Number.parseFloat(event.target.value);
    state.mouseSpeed = Number.isFinite(nextValue) ? nextValue : 1;
    window.localStorage.setItem("pc-phone-link-mouse-speed", String(state.mouseSpeed));
    updateMouseSpeedLabel();
  });
}
if (elements.streamFps) {
  elements.streamFps.addEventListener("input", (event) => setStreamFps(event.target.value, { persist: true }));
  elements.streamFps.addEventListener("change", (event) => setStreamFps(event.target.value, { persist: true, refresh: true }));
}
if (elements.streamWidth) {
  elements.streamWidth.addEventListener("change", (event) => setStreamWidth(event.target.value, { persist: true, refresh: true }));
}
if (elements.powerToggle && elements.powerMenu) {
  elements.powerToggle.addEventListener("click", () => togglePowerMenu(undefined, "desktop"));
}
if (elements.settingsPowerToggle && elements.settingsPowerMenu) {
  elements.settingsPowerToggle.addEventListener("click", () => togglePowerMenu(undefined, "settings"));
}
if (elements.powerMenu || elements.settingsPowerMenu) {
  document.querySelectorAll("[data-power-action]").forEach((button) => {
    button.addEventListener("click", () => {
      requestPowerAction(button.dataset.powerAction).catch((error) => showToast(error.message));
    });
  });
  document.addEventListener("pointerdown", (event) => {
    const insidePowerUi = elements.powerMenu?.contains(event.target)
      || elements.powerToggle?.contains(event.target)
      || elements.settingsPowerMenu?.contains(event.target)
      || elements.settingsPowerToggle?.contains(event.target);
    if (!insidePowerUi) closePowerMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePowerMenus();
  });
}
elements.textScale.addEventListener("input", (event) => {
  scheduleTextScaleApply(event.target.value);
});
elements.textScale.addEventListener("change", (event) => {
  scheduleTextScaleApply(event.target.value, 0, { showSuccessToast: true });
});
elements.applyTextScale.addEventListener("click", () => applySelectedTextScale().catch((error) => showToast(error.message)));
elements.fitShape.addEventListener("change", (event) => {
  setFitShape(event.target.value, { apply: state.phoneFitEnabled });
});
elements.applyFitShape.addEventListener("click", () => applyPhoneFit("shape-button").catch((error) => showToast(error.message)));
if (elements.controlMode) {
  elements.controlMode.addEventListener("change", (event) => setControlMode(event.target.value));
}
if (elements.followMouse) {
  elements.followMouse.addEventListener("change", (event) => {
    state.followMouse = event.target.checked;
    window.localStorage.setItem("pc-phone-link-follow-mouse", String(state.followMouse));
  });
}
elements.refreshTrustedDevices.addEventListener("click", () => refreshTrustedDevices().catch((error) => showToast(error.message)));
if (elements.restoreWindow) {
  elements.restoreWindow.addEventListener("click", () => restoreSelectedWindow().catch((error) => showToast(error.message)));
}
elements.toggleKeyboard.addEventListener("click", () => {
  if (usesMobileShell()) openDestination("keyboard", { toggle: true });
  else toggleKeyboardPanel();
});
elements.toggleMessageHistory.addEventListener("pointerdown", () => holdKeyboardCapture());
elements.toggleMessageHistory.addEventListener("click", toggleMessageHistoryPanel);
elements.clearTextInput.addEventListener("click", () => clearComposerDraft());
elements.fitToggle.addEventListener("click", () => handleFitToggle().catch((error) => showToast(error.message)));
if (elements.voiceInput) {
  elements.voiceInput.addEventListener("click", () => toggleVoiceInput().catch((error) => showToast(error.message)));
}
if (elements.rightClickMode) {
  elements.rightClickMode.addEventListener("click", () => setTapMode(state.tapMode === "right" ? "left" : "right"));
}
if (elements.doubleClickMode) {
  elements.doubleClickMode.addEventListener("click", () => setTapMode(state.tapMode === "double" ? "left" : "double"));
}
if (elements.scrollUp) {
  elements.scrollUp.addEventListener("click", () => sendWheel(240));
}
if (elements.scrollDown) {
  elements.scrollDown.addEventListener("click", () => sendWheel(-240));
}
elements.textForm.addEventListener("submit", handleTextSubmit);
elements.textInput.addEventListener("input", handleTextInput);
elements.textInput.addEventListener("focus", () => {
  state.keyboardComposerRequested = true;
  scheduleKeyboardComposerSync(0);
});
elements.textInput.addEventListener("blur", () => scheduleKeyboardComposerSync(150));
elements.remoteView.addEventListener("load", applyCameraTransform);

elements.touchLayer.addEventListener("pointerdown", handlePointerDown);
elements.touchLayer.addEventListener("pointermove", handlePointerMove);
elements.touchLayer.addEventListener("pointerup", handlePointerUp);
elements.touchLayer.addEventListener("pointercancel", handlePointerCancel);
elements.touchLayer.addEventListener("contextmenu", (event) => event.preventDefault());

document.addEventListener("click", (event) => {
  const specialKeyButton = event.target.closest("[data-special-key]");
  if (specialKeyButton) {
    sendSpecialKey(specialKeyButton.dataset.specialKey).catch((error) => showToast(error.message));
    return;
  }
  const editorButton = event.target.closest("[data-nav-editor-action]");
  if (editorButton) {
    const id = editorButton.dataset.shortcutId;
    const index = state.bottomNavOptional.indexOf(id);
    if (index < 0) return;
    const next = [...state.bottomNavOptional];
    if (editorButton.dataset.navEditorAction === "remove") next.splice(index, 1);
    if (editorButton.dataset.navEditorAction === "up" && index > 0) {
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
    }
    if (editorButton.dataset.navEditorAction === "down" && index < next.length - 1) {
      [next[index + 1], next[index]] = [next[index], next[index + 1]];
    }
    saveBottomNavConfig(next);
    return;
  }
  const bottomAction = event.target.closest("[data-bottom-action]");
  if (bottomAction) {
    executeBottomNavAction(bottomAction.dataset.bottomAction).catch((error) => showToast(error.message));
    return;
  }
  const destinationButton = event.target.closest("[data-destination]");
  if (destinationButton) {
    openDestination(destinationButton.dataset.destination, { toggle: true });
  }
});
elements.gestureHelpButton?.addEventListener("click", () => {
  elements.gestureHelp?.showModal();
  renderBottomNav();
});
elements.gestureHelp?.addEventListener("close", renderBottomNav);
elements.gestureDiagnostics?.addEventListener("change", () => {
  state.gestureDiagnosticsEnabled = Boolean(elements.gestureDiagnostics.checked);
  window.localStorage.setItem(GESTURE_DIAGNOSTICS_STORAGE_KEY, String(state.gestureDiagnosticsEnabled));
  logGestureDiagnostic("diagnostics-setting", { state: state.gestureDiagnosticsEnabled ? "enabled" : "disabled" }, {
    immediate: true,
    force: state.gestureDiagnosticsEnabled,
  });
});
elements.clearGestureLogs?.addEventListener("click", async () => {
  try {
    await apiFetch("/api/diagnostics/gestures/clear", { method: "POST" });
    state.gestureLogBuffer = [];
    showToast("Gesture logs cleared.");
  } catch (error) {
    showToast(error.message || "Could not clear gesture logs.");
  }
});
elements.installApp?.addEventListener("click", () => installApp().catch(() => showToast("Install could not start.")));
elements.bottomNavAddButton?.addEventListener("click", () => {
  const id = elements.bottomNavAdd?.value;
  if (!id || state.bottomNavOptional.length >= MAX_OPTIONAL_BOTTOM_NAV) return;
  saveBottomNavConfig([...state.bottomNavOptional, id]);
});
elements.bottomNavReset?.addEventListener("click", () => saveBottomNavConfig(DEFAULT_BOTTOM_NAV_OPTIONAL));
elements.revealControls?.addEventListener("click", () => setControlsHidden(false));
window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  state.installPrompt = event;
  syncInstallUi();
});
window.addEventListener("appinstalled", () => {
  state.installPrompt = null;
  syncInstallUi();
  showToast("App installed.");
});

function releaseActiveTouches() {
  cancelPendingTap("lifecycle-release");
  if (state.twoFingerGesture) finishTwoFingerGesture({ canceled: true });
  else if (state.controlMode === "touch" && state.directTouchDownSent) {
    const point = state.lastSourcePoint || state.startSourcePoint;
    if (point) sendPointer("touch_cancel", point);
  }
  state.activePointers.clear();
  resetPrimaryPointerState();
}

function emergencyTouchCancel(reason) {
  if (!state.token || !state.currentGestureId) return;
  void fetch("/api/gestures/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Access-Token": state.token },
    body: JSON.stringify({
      session_id: state.gestureSessionId,
      gesture_id: state.currentGestureId,
      reason,
    }),
    keepalive: true,
  }).catch(() => null);
}
window.addEventListener("blur", releaseActiveTouches);
window.addEventListener("pagehide", () => {
  emergencyTouchCancel("pagehide");
  releaseActiveTouches();
  logGestureDiagnostic("lifecycle-release", { reason: "pagehide", state: "reset" }, { immediate: true, force: true });
  flushGestureDiagnostics({ keepalive: true });
});
window.addEventListener("error", () => {
  logGestureDiagnostic("browser-error", { error_type: "ErrorEvent", reason: "uncaught", state: "failed" }, { immediate: true, force: true });
});
window.addEventListener("unhandledrejection", (event) => {
  logGestureDiagnostic("browser-error", {
    error_type: event.reason?.name || "PromiseRejection",
    reason: "unhandled-rejection",
    state: "failed",
  }, { immediate: true, force: true });
});
window.addEventListener("offline", () => setConnectionStatus("Offline", false));
window.addEventListener("online", () => {
  clearHostReconnectPolling();
  if (state.token) bootstrap({ quiet: true });
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && state.token && !state.hostReconnectTimer) {
    bootstrap({ quiet: true });
  }
});

window.addEventListener("resize", () => {
  syncViewportLayout();
  scheduleKeyboardComposerSync(60);
  if (state.selectedWindow) {
    scheduleStreamRefresh();
    applyCameraTransform();
  }
});

if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", () => {
    syncViewportLayout();
    scheduleKeyboardComposerSync(60);
    if (state.selectedWindow) {
      scheduleStreamRefresh();
      applyCameraTransform();
    }
  });
  window.visualViewport.addEventListener("scroll", syncViewportLayout);
}

syncViewportLayout();
syncControlsVisibility();
syncTargetActionButtons();
syncVoiceInputButton();
loadViewerPreferences();
loadMessageComposerState();
registerPwa();
loadSavedToken();
renderTrustedDevices();
if (elements.controlBar) {
  elements.controlBar.hidden = false;
}
syncKeyboardComposerVisibility();
const initialDestination = window.location.hash.slice(1);
if (["viewer", "windows", "keyboard", "controls", "settings"].includes(initialDestination)) {
  openDestination(initialDestination);
}
