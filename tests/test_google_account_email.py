import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from app import validate_google_email
from google_calendar import GoogleCalendarClient, GoogleCalendarError


class GoogleEmailValidationTests(unittest.TestCase):
    def test_accepts_gmail(self):
        self.assertEqual(validate_google_email(" user@gmail.com "), "user@gmail.com")

    def test_accepts_non_gmail_google_account(self):
        self.assertEqual(validate_google_email("person@example.org"), "person@example.org")

    def test_rejects_blank(self):
        with self.assertRaises(ValueError):
            validate_google_email("")

    def test_rejects_malformed(self):
        with self.assertRaises(ValueError):
            validate_google_email("not-an-email")


class GoogleAccountMatchTests(unittest.TestCase):
    def test_wrong_authorized_account_removes_token_and_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            token = Path(temp) / "token.json"
            token.write_text("{}", encoding="utf-8")
            client = GoogleCalendarClient(
                credentials_path=Path(temp) / "credentials.json",
                token_path=token,
            )
            client._account_email_from_credentials = Mock(return_value="other@gmail.com")

            with self.assertRaises(GoogleCalendarError):
                client._verify_expected_email(object(), "wanted@gmail.com")

            self.assertFalse(token.exists())

    def test_matching_authorized_account_is_returned(self):
        with tempfile.TemporaryDirectory() as temp:
            client = GoogleCalendarClient(
                credentials_path=Path(temp) / "credentials.json",
                token_path=Path(temp) / "token.json",
            )
            client._account_email_from_credentials = Mock(return_value="User@Gmail.com")
            actual = client._verify_expected_email(object(), "user@gmail.com")
            self.assertEqual(actual, "User@Gmail.com")


class GoogleDeleteEventTests(unittest.TestCase):
    def test_delete_event_uses_primary_calendar(self):
        client = GoogleCalendarClient()
        execute = Mock()
        delete = Mock(return_value=Mock(execute=execute))
        events = Mock(return_value=Mock(delete=delete))
        service = Mock(events=events)
        client.service = Mock(return_value=service)

        client.delete_event("google-event-123", expected_email="user@gmail.com")

        client.service.assert_called_once_with(
            interactive=False,
            expected_email="user@gmail.com",
        )
        delete.assert_called_once_with(
            calendarId="primary",
            eventId="google-event-123",
        )
        execute.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
