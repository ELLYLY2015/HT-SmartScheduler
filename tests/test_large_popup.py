import unittest

from popup_window import preferred_popup_geometry


class LargePopupTests(unittest.TestCase):
    def test_desktop_popup_is_large_and_centered(self):
        width, height, x, y = preferred_popup_geometry(1440, 900)
        self.assertEqual((width, height), (900, 450))
        self.assertEqual(x, (1440 - 900) // 2)
        self.assertEqual(y, (900 - 450) // 2)

    def test_popup_never_exceeds_small_screen(self):
        width, height, x, y = preferred_popup_geometry(640, 480)
        self.assertLessEqual(width, 640)
        self.assertLessEqual(height, 480)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


if __name__ == "__main__":
    unittest.main()
