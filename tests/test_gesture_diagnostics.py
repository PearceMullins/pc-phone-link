from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from phone_link import gesture_diagnostics


class GestureDiagnosticsTests(unittest.TestCase):
    def test_log_is_jsonl_correlated_and_privacy_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "gesture-events.jsonl"
            with mock.patch.object(gesture_diagnostics, "GESTURE_LOG_PATH", path):
                with gesture_diagnostics.gesture_context(
                    {"session_id": "session-1", "request_id": "request-1", "gesture_id": "gesture-1"}
                ):
                    gesture_diagnostics.log_gesture(
                        "server-received",
                        {
                            "action": "touch_move",
                            "x": 0.123456,
                            "y": 0.987654,
                            "token": "secret-token",
                            "text": "typed secret",
                            "client_host": "192.168.1.2",
                            "window_title": "Private document",
                            "reason": "Private document title",
                        },
                    )
                payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(payload["details"]["session_id"], "session-1")
            self.assertEqual(payload["details"]["request_id"], "request-1")
            self.assertEqual(payload["details"]["x"], 0.1235)
            serialized = json.dumps(payload)
            for private_value in ("secret-token", "typed secret", "192.168.1.2", "Private document"):
                self.assertNotIn(private_value, serialized)

    def test_log_rotation_caps_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "gesture-events.jsonl"
            with (
                mock.patch.object(gesture_diagnostics, "GESTURE_LOG_PATH", path),
                mock.patch.object(gesture_diagnostics, "MAX_LOG_BYTES", 250),
                mock.patch.object(gesture_diagnostics, "MAX_LOG_FILES", 3),
            ):
                for index in range(20):
                    gesture_diagnostics.log_gesture("frame", {"request_id": f"request-{index}", "state": "x" * 80})
                files = list(path.parent.glob("gesture-events.jsonl*"))

            self.assertLessEqual(len(files), 3)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
