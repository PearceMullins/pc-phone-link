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
  windows: [],
  mouseSpeed: 2.5,
  tapMode: "left",
  controlMode: "trackpad",
  fitShape: "auto",
  trustedDevices: [],
  trustedDevicesLoading: false,
  phoneFitEnabled: false,
  phoneFitOrientation: null,
  phoneFitViewportSize: null,
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
  controlQueue: Promise.resolve(),
  moveRequestInFlight: false,
  pendingMovePayload: null,
  viewportResizeTimer: null,
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
  pinchState: null,
  secondaryTapGesture: null,
  suppressPrimaryTapUp: false,
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
};

const TRACKPAD_BASE_SPEED = 2.8;
const FOLLOW_TYPING_MIN_SCALE = 1.6;
const FOLLOW_TYPING_LOG_BATCH_SIZE = 8;
const FOLLOW_TYPING_LOG_FLUSH_DELAY_MS = 1200;
const ACCESS_TOKEN_STORAGE_KEY = "pc-phone-link-token";
const PAIRING_DEVICE_NAME_STORAGE_KEY = "pc-phone-link-pairing-device-name";
const FIT_SHAPE_STORAGE_KEY = "pc-phone-link-fit-shape";
const CONTROL_MODE_STORAGE_KEY = "pc-phone-link-control-mode";
const STREAM_FPS_STORAGE_KEY = "pc-phone-link-stream-fps";
const STREAM_WIDTH_STORAGE_KEY = "pc-phone-link-stream-width";
const STREAM_WIDTH_OPTIONS = [1920, 1600, 1280, 960, 720, 480];
const MESSAGE_HISTORY_STORAGE_KEY = "pc-phone-link-message-history";
const MESSAGE_DRAFT_STORAGE_KEY = "pc-phone-link-message-draft";
const MAX_MESSAGE_HISTORY = 100;
const MAX_VISIBLE_MESSAGE_HISTORY = 12;
const KEYBOARD_VISIBLE_HEIGHT_DELTA = 140;
const KEYBOARD_VISIBLE_HEIGHT_RATIO = 0.18;
const SECONDARY_TAP_MAX_DISTANCE = 18;
const SECONDARY_TAP_MAX_DURATION_MS = 320;
const DIRECT_TOUCH_DRAG_THRESHOLD = 7;
const MAX_CAMERA_SCALE = 6;
const MAX_STREAM_FPS = 30;
const DEFAULT_STREAM_FPS = 20;
const MAX_STREAM_REQUEST_WIDTH = 1920;
const MAX_STREAM_DEVICE_PIXEL_RATIO = 2.5;
const STREAM_REFRESH_DEBOUNCE_MS = 180;
const STREAM_SOCKET_MAX_FAILURES = 2;
const STREAM_RECONNECT_DELAY_MS = 600;

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

