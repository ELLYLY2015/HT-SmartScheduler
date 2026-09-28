import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from database import SchedulerDatabase
from reminder import check_reminders


class WindowsSimultaneousDeliveryTests(unittest.TestCase):
    def test_gui_popup_uses_async_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            now = datetime(2026, 9, 25, 22, 0)
            start = now + timedelta(minutes=2)
            db.add_event(
                title="Parallel reminder",
                start_at=start,
                end_at=start + timedelta(minutes=30),
                reminder_minutes=2,
                reminder_mode="both",
            )
            parent = object()
            calls = []
            def popup(*args, **kwargs):
                calls.append("popup")
                return True
            def voice(*args, **kwargs):
                calls.append("voice")
                return True
            with mock.patch("reminder.show_popup", side_effect=popup), \
                 mock.patch("reminder.speak_async", side_effect=voice) as async_voice, \
                 mock.patch("reminder.speak") as sync_voice:
                triggered = check_reminders(db, now=now, popup_parent=parent)
            self.assertEqual(len(triggered), 1)
            self.assertEqual(calls, ["popup", "voice"])
            async_voice.assert_called_once()
            sync_voice.assert_not_called()


class PopupPaintOrderingTests(unittest.TestCase):
    def test_windows_popup_is_fully_painted_before_voice_starts(self):
        from voice import show_popup

        order = []

        class FakePopup:
            def deiconify(self):
                order.append("deiconify")
            def lift(self):
                order.append("lift")
            def update_idletasks(self):
                order.append("idle")
            def update(self):
                order.append("paint")

        parent = object()
        with mock.patch("popup_window.open_large_popup", return_value=FakePopup()):
            self.assertTrue(show_popup("hello", parent=parent))

        self.assertIn("paint", order)
        self.assertLess(order.index("idle"), order.index("paint"))


if __name__ == "__main__":
    unittest.main()
