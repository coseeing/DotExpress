# Multi-Format Document Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 PDF、DOCX、EPUB 文件匯入，將可用的 block-level 語意轉成 Markdown；PDF 缺少或無法可靠解析 tagged structure 時只抽取純文字。

**Architecture:** `client/documents/importers/` 封裝格式相依套件，所有 importer 先產生共用 immutable AST，再由單一 renderer 輸出 Markdown。DOCX 與 EPUB 共用 `lxml` HTML/XHTML mapper；PDF 必須先用 `pypdf` 檢查並解析 `/MarkInfo`、`/StructTreeRoot`，語意路徑失敗時才以 PyMuPDF 產生普通 `Paragraph` 節點。workspace 只接收 importer 的 `ImportedDocument`，GUI 不直接依賴解析套件。

**Tech Stack:** Python 3、`unittest`、`dataclasses`、mammoth、EbookLib、lxml、pypdf、PyMuPDF、wxPython、gettext

---

## 檔案配置

- Create: `client/documents/importers/__init__.py` — 匯出公開 importer API。
- Create: `client/documents/importers/base.py` — 定義 `ImportedDocument` 與共用副檔名、名稱處理。
- Create: `client/documents/importers/markdown_ast.py` — 定義 block-level AST。
- Create: `client/documents/importers/markdown_renderer.py` — 集中 Markdown escaping、間距與序列化。
- Create: `client/documents/importers/html_to_ast.py` — 使用 `lxml` 將 HTML/XHTML block elements 映射為 AST。
- Create: `client/documents/importers/docx_importer.py` — `mammoth HTML -> AST -> Markdown`。
- Create: `client/documents/importers/epub_importer.py` — `ebooklib spine XHTML -> AST -> Markdown`。
- Create: `client/documents/importers/pdf_importer.py` — tagged PDF AST 路徑與 PyMuPDF 純文字 fallback。
- Modify: `client/documents/workspace.py` — 依 `format_key` dispatch importer，轉成既有 `Document`。
- Modify: `client/ui/action_menu.py` — 在 Import submenu 加入 PDF、DOCX、EPUB。
- Modify: `client/gui.py` — 新增格式 wildcard mapping，保持既有批次匯入 UI。
- Modify: `client/requirements.txt` — 固定新增解析套件版本。
- Create: `client/tests/test_markdown_ast.py` — AST invariant 測試。
- Create: `client/tests/test_markdown_renderer.py` — Markdown 輸出測試。
- Create: `client/tests/test_html_to_ast.py` — 共用 HTML/XHTML mapping 測試。
- Create: `client/tests/test_docx_importer.py` — mock mammoth 邊界，測試 DOCX pipeline。
- Create: `client/tests/test_epub_importer.py` — mock EbookLib 邊界，測試 spine 順序。
- Create: `client/tests/test_pdf_importer.py` — mock pypdf/PyMuPDF 邊界，測試 tagged/fallback 決策。
- Modify: `client/tests/test_document_workspace.py` — 新格式 dispatch、重名與 BatchIssue 整合測試。
- Modify: `client/tests/test_action_menu.py` — 新 Import submenu 順序測試。
- Modify: `client/locales/dotexpress.pot` — 收錄新 wildcard 字串。
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — 新 wildcard 的繁中翻譯。
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — 編譯更新後 catalog。
- Reference: `docs/superpowers/specs/2026-06-30-multi-format-document-import-design.md`
- Reference: `docs/superpowers/specs/2026-06-30-multi-format-document-import-design_zh-TW.md`

### Task 1: 建立 block-level AST

**Files:**
- Create: `client/documents/importers/__init__.py`
- Create: `client/documents/importers/markdown_ast.py`
- Create: `client/tests/test_markdown_ast.py`

- [ ] **Step 1: 寫 AST invariant 的失敗測試**

```python
# client/tests/test_markdown_ast.py
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
```

- [ ] **Step 2: 執行測試並確認因 module 尚未存在而失敗**

Run: `cd client && python3 -m unittest tests.test_markdown_ast -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'documents.importers'`.

- [ ] **Step 3: 建立 immutable AST 與明確 union**

```python
# client/documents/importers/markdown_ast.py
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class Heading:
    level: int
    text: str

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 6:
            raise ValueError("Heading level must be between 1 and 6.")


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class ListItem:
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class ListBlock:
    ordered: bool
    items: tuple[ListItem, ...]


@dataclass(frozen=True)
class BlockQuote:
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class HorizontalRule:
    pass


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        width = len(self.headers)
        if any(len(row) != width for row in self.rows):
            raise ValueError("Table rows must have the same number of columns as headers.")


Block: TypeAlias = Heading | Paragraph | ListBlock | BlockQuote | HorizontalRule | Table


@dataclass(frozen=True)
class DocumentAst:
    blocks: tuple[Block, ...]
```

```python
# client/documents/importers/__init__.py
"""Semantic document importers."""
```

- [ ] **Step 4: 執行 AST 測試**

Run: `cd client && python3 -m unittest tests.test_markdown_ast -v`

Expected: 3 tests PASS.

- [ ] **Step 5: 提交 AST**

```bash
git add client/documents/importers/__init__.py client/documents/importers/markdown_ast.py client/tests/test_markdown_ast.py
git commit -m "feat: add document import AST"
```

### Task 2: 建立 Markdown renderer

**Files:**
- Create: `client/documents/importers/markdown_renderer.py`
- Create: `client/tests/test_markdown_renderer.py`

- [ ] **Step 1: 寫所有 node、巢狀 block 與 escaping 的失敗測試**

