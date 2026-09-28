from __future__ import annotations

import argparse
import sys
from pathlib import Path

from calendar_manager import export_ics
from chatbot import candidate_is_complete, event_end, format_candidate
from database import SchedulerDatabase
from extractor import extract_events
from voice import show_notification, show_popup, speak
from timezone_utils import current_wall_time, detect_local_timezone
from reminder import (
    check_reminders,
    reminder_service_status,
    run_reminder_loop,
    start_background_service,
    stop_background_service,
)


VERSION = "11.6.3"
ROOT = Path(__file__).resolve().parent
from runtime_paths import DB_PATH, ICS_PATH


def read_note_from_stdin() -> str:
    print("SMART SCHEDULER — PHASE 1")
    print("Paste or type your note below.")
    print("Press Enter on an empty line when finished.\n")

    lines = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if not line.strip():
            break

        lines.append(line)

    return "\n".join(lines).strip()


def process_note(note: str, db: SchedulerDatabase) -> tuple[int, int]:
    time_zone = db.get_setting("time_zone") or detect_local_timezone()
    candidates = extract_events(note, base=current_wall_time(time_zone))

    if not candidates:
        print("\nNo schedule items were found.")
        return 0, 0

    print(f"\nFound {len(candidates)} possible schedule item(s).\n")

    saved = 0
    incomplete = 0

    for index, event in enumerate(candidates, start=1):
        print(f"ITEM {index}")
        print("-" * 60)
        print(format_candidate(event))

        if not candidate_is_complete(event):
            incomplete += 1
            print("Action:    NOT saved — more date/time information is needed.\n")
            continue


        duration_minutes = event.duration_minutes or 60
        reminder_minutes = (
            event.reminder_minutes
            if event.reminder_minutes is not None
            else 30
        )
        end_at = event_end(event)

        conflicts = db.find_conflicts(event.start_at, end_at)

        if conflicts:
            print("Conflict:  Possible overlap with:")
            for conflict in conflicts:
                print(
                    f"           #{conflict['id']} {conflict['title']} "
                    f"({conflict['start_at']} -> {conflict['end_at']})"
                )

        event_id = db.add_event(
            title=event.duty,
            start_at=event.start_at,
            end_at=end_at,
            reminder_minutes_list=[reminder_minutes],
            event_type=event.event_type,
            source_text=event.source_text,
            reminder_mode="both",
        )

        saved += 1
        print(f"Action:    Saved automatically as event #{event_id}.\n")

    events = db.list_events()

    if events:
        export_ics(events, ICS_PATH)
        print(f"Calendar file updated: {ICS_PATH}")

    print(
        f"\nSummary: {saved} saved, "
        f"{incomplete} incomplete/not saved."
    )

    return saved, incomplete


def load_note(args) -> str:
    if args.file:
        return Path(args.file).read_text(encoding="utf-8").strip()

    if args.text:
        return args.text.strip()

    return read_note_from_stdin()


