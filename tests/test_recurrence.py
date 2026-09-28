import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from database import SchedulerDatabase
from recurrence import build_rrule, occurrences_between, recurrence_label
from reminder import check_reminders


class RecurrenceTests(unittest.TestCase):
    def test_build_weekly_rrule(self):
        rule = build_rrule("weekly", interval=2, count=5)
        self.assertEqual(rule, "RRULE:FREQ=WEEKLY;INTERVAL=2;COUNT=5")
        self.assertIn("Weekly", recurrence_label(rule))

    def test_weekday_occurrences_skip_weekend(self):
        start = datetime(2026, 9, 18, 9, 0)
        rule = build_rrule("weekdays")
        values = occurrences_between(
            start,
            rule,
            datetime(2026, 9, 18, 0, 0),
            datetime(2026, 9, 22, 23, 59),
        )
        self.assertEqual(
            [value.date().isoformat() for value in values],
            ["2026-09-18", "2026-09-21", "2026-09-22"],
        )

    def test_recurring_reminder_can_trigger_on_multiple_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            start = datetime(2026, 9, 20, 15, 0)
            db.add_event(
                title="Daily medication",
                start_at=start,
                end_at=start + timedelta(minutes=15),
                reminder_minutes=30,
                recurrence_rule=build_rrule("daily"),
            )

            first = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 30),
                speak_enabled=False,
                notifications_enabled=False,
            )
            repeated_same_time = check_reminders(
                db,
                now=datetime(2026, 9, 20, 14, 30),
                speak_enabled=False,
                notifications_enabled=False,
            )
            second_day = check_reminders(
                db,
                now=datetime(2026, 9, 21, 14, 30),
                speak_enabled=False,
                notifications_enabled=False,
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(len(repeated_same_time), 0)
            self.assertEqual(len(second_day), 1)


if __name__ == "__main__":
    unittest.main()
