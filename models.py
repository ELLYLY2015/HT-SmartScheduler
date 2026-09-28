from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class EventCandidate:
    source_text: str
    duty: str

    date_text: Optional[str] = None
    time_text: Optional[str] = None




    timing_kind: Optional[str] = None

    start_at: Optional[datetime] = None
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None

    duration_minutes: Optional[int] = None
    reminder_minutes: Optional[int] = None
    event_type: str = "event"
    confidence_notes: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)

        for field in ("start_at", "window_start", "window_end"):
            value = getattr(self, field)
            if value is not None:
                data[field] = value.isoformat()

        return data
