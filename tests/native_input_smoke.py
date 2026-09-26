"""Read-only Edge/CDP smoke test for physical mouse and keyboard passthrough."""

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
URL = "http://127.0.0.1:8878/"


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
        [sys.executable, "run_phone_link.py", "--host", "127.0.0.1", "--port", "8878", "--no-gui"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    edge = None
    try:
        wait_json("http://127.0.0.1:8878/api/connect-info")
        with tempfile.TemporaryDirectory(prefix="phone-link-native-", ignore_cleanup_errors=True) as profile:
            edge = subprocess.Popen(
                [
                    str(EDGE),
                    "--headless=new",
                    "--disable-gpu",
                    "--disable-background-networking",
                    "--no-first-run",
                    "--remote-allow-origins=*",
                    "--remote-debugging-port=9224",
                    f"--user-data-dir={profile}",
                    URL,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            targets = wait_json("http://127.0.0.1:9224/json")
            target = next(item for item in targets if item.get("type") == "page")
            browser = CDP(target["webSocketDebuggerUrl"])
            browser.call("Page.enable")
            browser.call("Runtime.enable")
            browser.call("Page.navigate", {"url": URL})
            deadline = time.monotonic() + 10
            while browser.evaluate(
                "document.readyState === 'complete' && Boolean(document.getElementById('authPanel'))"
            ) is not True:
                assert time.monotonic() < deadline
                time.sleep(0.05)
            browser.evaluate(
                "document.getElementById('authPanel').classList.add('hidden');"
                " document.querySelectorAll('.mobile-panel').forEach(panel => panel.style.transition = 'none')"
            )

            report = browser.evaluate(
                """(async () => {
                  const calls = [];
                  const keyCalls = [];
                  const pointerTypes = [];
                  window.__nativeRealApiFetch = apiFetch;
                  window.__nativeRealToken = state.token;
                  apiFetch = async (path, options = {}) => {
                    const payload = options.body ? JSON.parse(options.body) : {};
                    if (path.includes('/secure-desktop')) return { active: Boolean(window.__secureDesktopActive) };
                    if (path.includes('/system/restart-host')) {
                      window.__restartCalls = (window.__restartCalls || 0) + 1;
                      return { ok: true };
                    }
                    if (path.includes('/key-event')) keyCalls.push({ path, payload });
                    else if (path.includes('/pointer')) {
                      pointerTypes.push(payload.pointer_type);
                      calls.push({ path, payload });
                    }
                    return { ok: true, applied: true, cursor: { x: 0.5, y: 0.5, visible: true } };
                  };
                  state.token = 'native-test-token';
                  state.gestureSessionId = 'native-test-session';
                  localStorage.removeItem(NATIVE_INPUT_STORAGE_KEY);
                  localStorage.removeItem(INVERT_WHEEL_STORAGE_KEY);
                  loadViewerPreferences();
                  const defaultOff = state.nativeInputEnabled === false && elements.nativeInput.checked === false;
                  const defaultInvert = state.invertWheel;

                  updateSelectedWindow({ hwnd: 700, bounds: { width: 1280, height: 720 } });
                  openDestination('viewer');
                  elements.nativeInput.checked = true;
                  elements.nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                  const enabled = state.nativeInputEnabled
                    && localStorage.getItem(NATIVE_INPUT_STORAGE_KEY) === 'true'
                    && document.activeElement === elements.nativeInputCapture;
                  const statusAfterEnable = elements.nativeInputStatus.textContent;

                  const viewer = elements.viewerShell.getBoundingClientRect();
                  const center = { x: viewer.left + viewer.width / 2, y: viewer.top + viewer.height / 2 };
                  const pointer = (type, id, x, y, extra = {}) => elements.touchLayer.dispatchEvent(new PointerEvent(type, {
                    pointerId: id, clientX: x, clientY: y, pointerType: 'mouse', bubbles: true, cancelable: true, ...extra,
                  }));
                  const drain = async () => {
                    for (let attempt = 0; attempt < 40; attempt += 1) {
                      await new Promise(resolve => setTimeout(resolve, 0));
                      if (!state.pendingTouchMovePayload && !state.moveRequestInFlight
                        && !state.pendingWheelPayload && !state.wheelRequestInFlight) return;
                    }
                  };
                  const actions = () => calls.splice(0).map(item => item.payload.action);

                  pointer('pointermove', 1, center.x, center.y);
                  await drain();
                  const hoverActions = actions();
                  const statusAfterMouse = elements.nativeInputStatus.textContent;

                  const echoPoint = { x: center.x + 12, y: center.y + 9 };
                  pointer('pointermove', 8, echoPoint.x, echoPoint.y);
                  await drain();
                  calls.splice(0);
                  elements.touchLayer.dispatchEvent(new PointerEvent('pointerdown', {
                    pointerId: 90, clientX: echoPoint.x, clientY: echoPoint.y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  const echoSuppressed = state.activePointers.size === 0 && calls.length === 0;
                  elements.touchLayer.dispatchEvent(new PointerEvent('pointerup', {
                    pointerId: 90, clientX: echoPoint.x, clientY: echoPoint.y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  await drain();
                  calls.splice(0);

                  const savedArm = state.gestureArm;
                  state.gestureArm = 'left';
                  elements.touchLayer.dispatchEvent(new PointerEvent('pointerdown', {
                    pointerId: 91, clientX: center.x - 120, clientY: center.y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  elements.touchLayer.dispatchEvent(new PointerEvent('pointerup', {
                    pointerId: 91, clientX: center.x - 120, clientY: center.y, pointerType: 'touch', bubbles: true, cancelable: true,
                  }));
                  await drain();
                  const realTouchActions = actions();
                  state.gestureArm = savedArm;

                  window.__secureDesktopActive = true;
                  await pollSecureDesktop();
                  const secureNoticeShown = !elements.secureDesktopNotice.classList.contains('hidden');
                  window.__secureDesktopActive = false;
                  await pollSecureDesktop();
                  const secureNoticeHidden = elements.secureDesktopNotice.classList.contains('hidden');
                  delete window.__secureDesktopActive;

                  const savedFocus = { ...state.cameraFocus };
                  setCameraScale(2, { snap: false });
                  handlePointerResponse({ cursor: { x: 0.22, y: 0.66, visible: true } }, "move", "mouse");
                  const followedMouse = Math.abs(state.cameraFocus.x - 0.22) < 0.01
                    && Math.abs(state.cameraFocus.y - 0.66) < 0.01;
                  handlePointerResponse({ cursor: { x: 0.5, y: 0.5, visible: true } }, "move", "");
                  const followIgnoredForTouch = Math.abs(state.cameraFocus.x - 0.22) < 0.01;
                  setCameraScale(1, { snap: false });
                  state.cameraFocus = savedFocus;
                  applyCameraTransform();
                  const mousePointerTypesRecorded = pointerTypes.filter(type => type && type !== "touch");
                  const allMousePointers = pointerTypes.includes("mouse")
                    && mousePointerTypesRecorded.every(type => type === "mouse");

                  const realConfirm = window.confirm;
                  window.confirm = () => true;
                  elements.restartHost.click();
                  await new Promise(resolve => setTimeout(resolve, 0));
                  await new Promise(resolve => setTimeout(resolve, 0));
                  const restartRequested = window.__restartCalls === 1;
                  const reconnectScheduled = Boolean(state.hostReconnectTimer);
                  clearHostReconnectPolling();
                  window.confirm = realConfirm;
                  delete window.__restartCalls;
                  const restartConfirmCancelled = await (async () => {
                    window.confirm = () => false;
                    elements.restartHost.click();
                    await new Promise(resolve => setTimeout(resolve, 0));
                    const skipped = !window.__restartCalls;
                    window.confirm = realConfirm;
                    delete window.__restartCalls;
                    return skipped;
                  })();

                  pointer('pointermove', 1, center.x, center.y);
                  await drain();
                  calls.splice(0);

                  pointer('pointerdown', 1, center.x, center.y, { button: 0, buttons: 1 });
                  pointer('pointermove', 1, center.x + 40, center.y + 20, { button: 0, buttons: 1 });
                  pointer('pointerup', 1, center.x + 40, center.y + 20, { button: 0, buttons: 0 });
                  await drain();
                  const dragActions = actions();
                  const dragReleased = state.nativeMouseLeftDown === false;

                  pointer('pointerdown', 2, center.x - 60, center.y, { button: 0, buttons: 1 });
                  pointer('pointerup', 2, center.x - 60, center.y, { button: 0, buttons: 0 });
                  await drain();
                  const unsyncedClickActions = actions();

                  pointer('pointerdown', 3, center.x, center.y, { button: 2, buttons: 2 });
                  pointer('pointerup', 3, center.x, center.y, { button: 2, buttons: 0 });
                  pointer('pointerdown', 4, center.x, center.y, { button: 1, buttons: 4 });
                  pointer('pointerup', 4, center.x, center.y, { button: 1, buttons: 0 });
                  await drain();
                  const clickActions = actions();

                  const wheelAt = (x, y) => elements.touchLayer.dispatchEvent(new WheelEvent('wheel', {
                    deltaY: 240, deltaMode: 0, clientX: x, clientY: y, bubbles: true, cancelable: true,
                  }));
                  wheelAt(center.x + 90, center.y);
                  await drain();
                  const unsyncedWheelCalls = calls.splice(0).map(item => ({ action: item.payload.action, delta: item.payload.delta }));
                  wheelAt(center.x + 90, center.y);
                  await drain();
                  const syncedWheelCalls = calls.splice(0).map(item => ({ action: item.payload.action, delta: item.payload.delta }));
                  setInvertWheel(true);
                  wheelAt(center.x + 90, center.y);
                  await drain();
                  const invertedWheelCalls = calls.splice(0).map(item => ({ action: item.payload.action, delta: item.payload.delta }));
                  const invertStored = localStorage.getItem(INVERT_WHEEL_STORAGE_KEY);
                  setInvertWheel(false);

                  const key = (type, code, extra = {}) => {
                    const event = new KeyboardEvent(type, { code, key: code, bubbles: true, cancelable: true, ...extra });
                    document.dispatchEvent(event);
                    return event.defaultPrevented;
                  };
                  document.activeElement.blur();
                  const unfocused = document.activeElement !== elements.nativeInputCapture;
                  const keyDownPrevented = key('keydown', 'KeyA');
                  const shiftDownPrevented = key('keydown', 'ShiftLeft');
                  const controlDownPrevented = key('keydown', 'ControlLeft');
                  key('keyup', 'KeyA');
                  await drain();
                  const keyActions = keyCalls.splice(0).map(item => `${item.payload.key}:${item.payload.down}`);
                  const prevented = keyDownPrevented && shiftDownPrevented && controlDownPrevented;
                  const typedWithoutFocus = unfocused && keyActions.includes("KeyA:true") && keyActions.includes("KeyA:false");
                  const statusAfterKeys = elements.nativeInputStatus.textContent;

                  const legacyKey = (type) => {
                    const event = new KeyboardEvent(type, { code: 'Unidentified', key: 'Unidentified', bubbles: true, cancelable: true });
                    Object.defineProperty(event, 'keyCode', { get: () => 38 });
                    document.dispatchEvent(event);
                    return event;
                  };
                  const fallbackPrevented = legacyKey('keydown').defaultPrevented;
                  legacyKey('keyup');
                  await drain();
                  const fallbackActions = keyCalls.splice(0).map(item => `${item.payload.key}:${item.payload.down}`);

                  const probe = document.createElement('button');
                  probe.type = 'button';
                  document.body.appendChild(probe);
                  probe.focus();
                  await new Promise(resolve => setTimeout(resolve, 0));
                  const focusStolenBack = document.activeElement === elements.nativeInputCapture;
                  probe.remove();

                  openDestination('keyboard');
                  elements.textInput.focus();
                  const composerFocused = document.activeElement === elements.textInput;
                  const composerActive = `${document.activeElement?.tagName || ''}#${document.activeElement?.id || ''}`;
                  key('keydown', 'KeyB');
                  key('keyup', 'KeyB');
                  await drain();
                  const composerKeyCalls = keyCalls.map(item => `${item.payload.key}:${item.payload.down}`);
                  const composerIgnored = composerFocused && composerKeyCalls.every(entry => !entry.startsWith("KeyB"));
                  keyCalls.splice(0);

                  focusNativeInputCapture({ force: true });
                  key('keydown', 'KeyC');
                  await drain();
                  openDestination('controls');
                  await drain();
                  const destinationRelease = keyCalls.splice(0).map(item => `${item.payload.key}:${item.payload.down}`);

                  openDestination('viewer');
                  elements.nativeInput.checked = false;
                  elements.nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                  const disabled = state.nativeInputEnabled === false
                    && localStorage.getItem(NATIVE_INPUT_STORAGE_KEY) === 'false'
                    && state.nativeHeldKeys.size === 0;

                  localStorage.removeItem(NATIVE_INPUT_STORAGE_KEY);
                  loadViewerPreferences();
                  setControlMode('touch');
                  state.selectedWindow = null;
                  syncSecureDesktopPolling();
                  resetViewer();
                  apiFetch = window.__nativeRealApiFetch;
                  state.token = window.__nativeRealToken;
                  delete window.__nativeRealApiFetch;
                  delete window.__nativeRealToken;
                  return {
                    defaultOff, defaultInvert, enabled, statusAfterEnable, statusAfterMouse, hoverActions,
                    echoSuppressed, realTouchActions, secureNoticeShown, secureNoticeHidden,
                    followedMouse, followIgnoredForTouch, allMousePointers,
                    restartRequested, reconnectScheduled, restartConfirmCancelled,
                    dragActions, dragReleased, unsyncedClickActions, clickActions,
                    unsyncedWheelCalls, syncedWheelCalls, invertedWheelCalls, invertStored,
                    prevented, keyActions, typedWithoutFocus, statusAfterKeys, fallbackPrevented, fallbackActions, focusStolenBack,
                    composerFocused, composerActive, composerKeyCalls, composerIgnored, destinationRelease, disabled,
                  };
                })()""",
                await_promise=True,
            )
            assert report["defaultOff"], report
            assert report["defaultInvert"] is False, report
            assert report["enabled"], report
            assert report["hoverActions"] == ["move"], report
            assert "Mouse: active" in report["statusAfterMouse"], report
            assert report["echoSuppressed"], report
            assert report["realTouchActions"] == ["touch_tap"], report
            assert report["secureNoticeShown"] and report["secureNoticeHidden"], report
            assert report["allMousePointers"], report
            assert report["restartRequested"] and report["reconnectScheduled"], report
            assert report["restartConfirmCancelled"], report
            assert report["followedMouse"] and report["followIgnoredForTouch"], report
            assert report["dragActions"] == ["down_current", "move", "up_current"], report
            assert report["dragReleased"], report
            assert report["unsyncedClickActions"] == ["down", "up_current"], report
            assert report["clickActions"] == ["right_tap", "middle_click_current"], report
            assert report["unsyncedWheelCalls"] == [
                {"action": "move", "delta": 0},
                {"action": "wheel_current", "delta": -240},
            ], report
            assert report["syncedWheelCalls"] == [{"action": "wheel_current", "delta": -240}], report
            assert report["invertedWheelCalls"] == [{"action": "wheel_current", "delta": 240}], report
            assert report["invertStored"] == "true", report
            assert report["prevented"], report
            assert report["keyActions"] == [
                "KeyA:true", "ShiftLeft:true", "ControlLeft:true", "KeyA:false",
            ], report
            assert report["typedWithoutFocus"], report
            assert "waiting for a key" in report["statusAfterEnable"], report
            assert "receiving keys" in report["statusAfterKeys"], report
            assert report["fallbackPrevented"], report
            assert report["fallbackActions"] == ["ArrowUp:true", "ArrowUp:false"], report
            assert report["focusStolenBack"], report
            assert report["composerIgnored"], report
            assert report["composerKeyCalls"] == ["ShiftLeft:false", "ControlLeft:false"], report
            assert report["destinationRelease"] == ["KeyC:true", "KeyC:false"], report
            assert report["disabled"], report
            print("Native input smoke: hover/drag/click/wheel ok, typing works without focus and releases ok")
    finally:
        if edge is not None:
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
