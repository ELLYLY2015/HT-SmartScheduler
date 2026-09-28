from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from recurrence import occurrences_between
from runtime_paths import DB_PATH


DEFAULT_DB_PATH = DB_PATH


class SchedulerDatabase:
    def __init__(self, path: str | Path = DEFAULT_DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _ensure_column(conn, table: str, column: str, definition: str):
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def initialize(self):
        now = datetime.now().isoformat()

        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    start_at TEXT NOT NULL,
                    end_at TEXT NOT NULL,
                    reminder_minutes INTEGER,
                    event_type TEXT NOT NULL DEFAULT 'event',
                    source_text TEXT,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    notified_at TEXT,
                    created_at TEXT NOT NULL,
                    recurrence_rule TEXT,
                    location TEXT,
                    google_event_id TEXT,
                    google_sync_status TEXT,
                    reminder_mode TEXT NOT NULL DEFAULT 'both'
                )
                """
            )


            self._ensure_column(conn, "events", "recurrence_rule", "TEXT")
            self._ensure_column(conn, "events", "location", "TEXT")
            self._ensure_column(conn, "events", "google_event_id", "TEXT")
            self._ensure_column(conn, "events", "google_sync_status", "TEXT")
            self._ensure_column(conn, "events", "reminder_mode", "TEXT NOT NULL DEFAULT 'both'")

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    minutes_before INTEGER NOT NULL,
                    notified_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(event_id, minutes_before),
                    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
                )
                """
            )



            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_occurrences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER NOT NULL,
                    occurrence_start TEXT NOT NULL,
                    notified_at TEXT NOT NULL,
                    UNIQUE(reminder_id, occurrence_start),
                    FOREIGN KEY(reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
                )
                """
            )





            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminder_delivery_claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reminder_id INTEGER NOT NULL,
                    occurrence_start TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    UNIQUE(reminder_id, occurrence_start),
                    FOREIGN KEY(reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )


            conn.execute(
                """
                INSERT OR IGNORE INTO reminders (
                    event_id,
                    minutes_before,
                    created_at
                )
                SELECT
                    id,
                    reminder_minutes,
                    COALESCE(created_at, ?)
                FROM events
                WHERE reminder_minutes IS NOT NULL
                """,
                (now,),
            )

            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row["value"]) if row else default

    def set_setting(self, key: str, value: str):
        updated_at = datetime.now().isoformat()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), updated_at),
            )
            conn.commit()

    @staticmethod
    def _normalize_reminders(values) -> list[int]:
        if values is None:
            return []

        result = []
        for value in values:
            minutes = int(value)
            if minutes < 0:
                raise ValueError("Reminder minutes cannot be negative.")
            if minutes not in result:
                result.append(minutes)

        return sorted(result, reverse=True)

    def add_event(
        self,
        title: str,
        start_at: datetime,
        end_at: datetime,
        reminder_minutes: Optional[int] = None,
        event_type: str = "event",
        source_text: Optional[str] = None,
        reminder_minutes_list: Optional[list[int]] = None,
        recurrence_rule: Optional[str] = None,
        location: Optional[str] = None,
        google_sync_status: Optional[str] = None,
        reminder_mode: str = "both",
    ) -> int:
        if reminder_minutes_list is None:
            reminders = [int(reminder_minutes)] if reminder_minutes is not None else []
        else:
            reminders = self._normalize_reminders(reminder_minutes_list)

        reminder_mode = (reminder_mode or "both").lower().strip()
        if reminder_mode not in {"both", "popup", "voice"}:
            raise ValueError("reminder_mode must be 'both', 'popup', or 'voice'.")

        legacy_reminder = min(reminders) if reminders else None
        created_at = datetime.now().isoformat()

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    title,
                    start_at,
                    end_at,
                    reminder_minutes,
                    event_type,
                    source_text,
                    status,
                    created_at,
                    recurrence_rule,
                    location,
                    google_sync_status,
                    reminder_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    start_at.isoformat(),
                    end_at.isoformat(),
                    legacy_reminder,
                    event_type,
                    source_text,
                    created_at,
                    recurrence_rule,
                    location,
                    google_sync_status,
                    reminder_mode,
                ),
            )

            event_id = int(cursor.lastrowid)

            for minutes in reminders:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO reminders (
                        event_id,
                        minutes_before,
                        created_at
                    )
                    VALUES (?, ?, ?)
                    """,
                    (event_id, minutes, created_at),
                )

            conn.commit()
            return event_id

    def set_event_reminders(self, event_id: int, reminder_minutes_list: list[int]):
        reminders = self._normalize_reminders(reminder_minutes_list)
        legacy_reminder = min(reminders) if reminders else None
        created_at = datetime.now().isoformat()

        with self.connect() as conn:
            conn.execute("DELETE FROM reminders WHERE event_id = ?", (event_id,))

            for minutes in reminders:
                conn.execute(
                    """
                    INSERT INTO reminders (event_id, minutes_before, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (event_id, minutes, created_at),
                )

            conn.execute(
                """
                UPDATE events
                SET reminder_minutes = ?, notified_at = NULL
                WHERE id = ?
                """,
                (legacy_reminder, event_id),
            )
            conn.commit()

    def get_event_reminders(self, event_id: int) -> list[int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT minutes_before
                FROM reminders
                WHERE event_id = ?
                ORDER BY minutes_before DESC
                """,
                (event_id,),
            ).fetchall()
        return [int(row["minutes_before"]) for row in rows]

    def list_events(self, include_cancelled: bool = False) -> list[dict]:
        query = "SELECT * FROM events"
        params = ()

        if not include_cancelled:
            query += " WHERE status = ?"
            params = ("scheduled",)

        query += " ORDER BY start_at"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        events = []
        for row in rows:
            event = dict(row)
            event["reminder_minutes_list"] = self.get_event_reminders(int(event["id"]))
            events.append(event)
        return events

    def get_event(self, event_id: int) -> Optional[dict]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()

        if not row:
            return None

        event = dict(row)
        event["reminder_minutes_list"] = self.get_event_reminders(event_id)
        return event

    def find_conflicts(
        self,
        start_at: datetime,
        end_at: datetime,
        exclude_event_id: Optional[int] = None,
    ) -> list[dict]:
        query = """
            SELECT *
            FROM events
            WHERE status = 'scheduled'
              AND start_at < ?
              AND end_at > ?
        """
        params = [end_at.isoformat(), start_at.isoformat()]

        if exclude_event_id is not None:
            query += " AND id != ?"
            params.append(exclude_event_id)

        query += " ORDER BY start_at"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def _recurrence_occurrence_was_notified(
        self,
        conn,
        reminder_id: int,
        occurrence_start: datetime,
    ) -> bool:
        row = conn.execute(
            """
            SELECT 1
            FROM reminder_occurrences
            WHERE reminder_id = ? AND occurrence_start = ?
            """,
            (reminder_id, occurrence_start.isoformat()),
        ).fetchone()
        return row is not None

    def reminder_candidates(self, now: Optional[datetime] = None) -> list[dict]:
        now = now or datetime.now()

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    r.id AS reminder_id,
                    r.event_id AS event_id,
                    r.minutes_before AS reminder_minutes,
                    r.notified_at AS reminder_notified_at,
                    e.title AS title,
                    e.start_at AS start_at,
                    e.end_at AS end_at,
                    e.event_type AS event_type,
                    e.source_text AS source_text,
                    e.status AS status,
                    e.recurrence_rule AS recurrence_rule,
                    e.reminder_mode AS reminder_mode
                FROM reminders r
                JOIN events e ON e.id = r.event_id
                WHERE e.status = 'scheduled'
                ORDER BY e.start_at, r.minutes_before DESC
                """
            ).fetchall()

            candidates: list[dict] = []
            for row in rows:
                item = dict(row)
                recurrence_rule = item.get("recurrence_rule")

                if not recurrence_rule:
                    if item.get("reminder_notified_at") is None:
                        candidates.append(item)
                    continue

                start_at = datetime.fromisoformat(item["start_at"])
                minutes = int(item["reminder_minutes"])


                window_end = now + timedelta(minutes=max(0, minutes))
                occurrences = occurrences_between(
                    start_at,
                    recurrence_rule,
                    now,
                    window_end,
                )

                for occurrence in occurrences:
                    if self._recurrence_occurrence_was_notified(
                        conn,
                        int(item["reminder_id"]),
                        occurrence,
                    ):
                        continue

                    recurring_item = dict(item)
                    duration = datetime.fromisoformat(item["end_at"]) - start_at
                    recurring_item["start_at"] = occurrence.isoformat()
                    recurring_item["end_at"] = (occurrence + duration).isoformat()
                    recurring_item["occurrence_start"] = occurrence.isoformat()
                    candidates.append(recurring_item)

        return candidates

    def try_claim_reminder_delivery(
        self,
        reminder: dict,
        when: Optional[datetime] = None,
    ) -> bool:
        """Atomically claim one reminder occurrence for delivery.

        Several processes can notice the same due reminder before any of them
        marks it notified.  INSERT OR IGNORE against a unique key makes exactly
        one process the delivery owner; every other process skips it.
        """
        when = when or datetime.now()
        reminder_id = int(reminder["reminder_id"])
        occurrence_start = str(
            reminder.get("occurrence_start") or reminder["start_at"]
        )

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO reminder_delivery_claims (
                    reminder_id, occurrence_start, claimed_at
                )
                VALUES (?, ?, ?)
                """,
                (reminder_id, occurrence_start, when.isoformat()),
            )
            conn.commit()
            return cursor.rowcount == 1

    def mark_reminder_notified(self, reminder_id: int, when: Optional[datetime] = None):
        self.mark_reminders_notified([reminder_id], when)

    def mark_reminders_notified(
        self,
        reminder_ids: list[int],
        when: Optional[datetime] = None,
    ):
        if not reminder_ids:
            return

        when = when or datetime.now()
        placeholders = ",".join("?" for _ in reminder_ids)

        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE reminders
                SET notified_at = ?
                WHERE id IN ({placeholders})
                """,
                [when.isoformat(), *reminder_ids],
            )
            conn.commit()

    def mark_due_reminders_notified(
        self,
        reminders: list[dict],
        when: Optional[datetime] = None,
    ):
        if not reminders:
            return
        when = when or datetime.now()

        one_time_ids: list[int] = []
        with self.connect() as conn:
            for reminder in reminders:
                reminder_id = int(reminder["reminder_id"])
                occurrence_start = reminder.get("occurrence_start")
                if reminder.get("recurrence_rule") and occurrence_start:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO reminder_occurrences (
                            reminder_id,
                            occurrence_start,
                            notified_at
                        )
                        VALUES (?, ?, ?)
                        """,
                        (reminder_id, occurrence_start, when.isoformat()),
                    )
                else:
                    one_time_ids.append(reminder_id)

            if one_time_ids:
                placeholders = ",".join("?" for _ in one_time_ids)
                conn.execute(
                    f"UPDATE reminders SET notified_at = ? WHERE id IN ({placeholders})",
                    [when.isoformat(), *one_time_ids],
                )
            conn.commit()


    def mark_notified(self, event_id: int, when: Optional[datetime] = None):
        when = when or datetime.now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE events SET notified_at = ? WHERE id = ?",
                (when.isoformat(), event_id),
            )
            conn.execute(
                """
                UPDATE reminders
                SET notified_at = ?
                WHERE event_id = ? AND notified_at IS NULL
                """,
                (when.isoformat(), event_id),
            )
            conn.commit()

    def set_google_sync(
        self,
        event_id: int,
        google_event_id: Optional[str],
        status: str,
    ):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE events
                SET google_event_id = ?, google_sync_status = ?
                WHERE id = ?
                """,
                (google_event_id, status, event_id),
            )
            conn.commit()

    def cancel_event(self, event_id: int) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE events
                SET status = 'cancelled'
                WHERE id = ? AND status = 'scheduled'
                """,
                (event_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
