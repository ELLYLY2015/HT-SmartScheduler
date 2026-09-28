import unittest
from datetime import datetime

from extractor import extract_event


class FutureVocabularyTests(unittest.TestCase):
    def setUp(self):
        self.base = datetime(2026, 9, 15, 12, 0, 0)

    def test_next_day(self):
        event = extract_event("doctor next day at 9 AM", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 16, 9, 0))
        self.assertEqual(event.timing_kind, "exact")

    def test_by_tomorrow(self):
        event = extract_event("finish report by tomorrow", base=self.base)
        self.assertEqual(event.timing_kind, "deadline_window")
        self.assertEqual(event.window_end, datetime(2026, 9, 16, 23, 59, 59))

    def test_by_next_week(self):
        event = extract_event("finish report by next week", base=self.base)
        self.assertEqual(event.timing_kind, "deadline_window")
        self.assertIsNotNone(event.window_end)

    def test_next_year(self):
        event = extract_event("renew license next year", base=self.base)
        self.assertEqual(event.timing_kind, "window")
        self.assertEqual(event.window_start.year, 2027)

    def test_vague_future_words(self):
        for text in [
            "call Sarah soon",
            "email John later",
            "organize files eventually",
            "visit Japan someday",
            "do it shortly",
            "respond presently",
            "check again momentarily",
            "handle it in the future",
            "follow up before long",
            "follow up after a while",
            "follow up after a few days",
            "finish it in time",
        ]:
            with self.subTest(text=text):
                event = extract_event(text, base=self.base)
                self.assertEqual(event.timing_kind, "vague_future")
                self.assertIsNone(event.start_at)

    def test_sequence_reference_phrases(self):
        for text in [
            "call her after that",
            "send it as soon as approved",
            "email him soon after",
            "leave right after",
            "call afterward",
            "do the next task following",
            "then call John",
            "when approved send it",
            "do this second",
            "do this third",
            "continue in turn",
            "consequently send the notice",
            "call after",
            "continue since",
        ]:
            with self.subTest(text=text):
                event = extract_event(text, base=self.base)
                self.assertEqual(event.timing_kind, "sequence_reference")
                self.assertIsNone(event.start_at)

    def test_ongoing_words(self):
        for text in [
            "exercise daily from now on",
            "backup files henceforth",
        ]:
            with self.subTest(text=text):
                event = extract_event(text, base=self.base)
                self.assertEqual(event.timing_kind, "ongoing")
                self.assertEqual(event.window_start, self.base)

    def test_immediately(self):
        event = extract_event("call doctor immediately", base=self.base)
        self.assertEqual(event.timing_kind, "immediate")
        self.assertEqual(event.start_at, self.base)

    def test_this_evening(self):
        event = extract_event("study this evening", base=self.base)
        self.assertEqual(event.start_at, datetime(2026, 9, 15, 19, 0))


if __name__ == "__main__":
    unittest.main()
