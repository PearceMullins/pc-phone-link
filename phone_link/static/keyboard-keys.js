(function exposeKeyboardKeys(root, factory) {
  const helpers = factory();
  if (typeof module === "object" && module.exports) module.exports = helpers;
  root.PCPhoneLinkKeyboardKeys = helpers;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildKeyboardKeys() {
  const KEY_CODE_NAMES = Object.freeze({
    8: "Backspace",
    9: "Tab",
    13: "Enter",
    16: "ShiftLeft",
    17: "ControlLeft",
    18: "AltLeft",
    19: "Pause",
    20: "CapsLock",
    27: "Escape",
    32: "Space",
    33: "PageUp",
    34: "PageDown",
    35: "End",
    36: "Home",
    37: "ArrowLeft",
    38: "ArrowUp",
    39: "ArrowRight",
    40: "ArrowDown",
    45: "Insert",
    46: "Delete",
    91: "MetaLeft",
    92: "MetaRight",
    93: "ContextMenu",
    106: "NumpadMultiply",
    107: "NumpadAdd",
    109: "NumpadSubtract",
    110: "NumpadDecimal",
    111: "NumpadDivide",
    144: "NumLock",
    145: "ScrollLock",
    186: "Semicolon",
    187: "Equal",
    188: "Comma",
    189: "Minus",
    190: "Period",
    191: "Slash",
    192: "Backquote",
    219: "BracketLeft",
    220: "Backslash",
    221: "BracketRight",
    222: "Quote",
  });

  const KEY_NAMES = Object.freeze({
    " ": "Space",
    Enter: "Enter",
    Esc: "Escape",
    Escape: "Escape",
    Tab: "Tab",
    Backspace: "Backspace",
    Delete: "Delete",
    Insert: "Insert",
    Home: "Home",
    End: "End",
    PageUp: "PageUp",
    PageDown: "PageDown",
    ArrowUp: "ArrowUp",
    ArrowDown: "ArrowDown",
    ArrowLeft: "ArrowLeft",
    ArrowRight: "ArrowRight",
    Shift: "ShiftLeft",
    Control: "ControlLeft",
    Alt: "AltLeft",
    Meta: "MetaLeft",
    CapsLock: "CapsLock",
    ContextMenu: "ContextMenu",
    ",": "Comma",
    ".": "Period",
    "/": "Slash",
    ";": "Semicolon",
    "[": "BracketLeft",
    "]": "BracketRight",
    "\\": "Backslash",
    "-": "Minus",
    "=": "Equal",
    "`": "Backquote",
    "'": "Quote",
  });

  function nameFromKeyCode(keyCode) {
    const value = Number(keyCode);
    if (!Number.isFinite(value) || value <= 0) return "";
    if (KEY_CODE_NAMES[value]) return KEY_CODE_NAMES[value];
    if (value >= 48 && value <= 57) return `Digit${value - 48}`;
    if (value >= 65 && value <= 90) return `Key${String.fromCharCode(value)}`;
    if (value >= 96 && value <= 105) return `Numpad${value - 96}`;
    if (value >= 112 && value <= 123) return `F${value - 111}`;
    return "";
  }

  function nameFromKey(key) {
    const value = typeof key === "string" ? key : "";
    if (!value || value === "Unidentified") return "";
    if (/^[a-z]$/i.test(value)) return `Key${value.toUpperCase()}`;
    if (/^[0-9]$/.test(value)) return `Digit${value}`;
    if (/^F([1-9]|1[0-9]|2[0-4])$/.test(value)) return value;
    if (KEY_NAMES[value]) return KEY_NAMES[value];
    return "";
  }

  function nameForEvent(event) {
    if (!event || typeof event !== "object") return "";
    const code = typeof event.code === "string" ? event.code.trim() : "";
    if (code && code !== "Unidentified") return code;
    const fromKeyCode = nameFromKeyCode(event.keyCode);
    if (fromKeyCode) return fromKeyCode;
    return nameFromKey(event.key);
  }

  return Object.freeze({ nameForEvent, nameFromKeyCode, nameFromKey });
}));
