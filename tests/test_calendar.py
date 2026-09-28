import tempfile
import unittest
from pathlib import Path

from calendar_manager import export_ics


class CalendarTests(unittest.TestCase):
    def test_export_ics(self):
        events = [
            {
                "title": "Dentist",
                "start_at": "2026-09-22T14:30:00",
                "end_at": "2026-09-22T15:30:00",
                "reminder_minutes": 30,
                "source_text": "Dentist next Tuesday at 2:30 PM.",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = export_ics(events, Path(tmp) / "schedule.ics")
            content = path.read_text(encoding="utf-8")

            self.assertIn("BEGIN:VCALENDAR", content)
            self.assertIn("SUMMARY:Dentist", content)
            self.assertIn("BEGIN:VALARM", content)
            self.assertIn("TRIGGER:-PT30M", content)


if __name__ == "__main__":
    unittest.main()
