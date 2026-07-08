import sys
import types
import unittest

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

from documents.formats import build_import_wildcard, get_exportable_formats, get_format, get_importable_formats


class DocumentFormatsTest(unittest.TestCase):
    def test_get_format_returns_expected_descriptor(self) -> None:
        dep_format = get_format("dep")
        brl_format = get_format("brl")

        self.assertEqual(dep_format.extension, ".dep")
        self.assertEqual(brl_format.extension, ".brl")

    def test_get_format_rejects_unknown_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported document format"):
            get_format("missing")

    def test_importable_formats_preserve_existing_order(self) -> None:
        self.assertEqual(
            [descriptor.key for descriptor in get_importable_formats()],
            ["dep", "docx", "epub", "pdf", "txt"],
        )

    def test_exportable_formats_include_dep_and_brl(self) -> None:
        self.assertEqual(
            [descriptor.key for descriptor in get_exportable_formats()],
            ["dep", "brl"],
        )

    def test_import_wildcard_matches_existing_order_and_text(self) -> None:
        self.assertEqual(
            build_import_wildcard(),
            (
                "DEP (*.dep)|*.dep|"
                "DOCX (*.docx)|*.docx|"
                "EPUB (*.epub)|*.epub|"
                "PDF (*.pdf)|*.pdf|"
                "TXT (*.txt)|*.txt|"
                "All Supported Files (*.dep;*.docx;*.epub;*.pdf;*.txt)|*.dep;*.docx;*.epub;*.pdf;*.txt"
            ),
        )

    def test_export_requires_braille_policy_matches_format(self) -> None:
        self.assertFalse(get_format("dep").requires_braille)
        self.assertTrue(get_format("brl").requires_braille)


if __name__ == "__main__":
    unittest.main()
