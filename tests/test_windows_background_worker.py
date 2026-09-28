import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import reminder


class WindowsBackgroundWorkerTests(unittest.TestCase):
    def test_frozen_windows_prefers_dedicated_worker_beside_main_exe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_exe = root / "HT-SmartScheduler.exe"
            worker_exe = root / "HT-SmartScheduler-Reminder.exe"
            main_exe.write_bytes(b"")
            worker_exe.write_bytes(b"")

            with mock.patch("reminder.platform.system", return_value="Windows"), \
                 mock.patch.object(reminder.sys, "executable", str(main_exe)), \
                 mock.patch.object(reminder.sys, "frozen", True, create=True):
                self.assertEqual(reminder._windows_worker_executable(), worker_exe)

    def test_start_background_service_launches_dedicated_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_exe = root / "HT-SmartScheduler.exe"
            worker_exe = root / "HT-SmartScheduler-Reminder.exe"
            main_exe.write_bytes(b"")
            worker_exe.write_bytes(b"")
            pid_path = root / "service.pid"
            log_path = root / "service.log"
            heartbeat = root / "heartbeat.json"

            proc = mock.Mock(pid=43210)
            with mock.patch("reminder.platform.system", return_value="Windows"), \
                 mock.patch.object(reminder.sys, "executable", str(main_exe)), \
                 mock.patch.object(reminder.sys, "frozen", True, create=True), \
                 mock.patch.object(reminder, "PID_PATH", pid_path), \
                 mock.patch.object(reminder, "LOG_PATH", log_path), \
                 mock.patch.object(reminder, "HEARTBEAT_PATH", heartbeat), \
                 mock.patch("reminder.reminder_service_status", return_value=(False, None)), \
                 mock.patch("reminder.subprocess.Popen", return_value=proc) as popen:
                started, pid = reminder.start_background_service()

            self.assertTrue(started)
            self.assertEqual(pid, 43210)
            self.assertEqual(popen.call_args.args[0][0], str(worker_exe))
            self.assertIn("--reminders-daemon", popen.call_args.args[0])
            kwargs = popen.call_args.kwargs
            flags = kwargs.get("creationflags", 0)
            self.assertTrue(flags & 0x00000008)
            self.assertTrue(flags & 0x00000200)
            self.assertTrue(flags & 0x08000000)
            self.assertTrue(flags & 0x01000000)
            self.assertEqual(kwargs["env"].get("PYINSTALLER_RESET_ENVIRONMENT"), "1")

    def test_breakaway_access_denied_retries_without_breakaway_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main_exe = root / "HT-SmartScheduler.exe"
            worker_exe = root / "HT-SmartScheduler-Reminder.exe"
            main_exe.write_bytes(b"")
            worker_exe.write_bytes(b"")

            denied = OSError("breakaway denied")
            denied.winerror = 5
            proc = mock.Mock(pid=54321)
            with mock.patch("reminder.platform.system", return_value="Windows"), \
                 mock.patch.object(reminder.sys, "executable", str(main_exe)), \
                 mock.patch.object(reminder.sys, "frozen", True, create=True), \
                 mock.patch.object(reminder, "PID_PATH", root / "service.pid"), \
                 mock.patch.object(reminder, "LOG_PATH", root / "service.log"), \
                 mock.patch.object(reminder, "HEARTBEAT_PATH", root / "heartbeat.json"), \
                 mock.patch("reminder.reminder_service_status", return_value=(False, None)), \
                 mock.patch("reminder.subprocess.Popen", side_effect=[denied, proc]) as popen:
                started, pid = reminder.start_background_service()

            self.assertTrue(started)
            self.assertEqual(pid, 54321)
            self.assertEqual(popen.call_count, 2)
            first_flags = popen.call_args_list[0].kwargs["creationflags"]
            second_flags = popen.call_args_list[1].kwargs["creationflags"]
            self.assertTrue(first_flags & 0x01000000)
            self.assertFalse(second_flags & 0x01000000)
            self.assertTrue(second_flags & 0x00000008)
            self.assertTrue(second_flags & 0x00000200)


if __name__ == "__main__":
    unittest.main()
