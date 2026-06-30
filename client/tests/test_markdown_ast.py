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


class MarkdownAstTest(unittest.TestCase):
    def test_document_accepts_all_supported_block_nodes(self) -> None:
        document = DocumentAst(
            blocks=(
                Heading(1, "Title"),
                Paragraph("Body"),
                ListBlock(False, (ListItem((Paragraph("Item"),)),)),
                BlockQuote((Paragraph("Quote"),)),
                HorizontalRule(),
                Table(("Name", "Value"), (("A", "1"),)),
            )
        )
        self.assertEqual(len(document.blocks), 6)

    def test_heading_rejects_level_outside_one_through_six(self) -> None:
        with self.assertRaisesRegex(ValueError, "between 1 and 6"):
            Heading(0, "Invalid")
        with self.assertRaisesRegex(ValueError, "between 1 and 6"):
            Heading(7, "Invalid")

    def test_table_rejects_rows_with_different_width(self) -> None:
        with self.assertRaisesRegex(ValueError, "same number of columns"):
            Table(("A", "B"), (("only one",),))


if __name__ == "__main__":
    unittest.main()
