"""The script folder of F-18: the files (manager), the actions and the status of a script."""

import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT
from i18n import _
from shared.name_validation import NameValidationError
from tests.file_log_isolation import isolate_file_logs
from tests.windows_file_handles import hold_open
from text_scripts.actions import get_script_action_availability, script_display_name
from text_scripts.manager import (
    NO_PROCESSING_DISPLAY_NAME,
    ScriptImportSourceError,
    create_script,
    delete_script,
    ensure_no_processing_script,
    export_script,
    import_script,
    is_no_processing_script,
    list_script_names,
    normalize_script_name,
    rename_script,
    resolve_selected_script,
    script_exists,
    script_path_for_name,
)
from text_scripts.read_problems import (
    ScriptStatus,
    describe_script_problem,
    describe_unreadable_script,
    read_script_status,
)

LOGGER = "dotexpress.gui"
UPPER = b"def main(text: str) -> str:\n    return text.upper()\n"
# As some Windows editors save it: a BOM, CRLF and CJK text.
BOM_SCRIPT = b"\xef\xbb\xbf" + "def main(text):\r\n    return text.replace('台', '臺')\r\n".encode("utf-8")
NOT_UTF8 = "def main(text):\n    return text + '臺'\n".encode("cp950")


def setUpModule() -> None:
    # A script that cannot be read is logged to dotexpress.gui (gui.log), as a dictionary is (F-6).
    unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class ScriptFolderTestCase(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.script_dir = self.root / "script"

    def write_script(self, name: str, data: bytes = UPPER) -> Path:
        self.script_dir.mkdir(parents=True, exist_ok=True)
        path = self.script_dir / f"{name}.py"
        path.write_bytes(data)
        return path

    def listing(self, directory: Path | None = None) -> list[str]:
        return sorted(path.name for path in (directory or self.script_dir).iterdir())


class ScriptFolderTest(ScriptFolderTestCase):
    def test_ensure_creates_the_folder_and_no_processing(self) -> None:
        path = ensure_no_processing_script(self.script_dir)

        self.assertEqual(path, self.script_dir / "no-processing.py")
        self.assertEqual(path.read_bytes(), b"def main(input: str) -> str:\n    return input\n")
        self.assertEqual(self.listing(), ["no-processing.py"])

    def test_ensure_never_rewrites_an_existing_file(self) -> None:
        # F-18 (D4): user bytes in no-processing.py are left alone; conversion never reads them.
        altered = self.write_script("no-processing", b"def main(text):\n    return text.upper()\n")

        with patch("os.replace") as replace:
            ensure_no_processing_script(self.script_dir)

        replace.assert_not_called()
        self.assertEqual(altered.read_bytes(), b"def main(text):\n    return text.upper()\n")

    def test_no_processing_comes_first_and_the_others_in_dictionary_order(self) -> None:
        # F-18 (D1, O1): not alphabetical for No Processing; the others casefold, then the name.
        for name in ("zeta", "Beta", "alpha", "中文", "beta2", "no-processing"):
            self.write_script(name)

        self.assertEqual(list_script_names(self.script_dir), ["no-processing", "alpha", "Beta", "beta2", "zeta", "中文"])

    def test_only_python_files_are_scripts(self) -> None:
        self.write_script("alpha")
        (self.script_dir / "notes.txt").write_text("x", encoding="utf-8")
        (self.script_dir / "folder.py").mkdir()

        self.assertEqual(list_script_names(self.script_dir), ["alpha"])

    def test_a_missing_folder_lists_nothing(self) -> None:
        self.assertEqual(list_script_names(self.script_dir), [])

    def test_a_name_maps_to_a_python_file(self) -> None:
        self.assertEqual(script_path_for_name("臺灣", self.script_dir), self.script_dir / "臺灣.py")
        self.assertTrue(is_no_processing_script("no-processing"))
        self.assertTrue(is_no_processing_script(" No-Processing "))
        self.assertFalse(is_no_processing_script("no-processing2"))

    def test_resolve_keeps_a_listed_name_and_falls_back_to_no_processing(self) -> None:
        names = ["no-processing", "alpha"]
        self.assertEqual(resolve_selected_script(names, "alpha"), "alpha")
        for saved in ("missing", "", None, "Alpha"):
            with self.subTest(saved=saved):
                self.assertEqual(resolve_selected_script(names, saved), "no-processing")
        self.assertEqual(resolve_selected_script([], "alpha"), "no-processing")


class ScriptNameTest(ScriptFolderTestCase):
    def assert_refused(self, name: str, code: str) -> None:
        with self.assertRaises(NameValidationError) as raised:
            normalize_script_name(name)
        self.assertEqual(raised.exception.code, code)

    def test_names_follow_the_dictionary_rules(self) -> None:
        self.assertEqual(normalize_script_name("  大寫 1"), "大寫 1")
        self.assertEqual(normalize_script_name("1.1"), "1.1")
        for name, code in (("", "empty"), ("   ", "empty"), ("x" * 33, "too_long"), ("a/b", "invalid"), ("CON", "invalid"), ("a.", "invalid")):
            with self.subTest(name=name):
                self.assert_refused(name, code)

    def test_no_processing_names_are_reserved_in_any_case(self) -> None:
        # F-18 (D4): the internal name, the msgid and its translation.
        self.assertEqual(NO_PROCESSING_DISPLAY_NAME, "No Processing")
        for name in ("no-processing", "NO-PROCESSING", " No-Processing", "No Processing", "no processing", "不處理"):
            with self.subTest(name=name):
                self.assert_refused(name, "reserved")

    def test_script_exists_compares_the_normalized_name(self) -> None:
        self.write_script("alpha")

        self.assertTrue(script_exists(self.script_dir, " alpha"))
        self.assertFalse(script_exists(self.script_dir, "beta"))


class CreateScriptTest(ScriptFolderTestCase):
    def test_create_writes_the_source_as_it_is(self) -> None:
        source = "def main(text):\r\n    return text + '臺'\n"

        path = create_script(self.script_dir, " upper", source)

        self.assertEqual(path, self.script_dir / "upper.py")
        self.assertEqual(path.read_bytes(), source.encode("utf-8"))

    def test_a_taken_name_is_refused_and_the_file_kept(self) -> None:
        existing = self.write_script("upper", b"KEEP")

        with self.assertRaises(FileExistsError):
            create_script(self.script_dir, "upper", NO_PROCESSING_SCRIPT)

        self.assertEqual(existing.read_bytes(), b"KEEP")

    def test_invalid_code_writes_nothing(self) -> None:
        self.script_dir.mkdir()
        for source, error in (("def main(:\n", SyntaxError), ("def main(a, b):\n    return a\n", ValueError)):
            with self.subTest(source=source):
                with self.assertRaises(error):
                    create_script(self.script_dir, "bad", source)
                self.assertEqual(self.listing(), [])


class ImportScriptTest(ScriptFolderTestCase):
    def source(self, name: str, data: bytes) -> Path:
        folder = self.root / "source"
        folder.mkdir(exist_ok=True)
        path = folder / name
        path.write_bytes(data)
        return path

    def test_import_copies_the_original_bytes(self) -> None:
        for name, data in (("upper2.py", UPPER), ("bom.PY", BOM_SCRIPT)):
            with self.subTest(name=name):
                path = import_script(self.script_dir, self.source(name, data), Path(name).stem)

                self.assertEqual(path, self.script_dir / f"{Path(name).stem}.py")
                self.assertEqual(path.read_bytes(), data)

    def test_only_a_py_suffix_is_accepted(self) -> None:
        # F-18 (D8.5): the file filter can be bypassed by typing a name.
        for name in ("upper.txt", "upper", "upper.pyw", "upper.py.txt"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError) as raised:
                    import_script(self.script_dir, self.source(name, UPPER), "upper")
                self.assertEqual(str(raised.exception), "Only Python files (.py) can be imported.")
                self.assertFalse(self.script_dir.exists() and self.listing())

    def test_invalid_sources_copy_nothing(self) -> None:
        cases = (
            ("cp950.py", NOT_UTF8, UnicodeDecodeError),
            ("bad.py", b"def main(:\n", SyntaxError),
            ("two.py", b"def main(a, b):\n    return a\n", ValueError),
            ("int.py", b"def main(a: int) -> str:\n    return str(a)\n", ValueError),
        )
        for name, data, error in cases:
            with self.subTest(name=name):
                with self.assertRaises(error):
                    import_script(self.script_dir, self.source(name, data), Path(name).stem)
                self.assertEqual(self.listing(), [])

    def test_a_source_that_cannot_be_opened_is_told_apart(self) -> None:
        source = self.source("upper.py", UPPER)
        denied = PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(source))

        with patch.object(Path, "read_bytes", side_effect=denied), self.assertRaises(ScriptImportSourceError) as raised:
            import_script(self.script_dir, source, "upper")

        self.assertIs(raised.exception.error, denied)
        self.assertIs(raised.exception.__cause__, denied)
        self.assertEqual(self.listing(), [])

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_a_source_held_without_read_sharing_is_told_apart(self) -> None:
        source = self.source("upper.py", UPPER)
        hold_open(self, source, 0)

        with self.assertRaises(ScriptImportSourceError) as raised:
            import_script(self.script_dir, source, "upper")

        self.assertIsInstance(raised.exception.error, PermissionError)
        self.assertEqual(self.listing(), [])

    def test_a_taken_name_raises_file_exists_and_keeps_the_file(self) -> None:
        existing = self.write_script("upper", b"KEEP")

        with self.assertRaises(FileExistsError):
            import_script(self.script_dir, self.source("upper.py", UPPER), "Upper")

        self.assertEqual(existing.read_bytes(), b"KEEP")
        self.assertEqual(self.listing(), ["upper.py"])

    def test_a_reserved_name_is_refused(self) -> None:
        with self.assertRaises(NameValidationError):
            import_script(self.script_dir, self.source("no-processing.py", UPPER), "no-processing")


