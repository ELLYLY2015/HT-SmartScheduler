from __future__ import annotations

import re
import sys
import time as time_module
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, time as dt_time
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from calendar_manager import export_ics
from chatbot import candidate_is_complete, event_end, pretty_datetime, pretty_window
from database import SchedulerDatabase
from extractor import extract_events
from google_calendar import GoogleCalendarClient, GoogleCalendarError
from recurrence import build_rrule, next_occurrence_on_or_after, recurrence_label
from reminder import (
    check_reminders,
    reminder_service_status,
    start_background_service,
    stop_background_service,
    stop_all_reminder_daemons,
)
from voice import show_popup, speak, speak_async
from timezone_utils import current_wall_time, detect_local_timezone, validate_timezone_name


VERSION = "11.6.3"
ROOT = Path(__file__).resolve().parent
from runtime_paths import DB_PATH, ICS_PATH, LOG_PATH

MAX_REMINDERS = 5
DEFAULT_REMINDERS = [
    (30, "minutes"),
    (10, "minutes"),
    (5, "minutes"),
    (1, "hour"),
    (1, "day"),
]

RECURRENCE_OPTIONS = (
    "Does not repeat",
    "Daily",
    "Weekdays",
    "Weekly",
    "Monthly",
    "Yearly",
)

REMINDER_MODE_OPTIONS = (
    "Popup + Voice",
    "Popup only",
    "Voice only",
)

EVENT_TYPE_OPTIONS = (
    "Auto detect",
    "event",
    "task",
    "appointment",
    "medication",
    "meeting",
    "personal",
)


