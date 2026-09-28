import unittest
from pathlib import Path

import main


class V11CliTests(unittest.TestCase):
    def test_version_is_11(self):
        self.assertEqual(main.VERSION, "11.6.3")

    def test_root_is_absolute(self):
        self.assertTrue(main.ROOT.is_absolute())

    def test_parser_accepts_v11_reminder_flags(self):
        parser = main.build_parser()

        self.assertTrue(parser.parse_args(["--reminders"]).reminders)
        self.assertTrue(
            parser.parse_args(["--check-reminders"]).check_reminders
        )
        self.assertTrue(
            parser.parse_args(["--reminders-start"]).reminders_start
        )
        self.assertTrue(
            parser.parse_args(["--reminders-stop"]).reminders_stop
        )
        self.assertTrue(
            parser.parse_args(["--reminders-status"]).reminders_status
        )
        self.assertTrue(
            parser.parse_args(["--test-notification"]).test_notification
        )
        self.assertTrue(
            parser.parse_args(["--app"]).app
        )


if __name__ == "__main__":
    unittest.main()
