(function attachGameControls(root) {
  "use strict";

  const MOVEMENT_KEYS = Object.freeze(["w", "a", "s", "d"]);
  const INPUT_STYLES = Object.freeze(["pad", "joystick"]);
  const GAME_LAYOUT_GROUPS = Object.freeze(["movement", "mouse", "clicks"]);
  const DEFAULT_GAME_LAYOUT = Object.freeze({
    portrait: Object.freeze({
      movement: Object.freeze({ x: 0.24, y: 0.76 }),
      mouse: Object.freeze({ x: 0.76, y: 0.68 }),
      clicks: Object.freeze({ x: 0.76, y: 0.88 }),
    }),
    landscape: Object.freeze({
      movement: Object.freeze({ x: 0.16, y: 0.68 }),
      mouse: Object.freeze({ x: 0.84, y: 0.61 }),
      clicks: Object.freeze({ x: 0.84, y: 0.86 }),
    }),
  });

  function clampGameUiScale(value) {
    if (value === null || value === undefined || value === "") return 1;
    const candidate = Number(value);
    if (!Number.isFinite(candidate)) return 1;
    return Math.max(0.75, Math.min(candidate, 1.35));
  }

  function defaultGameLayout() {
    return JSON.parse(JSON.stringify(DEFAULT_GAME_LAYOUT));
  }

  function normalizeGamePosition(value, fallback) {
    const x = Number(value?.x);
    const y = Number(value?.y);
    return {
      x: Number.isFinite(x) ? Math.max(0, Math.min(x, 1)) : fallback.x,
      y: Number.isFinite(y) ? Math.max(0, Math.min(y, 1)) : fallback.y,
    };
  }

  function normalizeGameLayout(value) {
    const result = defaultGameLayout();
    for (const orientation of ["portrait", "landscape"]) {
      for (const group of GAME_LAYOUT_GROUPS) {
        result[orientation][group] = normalizeGamePosition(
          value?.[orientation]?.[group],
          DEFAULT_GAME_LAYOUT[orientation][group],
        );
      }
    }
    return result;
  }

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
    DEFAULT_GAME_LAYOUT,
    GAME_LAYOUT_GROUPS,
    INPUT_STYLES,
    MOVEMENT_KEYS,
    clampGameUiScale,
    defaultGameLayout,
    isMovementKey,
    keysForJoystick,
    mouseVectorForJoystick,
    nextControlMode,
    normalizeGameLayout,
    normalizeGamePosition,
    normalizeInputStyle,
  });

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.PCPhoneLinkGameControls = api;
})(typeof window !== "undefined" ? window : globalThis);
