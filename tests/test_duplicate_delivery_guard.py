import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from database import SchedulerDatabase
import reminder


class DuplicateDeliveryGuardTests(unittest.TestCase):
    def test_two_pollers_cannot_deliver_same_reminder(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.db"
            db1 = SchedulerDatabase(path)
            db2 = SchedulerDatabase(path)
            now = datetime(2026, 9, 25, 21, 0)
            start = now + timedelta(minutes=2)
            db1.add_event(
                title="Meeting",
                start_at=start,
                end_at=start + timedelta(minutes=30),
                reminder_minutes_list=[2],
                reminder_mode="both",
            )


            first_candidate = db1.reminder_candidates(now=now)[0]
            second_candidate = db2.reminder_candidates(now=now)[0]
            self.assertTrue(db1.try_claim_reminder_delivery(first_candidate, now))
            self.assertFalse(db2.try_claim_reminder_delivery(second_candidate, now))

    def test_check_reminders_skips_preclaimed_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.db"
            db = SchedulerDatabase(path)
            now = datetime(2026, 9, 25, 21, 0)
            start = now + timedelta(minutes=2)
            db.add_event(
                title="Meeting",
                start_at=start,
                end_at=start + timedelta(minutes=30),
                reminder_minutes_list=[2],
                reminder_mode="both",
            )
            candidate = db.reminder_candidates(now=now)[0]
            self.assertTrue(db.try_claim_reminder_delivery(candidate, now))

            with patch("reminder.show_notification") as notification, \
                 patch("reminder.show_popup") as popup, \
                 patch("reminder.speak") as speak:
                triggered = reminder.check_reminders(db, now=now)

            self.assertEqual(triggered, [])
            notification.assert_not_called()
            popup.assert_not_called()
            speak.assert_not_called()


if __name__ == "__main__":
    unittest.main()
