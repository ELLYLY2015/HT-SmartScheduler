import unittest

from nlp.normalizer import normalize_text


class Phase2NormalizerTests(unittest.TestCase):
    def test_known_typos(self):
        self.assertEqual(
            normalize_text("docter tomorow in haf an hr"),
            "doctor tomorrow in half an hour",
        )

    def test_weekend_typos(self):
        self.assertEqual(normalize_text("this weeken at 9 am"), "this weekend at 9 am")
        self.assertEqual(normalize_text("ths weknd at 9 am"), "this weekend at 9 am")
        self.assertEqual(normalize_text("nex weeknd at 8 am"), "next weekend at 8 am")

    def test_does_not_guess_ambiguous_time(self):
        self.assertEqual(
            normalize_text("meeting at 2"),
            "meeting at 2",
        )


if __name__ == "__main__":
    unittest.main()
