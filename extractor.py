from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta
from typing import Optional

from models import EventCandidate
from nlp.normalizer import normalize_text
from timing_language import interpret_special_future_phrase


WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

MONTH_INDEX = {
    name.lower(): i
    for i, name in enumerate(calendar.month_name)
    if name
}
MONTH_INDEX.update({
    name.lower(): i
    for i, name in enumerate(calendar.month_abbr)
    if name
})
MONTH_INDEX["sept"] = 9

DAYPART_TIME = {
    "morning": (8, 0),
    "afternoon": (15, 0),
    "evening": (19, 0),
    "tonight": (19, 0),
    "noon": (12, 0),
    "midnight": (0, 0),
}

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "a": 1,
    "an": 1,
    "couple": 2,
}

NUM_TOKEN = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|thirty|a|an|couple)"
)

UNIT_TOKEN = r"(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)"






EXACT_RELATIVE_PATTERNS = [
    rf"\bin\s+(?:the\s+)?next\s+{NUM_TOKEN}\s+{UNIT_TOKEN}\b",
    rf"\bwithin\s+(?:the\s+)?(?:next\s+)?{NUM_TOKEN}\s+{UNIT_TOKEN}\b",
    rf"\b{NUM_TOKEN}\s+{UNIT_TOKEN}\s+from\s+now\b",
    rf"\bafter\s+{NUM_TOKEN}\s+{UNIT_TOKEN}\b",
]


DATE_PATTERNS = [

    r"\bby\s+tomorrow\b",
    r"\bby\s+next\s+week\b",
    r"\bnext\s+year\b",


    rf"\bin\s+(?:the\s+)?next\s+{NUM_TOKEN}\s+(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)\b",
    rf"\bwithin\s+(?:the\s+)?(?:next\s+)?{NUM_TOKEN}\s+(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)\b",
    r"\bthis\s+week\b",
    r"\bnext\s+week\b",
    r"\bthis\s+month\b",
    r"\bnext\s+month\b",
    r"\bweekend\s+after\s+next\b",
    r"\bthis\s+weekend\b",
    r"\bnext\s+weekend\b",
    r"\bweekend\b",


    r"\bin\s+half\s+(?:an?\s+)?hour\b",
    r"\bhalf\s+(?:an?\s+)?hour\s+from\s+now\b",
    r"\bin\s+(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\b",
    r"\b(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\s+from\s+now\b",
    r"\bin\s+(?:an?|one)\s+hour\b",
    r"\b(?:an?|one)\s+hour\s+from\s+now\b",
    r"\bin\s+(?:one\s+and\s+a\s+half|1\.5)\s+hours?\b",
    r"\b(?:one\s+and\s+a\s+half|1\.5)\s+hours?\s+from\s+now\b",
    rf"\bin\s+{NUM_TOKEN}\s+(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)\b",
    rf"\b{NUM_TOKEN}\s+(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)\s+from\s+now\b",
    rf"\bafter\s+{NUM_TOKEN}\s+(?:minutes?|mins?|hours?|hrs?|days?|weeks?|months?)\b",
    rf"\b{NUM_TOKEN}\s+(?:days?|weeks?)\s+later\b",

    r"\bday\s+after\s+tomorrow\b",
    r"\bthe\s+next\s+day\b",
    r"\btomorrow\b",
    r"\btoday\b",
    r"\blater\s+today\b",

    r"\b(?:next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",

    r"\b(?:january|february|march|april|may|june|july|august|september|sept|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b",
]

TIME_PATTERNS = [

    r"\btomorrow\s+(?:morning|afternoon|evening|night)\b",
    r"\btoday\s+(?:morning|afternoon|evening|night)\b",
    r"\bthis\s+(?:morning|afternoon|evening)\b",


    r"\b(?:at\s+)?(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b(?:at\s+)?(?:[01]?\d|2[0-3]):[0-5]\d\b",


    r"\bnoon\b",
    r"\bmidnight\b",
    r"\bmorning\b",
    r"\bafternoon\b",
    r"\bevening\b",
    r"\btonight\b",
    r"\bnight\b",


    r"\bat\s+(?:1[0-2]|[1-9])\b",
]

