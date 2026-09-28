from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from database import SchedulerDatabase
from voice import show_notification, show_popup, speak, speak_async
from timezone_utils import current_wall_time, detect_local_timezone
from runtime_paths import PID_PATH, LOG_PATH, DATA_DIR, HEARTBEAT_PATH


ROOT = Path(__file__).resolve().parent


def _windows_hidden_process_kwargs() -> dict:
    """Return subprocess options that suppress console flashes on Windows.

    HT-SmartScheduler is packaged as a GUI app. Background maintenance tasks
    (PowerShell process discovery, taskkill, and the detached reminder daemon)
    must never create a visible console window.
    """
    if platform.system().lower() != "windows":
        return {}

    kwargs: dict = {}
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creationflags:
        kwargs["creationflags"] = creationflags

    startupinfo_cls = getattr(subprocess, "STARTUPINFO", None)
    startf_use_showwindow = getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    sw_hide = getattr(subprocess, "SW_HIDE", 0)
    if startupinfo_cls is not None:
        startupinfo = startupinfo_cls()
        if startf_use_showwindow:
            startupinfo.dwFlags |= startf_use_showwindow
        if hasattr(startupinfo, "wShowWindow"):
            startupinfo.wShowWindow = sw_hide
        kwargs["startupinfo"] = startupinfo

    return kwargs






def _windows_detached_process_flags(include_breakaway: bool = True) -> int:
    """Return flags for a background worker that can outlive the GUI.

    CREATE_NO_WINDOW prevents a console flash. DETACHED_PROCESS and
    CREATE_NEW_PROCESS_GROUP detach the worker from the GUI process.
    CREATE_BREAKAWAY_FROM_JOB is important on Windows machines where the GUI
    is placed in a job object that would otherwise terminate child processes
    when the GUI exits. Some managed environments disallow breakaway, so the
    caller retries without that bit if CreateProcess returns access denied.
    """
    if platform.system().lower() != "windows":
        return 0



    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    flags |= int(getattr(subprocess, "DETACHED_PROCESS", 0x00000008))
    flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
    if include_breakaway:
        flags |= int(getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000))
    return flags

def _windows_worker_executable() -> Path | None:
    """Return the dedicated Windows reminder helper beside the main EXE.

    The helper is built as a separate --windowed executable so it can remain
    alive after the GUI closes without showing a console window or relying on
    the fragile "main EXE spawns itself" path used by older builds.
    """
    if platform.system().lower() != "windows" or not getattr(sys, "frozen", False):
        return None
    candidate = Path(sys.executable).with_name("HT-SmartScheduler-Reminder.exe")
    return candidate if candidate.exists() else None

def reminder_trigger_time(reminder: dict) -> datetime:
    start = datetime.fromisoformat(reminder["start_at"])
    minutes = int(reminder["reminder_minutes"])
    return start - timedelta(minutes=minutes)


def format_lead_time(minutes: int) -> str:
    if minutes == 0:
        return "at the event time"

    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days} day{'s' if days != 1 else ''} before"

    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hour{'s' if hours != 1 else ''} before"

    return f"{minutes} minute{'s' if minutes != 1 else ''} before"


def build_reminder_message(reminder: dict) -> str:
    start = datetime.fromisoformat(reminder["start_at"])
    pretty_time = start.strftime("%I:%M %p").lstrip("0")
    pretty_date = start.strftime("%A, %B %d")
    lead = format_lead_time(int(reminder["reminder_minutes"]))

    return (
        f"{reminder['title']} is scheduled for "
        f"{pretty_date} at {pretty_time}. "
        f"This reminder is {lead}."
    )


def check_reminders(
    db: SchedulerDatabase,
    now: datetime | None = None,
    speak_enabled: bool = True,
    notifications_enabled: bool = True,
    popup_parent=None,
) -> list[dict]:
    if now is None:
        time_zone = db.get_setting("time_zone") or detect_local_timezone()
        now = current_wall_time(time_zone)
    candidates = db.reminder_candidates(now=now)


    due_by_event: dict[tuple[int, str], list[dict]] = defaultdict(list)

    for reminder in candidates:
        start = datetime.fromisoformat(reminder["start_at"])
        trigger_at = reminder_trigger_time(reminder)

        if trigger_at <= now < start:
            due_by_event[(int(reminder["event_id"]), reminder["start_at"])].append(reminder)

    triggered = []

    for (_event_id, _occurrence_start), due in due_by_event.items():




        chosen = min(
            due,
            key=lambda item: int(item["reminder_minutes"]),
        )





        if not db.try_claim_reminder_delivery(chosen, now):
            continue

        message = build_reminder_message(chosen)
        start = datetime.fromisoformat(chosen["start_at"])
        trigger_at = reminder_trigger_time(chosen)

        print(
            f"\nREMINDER DUE: {chosen['title']}\n"
            f"Event starts: {start.strftime('%Y-%m-%d %I:%M %p')}\n"
            f"Reminder: {format_lead_time(int(chosen['reminder_minutes']))}\n"
            f"Scheduled reminder time: "
            f"{trigger_at.strftime('%Y-%m-%d %I:%M %p')}"
        )

        mode = (chosen.get("reminder_mode") or "both").lower()
        popup_enabled = notifications_enabled and mode in {"both", "popup"}
        voice_enabled = speak_enabled and mode in {"both", "voice"}





        popup_sent = show_popup(
            message,
            title="HT-SmartScheduler Reminder",
            enabled=popup_enabled,
            timeout_seconds=20,
            parent=popup_parent,
        )

        if popup_enabled:
            print(
                "Popup reminder: "
                + ("opened" if popup_sent else "not confirmed")
            )
        else:
            print("Popup reminder: disabled for this event")




        if popup_parent is not None and voice_enabled:
            voice_ok = speak_async(
                f"Reminder. {message}",
                enabled=True,
            )
        else:
            voice_ok = speak(
                f"Reminder. {message}",
                enabled=voice_enabled,
            )
        if voice_enabled:
            print("Voice reminder: " + ("played" if voice_ok else "not confirmed"))
        else:
            print("Voice reminder: disabled for this event")

        db.mark_due_reminders_notified(due, now)
        triggered.append(chosen)

    return triggered


