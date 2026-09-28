# HT-SmartScheduler
**Describe it. Schedule it. Don’t miss it.**

HT-SmartScheduler is a cross-platform desktop reminder assistant for **macOS and Windows**. It turns natural-language requests into schedules and can remind you with a large popup, spoken voice, or both.
## Download

### [⬇️ Download HT-SmartScheduler](https://github.com/ELLYLY2015/HT-SmartScheduler/raw/refs/heads/main/HT-SmartScheduler.zip)

## What it can do

- Understand natural-language scheduling such as `Doctor tomorrow at 2 PM`, `Meeting in the next 15 minutes`, or `Golf next weekend at 9 AM`
- Popup reminders, voice reminders, or Popup + Voice
- Multiple reminder times
- Recurring schedules
- Automatic time-zone detection
- Upcoming Events with refresh and delete controls
- Optional Google Calendar integration
- NLP / machine-learning support combined with deterministic date/time validation

## Platform behavior

HT-SmartScheduler uses one shared codebase and automatically detects the operating system.

- **macOS:** uses the proven Mac layout and detached reminder service.
- **Windows:** uses the tuned 1000×650 layout and a dedicated hidden reminder worker. Closing the main HT-SmartScheduler window does **not** stop scheduled reminders; the worker continues in the background while the computer is awake.

## Build on macOS

```bash
bash build_mac_installer.sh
```

The DMG is created in `release/`.

## Build on Windows

```powershell
.\build_windows.bat
```

The Windows build creates two files in `dist`:

```text
dist\HT-SmartScheduler.exe
dist\HT-SmartScheduler-Reminder.exe
```

Keep both files together. Users open only `HT-SmartScheduler.exe`; the reminder worker runs silently in the background.

If you use `build_windows_installer.bat`, both EXE files are copied into the `release` folder.

## End users

End users do **not** need Python or pip. Python/PyInstaller are only required on the computer used to build the application.

## Important reminder behavior

- Reminders continue after the main Windows app window is closed.
- The computer still needs to be awake for popup/voice delivery.
- The **Stop** button stops the background reminder worker.
- Opening HT-SmartScheduler again starts/refreshes the reminder worker automatically.

## Windows background reminder note 

The Windows reminder helper is launched as an independent detached process. This prevents closing the main HT-SmartScheduler window from terminating the reminder worker on Windows systems that place child applications in a process job. The helper publishes its own PID and heartbeat so service status reflects the actual reminder process.
