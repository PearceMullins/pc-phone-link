const state = {
  token: null,
  connectCode: null,
  connectInFlight: false,
  controlUrl: null,
  pollTimer: null,
  pollAttempts: 0,
};

const SESSION_TOKEN_STORAGE_KEY = "pc-phone-link-wake-token";

const elements = {
  authPanel: document.getElementById("authPanel"),
  checkStatus: document.getElementById("checkStatus"),
  connectButton: document.getElementById("connectButton"),
  connectCodeDisplay: document.getElementById("connectCodeDisplay"),
  connectStatus: document.getElementById("connectStatus"),
  controlHint: document.getElementById("controlHint"),
  openControls: document.getElementById("openControls"),
  statusPill: document.getElementById("statusPill"),
  toast: document.getElementById("toast"),
  wakeButton: document.getElementById("wakeButton"),
};

function setStatus(message) {
  elements.statusPill.textContent = message;
}

function setConnectStatus(message) {
  elements.connectStatus.textContent = message || "Confirm this code matches the wake relay terminal:";
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timerId);
  showToast.timerId = window.setTimeout(() => {
    elements.toast.classList.add("hidden");
  }, 2800);
}

function stopPolling() {
  if (state.pollTimer) {
    window.clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.pollAttempts = 0;
}

function updateControlLink(controlUrl, online) {
  state.controlUrl = controlUrl || null;
  if (state.controlUrl && online) {
    elements.openControls.href = state.controlUrl;
    elements.openControls.classList.remove("hidden");
    return;
  }
  elements.openControls.classList.add("hidden");
}

function syncConnectControls() {
  const code = state.connectCode || "----";
  if (elements.connectCodeDisplay) {
    elements.connectCodeDisplay.textContent = code;
  }
  if (elements.connectButton) {
    elements.connectButton.disabled = state.connectInFlight || !state.connectCode;
    elements.connectButton.textContent = state.connectInFlight ? "Connecting..." : `Connect · ${code}`;
  }
}

async function loadConnectInfo() {
  try {
    const response = await fetch("/api/connect-info");
    if (!response.ok) {
      throw new Error("Could not load the connect code from this relay.");
    }
    const payload = await response.json();
    state.connectCode = payload.connect_code || null;
    syncConnectControls();
    return Boolean(state.connectCode);
  } catch (error) {
    setConnectStatus(error.message || "Could not load the connect code from this relay.");
    syncConnectControls();
    return false;
  }
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
    throw new Error("Connect this phone to use the wake relay.");
  }

  if (!response.ok) {
    let message = "Request failed.";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json();
}

async function connectPhone() {
  if (state.connectInFlight) {
    return;
  }

  state.connectInFlight = true;
  setConnectStatus("Connecting to this relay...");
  syncConnectControls();
  try {
    const response = await fetch("/api/connect", { method: "POST" });
    if (!response.ok) {
      let message = "Connection failed.";
      try {
        const payload = await response.json();
        message = payload.detail || message;
      } catch {
        message = response.statusText || message;
      }
      throw new Error(message);
    }
    const payload = await response.json();
    if (!payload.session_token) {
      throw new Error("Connection failed.");
    }
    state.token = payload.session_token;
    window.localStorage.setItem(SESSION_TOKEN_STORAGE_KEY, payload.session_token);
    elements.authPanel.classList.add("hidden");
    await bootstrap();
    showToast("Connected to the wake relay.");
  } catch (error) {
    setConnectStatus("Confirm this code matches the wake relay terminal:");
    showToast(error.message || "Connection failed.");
    await loadConnectInfo();
  } finally {
    state.connectInFlight = false;
    syncConnectControls();
  }
}

async function checkStatus() {
  if (!state.token) {
    return false;
  }

  const payload = await apiFetch("/api/control-status");
  updateControlLink(payload.control_url, payload.online);

  if (payload.online) {
    setStatus("PC is ready");
    elements.controlHint.textContent = "The main PC Phone Link controls are online.";
    return true;
  }

  if (payload.configured) {
    setStatus("PC is still waking");
    elements.controlHint.textContent = "When the PC answers again, this page can send you back to the main control screen.";
  } else {
    setStatus("Wake sent");
    elements.controlHint.textContent = "Wake packets are being sent. Open your main PC Phone Link page after the PC finishes starting.";
  }
  return false;
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(() => {
    state.pollAttempts += 1;
    checkStatus()
      .then((online) => {
        if (online || state.pollAttempts >= 30) {
          stopPolling();
        }
      })
      .catch(() => {
        if (state.pollAttempts >= 30) {
          stopPolling();
          setStatus("Wake sent");
        }
      });
  }, 4000);
}

async function bootstrap() {
  const info = await apiFetch("/api/info");
  elements.controlHint.textContent = info.control_url_configured
    ? "When the PC answers again, this page can send you back to the main control screen."
    : "This relay can wake the PC, but you still need to open your main control page manually if no control URL is configured.";
  updateControlLink(info.control_url, false);

  if (info.control_url_configured) {
    try {
      await checkStatus();
    } catch {
      setStatus("Ready to wake");
    }
  } else {
    setStatus("Ready to wake");
  }
}

async function wakePc() {
  setStatus("Sending wake signal");
  await apiFetch("/api/wake", { method: "POST" });
  showToast("Wake signal sent.");

  if (state.controlUrl) {
    setStatus("Starting PC");
    startPolling();
    return;
  }

  setStatus("Wake sent");
}

function loadSavedToken() {
  const token = window.localStorage.getItem(SESSION_TOKEN_STORAGE_KEY);
  if (!token) {
    elements.authPanel.classList.remove("hidden");
    void loadConnectInfo();
    return;
  }

  state.token = token;
  elements.authPanel.classList.add("hidden");
  bootstrap().catch((error) => {
    state.token = null;
    window.localStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
    elements.authPanel.classList.remove("hidden");
    setStatus("Connect needed");
    showToast(error.message || "Connection failed.");
    void loadConnectInfo();
  });
}

elements.connectButton.addEventListener("click", () => connectPhone().catch((error) => showToast(error.message)));

elements.wakeButton.addEventListener("click", () => {
  wakePc().catch((error) => showToast(error.message));
});

elements.checkStatus.addEventListener("click", () => {
  checkStatus()
    .then((online) => {
      if (!online) {
        showToast("The PC is not answering yet.");
      }
    })
    .catch((error) => showToast(error.message));
});

loadSavedToken();
