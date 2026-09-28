# HT-SmartScheduler v11.2.6 — Normal desktop app packaging

The end-user app does **not** install Python packages when it opens. The build
process bundles Python and the libraries into the application.

## macOS developer build

Double-click `build_mac.command` (or run `./build_mac.command` once). The output is:

`dist/HT-SmartScheduler.app`

Give users the `.app` (normally distributed in a DMG/ZIP after code signing).
They double-click it like a normal Mac application. They do not need Python,
Terminal, pip, or the source folder.

## Windows developer build

Run `build_windows.bat` on a Windows machine. The output is:

`dist\HT-SmartScheduler.exe`

The EXE contains the Python runtime and application dependencies. End users can
double-click it without installing Python or packages.

## User data

Packaged builds store writable data outside the application:

- macOS: `~/Library/Application Support/HT-SmartScheduler/`
- Windows: `%APPDATA%\HT-SmartScheduler\`

This includes the SQLite database, reminder log/PID, Google authorization token,
and exported ICS calendar. Updating/replacing the app therefore does not erase
user schedules.

## Google Calendar

Google Calendar remains optional. For a production build, place the developer
OAuth desktop client file at `data/google_credentials.json` **before building**.
The build script bundles it. User OAuth tokens are always written to the user's
application-data directory, never inside the application bundle.

## Important distribution note

PyInstaller creates a runnable app, but public distribution should also be code
signed. macOS distribution normally also uses Apple notarization. Windows
benefits from Authenticode signing. Signing is a release/distribution step and
is separate from bundling Python dependencies.
