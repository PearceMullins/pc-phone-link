(function attachGameControls(root) {
  "use strict";

  const MOVEMENT_KEYS = Object.freeze(["w", "a", "s", "d"]);
  const INPUT_STYLES = Object.freeze(["pad", "joystick"]);

  function normalizeInputStyle(value) {
    return INPUT_STYLES.includes(value) ? value : "pad";
  }

  function nextControlMode(value) {
    if (value === "touch") return "trackpad";
    if (value === "trackpad") return "game";
    return "touch";
  }

  function keysForJoystick(deltaX, deltaY, deadzone = 0.28) {
    const x = Number.isFinite(Number(deltaX)) ? Number(deltaX) : 0;
    const y = Number.isFinite(Number(deltaY)) ? Number(deltaY) : 0;
    const threshold = Math.max(0, Math.min(Number(deadzone) || 0, 0.95));
    const keys = [];
    if (y < -threshold) keys.push("w");
    if (x < -threshold) keys.push("a");
    if (y > threshold) keys.push("s");
    if (x > threshold) keys.push("d");
    return keys;
  }

  function mouseVectorForJoystick(deltaX, deltaY, deadzone = 0.16) {
    const x = Number.isFinite(Number(deltaX)) ? Number(deltaX) : 0;
    const y = Number.isFinite(Number(deltaY)) ? Number(deltaY) : 0;
    const threshold = Math.max(0, Math.min(Number(deadzone) || 0, 0.95));
    const rawMagnitude = Math.hypot(x, y);
    const magnitude = Math.min(rawMagnitude, 1);
    if (magnitude <= threshold) return { x: 0, y: 0, magnitude: 0 };
    const scaledMagnitude = (magnitude - threshold) / (1 - threshold);
    const curvedMagnitude = scaledMagnitude ** 1.55;
    return {
      x: (x / rawMagnitude) * curvedMagnitude,
      y: (y / rawMagnitude) * curvedMagnitude,
      magnitude: curvedMagnitude,
    };
  }

  function isMovementKey(value) {
    return MOVEMENT_KEYS.includes(String(value || "").toLowerCase());
  }

  const api = Object.freeze({
    INPUT_STYLES,
    MOVEMENT_KEYS,
    isMovementKey,
    keysForJoystick,
    mouseVectorForJoystick,
    nextControlMode,
    normalizeInputStyle,
  });

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.PCPhoneLinkGameControls = api;
})(typeof window !== "undefined" ? window : globalThis);
