from __future__ import annotations

from datetime import datetime, timedelta

from models import EventCandidate


def pretty_datetime(value: datetime | None) -> str:
    if value is None:
        return "Not resolved"

    return value.strftime("%A, %B %d, %Y at %I:%M %p").replace(" 0", " ")


def pretty_window(
    start: datetime | None,
    end: datetime | None,
) -> str:
    if start is None or end is None:
        return "None"

    return (
        f"{start.strftime('%a %b %d %Y %I:%M %p').replace(' 0', ' ')}"
        f"  →  "
        f"{end.strftime('%a %b %d %Y %I:%M %p').replace(' 0', ' ')}"
    )


def candidate_is_complete(event: EventCandidate) -> bool:
    return event.start_at is not None


def event_end(event: EventCandidate) -> datetime | None:
    if event.start_at is None:
        return None

    minutes = event.duration_minutes or 60
    return event.start_at + timedelta(minutes=minutes)


def format_candidate(event: EventCandidate) -> str:
    duration = (
        f"{event.duration_minutes} minutes"
        if event.duration_minutes is not None
        else "60 minutes (default)"
    )

    reminder = (
        f"{event.reminder_minutes} minutes before"
        if event.reminder_minutes is not None
        else "30 minutes before (default)"
    )

    lines = [
        f"Duty:      {event.duty}",
        f"Date text: {event.date_text or 'Not found'}",
        f"Time text: {event.time_text or 'Not found'}",
        f"Resolved:  {pretty_datetime(event.start_at)}",
        f"Timing:    {event.timing_kind or 'unclassified'}",
    ]

    if event.window_start is not None:
        lines.append(
            f"Window:    {pretty_window(event.window_start, event.window_end)}"
        )

    lines.extend([
        f"Duration:  {duration}",
        f"Reminder:  {reminder}",
        f"Type:      {event.event_type}",
        f"Status:    {event.confidence_notes or 'complete'}",
    ])

    return "\n".join(lines)
