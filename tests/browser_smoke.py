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
                            controls: ['rightClickMode','doubleClickMode','scrollUp','scrollDown','focusWindow','maximizeWindow','restoreWindow','fitShape','streamFps','streamWidth','textScale','refreshTrustedDevices','voiceInput','powerToggle','fitToggle','toggleKeyboard','toggleControls'].every(id => document.getElementById(id)) && document.querySelectorAll('[data-special-key]').length === 8,
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
                  const tapActions = calls.splice(0).map(item => item.action);

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
                  const prematureActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 21, 100, 200);
                  e('pointerdown', 22, 180, 200);
                  e('pointerup', 22, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
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
                  e('pointermove', 32, 183, 162);
                  const scrollModeAfterDrag = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleBeforeSeparation = state.cameraScale;
                  e('pointermove', 31, 63, 162);
                  const scrollModeAfterSeparation = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleAfterSeparation = state.cameraScale;
                  e('pointerup', 32, 183, 162);
                  const scrollActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 51, 100, 200);
                  e('pointerdown', 52, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  e('pointermove', 51, 100, 160);
                  e('pointermove', 52, 180, 160);
                  e('pointercancel', 52, 180, 160);
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
                  const twoFingerTapActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 5, 120, 220);
                  await new Promise(resolve => setTimeout(resolve, LONG_PRESS_DURATION_MS + 40));
                  e('pointerup', 5, 120, 220);
                  const longPressActions = calls.splice(0).map(item => item.action);

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
                  return { freshControls, legacyControls, savedControls, trackpadActions, touchModeStored, tapActions, panActions, panStartFocus, panEndFocus, boundedPanActions, boundedPanFocus, scaleOneActions, scaleOneFocus, scaleOneEndFocus, prematureMode, prematureActions, earlyReleaseActions, jitterArmed, readyStatus, readyHaptic, scrollActions, scrollModeAfterDrag, scrollModeAfterSeparation, scrollScaleBeforeSeparation, scrollScaleAfterSeparation, scrollCancelActions, scrollCancelState, pinchActions, pinchScale, pinchModeAfterSeparation, pinchModeAfterParallel, twoFingerTapActions, longPressActions, cancelActions, diagnosticEvents, diagnosticStates, diagnosticPointerTypes };
                })()""",
                await_promise=True,
            )
            assert gesture_report["freshControls"] == {"state": "touch", "stored": None, "select": "touch"}, gesture_report
            assert gesture_report["legacyControls"] == {"state": "touch", "stored": "mouse", "select": "touch"}, gesture_report
            assert gesture_report["savedControls"] == {"state": "trackpad", "stored": "trackpad", "select": "trackpad", "mouseSpeed": 3.4, "mouseSpeedInput": "3.4", "followMouse": True, "followMouseInput": True}, gesture_report
            assert gesture_report["trackpadActions"] == ["move_relative"], gesture_report
            assert gesture_report["touchModeStored"] == "touch", gesture_report
            assert gesture_report["tapActions"] == ["touch_tap"], gesture_report
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
            assert gesture_report["twoFingerTapActions"] == [], gesture_report
            assert gesture_report["longPressActions"] == ["touch_hold"], gesture_report
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
