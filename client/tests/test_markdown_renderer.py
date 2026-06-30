import unittest

from documents.importers.markdown_ast import (
    BlockQuote,
    DocumentAst,
    Heading,
    HorizontalRule,
    ListBlock,
    ListItem,
    Paragraph,
    Table,
)
from documents.importers.markdown_renderer import render_markdown


class MarkdownRendererTest(unittest.TestCase):
    def test_renders_supported_blocks_with_stable_spacing(self) -> None:
        ast = DocumentAst(
            (
                Heading(2, "Title"),
                Paragraph("Body"),
                ListBlock(
                    ordered=False,
                    items=(
                        ListItem((Paragraph("First"),)),
                        ListItem((Paragraph("Second"), ListBlock(True, (ListItem((Paragraph("Nested"),)),)))),
                    ),
                ),
                BlockQuote((Paragraph("Quoted\nline"),)),
                HorizontalRule(),
                Table(("Name", "A|B"), (("row", "line\nbreak"),)),
            )
        )
        self.assertEqual(
            render_markdown(ast),
            "## Title\n\nBody\n\n"
            "- First\n"
            "- Second\n"
            "  1. Nested\n\n"
            "> Quoted\n"
            "> line\n\n"
            "---\n\n"
            "| Name | A\\|B |\n"
            "| --- | --- |\n"
            "| row | line break |\n",
        )

    def test_empty_document_renders_empty_string(self) -> None:
        self.assertEqual(render_markdown(DocumentAst(())), "")


if __name__ == "__main__":
    unittest.main()
