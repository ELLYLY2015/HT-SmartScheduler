from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Iterable


WEEKDAY_CODES = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")


def build_rrule(
    recurrence: str,
    interval: int = 1,
    count: int | None = None,
) -> str | None:
    """Build an RFC5545-style RRULE accepted by Google Calendar.

    Supported recurrence names: none, daily, weekdays, weekly, monthly, yearly.
    """
    recurrence = (recurrence or "none").strip().lower()
    interval = max(1, int(interval or 1))

    if recurrence in {"", "none", "does not repeat", "no"}:
        return None

    mapping = {
        "daily": "DAILY",
        "weekly": "WEEKLY",
        "monthly": "MONTHLY",
        "yearly": "YEARLY",
    }

    parts: list[str]
    if recurrence == "weekdays":
        parts = ["FREQ=WEEKLY", f"INTERVAL={interval}", "BYDAY=MO,TU,WE,TH,FR"]
    elif recurrence in mapping:
        parts = [f"FREQ={mapping[recurrence]}", f"INTERVAL={interval}"]
    else:
        raise ValueError(f"Unsupported recurrence: {recurrence}")

    if count is not None and int(count) > 0:
        parts.append(f"COUNT={int(count)}")

    return "RRULE:" + ";".join(parts)


def parse_rrule(rrule: str | None) -> dict[str, str]:
    if not rrule:
        return {}

    value = rrule.strip()
    if value.upper().startswith("RRULE:"):
        value = value[6:]

    result: dict[str, str] = {}
    for piece in value.split(";"):
        if "=" not in piece:
            continue
        key, raw = piece.split("=", 1)
        result[key.strip().upper()] = raw.strip().upper()
    return result


def recurrence_label(rrule: str | None) -> str:
    params = parse_rrule(rrule)
    if not params:
        return "Does not repeat"

    freq = params.get("FREQ", "")
    interval = int(params.get("INTERVAL", "1") or 1)
    byday = params.get("BYDAY")

    if freq == "WEEKLY" and byday == "MO,TU,WE,TH,FR":
        base = "Weekdays"
    else:
        base = {
            "DAILY": "Daily",
            "WEEKLY": "Weekly",
            "MONTHLY": "Monthly",
            "YEARLY": "Yearly",
        }.get(freq, freq.title() or "Recurring")

    if interval > 1:
        base += f" (every {interval})"

    count = params.get("COUNT")
    if count:
        base += f", {count} occurrences"
    return base


def _add_months(value: datetime, months: int) -> datetime:
    total = value.year * 12 + (value.month - 1) + months
    year, month_index = divmod(total, 12)
    month = month_index + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _candidate_for_date(start_at: datetime, d: date) -> datetime:
    return start_at.replace(year=d.year, month=d.month, day=d.day)


def _matches_without_count(start_at: datetime, candidate: datetime, params: dict[str, str]) -> bool:
    if candidate < start_at:
        return False

    freq = params.get("FREQ")
    interval = max(1, int(params.get("INTERVAL", "1") or 1))
    delta_days = (candidate.date() - start_at.date()).days

    if freq == "DAILY":
        return delta_days % interval == 0

    if freq == "WEEKLY":
        week_index = delta_days // 7
        if week_index % interval != 0:
            return False
        byday = params.get("BYDAY")
        if byday:
            allowed = {code.strip() for code in byday.split(",")}
            return WEEKDAY_CODES[candidate.weekday()] in allowed
        return candidate.weekday() == start_at.weekday()

    if freq == "MONTHLY":
        month_diff = (candidate.year - start_at.year) * 12 + candidate.month - start_at.month
        if month_diff < 0 or month_diff % interval != 0:
            return False
        expected = _add_months(start_at, month_diff)
        return candidate.date() == expected.date()

    if freq == "YEARLY":
        year_diff = candidate.year - start_at.year
        if year_diff < 0 or year_diff % interval != 0:
            return False
        try:
            expected = start_at.replace(year=candidate.year)
        except ValueError:

            expected = start_at.replace(year=candidate.year, day=28)
        return candidate.date() == expected.date()

    return False


def _count_occurrences_through(start_at: datetime, candidate: datetime, params: dict[str, str]) -> int:
    """Return the 1-based occurrence number for candidate, or 0 if not an occurrence.

    COUNT is expected to be small in normal UI usage. This routine only runs when
    an RRULE includes COUNT, which keeps the normal endless-recurrence path fast.
    """
    if not _matches_without_count(start_at, candidate, params):
        return 0

    count = 0
    current = start_at.date()
    end = candidate.date()
    while current <= end:
        dt = _candidate_for_date(start_at, current)
        if _matches_without_count(start_at, dt, params):
            count += 1
        current += timedelta(days=1)
    return count


def matches_recurrence(start_at: datetime, candidate: datetime, rrule: str) -> bool:
    params = parse_rrule(rrule)
    if not params:
        return candidate == start_at

    if candidate.time().replace(microsecond=0) != start_at.time().replace(microsecond=0):
        return False

    if not _matches_without_count(start_at, candidate, params):
        return False

    count_limit = int(params.get("COUNT", "0") or 0)
    if count_limit:
        number = _count_occurrences_through(start_at, candidate, params)
        return 0 < number <= count_limit

    return True


def occurrences_between(
    start_at: datetime,
    rrule: str | None,
    window_start: datetime,
    window_end: datetime,
) -> list[datetime]:
    """Return recurrence instances whose starts are inside an inclusive window."""
    if window_end < window_start:
        return []

    if not rrule:
        return [start_at] if window_start <= start_at <= window_end else []



    first_date = max(start_at.date(), window_start.date())
    last_date = window_end.date()

    result: list[datetime] = []
    current = first_date
    while current <= last_date:
        candidate = _candidate_for_date(start_at, current)
        if window_start <= candidate <= window_end and matches_recurrence(start_at, candidate, rrule):
            result.append(candidate)
        current += timedelta(days=1)

    return result


def next_occurrence_on_or_after(
    start_at: datetime,
    rrule: str | None,
    when: datetime,
) -> datetime | None:
    """Return the next occurrence whose start is >= ``when``.

    This is used by the Upcoming Events view. One-time events return ``None``
    after their start time has passed. Recurring events stay visible only while
    their rule still has a future occurrence (including finite COUNT rules).
    """
    if not rrule:
        return start_at if start_at >= when else None

    params = parse_rrule(rrule)
    if not params:
        return start_at if start_at >= when else None

    freq = params.get("FREQ", "DAILY")
    interval = max(1, int(params.get("INTERVAL", "1") or 1))





    horizon_days = {
        "DAILY": interval * 2 + 2,
        "WEEKLY": interval * 14 + 14,
        "MONTHLY": interval * 62 + 62,
        "YEARLY": interval * 732 + 732,
    }.get(freq, interval * 732 + 732)

    current = max(start_at.date(), when.date())
    last = current + timedelta(days=horizon_days)
    while current <= last:
        candidate = _candidate_for_date(start_at, current)
        if candidate >= when and matches_recurrence(start_at, candidate, rrule):
            return candidate
        current += timedelta(days=1)

    return None
