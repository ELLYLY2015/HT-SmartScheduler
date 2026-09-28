import unittest
from unittest.mock import Mock, patch

import reminder
import voice


class WindowsHiddenSubprocessTests(unittest.TestCase):
    def test_daemon_discovery_hides_powershell_window(self):
        completed = Mock(stdout="", returncode=0)
        with patch("reminder.platform.system", return_value="Windows"), \
             patch("reminder.subprocess.run", return_value=completed) as run, \
             patch("reminder.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch("reminder.subprocess.STARTUPINFO", None, create=True):
            reminder.find_all_reminder_daemon_pids()

        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs.get("creationflags"), 0x08000000)
        self.assertIn("-NonInteractive", run.call_args.args[0])

    def test_windows_voice_hides_powershell_window(self):
        completed = Mock(returncode=0)
        with patch("voice.platform.system", return_value="Windows"), \
             patch("voice.subprocess.run", return_value=completed) as run, \
             patch("voice.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch("voice.subprocess.STARTUPINFO", None, create=True):
            self.assertTrue(voice.speak("test reminder", enabled=True))

        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs.get("creationflags"), 0x08000000)
        self.assertIs(kwargs.get("stdout"), voice.subprocess.DEVNULL)
        self.assertIs(kwargs.get("stderr"), voice.subprocess.DEVNULL)


if __name__ == "__main__":
    unittest.main()
