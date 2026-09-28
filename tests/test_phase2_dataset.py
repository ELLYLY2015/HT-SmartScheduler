import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nlp" / "data"


class Phase2DatasetTests(unittest.TestCase):
    def test_split_sizes(self):
        train = json.loads((DATA / "train.json").read_text())
        val = json.loads((DATA / "validation.json").read_text())
        test = json.loads((DATA / "test.json").read_text())

        self.assertEqual(len(train), 1100)
        self.assertEqual(len(val), 145)
        self.assertEqual(len(test), 145)

    def test_no_text_leakage_across_splits(self):
        train = {
            row["text"].lower()
            for row in json.loads((DATA / "train.json").read_text())
        }
        val = {
            row["text"].lower()
            for row in json.loads((DATA / "validation.json").read_text())
        }
        test = {
            row["text"].lower()
            for row in json.loads((DATA / "test.json").read_text())
        }

        self.assertFalse(train & val)
        self.assertFalse(train & test)
        self.assertFalse(val & test)


if __name__ == "__main__":
    unittest.main()
