"""Desktop executable entry point for Smart Scheduler.

Double-click: opens the normal GUI.
Internal --reminders-daemon: runs the detached reminder process using the same
bundled executable, so end users never need Python or a Terminal.
"""
from __future__ import annotations

import sys


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


def _run_reminder_daemon_direct() -> int:
    """Run the background reminder daemon with minimal imports.

    On Windows the packaged app is built with PyInstaller --windowed, so
    sys.stdout/sys.stderr can be None.  Any print() from the reminder path
    would then terminate the daemon before it could deliver reminders.
    Give the daemon real log streams and publish an early heartbeat before
    importing the heavier application modules.
    """
    import json
    import os
    import time
    from runtime_paths import DB_PATH, HEARTBEAT_PATH, LOG_PATH

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_out = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

    sys.stdout = log_out
    sys.stderr = log_out

    pid = os.getpid()
    heartbeat = HEARTBEAT_PATH.with_name(
        f"{HEARTBEAT_PATH.stem}-{pid}{HEARTBEAT_PATH.suffix}"
    )
    try:
        heartbeat.write_text(
            json.dumps({"pid": pid, "updated_at": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        pass

    from database import SchedulerDatabase
    from reminder import run_reminder_loop

    db = SchedulerDatabase(DB_PATH)
    run_reminder_loop(
        db,
        speak_enabled="--no-voice" not in sys.argv[1:],
        notifications_enabled=True,
        quiet=True,
    )
    return 0


def main() -> int:
    if "--popup-window" in sys.argv[1:]:
        return _run_popup_window()

    if "--reminders-daemon" in sys.argv[1:] and sys.platform.startswith("win"):
        return _run_reminder_daemon_direct()

    internal_or_cli_flags = {
        "--reminders-daemon",
        "--reminders",
        "--check-reminders",
        "--reminders-start",
        "--reminders-stop",
        "--reminders-status",
        "--test-notification",
        "--version",
        "--where",
        "--ml-preview",
        "--text",
        "--file",
        "--app",
    }




    if any(arg in internal_or_cli_flags for arg in sys.argv[1:]):
        from main import main as cli_main
        return int(cli_main() or 0)

    from app import launch_app
    launch_app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
