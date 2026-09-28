# Platform Build Notes

HT-SmartScheduler uses one shared codebase with platform-specific behavior selected automatically at runtime.

- **macOS:** keeps the proven detached reminder service and Mac UI sizing.
- **Windows:** keeps the tuned 1000×650 UI and uses a dedicated hidden `HT-SmartScheduler-Reminder.exe` worker. The worker stays running after the main window closes, so scheduled popup/voice reminders can still fire while the computer is awake.
- The Windows worker is built with `--windowed`, so it does not open PowerShell/console windows.
- `HT-SmartScheduler.exe` and `HT-SmartScheduler-Reminder.exe` must remain together in the same installed folder.
- Changes intended for one platform should remain behind the existing platform checks.
