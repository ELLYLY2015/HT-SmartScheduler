# HT-SmartScheduler Windows v11.6.3 — Packaging

Run `build_windows.bat` on a Windows development machine.

The build creates:

```text
dist\HT-SmartScheduler.exe
dist\HT-SmartScheduler-Reminder.exe
```

Both files are required and should be installed into the same folder. End users launch only `HT-SmartScheduler.exe`. The second EXE is the hidden background reminder worker that lets popup/voice reminders continue after the GUI closes.

End users do not need Python or pip.

For a public installer, package both EXE files together using Inno Setup, MSIX, or another Windows installer and create the Start Menu/Desktop shortcut only for `HT-SmartScheduler.exe`.
