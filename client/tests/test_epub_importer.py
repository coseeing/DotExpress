import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from lxml import etree

from documents.importers.base import ImportedDocument
from documents.importers.epub_importer import import_epub


class EpubImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "book.epub"
        self.path.write_bytes(b"epub")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    @patch("documents.importers.epub_importer.epub.read_epub")
    def test_imports_linear_spine_items_in_order(self, read_epub: Mock) -> None:
        first = Mock()
        first.get_content.return_value = b"<html xmlns='http://www.w3.org/1999/xhtml'><body><h1>First</h1></body></html>"
        second = Mock()
        second.get_content.return_value = b"<html xmlns='http://www.w3.org/1999/xhtml'><body><p>Second</p></body></html>"
        book = Mock(spine=[("chapter-2", "yes"), ("chapter-1", "yes"), ("nav", "no")])
        book.get_item_with_id.side_effect = {"chapter-2": second, "chapter-1": first, "nav": Mock()}.get
        read_epub.return_value = book

        self.assertEqual(import_epub(self.path), ImportedDocument("book", "Second\n\n# First\n"))

    @patch("documents.importers.epub_importer.epub.read_epub")
    def test_missing_spine_fails_import(self, read_epub: Mock) -> None:
        read_epub.return_value = Mock(spine=[])
        with self.assertRaisesRegex(ValueError, "readable spine"):
            import_epub(self.path)

    @patch("documents.importers.epub_importer.epub.read_epub")
    def test_malformed_spine_xhtml_fails_entire_import(self, read_epub: Mock) -> None:
        item = Mock()
        item.get_content.return_value = b"<html><body><p>broken</body></html>"
        book = Mock(spine=[("broken", "yes")])
        book.get_item_with_id.return_value = item
        read_epub.return_value = book
        with self.assertRaises(etree.XMLSyntaxError):
            import_epub(self.path)


if __name__ == "__main__":
    unittest.main()
