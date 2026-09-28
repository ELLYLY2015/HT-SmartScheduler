import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from database import SchedulerDatabase
from reminder import check_reminders
from extractor import extract_event


class ReminderTests(unittest.TestCase):
    def test_reminder_triggers_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")

            now = datetime(2026, 9, 20, 14, 30)
            start = datetime(2026, 9, 20, 15, 0)

            db.add_event(
                title="Dentist",
                start_at=start,
                end_at=start + timedelta(hours=1),
                reminder_minutes=30,
            )

            first = check_reminders(
                db,
                now=now,
                speak_enabled=False,
                notifications_enabled=False,
            )
            second = check_reminders(
                db,
                now=now,
                speak_enabled=False,
                notifications_enabled=False,
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(len(second), 0)

    def test_overdue_reminder_triggers_before_event_starts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")



            now = datetime(2026, 9, 20, 14, 50)
            start = datetime(2026, 9, 20, 15, 0)

            db.add_event(
                title="Call doctor",
                start_at=start,
                end_at=start + timedelta(hours=1),
                reminder_minutes=30,
            )

            triggered = check_reminders(
                db,
                now=now,
                speak_enabled=False,
                notifications_enabled=False,
            )

            self.assertEqual(len(triggered), 1)
            self.assertEqual(triggered[0]["title"], "Call doctor")

    def test_relative_phrase_can_trigger_ten_minute_reminder(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            base = datetime(2026, 9, 18, 22, 29)
            event = extract_event(
                "Dentist today in the next 15 minutes lasting 30 minutes",
                base=base,
            )
            self.assertEqual(event.start_at, datetime(2026, 9, 18, 22, 44))
            self.assertEqual(event.duration_minutes, 30)

            db.add_event(
                title=event.duty,
                start_at=event.start_at,
                end_at=event.start_at + timedelta(minutes=event.duration_minutes),
                reminder_minutes=10,
            )


            triggered = check_reminders(
                db,
                now=datetime(2026, 9, 18, 22, 34),
                speak_enabled=False,
                notifications_enabled=False,
            )
            self.assertEqual(len(triggered), 1)
            self.assertEqual(triggered[0]["title"].lower(), "dentist")


if __name__ == "__main__":
    unittest.main()