def preferred_startup_geometry(
    screen_width: int, screen_height: int, platform_name: str | None = None
) -> tuple[int, int, int, int]:
    """Return a comfortable startup size for the current desktop platform.

    macOS keeps the wide/tall dashboard size that already looks good there.
    Windows uses a smaller normal window with more breathing room around it;
    the Windows UI scale is reduced separately so the full workflow still fits
    without making the app occupy nearly the entire monitor.
    """
    screen_width = max(1, int(screen_width))
    screen_height = max(1, int(screen_height))
    platform_name = (platform_name or sys.platform).lower()

    if platform_name.startswith("win"):






        width = min(1000, screen_width)
        height = min(650, screen_height)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return width, height, x, y




    available_width = max(900, screen_width - 24)
    available_height = max(720, screen_height - 10)
    width = min(1440, available_width, screen_width)
    height = min(1010, available_height, screen_height)
    x = max(0, (screen_width - width) // 2)
    y = max(0, min(7, (screen_height - height) // 2))
    return width, height, x, y


def reminder_value_to_minutes(value: int, unit: str) -> int:
    value = int(value)
    if value < 0:
        raise ValueError("Reminder amount cannot be negative.")

    unit = unit.lower().strip()
    if unit in {"minute", "minutes"}:
        return value
    if unit in {"hour", "hours"}:
        return value * 60
    if unit in {"day", "days"}:
        return value * 1440
    raise ValueError(f"Unknown reminder unit: {unit}")


def duration_value_to_minutes(value: int, unit: str) -> int:
    return reminder_value_to_minutes(value, unit)


def format_reminder_minutes(minutes: int) -> str:
    if minutes == 0:
        return "at start"
    if minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days} day{'s' if days != 1 else ''}"
    if minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{minutes} min"



def format_header_datetime(value: datetime) -> tuple[str, str]:
    """Return friendly date/time strings for the dashboard header."""
    date_text = f"{value.strftime('%A, %B')} {value.day}, {value.year}"
    time_text = value.strftime("%I:%M %p").lstrip("0")
    return date_text, time_text

def validate_google_email(value: str) -> str:
    """Validate a Google-account email entered by the user.

    Google accounts can use Gmail addresses or another email domain, so this
    deliberately validates email shape rather than forcing @gmail.com.
    """
    email = (value or "").strip()
    if not email:
        raise ValueError("Enter the Google account email you want to use for Google Calendar.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid Google account email, for example name@gmail.com.")
    return email


def parse_date_override(value: str):
    value = value.strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Date override must be YYYY-MM-DD or MM/DD/YYYY.")


def parse_time_override(value: str):
    value = value.strip()
    if not value:
        return None

    for fmt in ("%H:%M", "%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(value.upper(), fmt).time()
        except ValueError:
            pass
    raise ValueError("Time override must look like 14:30 or 2:30 PM.")


def apply_datetime_overrides(event, date_value: str, time_value: str):
    date_override = parse_date_override(date_value)
    time_override = parse_time_override(time_value)

    if date_override is None and time_override is None:
        return event

    existing = event.start_at
    if existing is None and (date_override is None or time_override is None):
        raise ValueError(
            "If the note did not resolve an exact date/time, provide both a date and a time override."
        )

    final_date = date_override or existing.date()
    final_time = time_override or existing.time()
    event.start_at = datetime.combine(final_date, final_time).replace(second=0, microsecond=0)
    event.timing_kind = "exact"
    event.confidence_notes = None
    return event


class SmartSchedulerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.db = SchedulerDatabase(DB_PATH)
        self.google = GoogleCalendarClient()
        self.google_email = self.db.get_setting("google_email", "") or ""
        self.reminder_rows: list[tuple[tk.StringVar, tk.StringVar]] = []

        saved_time_zone = self.db.get_setting("time_zone")
        self.user_time_zone = saved_time_zone or detect_local_timezone()
        self.time_zone_needs_confirmation = saved_time_zone is None

        self.root.title(f"HT-SmartScheduler v{VERSION}")
        self._windows_ui = sys.platform.startswith("win")



        self.root.minsize(840, 580) if self._windows_ui else self.root.minsize(1000, 720)


        startup_w, startup_h, startup_x, startup_y = preferred_startup_geometry(
            self.root.winfo_screenwidth(), self.root.winfo_screenheight(), sys.platform
        )
        self.root.geometry(
            f"{startup_w}x{startup_h}+{startup_x}+{startup_y}"
        )





        self._design_width = 1380
        self._design_height = 900
        self._min_ui_scale = 0.52 if self._windows_ui else 0.95
        self._ui_scale = 1.0
        self._resize_after_id = None

        self._configure_style()
        self._build_ui()
        if self._windows_ui:




            self.root.protocol("WM_DELETE_WINDOW", self._windows_quit)
            self.root.bind("<Control-q>", lambda _e: self._windows_quit())
        self.root.bind("<Configure>", self._on_window_configure, add="+")


        self.root.bind("<Control-plus>", lambda _e: self._nudge_ui_scale(0.10))
        self.root.bind("<Control-equal>", lambda _e: self._nudge_ui_scale(0.10))
        self.root.bind("<Control-minus>", lambda _e: self._nudge_ui_scale(-0.10))
        self.root.bind("<Command-plus>", lambda _e: self._nudge_ui_scale(0.10))
        self.root.bind("<Command-equal>", lambda _e: self._nudge_ui_scale(0.10))
        self.root.bind("<Command-minus>", lambda _e: self._nudge_ui_scale(-0.10))
        self._set_reminder_count(1)
        self.refresh_events()
        self.refresh_service_status()
        self.refresh_google_status()



        self.root.after(5000, self._periodic_refresh_events)

        if self.time_zone_needs_confirmation:
            self.root.after(250, self.confirm_first_run_timezone)






        self._service_cleanup_done = False
        self._service_restart_failures = 0
        self._service_next_restart_at = 0.0
        self.root.after(900, self.ensure_reminder_service)
        if self._windows_ui:


            self.root.after(5000, self._windows_service_status_refresh)
        else:
            self.root.after(5000, self._reminder_service_watchdog)

    def _configure_style(self):
        """Create a clean dashboard look that is consistent on macOS/Windows."""
        self.colors = {
            "bg": "#F3F7FC",
            "card": "#FFFFFF",
            "soft": "#F7FAFE",
            "soft_blue": "#EAF3FF",
            "blue": "#1478F2",
            "blue_dark": "#0D5FC6",
            "text": "#102A4C",
            "muted": "#66758A",
            "border": "#D8E3EF",
            "green": "#18A558",
            "green_soft": "#ECF9F0",
            "orange": "#F5A623",
            "red": "#EF4444",
        }




        self._font_specs = {
            "title": (31, "bold"),
            "subtitle": (15, "normal"),
            "card_title": (17, "bold"),
            "card_subtitle": (13, "normal"),
            "body": (14, "normal"),
            "body_bold": (14, "bold"),
            "small": (13, "normal"),
            "small_bold": (13, "bold"),
            "tiny": (12, "normal"),
            "badge": (14, "bold"),
            "feature_icon": (22, "bold"),
            "input": (16, "normal"),
            "mono": (13, "normal"),
            "nav": (15, "bold"),
            "clock_date": (18, "bold"),
            "clock_time": (26, "bold"),
        }



        if self._windows_ui:



            self._font_specs.update({
                "title": (25, "bold"),
                "subtitle": (12, "normal"),
                "nav": (12, "bold"),
                "clock_date": (14, "bold"),
                "clock_time": (20, "bold"),
                "card_title": (15, "bold"),
                "card_subtitle": (11, "normal"),
                "body": (12, "normal"),
                "body_bold": (12, "bold"),
                "small": (11, "normal"),
                "small_bold": (11, "bold"),
                "tiny": (10, "normal"),
                "badge": (11, "bold"),
                "feature_icon": (17, "bold"),
                "input": (13, "normal"),
                "mono": (11, "normal"),
            })
        self.fonts = {}
        for name, (size, weight) in self._font_specs.items():
            family = "Menlo" if name == "mono" else "Helvetica"
            self.fonts[name] = tkfont.Font(
                root=self.root, family=family, size=size, weight=weight
            )

        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        self.style = style
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"])
        style.configure("Soft.TFrame", background=self.colors["soft"])
        style.configure("Header.TFrame", background=self.colors["bg"])

        style.configure("TLabel", font=self.fonts["body"])
        style.configure("TEntry", font=self.fonts["body"])
        style.configure("TCombobox", font=self.fonts["body"])
        style.configure("TSpinbox", font=self.fonts["body"])
        style.configure("Reminder.TSpinbox", font=self.fonts["body"], padding=(4, 4))
        style.configure("Reminder.TCombobox", font=self.fonts["body"], padding=(4, 4))
        style.configure("TRadiobutton", font=self.fonts["body"])
        style.configure("TCheckbutton", font=self.fonts["body"])

        style.configure(
            "AppTitle.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["text"],
            font=self.fonts["title"],
        )
        style.configure(
            "AppSubtitle.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=self.fonts["subtitle"],
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=self.fonts["card_title"],
        )
        style.configure(
            "CardSubtitle.TLabel",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=self.fonts["small"],
        )
        style.configure(
            "Body.TLabel",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=self.fonts["body"],
        )
        style.configure(
            "Muted.TLabel",
            background=self.colors["card"],
            foreground=self.colors["muted"],
            font=self.fonts["small"],
        )
        style.configure(
            "Status.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=self.fonts["small"],
        )
        style.configure(
            "Primary.TButton",
            background=self.colors["blue"],
            foreground="white",
            borderwidth=0,
            focusthickness=0,
            font=self.fonts["nav"],
            padding=(16, 8),
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["blue_dark"]), ("pressed", self.colors["blue_dark"])],
            foreground=[("disabled", "#B8C3D1")],
        )
        style.configure(
            "Secondary.TButton",
            background="#FFFFFF",
            foreground=self.colors["text"],
            bordercolor=self.colors["border"],
            lightcolor=self.colors["border"],
            darkcolor=self.colors["border"],
            font=self.fonts["body"],
            padding=(12, 7),
        )
        style.map("Secondary.TButton", background=[("active", self.colors["soft_blue"])])
        style.configure(
            "Tiny.TButton",
            background="#FFFFFF",
            foreground=self.colors["text"],
            font=self.fonts["small"],
            padding=(8, 4),
        )
        style.configure(
            "Big.TCheckbutton",
            background=self.colors["card"],
            foreground=self.colors["text"],
            font=self.fonts["body"],
        )
        style.map("Big.TCheckbutton", background=[("active", self.colors["card"])])
        style.configure(
            "Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            foreground=self.colors["text"],
            rowheight=28,
            borderwidth=0,
            font=self.fonts["small"],
        )
        style.configure(
            "Treeview.Heading",
            background="#F0F5FA",
            foreground=self.colors["text"],
            font=self.fonts["small_bold"],
            relief="flat",
            padding=(5, 7),
        )
        style.map("Treeview", background=[("selected", "#DDEEFF")], foreground=[("selected", self.colors["text"])])

    def _responsive_scale_for_size(self, width: int, height: int) -> float:
        """Return a comfortable UI scale for the current window dimensions."""
        if width <= 1 or height <= 1:
            return self._ui_scale


        area_ratio = (width * height) / float(self._design_width * self._design_height)
        scale = area_ratio ** 0.5



        if getattr(self, "_windows_ui", False):
            scale *= 0.86
        return max(getattr(self, "_min_ui_scale", 0.95), min(1.55, scale))

    def _apply_ui_scale(self, scale: float):
        scale = max(getattr(self, "_min_ui_scale", 0.95), min(1.65, float(scale)))
        if abs(scale - self._ui_scale) < 0.025:
            return
        self._ui_scale = scale
        header_fonts = {"title", "subtitle", "nav", "clock_date", "clock_time"}
        for name, (base_size, _weight) in self._font_specs.items():



            min_size = 7 if getattr(self, "_windows_ui", False) and name not in header_fonts else 8
            self.fonts[name].configure(size=max(min_size, int(round(base_size * scale))))



        self.style.configure("Treeview", rowheight=max(28, int(round(28 * scale))))
        self.style.configure(
            "Primary.TButton", padding=(int(16 * scale), int(8 * scale))
        )
        self.style.configure(
            "Secondary.TButton", padding=(int(12 * scale), int(7 * scale))
        )
        self.style.configure(
            "Tiny.TButton", padding=(int(8 * scale), int(4 * scale))
        )

    def _finish_responsive_resize(self):
        self._resize_after_id = None
        self._apply_ui_scale(
            self._responsive_scale_for_size(self.root.winfo_width(), self.root.winfo_height())
        )

    def _on_window_configure(self, event):


        if event.widget is not self.root:
            return
        if self._resize_after_id is not None:
            try:
                self.root.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.root.after(90, self._finish_responsive_resize)

    def _nudge_ui_scale(self, delta: float):
        """Accessibility shortcut: Ctrl/Cmd +/- makes text larger/smaller."""
        self._apply_ui_scale(self._ui_scale + delta)
        return "break"

    def _card(self, parent, title: str, number: str | None = None, subtitle: str | None = None, compact: bool = False):
        shell = tk.Frame(
            parent,
            bg=self.colors["card"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            bd=0,
        )
        if compact and getattr(self, "_windows_ui", False):
            header_padding = (8, 4, 8, 1)
            body_padding = (8, 2, 8, 5)
        else:
            header_padding = (12, 6, 12, 2) if compact else (12, 10, 12, 4)
            body_padding = (12, 3, 12, 7) if compact else (12, 6, 12, 12)
        header = ttk.Frame(shell, style="Card.TFrame", padding=header_padding)
        header.pack(fill="x")
        if number is not None:
            badge = tk.Label(
                header,
                text=number,
                bg=self.colors["blue"],
                fg="white",
                font=self.fonts["body_bold"],
                width=2,
                height=1,
                padx=3,
                pady=2,
            )
            badge.pack(side="left", padx=(0, 9))
        title_box = ttk.Frame(header, style="Card.TFrame")
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text=title, style="CardTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(title_box, text=subtitle, style="CardSubtitle.TLabel").pack(anchor="w", pady=(1, 0))
        body = ttk.Frame(shell, style="Card.TFrame", padding=body_padding)
        body.pack(fill="both", expand=True)
        return shell, body, header

    def _feature_chip(self, parent, icon: str, title: str, subtitle: str):
        chip = tk.Frame(
            parent,
            bg="#EEF5FF",
            highlightbackground="#D7E6FB",
            highlightthickness=1,
            padx=10,
            pady=7,
        )
        tk.Label(chip, text=icon, bg="#EEF5FF", fg=self.colors["blue"], font=self.fonts["feature_icon"]).pack(side="left")
        text = tk.Frame(chip, bg="#EEF5FF")
        text.pack(side="left", padx=(7, 0))
        tk.Label(text, text=title, bg="#EEF5FF", fg=self.colors["text"], font=self.fonts["small_bold"]).pack(anchor="w")
        tk.Label(text, text=subtitle, bg="#EEF5FF", fg=self.colors["muted"], font=self.fonts["tiny"]).pack(anchor="w")
        return chip

    def _make_scrollable_form(self, parent):
        """Return a vertically scrollable frame for the Create Schedule form."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            parent,
            bg=self.colors["bg"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas, style="App.TFrame")
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def update_scroll_region(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_inner_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        inner.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_inner_width)



        def on_wheel(event):
            delta = getattr(event, "delta", 0)
            if delta:
                step = -1 if delta > 0 else 1
                canvas.yview_scroll(step, "units")
            return "break"

        def bind_wheel(_event=None):
            canvas.bind_all("<MouseWheel>", on_wheel)

        def unbind_wheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)
        inner.bind("<Enter>", bind_wheel)
        inner.bind("<Leave>", unbind_wheel)
        return inner

    def _build_action_bar(self, parent):
        """Always-visible primary actions for the Create Schedule panel."""
        bar = tk.Frame(
            parent,
            bg="#FFFFFF",
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=6 if self._windows_ui else 10,
            pady=3 if self._windows_ui else 4,
        )




        bar_height = 54 if self._windows_ui else 72
        bar.configure(height=bar_height)
        bar.pack_propagate(False)
        bar.pack(fill="x", pady=(0, 0))

        ttk.Button(
            bar,
            text="Save Schedule",
            style="Primary.TButton",
            command=self.save_schedule,
        ).pack(side="left")
        ttk.Button(
            bar,
            text="Test Reminder" if self._windows_ui else "Test Selected Reminder",
            style="Secondary.TButton",
            command=self.test_reminder,
        ).pack(side="left", padx=(8, 0))

        self.service_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.service_var, style="Muted.TLabel").pack(
            side="left", padx=(12, 0)
        )
        ttk.Button(
            bar,
            text="Start",
            style="Tiny.TButton",
            command=self.start_service,
        ).pack(side="right")
        ttk.Button(
            bar,
            text="Stop",
            style="Tiny.TButton",
            command=self.stop_service,
        ).pack(side="right", padx=(0, 6))

    def _build_ui(self):


        self.root.minsize(840, 580) if self._windows_ui else self.root.minsize(1000, 720)

        outer_padding = (8, 2) if self._windows_ui else (18, 14)
        outer = ttk.Frame(self.root, style="App.TFrame", padding=outer_padding)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        header = ttk.Frame(outer, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 2 if self._windows_ui else 12))
        header.columnconfigure(0, weight=1)

        branding = ttk.Frame(header, style="Header.TFrame")
        branding.grid(row=0, column=0, sticky="w")
        ttk.Label(branding, text="HT-SmartScheduler", style="AppTitle.TLabel").pack(anchor="w")
        if self._windows_ui:


            ttk.Label(
                branding,
                text="Natural-language scheduling, popup/voice alerts, optional Google Calendar.",
                style="AppSubtitle.TLabel",
            ).pack(anchor="w")
        else:
            ttk.Label(
                branding,
                text="Turn everyday reminders into a simple conversation.",
                style="AppSubtitle.TLabel",
            ).pack(anchor="w")
            ttk.Label(
                branding,
                text="Natural-language scheduling, flexible popup/voice alerts, and optional Google Calendar sync.",
                style="AppSubtitle.TLabel",
            ).pack(anchor="w", pady=(2, 0))




        clock_panel = tk.Frame(
            header,
            bg="#EEF5FF",
            highlightbackground="#D7E6FB",
            highlightthickness=1,
            padx=6 if self._windows_ui else 18,
            pady=0 if self._windows_ui else 9,
        )
        clock_panel.grid(row=0, column=1, sticky="e")
        self.header_date_var = tk.StringVar(value="")
        self.header_time_var = tk.StringVar(value="")
        tk.Label(
            clock_panel,
            textvariable=self.header_date_var,
            bg="#EEF5FF",
            fg=self.colors["text"],
            font=self.fonts["clock_date"],
        ).pack(anchor="e")
        tk.Label(
            clock_panel,
            textvariable=self.header_time_var,
            bg="#EEF5FF",
            fg=self.colors["blue"],
            font=self.fonts["clock_time"],
        ).pack(anchor="e", pady=(2, 0))



        nav = tk.Frame(outer, bg="#E9F1F9", highlightbackground=self.colors["border"], highlightthickness=1)
        nav.grid(row=1, column=0, sticky="ew", pady=(0, 2 if self._windows_ui else 10))
        nav_padx = 10 if self._windows_ui else 22
        nav_pady = 1 if self._windows_ui else 7
        tk.Label(nav, text="▣  Create Schedule", bg=self.colors["blue"], fg="white", font=self.fonts["nav"], padx=nav_padx, pady=nav_pady).pack(side="left", fill="x", expand=True)
        tk.Label(nav, text="☷  Upcoming Events", bg="#E9F1F9", fg=self.colors["muted"], font=self.fonts["nav"], padx=nav_padx, pady=nav_pady).pack(side="left", fill="x", expand=True)




        content = tk.PanedWindow(
            outer,
            orient=tk.HORIZONTAL,
            bg=self.colors["border"],
            bd=0,
            relief="flat",
            sashwidth=10,
            sashrelief="flat",
            sashpad=2,
            opaqueresize=True,
            showhandle=False,
        )
        content.grid(row=2, column=0, sticky="nsew")
        outer.rowconfigure(2, weight=1)

        left = ttk.Frame(content, style="App.TFrame")
        right = ttk.Frame(content, style="App.TFrame")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)



        content.add(left, minsize=465 if self._windows_ui else 470, stretch="always")
        content.add(right, minsize=340 if self._windows_ui else 430, stretch="always")
        self.main_paned = content




        form_host = ttk.Frame(left, style="App.TFrame")
        form_host.grid(row=0, column=0, sticky="nsew")
        create_parent = self._make_scrollable_form(form_host)
        self._build_create_tab(create_parent)




        action_host = ttk.Frame(left, style="App.TFrame")
        action_host.grid(row=1, column=0, sticky="ew")
        self._build_action_bar(action_host)

        self._build_events_tab(right)


        self.root.after(120, self._set_initial_main_split)
        self.root.after(140, self._finish_responsive_resize)
        self.root.after(200, self._update_header_clock)

    def _set_initial_main_split(self):
        """Set the dashboard divider once without fighting later user drags."""
        paned = getattr(self, "main_paned", None)
        if paned is None:
            return
        try:
            total = paned.winfo_width()
            threshold = 820 if self._windows_ui else 900
            if total > threshold:
                ratio = 0.55 if self._windows_ui else 0.58
                paned.sash_place(0, int(total * ratio), 0)
        except tk.TclError:
            pass

    def _build_create_tab(self, parent):

        note_shell, note_frame, note_header = self._card(
            parent,
            "What do you need to remember?",
            "1",
            'Use natural language, for example: "Meeting tomorrow at 3 PM"',
            compact=True,
        )
        note_shell.pack(fill="x", pady=(0, 4))
        self.note_text = tk.Text(
            note_frame,
            height=3 if self._windows_ui else 4,
            wrap="word",
            font=self.fonts["input"],
            bg="#FFFFFF",
            fg=self.colors["text"],
            insertbackground=self.colors["blue"],
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["blue"],
            highlightthickness=1,
            relief="flat",
            padx=8,
            pady=7,
        )
        self.note_text.pack(fill="both", expand=True)


        detail_shell, details, _ = self._card(
            parent,
            "More details (optional)",
            "2",
            compact=True,
        )
        detail_shell.pack(fill="x", pady=(0, 4))
        details.columnconfigure(1, weight=1)
        details.columnconfigure(3, weight=1)

        self.date_override_var = tk.StringVar()
        self.time_override_var = tk.StringVar()
        self.duration_value_var = tk.StringVar()
        self.duration_unit_var = tk.StringVar(value="minutes")
        self.event_type_var = tk.StringVar(value="Auto detect")
        self.location_var = tk.StringVar()
        self.recurrence_var = tk.StringVar(value="Does not repeat")
        self.recurrence_interval_var = tk.StringVar(value="1")
        self.recurrence_count_var = tk.StringVar(value="0")

        if self._windows_ui:



            ttk.Label(details, text="Date override", style="Body.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
            ttk.Entry(details, textvariable=self.date_override_var).grid(row=0, column=1, sticky="ew", pady=2)
            ttk.Label(details, text="Time override", style="Body.TLabel").grid(row=0, column=2, sticky="w", padx=(10, 6), pady=2)
            ttk.Entry(details, textvariable=self.time_override_var).grid(row=0, column=3, sticky="ew", pady=2)

            ttk.Label(details, text="Duration", style="Body.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
            duration_box = ttk.Frame(details, style="Card.TFrame")
            duration_box.grid(row=1, column=1, sticky="ew", pady=2)
            ttk.Entry(duration_box, width=6, textvariable=self.duration_value_var).pack(side="left")
            ttk.Combobox(duration_box, width=7, state="readonly", values=("minutes", "hours", "days"), textvariable=self.duration_unit_var).pack(side="left", padx=(4, 0))

            ttk.Label(details, text="Type", style="Body.TLabel").grid(row=1, column=2, sticky="w", padx=(10, 6), pady=2)
            ttk.Combobox(details, state="readonly", values=EVENT_TYPE_OPTIONS, textvariable=self.event_type_var).grid(row=1, column=3, sticky="ew", pady=2)

            ttk.Label(details, text="Location", style="Body.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=2)
            ttk.Entry(details, textvariable=self.location_var).grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)

            ttk.Label(details, text="Repeat", style="Body.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 6), pady=(4, 2))
            ttk.Combobox(details, state="readonly", values=RECURRENCE_OPTIONS, textvariable=self.recurrence_var).grid(row=3, column=1, sticky="ew", pady=(4, 2))
            repeat_options = ttk.Frame(details, style="Card.TFrame")
            repeat_options.grid(row=3, column=2, columnspan=2, sticky="w", pady=(4, 2), padx=(10, 0))
            ttk.Label(repeat_options, text="Every", style="Body.TLabel").pack(side="left")
            ttk.Spinbox(repeat_options, from_=1, to=99, width=4, textvariable=self.recurrence_interval_var).pack(side="left", padx=(4, 3))
            ttk.Label(repeat_options, text="cycle(s)  Stop", style="Body.TLabel").pack(side="left")
            ttk.Spinbox(repeat_options, from_=0, to=999, width=4, textvariable=self.recurrence_count_var).pack(side="left", padx=(4, 3))
            ttk.Label(repeat_options, text="times", style="Muted.TLabel").pack(side="left")
        else:
            details.columnconfigure(4, weight=1)
            ttk.Label(details, text="Date override", style="Body.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(details, textvariable=self.date_override_var, width=18).grid(row=0, column=1, sticky="ew", pady=2)
            ttk.Label(details, text="YYYY-MM-DD", style="Muted.TLabel").grid(row=0, column=2, sticky="w", padx=(7, 14))

            ttk.Label(details, text="Time override", style="Body.TLabel").grid(row=0, column=3, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(details, textvariable=self.time_override_var, width=16).grid(row=0, column=4, sticky="ew", pady=2)
            ttk.Label(details, text="2:30 PM or 14:30", style="Muted.TLabel").grid(row=0, column=5, sticky="w", padx=(7, 0))

            ttk.Label(details, text="Duration", style="Body.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
            duration_box = ttk.Frame(details, style="Card.TFrame")
            duration_box.grid(row=1, column=1, sticky="ew", pady=2)
            ttk.Entry(duration_box, width=8, textvariable=self.duration_value_var).pack(side="left")
            ttk.Combobox(duration_box, width=9, state="readonly", values=("minutes", "hours", "days"), textvariable=self.duration_unit_var).pack(side="left", padx=(5, 0))
            ttk.Label(details, text="blank = detected/default", style="Muted.TLabel").grid(row=1, column=2, sticky="w", padx=(7, 14))

            ttk.Label(details, text="Type", style="Body.TLabel").grid(row=1, column=3, sticky="w", padx=(0, 8), pady=2)
            ttk.Combobox(details, state="readonly", values=EVENT_TYPE_OPTIONS, textvariable=self.event_type_var).grid(row=1, column=4, sticky="ew", pady=4)

            ttk.Label(details, text="Location", style="Body.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
            ttk.Entry(details, textvariable=self.location_var).grid(row=2, column=1, columnspan=5, sticky="ew", pady=4)

            ttk.Label(details, text="Repeat", style="Body.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=(7, 3))
            ttk.Combobox(details, state="readonly", values=RECURRENCE_OPTIONS, textvariable=self.recurrence_var).grid(row=3, column=1, sticky="ew", pady=(7, 3))
            repeat_options = ttk.Frame(details, style="Card.TFrame")
            repeat_options.grid(row=3, column=2, columnspan=4, sticky="w", pady=(7, 3), padx=(7, 0))
            ttk.Label(repeat_options, text="Every", style="Body.TLabel").pack(side="left")
            ttk.Spinbox(repeat_options, from_=1, to=99, width=5, textvariable=self.recurrence_interval_var).pack(side="left", padx=(5, 4))
            ttk.Label(repeat_options, text="cycle(s)   Stop after", style="Body.TLabel").pack(side="left")
            ttk.Spinbox(repeat_options, from_=0, to=999, width=6, textvariable=self.recurrence_count_var).pack(side="left", padx=(5, 4))
            ttk.Label(repeat_options, text="occurrences (0 = no end)", style="Muted.TLabel").pack(side="left")


        reminder_shell, reminders_frame, _ = self._card(
            parent,
            "Reminder",
            "3",
            compact=True,
        )
        reminder_shell.pack(fill="x", pady=(0, 4))
        reminders_frame.columnconfigure(1, weight=1)

        ttk.Label(reminders_frame, text="Delivery method", style="Body.TLabel").grid(row=0, column=0, sticky="nw", pady=3)
        self.reminder_mode_var = tk.StringVar(value="Popup + Voice")
        mode_box = ttk.Frame(reminders_frame, style="Card.TFrame")
        mode_box.grid(row=0, column=1, sticky="w", padx=(8, 0), pady=3)
        for label in REMINDER_MODE_OPTIONS:
            ttk.Radiobutton(
                mode_box,
                text=label,
                variable=self.reminder_mode_var,
                value=label,
            ).pack(side="left", padx=(0, 5 if self._windows_ui else 10))
        ttk.Button(
            mode_box,
            text="Test method" if self._windows_ui else "Test selected method",
            style="Tiny.TButton",
            command=self.test_reminder,
        ).pack(side="left", padx=(4, 0))

        ttk.Label(reminders_frame, text="How many reminders?", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        self.reminder_count_var = tk.IntVar(value=1)
        count_box = ttk.Frame(reminders_frame, style="Card.TFrame")
        count_box.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=2)
        self.reminder_count = ttk.Spinbox(count_box, from_=0, to=MAX_REMINDERS, width=5, textvariable=self.reminder_count_var, command=self._reminder_count_changed)
        self.reminder_count.pack(side="left")
        self.reminder_count.bind("<KeyRelease>", lambda _event: self._reminder_count_changed())
        ttk.Label(count_box, text="0 = none, maximum 5", style="Muted.TLabel").pack(side="left", padx=(8, 0))

        self.reminder_rows_frame = ttk.Frame(reminders_frame, style="Card.TFrame")
        self.reminder_rows_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 0))





        bottom_options = ttk.Frame(parent, style="App.TFrame")
        bottom_options.pack(fill="x", pady=(0, 4))


        google_shell, google_frame, _ = self._card(
            bottom_options,
            "Google Calendar (optional)",
            "4",
            compact=True,
        )
        google_shell.pack(fill="x", pady=(0, 4))

        self.google_sync_var = tk.BooleanVar(value=False)
        self.google_sync_check = ttk.Checkbutton(
            google_frame,
            text="Add this schedule to Google Calendar",
            variable=self.google_sync_var,
            command=self._google_sync_changed,
            style="Big.TCheckbutton",
        )
        self.google_sync_check.pack(anchor="w")

        email_row = ttk.Frame(google_frame, style="Card.TFrame")
        email_row.pack(fill="x", pady=(3, 0))
        ttk.Label(email_row, text="Google account", style="Body.TLabel").pack(side="left")
        self.google_email_var = tk.StringVar(value=self.google_email)
        self.google_email_entry = ttk.Entry(email_row, textvariable=self.google_email_var)
        self.google_email_entry.pack(side="left", fill="x", expand=True, padx=(8, 8))
        ttk.Label(email_row, text="optional", style="Muted.TLabel").pack(side="left")

        google_row = ttk.Frame(google_frame, style="Card.TFrame")
        google_row.pack(fill="x", pady=(3, 0))
        self.google_connect_button = ttk.Button(google_row, text="Connect Google Calendar", command=self.connect_google_calendar, style="Secondary.TButton")
        self.google_connect_button.pack(side="left")
        self.google_disconnect_button = ttk.Button(google_row, text="Disconnect", command=self.disconnect_google_calendar, style="Tiny.TButton")
        self.google_disconnect_button.pack(side="left", padx=(8, 0))
        self.google_status_var = tk.StringVar()
        if self._windows_ui:
            ttk.Label(
                google_row,
                textvariable=self.google_status_var,
                style="Muted.TLabel",
            ).pack(side="left", padx=(8, 0))
        else:
            ttk.Label(
                google_frame,
                textvariable=self.google_status_var,
                style="Muted.TLabel",
            ).pack(anchor="w", pady=(3, 0))
        self._google_sync_changed()


        tz_shell, tz_frame, _ = self._card(
            bottom_options,
            "Time Zone",
            "5",
            "Detected from your computer and used for parsing, reminders, and Calendar sync.",
            compact=True,
        )
        tz_shell.pack(fill="x")
        self.time_zone_var = tk.StringVar(value=self.user_time_zone)
        if self._windows_ui:
            tz_row = ttk.Frame(tz_frame, style="Card.TFrame")
            tz_row.pack(fill="x")
            ttk.Label(tz_row, text="Time zone", style="Body.TLabel").pack(side="left")
            ttk.Entry(tz_row, textvariable=self.time_zone_var).pack(side="left", fill="x", expand=True, padx=(6, 6))
            ttk.Button(
                tz_row,
                text="Detect",
                command=self.detect_device_timezone,
                style="Tiny.TButton",
            ).pack(side="left")
        else:
            ttk.Label(tz_frame, text="Your time zone", style="Body.TLabel").pack(anchor="w")
            ttk.Entry(tz_frame, textvariable=self.time_zone_var).pack(fill="x", pady=(2, 3))
            ttk.Button(
                tz_frame,
                text="Detect from device",
                command=self.detect_device_timezone,
                style="Secondary.TButton",
            ).pack(anchor="w")


    def _build_events_tab(self, parent):

        events_shell, events_body, events_header = self._card(
            parent,
            "Upcoming Events",
            None,
            "Past one-time events clear automatically; recurring events show their next occurrence.",
            compact=self._windows_ui,
        )
        if self._windows_ui:


            events_shell.pack(fill="x", expand=False, pady=(0, 6))
        else:
            events_shell.pack(fill="both", expand=True, pady=(0, 8))






        actions = ttk.Frame(events_body, style="Card.TFrame")
        actions.pack(fill="x", pady=(0, 4))
        ttk.Button(
            actions,
            text="Delete Selected",
            command=self.delete_selected_event,
            style="Tiny.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Refresh",
            command=self.refresh_events,
            style="Tiny.TButton",
        ).pack(side="right")
        table_parent = ttk.Frame(events_body, style="Card.TFrame")
        table_parent.pack(fill="both", expand=True)

        columns = ("event", "start", "repeat", "reminders", "delivery", "google")
        self.events_tree = ttk.Treeview(
            table_parent,
            columns=columns,
            show="headings",
            height=5 if self._windows_ui else 9,
        )
        headings = {
            "event": "Event",
            "start": "Next start",
            "repeat": "Repeat",
            "reminders": "Reminder",
            "delivery": "Delivery",
            "google": "Google",
        }
        for key, label in headings.items():
            self.events_tree.heading(key, text=label)
        if self._windows_ui:
            self.events_tree.column("event", width=60, minwidth=48)
            self.events_tree.column("start", width=95, minwidth=82)
            self.events_tree.column("repeat", width=45, minwidth=42)
            self.events_tree.column("reminders", width=50, minwidth=46)
            self.events_tree.column("delivery", width=55, minwidth=50)
            self.events_tree.column("google", width=40, minwidth=36, anchor="center")
        else:
            self.events_tree.column("event", width=125)
            self.events_tree.column("start", width=150)
            self.events_tree.column("repeat", width=85)
            self.events_tree.column("reminders", width=90)
            self.events_tree.column("delivery", width=100)
            self.events_tree.column("google", width=80, anchor="center")
        scrollbar = ttk.Scrollbar(table_parent, orient="vertical", command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=scrollbar.set)
        self.events_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        result_shell, result_frame, result_header = self._card(
            parent,
            "Saved Reminder Preview",
            None,
            "The latest save/test result stays visible here.",
            compact=self._windows_ui,
        )
        result_shell.pack(fill="x", pady=(0, 8))
        ttk.Button(result_header, text="Clear", command=lambda: self._write_result(""), style="Tiny.TButton").pack(side="right")
        self.result_text = tk.Text(
            result_frame,
            height=4 if self._windows_ui else 7,
            wrap="word",
            font=self.fonts["mono"],
            state="disabled",
            bg=self.colors["green_soft"],
            fg=self.colors["text"],
            highlightbackground="#CFEAD7",
            highlightthickness=1,
            relief="flat",
            padx=9,
            pady=7,
        )
        self.result_text.pack(fill="both", expand=True)


        tips_shell, tips_frame, _ = self._card(parent, "Tips & Features", None, None, compact=self._windows_ui)
        tips_shell.pack(fill="x")
        tips_frame.columnconfigure(0, weight=1)
        tips_frame.columnconfigure(1, weight=1)
        tips = [
            ("Natural Language", 'Try: "Dentist in the next 10 minutes"'),
            ("Google Calendar", "Optional — local reminders always work."),
            ("Popup & Voice", "Choose both, popup only, or voice only."),
            ("Recurring Reminders", "Daily, weekdays, weekly, monthly, yearly."),
            ("Auto Time Zone", "Detects the device time zone automatically."),
            ("Background Service", "Keeps checking reminders while the computer is awake."),
        ]
        for idx, (title, desc) in enumerate(tips):
            box = tk.Frame(tips_frame, bg="#F6F9FD", highlightbackground=self.colors["border"], highlightthickness=1, padx=6 if self._windows_ui else 9, pady=4 if self._windows_ui else 7)
            box.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=(0 if idx % 2 == 0 else 5, 5 if idx % 2 == 0 else 0), pady=4)
            tk.Label(box, text=title, bg="#F6F9FD", fg=self.colors["text"], font=self.fonts["small_bold"]).pack(anchor="w")
            tk.Label(box, text=desc, bg="#F6F9FD", fg=self.colors["muted"], font=self.fonts["tiny"], justify="left", wraplength=150 if self._windows_ui else 220).pack(anchor="w", pady=(1 if self._windows_ui else 2, 0))

    def _update_header_clock(self):
        """Update the header date/time using the scheduler's active time zone."""
        try:
            now = current_wall_time(self.user_time_zone)
        except Exception:
            now = datetime.now()

        date_text, time_text = format_header_datetime(now)
        if hasattr(self, "header_date_var"):
            self.header_date_var.set(date_text)
        if hasattr(self, "header_time_var"):
            self.header_time_var.set(time_text)



        try:
            self.root.after(15000, self._update_header_clock)
        except tk.TclError:
            pass

    def _reminder_count_changed(self):
        try:
            count = int(self.reminder_count_var.get())
        except (ValueError, tk.TclError):
            return
        count = max(0, min(MAX_REMINDERS, count))
        self.reminder_count_var.set(count)
        self._set_reminder_count(count)

    def _set_reminder_count(self, count: int):
        existing = [(value.get(), unit.get()) for value, unit in self.reminder_rows]

        for widget in self.reminder_rows_frame.winfo_children():
            widget.destroy()
        self.reminder_rows = []

        for index in range(count):
            row = ttk.Frame(self.reminder_rows_frame)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=f"Reminder {index + 1}", width=12).pack(side="left")

            if index < len(existing):
                default_value, default_unit = existing[index]
            else:
                default_value, default_unit = DEFAULT_REMINDERS[index]

            value_var = tk.StringVar(value=str(default_value))
            unit_var = tk.StringVar(value=default_unit)
            ttk.Spinbox(row, from_=0, to=9999, width=8, textvariable=value_var, style="Reminder.TSpinbox").pack(side="left", ipady=1)
            ttk.Combobox(
                row,
                width=10,
                state="readonly",
                values=("minutes", "hours", "days"),
                textvariable=unit_var,
                style="Reminder.TCombobox",
            ).pack(side="left", padx=(6, 6), ipady=1)
            ttk.Label(row, text="before each occurrence").pack(side="left")
            self.reminder_rows.append((value_var, unit_var))

    def get_reminder_mode(self) -> str:
        label = self.reminder_mode_var.get().strip()
        mapping = {
            "Popup + Voice": "both",
            "Popup only": "popup",
            "Voice only": "voice",
        }
        try:
            return mapping[label]
        except KeyError as exc:
            raise ValueError("Choose a valid reminder method.") from exc

    @staticmethod
    def reminder_mode_label(mode: str) -> str:
        return {
            "both": "Popup + Voice",
            "popup": "Popup only",
            "voice": "Voice only",
        }.get((mode or "both").lower(), "Popup + Voice")

    def get_reminder_minutes(self) -> list[int]:
        values = []
        for value_var, unit_var in self.reminder_rows:
            raw = value_var.get().strip()
            if not raw:
                raise ValueError("Each reminder needs a number.")
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValueError(f"Reminder amount '{raw}' is not a whole number.") from exc

            minutes = reminder_value_to_minutes(value, unit_var.get())
            if minutes not in values:
                values.append(minutes)
        return sorted(values, reverse=True)

    def get_duration_override(self):
        raw = self.duration_value_var.get().strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError("Duration must be a whole number.") from exc
        if value <= 0:
            raise ValueError("Duration must be greater than zero.")
        return duration_value_to_minutes(value, self.duration_unit_var.get())

    def get_recurrence_rule(self):
        label = self.recurrence_var.get()
        if label == "Does not repeat":
            return None

        try:
            interval = int(self.recurrence_interval_var.get())
            count = int(self.recurrence_count_var.get())
        except ValueError as exc:
            raise ValueError("Repeat interval and occurrence count must be whole numbers.") from exc

        if interval < 1:
            raise ValueError("Repeat interval must be at least 1.")
        if count < 0:
            raise ValueError("Occurrence count cannot be negative.")

        return build_rrule(label.lower(), interval=interval, count=(count or None))

    def _write_result(self, text: str):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

    def _save_time_zone(self, value: str) -> str:
        zone = validate_timezone_name(value)
        self.user_time_zone = zone
        self.time_zone_var.set(zone)
        self.db.set_setting("time_zone", zone)
        if hasattr(self, "header_date_var"):
            try:
                now = current_wall_time(zone)
            except Exception:
                now = datetime.now()
            date_text, time_text = format_header_datetime(now)
            self.header_date_var.set(date_text)
            self.header_time_var.set(time_text)
        return zone

    def detect_device_timezone(self):
        detected = detect_local_timezone()
        try:
            zone = self._save_time_zone(detected)
        except ValueError as exc:
            messagebox.showerror("Time zone", str(exc))
            return
        messagebox.showinfo("Time zone", f"Using device time zone: {zone}")
        self.refresh_events()

    def confirm_first_run_timezone(self):
        detected = self.user_time_zone
        use_detected = messagebox.askyesno(
            "Set your time zone",
            "HT-SmartScheduler uses one time zone for natural-language parsing, "
            "local reminders, recurrence, and Google Calendar.\n\n"
            f"Detected from this device: {detected}\n\n"
            "Use this time zone?",
            parent=self.root,
        )

        if use_detected:
            self._save_time_zone(detected)
            self.time_zone_needs_confirmation = False
            return

        while True:
            value = simpledialog.askstring(
                "Choose time zone",
                "Enter an IANA time zone, for example:\n"
                "America/Los_Angeles\nAmerica/Chicago\nAmerica/New_York",
                initialvalue=detected,
                parent=self.root,
            )
            if value is None:


                self._save_time_zone(detected)
                self.time_zone_needs_confirmation = False
                return
            try:
                self._save_time_zone(value)
            except ValueError as exc:
                messagebox.showerror("Time zone", str(exc), parent=self.root)
                continue
            self.time_zone_needs_confirmation = False
            return

    def _ask_for_exact_time_in_window(self, event) -> bool:
        if not event.window_start or not event.window_end:
            return False

        duration_text = (
            f"{event.duration_minutes} minutes"
            if event.duration_minutes is not None
            else "not specified"
        )
        prompt = (
            f"HT-SmartScheduler detected a start window:\n"
            f"{pretty_window(event.window_start, event.window_end)}\n\n"
            f"Duration: {duration_text}\n\n"
            "Enter the exact start time inside this window "
            "(for example 10:30 PM or 22:30).\n"
            "You can also enter NOW."
        )

        while True:
            answer = simpledialog.askstring(
                "Choose exact start time",
                prompt,
                parent=self.root,
            )
            if answer is None:
                return False

            value = answer.strip()
            if value.lower() == "now":
                chosen = current_wall_time(self.user_time_zone).replace(second=0, microsecond=0)
            else:
                try:
                    parsed = parse_time_override(value)
                except ValueError as exc:
                    messagebox.showerror("Start time", str(exc), parent=self.root)
                    continue
                candidate_dates = {event.window_start.date(), event.window_end.date()}
                possible = [
                    datetime.combine(day, parsed).replace(second=0, microsecond=0)
                    for day in candidate_dates
                ]
                possible = [
                    candidate
                    for candidate in possible
                    if event.window_start <= candidate <= event.window_end
                ]
                chosen = possible[0] if possible else None

            if chosen is None or not (event.window_start <= chosen <= event.window_end):
                messagebox.showerror(
                    "Start time",
                    "The selected time is outside the detected window.\n\n"
                    f"Choose a time between {pretty_window(event.window_start, event.window_end)}.",
                    parent=self.root,
                )
                continue

            event.start_at = chosen
            event.timing_kind = "exact"
            event.confidence_notes = None
            return True

    def _windows_quit(self):
        """Close only the Windows GUI; the reminder worker keeps running."""
        self.root.destroy()

    def _windows_service_status_refresh(self):
        """Refresh Windows worker status without spawning restart loops."""
        try:
            self.refresh_service_status()
        finally:
            try:
                self.root.after(5000, self._windows_service_status_refresh)
            except tk.TclError:
                pass

    def _reminder_service_watchdog(self):
        """Monitor the reminder daemon without creating a restart storm.

        Older builds retried a failed Windows daemon every five seconds. If the
        child could not stay alive, that produced an endless sequence of
        flashing console/PowerShell windows. This watchdog uses a cooldown and
        stops automatic retries after repeated failures. The user can still use
        the Start button to retry manually.
        """
        try:
            running, _pid = reminder_service_status()
            if running:
                self._service_restart_failures = 0
                self._service_next_restart_at = 0.0
            else:
                now = time_module.monotonic()
                failures = int(getattr(self, "_service_restart_failures", 0))
                next_restart = float(getattr(self, "_service_next_restart_at", 0.0))

                if failures < 2 and now >= next_restart:
                    try:
                        started, _pid = start_background_service(no_voice=False)
                        if started:


                            self._service_next_restart_at = now + 30.0
                        else:
                            self._service_next_restart_at = now + 30.0
                    except Exception:
                        self._service_restart_failures = failures + 1


                        self._service_next_restart_at = now + 60.0

            self.refresh_service_status()
        finally:
            self.root.after(5000, self._reminder_service_watchdog)

    def ensure_reminder_service(self):
        """Start exactly one reminder daemon, replacing legacy daemons first."""
        try:
            if not getattr(self, "_service_cleanup_done", False):
                stop_all_reminder_daemons()
                self._service_cleanup_done = True
            started, pid = start_background_service(no_voice=False)
        except Exception as exc:
            self.service_var.set(f"Reminder service: ERROR ({exc})")
            return

        self.refresh_service_status()
        if started:

            self._write_result(
                f"Reminder service started automatically (PID {pid}).\n"
                "Reminder service is active."
            )

    def _google_sync_changed(self):
        """Enable Google account controls only when the user opts in.

        Google Calendar is optional. When the box is unchecked, saving a local
        reminder never requires an email address, credentials file, or Google
        authorization.
        """
        enabled = bool(self.google_sync_var.get())
        state = "normal" if enabled else "disabled"

        for widget_name in (
            "google_email_entry",
            "google_connect_button",
            "google_disconnect_button",
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.configure(state=state)

        if hasattr(self, "google_status_var"):
            if enabled:
                self.refresh_google_status()
            else:
                self.google_status_var.set("Local only" if self._windows_ui else "Status: Optional — local HT-SmartScheduler only")

    def connect_google_calendar(self):
        try:
            email = validate_google_email(self.google_email_var.get())
            connected_email = self.google.connect(expected_email=email)
        except (ValueError, GoogleCalendarError) as exc:
            self.google_sync_var.set(False)
            messagebox.showerror("Google Calendar", str(exc))
        else:
            self.google_email = connected_email
            self.google_email_var.set(connected_email)
            self.db.set_setting("google_email", connected_email)
            self.google_sync_var.set(True)
            messagebox.showinfo(
                "Google Calendar",
                f"Connected to {connected_email}.\n\n"
                "Saved schedules can now be added to this account's Google Calendar.",
            )
        self.refresh_google_status()
        self._google_sync_changed()

    def disconnect_google_calendar(self):
        try:
            self.google.disconnect()
        except GoogleCalendarError as exc:
            messagebox.showerror("Google Calendar", str(exc))
            return
        self.google_sync_var.set(False)
        self.refresh_google_status()
        self._google_sync_changed()
        messagebox.showinfo(
            "Google Calendar",
            "Google Calendar disconnected. Local HT-SmartScheduler reminders are unchanged.",
        )

    def refresh_google_status(self):
        if hasattr(self, "google_sync_var") and not self.google_sync_var.get():
            self.google_status_var.set("Local only" if self._windows_ui else "Status: Optional — local HT-SmartScheduler only")
            return

        base = self.google.status_text()
        email = (getattr(self, "google_email_var", None).get().strip()
                 if getattr(self, "google_email_var", None) is not None
                 else self.google_email)
        if self.google.token_present() and email:
            self.google_status_var.set(f"Connected: {email}" if self._windows_ui else f"Status: Connected as {email}")
        else:
            self.google_status_var.set(base if self._windows_ui else "Status: " + base)

    def save_schedule(self):
        note = self.note_text.get("1.0", "end").strip()
        if not note:
            messagebox.showwarning("Missing note", "Enter a schedule note first.")
            return

        try:
            reminder_minutes = self.get_reminder_minutes()
            reminder_mode = self.get_reminder_mode()
            duration_override = self.get_duration_override()
            recurrence_rule = self.get_recurrence_rule()

            parse_date_override(self.date_override_var.get())
            parse_time_override(self.time_override_var.get())
            time_zone = self._save_time_zone(self.time_zone_var.get())
            google_email = None
            if self.google_sync_var.get():
                google_email = validate_google_email(self.google_email_var.get())
                if not self.google.credentials_present():
                    raise ValueError(
                        "Google Calendar is not configured yet. Add google_credentials.json "
                        "or turn off Google Calendar sync."
                    )
                if not self.google.token_present():
                    raise ValueError(
                        "Connect / Verify Google Calendar before saving with Google sync enabled."
                    )
                self.google_email = google_email
                self.db.set_setting("google_email", google_email)
        except ValueError as exc:
            messagebox.showerror("Schedule details", str(exc))
            return

        base_now = current_wall_time(time_zone)
        candidates = extract_events(note, base=base_now)
        if not candidates:
            self._write_result("No schedule items were found.")
            return

        lines: list[str] = []
        saved = 0
        unsaved_source_texts: list[str] = []
        location = self.location_var.get().strip()

        for index, event in enumerate(candidates, start=1):
            lines.append(f"ITEM {index}: {event.duty}")

            try:
                apply_datetime_overrides(
                    event,
                    self.date_override_var.get(),
                    self.time_override_var.get(),
                )
            except ValueError as exc:
                lines.append(f"  Not saved: {exc}")
                unsaved_source_texts.append(event.source_text)
                continue

            if duration_override is not None:
                event.duration_minutes = duration_override

            selected_type = self.event_type_var.get()
            if selected_type != "Auto detect":
                event.event_type = selected_type

            if not candidate_is_complete(event):
                if event.timing_kind == "window" and event.window_start and event.window_end:
                    lines.append(f"  Detected start window: {pretty_window(event.window_start, event.window_end)}")
                    if event.duration_minutes is not None:
                        lines.append(f"  Detected duration: {event.duration_minutes} minutes")
                    if self._ask_for_exact_time_in_window(event):
                        lines.append(f"  Exact start selected: {pretty_datetime(event.start_at)}")
                    else:
                        lines.append("  Not saved: an exact start time is required for reminders.")
                        unsaved_source_texts.append(event.source_text)
                        continue
                else:
                    lines.append(
                        f"  Not saved: {event.confidence_notes or 'missing exact date/time'}"
                    )
                    unsaved_source_texts.append(event.source_text)
                    continue

            end_at = event_end(event)
            conflicts = self.db.find_conflicts(event.start_at, end_at)

            event_id = self.db.add_event(
                title=event.duty,
                start_at=event.start_at,
                end_at=end_at,
                reminder_minutes_list=reminder_minutes,
                event_type=event.event_type,
                source_text=event.source_text,
                recurrence_rule=recurrence_rule,
                location=location,
                google_sync_status=("pending" if self.google_sync_var.get() else "local only"),
                reminder_mode=reminder_mode,
            )

            saved += 1
            lines.append(f"  Saved locally as event #{event_id}")
            lines.append(f"  Starts: {pretty_datetime(event.start_at)}")
            lines.append(f"  Repeat: {recurrence_label(recurrence_rule)}")

            if reminder_minutes:
                reminder_text = ", ".join(format_reminder_minutes(value) for value in reminder_minutes)
                lines.append(f"  Reminders: {reminder_text} before each occurrence")
                lines.append(f"  Reminder method: {self.reminder_mode_label(reminder_mode)}")
            else:
                lines.append("  Reminders: none")

            if location:
                lines.append(f"  Location: {location}")

            if conflicts:
                lines.append(f"  Conflict warning: overlaps {len(conflicts)} existing event(s)")

            if self.google_sync_var.get():
                try:
                    google_event = self.google.create_event(
                        title=event.duty,
                        start_at=event.start_at,
                        end_at=end_at,
                        source_text=event.source_text,
                        location=location,
                        reminder_minutes=reminder_minutes,
                        recurrence_rule=recurrence_rule,
                        time_zone=time_zone,
                        interactive_auth=False,
                        expected_email=google_email,
                    )
                    google_id = google_event.get("id")
                    self.db.set_google_sync(event_id, google_id, "synced")
                    lines.append(f"  Google Calendar: added to {google_email}")
                except GoogleCalendarError as exc:
                    self.db.set_google_sync(event_id, None, "error")
                    lines.append(f"  Google Calendar: not synced — {exc}")

        events = self.db.list_events()
        if events:
            export_ics(events, ICS_PATH)

        if saved:
            check_reminders(
                self.db,
                now=current_wall_time(time_zone),
                speak_enabled=True,
                notifications_enabled=True,
                popup_parent=self.root if self._windows_ui else None,
            )
            started, pid = start_background_service(no_voice=False)
            if started:
                lines.append(f"\nReminder service started automatically (PID {pid}).")
            else:
                lines.append(f"\nReminder service is already running (PID {pid}).")
            lines.append("Reminder service is active and will use each schedule's selected reminder method.")





            self.note_text.delete("1.0", "end")
            if unsaved_source_texts:
                self.note_text.insert("1.0", "\n".join(unsaved_source_texts))
                lines.append(
                    "Saved item(s) were removed from the input. "
                    "Unresolved item(s) were kept so you can correct them."
                )
            else:
                lines.append("Input cleared after save. Ready for a new reminder.")
            self.note_text.focus_set()

        self._write_result("\n".join(lines))
        self.refresh_events()
        self.refresh_service_status()
        self.refresh_google_status()

    def _on_tab_changed(self, _event=None):
        if hasattr(self, "events_tree"):
            self.refresh_events()

    def _periodic_refresh_events(self):
        """Remove expired rows from Upcoming Events while the GUI stays open."""
        try:
            if self.root.winfo_exists():
                self.refresh_events()
                self.root.after(5000, self._periodic_refresh_events)
        except tk.TclError:

            return

    def refresh_events(self):
        if not hasattr(self, "events_tree"):
            return
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)

        time_zone = self.db.get_setting("time_zone") or self.user_time_zone
        now = current_wall_time(time_zone)
        visible_events = []
        for event in self.db.list_events():
            first_start = datetime.fromisoformat(event["start_at"])
            next_start = next_occurrence_on_or_after(
                first_start,
                event.get("recurrence_rule"),
                now,
            )
            if next_start is None:


                continue
            visible_events.append((next_start, event))



        visible_events.sort(key=lambda pair: pair[0])

        for next_start, event in visible_events:
            reminders = event.get("reminder_minutes_list", [])
            reminder_text = ", ".join(format_reminder_minutes(value) for value in reminders) or "none"
            google_status = event.get("google_sync_status") or "local only"

            self.events_tree.insert(
                "",
                "end",
                iid=str(event["id"]),
                values=(
                    event["title"],
                    next_start.strftime("%a %b %d, %Y %I:%M %p"),
                    recurrence_label(event.get("recurrence_rule")),
                    reminder_text,
                    self.reminder_mode_label(event.get("reminder_mode") or "both"),
                    google_status,
                ),
            )

    def delete_selected_event(self):
        """Cancel the selected upcoming event and stop all future reminders.

        The database keeps a cancelled record for future History/Restore support,
        but the event disappears from Upcoming Events immediately.  If the event
        was synced to Google Calendar, the user can choose whether to remove the
        Google copy as well.
        """
        if not hasattr(self, "events_tree"):
            return

        selected = self.events_tree.selection()
        if not selected:
            messagebox.showinfo(
                "Delete event",
                "Select an event in Upcoming Events first.",
            )
            return

        try:
            event_id = int(selected[0])
        except (TypeError, ValueError):
            messagebox.showerror("Delete event", "Could not identify the selected event.")
            return

        event = self.db.get_event(event_id)
        if not event:
            messagebox.showinfo("Delete event", "That event no longer exists.")
            self.refresh_events()
            return

        title = event.get("title") or "this event"
        google_event_id = (event.get("google_event_id") or "").strip()
        delete_google = False

        if google_event_id:
            choice = messagebox.askyesnocancel(
                "Delete event",
                f'Delete "{title}"?\n\n'
                "Yes: remove it from HT-SmartScheduler and Google Calendar.\n"
                "No: remove it only from HT-SmartScheduler.\n"
                "Cancel: keep the event.",
            )
            if choice is None:
                return
            delete_google = bool(choice)
        else:
            if not messagebox.askyesno(
                "Delete event",
                f'Delete "{title}"?\n\n'
                "This will stop all future popup/voice reminders for this schedule.\n"
                "Recurring schedules will be cancelled completely.",
            ):
                return

        google_note = ""
        if delete_google:
            try:
                expected_email = self.db.get_setting("google_email") or None
                self.google.delete_event(
                    google_event_id,
                    interactive_auth=False,
                    expected_email=expected_email,
                )
                google_note = "\nGoogle Calendar: deleted"
            except GoogleCalendarError as exc:
                remove_local = messagebox.askyesno(
                    "Google Calendar",
                    "HT-SmartScheduler could not delete the Google Calendar copy:\n\n"
                    f"{exc}\n\n"
                    "Delete the local HT-SmartScheduler event anyway?",
                )
                if not remove_local:
                    return
                google_note = "\nGoogle Calendar: could not delete; Google copy may remain"

        if self.db.cancel_event(event_id):
            self._write_result(
                f'Deleted: {title}\n'
                "Future HT-SmartScheduler reminders for this event have been stopped."
                f"{google_note}"
            )
        else:
            self._write_result(f'Event was already removed: {title}')

        self.refresh_events()

    def refresh_service_status(self):
        running, pid = reminder_service_status()
        if running:
            label = "Service" if self._windows_ui else "Reminder service"
            self.service_var.set(f"{label}: RUNNING (PID {pid})")
        else:
            label = "Service" if self._windows_ui else "Reminder service"
            self.service_var.set(f"{label}: STOPPED")

    def start_service(self):
        self._service_restart_failures = 0
        self._service_next_restart_at = 0.0
        started, pid = start_background_service(no_voice=False)
        if started:
            messagebox.showinfo("Reminder service", f"Reminder service started (PID {pid}).")
        else:
            messagebox.showinfo("Reminder service", f"Reminder service is already running (PID {pid}).")
        self.refresh_service_status()

    def stop_service(self):
        stopped, pid = stop_background_service()
        if stopped:
            messagebox.showinfo("Reminder service", f"Reminder service stopped (PID {pid}).")
        else:
            messagebox.showinfo("Reminder service", "Reminder service is not running.")
        self.refresh_service_status()

    def test_reminder(self):
        try:
            mode = self.get_reminder_mode()
        except ValueError as exc:
            messagebox.showerror("Reminder method", str(exc))
            return

        popup_enabled = mode in {"both", "popup"}
        voice_enabled = mode in {"both", "voice"}
        message = "HT-SmartScheduler reminder test."

        popup = show_popup(
            message,
            title="HT-SmartScheduler Test",
            enabled=popup_enabled,
            timeout_seconds=20,
            parent=self.root if self._windows_ui else None,
        )
        if self._windows_ui and voice_enabled:
            voice_ok = speak_async(message, enabled=True)
        else:
            voice_ok = speak(message, enabled=voice_enabled)

        details = [
            "Test reminder sent.",
            f"Reminder method: {self.reminder_mode_label(mode)}",
        ]
        if popup_enabled:
            details.append(f"Popup: {'opened' if popup else 'not confirmed'}")
        else:
            details.append("Popup: disabled for this reminder method")

        if voice_enabled:
            details.append(f"Voice: {'played' if voice_ok else 'not confirmed'}")
        else:
            details.append("Voice: disabled for this reminder method")

        details.append(
            "If a real scheduled reminder does not appear, check "
            f"{LOG_PATH} for the daemon result."
        )
        self._write_result("\n".join(details))


def launch_app():
    root = tk.Tk()
    SmartSchedulerApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_app()
