const state = {
  token: null,
  controlUrl: null,
  pollTimer: null,
  pollAttempts: 0,
};

const elements = {
  authForm: document.getElementById("authForm"),
  authPanel: document.getElementById("authPanel"),
  authToken: document.getElementById("authToken"),
  checkStatus: document.getElementById("checkStatus"),
  controlHint: document.getElementById("controlHint"),
  deviceName: document.getElementById("deviceName"),
  openControls: document.getElementById("openControls"),
  startButton: document.getElementById("startButton"),
  statusPill: document.getElementById("statusPill"),
  toast: document.getElementById("toast"),
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

function syncActionState({ online, starting }) {
  elements.startButton.disabled = online || starting;
  elements.startButton.textContent = online
    ? "Controls running"
    : starting
      ? "Starting..."
      : "Start controls";
}

function applyLauncherState(payload) {
  if (payload.device_name) {
    elements.deviceName.textContent = payload.device_name;
  }

  const online = Boolean(payload.online);
  const starting = Boolean(payload.starting) && !online;
  updateControlLink(payload.control_url, online);
  syncActionState({ online, starting });

  if (online) {
    setStatus("Controls ready");
    elements.controlHint.textContent = "The main PC Phone Link server is running. Open it to start controlling the PC.";
    return;
  }

  if (payload.last_exit_code !== null && payload.last_exit_code !== undefined) {
    setStatus("Start failed");
    elements.controlHint.textContent = "The launcher could not keep the main server running. Check the launcher log on the PC, then try again.";
    return;
  }

  if (starting) {
    setStatus("Starting controls");
    elements.controlHint.textContent = "The launcher is starting the main PC Phone Link server on this PC.";
    return;
  }

  setStatus("Ready to start");
  elements.controlHint.textContent = "Tap Start controls to launch the main PC Phone Link server on this PC.";
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

async function checkStatus({ quiet = false } = {}) {
  if (!state.token) {
    return false;
  }

  const payload = await apiFetch("/api/status");
  applyLauncherState(payload);
  if (payload.online) {
    return true;
  }

  if (!quiet && payload.last_exit_code !== null && payload.last_exit_code !== undefined) {
    showToast("The host server did not stay running.");
  }
  return false;
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(() => {
    state.pollAttempts += 1;
    checkStatus({ quiet: true })
      .then((online) => {
        if (online) {
          stopPolling();
          showToast("PC controls are ready.");
          return;
        }
        if (state.pollAttempts >= 45) {
          stopPolling();
        }
      })
      .catch(() => {
        if (state.pollAttempts >= 45) {
          stopPolling();
        }
      });
  }, 2000);
}

async function bootstrap() {
  const info = await apiFetch("/api/info");
  applyLauncherState(info);
  if (info.starting) {
    startPolling();
  }
}

async function startControls() {
  setStatus("Starting controls");
  const payload = await apiFetch("/api/start", { method: "POST" });
  applyLauncherState(payload);

  if (payload.online) {
    showToast(payload.already_running ? "Controls are already running." : "PC controls are ready.");
    return;
  }

  showToast(payload.already_running ? "Controls are already running." : "Starting the PC controls server.");
  startPolling();
}

function loadSavedToken() {
  const urlToken = new URLSearchParams(window.location.search).get("token");
  const storedToken = window.localStorage.getItem("pc-phone-link-token");
  const token = urlToken || storedToken;
  if (!token) {
    elements.authPanel.classList.remove("hidden");
    return;
  }

  state.token = token;
  elements.authToken.value = token;
  elements.authPanel.classList.add("hidden");
  window.localStorage.setItem("pc-phone-link-token", token);

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
  window.localStorage.setItem("pc-phone-link-token", token);
  elements.authPanel.classList.add("hidden");
  try {
    await bootstrap();
  } catch (error) {
    setStatus("Auth needed");
    showToast(error.message || "Connection failed.");
  }
});

elements.startButton.addEventListener("click", () => {
  startControls().catch((error) => showToast(error.message));
});

elements.checkStatus.addEventListener("click", () => {
  checkStatus()
    .then((online) => {
      if (!online) {
        showToast("The PC controls are not ready yet.");
      }
    })
    .catch((error) => showToast(error.message));
});

loadSavedToken();
