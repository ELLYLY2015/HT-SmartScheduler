import unittest

from app import (
    format_reminder_minutes,
    reminder_value_to_minutes,
    preferred_startup_geometry,
)


class AppHelperTests(unittest.TestCase):
    def test_units_convert_to_minutes(self):
        self.assertEqual(reminder_value_to_minutes(10, "minutes"), 10)
        self.assertEqual(reminder_value_to_minutes(2, "hours"), 120)
        self.assertEqual(reminder_value_to_minutes(1, "day"), 1440)

    def test_format_reminder_minutes(self):
        self.assertEqual(format_reminder_minutes(10), "10 min")
        self.assertEqual(format_reminder_minutes(60), "1 hour")
        self.assertEqual(format_reminder_minutes(1440), "1 day")

    def test_preferred_startup_geometry_keeps_comfortable_dashboard_size(self):
        width, height, x, y = preferred_startup_geometry(1440, 1200)
        self.assertEqual(width, 1416)
        self.assertEqual(height, 1010)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


    def test_preferred_startup_geometry_uses_more_vertical_space(self):
        width, height, x, y = preferred_startup_geometry(1490, 1024)
        self.assertEqual(width, 1440)
        self.assertEqual(height, 1010)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_preferred_startup_geometry_fits_smaller_display(self):
        width, height, x, y = preferred_startup_geometry(1280, 800)
        self.assertLessEqual(width, 1280)
        self.assertLessEqual(height, 800)
        self.assertGreaterEqual(width, 900)
        self.assertGreaterEqual(height, 720)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)

    def test_windows_startup_geometry_is_smaller_than_full_screen(self):
        width, height, x, y = preferred_startup_geometry(1228, 798, "win32")
        self.assertEqual(width, 1000)
        self.assertEqual(height, 650)
        self.assertEqual(x, 114)
        self.assertEqual(y, 74)

    def test_macos_startup_geometry_keeps_existing_size(self):
        width, height, x, y = preferred_startup_geometry(1490, 1024, "darwin")
        self.assertEqual(width, 1440)
        self.assertEqual(height, 1010)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


if __name__ == "__main__":
    unittest.main()
