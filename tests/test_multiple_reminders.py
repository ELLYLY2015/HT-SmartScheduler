import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from calendar_manager import export_ics
from database import SchedulerDatabase
from reminder import check_reminders


class MultipleReminderTests(unittest.TestCase):
    def test_database_stores_multiple_reminders(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")

            event_id = db.add_event(
                title="Meeting",
                start_at=datetime(2026, 9, 20, 15, 0),
                end_at=datetime(2026, 9, 20, 16, 0),
                reminder_minutes_list=[1440, 60, 10],
            )

            self.assertEqual(
                db.get_event_reminders(event_id),
                [1440, 60, 10],
            )

    def test_each_reminder_can_trigger_at_its_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            start = datetime(2026, 9, 20, 15, 0)

            db.add_event(
                title="Meeting",
                start_at=start,
                end_at=start + timedelta(hours=1),
                reminder_minutes_list=[60, 30, 10],
            )

            first = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 0),
                speak_enabled=False,
                notifications_enabled=False,
            )
            second = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 30),
                speak_enabled=False,
                notifications_enabled=False,
            )
            third = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 50),
                speak_enabled=False,
                notifications_enabled=False,
            )

            self.assertEqual(
                [item["reminder_minutes"] for item in first + second + third],
                [60, 30, 10],
            )

    def test_missed_multiple_reminders_do_not_flood_user(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            start = datetime(2026, 9, 20, 15, 0)

            db.add_event(
                title="Meeting",
                start_at=start,
                end_at=start + timedelta(hours=1),
                reminder_minutes_list=[60, 30, 10],
            )

            triggered = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 55),
                speak_enabled=False,
                notifications_enabled=False,
            )

            self.assertEqual(len(triggered), 1)
            self.assertEqual(triggered[0]["reminder_minutes"], 10)

            again = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 56),
                speak_enabled=False,
                notifications_enabled=False,
            )
            self.assertEqual(again, [])

    def test_ics_contains_multiple_alarms(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = export_ics(
                [
                    {
                        "title": "Meeting",
                        "start_at": "2026-09-20T15:00:00",
                        "end_at": "2026-09-20T16:00:00",
                        "reminder_minutes_list": [60, 30, 10],
                        "source_text": "meeting",
                    }
                ],
                Path(tmp) / "schedule.ics",
            )

            content = path.read_text(encoding="utf-8")

            self.assertEqual(content.count("BEGIN:VALARM"), 3)
            self.assertIn("TRIGGER:-PT60M", content)
            self.assertIn("TRIGGER:-PT30M", content)
            self.assertIn("TRIGGER:-PT10M", content)


if __name__ == "__main__":
    unittest.main()
