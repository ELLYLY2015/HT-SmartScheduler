import unittest
from datetime import datetime

from app import apply_datetime_overrides, parse_date_override, parse_time_override
from models import EventCandidate


class V11AppDetailTests(unittest.TestCase):
    def test_parse_structured_overrides(self):
        self.assertEqual(parse_date_override("09/25/2026").isoformat(), "2026-09-25")
        self.assertEqual(parse_time_override("2:30 PM").strftime("%H:%M"), "14:30")

    def test_structured_fields_can_complete_ambiguous_candidate(self):
        event = EventCandidate(source_text="Doctor", duty="Doctor")
        apply_datetime_overrides(event, "2026-09-25", "14:30")
        self.assertEqual(event.start_at, datetime(2026, 9, 25, 14, 30))
        self.assertIsNone(event.confidence_notes)


if __name__ == "__main__":
    unittest.main()
