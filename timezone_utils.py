from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_timezone_name(name: str) -> str:
    """Validate and return an IANA time-zone name."""
    value = (name or "").strip()
    if not value:
        raise ValueError("Time zone cannot be blank.")

    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unknown time zone '{value}'. Use an IANA name such as "
            "America/Los_Angeles or America/Chicago."
        ) from exc

    return value


def detect_local_timezone() -> str:
    """Best-effort cross-platform detection of the device's IANA time zone.

    tzlocal is preferred when installed. The fallbacks keep the app usable even
    before dependencies are installed or on unusual systems.
    """
    try:
        from tzlocal import get_localzone_name

        name = get_localzone_name()
        if name:
            return validate_timezone_name(name)
    except Exception:
        pass

    env_tz = os.environ.get("TZ", "").strip()
    if env_tz:
        try:
            return validate_timezone_name(env_tz)
        except ValueError:
            pass

    try:
        link = Path("/etc/localtime").resolve()
        marker = "zoneinfo/"
        text = str(link)
        if marker in text:
            candidate = text.split(marker, 1)[1]
            return validate_timezone_name(candidate)
    except Exception:
        pass

    try:
        tzinfo = datetime.now().astimezone().tzinfo
        key = getattr(tzinfo, "key", None)
        if key:
            return validate_timezone_name(str(key))
    except Exception:
        pass


    return "UTC"


def current_wall_time(time_zone: str) -> datetime:
    """Return current wall-clock time in the selected user time zone.

    The scheduler stores wall-clock datetimes without offsets for compatibility
    with the existing v11 database. This helper centralizes which wall clock is
    used so parsing, reminders, and Google Calendar agree.
    """
    zone = ZoneInfo(validate_timezone_name(time_zone))
    return datetime.now(zone).replace(tzinfo=None)
