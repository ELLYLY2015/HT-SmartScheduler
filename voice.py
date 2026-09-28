from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


def _windows_hidden_process_kwargs() -> dict:
    """Suppress console/PowerShell windows for Windows subprocesses."""
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


def show_notification(
    text: str,
    title: str = "HT-SmartScheduler",
    enabled: bool = True,
) -> bool:
    """Show a native desktop notification when supported."""
    if not enabled:
        return False

    system = platform.system().lower()

    try:
        if system == "darwin" and shutil.which("osascript"):


            script = (
                f"display notification {json.dumps(text)} "
                f"with title {json.dumps(title)}"
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True

            if result.stderr.strip():
                print(f"(macOS notification error: {result.stderr.strip()})")
            return False

        if system == "linux" and shutil.which("notify-send"):
            result = subprocess.run(
                ["notify-send", title, text],
                check=False,
            )
            return result.returncode == 0

    except Exception as exc:
        print(f"(Notification error: {exc})")

    return False



def show_popup(
    text: str,
    title: str = "HT-SmartScheduler Reminder",
    enabled: bool = True,
    timeout_seconds: int = 20,
    parent=None,
) -> bool:
    """Show the large cross-platform HT-SmartScheduler reminder popup.

    The popup runs in a separate process so the reminder daemon never blocks
    while the user reads or dismisses it.  The dedicated popup is deliberately
    much larger than the old native message box for accessibility.
    """
    if not enabled:
        return False

    try:



        if parent is not None:
            from popup_window import open_large_popup
            popup = open_large_popup(parent, title, text, timeout_seconds)



            try:
                popup.deiconify()
                popup.lift()




                popup.update_idletasks()
                popup.update()
                popup.lift()
            except Exception:
                pass
            return True

        system = platform.system().lower()
        ready_path = None
        if system == "windows":
            ready_path = Path(tempfile.gettempdir()) / (
                f"ht-smartscheduler-popup-{os.getpid()}-{uuid.uuid4().hex}.ready"
            )

        if getattr(sys, "frozen", False):
            command = [
                sys.executable,
                "--popup-window",
                title,
                text,
                str(int(timeout_seconds)),
            ]
        else:
            entry = Path(__file__).resolve().with_name("desktop_entry.py")
            command = [
                sys.executable,
                str(entry),
                "--popup-window",
                title,
                text,
                str(int(timeout_seconds)),
            ]

        if ready_path is not None:
            command.append(str(ready_path))

        kwargs = dict(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if system == "windows":


            kwargs.update(_windows_hidden_process_kwargs())
            if getattr(sys, "frozen", False):



                env = os.environ.copy()
                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                kwargs["env"] = env

        subprocess.Popen(command, **kwargs)





        if ready_path is not None:
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline:
                if ready_path.exists():
                    break
                time.sleep(0.02)
            try:
                ready_path.unlink()
            except OSError:
                pass

        return True
    except Exception as exc:
        print(f"(Popup error: {exc})")
        return False

def speak_async(text: str, enabled: bool = True) -> bool:
    """Start text-to-speech without blocking the Tk event loop.

    Windows reminder popups are created on Tk's main thread.  Running the
    PowerShell speech command synchronously on that same thread delays the
    window paint until speech finishes.  A daemon worker lets popup and voice
    begin together while keeping all Tk work on the main thread.
    """
    if not enabled:
        return False

    def _worker():
        speak(text, enabled=True)

    threading.Thread(
        target=_worker,
        name="HT-SmartScheduler-Voice",
        daemon=True,
    ).start()
    return True


def speak(text: str, enabled: bool = True) -> bool:
    """Speak text using the operating system when possible."""
    if not enabled:
        return False

    print(f"\n🔊 {text}")

    system = platform.system().lower()

    try:
        if system == "darwin" and shutil.which("say"):
            result = subprocess.run(["say", text], check=False)
            return result.returncode == 0

        if system == "windows":
            escaped = text.replace("'", "''")
            command = (
                "Add-Type -AssemblyName System.Speech; "
                "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$speak.Speak('{escaped}');"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **_windows_hidden_process_kwargs(),
            )
            return result.returncode == 0

        if shutil.which("espeak"):
            result = subprocess.run(["espeak", text], check=False)
            return result.returncode == 0

        if shutil.which("spd-say"):
            result = subprocess.run(["spd-say", text], check=False)
            return result.returncode == 0

    except Exception as exc:
        print(f"(Voice error: {exc})")

    print("(No supported system text-to-speech command was found.)")
    return False
