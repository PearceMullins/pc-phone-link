const assert = require("node:assert/strict");
const {
  classifyTwoFingerGesture,
  isParallelTwoFingerDrag,
  midpoint,
  twoFingerMotion,
} = require("../phone_link/static/gestures.js");

assert.deepEqual(midpoint({ x: 0, y: 0 }, { x: 20, y: 10 }), { x: 10, y: 5 });
assert.equal(
  classifyTwoFingerGesture(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 80, y: 55 },
  ),
  null,
);
assert.equal(
  classifyTwoFingerGesture(
    { x: 45, y: 20 }, { x: 55, y: 20 },
    { x: 45, y: 60 }, { x: 55, y: 20 },
  ),
  null,
);
assert.equal(
  isParallelTwoFingerDrag(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 80, y: 55 },
  ),
  true,
);
assert.equal(
  classifyTwoFingerGesture(
    { x: 30, y: 30 }, { x: 70, y: 30 },
    { x: 10, y: 30 }, { x: 90, y: 30 },
  ),
  "pinch",
);
assert.equal(
  classifyTwoFingerGesture(
    { x: 30, y: 30 }, { x: 70, y: 30 },
    { x: 33, y: 32 }, { x: 73, y: 32 },
  ),
  null,
);
assert.equal(
  isParallelTwoFingerDrag(
    { x: 30, y: 30 }, { x: 70, y: 30 },
    { x: 10, y: 30 }, { x: 90, y: 30 },
  ),
  false,
);
assert.deepEqual(
  twoFingerMotion(
    { x: 10, y: 10 }, { x: 50, y: 10 },
    { x: 13, y: 12 }, { x: 53, y: 12 },
  ),
  { centroidMovement: Math.hypot(3, 2), separationChange: 0, movementA: Math.hypot(3, 2), movementB: Math.hypot(3, 2) },
);

console.log("gesture helpers: ok");
