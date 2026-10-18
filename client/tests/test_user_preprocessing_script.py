import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.preprocessing import user_script
from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    execute_script,
    read_script_source,
    save_script,
    validate_script,
)
from tests.full_disk import full_disk
from tests.windows_file_handles import make_read_only

# The msgids of the signature rule (F-18 D5).
ONE_MAIN = "The script must define exactly one top-level synchronous main function."
ONE_PARAMETER = "main must define exactly one positional parameter and no other parameters."
PARAMETER_ANNOTATION = "The parameter of main must be annotated as str, or not annotated."
RETURN_ANNOTATION = "The return value of main must be annotated as str, or not annotated."


class UserPreprocessingScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = self.directory / "upper.py"

    def test_the_single_script_next_to_the_dictionaries_is_gone(self) -> None:
        # F-18 (D-A): dictionary/preprocessing.py is not read, so nothing names it any more.
        for name in (
            "PREPROCESSING_FILENAME",
            "DEFAULT_PREPROCESSING_SCRIPT",
            "preprocessing_script_path",
            "load_preprocessing_script",
            "save_preprocessing_script",
            "execute_preprocessing_script",
            "validate_preprocessing_script",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(user_script, name))

    def test_no_processing_is_the_identity_script_of_the_spec(self) -> None:
        # F-18 (D-D): the text the user gave, also the template of a new script.
        self.assertEqual(NO_PROCESSING_SCRIPT_NAME, "no-processing")
        self.assertEqual(NO_PROCESSING_SCRIPT, "def main(input: str) -> str:\n    return input\n")
        self.assertEqual(SCRIPT_SUFFIX, ".py")
        validate_script(NO_PROCESSING_SCRIPT)

    def test_validation_accepts_helpers_imports_and_any_parameter_name(self) -> None:
        source = "import re\n\ndef clean(value):\n    return re.sub(' +', ' ', value)\n\ndef main(text):\n    return clean(text)\n"
        validate_script(source)

    def test_validation_rejects_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            validate_script("def main(:\n")

    def test_validation_does_not_execute_valid_module_code(self) -> None:
        validate_script(
            "raise RuntimeError('must not run while saving')\n"
            "def main(text):\n    return text\n"
        )

    def test_validation_requires_exactly_one_top_level_sync_main(self) -> None:
        invalid_sources = (
            "def helper(text):\n    return text\n",
            "async def main(text):\n    return text\n",
            "def main(text):\n    return text\n\ndef main(other):\n    return other\n",
            "def outer():\n    def main(text):\n        return text\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), ONE_MAIN)

    def test_validation_requires_one_positional_parameter_and_no_others(self) -> None:
        invalid_sources = (
            "def main():\n    return ''\n",
            "def main(first, second):\n    return first\n",
            "def main(text, *, option=False):\n    return text\n",
            "def main(*args):\n    return args[0]\n",
            "def main(text, **kwargs):\n    return text\n",
        )
        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), ONE_PARAMETER)

    def test_annotations_are_optional_and_str_when_present(self) -> None:
        # F-18 (D-B, D5, O2): a quoted "str" counts; a default value stays allowed.
        valid_sources = (
            "def main(x):\n    return x\n",
            "def main(x: str):\n    return x\n",
            "def main(x) -> str:\n    return x\n",
            "def main(x: str) -> str:\n    return x\n",
            "def main(x: 'str') -> 'str':\n    return x\n",
            "def main(x: str = '') -> str:\n    return x\n",
            "def main(x, /) -> str:\n    return x\n",
        )
        for source in valid_sources:
            with self.subTest(source=source):
                validate_script(source)

    def test_an_annotation_other_than_str_is_refused(self) -> None:
        invalid_sources = (
            ("from typing import Optional\ndef main(x: Optional[str]) -> str:\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: int) -> str:\n    return str(x)\n", PARAMETER_ANNOTATION),
            ("import builtins\ndef main(x: builtins.str):\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: 'int'):\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x: int) -> int:\n    return x\n", PARAMETER_ANNOTATION),
            ("def main(x) -> int:\n    return x\n", RETURN_ANNOTATION),
            ("def main(x: str) -> None:\n    return None\n", RETURN_ANNOTATION),
            ("from typing import Text\ndef main(x) -> Text:\n    return x\n", RETURN_ANNOTATION),
        )
        for source, message in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(ValueError) as raised:
                    validate_script(source)
                self.assertEqual(str(raised.exception), message)

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("os.replace", wraps=os.replace) as replace:
            save_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".upper.py.*.tmp")), [])

    def _temporary_files(self) -> list[str]:
        return sorted(path.name for path in self.directory.iterdir() if path.name.endswith(".tmp"))

    def test_save_installs_through_the_shared_atomic_writer(self) -> None:
        # F-8 (D6): synced before the replace, through the temporary-file name of
        # shared.atomic_write (16 hex digits).
        source = "def main(text):\r\n    return text\n"
        with patch("shared.atomic_write.os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            save_script(self.path, source)

        fsync.assert_called_once()
        replace.assert_called_once()
        self.assertRegex(Path(replace.call_args.args[0]).name, r"^\.upper\.py\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(self.path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self._temporary_files(), [])

    def test_save_creates_the_folder(self) -> None:
        path = self.directory / "script" / "upper.py"

        save_script(path, "def main(text):\n    return text\n")

        self.assertEqual(path.read_bytes(), b"def main(text):\n    return text\n")

    def test_write_error_leaves_no_temporary_file_and_keeps_the_script(self) -> None:
        old = b"def main(text):\n    return text\n"
        self.path.write_bytes(old)

        with full_disk(self.directory, after=10), self.assertRaises(OSError) as raised:
            save_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(raised.exception.errno, errno.ENOSPC)
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self._temporary_files(), [])

    @unittest.skipUnless(os.name == "nt", "Windows read-only attribute")
    def test_read_only_script_is_refused_with_the_in_place_verdict(self) -> None:
        # F-8 (D6): the message names the script, as an in-place write would (F-3 D3).
        old = b"def main(text):\n    return text\n"
        self.path.write_bytes(old)
        make_read_only(self, self.path)

        with self.assertRaises(PermissionError) as raised:
            save_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(Path(raised.exception.filename).name, "upper.py")
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self._temporary_files(), [])

    def test_invalid_save_does_not_overwrite_existing_file(self) -> None:
        original = "def main(text):\n    return text\n"
        self.path.write_text(original, encoding="utf-8")
        for source, error in (("def main(:\n", SyntaxError), ("def main(x: int):\n    return x\n", ValueError)):
            with self.subTest(source=source):
                with self.assertRaises(error):
                    save_script(self.path, source)
                self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_read_keeps_the_text_and_drops_a_bom(self) -> None:
        # F-18 (D6): UTF-8 with or without a BOM; line ends as they are.
        source = "def main(text):\r\n    return text + '臺'\r\n"
        for data in (source.encode("utf-8"), b"\xef\xbb\xbf" + source.encode("utf-8")):
            with self.subTest(bom=data.startswith(b"\xef")):
                self.path.write_bytes(data)
                self.assertEqual(read_script_source(self.path), source)

    def test_read_refuses_a_file_that_is_not_utf8_and_a_missing_file(self) -> None:
        self.path.write_bytes("def main(text):\n    return text + '臺'\n".encode("cp950"))
        with self.assertRaises(UnicodeDecodeError):
            read_script_source(self.path)
        with self.assertRaises(FileNotFoundError):
            read_script_source(self.directory / "missing.py")

    def test_execution_supports_helpers_imports_file_name_and_fresh_globals(self) -> None:
        self.path.write_text(
            "import re\n"
            "counter = globals().get('counter', 0) + 1\n"
            "def helper(text):\n    return re.sub(' +', ' ', text)\n"
            "def main(text):\n    return f'{counter}:{__file__}:{helper(text)}'\n",
            encoding="utf-8",
        )
        expected = f"1:{self.path}:a b"
        self.assertEqual(execute_script(self.path, "a  b"), expected)
        self.assertEqual(execute_script(self.path, "a  b"), expected)

    def test_execution_runs_a_script_saved_with_a_bom(self) -> None:
        self.path.write_bytes(b"\xef\xbb\xbfdef main(text: str) -> str:\r\n    return text.upper()\r\n")

        self.assertEqual(execute_script(self.path, "abc"), "ABC")

    def test_execution_of_a_missing_or_undecodable_script_fails(self) -> None:
        # F-18 (D10, O8): no identity fallback.
        with self.assertRaises(FileNotFoundError):
            execute_script(self.directory / "missing.py", "source")
        self.path.write_bytes("def main(text):\n    return '臺'\n".encode("cp950"))
        with self.assertRaises(UnicodeDecodeError):
            execute_script(self.path, "source")

    def test_execution_rejects_non_callable_main_and_non_string_return(self) -> None:
        invalid_sources = (
            "def main(text):\n    return text\nmain = None\n",
            "def main(text):\n    return 42\n",
        )
        # Translated when raised (F-12 D8), as the second one is formatted.
        messages = ("main 不是可以呼叫的函式。", "main 必須傳回 str，而不是 int。")
        for source, message in zip(invalid_sources, messages):
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(TypeError) as raised:
                    execute_script(self.path, "source")

                self.assertEqual(str(raised.exception), message)

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        for source in ("def main(first, second):\n    return first\n", "def main(x) -> bytes:\n    return x\n"):
            with self.subTest(source=source):
                self.path.write_text(source, encoding="utf-8")
                with self.assertRaises(ValueError):
                    execute_script(self.path, "source")


if __name__ == "__main__":
    unittest.main()
