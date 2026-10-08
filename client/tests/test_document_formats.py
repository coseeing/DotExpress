import inspect
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from documents.formats import (
    ExportContext,
    build_import_wildcard,
    get_exportable_formats,
    get_format,
    get_importable_formats,
)
from documents.workspace import Document
from dual_view.model import DualViewSegment


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

    def test_export_requires_braille_policy_matches_format(self) -> None:
        self.assertFalse(get_format("dep").requires_braille)
        self.assertTrue(get_format("brl").requires_braille)


if __name__ == "__main__":
    unittest.main()