def build_parser():
    parser = argparse.ArgumentParser(
        description="HT-SmartScheduler App v11.2 — Relative time + reminders + ML + Google Calendar"
    )

    source = parser.add_mutually_exclusive_group()

    source.add_argument(
        "--text",
        help='Process one note directly, e.g. --text "Dentist tomorrow at 9 AM"',
    )

    source.add_argument(
        "--file",
        help="Read the note from a UTF-8 text file.",
    )

    source.add_argument(
        "--ml-preview",
        help=(
            "Run the Phase 2 ML entity extractor without saving an event."
        ),
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the HT-SmartScheduler version.",
    )

    parser.add_argument(
        "--where",
        action="store_true",
        help="Show the exact project, database, and calendar paths.",
    )

    parser.add_argument(
        "--reminders",
        action="store_true",
        help="Run the reminder service in this Terminal.",
    )

    parser.add_argument(
        "--check-reminders",
        action="store_true",
        help="Check once for reminders that are due now.",
    )

    parser.add_argument(
        "--reminders-start",
        action="store_true",
        help="Start the reminder service in the background.",
    )

    parser.add_argument(
        "--reminders-stop",
        action="store_true",
        help="Stop the background reminder service.",
    )

    parser.add_argument(
        "--reminders-status",
        action="store_true",
        help="Show whether the background reminder service is running.",
    )

    parser.add_argument(
        "--test-notification",
        action="store_true",
        help="Send a notification immediately to test macOS notifications.",
    )

    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable spoken reminders.",
    )

    parser.add_argument(
        "--no-background",
        action="store_true",
        help="Do not automatically start the reminder background service.",
    )

    parser.add_argument(
        "--app",
        action="store_true",
        help="Open the HT-SmartScheduler desktop app.",
    )


    parser.add_argument(
        "--reminders-daemon",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    return parser


def main():
    args = build_parser().parse_args()

    if args.version:
        print(f"HT-SmartScheduler v{VERSION} — Time-zone safe + ML + Recurrence + Google Calendar")
        return 0

    if args.where:
        print(f"Project:  {ROOT}")
        print(f"Database: {DB_PATH.resolve()}")
        print(f"Calendar: {ICS_PATH.resolve()}")
        return 0

    if args.app:
        from app import launch_app
        launch_app()
        return 0

    if args.ml_preview:
        import json
        from nlp.ml_extractor import SchedulerMLExtractor

        extractor = SchedulerMLExtractor()
        print(
            json.dumps(
                extractor.analyze(args.ml_preview),
                indent=2,
            )
        )
        return 0

    db = SchedulerDatabase(DB_PATH)

    if args.test_notification:
        message = "HT-SmartScheduler notifications are working."
        sent = show_notification(
            message,
            title="HT-SmartScheduler Test",
            enabled=True,
        )
        popup = show_popup(
            message,
            title="HT-SmartScheduler Test",
            enabled=True,
            timeout_seconds=20,
        )
        speak(
            "HT-SmartScheduler notification test.",
            enabled=not args.no_voice,
        )
        print(
            "Notification banner: "
            + ("sent to macOS." if sent else "could not be confirmed.")
        )
        print(
            "Popup dialog: "
            + ("opened." if popup else "could not be confirmed.")
        )
        return 0

    if args.reminders_daemon:
        run_reminder_loop(
            db,
            speak_enabled=not args.no_voice,
            notifications_enabled=True,
            quiet=True,
        )
        return 0

    if args.reminders:
        run_reminder_loop(
            db,
            speak_enabled=not args.no_voice,
            notifications_enabled=True,
        )
        return 0

    if args.check_reminders:
        triggered = check_reminders(
            db,
            speak_enabled=not args.no_voice,
            notifications_enabled=True,
        )

        if not triggered:
            print("No reminders are due right now.")

        return 0

    if args.reminders_start:
        started, pid = start_background_service(
            no_voice=args.no_voice,
        )
        if started:
            print(f"Reminder background service started (PID {pid}).")
        else:
            print(f"Reminder background service is already running (PID {pid}).")
        return 0

    if args.reminders_stop:
        stopped, pid = stop_background_service()
        if stopped:
            print(f"Reminder background service stopped (PID {pid}).")
        else:
            print("Reminder background service is not running.")
        return 0

    if args.reminders_status:
        running, pid = reminder_service_status()
        if running:
            print(f"Reminder background service is running (PID {pid}).")
        else:
            print("Reminder background service is not running.")
        return 0

    note = load_note(args)

    if not note:
        print("No text was provided.")
        return 1

    saved, _ = process_note(note, db)

    if saved:


        check_reminders(
            db,
            speak_enabled=not args.no_voice,
            notifications_enabled=True,
        )

        if not args.no_background:
            started, pid = start_background_service(
                no_voice=args.no_voice,
            )
            if started:
                print(
                    f"\nReminder background service started automatically "
                    f"(PID {pid})."
                )
            else:
                print(
                    f"\nReminder background service is already running "
                    f"(PID {pid})."
                )
            print(
                "Stop it with: python main.py --reminders-stop"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
