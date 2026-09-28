import tempfile
import unittest
from pathlib import Path

from database import SchedulerDatabase
from main import process_note


class MainFlowTests(unittest.TestCase):
    def test_note_is_processed_without_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")

            saved, incomplete = process_note(
                "meeting at 2\nmeeting doctor tomorrow at 9 am",
                db,
            )

            self.assertEqual(saved, 1)
            self.assertEqual(incomplete, 1)

            events = db.list_events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["title"], "meeting doctor")


if __name__ == "__main__":
    unittest.main()
