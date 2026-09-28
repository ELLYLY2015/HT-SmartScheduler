from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class TimingInterpretation:
    phrase: Optional[str] = None
    kind: Optional[str] = None
    exact_at: Optional[datetime] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    note: Optional[str] = None


def _find_first(patterns: list[tuple[str, str]], text: str):
    """
    patterns: list of (regex, label).
    Returns earliest match; for same start position, longest match wins.
    """
    found = []

    for pattern, label in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found.append((match, label))

    if not found:
        return None, None

    match, label = min(
        found,
        key=lambda item: (
            item[0].start(),
            -len(item[0].group(0)),
        ),
    )
    return match, label


def _start_of_next_week(base: datetime) -> datetime:
    days = 7 - base.weekday()
    return (base + timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def _start_of_next_month(base: datetime) -> datetime:
    year = base.year
    month = base.month + 1

    if month == 13:
        month = 1
        year += 1

    return base.replace(
        year=year,
        month=month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def interpret_special_future_phrase(
    text: str,
    base: Optional[datetime] = None,
) -> TimingInterpretation:
    base = base or datetime.now()


    match = re.search(r"\bby\s+tomorrow\b", text, re.IGNORECASE)
    if match:
        end = (base + timedelta(days=1)).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        return TimingInterpretation(
            phrase=match.group(0),
            kind="deadline_window",
            window_start=base,
            window_end=end,
            note="recognized as a deadline no later than tomorrow",
        )

    match = re.search(r"\bby\s+next\s+week\b", text, re.IGNORECASE)
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="deadline_window",
            window_start=base,
            window_end=_start_of_next_week(base),
            note="recognized as a deadline before next week begins",
        )


    match = re.search(r"\bnext\s+year\b", text, re.IGNORECASE)
    if match:
        start = base.replace(
            year=base.year + 1,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        end = start.replace(year=start.year + 1)
        return TimingInterpretation(
            phrase=match.group(0),
            kind="window",
            window_start=start,
            window_end=end,
            note="recognized as the next calendar year",
        )


    match = re.search(r"\b(?:the\s+)?next\s+day\b", text, re.IGNORECASE)
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="exact",
            exact_at=base + timedelta(days=1),
            note="recognized as the next day",
        )


    match, _ = _find_first(
        [
            (r"\bfrom\s+now\s+on\b", "ongoing"),
            (r"\bhenceforth\b", "ongoing"),
        ],
        text,
    )
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="ongoing",
            window_start=base,
            note="recognized as ongoing from now forward",
        )


    match = re.search(r"\bimmediately\b", text, re.IGNORECASE)
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="immediate",
            exact_at=base.replace(second=0, microsecond=0),
            note="recognized as immediate future intent",
        )



    match, _ = _find_first(
        [
            (r"\bafter\s+a\s+few\s+days\b", "vague"),
            (r"\bafter\s+a\s+while\b", "vague"),
            (r"\bnot\s+long\s+after\b", "vague"),
            (r"\bbefore\s+long\b", "vague"),
            (r"\bin\s+the\s+future\b", "vague"),
            (r"\bin\s+a\s+moment\b", "vague"),
        ],
        text,
    )
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="vague_future",
            note="future timing recognized, but no exact date/time is stated",
        )


    match, _ = _find_first(
        [
            (r"\bas\s+soon\s+as\b", "sequence"),
            (r"\bsoon\s+after\b", "sequence"),
            (r"\bright\s+after\b", "sequence"),
            (r"\bafter\s+that\b", "sequence"),
            (r"\bafterward\b", "sequence"),
            (r"\bfollowing\b", "sequence"),
            (r"\bin\s+turn\b", "sequence"),
            (r"\bconsequently\b", "sequence"),
        ],
        text,
    )
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="sequence_reference",
            note=(
                "sequence/reference timing recognized; "
                "another event or condition is needed"
            ),
        )


    match, _ = _find_first(
        [
            (r"\beventually\b", "vague"),
            (r"\bsomeday\b", "vague"),
            (r"\bshortly\b", "vague"),
            (r"\bsoon\b", "vague"),
            (r"\blater\b", "vague"),
            (r"\bpresently\b", "vague"),
            (r"\bmomentarily\b", "vague"),
            (r"\bin\s+time\b", "vague"),
        ],
        text,
    )
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="vague_future",
            note="future timing recognized, but no exact date/time is stated",
        )



    match, _ = _find_first(
        [
            (r"\bafter\b", "sequence"),
            (r"\bthen\b", "sequence"),
            (r"\bwhen\b", "sequence"),
            (r"\bsecond\b", "sequence"),
            (r"\bthird\b", "sequence"),
            (r"\bsince\b", "sequence"),
        ],
        text,
    )
    if match:
        return TimingInterpretation(
            phrase=match.group(0),
            kind="sequence_reference",
            note=(
                "sequence/reference word recognized; "
                "it does not identify an exact future date by itself"
            ),
        )

    return TimingInterpretation()
