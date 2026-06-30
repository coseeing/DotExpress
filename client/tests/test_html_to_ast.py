import unittest

from lxml import etree

from documents.importers.html_to_ast import html_to_ast
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


class HtmlToAstTest(unittest.TestCase):
    def test_maps_supported_blocks_and_flattens_inline_content(self) -> None:
        source = """
        <main>
          <h1>Book <em>title</em></h1>
          <p>Hello <a href="/ignored">reader</a>.</p>
          <ul><li>One</li><li><p>Two</p><ol><li>Nested</li></ol></li></ul>
          <blockquote><p>Quote</p></blockquote>
          <hr/>
          <table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
        </main>
        """
        self.assertEqual(
            html_to_ast(source),
            DocumentAst(
                (
                    Heading(1, "Book title"),
                    Paragraph("Hello reader."),
                    ListBlock(
                        False,
                        (
                            ListItem((Paragraph("One"),)),
                            ListItem(
                                (
                                    Paragraph("Two"),
                                    ListBlock(True, (ListItem((Paragraph("Nested"),)),)),
                                )
                            ),
                        ),
                    ),
                    BlockQuote((Paragraph("Quote"),)),
                    HorizontalRule(),
                    Table(("A", "B"), (("1", "2"),)),
                )
            ),
        )

    def test_uses_first_row_as_headers_when_table_has_only_td_cells(self) -> None:
        self.assertEqual(
            html_to_ast("<table><tr><td>A</td></tr><tr><td>1</td></tr></table>"),
            DocumentAst((Table(("A",), (("1",),)),)),
        )

    def test_strict_xhtml_rejects_malformed_xml(self) -> None:
        with self.assertRaises(etree.XMLSyntaxError):
            html_to_ast("<html><body><p>broken</body></html>", xhtml=True)


if __name__ == "__main__":
    unittest.main()
