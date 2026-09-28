import unittest
from datetime import datetime, timedelta

from recurrence import build_rrule, next_occurrence_on_or_after


class UpcomingEventsTests(unittest.TestCase):
    def test_future_one_time_event_is_upcoming(self):
        now = datetime(2026, 9, 23, 10, 0)
        start = now + timedelta(minutes=5)
        self.assertEqual(next_occurrence_on_or_after(start, None, now), start)

    def test_passed_one_time_event_is_not_upcoming(self):
        now = datetime(2026, 9, 23, 10, 0)
        start = now - timedelta(seconds=1)
        self.assertIsNone(next_occurrence_on_or_after(start, None, now))

    def test_daily_recurring_event_returns_next_day_after_first_passes(self):
        start = datetime(2026, 9, 20, 9, 0)
        now = datetime(2026, 9, 23, 10, 0)
        rule = build_rrule("daily")
        self.assertEqual(
            next_occurrence_on_or_after(start, rule, now),
            datetime(2026, 9, 24, 9, 0),
        )

    def test_finite_recurrence_disappears_after_last_occurrence(self):
        start = datetime(2026, 9, 20, 9, 0)
        now = datetime(2026, 9, 23, 10, 0)
        rule = build_rrule("daily", count=3)
        self.assertIsNone(next_occurrence_on_or_after(start, rule, now))

    def test_today_recurring_occurrence_remains_if_still_in_future(self):
        start = datetime(2026, 9, 20, 15, 0)
        now = datetime(2026, 9, 23, 14, 0)
        rule = build_rrule("daily")
        self.assertEqual(
            next_occurrence_on_or_after(start, rule, now),
            datetime(2026, 9, 23, 15, 0),
        )


if __name__ == "__main__":
    unittest.main()
