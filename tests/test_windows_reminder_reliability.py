import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from database import SchedulerDatabase
from extractor import extract_event
import reminder


class WindowsReminderReliabilityTests(unittest.TestCase):
    def test_four_minute_event_two_minute_reminder_fires(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = SchedulerDatabase(Path(tmp) / "test.db")
            base = datetime(2026, 9, 24, 11, 28)
            event = extract_event("meeting in the next 4 minutes", base=base)
            self.assertEqual(event.start_at, base + timedelta(minutes=4))

            db.add_event(
                title=event.duty,
                start_at=event.start_at,
                end_at=event.start_at + timedelta(minutes=30),
                reminder_minutes_list=[2],
                reminder_mode="both",
            )

            with patch("reminder.show_notification", return_value=True) as notification, \
                 patch("reminder.show_popup", return_value=True) as popup, \
                 patch("reminder.speak", return_value=True) as speak:
                triggered = reminder.check_reminders(
                    db,
                    now=base + timedelta(minutes=2),
                )

            self.assertEqual(len(triggered), 1)
            notification.assert_not_called()
            popup.assert_called_once()
            speak.assert_called_once()
            self.assertTrue(popup.call_args.kwargs["enabled"])
            self.assertTrue(speak.call_args.kwargs["enabled"])

    def test_service_status_requires_live_heartbeat_after_startup_grace(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_path = Path(tmp) / "service.pid"
            heartbeat_path = Path(tmp) / "heartbeat.json"
            pid_path.write_text("12345", encoding="utf-8")

            old = time.time() - 120
            import os
            os.utime(pid_path, (old, old))

            with patch.object(reminder, "PID_PATH", pid_path), \
                 patch.object(reminder, "HEARTBEAT_PATH", heartbeat_path), \
                 patch("reminder.process_is_running", return_value=True):
                running, pid = reminder.reminder_service_status()

            self.assertFalse(running)
            self.assertIsNone(pid)
            self.assertFalse(pid_path.exists())


    def test_startup_grace_does_not_spawn_duplicate_daemon_during_slow_windows_boot(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_path = Path(tmp) / "service.pid"
            heartbeat_path = Path(tmp) / "heartbeat.json"
            pid_path.write_text("12345", encoding="utf-8")


            old = time.time() - 60
            import os
            os.utime(pid_path, (old, old))

            with patch.object(reminder, "PID_PATH", pid_path), \
                 patch.object(reminder, "HEARTBEAT_PATH", heartbeat_path), \
                 patch("reminder.process_is_running", return_value=True):
                running, pid = reminder.reminder_service_status()

            self.assertTrue(running)
            self.assertEqual(pid, 12345)

    def test_fresh_heartbeat_marks_service_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            pid_path = Path(tmp) / "service.pid"
            heartbeat_path = Path(tmp) / "heartbeat.json"
            pid_path.write_text("12345", encoding="utf-8")


            old = time.time() - 60
            import os
            os.utime(pid_path, (old, old))
            pid_heartbeat = heartbeat_path.with_name("heartbeat-12345.json")
            pid_heartbeat.write_text(
                json.dumps({"pid": 12345, "updated_at": time.time()}),
                encoding="utf-8",
            )

            with patch.object(reminder, "PID_PATH", pid_path), \
                 patch.object(reminder, "HEARTBEAT_PATH", heartbeat_path), \
                 patch("reminder.process_is_running", return_value=True):
                running, pid = reminder.reminder_service_status()

            self.assertTrue(running)
            self.assertEqual(pid, 12345)


if __name__ == "__main__":
    unittest.main()
