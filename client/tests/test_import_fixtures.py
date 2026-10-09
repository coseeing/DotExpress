import gettext
import unittest
from pathlib import Path

from documents.formats import build_import_wildcard
from documents.importers.docx_importer import import_docx
from documents.importers.epub_importer import import_epub
from documents.importers.pdf_importer import import_pdf


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "import"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"


class ImportFixtureSmokeTest(unittest.TestCase):
    def test_docx_fixture_imports_end_to_end(self) -> None:
        self.assertEqual(
            import_docx(FIXTURE_DIR / "fixture.docx").markdown_text,
            "# Fixture Title\n\n- List item\n\nQuoted text\n\nIntense quote\n\n| Head | Value |\n| --- | --- |\n| A | 1 |\n",
        )

    def test_epub_fixture_imports_end_to_end(self) -> None:
        self.assertEqual(
            import_epub(FIXTURE_DIR / "fixture.epub").markdown_text,
            "# Spine First\n\n- First bullet\n\n> Second chapter quote.\n\n| Name | Value |\n| --- | --- |\n| B | 2 |\n",
        )

    def test_untagged_pdf_fixture_imports_as_plain_text(self) -> None:
        self.assertEqual(
            import_pdf(FIXTURE_DIR / "fixture-untagged.pdf").markdown_text,
            "Fixture plain paragraph.\n",
        )

    def test_tagged_pdf_fixture_imports_using_semantic_path(self) -> None:
        self.assertEqual(
            import_pdf(FIXTURE_DIR / "fixture-tagged.pdf").markdown_text,
            "Tagged fixture title\nTagged fixture body.\n",
        )

    def test_zh_tw_catalog_loads_import_wildcard_translations(self) -> None:
        translation = gettext.translation("dotexpress", localedir=str(LOCALE_DIR), languages=["zh_TW"])

        # The import dialog builds its filters from the format labels; the old
        # "PDF files (*.pdf)|*.pdf"-style msgids are obsolete since P1-2.
        self.assertEqual(
            build_import_wildcard(translation.gettext),
            "DEP (*.dep)|*.dep|DOCX (*.docx)|*.docx|EPUB (*.epub)|*.epub|PDF (*.pdf)|*.pdf|TXT (*.txt)|*.txt|"
            "所有支援的檔案 (*.dep;*.docx;*.epub;*.pdf;*.txt)|*.dep;*.docx;*.epub;*.pdf;*.txt",
        )


if __name__ == "__main__":
    unittest.main()
