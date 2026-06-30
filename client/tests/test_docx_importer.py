import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from documents.importers.base import ImportedDocument
from documents.importers.docx_importer import import_docx


class DocxImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "lesson.docx"
        self.path.write_bytes(b"docx")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    @patch("documents.importers.docx_importer.mammoth.convert_to_html")
    def test_imports_mammoth_html_as_markdown(self, convert_to_html: Mock) -> None:
        convert_to_html.return_value = Mock(
            value="<h1>Lesson</h1><ul><li>One</li></ul><table><tr><th>A</th></tr><tr><td>1</td></tr></table>",
            messages=[],
        )
        self.assertEqual(
            import_docx(self.path),
            ImportedDocument("lesson", "# Lesson\n\n- One\n\n| A |\n| --- |\n| 1 |\n"),
        )
        self.assertFalse(convert_to_html.call_args.kwargs["external_file_access"])

    @patch("documents.importers.docx_importer.mammoth.convert_to_html")
    def test_empty_conversion_succeeds(self, convert_to_html: Mock) -> None:
        convert_to_html.return_value = Mock(value="", messages=[])
        self.assertEqual(import_docx(self.path), ImportedDocument("lesson", ""))

    def test_rejects_wrong_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, r"must use the \.docx extension"):
            import_docx(self.path.with_suffix(".doc"))


if __name__ == "__main__":
    unittest.main()
