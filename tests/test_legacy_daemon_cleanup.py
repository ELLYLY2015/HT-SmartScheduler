import unittest
from reminder import _parse_unix_daemon_pids


class LegacyDaemonCleanupTests(unittest.TestCase):
    def test_finds_old_and_new_scheduler_daemons_only(self):
        listing = """
  101 /Applications/HT-SmartScheduler.app/Contents/MacOS/HT-SmartScheduler --reminders-daemon
  202 /usr/bin/python3 /tmp/main.py --reminders-daemon
  303 /Applications/HT-SmartScheduler.app/Contents/MacOS/HT-SmartScheduler
  404 /usr/bin/python3 unrelated.py --reminders-daemon
"""
        self.assertEqual(_parse_unix_daemon_pids(listing), {101, 202})


if __name__ == "__main__":
    unittest.main()
