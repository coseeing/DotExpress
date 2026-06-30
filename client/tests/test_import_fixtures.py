import gettext
import unittest
from pathlib import Path

from documents.importers.docx_importer import import_docx
from documents.importers.epub_importer import import_epub
from documents.importers.pdf_importer import import_pdf


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "import"
LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"


class ImportFixtureSmokeTest(unittest.TestCase):
    def test_docx_fixture_imports_end_to_end(self) -> None:
        self.assertEqual(
            import_docx(FIXTURE_DIR / "fixture.docx").markdown_text,
            "# Fixture Title\n\n- List item\n\n> Quoted text\n>\n> Intense quote\n\n---\n\n| Head | Value |\n| --- | --- |\n| A | 1 |\n",
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
            "# Tagged fixture title\n\nTagged fixture body.\n",
        )

    def test_zh_tw_catalog_loads_import_wildcard_translations(self) -> None:
        translation = gettext.translation("dotexpress", localedir=str(LOCALE_DIR), languages=["zh_TW"])

        self.assertEqual(translation.gettext("PDF files (*.pdf)|*.pdf"), "PDF 檔案 (*.pdf)|*.pdf")
        self.assertEqual(translation.gettext("Word documents (*.docx)|*.docx"), "Word 文件 (*.docx)|*.docx")
        self.assertEqual(translation.gettext("EPUB books (*.epub)|*.epub"), "EPUB 電子書 (*.epub)|*.epub")


if __name__ == "__main__":
    unittest.main()