const elements = {
  app: document.getElementById("app"),
  applyTextScale: document.getElementById("applyTextScale"),
  authPanel: document.getElementById("authPanel"),
  connectButton: document.getElementById("connectButton"),
  connectCodeDisplay: document.getElementById("connectCodeDisplay"),
  connectStatus: document.getElementById("connectStatus"),
  pairingApprovalCodeBlock: document.getElementById("pairingApprovalCodeBlock"),
  pairingApprovalCodeDisplay: document.getElementById("pairingApprovalCodeDisplay"),
  pairingDeviceName: document.getElementById("pairingDeviceName"),
  clearTextInput: document.getElementById("clearTextInput"),
  controlBar: document.getElementById("controlBar"),
  deviceName: document.getElementById("deviceName"),
  doubleClickMode: document.getElementById("doubleClickMode"),
  emptyState: document.getElementById("emptyState"),
  applyFitShape: document.getElementById("applyFitShape"),
  fitToggle: document.getElementById("fitToggle"),
  fitShape: document.getElementById("fitShape"),
  fitShapeValue: document.getElementById("fitShapeValue"),
  focusWindow: document.getElementById("focusWindow"),
  followMouse: document.getElementById("followMouse"),
  controlMode: document.getElementById("controlMode"),
  keyboardPanel: document.getElementById("keyboardPanel"),
  maximizeWindow: document.getElementById("maximizeWindow"),
  messageHistory: document.getElementById("messageHistory"),
  messageHistorySection: document.getElementById("messageHistorySection"),
  mouseSpeed: document.getElementById("mouseSpeed"),
  mouseSpeedValue: document.getElementById("mouseSpeedValue"),
  powerMenu: document.getElementById("powerMenu"),
  powerToggle: document.getElementById("powerToggle"),
  refreshWindows: document.getElementById("refreshWindows"),
  refreshTrustedDevices: document.getElementById("refreshTrustedDevices"),
  remoteView: document.getElementById("remoteView"),
  restoreWindow: document.getElementById("restoreWindow"),
  rightClickMode: document.getElementById("rightClickMode"),
  scrollDown: document.getElementById("scrollDown"),
  scrollUp: document.getElementById("scrollUp"),
  selectedWindowTitle: document.getElementById("selectedWindowTitle"),
  sendText: document.getElementById("sendText"),
  statusPill: document.getElementById("statusPill"),
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
  toggleDrawer: document.getElementById("toggleDrawer"),
  toggleKeyboard: document.getElementById("toggleKeyboard"),
  touchLayer: document.getElementById("touchLayer"),
  trustedDevices: document.getElementById("trustedDevices"),
  trustedDevicesStatus: document.getElementById("trustedDevicesStatus"),
  toggleMessageHistory: document.getElementById("toggleMessageHistory"),
  viewerShell: document.getElementById("viewerShell"),
  voiceInput: document.getElementById("voiceInput"),
  windowDrawer: document.getElementById("windowDrawer"),
  windowList: document.getElementById("windowList"),
};

function clampRatio(value) {
  return Math.max(0, Math.min(1, value));
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
  elements.viewerShell.classList.toggle("direct-touch-active", state.controlMode === "touch");
  if (state.selectedWindow && elements.keyboardPanel.classList.contains("hidden")) {
    elements.statusPill.textContent = getInputReadyStatus();
  }
}

function setControlMode(value) {
  state.controlMode = value === "touch" ? "touch" : "trackpad";
  window.localStorage.setItem(CONTROL_MODE_STORAGE_KEY, state.controlMode);
  syncControlMode();
}

function getInputReadyStatus() {
  return state.controlMode === "touch" ? "Direct touch ready" : "Trackpad ready";
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
  const savedControlMode = window.localStorage.getItem(CONTROL_MODE_STORAGE_KEY) || "trackpad";
  state.controlMode = savedControlMode === "touch" ? "touch" : "trackpad";
  const savedStreamFps = Number.parseInt(window.localStorage.getItem(STREAM_FPS_STORAGE_KEY) || "", 10);
  if (Number.isFinite(savedStreamFps)) {
    state.streamFps = clampStreamFps(savedStreamFps);
  }
  state.streamWidth = normalizeStreamWidth(window.localStorage.getItem(STREAM_WIDTH_STORAGE_KEY));

  elements.mouseSpeed.value = String(state.mouseSpeed);
  elements.followMouse.checked = state.followMouse;
  updateMouseSpeedLabel();
  syncFitShapeControls();
  syncControlMode();
  syncStreamFpsControl();
  syncStreamWidthControl();
  syncTextScaleControl();
}

function updateMouseSpeedLabel() {
  elements.mouseSpeedValue.textContent = `${state.mouseSpeed.toFixed(2)}x`;
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
    window.clearInterval(state.hostReconnectTimer);
    state.hostReconnectTimer = null;
  }
  state.hostReconnectAttempts = 0;
}

