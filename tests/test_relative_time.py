import unittest
from datetime import datetime

from extractor import extract_event


class RelativeTimeTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 9, 15, 12, 0, 0)

    def test_in_two_days(self):
        event = extract_event(
            "meeting in 2 days at 3 PM",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 17, 15, 0))

    def test_in_three_days_word_number(self):
        event = extract_event(
            "meeting in three days at 4 PM",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 18, 16, 0))

    def test_two_days_from_now(self):
        event = extract_event(
            "doctor two days from now at 9 AM",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 17, 9, 0))

    def test_after_three_days(self):
        event = extract_event(
            "call John after 3 days at 11 AM",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 18, 11, 0))

    def test_in_two_hours(self):
        event = extract_event(
            "take medicine in 2 hours",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 14, 0))
        self.assertEqual(event.duty, "take medicine")

    def test_tomorrow_evening(self):
        event = extract_event(
            "study tomorrow evening",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 16, 19, 0))

    def test_in_the_next_three_days_is_exact_relative_start(self):
        event = extract_event(
            "finish report in the next 3 days",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 18, 12, 0))
        self.assertEqual(event.timing_kind, "exact")

    def test_within_two_weeks_is_exact_relative_start(self):
        event = extract_event(
            "renew registration within 2 weeks",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 29, 12, 0))
        self.assertEqual(event.timing_kind, "exact")

    def test_within_fifteen_minutes_is_exact_relative_start(self):
        event = extract_event(
            "meeting within 15 minutes lasting 30 minutes today",
            base=self.base,
        )
        self.assertEqual(event.duty, "meeting")
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 12, 15))
        self.assertEqual(event.timing_kind, "exact")
        self.assertEqual(event.duration_minutes, 30)
        self.assertIsNone(event.confidence_notes)

    def test_next_minutes_then_in_quantity_means_start_then_duration(self):
        event = extract_event(
            "meeting in the next 20 minutes in 30 minutes",
            base=self.base,
        )
        self.assertEqual(event.duty, "meeting")
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 12, 20))
        self.assertEqual(event.duration_minutes, 30)

    def test_today_in_the_next_minutes_prioritizes_relative_start(self):
        event = extract_event(
            "Dentist today in the next 15 minutes lasting 30 minutes",
            base=self.base,
        )
        self.assertEqual(event.duty.lower(), "dentist")
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 12, 15))
        self.assertEqual(event.duration_minutes, 30)

    def test_in_next_two_hours_without_the(self):
        event = extract_event("call mom in next 2 hours", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 14, 0))

    def test_within_next_two_months(self):
        event = extract_event("renew insurance within next 2 months", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 11, 15, 12, 0))

    def test_date_without_clock_does_not_default_to_midnight(self):
        event = extract_event("meeting today", base=self.base)
        self.assertIsNone(event.start_at)
        self.assertIn("missing time", event.confidence_notes)

    def test_next_week_recognized_as_window(self):
        event = extract_event(
            "meet Sarah next week",
            base=self.base,
        )
        self.assertIsNone(event.start_at)
        self.assertIsNotNone(event.window_start)
        self.assertIsNotNone(event.window_end)

    def test_next_month_recognized_as_window(self):
        event = extract_event(
            "renew subscription next month",
            base=self.base,
        )
        self.assertIsNone(event.start_at)
        self.assertEqual(event.window_start.month, 10)

    def test_day_after_tomorrow(self):
        event = extract_event(
            "gym day after tomorrow at 6 PM",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 17, 18, 0))


if __name__ == "__main__":
    unittest.main()
