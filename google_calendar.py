from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


from runtime_paths import DATA_DIR, TOKEN_PATH, google_credentials_path

ROOT = Path(__file__).resolve().parent
DEFAULT_CREDENTIALS_PATH = google_credentials_path()
DEFAULT_TOKEN_PATH = TOKEN_PATH





SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/calendar.events",
]
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleCalendarError(RuntimeError):
    pass


class GoogleCalendarClient:
    def __init__(
        self,
        credentials_path: str | Path = DEFAULT_CREDENTIALS_PATH,
        token_path: str | Path = DEFAULT_TOKEN_PATH,
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)

    def credentials_present(self) -> bool:
        return self.credentials_path.exists()

    def token_present(self) -> bool:
        return self.token_path.exists()

    def status_text(self) -> str:
        if not self.credentials_present():
            return "Not configured (google_credentials.json is missing)"
        if not self.token_present():
            return "Ready to connect"
        return "Connected / token saved"

    @staticmethod
    def _imports():
        try:
            from google.auth.transport.requests import AuthorizedSession, Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise GoogleCalendarError(
                "Google Calendar libraries are not installed. Run: "
                "python3 -m pip install -r requirements.txt"
            ) from exc
        return AuthorizedSession, Request, Credentials, InstalledAppFlow, build

    def _credentials(self, interactive: bool = True):
        AuthorizedSession, Request, Credentials, InstalledAppFlow, _build = self._imports()
        del AuthorizedSession
        creds = None

        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path),
                    SCOPES,
                )


                if hasattr(creds, "has_scopes") and not creds.has_scopes(SCOPES):
                    creds = None
            except Exception:
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                raise GoogleCalendarError(
                    f"Could not refresh Google Calendar authorization: {exc}"
                ) from exc

        if not creds or not creds.valid:
            if not interactive:
                raise GoogleCalendarError("Google Calendar is not connected yet.")
            if not self.credentials_path.exists():
                raise GoogleCalendarError(
                    "Google Calendar credentials are missing. Download a Desktop app "
                    "OAuth client JSON from Google Cloud and save it as "
                    f"{self.credentials_path.name} inside the data folder."
                )

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    SCOPES,
                )
                creds = flow.run_local_server(port=0)
            except Exception as exc:
                raise GoogleCalendarError(
                    f"Google Calendar authorization failed: {exc}"
                ) from exc

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds

    def _account_email_from_credentials(self, creds) -> str:
        AuthorizedSession, _Request, _Credentials, _InstalledAppFlow, _build = self._imports()
        try:
            response = AuthorizedSession(creds).get(USERINFO_URL, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise GoogleCalendarError(
                f"Could not verify the connected Google account email: {exc}"
            ) from exc

        email = str(payload.get("email") or "").strip()
        if not email:
            raise GoogleCalendarError(
                "Google authorization succeeded, but the account email could not be verified."
            )
        return email

    def connected_email(self, interactive: bool = False) -> str:
        creds = self._credentials(interactive=interactive)
        return self._account_email_from_credentials(creds)

    def _verify_expected_email(self, creds, expected_email: str | None) -> str:
        actual = self._account_email_from_credentials(creds)
        expected = (expected_email or "").strip().lower()
        if expected and actual.lower() != expected:


            try:
                self.token_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise GoogleCalendarError(
                "The Google account you authorized does not match the email entered in "
                f"HT-SmartScheduler. Entered: {expected_email}. Authorized: {actual}. "
                "Connect again and choose the same Google account."
            )
        return actual

    def connect(self, expected_email: str | None = None) -> str:
        creds = self._credentials(interactive=True)
        return self._verify_expected_email(creds, expected_email)

    def disconnect(self):
        try:
            self.token_path.unlink(missing_ok=True)
        except Exception as exc:
            raise GoogleCalendarError(f"Could not disconnect Google Calendar: {exc}") from exc

    def service(self, interactive: bool = True, expected_email: str | None = None):
        _AuthorizedSession, _Request, _Credentials, _InstalledAppFlow, build = self._imports()
        creds = self._credentials(interactive=interactive)
        if expected_email:
            self._verify_expected_email(creds, expected_email)
        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    def create_event(
        self,
        *,
        title: str,
        start_at: datetime,
        end_at: datetime,
        source_text: str = "",
        location: str = "",
        reminder_minutes: list[int] | None = None,
        recurrence_rule: str | None = None,
        time_zone: str = "America/Los_Angeles",
        interactive_auth: bool = True,
        expected_email: str | None = None,
    ) -> dict[str, Any]:
        try:
            ZoneInfo(time_zone)
        except ZoneInfoNotFoundError as exc:
            raise GoogleCalendarError(
                f"Unknown calendar time zone: {time_zone}. Use an IANA name such as America/Los_Angeles."
            ) from exc

        service = self.service(
            interactive=interactive_auth,
            expected_email=expected_email,
        )

        body: dict[str, Any] = {
            "summary": title,
            "description": source_text or "Created by HT-SmartScheduler",
            "start": {
                "dateTime": start_at.isoformat(),
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": end_at.isoformat(),
                "timeZone": time_zone,
            },
        }

        if location.strip():
            body["location"] = location.strip()

        if recurrence_rule:
            body["recurrence"] = [recurrence_rule]

        reminders = sorted({int(x) for x in (reminder_minutes or []) if int(x) >= 0})
        if reminders:
            body["reminders"] = {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": minutes}
                    for minutes in reminders[:5]
                ],
            }
        else:
            body["reminders"] = {"useDefault": False, "overrides": []}

        try:
            return service.events().insert(
                calendarId="primary",
                body=body,
            ).execute()
        except Exception as exc:
            raise GoogleCalendarError(f"Could not create Google Calendar event: {exc}") from exc

    def delete_event(
        self,
        event_id: str,
        *,
        interactive_auth: bool = False,
        expected_email: str | None = None,
    ) -> None:
        """Delete an event from the authorized user's primary Google Calendar."""
        event_id = (event_id or "").strip()
        if not event_id:
            raise GoogleCalendarError("Google Calendar event ID is missing.")

        service = self.service(
            interactive=interactive_auth,
            expected_email=expected_email,
        )
        try:
            service.events().delete(
                calendarId="primary",
                eventId=event_id,
            ).execute()
        except Exception as exc:
            raise GoogleCalendarError(f"Could not delete Google Calendar event: {exc}") from exc

