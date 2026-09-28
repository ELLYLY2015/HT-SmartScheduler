import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from database import SchedulerDatabase


class DatabaseTests(unittest.TestCase):
    def test_add_list_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")

            event_id = db.add_event(
                title="Test",
                start_at=datetime(2026, 9, 20, 15, 0),
                end_at=datetime(2026, 9, 20, 16, 0),
                reminder_minutes=30,
            )

            self.assertGreater(event_id, 0)
            self.assertEqual(len(db.list_events()), 1)

            conflicts = db.find_conflicts(
                datetime(2026, 9, 20, 15, 30),
                datetime(2026, 9, 20, 16, 30),
            )
            self.assertEqual(len(conflicts), 1)

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")

            event_id = db.add_event(
                title="Cancel me",
                start_at=datetime(2026, 9, 20, 15, 0),
                end_at=datetime(2026, 9, 20, 16, 0),
            )

            self.assertTrue(db.cancel_event(event_id))
            self.assertEqual(db.list_events(), [])
            self.assertEqual(db.reminder_candidates(datetime(2026, 9, 20, 14, 30)), [])


if __name__ == "__main__":
    unittest.main()
