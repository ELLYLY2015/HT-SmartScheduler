"""Hidden Windows reminder worker for HT-SmartScheduler.

This executable is built separately from the main GUI so it can stay alive
after the user closes the HT-SmartScheduler window.  It has no console window
and handles only background reminder polling plus standalone reminder popups.
"""
from __future__ import annotations

import json
import os
import sys
import time


def _run_popup_window() -> int:
    from popup_window import show_large_popup

    args = sys.argv[1:]
    try:
        index = args.index("--popup-window")
    except ValueError:
        return 2

    title = args[index + 1] if len(args) > index + 1 else "HT-SmartScheduler Reminder"
    text = args[index + 2] if len(args) > index + 2 else "Reminder"
    try:
        timeout = int(args[index + 3]) if len(args) > index + 3 else 20
    except ValueError:
        timeout = 20
    ready_file = args[index + 4] if len(args) > index + 4 else None
    return show_large_popup(title, text, timeout, ready_file=ready_file)


def _run_daemon() -> int:
    from runtime_paths import DB_PATH, HEARTBEAT_PATH, LOG_PATH, PID_PATH

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_out = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    sys.stdout = log_out
    sys.stderr = log_out

    pid = os.getpid()





    try:
        PID_PATH.write_text(str(pid), encoding="utf-8")
    except OSError:
        pass

    heartbeat = HEARTBEAT_PATH.with_name(
        f"{HEARTBEAT_PATH.stem}-{pid}{HEARTBEAT_PATH.suffix}"
    )
    try:
        heartbeat.write_text(
            json.dumps({"pid": pid, "updated_at": time.time()}),
            encoding="utf-8",
        )
        print(f"Windows reminder worker started (PID {pid}).", flush=True)
    except OSError:
        pass

    from database import SchedulerDatabase
    from reminder import run_reminder_loop

    db = SchedulerDatabase(DB_PATH)
    try:
        run_reminder_loop(
            db,
            speak_enabled="--no-voice" not in sys.argv[1:],
            notifications_enabled=True,
            quiet=True,
        )
    finally:


        try:
            if PID_PATH.read_text(encoding="utf-8").strip() == str(pid):
                PID_PATH.unlink()
        except (FileNotFoundError, OSError):
            pass
    return 0


def main() -> int:
    if "--popup-window" in sys.argv[1:]:
        return _run_popup_window()
    if "--reminders-daemon" in sys.argv[1:]:
        return _run_daemon()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
