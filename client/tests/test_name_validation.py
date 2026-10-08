import unittest

from shared import name_validation
from shared.name_validation import normalize_base_name

EMPTY = "Name cannot be empty."
INVALID = "Name contains invalid characters."
TRAILING = "Name cannot end with a period or space."
TOO_LONG = "Name cannot exceed 32 characters."


class NormalizeBaseNameTest(unittest.TestCase):
    def assert_rejected(self, name: str, message: str, **kwargs) -> ValueError:
        with self.assertRaises(ValueError) as caught:
            normalize_base_name(name, **kwargs)
        self.assertEqual(str(caught.exception), message)
        return caught.exception

    def test_returns_the_stripped_name(self) -> None:
        cases = (
            ("name", "name"),
            (" name", "name"),
            ("name　", "name"),
            ("　name", "name"),
            ("\xa0x", "x"),
            ("\x85a", "a"),
            ("1.1", "1.1"),
            ("x\x7f", "x\x7f"),
            ("a" * 32, "a" * 32),
            (" " + "a" * 32, "a" * 32),
            ("default", "default"),
        )
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(normalize_base_name(name), expected)

    def test_rejects_empty_names(self) -> None:
        for name in ("", " ", "　", "\t", " \t "):
            with self.subTest(name=name):
                self.assert_rejected(name, EMPTY)

    def test_rejects_control_characters(self) -> None:
        for name in ("a\tb", "\x00", "a\x1f", "a\t."):
            with self.subTest(name=name):
                self.assert_rejected(name, INVALID)

    def test_rejects_a_trailing_period_or_space_on_the_raw_name(self) -> None:
        for name in ("name.", "name ", " name ", ".", "..", "a" * 40 + ".", "a" * 33 + " "):
            with self.subTest(name=name):
                self.assert_rejected(name, TRAILING)

    def test_rejects_names_longer_than_32_characters_after_stripping(self) -> None:
        for name in ("a" * 33, "　" + "a" * 33, "?" * 33):
            with self.subTest(name=name):
                self.assert_rejected(name, TOO_LONG)

    def test_rejects_names_that_are_not_legal_windows_file_names(self) -> None:
        for name in ("a?b", "a<b", "CON", "con.txt", "COM1", "LPT9.a", "nul.tar.gz", "　..　", "name.　"):
            with self.subTest(name=name):
                self.assert_rejected(name, INVALID)

    def test_rejects_reserved_names_case_insensitively_with_the_stripped_name(self) -> None:
        cases = (
            ("default", {"default"}, "Name 'default' is reserved."),
            ("Default", {"default"}, "Name 'Default' is reserved."),
            (" DEFAULT", {"Default"}, "Name 'DEFAULT' is reserved."),
            ("default　", {"default"}, "Name 'default' is reserved."),
        )
        for name, reserved, message in cases:
            with self.subTest(name=name):
                self.assert_rejected(name, message, reserved_names=reserved)

    def test_windows_check_runs_before_the_reserved_check(self) -> None:
        self.assert_rejected("CON", INVALID, reserved_names={"con"})

    def test_errors_are_value_errors_with_the_message_as_only_argument(self) -> None:
        cases = (
            ("", EMPTY),
            ("a\tb", INVALID),
            ("name.", TRAILING),
            ("a" * 33, TOO_LONG),
            ("CON", INVALID),
        )
        for name, message in cases:
            with self.subTest(name=name):
                error = self.assert_rejected(name, message)
                self.assertIsInstance(error, ValueError)
                self.assertEqual(error.args, (message,))


class NameValidationErrorTest(unittest.TestCase):
    def test_each_check_raises_a_name_validation_error_with_its_code(self) -> None:
        cases = (
            ("", "empty", EMPTY),
            (" \t ", "empty", EMPTY),
            ("a\tb", "invalid", INVALID),
            ("name.", "invalid", TRAILING),
            ("name ", "invalid", TRAILING),
            ("a" * 33, "too_long", TOO_LONG),
            ("a?b", "invalid", INVALID),
            ("CON", "invalid", INVALID),
            ("\u3000..\u3000", "invalid", INVALID),
            (" Default", "reserved", "Name 'Default' is reserved."),
        )
        for name, code, message in cases:
            with self.subTest(name=name):
                with self.assertRaises(name_validation.NameValidationError) as caught:
                    normalize_base_name(name, reserved_names={"default"})
                self.assertIs(type(caught.exception), name_validation.NameValidationError)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(str(caught.exception), message)
                self.assertEqual(caught.exception.args, (message,))

    def test_name_validation_error_is_a_value_error_that_keeps_its_message(self) -> None:
        error = name_validation.NameValidationError("too_long", "Name cannot exceed 32 characters.")

        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, "too_long")
        self.assertEqual(error.args, ("Name cannot exceed 32 characters.",))
        self.assertEqual(str(error), "Name cannot exceed 32 characters.")


if __name__ == "__main__":
    unittest.main()
