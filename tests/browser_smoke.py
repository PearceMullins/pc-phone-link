"""Read-only Edge/CDP smoke test for mobile shell and gesture arbitration."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket


ROOT = Path(__file__).parents[1]
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
URL = "http://127.0.0.1:8877/"


class CDP:
    def __init__(self, socket_url: str) -> None:
        self.socket = websocket.create_connection(socket_url, origin="http://localhost", timeout=10)
        self.identifier = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.identifier += 1
        identifier = self.identifier
        self.socket.send(json.dumps({"id": identifier, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") != identifier:
                continue
            if "error" in message:
                raise AssertionError(f"CDP {method}: {message['error']}")
            return message.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = False) -> object:
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": await_promise,
                "returnByValue": True,
                "userGesture": True,
            },
        )["result"]
        if result.get("subtype") == "error":
            raise AssertionError(result.get("description"))
        return result.get("value")


def wait_json(url: str, timeout: float = 12) -> object:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.1)
    raise TimeoutError(url)


def main() -> None:
    assert EDGE.is_file(), f"Edge missing: {EDGE}"
    server = subprocess.Popen(
        [sys.executable, "run_phone_link.py", "--host", "127.0.0.1", "--port", "8877", "--no-gui"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    edge = None
    browser = None
    try:
        wait_json("http://127.0.0.1:8877/api/connect-info")
        with tempfile.TemporaryDirectory(prefix="phone-link-edge-", ignore_cleanup_errors=True) as profile:
            edge = subprocess.Popen(
                [
                    str(EDGE),
                    "--headless=new",
                    "--disable-gpu",
                    "--disable-background-networking",
                    "--no-first-run",
                    "--remote-allow-origins=*",
                    "--remote-debugging-port=9223",
                    f"--user-data-dir={profile}",
                    URL,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            targets = wait_json("http://127.0.0.1:9223/json")
            target = next(item for item in targets if item.get("type") == "page")
            browser = CDP(target["webSocketDebuggerUrl"])
            browser.call("Page.enable")
            browser.call("Runtime.enable")
            browser.call("Page.navigate", {"url": URL})
            deadline = time.monotonic() + 10
            while browser.evaluate("document.readyState === 'complete' && Boolean(document.getElementById('authPanel'))") is not True:
                assert time.monotonic() < deadline
                time.sleep(0.05)
            browser.evaluate("document.getElementById('authPanel').classList.add('hidden'); document.querySelectorAll('.mobile-panel').forEach(panel => panel.style.transition = 'none')")

            results: list[str] = []
            mobile_viewports = (
                (320, 800, False), (390, 844, False), (640, 360, False), (390, 844, True),
                (744, 1133, False), (1133, 744, False),
                (820, 1180, False), (1180, 820, False),
                (1024, 1366, False), (1366, 1024, False),
            )
            for width, height, standalone in mobile_viewports:
                browser.call(
                    "Emulation.setDeviceMetricsOverride",
                    {"width": width, "height": height, "deviceScaleFactor": 2, "mobile": True},
                )
                browser.call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
                browser.call(
                    "Emulation.setEmulatedMedia",
                    {"features": [{"name": "display-mode", "value": "standalone" if standalone else "browser"}]},
                )
                time.sleep(0.1)
                for destination in ("viewer", "windows", "keyboard", "controls", "settings"):
                    report = browser.evaluate(
                        f"""(() => {{
                          openDestination({destination!r});
                          const panel = {destination!r} === 'windows' ? elements.windowDrawer
                            : {destination!r} === 'controls' ? elements.controlsPanel
                            : {destination!r} === 'settings' ? elements.settingsPanel : null;
                          const nav = elements.mobileNav.getBoundingClientRect();
                          const viewer = elements.viewerShell.getBoundingClientRect();
                          const visible = panel ? panel.getBoundingClientRect() : null;
                          return {{
                            width: innerWidth,
                            coarsePointer: matchMedia('(pointer: coarse)').matches,
                            finePointer: matchMedia('(pointer: fine)').matches,
                            noHover: matchMedia('(hover: none)').matches,
                            canHover: matchMedia('(hover: hover)').matches,
                            mobileShell: usesMobileShell(),
                            rootOverflow: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - innerWidth,
                            navRight: nav.right,
                            navBottom: nav.bottom,
                            navTop: nav.top,
                            viewerBottom: viewer.bottom,
                            topbarDisplay: getComputedStyle(document.querySelector('.topbar')).display,
                            removedHeaderIds: ['toggleDrawer','deviceName','selectedWindowTitle'].every(id => !document.getElementById(id)),
                            panelLeft: visible?.left ?? 0,
                            panelRight: visible?.right ?? innerWidth,
                            panelOverflow: panel ? panel.scrollWidth - panel.clientWidth : 0,
                            keyboardOpen: !elements.keyboardPanel.classList.contains('hidden'),
                            controls: ['bottomNavEditor','bottomNavAdd','bottomNavReset','rightClickMode','doubleClickMode','scrollUp','scrollDown','focusWindow','maximizeWindow','restoreWindow','fitShape','streamFps','streamWidth','textScale','refreshTrustedDevices','voiceInput','powerToggle','fitToggle','toggleKeyboard','toggleControls'].every(id => document.getElementById(id)) && document.querySelectorAll('[data-special-key]').length === 8,
                            bottomActions: Array.from(elements.mobileNav.querySelectorAll('[data-bottom-action]')).map(button => button.dataset.bottomAction),
                            mandatoryEnabled: ['controls','settings'].every(id => !elements.mobileNav.querySelector(`[data-bottom-action="${id}"]`)?.disabled),
                            restoredMouseControls: ['controlMode','mouseSpeed','mouseSpeedValue','followMouse'].every(id => document.getElementById(id)) && Array.from(elements.controlMode.options).some(option => option.textContent === 'Mouse trackpad'),
                            removedModeBadge: !document.getElementById('controlModeBadge') && !document.querySelector('.viewer-status span'),
                          }};
                        }})()"""
                    )
                    assert report["width"] == width, report
                    assert report["mobileShell"] is True, report
                    assert report["rootOverflow"] <= 1, (width, height, destination, report)
                    assert report["navRight"] <= width + 1 and report["navBottom"] <= height + 1, report
                    assert report["topbarDisplay"] == "none", report
                    assert report["removedHeaderIds"], report
                    if destination == "viewer":
                        assert abs(report["viewerBottom"] - report["navTop"]) <= 1, report
                    assert report["panelLeft"] >= -1 and report["panelRight"] <= width + 1, report
                    assert report["panelOverflow"] <= 1, report
                    assert report["controls"], report
                    assert report["bottomActions"] == ["desktop", "windows", "keyboard", "controls", "settings"], report
                    assert report["mandatoryEnabled"], report
                    assert report["restoredMouseControls"], report
                    assert report["removedModeBadge"], report
                    assert report["keyboardOpen"] is (destination == "keyboard"), report
                power_report = browser.evaluate(
                    """(async () => {
                      openDestination('settings');
                      elements.settingsPowerToggle.click();
                      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                      const menu = elements.settingsPowerMenu.getBoundingClientRect();
                      const panel = elements.settingsPanel.getBoundingClientRect();
                      const buttons = Array.from(elements.settingsPowerMenu.querySelectorAll('[data-power-action]'));
                      const report = {
                        expanded: elements.settingsPowerToggle.getAttribute('aria-expanded'),
                        display: getComputedStyle(elements.settingsPowerMenu).display,
                        actions: buttons.map(button => button.dataset.powerAction),
                        dangerous: buttons.filter(button => button.classList.contains('power-menu-danger')).map(button => button.dataset.powerAction),
                        desktopMenuHidden: elements.powerMenu.classList.contains('hidden'),
                        left: menu.left, right: menu.right, top: menu.top, bottom: menu.bottom,
                        panelLeft: panel.left, panelRight: panel.right,
                        panelOverflow: elements.settingsPanel.scrollWidth - elements.settingsPanel.clientWidth,
                        restartConfirm: Boolean(POWER_ACTIONS.restart.confirm),
                        shutdownConfirm: Boolean(POWER_ACTIONS.shutdown.confirm),
                      };
                      openDestination('viewer');
                      report.closedAfterNavigation = elements.settingsPowerMenu.classList.contains('hidden')
                        && elements.settingsPowerToggle.getAttribute('aria-expanded') === 'false';
                      return report;
                    })()""",
                    await_promise=True,
                )
                assert power_report["expanded"] == "true" and power_report["display"] == "grid", power_report
                assert power_report["actions"] == ["lock", "sleep", "restart", "shutdown"], power_report
                assert power_report["dangerous"] == ["restart", "shutdown"], power_report
                assert power_report["restartConfirm"] and power_report["shutdownConfirm"], power_report
                assert power_report["desktopMenuHidden"], power_report
                assert power_report["closedAfterNavigation"], power_report
                assert power_report["left"] >= power_report["panelLeft"] - 1 and power_report["right"] <= power_report["panelRight"] + 1, power_report
                assert power_report["top"] >= -1 and power_report["bottom"] <= height + 1, (width, height, power_report)
                assert power_report["panelOverflow"] <= 1, power_report
                immersive = browser.evaluate("setControlsHidden(true); ({nav:getComputedStyle(elements.mobileNav).display,reveal:getComputedStyle(elements.revealControls).display})")
                assert immersive == {"nav": "none", "reveal": "block"}, immersive
                browser.evaluate("elements.revealControls.click()")
                assert browser.evaluate("getComputedStyle(elements.mobileNav).display") == "grid"
                image = browser.call("Page.captureScreenshot", {"format": "png"})["data"]
                assert len(image) > 5000
                results.append(f"{width}x{height}{'-standalone' if standalone else ''}")

            browser.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 1024, "height": 768, "deviceScaleFactor": 1, "mobile": False},
            )
            browser.call("Emulation.setTouchEmulationEnabled", {"enabled": False})
            desktop_report = browser.evaluate(
                "openDestination('viewer'); (() => { const drawer=elements.windowDrawer.getBoundingClientRect(); const header=document.querySelector('.topbar').getBoundingClientRect(); return {drawerWidth:drawer.width,drawerLeft:drawer.left,headerHeight:header.height,headerButtons:document.querySelectorAll('.topbar-actions > button').length,removed:['toggleDrawer','deviceName','selectedWindowTitle'].every(id=>!document.getElementById(id)),mobileShell:usesMobileShell(),navDisplay:getComputedStyle(elements.mobileNav).display}; })()"
            )
            assert desktop_report["drawerWidth"] > 300 and desktop_report["drawerLeft"] >= 0, desktop_report
            assert desktop_report["headerHeight"] > 0 and desktop_report["headerButtons"] >= 6, desktop_report
            assert desktop_report["removed"], desktop_report
            assert desktop_report["mobileShell"] is False and desktop_report["navDisplay"] == "none", desktop_report

            browser.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True},
            )
            browser.call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})

            selection_report = browser.evaluate(
                """(async () => {
                  const realApiFetch = apiFetch;
                  const realRefreshStream = refreshStream;
                  const oldToken = state.token;
                  const oldDiagnostics = state.gestureDiagnosticsEnabled;
                  const apiCalls = [];
                  const windowInfo = { hwnd: 777, title: 'Test', process_name: 'test.exe', bounds: { width: 1200, height: 800 }, cursor: { x: 0.5, y: 0.04, visible: true } };
                  apiFetch = async (path) => {
                    apiCalls.push(path);
                    if (path === '/api/windows') return { windows: [windowInfo] };
                    if (path === '/api/info') return { default_fps: 20, text_scale: 100 };
                    if (path === '/api/trusted-devices') return { devices: [] };
                    return { window: windowInfo };
                  };
                  refreshStream = () => {};
                  state.token = 'camera-invariant-test';
                  state.gestureDiagnosticsEnabled = false;
                  state.windows = [windowInfo];
                  state.followMouse = true;
                  openDestination('windows');
                  setCameraScale(2);
                  setCameraFocus(0.37, 0.74);
                  const before = { focus: { ...state.cameraFocus }, scale: state.cameraScale };
                  renderWindowList();
                  elements.windowList.querySelector('.window-card').click();
                  for (let attempt = 0; attempt < 20 && state.currentDestination !== 'viewer'; attempt += 1) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                  }
                  const report = {
                    destination: state.currentDestination,
                    windowsOpen: elements.windowDrawer.classList.contains('panel-open'),
                    drawerOpen: elements.windowDrawer.classList.contains('open'),
                    streamVisible: elements.remoteView.style.display,
                    before,
                    after: { focus: { ...state.cameraFocus }, scale: state.cameraScale },
                  };

                  setCameraScale(2.3);
                  setCameraFocus(0.31, 0.77);
                  const invariant = () => ({ focus: { ...state.cameraFocus }, scale: state.cameraScale });
                  const stable = invariant();
                  const checkpoints = [];
                  window.dispatchEvent(new Event('resize'));
                  checkpoints.push({ trigger: 'resize', camera: invariant() });
                  if (window.visualViewport) window.visualViewport.dispatchEvent(new Event('resize'));
                  checkpoints.push({ trigger: 'visualViewport', camera: invariant() });
                  openDestination('keyboard');
                  openDestination('viewer');
                  checkpoints.push({ trigger: 'keyboard', camera: invariant() });
                  state.streamParams = getStreamParams();
                  state.streamFallbackActive = true;
                  realRefreshStream();
                  checkpoints.push({ trigger: 'stream-refresh', camera: invariant() });
                  await refreshWindows();
                  checkpoints.push({ trigger: 'window-refresh', camera: invariant() });
                  await bootstrap({ quiet: true });
                  checkpoints.push({ trigger: 'bootstrap', camera: invariant() });
                  await new Promise(resolve => setTimeout(resolve, 300));
                  checkpoints.push({ trigger: 'timers', camera: invariant() });
                  handlePointerResponse({ cursor: { x: 0.5, y: 0.02, visible: true } }, 'click_current');
                  checkpoints.push({ trigger: 'passive-click-response', camera: invariant() });
                  handlePointerResponse({ cursor: { x: 0.82, y: 0.22, visible: true } }, 'move_relative');
                  report.explicitMouseFollow = invariant();
                  report.stable = stable;
                  report.checkpoints = checkpoints;
                  report.phoneFitCalls = apiCalls.filter(path => path.includes('/phone-fit'));
                  if (state.windowsRefreshTimer) {
                    clearInterval(state.windowsRefreshTimer);
                    state.windowsRefreshTimer = null;
                  }
                  apiFetch = realApiFetch;
                  refreshStream = realRefreshStream;
                  state.followMouse = false;
                  state.gestureDiagnosticsEnabled = oldDiagnostics;
                  state.token = oldToken;
                  state.selectedWindow = null;
                  state.windows = [];
                  resetViewer();
                  return report;
                })()""",
                await_promise=True,
            )
            assert selection_report["destination"] == "viewer" and selection_report["windowsOpen"] is False, selection_report
            assert selection_report["drawerOpen"] is False, selection_report
            assert selection_report["streamVisible"] == "block", selection_report
            assert selection_report["after"] == selection_report["before"], selection_report
            assert all(checkpoint["camera"] == selection_report["stable"] for checkpoint in selection_report["checkpoints"]), selection_report
            assert selection_report["explicitMouseFollow"]["focus"] == {"x": 0.82, "y": 0.22}, selection_report
            assert selection_report["explicitMouseFollow"]["scale"] == selection_report["stable"]["scale"], selection_report
            assert selection_report["phoneFitCalls"] == [], selection_report

            nav_report = browser.evaluate(
                """(async () => {
                  const realApiFetch = apiFetch;
                  const realRefreshStream = refreshStream;
                  const realRequestFullscreen = elements.app.requestFullscreen;
                  const apiCalls = [];
                  let fullscreenApiCalls = 0;
                  let desktopAvailable = true;
                  const desktop = { hwnd: -1, title: 'Full screen', process_name: 'desktop', is_desktop_capture: true, bounds: { width: 1920, height: 1080 } };
                  const appWindow = { hwnd: 777, title: 'App', process_name: 'app.exe', bounds: { width: 1200, height: 800 } };
                  elements.app.requestFullscreen = async () => { fullscreenApiCalls += 1; };
                  apiFetch = async (path) => {
                    apiCalls.push(path);
                    if (path === '/api/windows') return { windows: desktopAvailable ? [appWindow, desktop] : [] };
                    if (path === '/api/windows/-1/activate') return { window: desktop };
                    if (path === '/api/windows/777/activate') return { window: appWindow };
                    return { window: state.selectedWindow || appWindow };
                  };
                  refreshStream = () => {};
                  state.windows = [appWindow, desktop];
                  state.selectedWindow = null;
                  state.defaultDesktopHandled = false;
                  resetViewer();
                  await maybeSelectDefaultDesktopCapture();
                  const defaultDesktop = {
                    selected: state.selectedWindow?.is_desktop_capture === true,
                    hwnd: state.selectedWindow?.hwnd,
                    handled: state.defaultDesktopHandled === true,
                    destination: state.currentDestination,
                    activateCalls: apiCalls.filter(path => path === '/api/windows/-1/activate').length,
                  };
                  state.selectedWindow = null;
                  resetViewer();
                  await maybeSelectDefaultDesktopCapture();
                  const defaultDesktopOnce = {
                    stayedEmpty: state.selectedWindow === null,
                    activateCalls: apiCalls.filter(path => path === '/api/windows/-1/activate').length,
                  };
                  apiCalls.length = 0;
                  updateSelectedWindow(appWindow);
                  setCameraScale(2.1);
                  setCameraFocus(0.38, 0.69);
                  const cameraBeforeToggles = { scale: state.cameraScale, focus: { ...state.cameraFocus } };

                  localStorage.removeItem(BOTTOM_NAV_STORAGE_KEY);
                  loadBottomNavConfig();
                  const defaults = Array.from(elements.mobileNav.querySelectorAll('[data-bottom-action]')).map(button => button.dataset.bottomAction);
                  elements.mobileNav.querySelector('[data-bottom-action="desktop"]').click();
                  for (let attempt = 0; attempt < 20 && !state.selectedWindow?.is_desktop_capture; attempt += 1) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                  }
                  const desktopSelection = {
                    selected: state.selectedWindow?.is_desktop_capture === true,
                    hwnd: state.selectedWindow?.hwnd,
                    destination: state.currentDestination,
                    activateCalls: apiCalls.filter(path => path === '/api/windows/-1/activate').length,
                    fullscreenApiCalls,
                    active: elements.mobileNav.querySelector('[data-bottom-action="desktop"]').classList.contains('active'),
                  };
                  elements.mobileNav.querySelector('[data-bottom-action="desktop"]').click();
                  for (let attempt = 0; attempt < 20 && state.selectedWindow?.hwnd !== appWindow.hwnd; attempt += 1) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                  }
                  const desktopRestore = {
                    hwnd: state.selectedWindow?.hwnd,
                    destination: state.currentDestination,
                    appActivateCalls: apiCalls.filter(path => path === '/api/windows/777/activate').length,
                    active: elements.mobileNav.querySelector('[data-bottom-action="desktop"]').classList.contains('active'),
                    camera: { scale: state.cameraScale, focus: { ...state.cameraFocus } },
                  };
                  desktopAvailable = false;
                  state.windows = [];
                  await executeBottomNavAction('desktop');
                  const unavailableMessage = elements.toast.textContent;
                  desktopAvailable = true;
                  state.windows = [appWindow, desktop];
                  updateSelectedWindow(appWindow);

                  const panelVisible = (id) => id === 'windows'
                    ? elements.windowDrawer.classList.contains('panel-open')
                    : id === 'keyboard'
                      ? !elements.keyboardPanel.classList.contains('hidden')
                      : id === 'controls'
                        ? elements.controlsPanel.classList.contains('panel-open')
                        : elements.settingsPanel.classList.contains('panel-open');
                  const destinationToggles = {};
                  for (const id of ['windows', 'keyboard', 'controls', 'settings']) {
                    openDestination('viewer');
                    const tapDestination = () => elements.mobileNav.querySelector(`[data-bottom-action="${id}"]`).click();
                    tapDestination();
                    const shown = state.currentDestination === id && panelVisible(id)
                      && elements.mobileNav.querySelector(`[data-bottom-action="${id}"]`).getAttribute('aria-pressed') === 'true';
                    if (id === 'keyboard') elements.textInput.focus();
                    state.pointerDown = true;
                    state.pointerId = 900;
                    state.activePointers.set(900, { x: 20, y: 20 });
                    tapDestination();
                    const hidden = state.currentDestination === 'viewer'
                      && !elements.windowDrawer.classList.contains('panel-open')
                      && !elements.controlsPanel.classList.contains('panel-open')
                      && !elements.settingsPanel.classList.contains('panel-open')
                      && elements.keyboardPanel.classList.contains('hidden')
                      && state.pointerDown === false
                      && state.activePointers.size === 0
                      && state.pendingTap === null
                      && (id !== 'keyboard' || document.activeElement !== elements.textInput);
                    tapDestination();
                    const shownAgain = state.currentDestination === id && panelVisible(id);
                    tapDestination();
                    destinationToggles[id] = { shown, hidden, shownAgain };
                  }
                  const cameraAfterDestinationToggles = { scale: state.cameraScale, focus: { ...state.cameraFocus } };
                  const selectedAfterDestinationToggles = state.selectedWindow?.hwnd;

                  saveBottomNavConfig([]);
                  const mandatoryOnly = Array.from(elements.mobileNav.querySelectorAll('[data-bottom-action]')).map(button => ({
                    id: button.dataset.bottomAction,
                    disabled: button.disabled,
                  }));
                  const mandatoryEditorLocked = Array.from(elements.bottomNavEditor.querySelectorAll('.mandatory button')).every(button => button.disabled);

                  saveBottomNavConfig(['rightClick', 'gestureHelp']);
                  elements.bottomNavAdd.value = 'doubleClick';
                  elements.bottomNavAddButton.click();
                  elements.bottomNavEditor.querySelector('[data-shortcut-id="rightClick"][data-nav-editor-action="down"]').click();
                  const reordered = [...state.bottomNavOptional];
                  const customOverflow = {
                    nav: elements.mobileNav.scrollWidth - elements.mobileNav.clientWidth,
                    editor: elements.bottomNavEditor.scrollWidth - elements.bottomNavEditor.clientWidth,
                  };
                  elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').click();
                  const rightClickArmed = state.tapMode === 'right'
                    && elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').getAttribute('aria-pressed') === 'true';
                  elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').click();
                  const rightClickDisarmed = state.tapMode === 'left'
                    && elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').getAttribute('aria-pressed') === 'false';
                  elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').click();
                  const doubleClickArmed = state.tapMode === 'double'
                    && elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').getAttribute('aria-pressed') === 'true';
                  elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').click();
                  const doubleClickDisarmed = state.tapMode === 'left'
                    && elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').getAttribute('aria-pressed') === 'false';
                  elements.mobileNav.querySelector('[data-bottom-action="gestureHelp"]').click();
                  const gestureShown = elements.gestureHelp.open;
                  await executeBottomNavAction('gestureHelp');
                  const gestureHidden = !elements.gestureHelp.open;
                  await executeBottomNavAction('gestureHelp');
                  const gestureShownAgain = elements.gestureHelp.open;
                  await executeBottomNavAction('gestureHelp');
                  state.bottomNavOptional = [];
                  loadBottomNavConfig();
                  const persisted = [...state.bottomNavOptional];

                  localStorage.setItem(BOTTOM_NAV_STORAGE_KEY, JSON.stringify(['rightClick','bogus','rightClick','controls','doubleClick','fit','power']));
                  loadBottomNavConfig();
                  const sanitized = [...state.bottomNavOptional];
                  const storedSanitized = JSON.parse(localStorage.getItem(BOTTOM_NAV_STORAGE_KEY));

                  saveBottomNavConfig(['power']);
                  elements.mobileNav.querySelector('[data-bottom-action="power"]').click();
                  await new Promise(resolve => requestAnimationFrame(resolve));
                  const power = {
                    shown: state.currentDestination === 'settings'
                      && elements.settingsPowerToggle.getAttribute('aria-expanded') === 'true'
                      && !elements.settingsPowerMenu.classList.contains('hidden'),
                    powerRequests: apiCalls.filter(path => path === '/api/system/power').length,
                  };
                  elements.mobileNav.querySelector('[data-bottom-action="power"]').click();
                  power.hidden = state.currentDestination === 'viewer'
                    && elements.settingsPowerToggle.getAttribute('aria-expanded') === 'false'
                    && elements.settingsPowerMenu.classList.contains('hidden')
                    && !elements.settingsPanel.classList.contains('panel-open');
                  elements.mobileNav.querySelector('[data-bottom-action="power"]').click();
                  power.shownAgain = state.currentDestination === 'settings'
                    && elements.settingsPowerToggle.getAttribute('aria-expanded') === 'true'
                    && !elements.settingsPowerMenu.classList.contains('hidden');
                  elements.mobileNav.querySelector('[data-bottom-action="power"]').click();
                  const navOverflow = elements.mobileNav.scrollWidth - elements.mobileNav.clientWidth;
                  elements.bottomNavReset.click();
                  const reset = [...state.bottomNavOptional];
                  const storedReset = JSON.parse(localStorage.getItem(BOTTOM_NAV_STORAGE_KEY));

                  apiFetch = realApiFetch;
                  refreshStream = realRefreshStream;
                  elements.app.requestFullscreen = realRequestFullscreen;
                  state.selectedWindow = null;
                  state.defaultDesktopHandled = false;
                  state.windows = [];
                  resetViewer();
                  return { defaults, defaultDesktop, defaultDesktopOnce, desktopSelection, desktopRestore, cameraBeforeToggles, unavailableMessage, destinationToggles, cameraAfterDestinationToggles, selectedAfterDestinationToggles, mandatoryOnly, mandatoryEditorLocked, reordered, customOverflow, rightClickArmed, rightClickDisarmed, doubleClickArmed, doubleClickDisarmed, gestureShown, gestureHidden, gestureShownAgain, persisted, sanitized, storedSanitized, power, navOverflow, reset, storedReset };
                })()""",
                await_promise=True,
            )
            assert nav_report["defaults"] == ["desktop", "windows", "keyboard", "controls", "settings"], nav_report
            assert nav_report["defaultDesktop"] == {
                "selected": True,
                "hwnd": -1,
                "handled": True,
                "destination": "viewer",
                "activateCalls": 1,
            }, nav_report
            assert nav_report["defaultDesktopOnce"] == {"stayedEmpty": True, "activateCalls": 1}, nav_report
            assert nav_report["desktopSelection"] == {
                "selected": True,
                "hwnd": -1,
                "destination": "viewer",
                "activateCalls": 1,
                "fullscreenApiCalls": 0,
                "active": True,
            }, nav_report
            assert nav_report["desktopRestore"] == {
                "hwnd": 777,
                "destination": "viewer",
                "appActivateCalls": 1,
                "active": False,
                "camera": nav_report["cameraBeforeToggles"],
            }, nav_report
            assert "Full screen is unavailable" in nav_report["unavailableMessage"], nav_report
            assert all(value == {"shown": True, "hidden": True, "shownAgain": True} for value in nav_report["destinationToggles"].values()), nav_report
            assert nav_report["cameraAfterDestinationToggles"] == nav_report["cameraBeforeToggles"], nav_report
            assert nav_report["selectedAfterDestinationToggles"] == 777, nav_report
            assert nav_report["mandatoryOnly"] == [
                {"id": "controls", "disabled": False},
                {"id": "settings", "disabled": False},
            ], nav_report
            assert nav_report["mandatoryEditorLocked"], nav_report
            assert nav_report["reordered"] == ["gestureHelp", "rightClick", "doubleClick"], nav_report
            assert nav_report["customOverflow"]["nav"] <= 1 and nav_report["customOverflow"]["editor"] <= 1, nav_report
            assert nav_report["rightClickArmed"], nav_report
            assert nav_report["rightClickDisarmed"], nav_report
            assert nav_report["doubleClickArmed"], nav_report
            assert nav_report["doubleClickDisarmed"], nav_report
            assert nav_report["gestureShown"] and nav_report["gestureHidden"] and nav_report["gestureShownAgain"], nav_report
            assert nav_report["persisted"] == nav_report["reordered"], nav_report
            assert nav_report["sanitized"] == ["rightClick", "doubleClick", "fit"], nav_report
            assert nav_report["storedSanitized"] == nav_report["sanitized"], nav_report
            assert nav_report["power"] == {
                "shown": True,
                "powerRequests": 0,
                "hidden": True,
                "shownAgain": True,
            }, nav_report
            assert nav_report["navOverflow"] <= 1, nav_report
            assert nav_report["reset"] == ["desktop", "windows", "keyboard"] and nav_report["storedReset"] == nav_report["reset"], nav_report

            gesture_report = browser.evaluate(
                """(async () => {
                  const calls = [];
                  const haptics = [];
                  const realSendPointer = sendPointer;
                  const realRefreshStream = refreshStream;
                  const realHaptic = haptic;
                  sendPointer = (action, point = {}) => calls.push({ action, point });
                  refreshStream = () => {};
                  haptic = (pattern) => haptics.push(pattern);
                  viewerPointToSourceNormalized = (x, y) => ({ x: x / 1000, y: y / 1000 });
                  elements.touchLayer.setPointerCapture = () => {};
                  elements.touchLayer.releasePointerCapture = () => {};
                  elements.touchLayer.hasPointerCapture = () => false;
                  state.selectedWindow = { hwnd: 1 };
                  localStorage.removeItem(CONTROL_MODE_STORAGE_KEY);
                  state.controlMode = 'trackpad';
                  loadViewerPreferences();
                  const freshControls = {
                    state: state.controlMode,
                    stored: localStorage.getItem(CONTROL_MODE_STORAGE_KEY),
                    select: elements.controlMode.value,
                  };
                  localStorage.setItem(CONTROL_MODE_STORAGE_KEY, 'mouse');
                  state.controlMode = 'trackpad';
                  loadViewerPreferences();
                  const legacyControls = {
                    state: state.controlMode,
                    stored: localStorage.getItem(CONTROL_MODE_STORAGE_KEY),
                    select: elements.controlMode.value,
                  };
                  localStorage.setItem(CONTROL_MODE_STORAGE_KEY, 'trackpad');
                  localStorage.setItem('pc-phone-link-mouse-speed', '3.4');
                  localStorage.setItem('pc-phone-link-follow-mouse', 'true');
                  loadViewerPreferences();
                  const savedControls = {
                    state: state.controlMode,
                    stored: localStorage.getItem(CONTROL_MODE_STORAGE_KEY),
                    select: elements.controlMode.value,
                    mouseSpeed: state.mouseSpeed,
                    mouseSpeedInput: elements.mouseSpeed.value,
                    followMouse: state.followMouse,
                    followMouseInput: elements.followMouse.checked,
                  };
                  const e = (type, pointerId, clientX, clientY) => elements.touchLayer.dispatchEvent(new PointerEvent(type, {
                    pointerId, clientX, clientY, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));

                  e('pointerdown', 20, 120, 220);
                  e('pointermove', 20, 160, 250);
                  e('pointerup', 20, 160, 250);
                  const trackpadActions = calls.splice(0).map(item => item.action);
                  setControlMode('touch');
                  const touchModeStored = localStorage.getItem(CONTROL_MODE_STORAGE_KEY);

                  e('pointerdown', 10, 120, 220);
                  e('pointerup', 10, 120, 220);
                  const singleTapImmediateActions = calls.splice(0).map(item => item.action);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const singleTapActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 61, 120, 220);
                  e('pointerup', 61, 120, 220);
                  e('pointerdown', 62, 126, 225);
                  e('pointerup', 62, 126, 225);
                  const doubleTapActions = calls.splice(0).map(item => item.action);
                  const doubleTapStatus = elements.gestureStatus.textContent;
                  const doubleTapHaptic = haptics.at(-1);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const doubleTapDelayedActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 63, 120, 220);
                  e('pointerup', 63, 120, 220);
                  e('pointerdown', 64, 220, 320);
                  e('pointerup', 64, 220, 320);
                  const farTapImmediateActions = calls.splice(0).map(item => item.action);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const farTapDelayedActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 65, 120, 220);
                  e('pointerup', 65, 120, 220);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  e('pointerdown', 66, 124, 224);
                  e('pointerup', 66, 124, 224);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const lateTapActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 67, 120, 220);
                  e('pointerup', 67, 120, 220);
                  e('pointerdown', 68, 120, 220);
                  e('pointermove', 68, 180, 270);
                  e('pointerup', 68, 180, 270);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const pendingTapCanceledByDragActions = calls.splice(0).map(item => item.action);

                  setTapMode('double');
                  e('pointerdown', 69, 120, 220);
                  e('pointerup', 69, 120, 220);
                  const explicitDoubleActions = calls.splice(0).map(item => item.action);
                  const explicitDoubleModeAfterTap = state.tapMode;

                  const cancellationActions = {};
                  e('pointerdown', 70, 120, 220);
                  e('pointerup', 70, 120, 220);
                  openDestination('controls');
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.navigation = calls.splice(0).map(item => item.action);
                  openDestination('viewer');

                  e('pointerdown', 71, 120, 220);
                  e('pointerup', 71, 120, 220);
                  setControlMode('trackpad');
                  setControlMode('touch');
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.modeChange = calls.splice(0).map(item => item.action);

                  e('pointerdown', 72, 120, 220);
                  e('pointerup', 72, 120, 220);
                  updateSelectedWindow({ hwnd: 2 });
                  updateSelectedWindow({ hwnd: 1 });
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.windowChange = calls.splice(0).map(item => item.action);

                  e('pointerdown', 73, 120, 220);
                  e('pointerup', 73, 120, 220);
                  window.dispatchEvent(new Event('blur'));
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.blur = calls.splice(0).map(item => item.action);

                  e('pointerdown', 74, 120, 220);
                  e('pointerup', 74, 120, 220);
                  e('pointerdown', 75, 120, 220);
                  e('pointercancel', 75, 120, 220);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.pointerCancel = calls.splice(0).map(item => item.action);

                  e('pointerdown', 76, 120, 220);
                  e('pointerup', 76, 120, 220);
                  window.dispatchEvent(new Event('pagehide'));
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  cancellationActions.pagehide = calls.splice(0).map(item => item.action);

                  setCameraScale(2);
                  const panStartFocus = { ...state.cameraFocus };
                  e('pointerdown', 11, 120, 220);
                  e('pointermove', 11, 170, 260);
                  e('pointermove', 11, 200, 280);
                  e('pointerup', 11, 200, 280);
                  const panActions = calls.splice(0).map(item => item.action);
                  const panEndFocus = { ...state.cameraFocus };
                  setCameraFocus(0.01, 0.01);
                  e('pointerdown', 13, 100, 100);
                  e('pointermove', 13, 1000, 1000);
                  e('pointerup', 13, 1000, 1000);
                  const boundedPanActions = calls.splice(0).map(item => item.action);
                  const boundedPanFocus = { ...state.cameraFocus };
                  setCameraScale(1);
                  const scaleOneFocus = { ...state.cameraFocus };
                  e('pointerdown', 12, 120, 220);
                  e('pointermove', 12, 190, 270);
                  e('pointerup', 12, 190, 270);
                  const scaleOneActions = calls.splice(0).map(item => item.action);
                  const scaleOneEndFocus = { ...state.cameraFocus };

                  e('pointerdown', 1, 100, 200);
                  e('pointerdown', 2, 180, 200);
                  e('pointermove', 1, 100, 160);
                  e('pointermove', 2, 180, 160);
                  const prematureMode = state.twoFingerGesture?.mode ?? null;
                  e('pointerup', 2, 180, 160);
                  e('pointerup', 1, 100, 160);
                  const prematureActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 21, 100, 200);
                  e('pointerdown', 22, 180, 200);
                  e('pointerup', 22, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  e('pointerup', 21, 100, 200);
                  const earlyReleaseActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 31, 100, 200);
                  e('pointerdown', 32, 180, 200);
                  e('pointermove', 31, 103, 202);
                  e('pointermove', 32, 183, 202);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  const jitterArmed = state.twoFingerGesture?.scrollArmed === true;
                  const readyStatus = elements.gestureStatus.textContent;
                  const readyHaptic = haptics.at(-1);
                  e('pointermove', 31, 103, 162);
                  const scrollModeAfterDrag = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleBeforeSeparation = state.cameraScale;
                  e('pointermove', 31, 63, 162);
                  const scrollModeAfterSeparation = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleAfterSeparation = state.cameraScale;
                  e('pointerup', 32, 183, 202);
                  const scrollActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 51, 100, 200);
                  e('pointerdown', 52, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  e('pointermove', 51, 100, 160);
                  e('pointercancel', 52, 180, 200);
                  const scrollCancelActions = calls.splice(0).map(item => item.action);
                  const scrollCancelState = { gesture: state.twoFingerGesture, active: state.activePointers.size };

                  setCameraScale(1);
                  e('pointerdown', 3, 100, 200);
                  e('pointerdown', 4, 180, 200);
                  e('pointermove', 3, 60, 200);
                  const pinchModeAfterSeparation = state.twoFingerGesture?.mode ?? null;
                  e('pointermove', 3, 60, 150);
                  e('pointermove', 4, 180, 150);
                  const pinchModeAfterParallel = state.twoFingerGesture?.mode ?? null;
                  e('pointerup', 4, 180, 150);
                  const pinchActions = calls.splice(0).map(item => item.action);
                  const pinchScale = state.cameraScale;

                  e('pointerdown', 41, 100, 200);
                  e('pointerdown', 42, 180, 200);
                  e('pointerup', 42, 180, 200);
                  e('pointerup', 41, 100, 200);
                  const twoFingerTapActions = calls.splice(0).map(item => item.action);
                  const twoFingerTapStatus = elements.gestureStatus.textContent;
                  const twoFingerTapHaptic = haptics.at(-1);

                  e('pointerdown', 81, 100, 200);
                  e('pointerdown', 82, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_TAP_MAX_MS + 30));
                  e('pointerup', 82, 180, 200);
                  e('pointerup', 81, 100, 200);
                  const heldTwoFingerTapActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 5, 120, 220);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 300));
                  const heldFingerActions = calls.splice(0).map(item => item.action);
                  e('pointerup', 5, 120, 220);
                  await new Promise(resolve => setTimeout(resolve, DOUBLE_TAP_DELAY_MS + 30));
                  const heldThenReleasedActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 6, 120, 220);
                  e('pointermove', 6, 150, 250);
                  e('pointercancel', 6, 150, 250);
                  const cancelActions = calls.splice(0).map(item => item.action);
                  const diagnosticEvents = state.gestureLogBuffer.map(entry => entry.event);
                  const diagnosticStates = state.gestureLogBuffer.filter(entry => entry.event === 'gesture-state').map(entry => `${entry.details.gesture}:${entry.details.state}`);
                  const diagnosticPointerTypes = state.gestureLogBuffer.map(entry => entry.details.pointer_type).filter(Boolean);
                  sendPointer = realSendPointer;
                  refreshStream = realRefreshStream;
                  haptic = realHaptic;
                  state.selectedWindow = null;
                  resetViewer();
                  return { freshControls, legacyControls, savedControls, trackpadActions, touchModeStored, singleTapImmediateActions, singleTapActions, doubleTapActions, doubleTapStatus, doubleTapHaptic, doubleTapDelayedActions, farTapImmediateActions, farTapDelayedActions, lateTapActions, pendingTapCanceledByDragActions, explicitDoubleActions, explicitDoubleModeAfterTap, cancellationActions, panActions, panStartFocus, panEndFocus, boundedPanActions, boundedPanFocus, scaleOneActions, scaleOneFocus, scaleOneEndFocus, prematureMode, prematureActions, earlyReleaseActions, jitterArmed, readyStatus, readyHaptic, scrollActions, scrollModeAfterDrag, scrollModeAfterSeparation, scrollScaleBeforeSeparation, scrollScaleAfterSeparation, scrollCancelActions, scrollCancelState, pinchActions, pinchScale, pinchModeAfterSeparation, pinchModeAfterParallel, twoFingerTapActions, twoFingerTapStatus, twoFingerTapHaptic, heldTwoFingerTapActions, heldFingerActions, heldThenReleasedActions, cancelActions, diagnosticEvents, diagnosticStates, diagnosticPointerTypes };
                })()""",
                await_promise=True,
            )
            assert gesture_report["freshControls"] == {"state": "touch", "stored": None, "select": "touch"}, gesture_report
            assert gesture_report["legacyControls"] == {"state": "touch", "stored": "mouse", "select": "touch"}, gesture_report
            assert gesture_report["savedControls"] == {"state": "trackpad", "stored": "trackpad", "select": "trackpad", "mouseSpeed": 3.4, "mouseSpeedInput": "3.4", "followMouse": True, "followMouseInput": True}, gesture_report
            assert gesture_report["trackpadActions"] == ["move_relative"], gesture_report
            assert gesture_report["touchModeStored"] == "touch", gesture_report
            assert gesture_report["singleTapImmediateActions"] == [], gesture_report
            assert gesture_report["singleTapActions"] == ["touch_tap"], gesture_report
            assert gesture_report["doubleTapActions"] == ["touch_hold"], gesture_report
            assert gesture_report["doubleTapDelayedActions"] == [], gesture_report
            assert gesture_report["doubleTapStatus"] == "Right-click", gesture_report
            assert gesture_report["doubleTapHaptic"] == [18, 35, 18], gesture_report
            assert gesture_report["farTapImmediateActions"] == ["touch_tap"], gesture_report
            assert gesture_report["farTapDelayedActions"] == ["touch_tap"], gesture_report
            assert gesture_report["lateTapActions"] == ["touch_tap", "touch_tap"], gesture_report
            assert gesture_report["pendingTapCanceledByDragActions"] == [], gesture_report
            assert gesture_report["explicitDoubleActions"] == ["touch_double"], gesture_report
            assert gesture_report["explicitDoubleModeAfterTap"] == "left", gesture_report
            assert all(actions == [] for actions in gesture_report["cancellationActions"].values()), gesture_report
            assert gesture_report["panActions"] == [], gesture_report
            assert gesture_report["panEndFocus"]["x"] < gesture_report["panStartFocus"]["x"], gesture_report
            assert gesture_report["panEndFocus"]["y"] < gesture_report["panStartFocus"]["y"], gesture_report
            assert gesture_report["boundedPanActions"] == [], gesture_report
            assert gesture_report["boundedPanFocus"] == {"x": 0, "y": 0}, gesture_report
            assert gesture_report["scaleOneActions"] == [], gesture_report
            assert gesture_report["scaleOneEndFocus"] == gesture_report["scaleOneFocus"], gesture_report
            assert gesture_report["prematureMode"] is None and gesture_report["prematureActions"] == [], gesture_report
            assert gesture_report["earlyReleaseActions"] == [], gesture_report
            assert gesture_report["jitterArmed"] is True and gesture_report["readyStatus"] == "Scroll ready", gesture_report
            assert gesture_report["readyHaptic"] == [12, 24, 12], gesture_report
            assert gesture_report["scrollModeAfterDrag"] == "scroll" and gesture_report["scrollModeAfterSeparation"] == "scroll", gesture_report
            assert gesture_report["scrollScaleAfterSeparation"] == gesture_report["scrollScaleBeforeSeparation"], gesture_report
            assert gesture_report["scrollActions"][0] == "touch_down", gesture_report
            assert "touch_move" in gesture_report["scrollActions"] and gesture_report["scrollActions"][-1] == "touch_up", gesture_report
            assert gesture_report["scrollCancelActions"][0] == "touch_down" and gesture_report["scrollCancelActions"][-1] == "touch_cancel", gesture_report
            assert gesture_report["scrollCancelState"] == {"gesture": None, "active": 0}, gesture_report
            assert gesture_report["pinchModeAfterSeparation"] == "pinch" and gesture_report["pinchModeAfterParallel"] == "pinch", gesture_report
            assert gesture_report["pinchActions"] == [] and gesture_report["pinchScale"] > 1, gesture_report
            assert gesture_report["twoFingerTapActions"] == ["touch_double"], gesture_report
            assert gesture_report["twoFingerTapStatus"] == "Double-click", gesture_report
            assert gesture_report["twoFingerTapHaptic"] == [16, 30, 16], gesture_report
            assert gesture_report["heldTwoFingerTapActions"] == [], gesture_report
            assert gesture_report["heldFingerActions"] == [], gesture_report
            assert gesture_report["heldThenReleasedActions"] == ["touch_tap"], gesture_report
            assert gesture_report["cancelActions"] == [], gesture_report
            assert "gesture-classified" in gesture_report["diagnosticEvents"], gesture_report
            assert "two-finger-scroll:armed" in gesture_report["diagnosticStates"] and "two-finger-scroll:disarmed" in gesture_report["diagnosticStates"], gesture_report
            assert "touch" in gesture_report["diagnosticPointerTypes"], gesture_report
            error_report = browser.evaluate(
                "state.pointerDown=true; state.activePointers.set(99,{x:1,y:1}); handlePointerError(new Error('[Errno 87] Windows rejected native touch input.')); ({message:elements.toast.textContent,pointerDown:state.pointerDown,active:state.activePointers.size})"
            )
            assert "Lift all fingers" in error_report["message"], error_report
            assert error_report["pointerDown"] is False and error_report["active"] == 0, error_report
            browser_errors = browser.evaluate("state.gestureLogBuffer.filter(entry => entry.event === 'browser-error')")
            assert browser_errors == [], browser_errors
            print("Edge smoke: " + ", ".join(results) + "; gestures ok")
    finally:
        if browser:
            browser.socket.close()
        if edge:
            edge.terminate()
            try:
                edge.wait(timeout=5)
            except subprocess.TimeoutExpired:
                edge.kill()
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