DURATION_RE = re.compile(
    r"\b(?:for|lasting|duration(?:\s+of)?)\s+"
    r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)\b",
    re.IGNORECASE,
)





WINDOW_THEN_DURATION_RE = re.compile(
    rf"(?:within|in\s+the\s+next)\s+{NUM_TOKEN}\s+"
    r"(?:minutes?|mins?|hours?|hrs?).*?\bin\s+"
    r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|hours?|hrs?)\b",
    re.IGNORECASE,
)

REMINDER_RE = re.compile(
    r"\b(?:and\s+)?remind\s+me(?:\s+to)?\s*"
    r"(?:(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+before|"
    r"(?:the\s+)?day\s+before|(?:the\s+)?night\s+before)\b",
    re.IGNORECASE,
)


def _first_match(patterns: list[str], text: str):
    matches = []
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            matches.append(m)

    if not matches:
        return None



    return min(matches, key=lambda m: (m.start(), -len(m.group(0))))


def split_note(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    pieces = re.split(r"(?:\r?\n)+|(?<=[.!?])\s+|;\s*", text)
    return [p.strip() for p in pieces if p.strip()]


def _number_value(token: str) -> Optional[int]:
    token = token.lower().strip()

    if token.isdigit():
        return int(token)

    return NUMBER_WORDS.get(token)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])

    return value.replace(year=year, month=month, day=day)


def _relative_delta(amount: int, unit: str) -> tuple[str, int]:
    unit = unit.lower()

    if unit.startswith(("minute", "min")):
        return "minutes", amount
    if unit.startswith(("hour", "hr")):
        return "hours", amount
    if unit.startswith("day"):
        return "days", amount
    if unit.startswith("week"):
        return "weeks", amount
    if unit.startswith("month"):
        return "months", amount

    raise ValueError(f"Unsupported relative unit: {unit}")


def _apply_relative(base: datetime, amount: int, unit: str) -> datetime:
    kind, amount = _relative_delta(amount, unit)

    if kind == "minutes":
        return base + timedelta(minutes=amount)
    if kind == "hours":
        return base + timedelta(hours=amount)
    if kind == "days":
        return base + timedelta(days=amount)
    if kind == "weeks":
        return base + timedelta(weeks=amount)
    if kind == "months":
        return _add_months(base, amount)

    raise ValueError(kind)


def _resolve_natural_short_relative(
    phrase: str,
    base: datetime,
) -> Optional[datetime]:
    """
    Resolve common near-time phrases that are not simple integer quantities.

    Examples:
      in half hour
      in half an hour
      half an hour from now
      in a quarter hour
      in an hour
      in one and a half hours
    """
    low = re.sub(r"\s+", " ", phrase.lower().strip())

    if low.startswith("in "):
        low = low[3:].strip()

    if low.endswith(" from now"):
        low = low[:-9].strip()

    if re.fullmatch(r"half\s+(?:an?\s+)?hour", low):
        return base + timedelta(minutes=30)

    if re.fullmatch(r"(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour", low):
        return base + timedelta(minutes=15)

    if re.fullmatch(r"(?:an?|one)\s+hour", low):
        return base + timedelta(hours=1)

    if re.fullmatch(r"(?:one\s+and\s+a\s+half|1\.5)\s+hours?", low):
        return base + timedelta(minutes=90)

    return None


def _is_exact_short_relative_clock(phrase: str) -> bool:
    low = re.sub(r"\s+", " ", phrase.lower().strip())

    patterns = [
        r"in\s+half\s+(?:an?\s+)?hour",
        r"half\s+(?:an?\s+)?hour\s+from\s+now",
        r"in\s+(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour",
        r"(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\s+from\s+now",
        r"in\s+(?:an?|one)\s+hour",
        r"(?:an?|one)\s+hour\s+from\s+now",
        r"in\s+(?:one\s+and\s+a\s+half|1\.5)\s+hours?",
        r"(?:one\s+and\s+a\s+half|1\.5)\s+hours?\s+from\s+now",
    ]

    return any(re.fullmatch(pattern, low) for pattern in patterns)


