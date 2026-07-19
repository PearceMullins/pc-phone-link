(function exposeGestureHelpers(root, factory) {
  const helpers = factory();
  if (typeof module === "object" && module.exports) module.exports = helpers;
  root.PCPhoneLinkGestures = helpers;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildGestureHelpers() {
  function distance(first, second) {
    return Math.hypot(second.x - first.x, second.y - first.y);
  }

  function midpoint(first, second) {
    return { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 };
  }

  function twoFingerMotion(startA, startB, currentA, currentB) {
    const startMidpoint = midpoint(startA, startB);
    const currentMidpoint = midpoint(currentA, currentB);
    const centroidMovement = distance(startMidpoint, currentMidpoint);
    const separationChange = Math.abs(distance(currentA, currentB) - distance(startA, startB));
    return {
      centroidMovement,
      separationChange,
      movementA: distance(startA, currentA),
      movementB: distance(startB, currentB),
    };
  }

  function classifyTwoFingerGesture(startA, startB, currentA, currentB, threshold = 12) {
    const motion = twoFingerMotion(startA, startB, currentA, currentB);
    const hysteresis = threshold * 0.35;
    if (
      motion.separationChange >= threshold
      && motion.separationChange >= motion.centroidMovement + hysteresis
      && motion.separationChange >= motion.centroidMovement * 1.6
    ) return "pinch";
    return null;
  }

  function isParallelTwoFingerDrag(startA, startB, currentA, currentB, threshold = 6) {
    const first = { x: currentA.x - startA.x, y: currentA.y - startA.y };
    const second = { x: currentB.x - startB.x, y: currentB.y - startB.y };
    const firstDistance = Math.hypot(first.x, first.y);
    const secondDistance = Math.hypot(second.x, second.y);
    if (firstDistance < threshold || secondDistance < threshold) return false;
    const directionSimilarity = ((first.x * second.x) + (first.y * second.y)) / (firstDistance * secondDistance);
    const motion = twoFingerMotion(startA, startB, currentA, currentB);
    return directionSimilarity >= 0.8
      && motion.centroidMovement >= threshold
      && motion.separationChange <= Math.max(threshold, motion.centroidMovement * 0.5);
  }

  function isHoldAndDragScroll(armA, armB, currentA, currentB, holdSlop = 10, dragThreshold = 6) {
    const movementA = distance(armA, currentA);
    const movementB = distance(armB, currentB);
    const minDrag = Math.max(dragThreshold, holdSlop + 1);
    if (movementA <= holdSlop && movementB >= minDrag) {
      return { active: true, dragIndex: 1, anchorIndex: 0 };
    }
    if (movementB <= holdSlop && movementA >= minDrag) {
      return { active: true, dragIndex: 0, anchorIndex: 1 };
    }
    return { active: false, dragIndex: -1, anchorIndex: -1 };
  }

  return {
    distance,
    midpoint,
    twoFingerMotion,
    classifyTwoFingerGesture,
    isParallelTwoFingerDrag,
    isHoldAndDragScroll,
  };
}));