async function bootstrap({ quiet = false } = {}) {
  try {
    const info = await apiFetch("/api/info");
    elements.deviceName.textContent = info.device_name;
    if (!window.localStorage.getItem(STREAM_FPS_STORAGE_KEY)) {
      state.streamFps = clampStreamFps(info.default_fps || state.streamFps);
      syncStreamFpsControl();
    }
    if (typeof info.text_scale === "number" && Number.isFinite(info.text_scale)) {
      setTextScaleValue(info.text_scale, { confirmed: true });
    }
    elements.statusPill.textContent = getInputReadyStatus();
    await refreshWindows();
    void refreshTrustedDevices({ quiet: true });
    scheduleWindowRefresh();
    clearHostReconnectPolling();
    return true;
  } catch (error) {
    if (error.message === "Connect your phone to use PC Phone Link.") {
      state.token = null;
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
      elements.statusPill.textContent = "Connect needed";
      elements.authPanel.classList.remove("hidden");
      beginConnectFlow();
    } else if (!quiet) {
      elements.statusPill.textContent = "Connection lost";
    }
    if (!quiet) {
      showToast(error.message || "Connection failed.");
    }
    return false;
  }
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
    state.phoneFitOrientation = null;
    state.phoneFitViewportSize = null;
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
  const headers = new Headers(options.headers || {});
  headers.set("X-Access-Token", state.token || "");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    elements.authPanel.classList.remove("hidden");
    throw new Error(await readErrorMessage(response, "Connect your phone to use PC Phone Link."));
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
    updateCursorPosition(response.cursor, { allowMouseFollow: true });
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
    state.typingAnchor = null;
  }
  state.selectedWindow = windowInfo;
  state.phoneFitEnabled = Boolean(windowInfo.is_phone_fit);
  state.phoneFitOrientation = state.phoneFitEnabled ? getViewportOrientation() : null;
  state.phoneFitViewportSize = state.phoneFitEnabled ? getPhoneFitRequestSize(getViewerFitSize()) : null;
  if (windowInfo.cursor) {
    updateCursorPosition(windowInfo.cursor, { allowMouseFollow: true });
  }
  elements.selectedWindowTitle.textContent = windowInfo.title;
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
    state.phoneFitOrientation = null;
    state.phoneFitViewportSize = null;
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

  for (const windowInfo of state.windows) {
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
    subtitle.textContent = markers.length ? `${processName} - ${markers.join(" - ")}` : processName;
    button.append(subtitle);

    button.addEventListener("click", () => {
      selectWindow(windowInfo).catch((error) => showToast(error.message));
    });

    elements.windowList.append(button);
  }
}

async function selectWindow(windowInfo) {
  state.streamSocketFailures = 0;
  updateSelectedWindow(windowInfo);
  elements.emptyState.hidden = true;
  elements.remoteView.style.display = "block";
  const response = await apiFetch(`/api/windows/${windowInfo.hwnd}/activate`, {
    method: "POST",
    body: JSON.stringify({ maximize: false }),
  });
  updateSelectedWindow(response.window || windowInfo);
  refreshStream();
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
  return Math.min(Math.max(requestedWidth, 360), MAX_STREAM_REQUEST_WIDTH);
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
  const previousUrl = state.streamObjectUrl;
  state.streamObjectUrl = objectUrl;
  elements.remoteView.src = objectUrl;
  try {
    if (typeof elements.remoteView.decode === "function") {
      await elements.remoteView.decode();
    }
  } catch {
    // Decode fails when a newer source replaced this frame; keep streaming.
  }
  if (previousUrl) {
    URL.revokeObjectURL(previousUrl);
  }
  // Acknowledge only after the frame is decoded so the host adapts its pace
  // to what this phone can actually display, instead of queueing stale frames.
  if (state.streamGeneration === generation && socket.readyState === WebSocket.OPEN) {
    socket.send("r");
  }
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
  elements.selectedWindowTitle.textContent = "Open Windows to choose an app or fullscreen view";
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
  if (window.innerWidth < 900) {
    elements.windowDrawer.classList.remove("open");
  }
}

function toggleDrawer() {
  elements.windowDrawer.classList.toggle("open");
}

