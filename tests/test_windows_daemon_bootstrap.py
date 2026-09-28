import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import desktop_entry


class WindowsDaemonBootstrapTests(unittest.TestCase):
    def test_direct_daemon_sets_log_streams_and_early_heartbeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "test.db"
            log_path = root / "service.log"
            heartbeat_path = root / "service.heartbeat.json"

            class DummyDB:
                def __init__(self, path):
                    self.path = path

            def fake_loop(db, **kwargs):
                hb = heartbeat_path.with_name(
                    f"{heartbeat_path.stem}-{os.getpid()}{heartbeat_path.suffix}"
                )
                self.assertTrue(hb.exists())
                payload = json.loads(hb.read_text(encoding="utf-8"))
                self.assertEqual(payload["pid"], os.getpid())
                self.assertIsNotNone(sys.stdout)
                self.assertIsNotNone(sys.stderr)

            old_out, old_err = sys.stdout, sys.stderr
            try:
                with patch("runtime_paths.DB_PATH", db_path), \
                     patch("runtime_paths.LOG_PATH", log_path), \
                     patch("runtime_paths.HEARTBEAT_PATH", heartbeat_path), \
                     patch("database.SchedulerDatabase", DummyDB), \
                     patch("reminder.run_reminder_loop", side_effect=fake_loop):
                    result = desktop_entry._run_reminder_daemon_direct()
                self.assertEqual(result, 0)
            finally:
                try:
                    if sys.stdout is not old_out and sys.stdout:
                        sys.stdout.close()
                except Exception:
                    pass
                sys.stdout = old_out
                sys.stderr = old_err


if __name__ == "__main__":
    unittest.main()
