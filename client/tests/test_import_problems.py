"""Why an imported file was skipped (F-12 D3): the reasons of the Import Issues dialog."""

from __future__ import annotations

import ast
import errno
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.errors import PdfReadError

from documents.import_problems import ImportProblem, describe_import_problem
from documents.importers import import_epub, import_pdf
from documents.workspace import load_document_package, load_text_document
from shared.name_validation import NameValidationError

MODULE_PATH = Path(__file__).resolve().parents[1] / "documents" / "import_problems.py"
# The zh_TW reasons as the user sees them.
NOT_UTF8 = "檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。"
CANNOT_OPEN = "無法開啟檔案。檔案可能正被其他程式使用，或你沒有讀取權限。請關閉其他程式後再試一次。"
NAME_LENGTH = "文件名稱長度需為 1 到 32 個字元。"
NAME_INVALID = "文件名稱不是有效的 Windows 檔名。"
UNSUPPORTED = "無法匯入這種類型的檔案。"
WRONG_EXTENSION = "副檔名與選取的檔案類型不符。"
INVALID_PACKAGE = "匯入的檔案必須是有效的 DotExpress DEP 封裝檔。"
ENCRYPTED_PDF = "這個 PDF 檔已加密，無法匯入。"
DAMAGED_EPUB = "EPUB 檔已損壞，或沒有可讀取的內容。"
DAMAGED_FILE = "檔案已損壞或格式不正確。"


def _raised(function, *args) -> Exception:
    try:
        function(*args)
    except Exception as error:  # noqa: BLE001 (the error is the value under test)
        return error
    raise AssertionError(f"{function.__name__} raised nothing")