```python
# client/tests/test_markdown_renderer.py
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
```

- [ ] **Step 2: 執行測試並確認 renderer 尚未存在**

Run: `cd client && python3 -m unittest tests.test_markdown_renderer -v`

Expected: FAIL with `ModuleNotFoundError` for `markdown_renderer`.

- [ ] **Step 3: 實作單一 renderer**

```python
# client/documents/importers/markdown_renderer.py
from __future__ import annotations

from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, Paragraph, Table


def _table_cell(text: str) -> str:
    return " ".join(text.splitlines()).replace("|", "\\|").strip()


def _render_list(block: ListBlock, indent: int = 0) -> list[str]:
    lines: list[str] = []
    for index, item in enumerate(block.items, start=1):
        marker = f"{index}." if block.ordered else "-"
        first = True
        for child in item.blocks:
            if isinstance(child, Paragraph):
                child_lines = child.text.splitlines() or [""]
                prefix = " " * indent + marker + " " if first else " " * (indent + 2)
                lines.append(prefix + child_lines[0])
                lines.extend(" " * (indent + 2) + line for line in child_lines[1:])
            elif isinstance(child, ListBlock):
                lines.extend(_render_list(child, indent + 2))
            else:
                rendered = _render_block(child).splitlines()
                prefix = " " * indent + marker + " " if first else " " * (indent + 2)
                if rendered:
                    lines.append(prefix + rendered[0])
                    lines.extend(" " * (indent + 2) + line for line in rendered[1:])
            first = False
    return lines


def _render_block(block: Block) -> str:
    if isinstance(block, Heading):
        return f"{'#' * block.level} {block.text.strip()}"
    if isinstance(block, Paragraph):
        return block.text.strip()
    if isinstance(block, ListBlock):
        return "\n".join(_render_list(block))
    if isinstance(block, BlockQuote):
        content = "\n\n".join(_render_block(child) for child in block.blocks)
        return "\n".join(f"> {line}" if line else ">" for line in content.splitlines())
    if isinstance(block, HorizontalRule):
        return "---"
    if isinstance(block, Table):
        headers = tuple(_table_cell(cell) for cell in block.headers)
        rows = tuple(tuple(_table_cell(cell) for cell in row) for row in block.rows)
        header_line = f"| {' | '.join(headers)} |"
        divider = f"| {' | '.join('---' for _ in headers)} |"
        body = [f"| {' | '.join(row)} |" for row in rows]
        return "\n".join((header_line, divider, *body))
    raise TypeError(f"Unsupported block type: {type(block).__name__}")


def render_markdown(document: DocumentAst) -> str:
    rendered = [_render_block(block) for block in document.blocks]
    nonempty = [block for block in rendered if block]
    joined = "\n\n".join(nonempty)
    return f"{joined}\n" if joined else ""
```

- [ ] **Step 4: 執行 renderer 與 AST 測試**

Run: `cd client && python3 -m unittest tests.test_markdown_ast tests.test_markdown_renderer -v`

Expected: 5 tests PASS.

- [ ] **Step 5: 提交 renderer**

```bash
git add client/documents/importers/markdown_renderer.py client/tests/test_markdown_renderer.py
git commit -m "feat: render import AST as Markdown"
```

### Task 3: 使用 lxml 建立共用 HTML/XHTML mapper

**Files:**
- Create: `client/documents/importers/html_to_ast.py`
- Create: `client/tests/test_html_to_ast.py`
- Modify: `client/requirements.txt`

- [ ] **Step 1: 先加入固定版本依賴**

```text
# client/requirements.txt
EbookLib==0.20
lxml==5.2.2
mammoth==1.11.0
PyMuPDF==1.25.1
pypdf==5.6.0
```

- [ ] **Step 2: 安裝 client requirements**

Run: `python3 -m pip install -r client/requirements.txt`

Expected: command exits 0 and all five importer packages are installed.

- [ ] **Step 3: 寫 block mapping、inline flattening 與 malformed XHTML 測試**

```python
# client/tests/test_html_to_ast.py
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
```

- [ ] **Step 4: 執行測試並確認 mapper 尚未存在**

Run: `cd client && python3 -m unittest tests.test_html_to_ast -v`

Expected: FAIL with `ModuleNotFoundError` for `html_to_ast`.

- [ ] **Step 5: 實作 lxml parser 與 recursive block mapping**

建立以下公開介面與 helper：