def extract_duration_minutes(text: str) -> Optional[int]:
    m = DURATION_RE.search(text)
    if not m:
        m = WINDOW_THEN_DURATION_RE.search(text)
    if not m:
        return None

    amount = float(m.group(1))
    unit = m.group(2).lower()

    if unit.startswith(("hour", "hr")):
        return int(round(amount * 60))

    return int(round(amount))


def extract_reminder_minutes(text: str) -> Optional[int]:
    low = text.lower()

    if re.search(r"\b(?:the\s+)?night\s+before\b", low):
        return 12 * 60

    if re.search(r"\b(?:the\s+)?day\s+before\b", low):
        return 24 * 60

    m = re.search(
        r"(\d+)\s*(minutes?|mins?|hours?|hrs?)\s+before",
        text,
        re.IGNORECASE,
    )

    if not m:
        return None

    amount = int(m.group(1))
    unit = m.group(2).lower()

    if unit.startswith(("hour", "hr")):
        return amount * 60

    return amount


def extract_date_text(text: str) -> Optional[str]:



    natural_patterns = [
        r"\bin\s+half\s+(?:an?\s+)?hour\b",
        r"\bhalf\s+(?:an?\s+)?hour\s+from\s+now\b",
        r"\bin\s+(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\b",
        r"\b(?:a\s+)?quarter\s+(?:of\s+an?\s+)?hour\s+from\s+now\b",
        r"\bin\s+(?:one\s+and\s+a\s+half|1\.5)\s+hours?\b",
        r"\b(?:one\s+and\s+a\s+half|1\.5)\s+hours?\s+from\s+now\b",
    ]
    natural = _first_match(natural_patterns, text)
    if natural:
        return natural.group(0)




    precise_matches = []
    for pattern in EXACT_RELATIVE_PATTERNS:
        precise_matches.extend(re.finditer(pattern, text, re.IGNORECASE))
    if precise_matches:
        match = min(precise_matches, key=lambda item: (item.start(), -len(item.group(0))))
        return match.group(0)

    m = _first_match(DATE_PATTERNS, text)
    return m.group(0) if m else None


def extract_time_text(text: str) -> Optional[str]:
    m = _first_match(TIME_PATTERNS, text)
    return m.group(0) if m else None


def _resolve_weekday(
    weekday_name: str,
    base: datetime,
    prefix: Optional[str] = None,
) -> datetime:
    target = WEEKDAY_INDEX[weekday_name.lower()]
    current = base.weekday()
    delta = (target - current) % 7

    prefix = (prefix or "").lower()

    if prefix == "next":
        if delta == 0:
            delta = 7
    elif prefix == "this":
        pass
    else:
        if delta == 0:
            delta = 7

    return base + timedelta(days=delta)