HEARTBEAT_MAX_AGE_SECONDS = 45
DAEMON_STARTUP_GRACE_SECONDS = 90


def _heartbeat_path(pid: int | None = None) -> Path:
    """Return a PID-specific heartbeat file.

    Older versions used one shared heartbeat file.  If two daemons overlapped,
    they overwrote each other's PID and the GUI could mistakenly launch even
    more daemons.  A heartbeat per PID removes that feedback loop.
    """
    pid = int(pid or os.getpid())
    return HEARTBEAT_PATH.with_name(
        f"{HEARTBEAT_PATH.stem}-{pid}{HEARTBEAT_PATH.suffix}"
    )


def _write_heartbeat() -> None:
    """Record proof that this reminder daemon is alive and polling."""
    path = _heartbeat_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"pid": os.getpid(), "updated_at": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        pass


def _read_heartbeat(pid: int | None = None) -> tuple[int | None, float | None]:
    if not pid:
        return None, None
    path = _heartbeat_path(pid)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return int(payload.get("pid")), float(payload.get("updated_at"))
    except (FileNotFoundError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, None


def _heartbeat_is_fresh(pid: int | None, max_age: int = HEARTBEAT_MAX_AGE_SECONDS) -> bool:
    heartbeat_pid, updated_at = _read_heartbeat(pid)
    if not pid or heartbeat_pid != pid or updated_at is None:
        return False
    return (time.time() - updated_at) <= max_age


def _remove_runtime_marker(path: Path) -> None:
    try:
        path.unlink()
    except (FileNotFoundError, OSError):
        pass


def run_reminder_loop(
    db: SchedulerDatabase,
    poll_seconds: int = 10,
    speak_enabled: bool = True,
    notifications_enabled: bool = True,
    quiet: bool = False,
):
    if not quiet:
        print(
            "HT-SmartScheduler reminder service is running.\n"
            f"Checking every {poll_seconds} seconds.\n"
            "Press Ctrl+C to stop.\n"
        )



    _write_heartbeat()

    try:
        check_reminders(
            db,
            speak_enabled=speak_enabled,
            notifications_enabled=notifications_enabled,
        )
        _write_heartbeat()

        while True:
            time.sleep(poll_seconds)
            _write_heartbeat()
            check_reminders(
                db,
                speak_enabled=speak_enabled,
                notifications_enabled=notifications_enabled,
            )
            _write_heartbeat()
    except KeyboardInterrupt:
        if not quiet:
            print("\nReminder service stopped.")
    finally:
        heartbeat_pid, _ = _read_heartbeat(os.getpid())
        if heartbeat_pid == os.getpid():
            _remove_runtime_marker(_heartbeat_path(os.getpid()))


def _read_pid() -> int | None:
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None


def process_is_running(pid: int | None) -> bool:
    if not pid:
        return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def reminder_service_status() -> tuple[bool, int | None]:
    pid = _read_pid()

    if not process_is_running(pid):
        _remove_runtime_marker(PID_PATH)
        _remove_runtime_marker(_heartbeat_path(pid))
        _remove_runtime_marker(HEARTBEAT_PATH)
        return False, None



    if _heartbeat_is_fresh(pid):
        return True, pid

    try:
        pid_age = time.time() - PID_PATH.stat().st_mtime
    except OSError:
        pid_age = HEARTBEAT_MAX_AGE_SECONDS + 1

    if pid_age <= DAEMON_STARTUP_GRACE_SECONDS:
        return True, pid



    _remove_runtime_marker(PID_PATH)
    _remove_runtime_marker(_heartbeat_path(pid))
    _remove_runtime_marker(HEARTBEAT_PATH)
    return False, None


def _parse_unix_daemon_pids(process_listing: str) -> set[int]:
    """Return HT-SmartScheduler reminder-daemon PIDs from a ps listing."""
    pids: set[int] = set()
    for raw in process_listing.splitlines():
        line = raw.strip()
        if not line or "--reminders-daemon" not in line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        command = parts[1].lower()
        if "ht-smartscheduler" in command or "main.py" in command or "desktop_entry" in command:
            pids.add(pid)
    return pids


def find_all_reminder_daemon_pids() -> set[int]:
    """Find reminder daemons from current and older HT-SmartScheduler builds."""
    system = platform.system().lower()
    try:
        if system == "windows":
            ps_script = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.ProcessId -ne $PID -and "
                "$_.CommandLine -match '--reminders-daemon' -and "
                "($_.Name -match 'HT-SmartScheduler|python') } | "
                "ForEach-Object { $_.ProcessId }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                check=False,
                capture_output=True,
                text=True,
                **_windows_hidden_process_kwargs(),
            )
            pids: set[int] = set()
            for token in result.stdout.split():
                try:
                    pids.add(int(token))
                except ValueError:
                    pass
            return pids

        result = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            check=False,
            capture_output=True,
            text=True,
        )
        return _parse_unix_daemon_pids(result.stdout)
    except Exception:
        return set()