```python
# client/documents/importers/html_to_ast.py
from __future__ import annotations

from lxml import etree, html

from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table


def _tag(element) -> str:
    return etree.QName(element).localname.casefold()


def _text(element) -> str:
    return " ".join("".join(element.itertext()).split())


def _table(element) -> Table | None:
    rows = []
    for row in element.xpath(".//*[local-name()='tr']"):
        cells = [cell for cell in row if _tag(cell) in {"th", "td"}]
        if cells:
            rows.append((tuple(_text(cell) for cell in cells), any(_tag(cell) == "th" for cell in cells)))
    if not rows:
        return None
    width = max(len(cells) for cells, _ in rows)
    normalized = [cells + ("",) * (width - len(cells)) for cells, _ in rows]
    header_index = next((index for index, (_, has_th) in enumerate(rows) if has_th), 0)
    headers = normalized[header_index]
    data_rows = tuple(row for index, row in enumerate(normalized) if index != header_index)
    return Table(headers, data_rows)


def _list(element) -> ListBlock:
    items = []
    for child in element:
        if _tag(child) != "li":
            continue
        blocks: list[Block] = []
        direct_text = " ".join(part.strip() for part in child.xpath("./text()") if part.strip())
        if direct_text:
            blocks.append(Paragraph(direct_text))
        for nested in child:
            tag = _tag(nested)
            if tag in {"ul", "ol"}:
                blocks.append(_list(nested))
            elif tag == "p" and _text(nested):
                blocks.append(Paragraph(_text(nested)))
        if not blocks and _text(child):
            blocks.append(Paragraph(_text(child)))
        items.append(ListItem(tuple(blocks)))
    return ListBlock(_tag(element) == "ol", tuple(items))


def _blocks(root) -> tuple[Block, ...]:
    blocks: list[Block] = []
    for element in root.iter():
        tag = _tag(element)
        if any(_tag(ancestor) in {"ul", "ol", "blockquote", "table"} for ancestor in element.iterancestors()):
            continue
        if tag in {f"h{level}" for level in range(1, 7)} and _text(element):
            blocks.append(Heading(int(tag[1]), _text(element)))
        elif tag == "p" and _text(element):
            blocks.append(Paragraph(_text(element)))
        elif tag in {"ul", "ol"}:
            blocks.append(_list(element))
        elif tag == "blockquote":
            blocks.append(BlockQuote(_blocks(element)))
        elif tag == "hr":
            blocks.append(HorizontalRule())
        elif tag == "table":
            table = _table(element)
            if table is not None:
                blocks.append(table)
    return tuple(blocks)


def html_to_ast(source: str | bytes, *, xhtml: bool = False) -> DocumentAst:
    if xhtml:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        root = etree.fromstring(source.encode("utf-8") if isinstance(source, str) else source, parser)
    else:
        root = html.fragment_fromstring(source, create_parent="main")
    return DocumentAst(_blocks(root))
```

實作時以測試為準修正 `blockquote` traversal：`_blocks(element)` 必須處理 root 本身的直接 children，且不得因 blockquote ancestor filter 而回傳空 tuple。保留 strict XHTML parser 的 `resolve_entities=False`、`no_network=True`，不啟用 recover。

- [ ] **Step 6: 執行共用 mapper 測試**

Run: `cd client && python3 -m unittest tests.test_html_to_ast tests.test_markdown_renderer -v`

Expected: 5 tests PASS.

- [ ] **Step 7: 提交依賴與 mapper**

```bash
git add client/requirements.txt client/documents/importers/html_to_ast.py client/tests/test_html_to_ast.py
git commit -m "feat: map HTML blocks to import AST"
```

### Task 4: 實作 DOCX importer

**Files:**
- Create: `client/documents/importers/base.py`
- Create: `client/documents/importers/docx_importer.py`
- Create: `client/tests/test_docx_importer.py`
- Modify: `client/documents/importers/__init__.py`

- [ ] **Step 1: 寫 importer contract、成功、空內容與副檔名測試**

```python
# client/tests/test_docx_importer.py
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from documents.importers.base import ImportedDocument
from documents.importers.docx_importer import import_docx


class DocxImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "lesson.docx"
        self.path.write_bytes(b"docx")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    @patch("documents.importers.docx_importer.mammoth.convert_to_html")
    def test_imports_mammoth_html_as_markdown(self, convert_to_html: Mock) -> None:
        convert_to_html.return_value = Mock(
            value="<h1>Lesson</h1><ul><li>One</li></ul><table><tr><th>A</th></tr><tr><td>1</td></tr></table>",
            messages=[],
        )
        self.assertEqual(
            import_docx(self.path),
            ImportedDocument("lesson", "# Lesson\n\n- One\n\n| A |\n| --- |\n| 1 |\n"),
        )
        self.assertFalse(convert_to_html.call_args.kwargs["external_file_access"])

    @patch("documents.importers.docx_importer.mammoth.convert_to_html")
    def test_empty_conversion_succeeds(self, convert_to_html: Mock) -> None:
        convert_to_html.return_value = Mock(value="", messages=[])
        self.assertEqual(import_docx(self.path), ImportedDocument("lesson", ""))

    def test_rejects_wrong_extension(self) -> None:
        with self.assertRaisesRegex(ValueError, r"must use the \.docx extension"):
            import_docx(self.path.with_suffix(".doc"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試並確認 contract 尚未存在**

Run: `cd client && python3 -m unittest tests.test_docx_importer -v`

Expected: FAIL importing `documents.importers.base`.

- [ ] **Step 3: 實作共用結果與 DOCX pipeline**

```python
# client/documents/importers/base.py
from dataclasses import dataclass
from pathlib import Path

from name_validation import normalize_base_name


@dataclass(frozen=True)
class ImportedDocument:
    name: str
    markdown_text: str


def validate_source(path: Path | str, extension: str) -> Path:
    source = Path(path)
    if source.suffix.casefold() != extension:
        raise ValueError(f"Source document must use the {extension} extension.")
    return source


def source_name(path: Path) -> str:
    return normalize_base_name(path.stem)
```

```python
# client/documents/importers/docx_importer.py
from pathlib import Path

import mammoth

from .base import ImportedDocument, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_renderer import render_markdown


def import_docx(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".docx")
    with source.open("rb") as stream:
        result = mammoth.convert_to_html(
            stream,
            include_embedded_style_map=False,
            external_file_access=False,
        )
    ast = html_to_ast(result.value)
    return ImportedDocument(source_name(source), render_markdown(ast))
```

```python
# client/documents/importers/__init__.py
from .base import ImportedDocument
from .docx_importer import import_docx

