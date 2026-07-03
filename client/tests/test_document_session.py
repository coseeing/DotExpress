import unittest
import sys
import types

if "mammoth" not in sys.modules:
    mammoth = types.ModuleType("mammoth")
    mammoth.convert_to_html = lambda *args, **kwargs: types.SimpleNamespace(value="")
    sys.modules["mammoth"] = mammoth

if "ebooklib" not in sys.modules:
    ebooklib = types.ModuleType("ebooklib")
    epub = types.ModuleType("ebooklib.epub")
    epub.read_epub = lambda *_args, **_kwargs: types.SimpleNamespace(spine=[], get_item_with_id=lambda _item_id: None)
    ebooklib.epub = epub
    sys.modules["ebooklib"] = ebooklib
    sys.modules["ebooklib.epub"] = epub

if "pymupdf" not in sys.modules:
    sys.modules["pymupdf"] = types.ModuleType("pymupdf")

if "pypdf" not in sys.modules:
    pypdf = types.ModuleType("pypdf")
    pypdf.PdfReader = type("PdfReader", (), {})
    sys.modules["pypdf"] = pypdf

if "lxml" not in sys.modules:
    lxml = types.ModuleType("lxml")
    etree = types.ModuleType("lxml.etree")
    html = types.ModuleType("lxml.html")

    class _QName:
        def __init__(self, element):
            self.localname = getattr(element, "tag", "")

    etree.QName = _QName
    etree.XMLParser = lambda *args, **kwargs: object()
    etree.fromstring = lambda *args, **kwargs: types.SimpleNamespace(xpath=lambda *_a, **_k: [])
    html.fragment_fromstring = lambda *args, **kwargs: types.SimpleNamespace()
    lxml.etree = etree
    lxml.html = html
    sys.modules["lxml"] = lxml
    sys.modules["lxml.etree"] = etree
    sys.modules["lxml.html"] = html

from documents.session import (
    DeleteDocumentDecision,
    format_window_title,
    get_adjacent_document_name,
    plan_delete_document,
)
from documents.workspace import Document


class DocumentSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            Document(name="alpha", text="a", braille="1"),
            Document(name="math", text="m", braille="2"),
            Document(name="zoo", text="z", braille="3"),
        ]

    def test_plan_delete_document_prefers_previous_selection_and_tracks_open_document(self) -> None:
        self.assertEqual(
            plan_delete_document(self.documents, "math", open_name="math"),
            DeleteDocumentDecision(preferred_name="alpha", was_open=True),
        )

    def test_plan_delete_document_uses_next_selection_when_first_removed(self) -> None:
        self.assertEqual(
            plan_delete_document(self.documents, "alpha", open_name="zoo"),
            DeleteDocumentDecision(preferred_name="math", was_open=False),
        )

    def test_get_adjacent_document_name_wraps_forward_from_last_document(self) -> None:
        self.assertEqual(
            get_adjacent_document_name(self.documents, "zoo", step=1),
            "alpha",
        )

    def test_get_adjacent_document_name_wraps_backward_from_first_document(self) -> None:
        self.assertEqual(
            get_adjacent_document_name(self.documents, "alpha", step=-1),
            "zoo",
        )

    def test_get_adjacent_document_name_returns_none_when_documents_are_empty(self) -> None:
        self.assertIsNone(get_adjacent_document_name([], "alpha", step=1))

    def test_get_adjacent_document_name_falls_back_to_list_boundaries_when_current_name_missing(self) -> None:
        self.assertEqual(get_adjacent_document_name(self.documents, None, step=1), "alpha")
        self.assertEqual(get_adjacent_document_name(self.documents, None, step=-1), "zoo")

    def test_format_window_title_includes_open_document_name(self) -> None:
        self.assertEqual(format_window_title("lesson1"), "lesson1 - DotExpress")
        self.assertEqual(format_window_title(None), "DotExpress")
        self.assertEqual(format_window_title(""), "DotExpress")


if __name__ == "__main__":
    unittest.main()
