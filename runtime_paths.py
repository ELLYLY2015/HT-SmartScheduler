from __future__ import annotations

import os
import platform
import sys
import shutil
from pathlib import Path

APP_NAME = "HT-SmartScheduler"
APP_DIR_NAME = "HT-SmartScheduler"
LEGACY_APP_NAME = "Smart Scheduler"
LEGACY_APP_DIR_NAME = "SmartScheduler"


def is_frozen() -> bool:
    """Return True when running from a PyInstaller-built desktop app."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Read-only root containing bundled application resources."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Writable per-user storage location.

    Source-code runs intentionally keep the legacy project/data behavior so
    existing development databases continue to work. Packaged apps use the OS
    application-data directory so updates/reinstalls don't overwrite user data.
    """
    if not is_frozen():
        path = Path(__file__).resolve().parent / "data"
    else:
        system = platform.system().lower()
        home = Path.home()
        legacy_path = None
        if system == "darwin":
            base_dir = home / "Library" / "Application Support"
            path = base_dir / APP_NAME
            legacy_path = base_dir / LEGACY_APP_NAME
        elif system == "windows":
            base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
            base_dir = Path(base) if base else home / "AppData" / "Roaming"
            path = base_dir / APP_DIR_NAME
            legacy_path = base_dir / LEGACY_APP_DIR_NAME
        else:
            base = os.environ.get("XDG_DATA_HOME")
            base_dir = Path(base) if base else home / ".local" / "share"
            path = base_dir / APP_DIR_NAME
            legacy_path = base_dir / LEGACY_APP_DIR_NAME



        if not path.exists() and legacy_path and legacy_path.exists():
            try:
                shutil.copytree(legacy_path, path)
            except Exception:
                pass

    path.mkdir(parents=True, exist_ok=True)
    return path


RESOURCE_ROOT = resource_root()
DATA_DIR = user_data_dir()
DB_PATH = DATA_DIR / "smart_scheduler.db"
ICS_PATH = DATA_DIR / "schedule.ics"
PID_PATH = DATA_DIR / "reminder_service.pid"
LOG_PATH = DATA_DIR / "reminder_service.log"
HEARTBEAT_PATH = DATA_DIR / "reminder_service.heartbeat.json"
TOKEN_PATH = DATA_DIR / "google_token.json"


def google_credentials_path() -> Path:
    """Return OAuth client configuration location.

    For development, use data/google_credentials.json as before. For a packaged
    product, a developer can place that file in data/ before building and it is
    bundled read-only into the application. If it was not bundled, fall back to
    the user's data directory so a developer/tester can still configure it.
    """
    bundled = RESOURCE_ROOT / "data" / "google_credentials.json"
    if bundled.exists():
        return bundled
    return DATA_DIR / "google_credentials.json"
