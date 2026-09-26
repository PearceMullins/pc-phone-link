const assert = require("node:assert/strict");
const { nameForEvent, nameFromKeyCode, nameFromKey } = require("../phone_link/static/keyboard-keys.js");

assert.equal(nameForEvent({ code: "KeyA" }), "KeyA");
assert.equal(nameForEvent({ code: "Digit7" }), "Digit7");
assert.equal(nameForEvent({ code: "NumpadEnter" }), "NumpadEnter");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 38 }), "ArrowUp");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 65 }), "KeyA");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 49 }), "Digit1");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 97 }), "Numpad1");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 116 }), "F5");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 16 }), "ShiftLeft");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 17 }), "ControlLeft");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 18 }), "AltLeft");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 91 }), "MetaLeft");
assert.equal(nameForEvent({ code: "Unidentified", key: "a" }), "KeyA");
assert.equal(nameForEvent({ code: "Unidentified", key: "Z" }), "KeyZ");
assert.equal(nameForEvent({ code: "", key: "5" }), "Digit5");
assert.equal(nameForEvent({ code: "", key: " " }), "Space");
assert.equal(nameForEvent({ code: "", key: "Enter" }), "Enter");
assert.equal(nameForEvent({ code: "", key: "Esc" }), "Escape");
assert.equal(nameForEvent({ code: "", key: "ArrowUp" }), "ArrowUp");
assert.equal(nameForEvent({ code: "", key: "F12" }), "F12");
assert.equal(nameForEvent({ code: "", key: "," }), "Comma");
assert.equal(nameForEvent({ code: "", key: "'" }), "Quote");

assert.equal(nameForEvent({ code: "Unidentified", key: "€" }), "");
assert.equal(nameForEvent({ code: "Unidentified", key: "Unidentified" }), "");
assert.equal(nameForEvent({ code: "Unidentified", keyCode: 0, key: "Dead" }), "");
assert.equal(nameForEvent({}), "");
assert.equal(nameForEvent(null), "");

assert.equal(nameFromKeyCode("38"), "ArrowUp");
assert.equal(nameFromKeyCode(-1), "");
assert.equal(nameFromKeyCode(120), "F9");
assert.equal(nameFromKeyCode(300), "");

assert.equal(nameFromKey("q"), "KeyQ");
assert.equal(nameFromKey("£"), "");
assert.equal(nameFromKey(""), "");
assert.equal(nameFromKey("F1"), "F1");
assert.equal(nameFromKey("F30"), "");

const arrows = [37, 38, 39, 40].map((code) => nameForEvent({ code: "Unidentified", keyCode: code }));
assert.deepEqual(arrows, ["ArrowLeft", "ArrowUp", "ArrowRight", "ArrowDown"]);

const letters = "abcdefghijklmnopqrstuvwxyz".split("");
assert.deepEqual(
  letters.map((letter) => nameForEvent({ code: "Unidentified", key: letter })),
  letters.map((letter) => `Key${letter.toUpperCase()}`),
);

const digits = "0123456789".split("");
assert.deepEqual(
  digits.map((digit) => nameForEvent({ code: "Unidentified", key: digit })),
  digits.map((digit) => `Digit${digit}`),
);

const functionKeys = Array.from({ length: 24 }, (_, index) => `F${index + 1}`);
assert.deepEqual(
  functionKeys.map((name) => nameForEvent({ code: name })),
  functionKeys,
);

console.log("keyboard-keys: fallback mapping ok");
