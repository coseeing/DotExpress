import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.preprocessing.user_script import (
    DEFAULT_PREPROCESSING_SCRIPT,
    execute_preprocessing_script,
    load_preprocessing_script,
    preprocessing_script_path,
    save_preprocessing_script,
    validate_preprocessing_script,
)
from tests.full_disk import full_disk
from tests.windows_file_handles import make_read_only


class UserPreprocessingScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.directory = Path(self._tmpdir.name)
        self.path = preprocessing_script_path(self.directory)

    def test_path_uses_dictionary_directory(self) -> None:
        self.assertEqual(self.path, self.directory / "preprocessing.py")

    def test_missing_file_loads_identity_script_without_creating_file(self) -> None:
        self.assertEqual(load_preprocessing_script(self.path), DEFAULT_PREPROCESSING_SCRIPT)
        self.assertFalse(self.path.exists())

    def test_validation_accepts_helpers_imports_and_any_parameter_name(self) -> None:
        source = "import re\n\ndef clean(value):\n    return re.sub(' +', ' ', value)\n\ndef main(text):\n    return clean(text)\n"
        validate_preprocessing_script(source)

    def test_validation_rejects_syntax_error(self) -> None:
        with self.assertRaises(SyntaxError):
            validate_preprocessing_script("def main(:\n")

    def test_validation_does_not_execute_valid_module_code(self) -> None:
        validate_preprocessing_script(
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
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

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
                with self.assertRaises(ValueError):
                    validate_preprocessing_script(source)

    def test_save_uses_utf8_and_atomic_replace(self) -> None:
        source = "def main(text):\n    return text + '臺灣'\n"
        with patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)
        self.assertEqual(self.path.read_text(encoding="utf-8"), source)
        replace.assert_called_once()
        self.assertEqual(list(self.directory.glob(".preprocessing.py.*.tmp")), [])

    def _temporary_files(self) -> list[str]:
        return sorted(path.name for path in self.directory.iterdir() if path.name.endswith(".tmp"))

    def test_save_installs_through_the_shared_atomic_writer(self) -> None:
        # F-8 (D6): synced before the replace, through the temporary-file name of
        # shared.atomic_write (16 hex digits).
        source = "def main(text):\r\n    return text\n"
        with patch("shared.atomic_write.os.fsync", wraps=os.fsync) as fsync, patch("os.replace", wraps=os.replace) as replace:
            save_preprocessing_script(self.path, source)

        fsync.assert_called_once()
        replace.assert_called_once()
        self.assertRegex(Path(replace.call_args.args[0]).name, r"^\.preprocessing\.py\.[0-9a-f]{16}\.tmp$")
        self.assertEqual(self.path.read_bytes(), source.encode("utf-8"))
        self.assertEqual(self._temporary_files(), [])

    def test_write_error_leaves_no_temporary_file_and_keeps_the_script(self) -> None:
        old = b"def main(text):\n    return text\n"
        self.path.write_bytes(old)

        with full_disk(self.directory, after=10), self.assertRaises(OSError) as raised:
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

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
            save_preprocessing_script(self.path, "def main(text):\n    return text.upper()\n")

        self.assertEqual(Path(raised.exception.filename).name, "preprocessing.py")
        self.assertEqual(str(raised.exception), f"[Errno 13] Permission denied: {str(self.path)!r}")
        self.assertEqual(self.path.read_bytes(), old)
        self.assertEqual(self._temporary_files(), [])

    def test_invalid_save_does_not_overwrite_existing_file(self) -> None:
        original = "def main(text):\n    return text\n"
        self.path.write_text(original, encoding="utf-8")
        with self.assertRaises(SyntaxError):
            save_preprocessing_script(self.path, "def main(:\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_execution_supports_helpers_imports_file_name_and_fresh_globals(self) -> None:
        self.path.write_text(
            "import re\n"
            "counter = globals().get('counter', 0) + 1\n"
            "def helper(text):\n    return re.sub(' +', ' ', text)\n"
            "def main(text):\n    return f'{counter}:{__file__}:{helper(text)}'\n",
            encoding="utf-8",
        )
        expected = f"1:{self.path}:a b"
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)
        self.assertEqual(execute_preprocessing_script(self.path, "a  b"), expected)

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
                    execute_preprocessing_script(self.path, "source")

                self.assertEqual(str(raised.exception), message)

    def test_execution_rejects_externally_written_invalid_contract(self) -> None:
        self.path.write_text("def main(first, second):\n    return first\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            execute_preprocessing_script(self.path, "source")


if __name__ == "__main__":
    unittest.main()
