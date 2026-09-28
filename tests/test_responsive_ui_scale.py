import unittest

from app import SmartSchedulerApp


class ResponsiveUIScaleTests(unittest.TestCase):
    def setUp(self):
        self.app = SmartSchedulerApp.__new__(SmartSchedulerApp)
        self.app._design_width = 1380
        self.app._design_height = 900
        self.app._ui_scale = 1.0

    def test_design_size_is_normal_scale(self):
        self.assertAlmostEqual(self.app._responsive_scale_for_size(1380, 900), 1.0)

    def test_larger_window_increases_scale(self):
        self.assertGreater(self.app._responsive_scale_for_size(1920, 1080), 1.2)

    def test_scale_is_capped(self):
        self.assertLessEqual(self.app._responsive_scale_for_size(6000, 4000), 1.55)

    def test_small_window_does_not_become_tiny(self):
        self.assertGreaterEqual(self.app._responsive_scale_for_size(900, 720), 0.95)

    def test_windows_scale_is_more_compact(self):
        self.app._windows_ui = True
        self.app._min_ui_scale = 0.52
        scale = self.app._responsive_scale_for_size(1000, 650)
        self.assertLess(scale, 0.65)
        self.assertGreaterEqual(scale, 0.52)


if __name__ == '__main__':
    unittest.main()
