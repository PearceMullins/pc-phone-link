const assert = require("node:assert/strict");
const game = require("../phone_link/static/game-controls.js");

assert.deepEqual(game.keysForJoystick(0, 0), []);
assert.deepEqual(game.keysForJoystick(0.8, -0.8), ["w", "d"]);
assert.deepEqual(game.keysForJoystick(-0.8, 0.8), ["a", "s"]);
assert.deepEqual(game.keysForJoystick(0.27, -0.27), []);
assert.deepEqual(game.keysForJoystick(0.29, 0), ["d"]);
assert.equal(game.normalizeInputStyle("joystick"), "joystick");
assert.equal(game.normalizeInputStyle("invalid"), "pad");
assert.equal(game.nextControlMode("touch"), "trackpad");
assert.equal(game.nextControlMode("trackpad"), "game");
assert.equal(game.nextControlMode("game"), "touch");
assert.equal(game.isMovementKey("W"), true);
assert.equal(game.isMovementKey("shift"), false);
assert.deepEqual(game.mouseVectorForJoystick(0.1, 0.1), { x: 0, y: 0, magnitude: 0 });
const mouseDiagonal = game.mouseVectorForJoystick(1, -1);
assert.ok(mouseDiagonal.x > 0.6 && mouseDiagonal.y < -0.6);
assert.ok(mouseDiagonal.magnitude > 0.99);
const mousePartial = game.mouseVectorForJoystick(0.5, 0);
assert.ok(mousePartial.x > 0 && mousePartial.x < 0.5);
assert.equal(mousePartial.y, 0);

console.log("game controls tests passed");