class RenameDeleteExportTest(ScriptFolderTestCase):
    def test_rename_moves_the_file(self) -> None:
        self.write_script("upper", BOM_SCRIPT)

        path = rename_script(self.script_dir, "upper", " shout")

        self.assertEqual(path, self.script_dir / "shout.py")
        self.assertEqual(self.listing(), ["shout.py"])
        self.assertEqual(path.read_bytes(), BOM_SCRIPT)

    def test_rename_refuses_no_processing_and_a_taken_name(self) -> None:
        ensure_no_processing_script(self.script_dir)
        self.write_script("upper")
        self.write_script("shout")

        with self.assertRaises(ValueError):
            rename_script(self.script_dir, "no-processing", "other")
        with self.assertRaises(FileExistsError):
            rename_script(self.script_dir, "upper", "shout")
        with self.assertRaises(NameValidationError):
            rename_script(self.script_dir, "upper", "No Processing")
        self.assertEqual(self.listing(), ["no-processing.py", "shout.py", "upper.py"])

    @unittest.skipUnless(os.name == "nt", "case-insensitive file names")
    def test_a_case_only_rename_works(self) -> None:
        self.write_script("upper")

        rename_script(self.script_dir, "upper", "Upper")

        self.assertEqual(list_script_names(self.script_dir), ["Upper"])

    def test_delete_removes_a_script_and_refuses_no_processing(self) -> None:
        ensure_no_processing_script(self.script_dir)
        self.write_script("upper")

        delete_script(self.script_dir, "upper")
        with self.assertRaises(ValueError):
            delete_script(self.script_dir, "No-Processing")

        self.assertEqual(self.listing(), ["no-processing.py"])

    def test_export_copies_the_bytes(self) -> None:
        self.write_script("bom", BOM_SCRIPT)
        self.write_script("cp950", NOT_UTF8)
        export_dir = self.root / "export"
        export_dir.mkdir()
        (export_dir / "bom.py").write_bytes(b"OLD")

        for name, data in (("bom", BOM_SCRIPT), ("cp950", NOT_UTF8)):
            with self.subTest(name=name):
                export_script(self.script_dir, name, export_dir / f"{name}.py")
                self.assertEqual((export_dir / f"{name}.py").read_bytes(), data)
        self.assertEqual(self.listing(export_dir), ["bom.py", "cp950.py"])

    def test_export_of_no_processing_writes_its_text_not_the_file(self) -> None:
        # F-18 (D4): the documented content, even after the disk file was altered.
        self.write_script("no-processing", b"def main(text):\n    return text.upper()\n")
        destination = self.root / "no-processing.py"

        export_script(self.script_dir, "no-processing", destination)

        self.assertEqual(destination.read_bytes(), b"def main(input: str) -> str:\n    return input\n")

    def test_export_onto_a_folder_fails_as_a_dictionary_export_does(self) -> None:
        self.write_script("upper")
        destination = self.root / "folder.py"
        (destination / "keep").mkdir(parents=True)

        for name in ("upper", "no-processing"):
            with self.subTest(name=name):
                with self.assertRaises(OSError) as raised:
                    export_script(self.script_dir, name, destination)
                code = errno.EACCES if os.name == "nt" else errno.EISDIR
                self.assertEqual(str(raised.exception), f"[Errno {code}] {os.strerror(code)}: {str(destination)!r}")
                self.assertEqual(os.listdir(destination), ["keep"])