def stop_all_reminder_daemons() -> list[int]:
    """Stop every old/current detached reminder daemon for this user.

    Older app versions could leave detached daemons running after the GUI was
    replaced. Those old processes still used the legacy small popup and their
    own voice call, which is why one event could create several small dialogs,
    several large dialogs, and overlapping voices. New versions clean them up
    before starting one fresh daemon.
    """
    stopped: list[int] = []
    current_pid = os.getpid()
    for pid in sorted(find_all_reminder_daemon_pids()):
        if pid == current_pid:
            continue
        try:
            if platform.system().lower() == "windows":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    **_windows_hidden_process_kwargs(),
                )
            else:
                os.kill(pid, signal.SIGTERM)
            stopped.append(pid)
        except OSError:
            pass

    _remove_runtime_marker(PID_PATH)
    _remove_runtime_marker(HEARTBEAT_PATH)
    try:
        for path in HEARTBEAT_PATH.parent.glob(
            f"{HEARTBEAT_PATH.stem}-*{HEARTBEAT_PATH.suffix}"
        ):
            _remove_runtime_marker(path)
    except OSError:
        pass
    return stopped


def start_background_service(no_voice: bool = False) -> tuple[bool, int]:
    running, pid = reminder_service_status()

    if running and pid is not None:
        return False, pid

    PID_PATH.parent.mkdir(parents=True, exist_ok=True)

    frozen = bool(getattr(sys, "frozen", False))
    windows = platform.system().lower() == "windows"

    if frozen:


        worker = _windows_worker_executable()
        executable = str(worker) if worker is not None else sys.executable
        command = [executable, "--reminders-daemon"]
        working_dir = DATA_DIR
    else:
        command = [
            sys.executable,
            str(ROOT / "main.py"),
            "--reminders-daemon",
        ]
        working_dir = ROOT

    if no_voice:
        command.append("--no-voice")

    log_handle = open(LOG_PATH, "a", encoding="utf-8")
    env = os.environ.copy()
    if frozen:


        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

    popen_kwargs = dict(
        cwd=str(working_dir),
        stdin=subprocess.DEVNULL,
        stdout=log_handle,
        stderr=log_handle,
        env=env,
    )



    _remove_runtime_marker(PID_PATH)
    _remove_runtime_marker(HEARTBEAT_PATH)

    try:
        if windows:
            popen_kwargs["close_fds"] = True
            if frozen:



                popen_kwargs["creationflags"] = _windows_detached_process_flags(True)
                try:
                    process = subprocess.Popen(command, **popen_kwargs)
                except OSError as exc:




                    if getattr(exc, "winerror", None) != 5:
                        raise
                    popen_kwargs["creationflags"] = _windows_detached_process_flags(False)
                    process = subprocess.Popen(command, **popen_kwargs)
            else:
                popen_kwargs.update(_windows_hidden_process_kwargs())
                process = subprocess.Popen(command, **popen_kwargs)
        else:
            popen_kwargs["start_new_session"] = True
            process = subprocess.Popen(command, **popen_kwargs)
    finally:
        log_handle.close()

    if not (windows and frozen):

        PID_PATH.write_text(str(process.pid), encoding="utf-8")
        _remove_runtime_marker(_heartbeat_path(process.pid))




    return True, process.pid


def stop_background_service() -> tuple[bool, int | None]:
    running, pid = reminder_service_status()

    if not running or pid is None:
        return False, None

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

    _remove_runtime_marker(PID_PATH)
    _remove_runtime_marker(_heartbeat_path(pid))
    _remove_runtime_marker(HEARTBEAT_PATH)

    return True, pid
