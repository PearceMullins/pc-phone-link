(function exposeGestureArms(root, factory) {
  const helpers = factory();
  if (typeof module === "object" && module.exports) module.exports = helpers;
  root.PCPhoneLinkGestureArms = helpers;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildGestureArms() {
  const GESTURE_ARMS = Object.freeze({
    GESTURES: "gestures",
    LEFT: "left",
    RIGHT: "right",
    DOUBLE: "double",
    PAN: "pan",
    DRAG: "drag",
    SCROLL: "scroll",
    ZOOM: "zoom",
  });

  const ARM_VALUES = Object.freeze(Object.values(GESTURE_ARMS));

  const TAP_ARMS = Object.freeze(["left", "right", "double"]);

  const ONE_FINGER_DRAG_ARMS = Object.freeze(["pan", "drag", "scroll", "zoom"]);

  const ARM_BUTTON_IDS = Object.freeze({
    left: "clickMode",
    right: "rightClickMode",
    double: "doubleClickMode",
    pan: "panMode",
    drag: "dragMode",
    scroll: "scrollMode",
    zoom: "zoomMode",
  });

  const ARM_LABELS = Object.freeze({
    gestures: "Gestures",
    left: "Click",
    right: "Right-click",
    double: "Double-click",
    pan: "Pan viewer",
    drag: "Drag",
    scroll: "Scroll",
    zoom: "Zoom",
  });

  const ARM_ARMED_STATUS = Object.freeze({
    gestures: "Gestures enabled",
    left: "Click armed",
    right: "Right-click armed",
    double: "Double-click armed",
    pan: "Pan armed",
    drag: "Drag armed",
    scroll: "Scroll armed",
    zoom: "Zoom armed",
  });

  const ARM_CANCELED_STATUS = Object.freeze({
    gestures: "Gestures disabled",
    left: "Click canceled",
    right: "Right-click canceled",
    double: "Double-click canceled",
    pan: "Pan canceled",
    drag: "Drag canceled",
    scroll: "Scroll canceled",
    zoom: "Zoom canceled",
  });

  function isValidArm(mode) {
    return ARM_VALUES.includes(mode);
  }

  function isTapArm(mode) {
    return TAP_ARMS.includes(mode);
  }

  function isOneFingerDragArm(mode) {
    return ONE_FINGER_DRAG_ARMS.includes(mode);
  }

  function toggleArm(current, requested) {
    if (!isValidArm(requested)) return GESTURE_ARMS.GESTURES;
    return current === requested ? GESTURE_ARMS.GESTURES : requested;
  }

  function consumesOnGesture(mode) {
    return mode !== GESTURE_ARMS.GESTURES;
  }

  function effectiveTouchDragArm(mode) {
    if (mode === GESTURE_ARMS.GESTURES || mode === GESTURE_ARMS.LEFT) return GESTURE_ARMS.PAN;
    return mode;
  }

  function armStatusAfterToggle(previous, next, requested) {
    return next === requested ? ARM_ARMED_STATUS[requested] : ARM_CANCELED_STATUS[requested];
  }

  return {
    GESTURE_ARMS,
    ARM_VALUES,
    TAP_ARMS,
    ONE_FINGER_DRAG_ARMS,
    ARM_BUTTON_IDS,
    ARM_LABELS,
    ARM_ARMED_STATUS,
    ARM_CANCELED_STATUS,
    isValidArm,
    isTapArm,
    isOneFingerDragArm,
    toggleArm,
    consumesOnGesture,
    effectiveTouchDragArm,
    armStatusAfterToggle,
  };
}));
