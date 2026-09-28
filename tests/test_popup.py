import unittest

from voice import show_popup


class PopupTests(unittest.TestCase):
    def test_popup_can_be_disabled(self):
        self.assertFalse(
            show_popup(
                "test",
                enabled=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
