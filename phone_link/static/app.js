const state = {
  token: null,
  pairingRequestId: null,
  pairingRequestInFlight: false,
  pairingPhoneApproved: false,
  pairingPollTimer: null,
  selectedWindow: null,
  windows: [],
  mouseSpeed: 2.5,
  tapMode: "left",
  phoneFitEnabled: false,
  phoneFitOrientation: null,
  phoneFitViewportSize: null,
  pointerDown: false,
  dragActive: false,
  pointerId: null,
  startClientPoint: null,
  lastClientPoint: null,
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
  streamFps: 12,
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
const MESSAGE_HISTORY_STORAGE_KEY = "pc-phone-link-message-history";
const MESSAGE_DRAFT_STORAGE_KEY = "pc-phone-link-message-draft";
const MAX_MESSAGE_HISTORY = 100;
const MAX_VISIBLE_MESSAGE_HISTORY = 12;
const KEYBOARD_VISIBLE_HEIGHT_DELTA = 140;
const KEYBOARD_VISIBLE_HEIGHT_RATIO = 0.18;
const SECONDARY_TAP_MAX_DISTANCE = 18;
const SECONDARY_TAP_MAX_DURATION_MS = 320;

const elements = {
  app: document.getElementById("app"),
  applyTextScale: document.getElementById("applyTextScale"),
  authForm: document.getElementById("authForm"),
  authPanel: document.getElementById("authPanel"),
  approvePairing: document.getElementById("approvePairing"),
  clearTextInput: document.getElementById("clearTextInput"),
  controlBar: document.getElementById("controlBar"),
  deviceName: document.getElementById("deviceName"),
  doubleClickMode: document.getElementById("doubleClickMode"),
  emptyState: document.getElementById("emptyState"),
  fitToggle: document.getElementById("fitToggle"),
  focusWindow: document.getElementById("focusWindow"),
  followMouse: document.getElementById("followMouse"),
  keyboardPanel: document.getElementById("keyboardPanel"),
  maximizeWindow: document.getElementById("maximizeWindow"),
  messageHistory: document.getElementById("messageHistory"),
  messageHistorySection: document.getElementById("messageHistorySection"),
  mouseSpeed: document.getElementById("mouseSpeed"),
  mouseSpeedValue: document.getElementById("mouseSpeedValue"),
  pairingDeviceName: document.getElementById("pairingDeviceName"),
  pairingStatus: document.getElementById("pairingStatus"),
  refreshWindows: document.getElementById("refreshWindows"),
  remoteView: document.getElementById("remoteView"),
  requestPairing: document.getElementById("requestPairing"),
  restoreWindow: document.getElementById("restoreWindow"),
  rightClickMode: document.getElementById("rightClickMode"),
  scrollDown: document.getElementById("scrollDown"),
  scrollUp: document.getElementById("scrollUp"),
  selectedWindowTitle: document.getElementById("selectedWindowTitle"),
  sendText: document.getElementById("sendText"),
  statusPill: document.getElementById("statusPill"),
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

function viewerPointToSourceNormalized(clientX, clientY) {
  const viewerRect = elements.viewerShell.getBoundingClientRect();
  const displayed = getDisplayedImageRect();
  const localX = clientX - viewerRect.left;
  const localY = clientY - viewerRect.top;
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
  const clampedScale = Math.max(1, Math.min(nextScale, 4));
  state.cameraScale = clampedScale < 1.15 ? 1 : clampedScale;
  applyCameraTransform();
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
    elements.remoteView.style.transformOrigin = "0 0";
    elements.remoteView.style.transform = "none";
    return;
  }

  if (state.cameraScale === 1) {
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
    translateX = 0;
  }

  if (minTranslateY <= maxTranslateY) {
    translateY = Math.min(maxTranslateY, Math.max(minTranslateY, translateY));
  } else {
    translateY = 0;
  }

  elements.remoteView.style.transformOrigin = "0 0";
  elements.remoteView.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
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

  elements.mouseSpeed.value = String(state.mouseSpeed);
  elements.followMouse.checked = state.followMouse;
  updateMouseSpeedLabel();
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

function getDefaultPairingDeviceName() {
  const storedName = window.localStorage.getItem(PAIRING_DEVICE_NAME_STORAGE_KEY);
  if (storedName && storedName.trim()) {
    return storedName.trim();
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

function setPairingStatus(message) {
  elements.pairingStatus.textContent = message || "Send a connection request to this PC, then approve it on both devices to pair this browser.";
}

function stopPairingPolling() {
  if (!state.pairingPollTimer) {
    return;
  }
  window.clearInterval(state.pairingPollTimer);
  state.pairingPollTimer = null;
}

function clearPairingRequest({ message = null } = {}) {
  stopPairingPolling();
  state.pairingRequestId = null;
  state.pairingPhoneApproved = false;
  state.pairingRequestInFlight = false;
  if (message) {
    setPairingStatus(message);
  }
  syncPairingControls();
}

function syncPairingControls() {
  const hasPendingRequest = Boolean(state.pairingRequestId);
  elements.pairingDeviceName.disabled = hasPendingRequest || state.pairingRequestInFlight;
  elements.requestPairing.disabled = state.pairingRequestInFlight || hasPendingRequest;
  elements.requestPairing.textContent = state.pairingRequestInFlight ? "Sending request..." : "Send request";
  elements.approvePairing.disabled = state.pairingRequestInFlight || !hasPendingRequest || state.pairingPhoneApproved;
  elements.approvePairing.textContent = state.pairingPhoneApproved ? "Approved on this phone" : "Approve on this phone";
}

async function finishPairing(accessToken) {
  stopPairingPolling();
  state.pairingRequestId = null;
  state.pairingPhoneApproved = false;
  state.token = accessToken;
  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
  elements.authPanel.classList.add("hidden");
  syncPairingControls();
  const connected = await bootstrap({ quiet: true });
  if (!connected) {
    elements.authPanel.classList.remove("hidden");
  }
}

async function applyPairingResponse(response) {
  if (response?.pairing_id) {
    state.pairingRequestId = response.pairing_id;
  }
  state.pairingPhoneApproved = Boolean(response?.phone_approved);
  setPairingStatus(response?.message);

  if (response?.access_token) {
    await finishPairing(response.access_token);
    return true;
  }

  if (response?.status === "expired" || response?.status === "rejected") {
    clearPairingRequest({ message: response.message });
    return false;
  }

  syncPairingControls();
  return false;
}

async function pollPairingStatus({ quiet = true } = {}) {
  if (!state.pairingRequestId) {
    return false;
  }

  try {
    const response = await apiFetch(`/api/pairing/${encodeURIComponent(state.pairingRequestId)}`);
    return applyPairingResponse(response);
  } catch (error) {
    clearPairingRequest({ message: error.message });
    if (!quiet) {
      showToast(error.message || "Connection request failed.");
    }
    return false;
  }
}

function startPairingPolling() {
  stopPairingPolling();
  if (!state.pairingRequestId) {
    return;
  }
  state.pairingPollTimer = window.setInterval(() => {
    void pollPairingStatus();
  }, 1000);
}

async function requestPairing() {
  const deviceName = (elements.pairingDeviceName.value || getDefaultPairingDeviceName()).trim() || "This phone";
  elements.pairingDeviceName.value = deviceName;
  window.localStorage.setItem(PAIRING_DEVICE_NAME_STORAGE_KEY, deviceName);
  state.pairingRequestInFlight = true;
  setPairingStatus("Sending connection request to the PC.");
  syncPairingControls();
  try {
    const response = await apiFetch("/api/pairing/request", {
      method: "POST",
      body: JSON.stringify({ device_name: deviceName }),
    });
    const connected = await applyPairingResponse(response);
    if (!connected && state.pairingRequestId) {
      startPairingPolling();
    }
  } finally {
    state.pairingRequestInFlight = false;
    syncPairingControls();
  }
}

async function approvePairingOnPhone() {
  if (!state.pairingRequestId) {
    return;
  }

  state.pairingRequestInFlight = true;
  syncPairingControls();
  try {
    const response = await apiFetch(`/api/pairing/${encodeURIComponent(state.pairingRequestId)}/approve`, {
      method: "POST",
    });
    const connected = await applyPairingResponse(response);
    if (!connected && state.pairingRequestId) {
      startPairingPolling();
    }
  } finally {
    state.pairingRequestInFlight = false;
    syncPairingControls();
  }
}

function loadSavedToken() {
  elements.pairingDeviceName.value = getDefaultPairingDeviceName();
  setPairingStatus();
  syncPairingControls();

  const token = window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  if (!token) {
    elements.authPanel.classList.remove("hidden");
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
    state.streamFps = Math.max(1, Math.min(Number(info.default_fps) || 12, 12));
    if (typeof info.text_scale === "number" && Number.isFinite(info.text_scale)) {
      setTextScaleValue(info.text_scale, { confirmed: true });
    }
    elements.statusPill.textContent = "Trackpad ready";
    await refreshWindows();
    scheduleWindowRefresh();
    clearHostReconnectPolling();
    return true;
  } catch (error) {
    if (error.message === "Approve this phone on both devices to connect.") {
      state.token = null;
      window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
      elements.statusPill.textContent = "Approval needed";
      elements.authPanel.classList.remove("hidden");
      clearPairingRequest({
        message: "Send a connection request to this PC, then approve it on both devices to pair this browser.",
      });
    } else if (!quiet) {
      elements.statusPill.textContent = "Connection lost";
    }
    if (!quiet) {
      showToast(error.message || "Connection failed.");
    }
    return false;
  }
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
    throw new Error(await readErrorMessage(response, "Approve this phone on both devices to connect."));
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
  state.phoneFitViewportSize = state.phoneFitEnabled ? getViewerFitSize() : null;
  if (windowInfo.cursor) {
    updateCursorPosition(windowInfo.cursor, { allowMouseFollow: true });
  }
  elements.selectedWindowTitle.textContent = windowInfo.title;
  syncPhoneFitButton();
  syncTargetActionButtons();
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

function refreshStream() {
  if (!state.selectedWindow) {
    return;
  }

  const viewerRect = elements.viewerShell.getBoundingClientRect();
  const devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
  const width = Math.min(Math.max(Math.round(viewerRect.width * devicePixelRatio), 360), 680);
  const fps = Math.max(1, Math.min(state.streamFps || 12, 12));
  const streamUrl = `/api/windows/${state.selectedWindow.hwnd}/stream?token=${encodeURIComponent(state.token)}&width=${width}&fps=${fps}&t=${Date.now()}`;
  elements.remoteView.src = streamUrl;
  applyCameraTransform();
}

function resetViewer() {
  elements.selectedWindowTitle.textContent = "Open Windows to choose an app or fullscreen view";
  elements.remoteView.removeAttribute("src");
  elements.remoteView.style.display = "none";
  elements.emptyState.hidden = false;
  state.typingAnchor = null;
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
  elements.statusPill.textContent = state.selectedWindow ? "Trackpad ready" : "Ready";
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
      ? (state.selectedWindow ? "Trackpad ready" : "Ready")
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
    x: 0.5,
    y: 0.5,
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

  state.pointerDown = false;
  state.dragActive = false;
  state.pointerId = null;
  state.startClientPoint = null;
  state.lastClientPoint = null;
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

  if (!state.dragActive && (totalDeltaX > 4 || totalDeltaY > 4)) {
    state.dragActive = true;
  }

  state.lastClientPoint = {
    x: event.clientX,
    y: event.clientY,
  };
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
      sendPointer("right_click_current");
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

  state.pointerDown = false;
  state.dragActive = false;
  state.pointerId = null;
  state.startClientPoint = null;
  state.lastClientPoint = null;
  state.suppressPrimaryTapUp = false;
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

  state.pointerDown = false;
  state.dragActive = false;
  state.pointerId = null;
  state.startClientPoint = null;
  state.lastClientPoint = null;
  state.suppressPrimaryTapUp = false;
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
  writeClientLog(
    "phone-fit",
    "phone-fit-request",
    buildPhoneFitLogDetails({
      trigger,
      requestedViewportWidth: viewerSize.width,
      requestedViewportHeight: viewerSize.height,
    }),
  );
  let response;
  try {
    response = await apiFetch(`/api/windows/${state.selectedWindow.hwnd}/phone-fit`, {
      method: "POST",
      body: JSON.stringify({
        viewport_width: viewerSize.width,
        viewport_height: viewerSize.height,
      }),
    });
  } catch (error) {
    writeClientLog(
      "phone-fit",
      "phone-fit-error",
      buildPhoneFitLogDetails({
        trigger,
        requestedViewportWidth: viewerSize.width,
        requestedViewportHeight: viewerSize.height,
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
      requestedViewportWidth: viewerSize.width,
      requestedViewportHeight: viewerSize.height,
      responseWindow: summarizeWindowForLog(response.window || state.selectedWindow),
    }),
  );
  state.phoneFitEnabled = true;
  state.phoneFitOrientation = getViewportOrientation();
  state.phoneFitViewportSize = viewerSize;
  syncPhoneFitButton();
  refreshStream();
}

function scheduleAutoPhoneFit(trigger = "viewport-change") {
  if (!state.phoneFitEnabled || !state.selectedWindow || state.selectedWindow.is_desktop_capture) {
    return;
  }

  const nextViewerSize = getViewerFitSize();
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

elements.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await requestPairing();
  } catch (error) {
    showToast(error.message || "Connection failed.");
  }
});

elements.approvePairing.addEventListener("click", () => approvePairingOnPhone().catch((error) => showToast(error.message)));

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
elements.textScale.addEventListener("input", (event) => {
  scheduleTextScaleApply(event.target.value);
});
elements.textScale.addEventListener("change", (event) => {
  scheduleTextScaleApply(event.target.value, 0, { showSuccessToast: true });
});
elements.applyTextScale.addEventListener("click", () => applySelectedTextScale().catch((error) => showToast(error.message)));
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
if (elements.controlBar) {
  elements.controlBar.hidden = false;
}
syncKeyboardComposerVisibility();