def _week_bounds(base: datetime, next_week: bool = False):
    start = base - timedelta(days=base.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    if next_week:
        start += timedelta(days=7)

    end = start + timedelta(days=7)
    return start, end


def _month_bounds(base: datetime, next_month: bool = False):
    year = base.year
    month = base.month

    if next_month:
        month += 1
        if month == 13:
            month = 1
            year += 1

    start = base.replace(
        year=year,
        month=month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end = _add_months(start, 1)
    return start, end


def _this_calendar_weekend_start(base: datetime) -> datetime:
    """Saturday 00:00 belonging to the base date's Monday-Sunday week."""
    monday = (base - timedelta(days=base.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday + timedelta(days=5)


def _weekend_bounds(base: datetime, mode: str = "this"):
    """Return Saturday 00:00 through Monday 00:00 for a weekend phrase.

    Modes:
      this  -> weekend in the current calendar week
      next  -> weekend one calendar week later
      after_next -> weekend two calendar weeks later
      upcoming -> nearest weekend that has not completely passed
    """
    start = _this_calendar_weekend_start(base)

    if mode == "next":
        start += timedelta(days=7)
    elif mode == "after_next":
        start += timedelta(days=14)
    elif mode == "upcoming":

        if base >= start + timedelta(days=2):
            start += timedelta(days=7)

    end = start + timedelta(days=2)
    return start, end


def _resolve_weekend_datetime(
    date_text: str,
    time_text: Optional[str],
    base: datetime,
) -> Optional[datetime]:
    """Resolve weekend + explicit clock time to the earliest valid occurrence.

    A weekend phrase represents Saturday/Sunday. When the user supplies a clock
    time, HT-SmartScheduler chooses the earliest occurrence of that time in the
    requested weekend. This lets phrases such as "this weekend at 9 AM" save
    directly instead of asking the user to choose Saturday manually.
    """
    if not date_text or not time_text:
        return None

    low = date_text.lower().strip()
    mode = None
    if low == "this weekend":
        mode = "this"
    elif low == "next weekend":
        mode = "next"
    elif low == "weekend after next":
        mode = "after_next"
    elif low == "weekend":
        mode = "upcoming"

    if mode is None:
        return None

    time_value = resolve_time(time_text)
    if time_value is None:
        return None

    hour, minute = time_value
    start, _ = _weekend_bounds(base, mode=mode)
    candidates = [
        (start + timedelta(days=offset)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        for offset in (0, 1)
    ]

    future = [candidate for candidate in candidates if candidate >= base]
    if future:
        return min(future)



    if mode in {"this", "upcoming"}:
        next_start = start + timedelta(days=7)
        return next_start.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )

    return candidates[0]


def resolve_date_window(
    date_text: Optional[str],
    base: Optional[datetime] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Return a recognized scheduling window for phrases that do not identify
    one exact date, e.g. "next week" or "sometime this weekend".
    """
    if not date_text:
        return None, None

    base = base or datetime.now()
    low = date_text.lower().strip()

    special = interpret_special_future_phrase(date_text, base)
    if special.kind in {"window", "deadline_window", "ongoing"}:
        return special.window_start, special.window_end

    if low == "this week":
        return _week_bounds(base, next_week=False)

    if low == "next week":
        return _week_bounds(base, next_week=True)

    if low == "this month":
        return _month_bounds(base, next_month=False)

    if low == "next month":
        return _month_bounds(base, next_month=True)

    if low == "this weekend":
        return _weekend_bounds(base, mode="this")

    if low == "next weekend":
        return _weekend_bounds(base, mode="next")

    if low == "weekend after next":
        return _weekend_bounds(base, mode="after_next")

    if low == "weekend":
        return _weekend_bounds(base, mode="upcoming")

    return None, None


def resolve_date(date_text: str, base: Optional[datetime] = None) -> Optional[datetime]:
    if not date_text:
        return None

    base = base or datetime.now()
    raw = date_text.strip()
    low = raw.lower()




    m = re.fullmatch(
        rf"in\s+(?:the\s+)?next\s+({NUM_TOKEN})\s+({UNIT_TOKEN})",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))

    m = re.fullmatch(
        rf"within\s+(?:the\s+)?(?:next\s+)?({NUM_TOKEN})\s+({UNIT_TOKEN})",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))

    special = interpret_special_future_phrase(raw, base)
    if special.kind in {"exact", "immediate"} and special.exact_at is not None:
        return special.exact_at



    w_start, w_end = resolve_date_window(raw, base)
    if w_start is not None:
        return None

    if low in {"today", "later today"}:
        return base

    if low in {"tomorrow", "the next day"}:
        return base + timedelta(days=1)

    if low == "day after tomorrow":
        return base + timedelta(days=2)

    natural_short_relative = _resolve_natural_short_relative(raw, base)
    if natural_short_relative is not None:
        return natural_short_relative


    m = re.fullmatch(
        rf"in\s+({NUM_TOKEN})\s+({UNIT_TOKEN})",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))


    m = re.fullmatch(
        rf"({NUM_TOKEN})\s+({UNIT_TOKEN})\s+from\s+now",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))


    m = re.fullmatch(
        rf"after\s+({NUM_TOKEN})\s+({UNIT_TOKEN})",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))


    m = re.fullmatch(
        rf"({NUM_TOKEN})\s+(days?|weeks?)\s+later",
        low,
    )
    if m:
        amount = _number_value(m.group(1))
        return _apply_relative(base, amount, m.group(2))

    weekday_match = re.fullmatch(
        r"(?:(next|this)\s+)?"
        r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
        low,
        flags=re.IGNORECASE,
    )

    if weekday_match:
        prefix, weekday = weekday_match.groups()
        return _resolve_weekday(weekday, base, prefix)

    iso_match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        try:
            return base.replace(year=year, month=month, day=day)
        except ValueError:
            return None

    slash_match = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?",
        raw,
    )

    if slash_match:
        month, day, year = slash_match.groups()
        month = int(month)
        day = int(day)

        if year is None:
            year = base.year
            try:
                candidate = base.replace(year=year, month=month, day=day)
            except ValueError:
                return None

            if candidate.date() < base.date():
                year += 1
        else:
            year = int(year)
            if year < 100:
                year += 2000

        try:
            return base.replace(year=year, month=month, day=day)
        except ValueError:
            return None

    month_match = re.fullmatch(
        r"([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,\s*(\d{4}))?",
        raw,
    )

    if month_match:
        month_name, day, year = month_match.groups()
        month = MONTH_INDEX.get(month_name.lower())

        if not month:
            return None

        day = int(day)

        if year is None:
            year = base.year
            try:
                candidate = base.replace(year=year, month=month, day=day)
            except ValueError:
                return None

            if candidate.date() < base.date():
                year += 1
        else:
            year = int(year)

        try:
            return base.replace(year=year, month=month, day=day)
        except ValueError:
            return None

    return None


def resolve_time(time_text: str) -> Optional[tuple[int, int]]:
    if not time_text:
        return None

    raw = re.sub(r"^\s*at\s+", "", time_text.strip(), flags=re.IGNORECASE)
    low = raw.lower().replace(".", "")


    m = re.fullmatch(
        r"(?:today|tomorrow|this)\s+(morning|afternoon|evening|night)",
        low,
    )
    if m:
        part = m.group(1)
        if part == "night":
            return 20, 0
        return DAYPART_TIME[part]

    if low == "night":
        return 20, 0

    if low in DAYPART_TIME:
        return DAYPART_TIME[low]

    m12 = re.fullmatch(
        r"(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(am|pm)",
        low,
    )

    if m12:
        hour = int(m12.group(1))
        minute = int(m12.group(2) or 0)
        ampm = m12.group(3)

        if ampm == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

        return hour, minute

    m24 = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", low)
    if m24:
        return int(m24.group(1)), int(m24.group(2))


    if re.fullmatch(r"(?:1[0-2]|[1-9])", low):
        return None

    return None


def resolve_datetime(
    date_text: Optional[str],
    time_text: Optional[str],
    base: Optional[datetime] = None,
) -> Optional[datetime]:
    if not date_text:
        return None

    base = base or datetime.now()



    weekend_start = _resolve_weekend_datetime(date_text, time_text, base)
    if weekend_start is not None:
        return weekend_start


    relative = resolve_date(date_text, base)
    if relative is None:
        return None

    low = date_text.lower().strip()

    exact_relative = any(
        re.fullmatch(pattern, low, re.IGNORECASE)
        for pattern in EXACT_RELATIVE_PATTERNS
    )
    classic_relative = re.fullmatch(
        rf"(?:in\s+{NUM_TOKEN}\s+{UNIT_TOKEN}|"
        rf"{NUM_TOKEN}\s+{UNIT_TOKEN}\s+from\s+now|"
        rf"after\s+{NUM_TOKEN}\s+{UNIT_TOKEN})",
        low,
    )

    if exact_relative or classic_relative or _is_exact_short_relative_clock(low):



        if time_text:
            explicit_time = resolve_time(time_text)
            if explicit_time is not None:
                hour, minute = explicit_time
                return relative.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
        return relative.replace(second=0, microsecond=0)


    if time_text:
        combined = time_text.lower().strip()
        m = re.fullmatch(
            r"(today|tomorrow|this)\s+(morning|afternoon|evening|night)",
            combined,
        )
        if m:
            date_word, part = m.groups()

            if date_word == "tomorrow":
                relative = base + timedelta(days=1)
            elif date_word in {"today", "this"}:
                relative = base

            hour, minute = resolve_time(time_text)
            return relative.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )

    if not time_text:


        return None

    time_value = resolve_time(time_text)
    if time_value is None:
        return None

    hour, minute = time_value
    return relative.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )


def infer_event_type(text: str) -> str:
    low = text.lower()

    if (
        "deadline" in low
        or "due" in low
        or re.search(
            r"\bby\s+(?:today|tomorrow|day after tomorrow|next|this|"
            r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
            r"january|february|march|april|may|june|july|august|"
            r"september|october|november|december|\d)",
            low,
        )
    ):
        return "deadline"

    return "event"


def clean_duty(
    text: str,
    date_text: Optional[str],
    time_text: Optional[str],
) -> str:
    duty = text

    duty = re.sub(
        r"\b(?:and\s+)?remind\s+me(?:\s+to)?\s*"
        r"(?:(?:\d+)\s*(?:minutes?|mins?|hours?|hrs?)\s+before|"
        r"(?:the\s+)?day\s+before|(?:the\s+)?night\s+before)\b",
        " ",
        duty,
        flags=re.IGNORECASE,
    )

    duty = DURATION_RE.sub(" ", duty)

    if time_text:
        duty = re.sub(
            re.escape(time_text),
            " ",
            duty,
            count=1,
            flags=re.IGNORECASE,
        )

    if date_text:
        duty = re.sub(
            re.escape(date_text),
            " ",
            duty,
            count=1,
            flags=re.IGNORECASE,
        )



        if re.search(
            rf"(?:within(?:\s+the)?(?:\s+next)?|in(?:\s+the)?\s+next)\s+{NUM_TOKEN}\s+"
            r"(?:minutes?|mins?|hours?|hrs?)",
            date_text,
            re.IGNORECASE,
        ):
            duty = re.sub(r"\b(?:today|later\s+today)\b", " ", duty, flags=re.IGNORECASE)


            duty = re.sub(
                r"\bin\s+\d+(?:\.\d+)?\s*(?:minutes?|mins?|hours?|hrs?)\b",
                " ",
                duty,
                count=1,
                flags=re.IGNORECASE,
            )

    duty = re.sub(
        r"^\s*(?:please\s+)?(?:schedule|add|create|book)\s+",
        "",
        duty,
        flags=re.IGNORECASE,
    )

    duty = re.sub(
        r"^\s*remind\s+me\s+to\s+",
        "",
        duty,
        flags=re.IGNORECASE,
    )

    duty = re.sub(
        r"\b(?:at|on|by|in)\b(?=\s*(?:$|[,.]))",
        " ",
        duty,
        flags=re.IGNORECASE,
    )

    duty = re.sub(
        r"\s+\b(?:at|on|by|in)\b\s*$",
        " ",
        duty,
        flags=re.IGNORECASE,
    )

    duty = re.sub(r"\s+", " ", duty).strip(" ,.-")

    return duty or "Untitled event"


def extract_event(
    sentence: str,
    base: Optional[datetime] = None,
) -> EventCandidate:
    base = base or datetime.now()




    parsing_sentence = normalize_text(sentence)

    core_date_text = extract_date_text(parsing_sentence)
    time_text = extract_time_text(parsing_sentence)
    special = interpret_special_future_phrase(parsing_sentence, base)



    date_text = core_date_text

    if special.phrase:
        special_start = parsing_sentence.lower().find(special.phrase.lower())
        core_start = (
            parsing_sentence.lower().find(core_date_text.lower())
            if core_date_text
            else None
        )

        if core_date_text is None:
            date_text = special.phrase
        elif special_start < core_start:
            date_text = special.phrase
        elif special_start == core_start and len(special.phrase) > len(core_date_text):
            date_text = special.phrase


    if time_text:
        m = re.fullmatch(
            r"(today|tomorrow|this)\s+(morning|afternoon|evening|night)",
            time_text,
            flags=re.IGNORECASE,
        )
        if m:
            date_word = m.group(1).lower()
            if date_word == "this":
                date_word = "today"


            if date_text is None or date_text.lower() in {"today", "tomorrow"}:
                date_text = date_word

    duration = extract_duration_minutes(parsing_sentence)
    reminder = extract_reminder_minutes(parsing_sentence)

    window_start, window_end = resolve_date_window(date_text, base)
    start_at = resolve_datetime(date_text, time_text, base)

    timing_kind = None
    notes = []




    special_selected = (
        special.phrase is not None
        and date_text is not None
        and special.phrase.lower() == date_text.lower()
    )

    if special_selected:
        timing_kind = special.kind

        if special.exact_at is not None:
            if time_text and resolve_time(time_text) is not None:
                hour, minute = resolve_time(time_text)
                start_at = special.exact_at.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0,
                )
            else:
                start_at = special.exact_at

        if special.window_start is not None:
            window_start = special.window_start

        if special.window_end is not None:
            window_end = special.window_end

        if special.note and timing_kind in {
            "vague_future",
            "sequence_reference",
            "ongoing",
            "window",
            "deadline_window",
        }:
            notes.append(special.note)

    elif start_at is not None:
        timing_kind = "exact"

    elif window_start is not None:
        timing_kind = "window"
        notes.append("recognized date window, but no exact date was specified")

    if date_text is None:
        notes.append("missing date")

    if time_text is None:
        exact_relative_clock = bool(
            date_text
            and (
                any(
                    re.fullmatch(pattern, date_text.lower(), re.IGNORECASE)
                    for pattern in EXACT_RELATIVE_PATTERNS
                )
                or re.fullmatch(
                    rf"(?:in\s+{NUM_TOKEN}\s+{UNIT_TOKEN}|"
                    rf"{NUM_TOKEN}\s+{UNIT_TOKEN}\s+from\s+now|"
                    rf"after\s+{NUM_TOKEN}\s+{UNIT_TOKEN})",
                    date_text.lower(),
                )
                or _is_exact_short_relative_clock(date_text)
            )
        )



        semantic_without_clock = timing_kind in {
            "vague_future",
            "sequence_reference",
            "ongoing",
            "window",
            "deadline_window",
            "immediate",
        }

        if not exact_relative_clock and not semantic_without_clock:
            notes.append("missing time")

    elif resolve_time(time_text) is None:
        notes.append("time is ambiguous (AM/PM not specified)")

    return EventCandidate(
        source_text=sentence,
        duty=clean_duty(parsing_sentence, date_text, time_text),
        date_text=date_text,
        time_text=time_text,
        timing_kind=timing_kind,
        start_at=start_at,
        window_start=window_start,
        window_end=window_end,
        duration_minutes=duration,
        reminder_minutes=reminder,
        event_type=infer_event_type(parsing_sentence),
        confidence_notes=", ".join(notes) if notes else None,
    )


def extract_events(
    text: str,
    base: Optional[datetime] = None,
) -> list[EventCandidate]:
    return [extract_event(item, base=base) for item in split_note(text)]
