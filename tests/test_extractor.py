import unittest
from datetime import datetime

from extractor import (
    extract_event,
    extract_events,
    resolve_datetime,
)


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 9, 15, 12, 0, 0)

    def test_tomorrow_time_duration(self):
        event = extract_event(
            "Study Python tomorrow at 7 PM for 2 hours.",
            base=self.base,
        )
        self.assertEqual(event.duty, "Study Python")
        self.assertEqual(event.duration_minutes, 120)
        self.assertEqual(event.start_at, datetime(2026, 9, 16, 19, 0))

    def test_next_tuesday(self):
        event = extract_event(
            "Dentist next Tuesday at 2:30 PM.",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 22, 14, 30))
        self.assertEqual(event.duty, "Dentist")

    def test_daypart(self):
        event = extract_event(
            "Study DP-300 Wednesday evening for 2 hours.",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 16, 19, 0))
        self.assertEqual(event.duration_minutes, 120)

    def test_month_date(self):
        event = extract_event(
            "Doctor appointment September 22 at 3 PM.",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 22, 15, 0))

    def test_slash_date(self):
        value = resolve_datetime("9/22/2026", "3 PM", self.base)
        self.assertEqual(value, datetime(2026, 9, 22, 15, 0))

    def test_iso_date(self):
        value = resolve_datetime("2026-09-22", "15:30", self.base)
        self.assertEqual(value, datetime(2026, 9, 22, 15, 30))

    def test_multiple_sentences(self):
        events = extract_events(
            "Dentist tomorrow at 2 PM. Meeting Friday at 10 AM.",
            base=self.base,
        )
        self.assertEqual(len(events), 2)

    def test_reminder(self):
        event = extract_event(
            "Dentist tomorrow at 2 PM for 1 hour and remind me 30 minutes before.",
            base=self.base,
        )
        self.assertEqual(event.reminder_minutes, 30)
        self.assertEqual(event.duration_minutes, 60)
        self.assertEqual(event.duty, "Dentist")


    def test_bare_hour_is_recognized_but_ambiguous(self):
        event = extract_event(
            "meeting at 2",
            base=self.base,
        )
        self.assertEqual(event.duty, "meeting")
        self.assertEqual(event.time_text.lower(), "at 2")
        self.assertIsNone(event.start_at)
        self.assertIn("ambiguous", event.confidence_notes)

    def test_deadline(self):
        event = extract_event(
            "Finish ML homework by Friday at 11:59 PM.",
            base=self.base,
        )
        self.assertEqual(event.event_type, "deadline")
        self.assertTrue(event.duty.startswith("Finish ML homework"))


if __name__ == "__main__":
    unittest.main()
