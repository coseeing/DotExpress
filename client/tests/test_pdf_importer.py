import tempfile
import unittest
from pathlib import Path

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

    def test_tagged_ast_supports_simple_structure_tree(self) -> None:
        class Page:
            def extract_text(self, *, visitor_operand_before, visitor_text):
                visitor_operand_before(b"BDC", [None, {"/MCID": 1}], None, None)
                visitor_text("Title", None, None, None, None)
                visitor_operand_before(b"EMC", [], None, None)
                visitor_operand_before(b"BDC", [None, {"/MCID": 2}], None, None)
                visitor_text("Body", None, None, None, None)
                visitor_operand_before(b"EMC", [], None, None)

        class Reader:
            pass

        reader = Reader()
        page = Page()
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
        self.assertEqual(
            _extract_tagged_ast(reader, structure["/StructTreeRoot"]),
            DocumentAst((Heading(2, "Title"), Paragraph("Body"))),
        )


if __name__ == "__main__":
    unittest.main()
