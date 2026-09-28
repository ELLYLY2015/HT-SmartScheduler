from datetime import datetime
import unittest

from app import format_header_datetime


class HeaderClockTests(unittest.TestCase):
    def test_friendly_date_and_time(self):
        date_text, time_text = format_header_datetime(datetime(2026, 8, 10, 22, 42))
        self.assertEqual(date_text, "Monday, August 10, 2026")
        self.assertEqual(time_text, "10:42 PM")


if __name__ == "__main__":
    unittest.main()