function setTapMode(mode) {
  state.tapMode = mode;
  if (elements.rightClickMode) {
    elements.rightClickMode.classList.toggle("mode-active", mode === "right");
  }
  if (elements.doubleClickMode) {
    elements.doubleClickMode.classList.toggle("mode-active", mode === "double");
  }
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
  elements.statusPill.textContent = "Keyboard ready";
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
  elements.statusPill.textContent = state.selectedWindow ? getInputReadyStatus() : "Ready";
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
    elements.statusPill.textContent = "Listening";
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
    elements.statusPill.textContent = elements.keyboardPanel.classList.contains("hidden")
      ? (state.selectedWindow ? getInputReadyStatus() : "Ready")
      : "Keyboard ready";
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

function sendPointer(action, payload = {}) {
  if (!state.selectedWindow) {
    showToast("Open Windows and choose an app.");
    return;
  }

  const requestPayload = {
    action,
    x: Number.isFinite(payload.x) ? payload.x : 0.5,
    y: Number.isFinite(payload.y) ? payload.y : 0.5,
    delta: payload.delta || 0,
    delta_x: payload.deltaX || 0,
    delta_y: payload.deltaY || 0,
  };

  if (action === "move_relative") {
    state.pendingMovePayload = requestPayload;
    flushPendingMove();
    return;
  }

  queueJsonPost(pointerPath(), requestPayload)
    .then((response) => handlePointerResponse(response, action))
    .catch((error) => showToast(error.message));
}

function getPointerDistance(first, second) {
  return Math.hypot(second.x - first.x, second.y - first.y);
}

function getPointerMidpoint(first, second) {
  return {
    x: (first.x + second.x) / 2,
    y: (first.y + second.y) / 2,
  };
}

function clearSecondaryTapGesture() {
  state.secondaryTapGesture = null;
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
  const action = state.tapMode === "double"
    ? "double"
    : state.tapMode === "right"
      ? "right_tap"
      : "tap";
  sendPointer(action, point);
}

function startPinchGesture() {
  const points = Array.from(state.activePointers.values());
  if (points.length < 2) {
    return;
  }

  const midpoint = getPointerMidpoint(points[0], points[1]);
  clearSecondaryTapGesture();
  state.suppressPrimaryTapUp = false;
  state.pinchState = {
    startDistance: Math.max(getPointerDistance(points[0], points[1]), 1),
    startScale: state.cameraScale,
    startFocus: viewerPointToSourceNormalized(midpoint.x, midpoint.y) || state.cameraFocus,
  };

  if (state.pointerId !== null && elements.touchLayer.hasPointerCapture(state.pointerId)) {
    elements.touchLayer.releasePointerCapture(state.pointerId);
  }

  resetPrimaryPointerState();
  setCameraFocus(state.pinchState.startFocus.x, state.pinchState.startFocus.y);
}

function handlePointerDown(event) {
  state.activePointers.set(event.pointerId, {
    x: event.clientX,
    y: event.clientY,
  });

  if (state.activePointers.size >= 2) {
    if (!state.selectedWindow) {
      return;
    }

    event.preventDefault();

    if (state.pinchState) {
      return;
    }

    if (
      state.pointerDown
      && state.pointerId !== null
      && state.activePointers.size === 2
      && state.activePointers.has(state.pointerId)
    ) {
      const primaryPoint = state.activePointers.get(state.pointerId);
      state.secondaryTapGesture = {
        primaryPointerId: state.pointerId,
        pointerId: event.pointerId,
        primaryStartX: primaryPoint.x,
        primaryStartY: primaryPoint.y,
        primarySourcePoint: state.lastSourcePoint || state.startSourcePoint,
        startX: event.clientX,
        startY: event.clientY,
        startedAt: Date.now(),
      };
      return;
    }

    clearSecondaryTapGesture();
    startPinchGesture();
    return;
  }

  if (!state.selectedWindow || state.pinchState) {
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

  if (state.pinchState) {
    if (state.activePointers.size < 2) {
      return;
    }

    event.preventDefault();
    const points = Array.from(state.activePointers.values());
    const midpoint = getPointerMidpoint(points[0], points[1]);
    const distance = Math.max(getPointerDistance(points[0], points[1]), 1);
    const nextScale = state.pinchState.startScale * (distance / state.pinchState.startDistance);
    const nextFocus = viewerPointToSourceNormalized(midpoint.x, midpoint.y) || state.pinchState.startFocus;
    setCameraFocus(nextFocus.x, nextFocus.y);
    setCameraScale(nextScale);
    return;
  }

  if (state.secondaryTapGesture) {
    const primaryPoint = state.activePointers.get(state.secondaryTapGesture.primaryPointerId);
    const secondaryPoint = state.activePointers.get(state.secondaryTapGesture.pointerId);

    if (!primaryPoint || !secondaryPoint) {
      clearSecondaryTapGesture();
      return;
    }

    const primaryMovement = Math.hypot(
      primaryPoint.x - state.secondaryTapGesture.primaryStartX,
      primaryPoint.y - state.secondaryTapGesture.primaryStartY,
    );
    const secondaryMovement = Math.hypot(
      secondaryPoint.x - state.secondaryTapGesture.startX,
      secondaryPoint.y - state.secondaryTapGesture.startY,
    );

    event.preventDefault();

    if (
      primaryMovement > SECONDARY_TAP_MAX_DISTANCE
      || secondaryMovement > SECONDARY_TAP_MAX_DISTANCE
      || state.activePointers.size > 2
    ) {
      startPinchGesture();
    }
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
  if (!state.dragActive && (totalDeltaX > dragThreshold || totalDeltaY > dragThreshold)) {
    state.dragActive = true;
  }

  state.lastClientPoint = {
    x: event.clientX,
    y: event.clientY,
  };

  if (state.controlMode === "touch") {
    const point = getDirectTouchPoint(event);
    if (!point) {
      return;
    }
    state.lastSourcePoint = point;
    if (!state.directTouchDownSent && (totalDeltaX > DIRECT_TOUCH_DRAG_THRESHOLD || totalDeltaY > DIRECT_TOUCH_DRAG_THRESHOLD)) {
      sendPointer("down", state.startSourcePoint || point);
      state.directTouchDownSent = true;
    }
    if (state.directTouchDownSent) {
      sendPointer("move", point);
    }
    return;
  }

  sendPointer("move_relative", {
    deltaX: deltaX * state.mouseSpeed * TRACKPAD_BASE_SPEED,
    deltaY: deltaY * state.mouseSpeed * TRACKPAD_BASE_SPEED,
  });
}

function handlePointerUp(event) {
  const secondaryTapGesture = state.secondaryTapGesture;

  if (secondaryTapGesture && event.pointerId === secondaryTapGesture.pointerId) {
    const primaryPoint = state.activePointers.get(secondaryTapGesture.primaryPointerId);
    const secondaryPoint = state.activePointers.get(secondaryTapGesture.pointerId);
    const primaryMovement = primaryPoint
      ? Math.hypot(
        primaryPoint.x - secondaryTapGesture.primaryStartX,
        primaryPoint.y - secondaryTapGesture.primaryStartY,
      )
      : Number.POSITIVE_INFINITY;
    const secondaryMovement = secondaryPoint
      ? Math.hypot(
        secondaryPoint.x - secondaryTapGesture.startX,
        secondaryPoint.y - secondaryTapGesture.startY,
      )
      : Number.POSITIVE_INFINITY;
    const duration = Date.now() - secondaryTapGesture.startedAt;

    event.preventDefault();
    state.activePointers.delete(event.pointerId);
    clearSecondaryTapGesture();
    state.suppressPrimaryTapUp = true;

    if (
      primaryPoint
      && duration <= SECONDARY_TAP_MAX_DURATION_MS
      && primaryMovement <= SECONDARY_TAP_MAX_DISTANCE
      && secondaryMovement <= SECONDARY_TAP_MAX_DISTANCE
    ) {
      if (state.controlMode === "touch" && secondaryTapGesture.primarySourcePoint) {
        sendPointer("right_tap", secondaryTapGesture.primarySourcePoint);
      } else {
        sendPointer("right_click_current");
      }
    }
    return;
  }

  if (secondaryTapGesture && event.pointerId === secondaryTapGesture.primaryPointerId) {
    event.preventDefault();
    clearSecondaryTapGesture();
    state.suppressPrimaryTapUp = true;
  }

  state.activePointers.delete(event.pointerId);

  if (state.pinchState) {
    event.preventDefault();
    if (state.activePointers.size < 2) {
      state.pinchState = null;
    }
    return;
  }

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
        sendPointer("up", releasePoint);
      }
    } else if (!didDrag) {
      sendTapActionAtPoint(point);
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
  if (
    state.secondaryTapGesture
    && (
      event.pointerId === state.secondaryTapGesture.pointerId
      || event.pointerId === state.secondaryTapGesture.primaryPointerId
    )
  ) {
    clearSecondaryTapGesture();
  }

  state.activePointers.delete(event.pointerId);

  if (state.pinchState && state.activePointers.size < 2) {
    state.pinchState = null;
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
  state.phoneFitOrientation = getViewportOrientation();
  state.phoneFitViewportSize = requestSize;
  syncPhoneFitButton();
  refreshStream();
}

function scheduleAutoPhoneFit(trigger = "viewport-change") {
  if (!state.phoneFitEnabled || !state.selectedWindow || state.selectedWindow.is_desktop_capture) {
    return;
  }

  const nextViewerSize = getPhoneFitRequestSize(getViewerFitSize());
  const previousViewerSize = state.phoneFitViewportSize;
  const orientationChanged = getViewportOrientation() !== state.phoneFitOrientation;
  const sizeChanged = !previousViewerSize
    || Math.abs(nextViewerSize.width - previousViewerSize.width) >= 2
    || Math.abs(nextViewerSize.height - previousViewerSize.height) >= 2;

  if (!orientationChanged && !sizeChanged) {
    return;
  }

  window.clearTimeout(state.viewportResizeTimer);
  state.viewportResizeTimer = window.setTimeout(() => {
    state.viewportResizeTimer = null;
    applyPhoneFit(trigger).catch((error) => showToast(error.message));
  }, 180);
}

async function requestTextSizeUpdate(
  action,
  {
    value = null,
    statusMessage,
    successMessage = null,
    unchangedMessage = null,
    showSuccessToast = true,
    showUnchangedToast = true,
  } = {},
) {
  const previousStatus = elements.statusPill.textContent;
  if (statusMessage) {
    elements.statusPill.textContent = statusMessage;
  }
  let response;
  try {
    response = await apiFetch("/api/system/text-size", {
      method: "POST",
      body: JSON.stringify({ action, value }),
    });
  } catch (error) {
    elements.statusPill.textContent = previousStatus;
    throw error;
  }
  elements.statusPill.textContent = previousStatus;
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
    statusMessage: "Making text larger",
    successMessage: "Text size increased to",
    unchangedMessage: (response) => `Text is already at the largest size (${response.text_scale}%).`,
  });
}

async function makeTextSmaller() {
  cancelPendingTextScaleApply();
  await requestTextSizeUpdate("smaller", {
    statusMessage: "Making text smaller",
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
      statusMessage: "Updating text size",
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

function togglePowerMenu(force) {
  if (!elements.powerMenu) {
    return;
  }
  const shouldShow = typeof force === "boolean" ? force : elements.powerMenu.classList.contains("hidden");
  elements.powerMenu.classList.toggle("hidden", !shouldShow);
}

async function requestPowerAction(action) {
  const config = POWER_ACTIONS[action];
  if (!config) {
    return;
  }
  togglePowerMenu(false);
  if (config.confirm && !window.confirm(config.confirm)) {
    return;
  }
  const previousStatus = elements.statusPill.textContent;
  elements.statusPill.textContent = config.pending;
  try {
    await apiFetch("/api/system/power", {
      method: "POST",
      body: JSON.stringify({ action }),
    });
  } finally {
    elements.statusPill.textContent = previousStatus;
  }
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

  const previousStatus = elements.statusPill.textContent;
  elements.statusPill.textContent = "Sending message";
  if (state.followTyping) {
    queueFollowTypingLog("send-message", buildFollowTypingLogDetails({
      textLength: message.length,
      lineCount: message.split(/\r?\n/).length,
    }), { immediate: true });
    nudgeCameraForTyping(message, "forward");
  }

  try {
    await queueJsonPost(`/api/windows/${state.selectedWindow.hwnd}/text`, {
      text: message,
    });
    await queueJsonPost(`/api/windows/${state.selectedWindow.hwnd}/key`, {
      key: "enter",
    });
  } catch (error) {
    elements.statusPill.textContent = previousStatus;
    throw error;
  }

  rememberSentMessage(message);
  clearComposerDraft();
  elements.statusPill.textContent = previousStatus;
  showToast("Message sent.");
}

function handleTextSubmit(event) {
  event.preventDefault();
  if (state.voiceListening && state.voiceRecognition) {
    state.voiceRecognition.stop();
  }
  sendComposedText().catch((error) => showToast(error.message));
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

elements.toggleDrawer.addEventListener("click", toggleDrawer);
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
elements.mouseSpeed.addEventListener("input", (event) => {
  const nextValue = Number.parseFloat(event.target.value);
  state.mouseSpeed = Number.isFinite(nextValue) ? nextValue : 1;
  window.localStorage.setItem("pc-phone-link-mouse-speed", String(state.mouseSpeed));
  updateMouseSpeedLabel();
});
if (elements.streamFps) {
  elements.streamFps.addEventListener("input", (event) => setStreamFps(event.target.value, { persist: true }));
  elements.streamFps.addEventListener("change", (event) => setStreamFps(event.target.value, { persist: true, refresh: true }));
}
if (elements.streamWidth) {
  elements.streamWidth.addEventListener("change", (event) => setStreamWidth(event.target.value, { persist: true, refresh: true }));
}
if (elements.powerToggle && elements.powerMenu) {
  elements.powerToggle.addEventListener("click", () => togglePowerMenu());
  elements.powerMenu.querySelectorAll("[data-power-action]").forEach((button) => {
    button.addEventListener("click", () => {
      requestPowerAction(button.dataset.powerAction).catch((error) => showToast(error.message));
    });
  });
  document.addEventListener("pointerdown", (event) => {
    if (elements.powerMenu.classList.contains("hidden")) {
      return;
    }
    if (elements.powerMenu.contains(event.target) || elements.powerToggle.contains(event.target)) {
      return;
    }
    togglePowerMenu(false);
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
elements.controlMode.addEventListener("change", (event) => setControlMode(event.target.value));
elements.refreshTrustedDevices.addEventListener("click", () => refreshTrustedDevices().catch((error) => showToast(error.message)));
elements.followMouse.addEventListener("change", (event) => {
  state.followMouse = event.target.checked;
  window.localStorage.setItem("pc-phone-link-follow-mouse", String(state.followMouse));
  if (state.followMouse) {
    syncCameraToCursor();
  }
});
if (elements.restoreWindow) {
  elements.restoreWindow.addEventListener("click", () => restoreSelectedWindow().catch((error) => showToast(error.message)));
}
elements.toggleKeyboard.addEventListener("click", toggleKeyboardPanel);
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

window.addEventListener("resize", () => {
  syncViewportLayout();
  scheduleKeyboardComposerSync(60);
  if (state.selectedWindow) {
    refreshStream();
    applyCameraTransform();
    scheduleAutoPhoneFit("window-resize");
  }
});

if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", () => {
    syncViewportLayout();
    scheduleKeyboardComposerSync(60);
    if (state.selectedWindow) {
      refreshStream();
      applyCameraTransform();
      scheduleAutoPhoneFit("visual-viewport-resize");
    }
  });
  window.visualViewport.addEventListener("scroll", syncViewportLayout);
}

syncViewportLayout();
syncTargetActionButtons();
syncVoiceInputButton();
loadViewerPreferences();
loadMessageComposerState();
loadSavedToken();
renderTrustedDevices();
if (elements.controlBar) {
  elements.controlBar.hidden = false;
}
syncKeyboardComposerVisibility();
