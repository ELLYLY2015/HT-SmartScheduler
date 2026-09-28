from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _dt(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _fold(line: str, limit: int = 73) -> list[str]:
    if len(line) <= limit:
        return [line]

    parts = [line[:limit]]
    rest = line[limit:]

    while rest:
        parts.append(" " + rest[: limit - 1])
        rest = rest[limit - 1 :]

    return parts


def _event_reminders(event: dict) -> list[int]:
    values = event.get("reminder_minutes_list")

    if values is not None:
        return sorted(
            {int(value) for value in values},
            reverse=True,
        )

    legacy = event.get("reminder_minutes")
    return [int(legacy)] if legacy is not None else []


def export_ics(
    events: list[dict],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HT-SmartScheduler//v11//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    now = datetime.now()

    for event in events:
        start = datetime.fromisoformat(event["start_at"])
        end = datetime.fromisoformat(event["end_at"])

        event_lines = [
            "BEGIN:VEVENT",
            f"UID:{uuid4()}@smart-scheduler",
            f"DTSTAMP:{_dt(now)}",
            f"DTSTART:{_dt(start)}",
            f"DTEND:{_dt(end)}",
            f"SUMMARY:{_escape(event['title'])}",
            f"DESCRIPTION:{_escape(event.get('source_text') or '')}",
        ]

        if event.get("location"):
            event_lines.append(f"LOCATION:{_escape(event['location'])}")

        if event.get("recurrence_rule"):
            event_lines.append(event["recurrence_rule"])

        for reminder in _event_reminders(event):
            event_lines.extend(
                [
                    "BEGIN:VALARM",
                    f"TRIGGER:-PT{int(reminder)}M",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{_escape(event['title'])}",
                    "END:VALARM",
                ]
            )

        event_lines.append("END:VEVENT")

        for line in event_lines:
            lines.extend(_fold(line))

    lines.append("END:VCALENDAR")

    output_path.write_text(
        "\r\n".join(lines) + "\r\n",
        encoding="utf-8",
    )

    return output_path
