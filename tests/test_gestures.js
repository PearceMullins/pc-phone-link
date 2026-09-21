const assert = require("node:assert/strict");
const {
  classifyHoldAndDrag,
  classifyTwoFingerGesture,
  isDoubleTapCandidate,
  isHoldAndTapDrag,
  isHoldAndDragScroll,
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
assert.deepEqual(
  isHoldAndDragScroll(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 22 }, { x: 80, y: 55 },
  ),
  { active: true, dragIndex: 1, anchorIndex: 0 },
);
assert.deepEqual(
  isHoldAndDragScroll(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 82, y: 21 },
  ),
  { active: true, dragIndex: 0, anchorIndex: 1 },
);
assert.deepEqual(
  isHoldAndDragScroll(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 80, y: 55 },
  ),
  { active: false, dragIndex: -1, anchorIndex: -1 },
);
assert.deepEqual(
  isHoldAndDragScroll(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 22, y: 22 }, { x: 83, y: 24 },
  ),
  { active: false, dragIndex: -1, anchorIndex: -1 },
);
assert.deepEqual(
  classifyHoldAndDrag(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 82, y: 21 },
  ),
  { active: true, mode: "drag", dragIndex: 0, anchorIndex: 1 },
);
assert.deepEqual(
  classifyHoldAndDrag(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 22 }, { x: 80, y: 55 },
  ),
  { active: true, mode: "scroll", dragIndex: 1, anchorIndex: 0 },
);
assert.deepEqual(
  classifyHoldAndDrag(
    { x: 20, y: 20 }, { x: 80, y: 20 },
    { x: 20, y: 55 }, { x: 80, y: 55 },
  ),
  { active: false, mode: null, dragIndex: -1, anchorIndex: -1 },
);
assert.equal(
  isDoubleTapCandidate(
    { completedAt: 1000, clientPoint: { x: 100, y: 100 } },
    1200,
    { x: 110, y: 100 },
    { delayMs: 320, distancePx: 28 },
  ),
  true,
);
assert.equal(
  isDoubleTapCandidate(
    { completedAt: 1000, clientPoint: { x: 100, y: 100 } },
    1400,
    { x: 110, y: 100 },
    { delayMs: 320, distancePx: 28 },
  ),
  false,
);
assert.equal(
  isDoubleTapCandidate(
    { completedAt: 1000, clientPoint: { x: 100, y: 100 } },
    1200,
    { x: 200, y: 100 },
    { delayMs: 320, distancePx: 28 },
  ),
  false,
);
assert.equal(isDoubleTapCandidate(null, 1200, { x: 100, y: 100 }), false);
assert.equal(isHoldAndTapDrag({ elapsedMs: 120, tapperMovement: 3, holderMovement: 4 }), true);
assert.equal(isHoldAndTapDrag({ elapsedMs: 400, tapperMovement: 3, holderMovement: 4 }), false);
assert.equal(isHoldAndTapDrag({ elapsedMs: 120, tapperMovement: 40, holderMovement: 4 }), false);
assert.equal(isHoldAndTapDrag({ elapsedMs: 120, tapperMovement: 3, holderMovement: 40 }), false);
assert.equal(isHoldAndTapDrag({ elapsedMs: 120, tapperMovement: 12, holderMovement: 12 }), true);

console.log("gesture helpers: ok");
