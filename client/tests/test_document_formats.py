import errno
import inspect
import os
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from conversion.output import DualViewSegment
from documents.formats import (
    ALL_SUPPORTED_FILES_LABEL,
    DOCUMENT_FORMATS,
    ExportContext,
    build_export_wildcard,
    build_import_wildcard,
    get_exportable_formats,
    get_format,
    get_import_filter_labels,
    get_importable_formats,
)
from documents.workspace import Document
import i18n
from i18n import _
from tests.full_disk import full_disk


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
            ["dep", "brl", "html"],
        )

    def test_html_format_uses_html_extension_and_does_not_require_braille(self) -> None:
        descriptor = get_format("html")

        self.assertEqual(descriptor.extension, ".html")
        self.assertEqual(descriptor.wildcard_label, "HTML")
        self.assertTrue(descriptor.exportable)
        self.assertFalse(descriptor.requires_braille)
        self.assertIsNotNone(descriptor.writer)

    def test_html_writer_renders_cached_dual_view_results_as_utf8(self) -> None:
        document = Document("alpha", "source", "braille")
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "alpha.html"
            with patch("documents.formats.render_dual_view_html", return_value="雙視內容") as render:
                get_format("html").writer(
                    destination,
                    document,
                    ExportContext(
                        dual_view_results=(DualViewSegment(result=Mock(raw=[], braille=[], raw_to_braille_pos=[]), source_kind="text"),),
                    ),
                )

            self.assertEqual(destination.read_text(encoding="utf-8"), "雙視內容")
            render.assert_called_once()

    def test_html_writer_declares_the_interface_language(self) -> None:
        # F-14 (D6): read at each export, for a document with conversion data and one without.
        self.addCleanup(i18n.set_language, i18n.current_language())
        results = (
            DualViewSegment(
                result=SimpleNamespace(raw=["a"], braille=["⠁"], braille_to_raw_pos=[0], raw_to_braille_pos=[0]),
                source_kind="text",
            ),
        )
        expected = {
            "zh_TW": ("zh-TW", "此文件沒有可顯示的轉換資料。"),
            "en": ("en", "No conversion data is available for this document."),
        }
        with TemporaryDirectory() as directory:
            for language, (tag, empty) in expected.items():
                with self.subTest(language):
                    i18n.set_language(language)
                    with_data = Path(directory) / f"{language}-alpha.html"
                    without_data = Path(directory) / f"{language}-new.html"

                    get_format("html").writer(with_data, Document("alpha", "a", "b"), ExportContext(dual_view_results=results))
                    get_format("html").writer(without_data, Document("new", "", None), ExportContext())

                    pages = [path.read_text(encoding="utf-8") for path in (with_data, without_data)]
                    for page in pages:
                        self.assertTrue(page.startswith(f'<!doctype html>\n<html lang="{tag}">\n'), page[:60])
                    self.assertIn('<span class="source">a</span>', pages[0])
                    self.assertIn(empty, pages[1])

    def test_html_export_failure_keeps_the_existing_file(self) -> None:
        # F-8 (D8): the page is rendered first; a write that failed part way left the
        # first part of the page in place of the old file.
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "alpha.html"
            destination.write_bytes(b"OLD GOOD EXPORT")
            with patch("documents.formats.render_dual_view_html", return_value="<p>雙視</p>\n<p>內容</p>\n"):
                with full_disk(directory, after=5), self.assertRaises(OSError) as raised:
                    get_format("html").writer(destination, Document("alpha", "a", "1"), ExportContext())

            self.assertEqual(raised.exception.errno, errno.ENOSPC)
            self.assertEqual(destination.read_bytes(), b"OLD GOOD EXPORT")
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()), ["alpha.html"])

    def test_exports_keep_their_crlf_bytes(self) -> None:
        # F-8 (D8): the atomic writes translate newlines as Path.write_text did (CRLF on Windows).
        text = "line 1\nline 2\n"
        with TemporaryDirectory() as directory:
            for key in ("brl", "html"):
                with self.subTest(key):
                    destination = Path(directory) / f"alpha.{key}"
                    with patch("documents.formats.render_dual_view_html", return_value=text):
                        get_format(key).writer(destination, Document("alpha", "a", text), ExportContext())

                    self.assertEqual(destination.read_bytes(), text.replace("\n", os.linesep).encode("utf-8"))

    def test_writers_take_path_document_and_context(self) -> None:
        for descriptor in get_exportable_formats():
            with self.subTest(format_key=descriptor.key):
                parameters = list(inspect.signature(descriptor.writer).parameters.values())
                self.assertEqual([parameter.name for parameter in parameters], ["path", "document", "context"])
                self.assertTrue(
                    all(parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD for parameter in parameters)
                )
                self.assertTrue(all(parameter.default is inspect.Parameter.empty for parameter in parameters))
                with TemporaryDirectory() as directory:
                    with self.assertRaises(TypeError):
                        descriptor.writer(Path(directory) / f"alpha{descriptor.extension}", Document("alpha", "t", "b"))

    def test_writers_return_destination_path(self) -> None:
        for descriptor in get_exportable_formats():
            with self.subTest(format_key=descriptor.key):
                with TemporaryDirectory() as directory:
                    destination = Path(directory) / f"alpha{descriptor.extension}"
                    written = descriptor.writer(str(destination), Document("alpha", "t", "b"), ExportContext())
                    self.assertEqual(written, destination)
                    self.assertIsInstance(written, Path)
                    self.assertTrue(destination.is_file())

    def test_dep_and_brl_writers_ignore_the_context(self) -> None:
        context = ExportContext(
            dual_view_results=(DualViewSegment(result=Mock(raw=[], braille=[], raw_to_braille_pos=[]), source_kind="text"),),
        )
        document = Document("alpha", "text", "\u2801")
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for key in ("dep", "brl"):
                with self.subTest(format_key=key):
                    writer = get_format(key).writer
                    writer(root / "plain" / f"alpha.{key}", document, ExportContext())
                    writer(root / "context" / f"alpha.{key}", document, context)
                    if key == "dep":
                        contents = []
                        for folder in ("plain", "context"):
                            with zipfile.ZipFile(root / folder / "alpha.dep") as archive:
                                contents.append({name: archive.read(name) for name in archive.namelist()})
                        self.assertEqual(contents[0], contents[1])
                        self.assertEqual(contents[0], {"alpha.txt": b"text", "alpha.brl": "\u2801".encode("utf-8")})
                    else:
                        self.assertEqual(
                            (root / "plain" / "alpha.brl").read_bytes(),
                            (root / "context" / "alpha.brl").read_bytes(),
                        )

    def test_export_fields_are_all_set_exactly_for_exportable_formats(self) -> None:
        for descriptor in DOCUMENT_FORMATS:
            with self.subTest(format_key=descriptor.key):
                self.assertEqual(
                    {
                        descriptor.exportable,
                        descriptor.writer is not None,
                        descriptor.export_wildcard is not None,
                        descriptor.export_label is not None,
                    },
                    {descriptor.exportable},
                )

    def test_export_labels_match_menu_text(self) -> None:
        self.assertEqual(
            [(descriptor.key, descriptor.export_label) for descriptor in get_exportable_formats()],
            [("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML")],
        )

    def test_export_wildcard_is_the_single_format_save_filter(self) -> None:
        expected = {
            "dep": "DotExpress files (*.dep)|*.dep",
            "brl": "Braille files (*.brl)|*.brl",
            "html": "HTML files (*.html)|*.html",
        }
        for key, wildcard in expected.items():
            with self.subTest(format_key=key):
                self.assertEqual(build_export_wildcard(get_format(key)), wildcard)
                self.assertEqual(build_export_wildcard(get_format(key), lambda value: f"T[{value}]"), f"T[{wildcard}]")

    def test_html_save_filter_is_translated(self) -> None:
        # F-12 (D8): a msgid like the BRL filter; the label HTML stays as it is.
        self.assertEqual(build_export_wildcard(get_format("html"), _), "HTML 檔 (*.html)|*.html")

    def test_export_wildcard_rejects_non_exportable_format(self) -> None:
        with self.assertRaisesRegex(ValueError, 'Unsupported export format: "txt"\\.'):
            build_export_wildcard(get_format("txt"))

    def test_export_context_defaults_to_no_results(self) -> None:
        self.assertEqual(ExportContext().dual_view_results, ())
        self.assertEqual(ExportContext(), ExportContext(dual_view_results=()))

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

    def test_all_supported_files_label_is_the_last_import_filter_label(self) -> None:
        self.assertEqual(ALL_SUPPORTED_FILES_LABEL, "All Supported Files")
        self.assertEqual(get_import_filter_labels()[-1], ALL_SUPPORTED_FILES_LABEL)
        self.assertEqual(get_import_filter_labels(), ["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"])

    def test_export_requires_braille_policy_matches_format(self) -> None:
        self.assertFalse(get_format("dep").requires_braille)
        self.assertTrue(get_format("brl").requires_braille)


if __name__ == "__main__":
    unittest.main()
