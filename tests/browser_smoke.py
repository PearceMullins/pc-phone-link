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
                for destination in ("viewer", "windows", "files", "keyboard", "shortcuts", "controls", "settings"):
                    report = browser.evaluate(
                        f"""(() => {{
                          if ({destination!r} === 'files') state.filesLoaded = true;
                          openDestination({destination!r});
                          if ({destination!r} === 'shortcuts') elements.shortcutMenu.scrollTop = elements.shortcutMenu.scrollHeight;
                          const panel = {destination!r} === 'windows' ? elements.windowDrawer
                            : {destination!r} === 'files' ? elements.filesPanel
                            : {destination!r} === 'shortcuts' ? elements.shortcutsPanel
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
                            controls: ['bottomNavEditor','bottomNavAdd','bottomNavReset','clickMode','rightClickMode','doubleClickMode','panMode','dragMode','scrollMode','zoomMode','scrollUp','scrollDown','focusWindow','maximizeWindow','restoreWindow','closeWindow','filesPanel','fileList','filePathInput','closeFiles','shortcutsPanel','shortcutMenu','activeShortcut','fitShape','streamFps','streamWidth','textScale','refreshTrustedDevices','voiceInput','powerToggle','fitToggle','toggleKeyboard','toggleControls','gameControls','gameInputStyle','gameUiSize','gameUiSizeValue','gameUiSizePreview','editGameLayout','resetGameLayout','doneGameLayout','resetGameLayoutOverlay','gamePad','gameJoystick','gameMouseJoystick','gameMouseJoystickKnob'].every(id => document.getElementById(id)) && document.querySelectorAll('[data-game-layout-group]').length === 3 && document.querySelectorAll('[data-game-mouse-button]').length === 3 && document.querySelectorAll('[data-special-key]').length === 8 && document.querySelectorAll('[data-pointer-shortcut]').length === 8 && Array.from(elements.controlMode.options).some(option => option.value === 'game'),
                            shortcutBottom: {destination!r} === 'shortcuts' ? elements.shortcutMenu.lastElementChild.getBoundingClientRect().bottom : 0,
                            bottomActions: Array.from(elements.mobileNav.querySelectorAll('[data-bottom-action]')).map(button => button.dataset.bottomAction),
                            mandatoryEnabled: ['shortcuts','controls','settings'].every(id => !elements.mobileNav.querySelector(`[data-bottom-action="${id}"]`)?.disabled),
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
                    if destination == "shortcuts":
                        assert report["shortcutBottom"] <= report["navTop"] + 1, report
                        assert report["shortcutBottom"] >= report["navTop"] - 20, report
                    assert report["controls"], report
                    assert report["bottomActions"] == ["desktop", "windows", "keyboard", "shortcuts", "controls", "settings"], report
                    assert report["mandatoryEnabled"], report
                    assert report["restoredMouseControls"], report
                    assert report["removedModeBadge"], report
                    assert report["keyboardOpen"] is (destination == "keyboard"), report
                game_responsive = browser.evaluate(
                    """(() => {
                      state.selectedWindow = { hwnd: 999, bounds: { width: 1280, height: 720 } };
                      openDestination('viewer');
                      setControlMode('game');
                      const viewer = elements.viewerShell.getBoundingClientRect();
                      const controls = elements.gameControls.getBoundingClientRect();
                      const movement = document.querySelector('.game-movement-control').getBoundingClientRect();
                      const mouse = document.querySelector('.game-mouse-stick-control').getBoundingClientRect();
                      const clicks = document.querySelector('.game-mouse-buttons-control').getBoundingClientRect();
                      const mouseStick = elements.gameMouseJoystick.getBoundingClientRect();
                      const minButton = Math.min(...Array.from(document.querySelectorAll('[data-game-mouse-button]'), button => button.getBoundingClientRect().height));
                      const savedScale = state.gameUiScale;
                      const savedLayout = JSON.parse(JSON.stringify(state.gameLayout));
                      state.gameUiScale = 1.35;
                      applyGameLayout();
                      const maxScaleReachable = [...document.querySelectorAll('[data-game-layout-group]')].every(group => {
                        const rect = group.getBoundingClientRect();
                        return rect.left >= viewer.left - 1 && rect.right <= viewer.right + 1
                          && rect.top >= viewer.top - 1 && rect.bottom <= viewer.bottom + 1;
                      });
                      state.gameUiScale = savedScale;
                      state.gameLayout = savedLayout;
                      applyGameLayout();
                      const result = {
                        visible: !elements.gameControls.classList.contains('hidden'),
                        left: controls.left, right: controls.right, bottom: controls.bottom,
                        viewerLeft: viewer.left, viewerRight: viewer.right, viewerBottom: viewer.bottom,
                        separated: movement.right <= mouse.left + 1 && movement.right <= clicks.left + 1,
                        groupsReachable: [movement, mouse, clicks].every(group => group.left >= viewer.left - 1 && group.right <= viewer.right + 1 && group.top >= viewer.top - 1 && group.bottom <= viewer.bottom + 1),
                        maxScaleReachable,
                        mouseStickWidth: mouseStick.width,
                        minButton,
                        overflow: elements.viewerShell.scrollWidth - elements.viewerShell.clientWidth,
                      };
                      setControlMode('touch');
                      state.selectedWindow = null;
                      resetViewer();
                      return result;
                    })()"""
                )
                assert game_responsive["visible"], (width, height, game_responsive)
                assert game_responsive["left"] >= game_responsive["viewerLeft"] - 1, game_responsive
                assert game_responsive["right"] <= game_responsive["viewerRight"] + 1, game_responsive
                assert game_responsive["bottom"] <= game_responsive["viewerBottom"] + 1, game_responsive
                assert game_responsive["separated"] and game_responsive["groupsReachable"] and game_responsive["maxScaleReachable"] and game_responsive["overflow"] <= 1, game_responsive
                assert game_responsive["mouseStickWidth"] >= 95 and game_responsive["minButton"] >= 36, game_responsive
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

            game_layout = browser.evaluate(
                """(() => {
                  window.__gameRealApiFetch = apiFetch;
                  window.__gameRealRefreshStream = refreshStream;
                  window.__gameRealToken = state.token;
                  window.__gameCalls = [];
                  window.__gameMouseCalls = [];
                  apiFetch = async (path, options = {}) => {
                    if (path.includes('/game-key')) {
                      window.__gameCalls.push({ path, payload: JSON.parse(options.body) });
                      return { ok: true, applied: true };
                    }
                    if (path.includes('/pointer')) {
                      window.__gameMouseCalls.push({ path, payload: JSON.parse(options.body) });
                      return { ok: true, cursor: { x: 0.5, y: 0.5, visible: true } };
                    }
                    return {};
                  };
                  state.token = 'game-test-token';
                  state.gestureSessionId = 'game-test-session';
                  refreshStream = () => {};
                  if (state.streamRefreshTimer) {
                    clearTimeout(state.streamRefreshTimer);
                    state.streamRefreshTimer = null;
                  }
                  closeStreamSocket();
                  updateSelectedWindow({ hwnd: 444, bounds: { width: 1280, height: 720 } });
                  openDestination('viewer');
                  setGameInputStyle('pad');
                  setControlMode('game');
                  const viewer = elements.viewerShell.getBoundingClientRect();
                  const controls = elements.gameControls.getBoundingClientRect();
                  const w = document.querySelector('[data-game-key="w"]').getBoundingClientRect();
                  const mouse = elements.gameMouseJoystick.getBoundingClientRect();
                  return {
                    visible: !elements.gameControls.classList.contains('hidden'),
                    mode: elements.controlMode.value,
                    style: elements.gameInputStyle.value,
                    touchDisabled: getComputedStyle(elements.touchLayer).pointerEvents,
                    viewer: { left: viewer.left, right: viewer.right, top: viewer.top, bottom: viewer.bottom },
                    controls: { left: controls.left, right: controls.right, top: controls.top, bottom: controls.bottom },
                    mouse: { left: mouse.left, right: mouse.right, top: mouse.top, bottom: mouse.bottom },
                    mouseButtons: document.querySelectorAll('[data-game-mouse-button]').length,
                    w: { x: w.left + w.width / 2, y: w.top + w.height / 2 },
                  };
                })()"""
            )
            assert game_layout["visible"] and game_layout["mode"] == "game" and game_layout["style"] == "pad", game_layout
            assert game_layout["touchDisabled"] == "none", game_layout
            assert game_layout["controls"]["left"] >= game_layout["viewer"]["left"] - 1, game_layout
            assert game_layout["controls"]["right"] <= game_layout["viewer"]["right"] + 1, game_layout
            assert game_layout["controls"]["bottom"] <= game_layout["viewer"]["bottom"] + 1, game_layout
            assert game_layout["mouseButtons"] == 3, game_layout
            assert game_layout["mouse"]["right"] <= game_layout["viewer"]["right"] + 1, game_layout
            browser.call(
                "Input.dispatchMouseEvent",
                {
                    "type": "mousePressed", "x": game_layout["w"]["x"], "y": game_layout["w"]["y"],
                    "button": "left", "buttons": 1, "clickCount": 1,
                },
            )
            time.sleep(0.05)
            browser.call(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseReleased", "x": game_layout["w"]["x"], "y": game_layout["w"]["y"],
                    "button": "left", "buttons": 0, "clickCount": 1,
                },
            )
            time.sleep(0.05)
            real_game_touch = browser.evaluate(
                "({calls:window.__gameCalls.map(item=>`${item.payload.action}:${item.payload.key}`),held:[...state.gameHeldKeys],pointers:state.gamePadPointers.size})"
            )
            assert real_game_touch["held"] == [] and real_game_touch["pointers"] == 0, real_game_touch
            assert real_game_touch["calls"] in ([], ["down:w", "up:w"]), real_game_touch

            game_report = browser.evaluate(
                """(async () => {
                  const calls = window.__gameCalls;
                  const mouseCalls = window.__gameMouseCalls;
                  const captureTargets = [
                    ...document.querySelectorAll('[data-game-key], [data-game-mouse-button]'),
                    elements.gameJoystick,
                    elements.gameMouseJoystick,
                  ];
                  captureTargets.forEach(target => { target.setPointerCapture = () => {}; });
                  calls.length = 0;
                  mouseCalls.length = 0;
                  const pointer = (target, type, id, x = 10, y = 10) => target.dispatchEvent(new PointerEvent(type, {
                    pointerId: id, clientX: x, clientY: y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  const drain = async () => {
                    await state.gameKeyQueue.catch(() => null);
                    await state.gameMouseClickQueue.catch(() => null);
                    for (let attempt = 0; attempt < 20 && state.gameMouseMoveInFlight; attempt += 1) {
                      await new Promise(resolve => setTimeout(resolve, 0));
                    }
                    await new Promise(resolve => setTimeout(resolve, 0));
                  };
                  const key = name => document.querySelector(`[data-game-key="${name}"]`);

                  pointer(key('w'), 'pointerdown', 401);
                  pointer(key('d'), 'pointerdown', 402);
                  pointer(key('w'), 'pointerup', 401);
                  pointer(key('d'), 'pointercancel', 402);
                  await drain();
                  const padActions = calls.splice(0).map(item => `${item.payload.action}:${item.payload.key}`);
                  const padReleased = state.gameHeldKeys.size === 0 && state.gamePadPointers.size === 0;

                  setGameInputStyle('joystick');
                  const mouseAvailableWithMovementJoystick = !elements.gameMouseJoystick.classList.contains('hidden')
                    && getComputedStyle(elements.gameMouseJoystick).display !== 'none';
                  const rect = elements.gameJoystick.getBoundingClientRect();
                  const cx = rect.left + rect.width / 2;
                  const cy = rect.top + rect.height / 2;
                  pointer(elements.gameJoystick, 'pointerdown', 410, cx + rect.width * 0.35, cy - rect.height * 0.35);
                  pointer(elements.gameJoystick, 'pointermove', 410, cx - rect.width * 0.35, cy + rect.height * 0.35);
                  pointer(elements.gameJoystick, 'lostpointercapture', 410, cx, cy);
                  await drain();
                  const joystickActions = calls.splice(0).map(item => `${item.payload.action}:${item.payload.key}`);
                  const joystickReleased = state.gameHeldKeys.size === 0
                    && state.gameJoystickPointerId === null
                    && state.gameJoystickKeys.size === 0;

                  const mouseRect = elements.gameMouseJoystick.getBoundingClientRect();
                  const mouseX = mouseRect.left + mouseRect.width / 2;
                  const mouseY = mouseRect.top + mouseRect.height / 2;
                  pointer(elements.gameJoystick, 'pointerdown', 411, cx + rect.width * 0.35, cy - rect.height * 0.35);
                  pointer(elements.gameMouseJoystick, 'pointerdown', 412, mouseX - mouseRect.width * 0.35, mouseY + mouseRect.height * 0.3);
                  await new Promise(resolve => setTimeout(resolve, 90));
                  const dualJoystickActive = state.gameHeldKeys.has('w')
                    && state.gameHeldKeys.has('d')
                    && state.gameMousePointerId === 412
                    && state.gameMouseVector.x < 0
                    && state.gameMouseVector.y > 0;
                  pointer(elements.gameMouseJoystick, 'pointerup', 412, mouseX, mouseY);
                  pointer(elements.gameJoystick, 'pointerup', 411, cx, cy);
                  await drain();
                  const dualJoystickKeyActions = calls.splice(0).map(item => `${item.payload.action}:${item.payload.key}`);
                  const dualJoystickMouseMoves = mouseCalls.splice(0).filter(item => item.payload.action === 'move_relative').length;

                  setGameInputStyle('pad');
                  const mouseButton = name => document.querySelector(`[data-game-mouse-button="${name}"]`);
                  pointer(key('w'), 'pointerdown', 430);
                  pointer(elements.gameMouseJoystick, 'pointerdown', 431, mouseX + mouseRect.width * 0.38, mouseY - mouseRect.height * 0.3);
                  await new Promise(resolve => setTimeout(resolve, 100));
                  const simultaneousSnapshot = {
                    held: [...state.gameHeldKeys],
                    mousePointer: state.gameMousePointerId,
                    mouseX: state.gameMouseVector.x,
                    mouseY: state.gameMouseVector.y,
                    mode: state.controlMode,
                    destination: state.currentDestination,
                    keyCalls: calls.map(item => `${item.payload.action}:${item.payload.reason}`),
                  };
                  const simultaneousActive = simultaneousSnapshot.held.includes('w')
                    && simultaneousSnapshot.mousePointer === 431
                    && simultaneousSnapshot.mouseX > 0
                    && simultaneousSnapshot.mouseY < 0;
                  for (const [index, name] of ['left', 'middle', 'right'].entries()) {
                    pointer(mouseButton(name), 'pointerdown', 440 + index);
                    pointer(mouseButton(name), 'pointerup', 440 + index);
                  }
                  await drain();
                  pointer(elements.gameMouseJoystick, 'pointerup', 431, mouseX, mouseY);
                  pointer(key('w'), 'pointerup', 430);
                  await drain();
                  const simultaneousKeyActions = calls.splice(0).map(item => `${item.payload.action}:${item.payload.key}`);
                  const mouseActions = mouseCalls.splice(0).map(item => item.payload.action);
                  const mouseReleased = state.gameMousePointerId === null
                    && state.gameMouseVector.magnitude === 0
                    && state.gameMouseFrame === null
                    && state.pendingGameMouseMove === null
                    && state.gameMouseClickPointers.size === 0;

                  pointer(mouseButton('middle'), 'pointerdown', 448);
                  pointer(mouseButton('middle'), 'pointercancel', 448);
                  pointer(mouseButton('right'), 'pointerdown', 449);
                  pointer(mouseButton('right'), 'lostpointercapture', 449);
                  await drain();
                  const canceledClickActions = mouseCalls.splice(0).map(item => item.payload.action);
                  const canceledClicksReleased = state.gameMouseClickPointers.size === 0;

                  pointer(elements.gameMouseJoystick, 'pointerdown', 450, mouseX + mouseRect.width * 0.4, mouseY);
                  pointer(elements.gameMouseJoystick, 'pointercancel', 450, mouseX, mouseY);
                  const pointerCancelReleased = state.gameMousePointerId === null && state.gameMouseFrame === null;
                  pointer(elements.gameMouseJoystick, 'pointerdown', 451, mouseX, mouseY - mouseRect.height * 0.4);
                  pointer(elements.gameMouseJoystick, 'lostpointercapture', 451, mouseX, mouseY);
                  const lostCaptureReleased = state.gameMousePointerId === null && state.gameMouseFrame === null;

                  pointer(key('a'), 'pointerdown', 420);
                  pointer(elements.gameMouseJoystick, 'pointerdown', 452, mouseX + mouseRect.width * 0.4, mouseY);
                  pointer(mouseButton('left'), 'pointerdown', 453);
                  window.dispatchEvent(new Event('blur'));
                  await drain();
                  const blurActions = calls.splice(0).map(item => item.payload.action);
                  const blurReleased = state.gameHeldKeys.size === 0
                    && state.gameMousePointerId === null
                    && state.gameMouseClickPointers.size === 0
                    && state.gameMouseFrame === null;

                  pointer(key('s'), 'pointerdown', 421);
                  pointer(elements.gameMouseJoystick, 'pointerdown', 454, mouseX, mouseY + mouseRect.height * 0.4);
                  openDestination('controls');
                  await drain();
                  const destinationActions = calls.splice(0).map(item => item.payload.action);
                  const destinationReleased = state.gameHeldKeys.size === 0 && state.gameMousePointerId === null;

                  openDestination('viewer');
                  setControlMode('game');
                  pointer(elements.gameMouseJoystick, 'pointerdown', 455, mouseX + mouseRect.width * 0.4, mouseY);
                  setControlMode('touch');
                  const modeReleased = state.gameMousePointerId === null && state.gameMouseFrame === null;
                  setControlMode('game');

                  pointer(elements.gameMouseJoystick, 'pointerdown', 456, mouseX + mouseRect.width * 0.4, mouseY);
                  Object.defineProperty(document, 'visibilityState', { configurable: true, value: 'hidden' });
                  document.dispatchEvent(new Event('visibilitychange'));
                  delete document.visibilityState;
                  const visibilityReleased = state.gameMousePointerId === null && state.gameMouseFrame === null;

                  pointer(elements.gameMouseJoystick, 'pointerdown', 457, mouseX + mouseRect.width * 0.4, mouseY);
                  setConnectionStatus('Offline', false);
                  const disconnectReleased = state.gameMousePointerId === null && state.gameMouseFrame === null;
                  setConnectionStatus('Connected', true);

                  pointer(key('d'), 'pointerdown', 422);
                  pointer(elements.gameMouseJoystick, 'pointerdown', 458, mouseX + mouseRect.width * 0.4, mouseY);
                  updateSelectedWindow({ hwnd: 445, bounds: { width: 1280, height: 720 } });
                  await drain();
                  const targetActions = calls.splice(0).map(item => item.payload.action);
                  const targetReleased = state.gameHeldKeys.size === 0 && state.gameMousePointerId === null;

                  const mouseStableApiFetch = apiFetch;
                  apiFetch = async (path, options = {}) => {
                    if (path.includes('/pointer')) throw new Error('simulated mouse transport loss');
                    return mouseStableApiFetch(path, options);
                  };
                  pointer(elements.gameMouseJoystick, 'pointerdown', 459, mouseX + mouseRect.width * 0.4, mouseY);
                  await new Promise(resolve => setTimeout(resolve, 90));
                  await drain();
                  const mouseErrorReleased = state.gameMousePointerId === null
                    && state.gameMouseFrame === null
                    && state.pendingGameMouseMove === null;
                  apiFetch = mouseStableApiFetch;

                  setControlMode('game');
                  setGameInputStyle('pad');
                  const stableApiFetch = apiFetch;
                  apiFetch = async (path, options = {}) => {
                    if (!path.includes('/game-key')) return {};
                    const payload = JSON.parse(options.body);
                    calls.push({ path, payload });
                    if (payload.action === 'up') throw new Error('simulated transport loss');
                    return { ok: true, applied: true };
                  };
                  pointer(key('w'), 'pointerdown', 423);
                  await drain();
                  pointer(key('w'), 'pointerup', 423);
                  await drain();
                  const errorActions = calls.splice(0).map(item => item.payload.action);
                  const errorReleased = state.gameHeldKeys.size === 0 && state.gamePadPointers.size === 0;
                  apiFetch = stableApiFetch;

                  localStorage.setItem(CONTROL_MODE_STORAGE_KEY, 'game');
                  localStorage.setItem(GAME_INPUT_STYLE_STORAGE_KEY, 'joystick');
                  loadViewerPreferences();
                  const persisted = {
                    mode: state.controlMode,
                    style: state.gameInputStyle,
                    selectMode: elements.controlMode.value,
                    selectStyle: elements.gameInputStyle.value,
                  };

                  setControlMode('touch');
                  state.selectedWindow = null;
                  resetViewer();
                  apiFetch = window.__gameRealApiFetch;
                  refreshStream = window.__gameRealRefreshStream;
                  state.token = window.__gameRealToken;
                  delete window.__gameRealApiFetch;
                  delete window.__gameRealRefreshStream;
                  delete window.__gameRealToken;
                  delete window.__gameCalls;
                  delete window.__gameMouseCalls;
                  captureTargets.forEach(target => { delete target.setPointerCapture; });
                  localStorage.removeItem(CONTROL_MODE_STORAGE_KEY);
                  localStorage.removeItem(GAME_INPUT_STYLE_STORAGE_KEY);
                  return {
                    padActions, padReleased, joystickActions, joystickReleased,
                    mouseAvailableWithMovementJoystick, dualJoystickActive, dualJoystickKeyActions, dualJoystickMouseMoves,
                    simultaneousSnapshot, simultaneousActive, simultaneousKeyActions, mouseActions, mouseReleased,
                    canceledClickActions, canceledClicksReleased,
                    pointerCancelReleased, lostCaptureReleased,
                    blurActions, blurReleased, destinationActions, destinationReleased,
                    modeReleased, visibilityReleased, disconnectReleased,
                    targetActions, targetReleased, mouseErrorReleased, errorActions, errorReleased, persisted,
                  };
                })()""",
                await_promise=True,
            )
            assert game_report["padActions"] == ["down:w", "down:d", "up:w", "up:d"], game_report
            assert game_report["padReleased"], game_report
            assert game_report["joystickActions"] == [
                "down:w", "down:d", "up:w", "up:d", "down:a", "down:s", "up:a", "up:s",
            ], game_report
            assert game_report["joystickReleased"], game_report
            assert game_report["mouseAvailableWithMovementJoystick"], game_report
            assert game_report["dualJoystickActive"], game_report
            assert game_report["dualJoystickKeyActions"] == ["down:w", "down:d", "up:w", "up:d"], game_report
            assert game_report["dualJoystickMouseMoves"] >= 1, game_report
            assert game_report["simultaneousActive"], game_report
            assert game_report["simultaneousKeyActions"] == ["down:w", "up:w"], game_report
            assert game_report["mouseActions"].count("move_relative") >= 1, game_report
            assert [action for action in game_report["mouseActions"] if action != "move_relative"] == [
                "click_current", "middle_click_current", "right_click_current",
            ], game_report
            assert game_report["mouseReleased"], game_report
            assert game_report["canceledClickActions"] == [] and game_report["canceledClicksReleased"], game_report
            assert game_report["pointerCancelReleased"] and game_report["lostCaptureReleased"], game_report
            assert sorted(game_report["blurActions"]) == ["down", "release_all"], game_report
            assert game_report["blurReleased"], game_report
            assert game_report["destinationActions"] == ["down", "release_all"], game_report
            assert game_report["destinationReleased"], game_report
            assert game_report["modeReleased"] and game_report["visibilityReleased"], game_report
            assert game_report["disconnectReleased"], game_report
            assert game_report["targetActions"] == ["down", "release_all"], game_report
            assert game_report["targetReleased"], game_report
            assert game_report["mouseErrorReleased"], game_report
            assert game_report["errorActions"] == ["down", "up", "release_all"], game_report
            assert game_report["errorReleased"], game_report
            assert game_report["persisted"] == {
                "mode": "game", "style": "joystick", "selectMode": "game", "selectStyle": "joystick",
            }, game_report

            game_layout_edit = browser.evaluate(
                """(async () => {
                  window.__layoutRealApiFetch = apiFetch;
                  window.__layoutRealRefreshStream = refreshStream;
                  window.__layoutOldToken = state.token;
                  const calls = [];
                  apiFetch = async (path, options = {}) => {
                    if (path.includes('/game-key') || path.includes('/pointer')) calls.push({ path, body: options.body });
                    return { ok: true, applied: true, cursor: { x: 0.5, y: 0.5, visible: true } };
                  };
                  state.token = 'layout-test-token';
                  state.gestureSessionId = 'layout-test-session';
                  refreshStream = () => {};
                  closeStreamSocket();
                  localStorage.removeItem(GAME_UI_SCALE_STORAGE_KEY);
                  localStorage.removeItem(GAME_LAYOUT_STORAGE_KEY);
                  state.gameLayout = window.PCPhoneLinkGameControls.defaultGameLayout();
                  setGameUiScale(1);
                  updateSelectedWindow({ hwnd: 446, bounds: { width: 1280, height: 720 } });
                  openDestination('viewer');
                  setGameInputStyle('joystick');
                  setControlMode('game');
                  syncGameControlsUi();
                  const movement = document.querySelector('[data-game-layout-group="movement"]');
                  const handle = movement.querySelector('.game-layout-handle');
                  movement.setPointerCapture = () => {};
                  const initialWidth = movement.getBoundingClientRect().width;

                  elements.gameUiSize.value = '125';
                  elements.gameUiSize.dispatchEvent(new Event('input', { bubbles: true }));
                  const scaledWidth = movement.getBoundingClientRect().width;
                  const scaleStored = Number(localStorage.getItem(GAME_UI_SCALE_STORAGE_KEY));
                  const previewScale = elements.gameUiSizePreview.style.getPropertyValue('--game-ui-preview-scale');

                  setGameLayoutEditing(true, { openViewer: false });
                  const fire = (target, type, id, x, y) => target.dispatchEvent(new PointerEvent(type, {
                    pointerId: id, clientX: x, clientY: y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  let rect = movement.getBoundingClientRect();
                  fire(handle, 'pointerdown', 701, rect.left + rect.width / 2, rect.top + 4);
                  fire(handle, 'pointermove', 701, -500, -500);
                  fire(handle, 'pointerup', 701, -500, -500);
                  rect = movement.getBoundingClientRect();
                  const container = elements.gameControls.getBoundingClientRect();
                  const clamped = rect.left >= container.left - 1 && rect.top >= container.top - 1
                    && rect.right <= container.right + 1 && rect.bottom <= container.bottom + 1;
                  const persistedMove = JSON.parse(localStorage.getItem(GAME_LAYOUT_STORAGE_KEY)).portrait.movement;

                  const w = document.querySelector('[data-game-key="w"]');
                  const wRect = w.getBoundingClientRect();
                  fire(w, 'pointerdown', 702, wRect.left + wRect.width / 2, wRect.top + wRect.height / 2);
                  fire(w, 'pointerup', 702, wRect.left + wRect.width / 2, wRect.top + wRect.height / 2);
                  await new Promise(resolve => setTimeout(resolve, 0));
                  const inputSuppressed = calls.length === 0 && state.gameHeldKeys.size === 0;
                  const handlesVisible = [...document.querySelectorAll('.game-layout-handle')]
                    .every(item => getComputedStyle(item).display !== 'none');

                  state.gameLayout.portrait = {
                    movement: { x: 0, y: 0 }, mouse: { x: 1, y: 0 }, clicks: { x: 1, y: 1 },
                  };
                  state.gameLayout.landscape = {
                    movement: { x: 0, y: 1 }, mouse: { x: 1, y: 0 }, clicks: { x: 1, y: 1 },
                  };
                  saveGameLayout();
                  applyGameLayout({ persistClamp: true });
                  return {
                    initialWidth, scaledWidth, scaleStored, previewScale,
                    value: elements.gameUiSizeValue.textContent,
                    editing: state.gameLayoutEditing,
                    handlesVisible, clamped, persistedMove, inputSuppressed,
                    orientation: currentGameLayoutOrientation(),
                    storedHasBoth: ['portrait', 'landscape'].every(key => Boolean(JSON.parse(localStorage.getItem(GAME_LAYOUT_STORAGE_KEY))[key])),
                  };
                })()""",
                await_promise=True,
            )
            assert game_layout_edit["scaledWidth"] > game_layout_edit["initialWidth"] * 1.2, game_layout_edit
            assert game_layout_edit["scaleStored"] == 1.25 and game_layout_edit["previewScale"] == "1.25", game_layout_edit
            assert game_layout_edit["value"] == "125%" and game_layout_edit["editing"], game_layout_edit
            assert game_layout_edit["handlesVisible"] and game_layout_edit["clamped"] and game_layout_edit["inputSuppressed"], game_layout_edit
            assert game_layout_edit["storedHasBoth"] and game_layout_edit["orientation"] == "portrait", game_layout_edit
            assert 0 <= game_layout_edit["persistedMove"]["x"] <= 1 and 0 <= game_layout_edit["persistedMove"]["y"] <= 1, game_layout_edit

            browser.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 640, "height": 360, "deviceScaleFactor": 2, "mobile": True},
            )
            time.sleep(0.1)
            rotated_game_layout = browser.evaluate(
                """(() => {
                  syncViewportLayout();
                  syncGameControlsUi();
                  const container = elements.gameControls.getBoundingClientRect();
                  const groups = [...document.querySelectorAll('[data-game-layout-group]')].map(group => {
                    const rect = group.getBoundingClientRect();
                    return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
                  });
                  return {
                    orientation: currentGameLayoutOrientation(),
                    reachable: groups.every(rect => rect.left >= container.left - 1 && rect.top >= container.top - 1
                      && rect.right <= container.right + 1 && rect.bottom <= container.bottom + 1),
                    groups,
                  };
                })()"""
            )
            assert rotated_game_layout["orientation"] == "landscape" and rotated_game_layout["reachable"], rotated_game_layout

            browser.call(
                "Emulation.setDeviceMetricsOverride",
                {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True},
            )
            time.sleep(0.1)
            game_layout_reset = browser.evaluate(
                """(async () => {
                  syncViewportLayout();
                  syncGameControlsUi();
                  elements.resetGameUiSize.click();
                  elements.resetGameLayoutOverlay.click();
                  elements.doneGameLayout.click();
                  const fire = (target, type, id, x, y) => target.dispatchEvent(new PointerEvent(type, {
                    pointerId: id, clientX: x, clientY: y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  const movementRect = elements.gameJoystick.getBoundingClientRect();
                  const mouseRect = elements.gameMouseJoystick.getBoundingClientRect();
                  fire(elements.gameJoystick, 'pointerdown', 711,
                    movementRect.left + movementRect.width * 0.82, movementRect.top + movementRect.height * 0.18);
                  fire(elements.gameMouseJoystick, 'pointerdown', 712,
                    mouseRect.left + mouseRect.width * 0.18, mouseRect.top + mouseRect.height * 0.82);
                  const simultaneousAfterEdit = state.gameHeldKeys.has('w') && state.gameHeldKeys.has('d')
                    && state.gameMousePointerId === 712 && state.gameMouseVector.x < 0 && state.gameMouseVector.y > 0;
                  fire(elements.gameMouseJoystick, 'pointercancel', 712, mouseRect.left, mouseRect.top);
                  fire(elements.gameJoystick, 'pointercancel', 711, movementRect.left, movementRect.top);
                  await state.gameKeyQueue.catch(() => null);
                  const defaults = window.PCPhoneLinkGameControls.defaultGameLayout();
                  const stored = JSON.parse(localStorage.getItem(GAME_LAYOUT_STORAGE_KEY));
                  const result = {
                    layoutReset: JSON.stringify(stored) === JSON.stringify(defaults),
                    sizeReset: state.gameUiScale === 1 && elements.gameUiSizeValue.textContent === '100%',
                    editFinished: !state.gameLayoutEditing && !elements.gameControls.classList.contains('editing'),
                    simultaneousAfterEdit,
                    releasedAfterEdit: state.gameHeldKeys.size === 0 && state.gameMousePointerId === null,
                  };
                  setControlMode('touch');
                  state.selectedWindow = null;
                  resetViewer();
                  apiFetch = window.__layoutRealApiFetch;
                  refreshStream = window.__layoutRealRefreshStream;
                  state.token = window.__layoutOldToken;
                  delete window.__layoutRealApiFetch;
                  delete window.__layoutRealRefreshStream;
                  delete window.__layoutOldToken;
                  localStorage.removeItem(GAME_UI_SCALE_STORAGE_KEY);
                  localStorage.removeItem(GAME_LAYOUT_STORAGE_KEY);
                  return result;
                })()""",
                await_promise=True,
            )
            assert all(game_layout_reset.values()), game_layout_reset

            browser.evaluate(
                """(() => {
                  window.__realTouchActions = [];
                  window.__realTouchEvents = [];
                  window.__realTouchSendPointer = sendPointer;
                  window.__realTouchViewerPoint = viewerPointToSourceNormalized;
                  window.__realTouchHandler = event => window.__realTouchEvents.push({
                    type: event.type,
                    pointerType: event.pointerType,
                    pointerId: event.pointerId,
                    defaultPrevented: event.defaultPrevented,
                  });
                  for (const type of ['pointerdown','pointermove','pointerup','pointercancel']) {
                    elements.touchLayer.addEventListener(type, window.__realTouchHandler);
                  }
                  sendPointer = (action, payload = {}) => window.__realTouchActions.push({ action, payload });
                  viewerPointToSourceNormalized = (x, y) => ({ x: x / 390, y: y / 844 });
                  state.selectedWindow = { hwnd: 1 };
                  openDestination('viewer');
                })()"""
            )

            def dispatch_real_drag(mode: str) -> dict:
                browser.evaluate(
                    f"window.__realTouchActions.length=0; window.__realTouchEvents.length=0; setCameraScale({1 if mode == 'pan' else 2}); setCameraFocus(0.5,0.5); setGestureArm({mode!r});"
                )
                browser.call(
                    "Input.dispatchTouchEvent",
                    {"type": "touchStart", "touchPoints": [{"x": 195, "y": 320, "id": 1, "radiusX": 5, "radiusY": 5, "force": 1}]},
                )
                browser.call(
                    "Input.dispatchTouchEvent",
                    {"type": "touchMove", "touchPoints": [{"x": 195, "y": 250, "id": 1, "radiusX": 5, "radiusY": 5, "force": 1}]},
                )
                browser.call(
                    "Input.dispatchTouchEvent",
                    {"type": "touchMove", "touchPoints": [{"x": 195, "y": 180, "id": 1, "radiusX": 5, "radiusY": 5, "force": 1}]},
                )
                browser.call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
                time.sleep(0.05)
                return browser.evaluate(
                    "({events:[...window.__realTouchEvents],actions:window.__realTouchActions.map(item=>item.action),camera:{scale:state.cameraScale,focus:{...state.cameraFocus}},mode:state.gestureArm,pointerDown:state.pointerDown,active:state.activePointers.size})"
                )

            real_touch_report = {mode: dispatch_real_drag(mode) for mode in ("scroll", "drag", "pan", "zoom")}
            browser.evaluate(
                """(() => {
                  for (const type of ['pointerdown','pointermove','pointerup','pointercancel']) {
                    elements.touchLayer.removeEventListener(type, window.__realTouchHandler);
                  }
                  sendPointer = window.__realTouchSendPointer;
                  viewerPointToSourceNormalized = window.__realTouchViewerPoint;
                  state.selectedWindow = null;
                  setGestureArm('gestures');
                })()"""
            )
            for mode, report in real_touch_report.items():
                assert [event["type"] for event in report["events"]] == ["pointerdown", "pointermove", "pointermove", "pointerup"], (mode, report)
                assert report["mode"] == mode and report["pointerDown"] is False and report["active"] == 0, (mode, report)
            assert real_touch_report["scroll"]["actions"] == ["wheel_current", "wheel_current"], real_touch_report
            assert real_touch_report["drag"]["actions"] == ["down", "move", "move", "up"], real_touch_report
            assert real_touch_report["pan"]["actions"] == [] and real_touch_report["pan"]["camera"]["scale"] >= 2, real_touch_report
            assert real_touch_report["zoom"]["actions"] == [] and real_touch_report["zoom"]["camera"]["scale"] > 2, real_touch_report

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
                  elements.windowList.querySelector('.window-card-select').click();
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

            files_report = browser.evaluate(
                """(async () => {
                  const realApiFetch = apiFetch;
                  const realConfirm = window.confirm;
                  const calls = [];
                  const appWindow = { hwnd: 888, title: 'File Explorer', process_name: 'explorer.exe', bounds: { width: 1000, height: 700 } };
                  apiFetch = async (path) => {
                    calls.push(path);
                    if (path === '/api/files') return {
                      path: null, parent: null, breadcrumbs: [], truncated: false,
                      entries: [{ name: 'Demo', path: 'C:/Demo', is_directory: true, is_location: true }],
                    };
                    if (path.startsWith('/api/files?')) return {
                      path: 'C:/Demo', parent: 'C:/', breadcrumbs: [{ name: 'C:', path: 'C:/' }, { name: 'Demo', path: 'C:/Demo' }], truncated: false,
                      entries: [{ name: 'report.txt', path: 'C:/Demo/report.txt', is_directory: false, size: 2048, modified_at: '2026-08-12T12:00:00Z' }],
                    };
                    if (path === '/api/files/reveal') return { ok: true };
                    if (path === '/api/windows/888/close') return { ok: true };
                    if (path === '/api/windows') return { windows: [appWindow] };
                    return {};
                  };
                  window.confirm = () => true;
                  state.filesLoaded = false;
                  state.filesEntries = [];
                  state.filesPath = null;
                  openDestination('files');
                  for (let attempt = 0; attempt < 30 && !state.filesLoaded; attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  const root = {
                    destination: state.currentDestination,
                    panelOpen: elements.filesPanel.classList.contains('panel-open'),
                    rows: elements.fileList.querySelectorAll('.file-entry').length,
                  };
                  elements.fileList.querySelector('.file-entry-main').click();
                  for (let attempt = 0; attempt < 30 && state.filesPath !== 'C:/Demo'; attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  const folder = {
                    path: state.filesPath,
                    address: elements.filePathInput.value,
                    rows: elements.fileList.querySelectorAll('.file-entry').length,
                    upEnabled: !elements.fileUp.disabled,
                  };
                  elements.fileList.querySelector('.file-entry-main').click();
                  for (let attempt = 0; attempt < 30 && !calls.includes('/api/files/reveal'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  elements.closeFiles.click();
                  const closedPanel = state.currentDestination === 'viewer' && !elements.filesPanel.classList.contains('panel-open');

                  state.windows = [appWindow];
                  renderWindowList();
                  elements.windowList.querySelector('.window-close-button').click();
                  for (let attempt = 0; attempt < 30 && !calls.includes('/api/windows/888/close'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  await new Promise(resolve => setTimeout(resolve, 400));
                  const close = {
                    call: calls.includes('/api/windows/888/close'),
                    confirmText: true,
                    closeButton: Boolean(elements.windowList.querySelector('.window-close-button')),
                  };
                  apiFetch = realApiFetch;
                  window.confirm = realConfirm;
                  state.windows = [];
                  state.filesEntries = [];
                  state.filesLoaded = false;
                  renderWindowList();
                  renderFileBrowser();
                  return { root, folder, closedPanel, revealed: calls.includes('/api/files/reveal'), close };
                })()""",
                await_promise=True,
            )
            assert files_report["root"] == {"destination": "files", "panelOpen": True, "rows": 1}, files_report
            assert files_report["folder"] == {"path": "C:/Demo", "address": "C:/Demo", "rows": 1, "upEnabled": True}, files_report
            assert files_report["revealed"] and files_report["closedPanel"], files_report
            assert files_report["close"] == {"call": True, "confirmText": True, "closeButton": True}, files_report

            apps_report = browser.evaluate(
                """(async () => {
                  const realApiFetch = apiFetch;
                  const calls = [];
                  const appWindow = { hwnd: 889, title: 'File Explorer', process_name: 'explorer.exe', bounds: { width: 1000, height: 700 } };
                  apiFetch = async (path, options = {}) => {
                    calls.push(path);
                    if (path === '/api/apps') return {
                      apps: [
                        { id: 'a1', name: 'Notepad', target: 'C:/Windows/notepad.exe', source: 'Start Menu', icon_url: '/api/apps/icon?id=a1', running_hwnd: null, running_title: '' },
                        { id: 'a2', name: 'Calculator', target: 'C:/Windows/calc.exe', source: 'Start Menu', icon_url: '/api/apps/icon?id=a2', running_hwnd: 889, running_title: 'File Explorer' },
                      ],
                      quick_actions: [
                        { id: 'show_desktop', label: 'Show desktop', icon: 'D' },
                        { id: 'run_dialog', label: 'Run dialog', icon: 'R' },
                      ],
                      total: 2,
                    };
                    if (path === '/api/pins') {
                      if (options.method === 'POST') return { ok: true, pins: [{ id: 'p1', kind: 'app', label: 'Notepad', target: 'C:/Windows/notepad.exe' }] };
                      return { pins: [] };
                    }
                    if (path === '/api/launch' || path === '/api/quick-actions') throw new Error('blocked in smoke test');
                    if (path === '/api/windows') return { windows: [appWindow] };
                    return {};
                  };
                  state.appsLoaded = false;
                  state.apps = [];
                  state.quickActions = [];
                  state.pins = [];
                  state.pinsLoaded = false;
                  state.appSearch = '';
                  state.windows = [appWindow];
                  openDestination('apps');
                  for (let attempt = 0; attempt < 40 && !state.appsLoaded; attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  const opened = {
                    destination: state.currentDestination,
                    panelOpen: elements.appsPanel.classList.contains('panel-open'),
                    apps: elements.appList.querySelectorAll('.app-entry:not(.window-result)').length,
                    quickActions: elements.quickActions.querySelectorAll('.quick-action').length,
                  };
                  elements.appSearchInput.value = 'file explorer';
                  elements.appSearchInput.dispatchEvent(new Event('input'));
                  const filtered = {
                    windows: elements.appList.querySelectorAll('.window-result').length,
                    apps: elements.appList.querySelectorAll('.app-entry:not(.window-result)').length,
                  };
                  elements.appSearchInput.value = '';
                  elements.appSearchInput.dispatchEvent(new Event('input'));
                  elements.appList.querySelector('.app-entry:not(.window-result) .app-entry-main').click();
                  elements.quickActions.querySelector('.quick-action').click();
                  for (let attempt = 0; attempt < 30 && (!calls.includes('/api/launch') || !calls.includes('/api/quick-actions')); attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  elements.appList.querySelector('.app-pin-button').click();
                  for (let attempt = 0; attempt < 30 && !elements.pinnedItems.querySelector('.pinned-chip'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 0));
                  const actions = {
                    launched: calls.includes('/api/launch'),
                    quickAction: calls.includes('/api/quick-actions'),
                    pinnedChips: elements.pinnedItems.querySelectorAll('.pinned-chip').length,
                  };
                  openDestination('viewer');
                  const closed = state.currentDestination === 'viewer' && !elements.appsPanel.classList.contains('panel-open');
                  apiFetch = realApiFetch;
                  state.appsLoaded = false;
                  state.apps = [];
                  state.quickActions = [];
                  state.pins = [];
                  state.pinsLoaded = false;
                  state.appSearch = "";
                  state.windows = [];
                  renderApps();
                  renderWindowList();
                  return { opened, filtered, actions, closed };
                })()""",
                await_promise=True,
            )
            assert apps_report["opened"] == {"destination": "apps", "panelOpen": True, "apps": 2, "quickActions": 2}, apps_report
            assert apps_report["filtered"] == {"windows": 1, "apps": 0}, apps_report
            assert apps_report["actions"] == {"launched": True, "quickAction": True, "pinnedChips": 1}, apps_report
            assert apps_report["closed"] is True, apps_report

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
                      : id === 'shortcuts'
                        ? elements.shortcutsPanel.classList.contains('panel-open')
                      : id === 'apps'
                        ? elements.appsPanel.classList.contains('panel-open')
                      : id === 'controls'
                        ? elements.controlsPanel.classList.contains('panel-open')
                        : elements.settingsPanel.classList.contains('panel-open');
                  saveBottomNavConfig(['windows', 'apps', 'keyboard']);
                  const destinationToggles = {};
                  for (const id of ['windows', 'apps', 'keyboard', 'shortcuts', 'controls', 'settings']) {
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
                      && !elements.appsPanel.classList.contains('panel-open')
                      && !elements.shortcutsPanel.classList.contains('panel-open')
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

                  localStorage.removeItem(POINTER_SHORTCUT_STORAGE_KEY);
                  setGestureArm('gestures');
                  openDestination('shortcuts');
                  const shortcutMenuShown = state.currentDestination === 'shortcuts'
                    && elements.shortcutsPanel.classList.contains('panel-open');
                  elements.shortcutMenu.querySelector('[data-pointer-shortcut="right"]').click();
                  const shortcutSelection = {
                    menuShown: shortcutMenuShown,
                    mode: state.gestureArm,
                    stored: localStorage.getItem(POINTER_SHORTCUT_STORAGE_KEY),
                    destination: state.currentDestination,
                    panelHidden: !elements.shortcutsPanel.classList.contains('panel-open'),
                    selected: elements.shortcutMenu.querySelector('[data-pointer-shortcut="right"]').getAttribute('aria-pressed'),
                    badge: elements.activeShortcut.textContent,
                  };
                  loadGestureShortcut();
                  shortcutSelection.reloadedMode = state.gestureArm;
                  elements.shortcutMenu.querySelector('[data-pointer-shortcut="gestures"]').click();
                  shortcutSelection.gesturesMode = state.gestureArm;

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
                  const rightClickArmed = state.gestureArm === 'right'
                    && elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').getAttribute('aria-pressed') === 'true';
                  elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').click();
                  const rightClickDisarmed = state.gestureArm === 'gestures'
                    && elements.mobileNav.querySelector('[data-bottom-action="rightClick"]').getAttribute('aria-pressed') === 'false';
                  elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').click();
                  const doubleClickArmed = state.gestureArm === 'double'
                    && elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').getAttribute('aria-pressed') === 'true';
                  elements.mobileNav.querySelector('[data-bottom-action="doubleClick"]').click();
                  const doubleClickDisarmed = state.gestureArm === 'gestures'
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
                  return { defaults, defaultDesktop, defaultDesktopOnce, desktopSelection, desktopRestore, cameraBeforeToggles, unavailableMessage, destinationToggles, cameraAfterDestinationToggles, selectedAfterDestinationToggles, mandatoryOnly, mandatoryEditorLocked, shortcutSelection, reordered, customOverflow, rightClickArmed, rightClickDisarmed, doubleClickArmed, doubleClickDisarmed, gestureShown, gestureHidden, gestureShownAgain, persisted, sanitized, storedSanitized, power, navOverflow, reset, storedReset };
                })()""",
                await_promise=True,
            )
            assert nav_report["defaults"] == ["desktop", "windows", "keyboard", "shortcuts", "controls", "settings"], nav_report
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
                {"id": "shortcuts", "disabled": False},
                {"id": "controls", "disabled": False},
                {"id": "settings", "disabled": False},
            ], nav_report
            assert nav_report["mandatoryEditorLocked"], nav_report
            assert nav_report["shortcutSelection"] == {
                "menuShown": True,
                "mode": "right",
                "stored": "right",
                "destination": "viewer",
                "panelHidden": True,
                "selected": "true",
                "badge": "Right click",
                "reloadedMode": "right",
                "gesturesMode": "gestures",
            }, nav_report
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

            wheel_report = browser.evaluate(
                """(async () => {
                  const realApiFetch = apiFetch;
                  const requests = [];
                  const resolvers = [];
                  apiFetch = (path, options) => {
                    const payload = JSON.parse(options.body);
                    requests.push({ path, delta: payload.delta });
                    return new Promise(resolve => resolvers.push(resolve));
                  };
                  state.gestureDiagnosticsEnabled = true;
                  state.gestureLogBuffer = [];
                  state.selectedWindow = { hwnd: 432 };
                  state.pendingWheelPayload = null;
                  state.pendingWheelHwnd = null;
                  state.wheelRequestInFlight = false;
                  sendPointer('wheel_current', { delta: 10 });
                  sendPointer('wheel_current', { delta: 20 });
                  sendPointer('wheel_current', { delta: 30 });
                  for (let attempt = 0; attempt < 20 && requests.length < 1; attempt += 1) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                  }
                  const requestsBeforeRelease = requests.length;
                  resolvers.shift()({});
                  for (let attempt = 0; attempt < 20 && requests.length < 2; attempt += 1) {
                    await new Promise(resolve => setTimeout(resolve, 0));
                  }
                  const deltas = requests.map(request => request.delta);
                  const paths = requests.map(request => request.path);
                  resolvers.shift()({});
                  await new Promise(resolve => setTimeout(resolve, 0));
                  const diagnosticEvents = state.gestureLogBuffer.map(entry => entry.event);
                  const diagnosticDetails = state.gestureLogBuffer
                    .filter(entry => ['browser-action-queued','browser-action-sent','browser-action-ack'].includes(entry.event))
                    .map(entry => entry.details);
                  apiFetch = realApiFetch;
                  state.selectedWindow = null;
                  state.pendingWheelPayload = null;
                  state.pendingWheelHwnd = null;
                  state.wheelRequestInFlight = false;
                  return { requestsBeforeRelease, deltas, paths, diagnosticEvents, diagnosticDetails };
                })()""",
                await_promise=True,
            )
            assert wheel_report["requestsBeforeRelease"] == 1, wheel_report
            assert wheel_report["deltas"] == [10, 50], wheel_report
            assert wheel_report["paths"] == ["/api/windows/432/pointer", "/api/windows/432/pointer"], wheel_report
            for event in ("browser-action-queued", "browser-action-sent", "browser-action-ack", "browser-action-coalesced"):
                assert event in wheel_report["diagnosticEvents"], wheel_report
            assert all(
                "request_id" in details and "shortcut" in details and "queue_depth" in details
                for details in wheel_report["diagnosticDetails"]
            ), wheel_report

            clear_report = browser.evaluate(
                """(async () => {
                  const realFetch = window.fetch;
                  const realToken = state.token;
                  const startGeneration = state.gestureLogGeneration;
                  let requestAborted = false;
                  window.fetch = (_path, options) => new Promise((_resolve, reject) => {
                    options.signal.addEventListener('abort', () => {
                      requestAborted = true;
                      reject(new DOMException('Aborted', 'AbortError'));
                    }, { once: true });
                  });
                  state.token = 'test-token';
                  state.gestureLogBuffer = [{ event: 'test', at: new Date().toISOString(), details: {} }];
                  flushGestureDiagnostics();
                  const flushStarted = state.gestureLogFlushInFlight;
                  resetPendingGestureDiagnostics();
                  await new Promise(resolve => setTimeout(resolve, 0));
                  const report = {
                    flushStarted,
                    requestAborted,
                    generationAdvanced: state.gestureLogGeneration === startGeneration + 1,
                    inFlight: state.gestureLogFlushInFlight,
                    buffered: state.gestureLogBuffer.length,
                    controllerCleared: state.gestureLogAbortController === null,
                  };
                  state.token = realToken;
                  window.fetch = realFetch;
                  return report;
                })()""",
                await_promise=True,
            )
            assert clear_report == {
                "flushStarted": True,
                "requestAborted": True,
                "generationAdvanced": True,
                "inFlight": False,
                "buffered": 0,
                "controllerCleared": True,
            }, clear_report

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
                  setGestureArm('gestures');
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

                  setGestureArm('double');
                  e('pointerdown', 69, 120, 220);
                  e('pointerup', 69, 120, 220);
                  const explicitDoubleActions = calls.splice(0).map(item => item.action);
                  const explicitDoubleModeAfterTap = state.gestureArm;
                  setGestureArm('gestures');

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

                  elements.touchLayer.setPointerCapture = () => { throw new DOMException('capture unavailable', 'NotFoundError'); };
                  setGestureArm('scroll');
                  e('pointerdown', 100, 120, 240);
                  const captureFailureContinued = state.dragActive === true && state.pointerDown === true;
                  e('pointerup', 100, 120, 240);
                  const captureFailureLogged = state.gestureLogBuffer.some(entry => entry.event === 'pointer-capture'
                    && entry.details.reason === 'capture-failed' && entry.details.state === 'continuing');
                  elements.touchLayer.setPointerCapture = () => {};
                  calls.splice(0);

                  setGestureArm('scroll');
                  e('pointerdown', 101, 120, 240);
                  const shortcutScrollImmediate = state.dragActive === true && state.twoFingerGesture === null;
                  e('pointerdown', 102, 180, 240);
                  const shortcutScrollBlocksNormalGestures = state.twoFingerGesture === null && state.activePointers.size === 1;
                  e('pointermove', 101, 120, 200);
                  e('pointermove', 101, 120, 160);
                  e('pointerup', 101, 120, 160);
                  const shortcutScrollActions = calls.splice(0).map(item => item.action);

                  setGestureArm('drag');
                  e('pointerdown', 103, 120, 240);
                  const shortcutDragImmediate = state.dragActive === true;
                  e('pointermove', 103, 160, 200);
                  e('pointerup', 103, 160, 200);
                  const shortcutDragActions = calls.splice(0).map(item => item.action);

                  setCameraScale(1);
                  const shortcutPanStart = { ...state.cameraFocus };
                  setGestureArm('pan');
                  e('pointerdown', 104, 120, 240);
                  const shortcutPanImmediate = state.dragActive === true;
                  e('pointermove', 104, 170, 200);
                  e('pointerup', 104, 170, 200);
                  const shortcutPanMoved = state.cameraFocus.x !== shortcutPanStart.x || state.cameraFocus.y !== shortcutPanStart.y;
                  const shortcutPanScale = state.cameraScale;
                  calls.splice(0);

                  setCameraScale(1);
                  setGestureArm('zoom');
                  e('pointerdown', 105, 120, 240);
                  const shortcutZoomImmediate = state.dragActive === true;
                  e('pointermove', 105, 120, 180);
                  e('pointerup', 105, 120, 180);
                  const shortcutZoomScale = state.cameraScale;
                  calls.splice(0);
                  const shortcutDiagnosticEntries = state.gestureLogBuffer
                    .filter(entry => ['pointer-ready','shortcut-drag-frame','shortcut-drag-finish','pointer-capture'].includes(entry.event));
                  setGestureArm('gestures');

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
                  e('pointermove', 32, 183, 162);
                  const scrollModeAfterDrag = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleBeforeSeparation = state.cameraScale;
                  e('pointermove', 32, 223, 162);
                  const scrollModeAfterSeparation = state.twoFingerGesture?.mode ?? null;
                  const scrollScaleAfterSeparation = state.cameraScale;
                  e('pointerup', 31, 103, 202);
                  const scrollActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 91, 100, 200);
                  e('pointerdown', 92, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  e('pointermove', 91, 100, 160);
                  const fileDragMode = state.twoFingerGesture?.mode ?? null;
                  const fileDragStatus = elements.gestureStatus.textContent;
                  e('pointermove', 91, 100, 140);
                  e('pointerup', 92, 180, 200);
                  const fileDragActions = calls.splice(0).map(item => item.action);

                  e('pointerdown', 51, 100, 200);
                  e('pointerdown', 52, 180, 200);
                  await new Promise(resolve => setTimeout(resolve, TWO_FINGER_SCROLL_HOLD_MS + 30));
                  e('pointermove', 52, 180, 160);
                  e('pointercancel', 51, 100, 200);
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
                  return { freshControls, legacyControls, savedControls, trackpadActions, touchModeStored, singleTapImmediateActions, singleTapActions, doubleTapActions, doubleTapStatus, doubleTapHaptic, doubleTapDelayedActions, farTapImmediateActions, farTapDelayedActions, lateTapActions, pendingTapCanceledByDragActions, explicitDoubleActions, explicitDoubleModeAfterTap, cancellationActions, panActions, panStartFocus, panEndFocus, boundedPanActions, boundedPanFocus, scaleOneActions, scaleOneFocus, scaleOneEndFocus, captureFailureContinued, captureFailureLogged, shortcutScrollImmediate, shortcutScrollBlocksNormalGestures, shortcutScrollActions, shortcutDragImmediate, shortcutDragActions, shortcutPanImmediate, shortcutPanMoved, shortcutPanScale, shortcutZoomImmediate, shortcutZoomScale, shortcutDiagnosticEntries, prematureMode, prematureActions, earlyReleaseActions, jitterArmed, readyStatus, readyHaptic, scrollActions, scrollModeAfterDrag, scrollModeAfterSeparation, scrollScaleBeforeSeparation, scrollScaleAfterSeparation, fileDragMode, fileDragStatus, fileDragActions, scrollCancelActions, scrollCancelState, pinchActions, pinchScale, pinchModeAfterSeparation, pinchModeAfterParallel, twoFingerTapActions, twoFingerTapStatus, twoFingerTapHaptic, heldTwoFingerTapActions, heldFingerActions, heldThenReleasedActions, cancelActions, diagnosticEvents, diagnosticStates, diagnosticPointerTypes };
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
            assert gesture_report["explicitDoubleModeAfterTap"] == "double", gesture_report
            assert all(actions == [] for actions in gesture_report["cancellationActions"].values()), gesture_report
            assert gesture_report["panActions"] == [], gesture_report
            assert gesture_report["panEndFocus"]["x"] < gesture_report["panStartFocus"]["x"], gesture_report
            assert gesture_report["panEndFocus"]["y"] < gesture_report["panStartFocus"]["y"], gesture_report
            assert gesture_report["boundedPanActions"] == [], gesture_report
            assert gesture_report["boundedPanFocus"] == {"x": 0, "y": 0}, gesture_report
            assert gesture_report["scaleOneActions"] == [], gesture_report
            assert gesture_report["scaleOneEndFocus"] == gesture_report["scaleOneFocus"], gesture_report
            assert gesture_report["captureFailureContinued"] and gesture_report["captureFailureLogged"], gesture_report
            assert gesture_report["shortcutScrollImmediate"] and gesture_report["shortcutScrollBlocksNormalGestures"], gesture_report
            assert gesture_report["shortcutScrollActions"] == ["wheel_current", "wheel_current"], gesture_report
            assert gesture_report["shortcutDragImmediate"], gesture_report
            assert gesture_report["shortcutDragActions"] == ["down", "move", "up"], gesture_report
            assert gesture_report["shortcutPanImmediate"] and gesture_report["shortcutPanMoved"] and gesture_report["shortcutPanScale"] >= 2, gesture_report
            assert gesture_report["shortcutZoomImmediate"] and gesture_report["shortcutZoomScale"] > 1, gesture_report
            shortcut_diagnostic_events = {entry["event"] for entry in gesture_report["shortcutDiagnosticEntries"]}
            assert {"pointer-ready", "shortcut-drag-frame", "shortcut-drag-finish", "pointer-capture"} <= shortcut_diagnostic_events, gesture_report
            assert all(
                "shortcut" in entry["details"] and "pointer_type" in entry["details"]
                for entry in gesture_report["shortcutDiagnosticEntries"]
            ), gesture_report
            assert gesture_report["prematureMode"] is None and gesture_report["prematureActions"] == [], gesture_report
            assert gesture_report["earlyReleaseActions"] == [], gesture_report
            assert gesture_report["jitterArmed"] is True and gesture_report["readyStatus"] == "Scroll ready", gesture_report
            assert gesture_report["readyHaptic"] == [12, 24, 12], gesture_report
            assert gesture_report["scrollModeAfterDrag"] == "scroll" and gesture_report["scrollModeAfterSeparation"] == "scroll", gesture_report
            assert gesture_report["scrollScaleAfterSeparation"] == gesture_report["scrollScaleBeforeSeparation"], gesture_report
            assert gesture_report["scrollActions"][0] == "touch_down", gesture_report
            assert "touch_move" in gesture_report["scrollActions"] and gesture_report["scrollActions"][-1] == "touch_up", gesture_report
            assert gesture_report["fileDragMode"] == "drag" and gesture_report["fileDragStatus"] == "Drag", gesture_report
            assert gesture_report["fileDragActions"][0] == "down", gesture_report
            assert "move" in gesture_report["fileDragActions"] and gesture_report["fileDragActions"][-1] == "up", gesture_report
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