class ScriptActionsTest(unittest.TestCase):
    def test_no_processing_can_only_be_exported(self) -> None:
        # F-18 (D7): unlike the default dictionary, it cannot be edited either.
        names = ["no-processing", "upper"]
        availability = get_script_action_availability(names, "no-processing")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (False, False, False, True),
        )
        availability = get_script_action_availability(names, "upper")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (True, True, True, True),
        )
        availability = get_script_action_availability([], "")
        self.assertEqual(
            (availability.edit, availability.delete, availability.rename, availability.export),
            (False, False, False, False),
        )

    def test_no_processing_is_shown_translated(self) -> None:
        self.assertEqual(script_display_name("no-processing"), "不處理")
        self.assertEqual(script_display_name("no-processing"), _("No Processing"))
        self.assertEqual(script_display_name("大寫"), "大寫")


class ScriptStatusTest(ScriptFolderTestCase):
    def test_a_valid_script_is_ready(self) -> None:
        for name, data in (("upper", UPPER), ("bom", BOM_SCRIPT)):
            with self.subTest(name=name):
                check = read_script_status(self.write_script(name, data))
                self.assertEqual((check.status, check.error), (ScriptStatus.READY, None))

    def test_code_that_breaks_the_rule_is_not_valid_and_not_logged(self) -> None:
        cases = (
            (b"def main(:\n", SyntaxError),
            (b"def main(a, b):\n    return a\n", ValueError),
            (b"def main(a) -> int:\n    return a\n", ValueError),
        )
        for data, error in cases:
            with self.subTest(data=data):
                with self.assertNoLogs(LOGGER):
                    check = read_script_status(self.write_script("bad", data))
                self.assertEqual(check.status, ScriptStatus.NOT_VALID)
                self.assertIsInstance(check.error, error)

    def test_a_file_that_cannot_be_read_is_unreadable_and_logged_on_one_line(self) -> None:
        path = self.write_script("cp950", NOT_UTF8)
        with self.assertLogs(LOGGER, "ERROR") as logs:
            check = read_script_status(path)

        self.assertEqual(check.status, ScriptStatus.UNREADABLE)
        self.assertIsInstance(check.error, UnicodeDecodeError)
        self.assertEqual(len(logs.records), 1)
        self.assertTrue(logs.output[0].startswith('ERROR:dotexpress.gui:Cannot read script "cp950.py": UnicodeDecodeError: '))
        self.assertIsNone(logs.records[0].exc_info)

    @unittest.skipUnless(os.name == "nt", "Windows sharing modes")
    def test_a_file_held_without_read_sharing_is_unreadable(self) -> None:
        path = self.write_script("locked")
        hold_open(self, path, 0)
        with self.assertLogs(LOGGER, "ERROR"):
            check = read_script_status(path)

        self.assertEqual(check.status, ScriptStatus.UNREADABLE)
        self.assertIsInstance(check.error, PermissionError)
        self.assertEqual(
            describe_script_problem(check.error),
            "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。",
        )

    def test_each_problem_has_its_reason(self) -> None:
        not_utf8 = self.assertRaises(UnicodeDecodeError)
        with not_utf8:
            NOT_UTF8.decode("utf-8")
        cases = (
            (not_utf8.exception, "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"),
            (
                PermissionError(errno.EACCES, "denied"),
                "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。",
            ),
            (FileNotFoundError(errno.ENOENT, "missing"), "無法讀取檔案：[Errno 2] missing"),
            (SyntaxError("invalid syntax", ("bad.py", 1, 10, "def main(:\n")), "invalid syntax (bad.py, line 1)"),
            (
                ValueError("main must define exactly one positional parameter and no other parameters."),
                "main 必須恰好定義一個位置參數，且不得有其他參數。",
            ),
            (ValueError("The parameter of main must be annotated as str, or not annotated."), "main 的參數只能標註為 str，或不加標註。"),
            (
                ValueError("The return value of main must be annotated as str, or not annotated."),
                "main 的傳回值只能標註為 str，或不加標註。",
            ),
            (RecursionError("too deep"), "too deep"),
        )
        for error, reason in cases:
            with self.subTest(error=type(error).__name__, reason=reason):
                self.assertEqual(describe_script_problem(error), reason)

    def test_the_edit_box_names_the_script_above_the_reason(self) -> None:
        error = FileNotFoundError(errno.ENOENT, "missing")

        self.assertEqual(describe_unreadable_script("upper", error), "無法讀取腳本「upper」。\n\n無法讀取檔案：[Errno 2] missing")


if __name__ == "__main__":
    unittest.main()