class ImportProblemTest(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)

    def _package(self, name: str, members: dict[str, bytes]) -> Path:
        path = self.root / f"{name}.dep"
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in members.items():
                archive.writestr(member, data)
        return path

    def test_import_problem_is_a_value_error_that_keeps_its_english_text(self) -> None:
        error = ImportProblem("Text document must use the .txt extension.", "The file name extension does not match the selected file type.")

        self.assertIsInstance(error, ValueError)
        self.assertEqual(str(error), "Text document must use the .txt extension.")
        self.assertEqual(error.reason, "The file name extension does not match the selected file type.")

    def test_a_text_file_that_is_not_utf8(self) -> None:
        path = self.root / "big5.txt"
        path.write_bytes("臺北".encode("cp950"))
        error = _raised(load_text_document, path)

        self.assertIsInstance(error, UnicodeDecodeError)
        self.assertEqual(describe_import_problem(error, "txt"), NOT_UTF8)

    def test_a_file_that_cannot_be_opened(self) -> None:
        error = PermissionError(errno.EACCES, "Permission denied", "locked.txt")

        for format_key in ("txt", "docx", "dep"):
            with self.subTest(format_key=format_key):
                self.assertEqual(describe_import_problem(error, format_key), CANNOT_OPEN)

    def test_a_file_name_that_is_not_a_document_name(self) -> None:
        cases = {
            "too_long": NAME_LENGTH,
            "empty": NAME_LENGTH,
            "invalid": NAME_INVALID,
            "reserved": NAME_INVALID,
        }
        for code, expected in cases.items():
            with self.subTest(code=code):
                self.assertEqual(describe_import_problem(NameValidationError(code, "English text"), "txt"), expected)

    def test_the_problems_of_the_loaders_show_their_reason(self) -> None:
        (self.root / "notes.md").write_text("x", encoding="utf-8")
        (self.root / "notes.pdf").write_text("x", encoding="utf-8")
        cases = (
            ("txt", lambda: load_text_document(self.root / "notes.md"), WRONG_EXTENSION),
            ("pdf", lambda: import_pdf(self.root / "notes.md"), WRONG_EXTENSION),
            ("epub", lambda: import_epub(self.root / "notes.pdf"), WRONG_EXTENSION),
            ("dep", lambda: load_document_package(self.root / "notes.md"), INVALID_PACKAGE),
            ("dep", lambda: load_document_package(self._package("one", {"one.txt": b"a"})), INVALID_PACKAGE),
            (
                "dep",
                lambda: load_document_package(self._package("two", {"two.txt": b"a", "other.brl": b"b"})),
                INVALID_PACKAGE,
            ),
        )
        for format_key, load, expected in cases:
            with self.subTest(format_key=format_key, expected=expected):
                error = _raised(load)

                self.assertIsInstance(error, ImportProblem)
                self.assertEqual(describe_import_problem(error, format_key), expected)

    def test_an_encrypted_pdf(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.encrypt("secret")
        path = self.root / "locked.pdf"
        with path.open("wb") as stream:
            writer.write(stream)
        error = _raised(import_pdf, path)

        self.assertIsInstance(error, ImportProblem)
        self.assertEqual(str(error), "Encrypted PDF cannot be imported.")
        self.assertEqual(describe_import_problem(error, "pdf"), ENCRYPTED_PDF)

    def test_an_epub_without_readable_content(self) -> None:
        path = self.root / "book.epub"
        path.write_bytes(b"stub")
        books = {
            "no spine": SimpleNamespace(spine=[], get_item_with_id=lambda item_id: None),
            "a missing spine item": SimpleNamespace(spine=[("chapter1", "yes")], get_item_with_id=lambda item_id: None),
        }
        for label, book in books.items():
            with self.subTest(label), patch("documents.importers.epub_importer.epub.read_epub", return_value=book):
                error = _raised(import_epub, path)

                self.assertIsInstance(error, ImportProblem)
                self.assertEqual(describe_import_problem(error, "epub"), DAMAGED_EPUB)

    def test_any_other_error_reading_a_package(self) -> None:
        not_a_zip = self.root / "broken.dep"
        not_a_zip.write_bytes(b"not a zip")
        bad_metadata = self._package(
            "meta", {"meta.txt": b"a", "meta.brl": b"b", "meta.meta.json": b"{"}
        )
        not_utf8 = self._package("big5", {"big5.txt": "臺北".encode("cp950"), "big5.brl": b""})
        errors = {
            "not a zip archive": _raised(load_document_package, not_a_zip),
            "metadata that is not JSON": _raised(load_document_package, bad_metadata),
            "text that is not UTF-8": _raised(load_document_package, not_utf8),
            "a missing member": KeyError("There is no item named 'alpha.brl' in the archive"),
        }
        self.assertIsInstance(errors["not a zip archive"], zipfile.BadZipFile)
        self.assertIsInstance(errors["metadata that is not JSON"], json.JSONDecodeError)
        self.assertIsInstance(errors["text that is not UTF-8"], UnicodeDecodeError)
        for label, error in errors.items():
            with self.subTest(label):
                self.assertEqual(describe_import_problem(error, "dep"), INVALID_PACKAGE)

    def test_a_damaged_docx_epub_or_pdf_is_told_in_our_words(self) -> None:
        # F-12 review M-3: the library's English text is for the log, not for the box.
        cases = (
            ("docx", zipfile.BadZipFile("File is not a zip file")),
            ("epub", zipfile.BadZipFile("File is not a zip file")),
            ("pdf", ValueError("Stream has ended unexpectedly")),
            ("pdf", PdfReadError("EOF marker not found")),
            ("PDF", KeyError("/Root")),
        )
        for format_key, error in cases:
            with self.subTest(format_key=format_key, error=repr(error)):
                self.assertEqual(describe_import_problem(error, format_key), DAMAGED_FILE)

    def test_a_truncated_docx_and_pdf_from_the_real_libraries(self) -> None:
        from documents.importers import import_docx

        bad_docx = self.root / "bad.docx"
        bad_docx.write_bytes(b"PK\x03\x04 truncated")
        bad_pdf = self.root / "bad.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4\n1 0 obj\n<<")
        for loader, path, key in ((import_docx, bad_docx, "docx"), (import_pdf, bad_pdf, "pdf")):
            with self.subTest(key):
                error = _raised(loader, path)
                self.assertEqual(describe_import_problem(error, key), DAMAGED_FILE)

    def test_any_other_error_shows_its_own_text(self) -> None:
        missing = FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "gone.dep")
        cases = (
            ("docx", FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), "gone.docx")),
            ("pdf", OSError(errno.EIO, "I/O error")),
            ("dep", missing),
            ("txt", ValueError("odd")),
        )
        for format_key, error in cases:
            with self.subTest(format_key=format_key):
                self.assertEqual(describe_import_problem(error, format_key), f"無法讀取檔案：{error}")

    def test_module_imports_neither_wx_nor_dictionaries(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])

        self.assertFalse(imported & {"wx", "gui", "dialog", "dictionaries"}, imported)


if __name__ == "__main__":
    unittest.main()
