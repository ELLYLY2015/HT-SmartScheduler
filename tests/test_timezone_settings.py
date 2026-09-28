import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from database import SchedulerDatabase
from timezone_utils import current_wall_time, validate_timezone_name


class TimeZoneSettingsTests(unittest.TestCase):
    def test_database_persists_user_timezone(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            self.assertIsNone(db.get_setting("time_zone"))
            db.set_setting("time_zone", "America/Chicago")
            self.assertEqual(db.get_setting("time_zone"), "America/Chicago")

    def test_validate_timezone(self):
        self.assertEqual(validate_timezone_name("America/Chicago"), "America/Chicago")
        with self.assertRaises(ValueError):
            validate_timezone_name("Central Time")

    def test_current_wall_time_matches_selected_zone(self):
        wall = current_wall_time("America/Chicago")
        expected = datetime.now(ZoneInfo("America/Chicago")).replace(tzinfo=None)
        self.assertLess(abs((wall - expected).total_seconds()), 5)


if __name__ == "__main__":
    unittest.main()
