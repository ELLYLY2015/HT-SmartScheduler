import unittest
from datetime import datetime

from extractor import extract_event
from nlp.normalizer import normalize_text


class WeekendLanguageTests(unittest.TestCase):
    def setUp(self):

        self.base = datetime(2026, 9, 24, 2, 0)

    def test_this_weekend_with_time_resolves_to_saturday(self):
        event = extract_event("meeting a friend this weekend at 9 am", self.base)
        self.assertEqual(event.date_text.lower(), "this weekend")
        self.assertEqual(event.start_at, datetime(2026, 9, 26, 9, 0))
        self.assertEqual(event.duty, "meeting a friend")
        self.assertEqual(event.timing_kind, "exact")

    def test_user_example_typo_weeken_is_repaired(self):
        event = extract_event("meeting a friend this weeken at 9 am", self.base)
        self.assertEqual(event.date_text.lower(), "this weekend")
        self.assertEqual(event.start_at, datetime(2026, 9, 26, 9, 0))
        self.assertEqual(event.duty, "meeting a friend")

    def test_fuzzy_weekend_and_modifier_typos(self):
        event = extract_event("meet friend ths weknd at 9 am", self.base)
        self.assertEqual(event.date_text.lower(), "this weekend")
        self.assertEqual(event.start_at, datetime(2026, 9, 26, 9, 0))

    def test_next_weekend_and_typo(self):
        event = extract_event("golf nex weeknd at 8 am", self.base)
        self.assertEqual(event.date_text.lower(), "next weekend")
        self.assertEqual(event.start_at, datetime(2026, 10, 3, 8, 0))
        self.assertEqual(event.duty, "golf")

    def test_coming_weekend_means_nearest_upcoming_weekend(self):
        event = extract_event("dinner coming weekend at 7 pm", self.base)
        self.assertEqual(event.date_text.lower(), "weekend")
        self.assertEqual(event.start_at, datetime(2026, 9, 26, 19, 0))

    def test_weekend_after_next(self):
        event = extract_event("golf weekend after next at 9 am", self.base)
        self.assertEqual(event.date_text.lower(), "weekend after next")
        self.assertEqual(event.start_at, datetime(2026, 10, 10, 9, 0))

    def test_bare_weekend(self):
        event = extract_event("see family weekend at 11 am", self.base)
        self.assertEqual(event.date_text.lower(), "weekend")
        self.assertEqual(event.start_at, datetime(2026, 9, 26, 11, 0))

    def test_normalizer_preserves_non_timing_words(self):
        self.assertEqual(
            normalize_text("finish weekendhouse notes"),
            "finish weekendhouse notes",
        )


if __name__ == "__main__":
    unittest.main()