__all__ = ["ImportedDocument", "import_docx"]
```

- [ ] **Step 4: 執行 DOCX 與共用 pipeline 測試**

Run: `cd client && python3 -m unittest tests.test_docx_importer tests.test_html_to_ast tests.test_markdown_renderer -v`

Expected: all tests PASS.

- [ ] **Step 5: 提交 DOCX importer**

```bash
git add client/documents/importers/base.py client/documents/importers/docx_importer.py client/documents/importers/__init__.py client/tests/test_docx_importer.py
git commit -m "feat: import DOCX as semantic Markdown"
```

### Task 5: 實作 EPUB spine importer

**Files:**
- Create: `client/documents/importers/epub_importer.py`
- Create: `client/tests/test_epub_importer.py`
- Modify: `client/documents/importers/__init__.py`

- [ ] **Step 1: 寫 spine 順序、linear flag、缺 spine 與壞 XHTML 測試**

```python
# client/tests/test_epub_importer.py
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
```

- [ ] **Step 2: 執行測試並確認 EPUB importer 尚未存在**

Run: `cd client && python3 -m unittest tests.test_epub_importer -v`

Expected: FAIL importing `epub_importer`.

- [ ] **Step 3: 實作以 spine 為唯一順序來源的 importer**

```python
# client/documents/importers/epub_importer.py
from pathlib import Path

from ebooklib import epub

from .base import ImportedDocument, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_ast import DocumentAst
from .markdown_renderer import render_markdown


def import_epub(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".epub")
    book = epub.read_epub(str(source))
    if not book.spine:
        raise ValueError("EPUB does not contain a readable spine.")

    blocks = []
    for item_id, linear in book.spine:
        if str(linear).casefold() == "no":
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            raise ValueError(f'EPUB spine item "{item_id}" is missing.')
        chapter = html_to_ast(item.get_content(), xhtml=True)
        blocks.extend(chapter.blocks)

    return ImportedDocument(source_name(source), render_markdown(DocumentAst(tuple(blocks))))
```

`html_to_ast(..., xhtml=True)` 必須定位 XHTML `<body>` 後再 mapping；若 document 沒有 body，使用 root。章節邊界由 renderer 的 block 間空白行保留，不建立額外 AST node，也不加入 EPUB metadata。

- [ ] **Step 4: 匯出 EPUB API 並執行測試**

```python
# client/documents/importers/__init__.py
from .base import ImportedDocument
from .docx_importer import import_docx
from .epub_importer import import_epub

__all__ = ["ImportedDocument", "import_docx", "import_epub"]
```

Run: `cd client && python3 -m unittest tests.test_epub_importer tests.test_html_to_ast tests.test_markdown_renderer -v`

Expected: all tests PASS.

- [ ] **Step 5: 提交 EPUB importer**

```bash
git add client/documents/importers/epub_importer.py client/documents/importers/__init__.py client/tests/test_epub_importer.py
git commit -m "feat: import EPUB spine as semantic Markdown"
```

### Task 6: 建立 PDF structure inspection 與純文字 fallback

**Files:**
- Create: `client/documents/importers/pdf_importer.py`
- Create: `client/tests/test_pdf_importer.py`

- [ ] **Step 1: 寫 `/MarkInfo`、`/StructTreeRoot` 與 fallback 決策測試**

```python
# client/tests/test_pdf_importer.py
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from documents.importers.base import ImportedDocument
from documents.importers.markdown_ast import DocumentAst, Heading, Paragraph
from documents.importers.pdf_importer import _has_tagged_structure, import_pdf


class PdfImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = Path(self._tmpdir.name) / "paper.pdf"
        self.path.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_tagged_structure_requires_marked_true_and_structure_root(self) -> None:
        self.assertFalse(_has_tagged_structure({}))
        self.assertFalse(_has_tagged_structure({"/MarkInfo": {"/Marked": True}}))
        self.assertFalse(_has_tagged_structure({"/StructTreeRoot": {"/K": []}}))
        self.assertTrue(
            _has_tagged_structure(
                {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/P"}]}}
            )
        )

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_untagged_pdf_uses_plain_text_paragraphs(self, reader_type: Mock, fallback: Mock) -> None:
        reader_type.return_value.trailer = {"/Root": {}}
        fallback.return_value = DocumentAst((Paragraph("Page one"), Paragraph("Page two")))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "Page one\n\nPage two\n"))
        fallback.assert_called_once_with(self.path)

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer._extract_tagged_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_usable_tagged_pdf_uses_semantic_ast(
        self, reader_type: Mock, tagged: Mock, fallback: Mock
    ) -> None:
        root = {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/H1"}]}}
        reader_type.return_value.trailer = {"/Root": root}
        tagged.return_value = DocumentAst((Heading(1, "Tagged title"),))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "# Tagged title\n"))
        fallback.assert_not_called()

    @patch("documents.importers.pdf_importer._extract_plain_text_ast")
    @patch("documents.importers.pdf_importer._extract_tagged_ast")
    @patch("documents.importers.pdf_importer.PdfReader")
    def test_unreliable_tagged_pdf_falls_back_for_entire_file(
        self, reader_type: Mock, tagged: Mock, fallback: Mock
    ) -> None:
        root = {"/MarkInfo": {"/Marked": True}, "/StructTreeRoot": {"/K": [{"/S": "/P"}]}}
        reader_type.return_value.trailer = {"/Root": root}
        tagged.side_effect = ValueError("Tagged PDF reading order is unreliable.")
        fallback.return_value = DocumentAst((Paragraph("Plain"),))
        self.assertEqual(import_pdf(self.path), ImportedDocument("paper", "Plain\n"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試並確認 PDF importer 尚未存在**

Run: `cd client && python3 -m unittest tests.test_pdf_importer -v`

Expected: FAIL importing `pdf_importer`.

- [ ] **Step 3: 實作 catalog dereference、必要檢查與 fallback orchestration**

```python
# client/documents/importers/pdf_importer.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import pymupdf
from pypdf import PdfReader

from .base import ImportedDocument, source_name, validate_source
from .markdown_ast import DocumentAst, Paragraph
from .markdown_renderer import render_markdown


def _resolve(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _has_tagged_structure(catalog: Any) -> bool:
    catalog = _resolve(catalog)
    mark_info = _resolve(catalog.get("/MarkInfo", {}))
    structure = _resolve(catalog.get("/StructTreeRoot"))
    return bool(mark_info.get("/Marked")) and bool(structure) and "/K" in structure


def _extract_plain_text_ast(path: Path) -> DocumentAst:
    paragraphs = []
    with pymupdf.open(path) as document:
        if document.needs_pass:
            raise ValueError("Encrypted PDF cannot be imported.")
        for page in document:
            text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n")
            for part in text.split("\n\n"):
                normalized = "\n".join(line.rstrip() for line in part.splitlines()).strip()
                if normalized:
                    paragraphs.append(Paragraph(normalized))
    return DocumentAst(tuple(paragraphs))


def _extract_tagged_ast(reader: PdfReader, structure_root: Any) -> DocumentAst:
    raise ValueError("Tagged PDF structure mapping is not available.")


def import_pdf(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".pdf")
    reader = PdfReader(str(source))
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF cannot be imported.")
    catalog = _resolve(reader.trailer["/Root"])
    ast = None
    if _has_tagged_structure(catalog):
        try:
            ast = _extract_tagged_ast(reader, _resolve(catalog["/StructTreeRoot"]))
        except (KeyError, TypeError, ValueError):
            ast = None
    if ast is None:
        ast = _extract_plain_text_ast(source)
    return ImportedDocument(source_name(source), render_markdown(ast))
```

此步的 `_extract_tagged_ast` 明確 raise `ValueError`，下一個 task 會以完整 walker 取代此函式；不可把 tagged PDF 永久導向 fallback。

- [ ] **Step 4: 執行 PDF orchestration 測試**

Run: `cd client && python3 -m unittest tests.test_pdf_importer -v`

Expected: 4 tests PASS.

- [ ] **Step 5: 提交 PDF inspection 與 fallback**

```bash
git add client/documents/importers/pdf_importer.py client/tests/test_pdf_importer.py
git commit -m "feat: inspect PDF tags and extract fallback text"
```

### Task 7: 完成 tagged PDF structure-tree mapping

**Files:**
- Modify: `client/documents/importers/pdf_importer.py`
- Modify: `client/tests/test_pdf_importer.py`
- Modify: `client/documents/importers/__init__.py`

- [ ] **Step 1: 加入 structure role、list、table、unsupported flatten 與 reading-order 測試**

測試以小型 fake PDF object graph 驗證以下完整 mapping：

```python
# client/tests/test_pdf_importer.py
    def test_maps_supported_structure_roles_from_mcid_text(self) -> None:
        reader = Mock()
        reader.pages = [Mock()]
        mcid_text = {(0, 1): "Title", (0, 2): "Body", (0, 3): "First"}
        structure = {
            "/K": [
                {"/S": "/H1", "/Pg": reader.pages[0], "/K": 1},
                {"/S": "/P", "/Pg": reader.pages[0], "/K": 2},
                {
                    "/S": "/L",
                    "/Pg": reader.pages[0],
                    "/K": [
                        {"/S": "/LI", "/K": [{"/S": "/Lbl", "/K": []}, {"/S": "/LBody", "/K": 3}]}
                    ],
                },
            ]
        }
        with patch("documents.importers.pdf_importer._extract_mcid_text", return_value=mcid_text):
            self.assertEqual(
                _extract_tagged_ast(reader, structure),
                DocumentAst(
                    (
                        Heading(1, "Title"),
                        Paragraph("Body"),
                        ListBlock(False, (ListItem((Paragraph("First"),)),)),
                    )
                ),
            )

    def test_role_map_alias_is_applied_before_mapping(self) -> None:
        reader = Mock(pages=[Mock()])
        structure = {"/RoleMap": {"/CustomHeading": "/H2"}, "/K": {"/S": "/CustomHeading", "/Pg": reader.pages[0], "/K": 4}}
        with patch("documents.importers.pdf_importer._extract_mcid_text", return_value={(0, 4): "Alias"}):
            self.assertEqual(_extract_tagged_ast(reader, structure), DocumentAst((Heading(2, "Alias"),)))

    def test_missing_mcid_text_rejects_semantic_path(self) -> None:
        reader = Mock(pages=[Mock()])
        structure = {"/K": {"/S": "/P", "/Pg": reader.pages[0], "/K": 99}}
        with patch("documents.importers.pdf_importer._extract_mcid_text", return_value={}):
            with self.assertRaisesRegex(ValueError, "reading order"):
                _extract_tagged_ast(reader, structure)
```

另加入 table fixture，要求 `/Table -> /TR -> /TH|/TD` 產生 `Table`；加入 `/BlockQuote` fixture；加入未知 block role fixture，要求 descendant MCID 可依順序完整取得時降為 `Paragraph`。沒有可靠 MCID text、找不到 page、重複或跨 page 無法排序時，測試必須要求整份 semantic path raise `ValueError`。

- [ ] **Step 2: 執行新增測試並確認 `_extract_tagged_ast` 尚未實作**

Run: `cd client && python3 -m unittest tests.test_pdf_importer -v`

Expected: FAIL because `_extract_tagged_ast` still raises `Tagged PDF structure mapping is not available.`

- [ ] **Step 3: 以 pypdf visitor 建立 `(page_index, MCID) -> text`**

```python
def _extract_mcid_text(reader: PdfReader) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], list[str]] = {}
    for page_index, page in enumerate(reader.pages):
        mcid_stack: list[int | None] = []

        def before(operator, operands, _cm, _tm) -> None:
            if operator == b"BDC":
                properties = _resolve(operands[1]) if len(operands) > 1 else {}
                mcid = properties.get("/MCID") if hasattr(properties, "get") else None
                mcid_stack.append(int(mcid) if mcid is not None else None)
            elif operator == b"BMC":
                mcid_stack.append(None)
            elif operator == b"EMC" and mcid_stack:
                mcid_stack.pop()

        def text_visitor(text, _cm, _tm, _font, _size) -> None:
            if mcid_stack and mcid_stack[-1] is not None and text:
                result.setdefault((page_index, mcid_stack[-1]), []).append(text)

        page.extract_text(visitor_operand_before=before, visitor_text=text_visitor)
    return {key: "".join(parts).strip() for key, parts in result.items() if "".join(parts).strip()}
```

建立 page object identity/indirect reference 到 page index 的 map。Structure `/K` 可能是 integer MCID、`/MCR` dictionary、structure dictionary 或 array；walker 必須逐一 resolve，不可依 dict iteration 順序猜測 reading order。

- [ ] **Step 4: 實作 structure walker 與正式支援的 block roles**

定義並保持以下 helper contract；函式本體依本 step 下方逐項 mapping 規則完成，不保留上一 task 的 raise-only stub：

```python
@dataclass(frozen=True)
class StructureContext:
    role_map: dict[str, str]
    page_indexes: dict[tuple[int, int], int]
    mcid_text: dict[tuple[int, int], str]


def _extract_tagged_ast(reader: PdfReader, structure_root: Any) -> DocumentAst:
    root = _resolve(structure_root)
    context = StructureContext(
        role_map={str(key): str(_resolve(value)) for key, value in _resolve(root.get("/RoleMap", {})).items()},
        page_indexes=_build_page_indexes(reader),
        mcid_text=_extract_mcid_text(reader),
    )
    blocks = _structure_blocks(root.get("/K", []), context, inherited_page=None, active=set())
    if not blocks and context.mcid_text:
        raise ValueError("Tagged PDF reading order is unreliable.")
    return DocumentAst(blocks)
```

`StructureContext` 保存 `role_map`、`page_indexes`、`mcid_text`。Role 先套用 `/RoleMap`，再移除開頭 `/`。只直接映射：

```python
SUPPORTED_ROLES = {
    "H1", "H2", "H3", "H4", "H5", "H6",
    "P", "L", "LI", "Lbl", "LBody",
    "BlockQuote", "Table", "TR", "TH", "TD", "Artifact",
}
```

- `H1` 至 `H6` 產生 `Heading`。
- `P` 產生 `Paragraph`。
- `L` 依 `/ListNumbering` 的 `Decimal`、`UpperRoman`、`LowerRoman`、`UpperAlpha`、`LowerAlpha` 判定 ordered；其餘為 unordered。
- `LI` 忽略 `Lbl` 顯示文字，只將 `LBody` blocks 放入 `ListItem`。
- `BlockQuote` 保留 descendant blocks。
- `Table` 僅接受規則的 `TR` 與等寬 `TH`/`TD` rows；第一個含 `TH` 的 row 為 headers，沒有 `TH` 時第一 row 為 headers。
- `Artifact` 忽略。
- 未支援 role 若 descendant MCID 可依 `/K` 順序完整 flatten，產生一個 `Paragraph`。
- 任一必要 page/MCID 無法解析、表格 reading order 不可靠、或 structure cycle 出現時 raise `ValueError`，由 `import_pdf()` 對整份檔案 fallback。

- [ ] **Step 5: 執行 PDF 完整測試**

Run: `cd client && python3 -m unittest tests.test_pdf_importer -v`

Expected: tagged semantic、untagged fallback、無 heuristic inference 與失敗 fallback 測試全部 PASS。

- [ ] **Step 6: 匯出 PDF API 並執行所有 importer unit tests**

```python
# client/documents/importers/__init__.py
from .base import ImportedDocument
from .docx_importer import import_docx
from .epub_importer import import_epub
from .pdf_importer import import_pdf

__all__ = ["ImportedDocument", "import_docx", "import_epub", "import_pdf"]
```

Run: `cd client && python3 -m unittest tests.test_markdown_ast tests.test_markdown_renderer tests.test_html_to_ast tests.test_docx_importer tests.test_epub_importer tests.test_pdf_importer -v`

Expected: all tests PASS.

- [ ] **Step 7: 提交 tagged PDF support**

```bash
git add client/documents/importers/pdf_importer.py client/documents/importers/__init__.py client/tests/test_pdf_importer.py
git commit -m "feat: map tagged PDF structure to Markdown"
```

### Task 8: 整合 workspace batch import dispatch

**Files:**
- Modify: `client/documents/workspace.py`
- Modify: `client/tests/test_document_workspace.py`

- [ ] **Step 1: 寫新格式 dispatch、重名、錯誤與未知格式測試**

```python
# client/tests/test_document_workspace.py
from unittest.mock import Mock, patch
from documents.importers.base import ImportedDocument

    def test_batch_import_documents_dispatches_semantic_importer(self) -> None:
        source = Path(self._tmpdir.name) / "lesson.docx"
        loader = Mock(return_value=Document("lesson", "# Heading\n", None))
        with patch.dict("documents.workspace.IMPORT_LOADERS", {"docx": loader}, clear=False):
            documents, issues = batch_import_documents(
                [source], format_key="docx", existing_names=set()
            )

        self.assertEqual(documents, [Document("lesson", "# Heading\n", None)])
        self.assertEqual(issues, [])
        loader.assert_called_once_with(source)

    def test_batch_import_documents_rejects_unknown_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported import format"):
            batch_import_documents([], format_key="rtf", existing_names=set())
```

保留並擴充既有 duplicate 與 invalid file tests，分別讓 mock importer 回傳重名的 `ImportedDocument` 及 raise `ValueError("corrupt document")`，確認輸出仍是既有 `BatchIssue(path, reason)`。

- [ ] **Step 2: 執行 workspace 測試並確認新 dispatch 尚未存在**

Run: `cd client && python3 -m unittest tests.test_document_workspace -v`

Expected: FAIL because `IMPORT_LOADERS` and new format dispatch do not exist.

- [ ] **Step 3: 建立明確 loader registry 與 adapter**

```python
# client/documents/workspace.py
from collections.abc import Callable

from documents.importers import ImportedDocument, import_docx, import_epub, import_pdf

ImportResultLoader = Callable[[Path | str], ImportedDocument]
DocumentLoader = Callable[[Path | str], Document]


def _load_imported_document(path: Path | str, importer: ImportResultLoader) -> Document:
    imported = importer(path)
    return Document(name=imported.name, text=imported.markdown_text, braille=None)


IMPORT_LOADERS: dict[str, DocumentLoader] = {
    "dep": load_document_package,
    "txt": load_text_document,
    "docx": lambda path: _load_imported_document(path, import_docx),
    "epub": lambda path: _load_imported_document(path, import_epub),
    "pdf": lambda path: _load_imported_document(path, import_pdf),
}
```

在 `batch_import_documents()` 進入 loop 前以 `IMPORT_LOADERS.get(format_key.casefold())` 取 loader，找不到就 raise `ValueError(f'Unsupported import format: "{format_key}".')`。所有 registry loader 統一回傳 `Document`；`DEP`/`TXT` 的 loader 不改動，新格式經 `_load_imported_document()` adapter 轉換。排序、單檔 exception 收集與 case-insensitive duplicate 規則保持原樣。

- [ ] **Step 4: 執行 workspace 與 importer tests**

Run: `cd client && python3 -m unittest tests.test_document_workspace tests.test_docx_importer tests.test_epub_importer tests.test_pdf_importer -v`

Expected: all tests PASS.

- [ ] **Step 5: 提交 workspace integration**

```bash
git add client/documents/workspace.py client/tests/test_document_workspace.py
git commit -m "feat: dispatch multi-format document imports"
```

### Task 9: 擴充選單、wildcard 與翻譯

**Files:**
- Modify: `client/ui/action_menu.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_action_menu.py`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: 更新選單測試期待值**

```python
# client/tests/test_action_menu.py
                ("submenu", "Import", ["DEP", "TXT", "PDF", "DOCX", "EPUB"]),
```

另加入：

```python
    def test_document_import_format_labels_include_semantic_formats(self) -> None:
        from ui.action_menu import get_document_import_format_labels
        self.assertEqual(get_document_import_format_labels(), ["DEP", "TXT", "PDF", "DOCX", "EPUB"])
```

- [ ] **Step 2: 執行 action menu 測試並確認舊格式列表造成失敗**

Run: `cd client && python3 -m unittest tests.test_action_menu -v`

Expected: FAIL showing only `DEP` and `TXT`.

- [ ] **Step 3: 更新共用 menu descriptor**

```python
# client/ui/action_menu.py
    DocumentMenuItem("submenu", "Import", "import", ("DEP", "TXT", "PDF", "DOCX", "EPUB")),

def get_document_import_format_labels() -> list[str]:
    return ["DEP", "TXT", "PDF", "DOCX", "EPUB"]
```

- [ ] **Step 4: 以 mapping 取代 GUI 二分 wildcard 判斷**

```python
# client/gui.py, constants near existing wildcard constants
PDF_WILDCARD = "PDF files (*.pdf)|*.pdf"
DOCX_WILDCARD = "Word documents (*.docx)|*.docx"
EPUB_WILDCARD = "EPUB books (*.epub)|*.epub"

IMPORT_WILDCARDS = {
    "dep": DEP_WILDCARD,
    "txt": TXT_WILDCARD,
    "pdf": PDF_WILDCARD,
    "docx": DOCX_WILDCARD,
    "epub": EPUB_WILDCARD,
}
```

```python
# client/gui.py
    def _get_import_wildcard(self, format_key: str) -> str:
        try:
            return _(IMPORT_WILDCARDS[format_key])
        except KeyError as exc:
            raise ValueError(f'Unsupported import format: "{format_key}".') from exc
```

在 `on_import_document()` 使用 `wildcard = self._get_import_wildcard(format_key)`。既有 `_get_dep_wildcard()`、`_get_txt_wildcard()` 保留給 export 或其他 caller，不重寫 export 流程。

- [ ] **Step 5: 更新 gettext template 與繁中翻譯**

新增以下 msgid/msgstr：

```po
msgid "PDF files (*.pdf)|*.pdf"
msgstr "PDF 檔案 (*.pdf)|*.pdf"

msgid "Word documents (*.docx)|*.docx"
msgstr "Word 文件 (*.docx)|*.docx"

msgid "EPUB books (*.epub)|*.epub"
msgstr "EPUB 電子書 (*.epub)|*.epub"
```

Run on Windows: `scripts\generate-pot.bat`

Expected: `client/locales/dotexpress.pot` contains all three new msgids.

- [ ] **Step 6: 編譯並驗證 catalog**

Run: `msgfmt --check client/locales/zh_TW/LC_MESSAGES/dotexpress.po -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

Expected: command exits 0 without format errors. 若目前平台沒有 `msgfmt`，必須在有 gettext 的 Windows build 環境執行；不得提交與 `.po` 不一致的舊 `.mo`。

- [ ] **Step 7: 執行選單與 workspace tests**

Run: `cd client && python3 -m unittest tests.test_action_menu tests.test_document_workspace -v`

Expected: all tests PASS.

- [ ] **Step 8: 提交 UI 與 localization**

```bash
git add client/ui/action_menu.py client/gui.py client/tests/test_action_menu.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: expose multi-format document import"
```

### Task 10: 加入真實格式 smoke fixtures 並完成回歸驗證

**Files:**
- Create: `client/tests/fixtures/import/sample.docx`
- Create: `client/tests/fixtures/import/sample.epub`
- Create: `client/tests/fixtures/import/untagged.pdf`
- Create: `client/tests/fixtures/import/tagged.pdf`
- Create: `client/tests/test_import_fixtures.py`

- [ ] **Step 1: 建立最小、可重現且無版權內容的 fixtures**

`sample.docx` 必須含 Heading 1、兩項 unordered list、blockquote style、horizontal rule 對應 style 與 2x2 table。`sample.epub` 必須含兩個 linear spine XHTML，順序與檔名順序相反。`untagged.pdf` 必須只有兩段文字且 catalog 無 `/StructTreeRoot`。`tagged.pdf` 必須同時含 `/MarkInfo << /Marked true >>`、`/StructTreeRoot`、H1/P 的 MCID marked content。

Fixtures 以 LibreOffice/Word、EbookLib 與支援 tagged PDF 的產生工具建立後提交 binary；測試不依賴 fixture 生成工具。

- [ ] **Step 2: 寫 end-to-end smoke tests**

```python
# client/tests/test_import_fixtures.py
import unittest
from pathlib import Path

from documents.importers import import_docx, import_epub, import_pdf

FIXTURES = Path(__file__).parent / "fixtures" / "import"


class ImportFixturesTest(unittest.TestCase):
    def test_docx_fixture_preserves_block_semantics(self) -> None:
        result = import_docx(FIXTURES / "sample.docx")
        self.assertIn("# Sample", result.markdown_text)
        self.assertIn("- First", result.markdown_text)
        self.assertIn("> Quote", result.markdown_text)
        self.assertIn("| Name | Value |", result.markdown_text)

    def test_epub_fixture_follows_spine_order(self) -> None:
        result = import_epub(FIXTURES / "sample.epub")
        self.assertLess(result.markdown_text.index("# First"), result.markdown_text.index("# Second"))

    def test_untagged_pdf_outputs_plain_paragraphs_without_inference(self) -> None:
        result = import_pdf(FIXTURES / "untagged.pdf")
        self.assertIn("Plain first paragraph", result.markdown_text)
        self.assertNotIn("# ", result.markdown_text)
        self.assertNotIn("| --- |", result.markdown_text)

    def test_tagged_pdf_preserves_heading_and_paragraph(self) -> None:
        result = import_pdf(FIXTURES / "tagged.pdf")
        self.assertEqual(result.markdown_text, "# Tagged heading\n\nTagged paragraph\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 執行 smoke tests**

Run: `cd client && python3 -m unittest tests.test_import_fixtures -v`

Expected: 4 tests PASS. Tagged PDF 測試若 fallback 成純文字必須視為 FAIL，不能放寬 assertion。

- [ ] **Step 4: 執行完整 client test suite**

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: all non-platform-skipped client tests PASS;只允許既有、明確標記的 Windows/liblouis skip。

- [ ] **Step 5: 執行 syntax 與依賴 smoke check**

Run: `python3 -m compileall -q client`

Expected: command exits 0.

Run: `python3 -c "import ebooklib, fitz, lxml, mammoth, pypdf; print('import dependencies ok')"`

Expected: prints `import dependencies ok`.

- [ ] **Step 6: 在 Windows 手動驗證 GUI**

啟動 DotExpress，確認 File 與文件列表 Actions 的 Import submenu 都依序顯示 `DEP`, `TXT`, `PDF`, `DOCX`, `EPUB`。每種新格式各匯入一個 fixture，確認文件名稱取自 stem、Markdown 顯示在 source editor、braille 保持 pending 並在既有 save/convert 流程處理；再混合選取一個有效與一個損壞檔，確認有效檔仍匯入且損壞檔出現在 `Import Issues`。

- [ ] **Step 7: 提交 smoke fixtures 與最終測試**

```bash
git add client/tests/fixtures/import client/tests/test_import_fixtures.py
git commit -m "test: cover multi-format import fixtures"
```

- [ ] **Step 8: 檢查最終 diff 範圍**

Run: `git status --short`

Expected: plan implementation files clean；既有未追蹤 `ref/` 保持未加入版本控制。

Run: `git diff --check`

Expected: no whitespace errors.
