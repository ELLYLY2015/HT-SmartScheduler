import unittest
from datetime import datetime

from extractor import extract_event


class NearTimingTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 9, 15, 20, 4, 0)

    def test_in_half_hour(self):
        event = extract_event("take medicine in half hour", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 20, 34))
        self.assertEqual(event.duty, "take medicine")
        self.assertEqual(event.timing_kind, "exact")

    def test_double_space_half_hour(self):
        event = extract_event("take medicine in half  hour", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 20, 34))

    def test_in_half_an_hour(self):
        event = extract_event("take medicine in half an hour", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 20, 34))

    def test_half_an_hour_from_now(self):
        event = extract_event("meeting half an hour from now", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 20, 34))

    def test_in_a_quarter_hour(self):
        event = extract_event("call John in a quarter hour", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 20, 19))

    def test_in_an_hour(self):
        event = extract_event("take medicine in an hour", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 21, 4))

    def test_in_one_and_a_half_hours(self):
        event = extract_event(
            "meeting in one and a half hours",
            base=self.base,
        )
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 21, 34))

    def test_in_1_point_5_hours(self):
        event = extract_event("meeting in 1.5 hours", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 21, 34))


if __name__ == "__main__":
    unittest.main()
