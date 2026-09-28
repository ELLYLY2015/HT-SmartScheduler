from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk


DEFAULT_POPUP_WIDTH = 900
DEFAULT_POPUP_HEIGHT = 450


def preferred_popup_geometry(screen_width: int, screen_height: int) -> tuple[int, int, int, int]:
    """Return a large centered reminder-popup geometry that still fits the screen."""
    screen_width = max(1, int(screen_width))
    screen_height = max(1, int(screen_height))

    width = min(DEFAULT_POPUP_WIDTH, max(320, int(screen_width * 0.88)))
    height = min(DEFAULT_POPUP_HEIGHT, max(220, int(screen_height * 0.72)))
    width = min(width, screen_width)
    height = min(height, screen_height)
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    return width, height, x, y


def _populate_popup(window: tk.Misc, title: str, text: str, timeout_seconds: int) -> None:
    window.title(title)
    window.configure(bg="#F4F8FE")

    width, height, x, y = preferred_popup_geometry(
        window.winfo_screenwidth(), window.winfo_screenheight()
    )
    window.geometry(f"{width}x{height}+{x}+{y}")
    window.minsize(min(620, width), min(300, height))

    try:
        window.attributes("-topmost", True)
    except tk.TclError:
        pass

    outer = tk.Frame(window, bg="#F4F8FE", padx=38, pady=30)
    outer.pack(fill="both", expand=True)

    tk.Label(
        outer,
        text="HT-SmartScheduler Reminder",
        bg="#F4F8FE",
        fg="#12325A",
        font=("Helvetica", 25, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 22))

    message = tk.Label(
        outer,
        text=text,
        bg="white",
        fg="#102A4C",
        font=("Helvetica", 21, "normal"),
        justify="left",
        anchor="nw",
        wraplength=max(360, width - 110),
        padx=26,
        pady=26,
        relief="solid",
        borderwidth=1,
    )
    message.pack(fill="both", expand=True)

    button_row = tk.Frame(outer, bg="#F4F8FE")
    button_row.pack(fill="x", pady=(22, 0))

    ok_button = ttk.Button(button_row, text="OK", command=window.destroy)
    ok_button.pack(side="right", ipadx=28, ipady=8)
    ok_button.focus_set()

    window.bind("<Return>", lambda _event: window.destroy())
    window.bind("<Escape>", lambda _event: window.destroy())

    timeout_seconds = max(1, int(timeout_seconds))
    window.after(timeout_seconds * 1000, window.destroy)
    window.after(150, lambda: (window.lift(), window.focus_force()))


def open_large_popup(parent: tk.Misc, title: str, text: str, timeout_seconds: int = 20) -> tk.Toplevel:
    """Open a non-blocking popup inside the already-running GUI process.

    This is the preferred Windows path: it avoids spawning the packaged EXE
    again just to show a reminder window.
    """
    popup = tk.Toplevel(parent)
    _populate_popup(popup, title, text, timeout_seconds)
    return popup


def show_large_popup(
    title: str,
    text: str,
    timeout_seconds: int = 20,
    ready_file: str | None = None,
) -> int:
    """Show a standalone large reminder dialog.

    On Windows the background reminder worker may supply ``ready_file``.  The
    popup writes that marker only after Tk has mapped and painted the window,
    allowing voice playback to begin at the same visible moment.
    """
    root = tk.Tk()
    _populate_popup(root, title, text, timeout_seconds)
    try:
        root.update_idletasks()
        root.update()
        root.lift()
    except tk.TclError:
        pass

    if ready_file:
        try:
            Path(ready_file).write_text("ready", encoding="utf-8")
        except OSError:
            pass

    root.mainloop()
    return 0
