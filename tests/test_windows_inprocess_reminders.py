import unittest
from unittest import mock

import app
import reminder
import voice


class DummyRoot:
    def __init__(self):
        self.calls = []

    def after(self, ms, fn):
        self.calls.append((ms, fn))


class WindowsReminderArchitectureTests(unittest.TestCase):
    def test_show_popup_with_parent_does_not_spawn_subprocess(self):
        parent = object()
        with mock.patch("popup_window.open_large_popup") as open_popup, \
             mock.patch("voice.subprocess.Popen") as popen:
            self.assertTrue(voice.show_popup("hello", parent=parent))
            open_popup.assert_called_once()
            popen.assert_not_called()

    def test_check_reminders_accepts_popup_parent(self):
        import inspect
        self.assertIn("popup_parent", inspect.signature(reminder.check_reminders).parameters)

    def test_windows_status_refresh_is_passive(self):
        obj = object.__new__(app.SmartSchedulerApp)
        obj.root = DummyRoot()
        obj.refresh_service_status = mock.Mock()

        obj._windows_service_status_refresh()

        obj.refresh_service_status.assert_called_once()
        self.assertEqual(obj.root.calls[0][0], 5000)


if __name__ == "__main__":
    unittest.main()
