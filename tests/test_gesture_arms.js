const assert = require("node:assert/strict");
const {
  ARM_ARMED_STATUS,
  ARM_BUTTON_IDS,
  ARM_CANCELED_STATUS,
  ARM_LABELS,
  ARM_VALUES,
  GESTURE_ARMS,
  ONE_FINGER_DRAG_ARMS,
  TAP_ARMS,
  armStatusAfterToggle,
  consumesOnGesture,
  effectiveTouchDragArm,
  isOneFingerDragArm,
  isTapArm,
  isValidArm,
  toggleArm,
} = require("../phone_link/static/gesture-arms.js");

assert.deepEqual(ARM_VALUES, ["gestures", "left", "right", "double", "pan", "drag", "scroll", "zoom"]);
assert.deepEqual(TAP_ARMS, ["left", "right", "double"]);
assert.deepEqual(ONE_FINGER_DRAG_ARMS, ["pan", "drag", "scroll", "zoom"]);
assert.equal(isValidArm("pan"), true);
assert.equal(isValidArm("bogus"), false);
assert.equal(isTapArm("double"), true);
assert.equal(isTapArm("scroll"), false);
assert.equal(isOneFingerDragArm("zoom"), true);
assert.equal(isOneFingerDragArm("left"), false);
assert.equal(toggleArm("left", "right"), "right");
assert.equal(toggleArm("right", "right"), "gestures");
assert.equal(toggleArm("drag", "scroll"), "scroll");
assert.equal(consumesOnGesture("gestures"), false);
assert.equal(consumesOnGesture("left"), true);
assert.equal(consumesOnGesture("pan"), true);
assert.equal(effectiveTouchDragArm("left"), GESTURE_ARMS.PAN);
assert.equal(effectiveTouchDragArm("gestures"), GESTURE_ARMS.PAN);
assert.equal(effectiveTouchDragArm("drag"), "drag");
assert.equal(armStatusAfterToggle("left", "right", "right"), ARM_ARMED_STATUS.right);
assert.equal(armStatusAfterToggle("right", "left", "right"), ARM_CANCELED_STATUS.right);
assert.equal(ARM_BUTTON_IDS.pan, "panMode");
assert.equal(ARM_LABELS.zoom, "Zoom");

console.log("gesture arms: ok");
