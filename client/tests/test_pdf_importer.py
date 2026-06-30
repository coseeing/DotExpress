import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from documents.importers.base import ImportedDocument
from documents.importers.markdown_ast import DocumentAst, Heading, Paragraph
from documents.importers.pdf_importer import _extract_tagged_ast, _has_tagged_structure, import_pdf


class PdfImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "paper.pdf"
        self.path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_tagged_structure_requires_marked_true_and_structure_root(self) -> None:
        self.assertFalse(_has_tagged_structure({}))
        self.assertFalse(_has_tagged_structure({"/MarkInfo": {"/Marked": True}}))
        self.assertFalse(_has_tagged_structure({"/StructTreeRoot": {"/K": []}}))
        self.assertTrue(
            _has_tagged_structure(
                {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/P"}]}}
            )
        )

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_untagged_pdf_uses_plain_text_paragraphs(self, reader_type: Mock, fallback: Mock) -> None:
        reader_type.return_value.trailer = {"/Root": {}}
        fallback.return_value = DocumentAst((Paragraph("Page one"), Paragraph("Page two")))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "Page one\n\nPage two\n"))
        fallback.assert_called_once_with(self.path)

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer._extract_tagged_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_usable_tagged_pdf_uses_semantic_ast(
        self, reader_type: Mock, tagged: Mock, fallback: Mock
    ) -> None:
        root = {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/H1"}]}}
        reader_type.return_value.trailer = {"/Root": root}
        tagged.return_value = DocumentAst((Heading(1, "Tagged title"),))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "# Tagged title\n"))
        fallback.assert_not_called()

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer._extract_tagged_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_unreliable_tagged_pdf_falls_back_for_entire_file(
        self, reader_type: Mock, tagged: Mock, fallback: Mock
    ) -> None:
        root = {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/P"}]}}
        reader_type.return_value.trailer = {"/Root": root}
        tagged.side_effect = ValueError("Tagged PDF reading order is unreliable.")
        fallback.return_value = DocumentAst((Paragraph("Plain"),))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "Plain\n"))

    def test_tagged_ast_supports_simple_structure_tree(self) -> None:
        reader = Mock()
        page = Mock()
        reader.pages = [page]
        structure = {
            "/MarkInfo": {"/Marked": True},
            "/StructTreeRoot": {
                "/RoleMap": {"/CustomHeading": "/H2"},
                "/K": [
                    {"/S": "/CustomHeading", "/Pg": page, "/K": 1},
                    {"/S": "/P", "/Pg": page, "/K": 2},
                ],
            },
        }
        with patch("documents.importers.pdf_importer._extract_mcid_text", return_value={(0, 1): "Title", (0, 2): "Body"}):
            self.assertEqual(
                _extract_tagged_ast(reader, structure["/StructTreeRoot"]),
                DocumentAst((Heading(2, "Title"), Paragraph("Body"))),
            )


if __name__ == "__main__":
    unittest.main()
