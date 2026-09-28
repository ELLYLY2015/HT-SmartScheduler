import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from database import SchedulerDatabase
from reminder import check_reminders


class ReminderDeliveryTests(unittest.TestCase):
    def _make_event(self, mode: str):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = SchedulerDatabase(Path(tmp.name) / "test.db")
        now = datetime(2026, 9, 23, 10, 0)
        start = now + timedelta(minutes=10)
        event_id = db.add_event(
            title="Delivery test",
            start_at=start,
            end_at=start + timedelta(minutes=30),
            reminder_minutes=10,
            reminder_mode=mode,
        )
        return db, now, event_id

    def test_database_persists_reminder_mode(self):
        db, _now, event_id = self._make_event("voice")
        self.assertEqual(db.get_event(event_id)["reminder_mode"], "voice")

    @patch("reminder.speak", return_value=True)
    @patch("reminder.show_popup", return_value=True)
    @patch("reminder.show_notification", return_value=True)
    def test_popup_only_does_not_speak(self, notification, popup, speak):
        db, now, _event_id = self._make_event("popup")
        triggered = check_reminders(db, now=now)
        self.assertEqual(len(triggered), 1)
        notification.assert_not_called()
        popup.assert_called_once()
        self.assertTrue(popup.call_args.kwargs["enabled"])
        speak.assert_called_once()
        self.assertFalse(speak.call_args.kwargs["enabled"])

    @patch("reminder.speak", return_value=True)
    @patch("reminder.show_popup", return_value=True)
    @patch("reminder.show_notification", return_value=True)
    def test_voice_only_does_not_show_popup(self, notification, popup, speak):
        db, now, _event_id = self._make_event("voice")
        triggered = check_reminders(db, now=now)
        self.assertEqual(len(triggered), 1)
        notification.assert_not_called()
        popup.assert_called_once()
        self.assertFalse(popup.call_args.kwargs["enabled"])
        speak.assert_called_once()
        self.assertTrue(speak.call_args.kwargs["enabled"])

    @patch("reminder.speak", return_value=True)
    @patch("reminder.show_popup", return_value=True)
    @patch("reminder.show_notification", return_value=True)
    def test_both_enables_popup_and_voice(self, notification, popup, speak):
        db, now, _event_id = self._make_event("both")
        triggered = check_reminders(db, now=now)
        self.assertEqual(len(triggered), 1)
        notification.assert_not_called()
        self.assertTrue(popup.call_args.kwargs["enabled"])
        self.assertTrue(speak.call_args.kwargs["enabled"])


if __name__ == "__main__":
    unittest.main()
