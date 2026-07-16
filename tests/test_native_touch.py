from __future__ import annotations

import ctypes
import time
import unittest
from unittest import mock

from phone_link import windows_host


class NativeTouchTests(unittest.TestCase):
    def setUp(self) -> None:
        windows_host._stop_touch_cursor_guard(settle_seconds=0)
        windows_host._touch_initialized = False
        windows_host._touch_contact_active = False
        windows_host._touch_contact_point = (0, 0)
        windows_host._touch_gesture_id = ""

    def test_touch_tap_emits_native_down_and_up(self) -> None:
        with (
            mock.patch.object(windows_host, "_inject_touch_contact") as inject,
            mock.patch.object(windows_host.time, "sleep") as sleep,
        ):
            windows_host._handle_native_touch("touch_tap", 120, 240)

        self.assertEqual(
            inject.call_args_list,
            [mock.call("down", 120, 240, gesture_id=""), mock.call("up", 120, 240, gesture_id="")],
        )
        sleep.assert_called_once_with(0.015)

    def test_touch_up_reuses_last_injected_point(self) -> None:
        windows_host._touch_initialized = True
        windows_host._touch_contact_active = True
        windows_host._touch_contact_point = (120, 240)
        with (
            mock.patch.object(windows_host, "_inject_touch_contact_unlocked") as inject,
            mock.patch.object(windows_host, "_schedule_touch_cursor_guard_stop"),
        ):
            windows_host._inject_touch_contact("up", 180, 300)

        inject.assert_called_once_with("up", 120, 240)
        self.assertFalse(windows_host._touch_contact_active)

    def test_touch_hold_sends_keepalive_updates_before_up(self) -> None:
        with (
            mock.patch.object(windows_host, "_inject_touch_contact") as inject,
            mock.patch.object(windows_host.time, "sleep") as sleep,
        ):
            windows_host._handle_native_touch("touch_hold", 120, 240)

        self.assertEqual(inject.call_args_list[0], mock.call("down", 120, 240, gesture_id=""))
        self.assertEqual(inject.call_args_list[-1], mock.call("up", 120, 240, gesture_id=""))
        self.assertGreaterEqual(inject.call_args_list.count(mock.call("move", 120, 240, gesture_id="")), 3)
        self.assertTrue(all(call_arg == mock.call(0.12) for call_arg in sleep.call_args_list))

    def test_native_touch_failure_clears_active_contact(self) -> None:
        windows_host._touch_initialized = True
        windows_host._touch_contact_active = True
        windows_host._touch_contact_point = (120, 240)
        failure = OSError(87, "Windows rejected native touch input.")
        with (
            mock.patch.object(windows_host, "_inject_touch_contact_unlocked", side_effect=failure),
            mock.patch.object(windows_host, "_stop_touch_cursor_guard"),
        ):
            with self.assertRaises(OSError):
                windows_host._inject_touch_contact("move", 130, 250)

        self.assertFalse(windows_host._touch_contact_active)

    def test_stale_release_cannot_cancel_new_gesture(self) -> None:
        windows_host._touch_initialized = True
        windows_host._touch_contact_active = True
        windows_host._touch_contact_point = (120, 240)
        windows_host._touch_gesture_id = "gesture-new"
        with mock.patch.object(windows_host, "_inject_touch_contact_unlocked") as inject:
            windows_host._inject_touch_contact("up", 120, 240, gesture_id="gesture-old")

        inject.assert_not_called()
        self.assertTrue(windows_host._touch_contact_active)

    def test_error_87_move_recovers_as_fresh_down(self) -> None:
        windows_host._touch_initialized = True
        windows_host._touch_contact_active = True
        windows_host._touch_contact_point = (120, 240)
        windows_host._touch_gesture_id = "gesture-1"
        failure = OSError(87, "Windows rejected native touch input.")
        with (
            mock.patch.object(windows_host, "_inject_touch_contact_unlocked", side_effect=[failure, None]) as inject,
            mock.patch.object(windows_host, "_stop_touch_cursor_guard"),
            mock.patch.object(windows_host, "_start_touch_cursor_guard"),
            mock.patch.object(windows_host.time, "sleep"),
        ):
            windows_host._inject_touch_contact("move", 130, 250, gesture_id="gesture-1")

        self.assertEqual(inject.call_args_list[-1], mock.call("down", 130, 250))
        self.assertTrue(windows_host._touch_contact_active)
        self.assertEqual(windows_host._touch_contact_point, (130, 250))

    def test_emergency_cancel_resets_active_contact(self) -> None:
        windows_host._touch_contact_active = True
        windows_host._touch_contact_point = (120, 240)
        windows_host._touch_gesture_id = "gesture-1"
        with (
            mock.patch.object(windows_host, "_inject_touch_contact_unlocked") as inject,
            mock.patch.object(windows_host, "_stop_touch_cursor_guard"),
        ):
            released = windows_host.cancel_active_touch(gesture_id="gesture-1", reason="pagehide")

        self.assertTrue(released)
        inject.assert_called_once_with("cancel", 120, 240)
        self.assertFalse(windows_host._touch_contact_active)

    def test_touch_pointer_action_does_not_move_mouse_cursor(self) -> None:
        with (
            mock.patch.object(windows_host, "_ensure_window", return_value=55),
            mock.patch.object(windows_host, "focus_window"),
            mock.patch.object(windows_host, "get_window_rect", return_value=(10, 20, 110, 220)),
            mock.patch.object(windows_host, "_handle_native_touch") as native_touch,
            mock.patch.object(windows_host.win32api, "SetCursorPos") as set_cursor,
        ):
            windows_host.handle_pointer(55, "touch_tap", 0.5, 0.5)

        native_touch.assert_called_once_with("touch_tap", 59, 119, gesture_id="")
        set_cursor.assert_not_called()

    def test_touch_drag_focuses_once_on_down(self) -> None:
        with (
            mock.patch.object(windows_host, "_ensure_window", return_value=55),
            mock.patch.object(windows_host, "focus_window") as focus,
            mock.patch.object(windows_host, "get_window_rect", return_value=(0, 0, 100, 100)),
            mock.patch.object(windows_host, "_handle_native_touch"),
        ):
            windows_host.handle_pointer(55, "touch_down", 0.1, 0.1)
            windows_host.handle_pointer(55, "touch_move", 0.2, 0.2)
            windows_host.handle_pointer(55, "touch_up", 0.3, 0.3)

        focus.assert_called_once_with(55)

    def test_injected_contact_uses_touch_flags_and_screen_point(self) -> None:
        captured: dict[str, object] = {}

        def capture_contact(count: int, contact_pointer: object) -> bool:
            contact = ctypes.cast(
                contact_pointer,
                ctypes.POINTER(windows_host.POINTER_TOUCH_INFO),
            ).contents
            captured.update(
                count=count,
                pointer_type=contact.pointerInfo.pointerType,
                pointer_flags=contact.pointerInfo.pointerFlags,
                point=(contact.pointerInfo.ptPixelLocation.x, contact.pointerInfo.ptPixelLocation.y),
                raw_point=(contact.pointerInfo.ptPixelLocationRaw.x, contact.pointerInfo.ptPixelLocationRaw.y),
                raw_contact=(
                    contact.rcContactRaw.left,
                    contact.rcContactRaw.top,
                    contact.rcContactRaw.right,
                    contact.rcContactRaw.bottom,
                ),
            )
            return True

        with mock.patch.object(windows_host, "inject_touch_input", side_effect=capture_contact):
            windows_host._inject_touch_contact_unlocked("down", 321, 654)

        self.assertEqual(captured["count"], 1)
        self.assertEqual(captured["pointer_type"], windows_host.PT_TOUCH)
        self.assertEqual(
            captured["pointer_flags"],
            windows_host.POINTER_FLAG_INRANGE
            | windows_host.POINTER_FLAG_INCONTACT
            | windows_host.POINTER_FLAG_DOWN,
        )
        self.assertEqual(captured["point"], (321, 654))
        self.assertEqual(captured["raw_point"], (0, 0))
        self.assertEqual(captured["raw_contact"], (0, 0, 0, 0))

    def test_touch_cancel_uses_canceled_up_flags(self) -> None:
        captured: dict[str, int] = {}

        def capture_contact(count: int, contact_pointer: object) -> bool:
            contact = ctypes.cast(contact_pointer, ctypes.POINTER(windows_host.POINTER_TOUCH_INFO)).contents
            captured["flags"] = contact.pointerInfo.pointerFlags
            return True

        with mock.patch.object(windows_host, "inject_touch_input", side_effect=capture_contact):
            windows_host._inject_touch_contact_unlocked("cancel", 321, 654)

        self.assertEqual(captured["flags"], windows_host.POINTER_FLAG_CANCELED | windows_host.POINTER_FLAG_UP)

    def test_touch_injection_pins_and_restores_system_cursor_bounds(self) -> None:
        clip_calls: list[tuple[int, int, int, int] | None] = []

        def save_existing_clip(rect_pointer: object) -> bool:
            rect = ctypes.cast(rect_pointer, ctypes.POINTER(windows_host.RECT)).contents
            rect.left, rect.top, rect.right, rect.bottom = (-100, -50, 2400, 1400)
            return True

        def record_clip(rect_pointer: object) -> bool:
            if not rect_pointer:
                clip_calls.append(None)
                return True
            rect = ctypes.cast(rect_pointer, ctypes.POINTER(windows_host.RECT)).contents
            clip_calls.append((rect.left, rect.top, rect.right, rect.bottom))
            return True

        with (
            mock.patch.object(windows_host, "get_clip_cursor", side_effect=save_existing_clip),
            mock.patch.object(windows_host, "clip_cursor", side_effect=record_clip),
            mock.patch.object(windows_host, "inject_touch_input", return_value=True),
            mock.patch.object(windows_host.win32api, "GetCursorPos", return_value=(900, 700)),
            mock.patch.object(windows_host.win32api, "SetCursorPos") as set_cursor,
        ):
            windows_host._inject_touch_input_preserving_cursor(windows_host.POINTER_TOUCH_INFO())

        self.assertEqual(clip_calls, [(900, 700, 901, 701), (-100, -50, 2400, 1400)])
        set_cursor.assert_not_called()

    def test_cursor_guard_reverses_touch_to_mouse_promotion(self) -> None:
        cursor = [(900, 700)]
        clip_calls: list[tuple[int, int, int, int]] = []

        def set_cursor(point: tuple[int, int]) -> None:
            cursor[0] = point

        def save_clip(rect_pointer: object) -> bool:
            rect = ctypes.cast(rect_pointer, ctypes.POINTER(windows_host.RECT)).contents
            rect.left, rect.top, rect.right, rect.bottom = (-100, -50, 2400, 1400)
            return True

        def record_clip(rect_pointer: object) -> bool:
            rect = ctypes.cast(rect_pointer, ctypes.POINTER(windows_host.RECT)).contents
            clip_calls.append((rect.left, rect.top, rect.right, rect.bottom))
            return True

        with (
            mock.patch.object(windows_host.win32api, "GetCursorPos", side_effect=lambda: cursor[0]),
            mock.patch.object(windows_host.win32api, "SetCursorPos", side_effect=set_cursor),
            mock.patch.object(windows_host, "get_clip_cursor", side_effect=save_clip),
            mock.patch.object(windows_host, "clip_cursor", side_effect=record_clip),
        ):
            windows_host._start_touch_cursor_guard()
            cursor[0] = (120, 240)
            deadline = time.perf_counter() + 0.1
            while cursor[0] != (900, 700) and time.perf_counter() < deadline:
                time.sleep(0.002)
            windows_host._stop_touch_cursor_guard(settle_seconds=0)

        self.assertEqual(cursor[0], (900, 700))
        self.assertEqual(clip_calls[0], (900, 700, 901, 701))
        self.assertEqual(clip_calls[-1], (-100, -50, 2400, 1400))


if __name__ == "__main__":
    unittest.main()
