const state = {
  token: null,
  controlUrl: null,
  controlStartConfigured: false,
  pollTimer: null,
  pollAttempts: 0,
  startingControls: false,
};

const elements = {
  authForm: document.getElementById("authForm"),
  authPanel: document.getElementById("authPanel"),
  authToken: document.getElementById("authToken"),
  checkStatus: document.getElementById("checkStatus"),
  controlHint: document.getElementById("controlHint"),
  openControls: document.getElementById("openControls"),
  startControls: document.getElementById("startControls"),
  statusPill: document.getElementById("statusPill"),
  toast: document.getElementById("toast"),
  wakeButton: document.getElementById("wakeButton"),
};

function setStatus(message) {
  elements.statusPill.textContent = message;
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

function updateStartButton() {
  elements.startControls.disabled = !state.controlStartConfigured || state.startingControls;
  elements.startControls.textContent = state.startingControls ? "Starting..." : "Start controls";
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
    throw new Error("Access code rejected.");
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

async function checkStatus() {
  if (!state.token) {
    return false;
  }

  const payload = await apiFetch("/api/control-status");
  state.controlStartConfigured = Boolean(payload.control_start_configured);
  updateControlLink(payload.control_url, payload.online);
  if (payload.online) {
    state.startingControls = false;
  }
  updateStartButton();

  if (payload.online) {
    setStatus("PC is ready");
    elements.controlHint.textContent = "The main PC Phone Link controls are online.";
    return true;
  }

  if (state.startingControls) {
    setStatus("Starting controls");
    elements.controlHint.textContent = "The relay asked the launcher to start the main control server.";
    return false;
  }

  if (payload.configured && state.controlStartConfigured) {
    setStatus("Controls are offline");
    elements.controlHint.textContent = "Wake the PC if needed, then tap Start controls whenever you want the main phone controls online.";
    return false;
  }

  if (payload.configured) {
    setStatus("PC is still waking");
    elements.controlHint.textContent = "When the PC answers again, this page can send you back to the main control screen.";
  } else {
    setStatus("Wake sent");
    elements.controlHint.textContent = state.controlStartConfigured
      ? "Wake packets are being sent. After the PC wakes, tap Start controls to bring the main phone controls online."
      : "Wake packets are being sent. Open your main PC Phone Link page after the PC finishes starting.";
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
          if (!online) {
            state.startingControls = false;
            updateStartButton();
          }
          stopPolling();
        }
      })
      .catch(() => {
        if (state.pollAttempts >= 30) {
          state.startingControls = false;
          updateStartButton();
          stopPolling();
          setStatus("Wake sent");
        }
      });
  }, 4000);
}

async function bootstrap() {
  const info = await apiFetch("/api/info");
  state.controlStartConfigured = Boolean(info.control_start_configured);
  updateStartButton();
  elements.controlHint.textContent = info.control_start_configured
    ? (
        info.control_url_configured
          ? "Wake the PC, then tap Start controls whenever you want the main phone controls online."
          : "This relay can wake the PC and request the control server to start, but you still need a control URL configured for the Open PC controls link."
      )
    : (
        info.control_url_configured
          ? "When the PC answers again, this page can send you back to the main control screen."
          : "This relay can wake the PC, but you still need to open your main control page manually if no control URL is configured."
      );
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

async function startControls() {
  if (!state.controlStartConfigured) {
    showToast("This relay is not configured to start the control server.");
    return;
  }

  state.startingControls = true;
  updateStartButton();
  setStatus("Starting controls");
  elements.controlHint.textContent = "Asking the launcher to start the main control server.";
  try {
    await apiFetch("/api/control-start", { method: "POST" });
  } catch (error) {
    state.startingControls = false;
    updateStartButton();
    throw error;
  }

  showToast("Start request sent.");
  if (state.controlUrl) {
    startPolling();
    return;
  }

  setStatus("Start requested");
  elements.controlHint.textContent = "The launcher accepted the start request. Open your configured control page when it becomes available.";
  state.startingControls = false;
  updateStartButton();
}

function loadSavedToken() {
  const urlToken = new URLSearchParams(window.location.search).get("token");
  const storedToken = window.localStorage.getItem("pc-phone-link-wake-token");
  const token = urlToken || storedToken;
  if (!token) {
    elements.authPanel.classList.remove("hidden");
    return;
  }

  state.token = token;
  elements.authToken.value = token;
  elements.authPanel.classList.add("hidden");
  window.localStorage.setItem("pc-phone-link-wake-token", token);

  if (urlToken) {
    window.history.replaceState({}, "", window.location.pathname);
  }

  bootstrap().catch((error) => {
    setStatus("Auth needed");
    showToast(error.message || "Connection failed.");
  });
}

elements.authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const token = elements.authToken.value.trim();
  if (!token) {
    return;
  }

  state.token = token;
  window.localStorage.setItem("pc-phone-link-wake-token", token);
  elements.authPanel.classList.add("hidden");
  try {
    await bootstrap();
  } catch (error) {
    setStatus("Auth needed");
    showToast(error.message || "Connection failed.");
  }
});

elements.wakeButton.addEventListener("click", () => {
  wakePc().catch((error) => showToast(error.message));
});

elements.startControls.addEventListener("click", () => {
  startControls().catch((error) => showToast(error.message));
});

elements.checkStatus.addEventListener("click", () => {
  checkStatus()
    .then((online) => {
      if (!online) {
        showToast(state.controlStartConfigured ? "The PC controls are not ready yet." : "The PC is not answering yet.");
      }
    })
    .catch((error) => showToast(error.message));
});

loadSavedToken();
