import unittest
from unittest import mock

import app


class DummyRoot:
    def __init__(self):
        self.destroyed = False
        self.iconified = False

    def destroy(self):
        self.destroyed = True

    def iconify(self):
        self.iconified = True


class WindowsCloseBehaviorTests(unittest.TestCase):
    def test_windows_quit_closes_gui_without_stopping_background_worker(self):
        obj = object.__new__(app.SmartSchedulerApp)
        obj.root = DummyRoot()

        with mock.patch("app.stop_background_service") as stop_service:
            obj._windows_quit()

        self.assertTrue(obj.root.destroyed)
        self.assertFalse(obj.root.iconified)
        stop_service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
