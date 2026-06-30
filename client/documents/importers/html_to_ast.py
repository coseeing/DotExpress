from __future__ import annotations

from collections.abc import Iterable

from lxml import etree, html

from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table

_HEADING_TAGS = {f"h{level}" for level in range(1, 7)}
_BLOCK_TAGS = _HEADING_TAGS | {"p", "ul", "ol", "blockquote", "hr", "table"}


def _tag(element) -> str:
    return etree.QName(element).localname.casefold()


def _text(element) -> str:
    return " ".join("".join(element.itertext()).split())


def _significant_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split())
    return text if text else None


def _inline_text(element) -> str:
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        tag = _tag(child)
        if tag not in _BLOCK_TAGS:
            parts.append(_inline_text(child))
        if child.tail:
            parts.append(child.tail)
    return " ".join("".join(parts).split())


def _table(element) -> Table | None:
    rows: list[tuple[tuple[str, ...], bool]] = []
    for row in element.xpath(".//*[local-name()='tr']"):
        cells = [cell for cell in row if _tag(cell) in {"th", "td"}]
        if not cells:
            continue
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
    items: list[ListItem] = []
    for child in element:
        if _tag(child) != "li":
            continue
        blocks: list[Block] = []
        buffered_text = _significant_text(child.text)
        if buffered_text:
            blocks.append(Paragraph(_inline_text(child)))
            buffered_text = None
        for nested in child:
            tag = _tag(nested)
            if tag in {"ul", "ol"}:
                blocks.append(_list(nested))
            elif tag == "blockquote":
                blocks.append(BlockQuote(_blocks(nested)))
            elif tag == "hr":
                blocks.append(HorizontalRule())
            elif tag == "table":
                table = _table(nested)
                if table is not None:
                    blocks.append(table)
            elif tag == "p":
                text = _significant_text(_inline_text(nested))
                if text:
                    blocks.append(Paragraph(text))
            elif tag in _HEADING_TAGS:
                text = _significant_text(_inline_text(nested))
                if text:
                    blocks.append(Heading(int(tag[1]), text))
            if nested.tail and _significant_text(nested.tail):
                blocks.append(Paragraph(_significant_text(nested.tail) or ""))
        if not blocks:
            text = _significant_text(_inline_text(child))
            if text:
                blocks.append(Paragraph(text))
        items.append(ListItem(tuple(blocks)))
    return ListBlock(_tag(element) == "ol", tuple(items))


def _blocks(root) -> tuple[Block, ...]:
    blocks: list[Block] = []
    for child in root:
        tag = _tag(child)
        if tag in _HEADING_TAGS:
            text = _significant_text(_inline_text(child))
            if text:
                blocks.append(Heading(int(tag[1]), text))
        elif tag == "p":
            text = _significant_text(_inline_text(child))
            if text:
                blocks.append(Paragraph(text))
        elif tag in {"ul", "ol"}:
            blocks.append(_list(child))
        elif tag == "blockquote":
            blocks.append(BlockQuote(_blocks(child)))
        elif tag == "hr":
            blocks.append(HorizontalRule())
        elif tag == "table":
            table = _table(child)
            if table is not None:
                blocks.append(table)
        elif list(child):
            blocks.extend(_blocks(child))
        elif _significant_text(_inline_text(child)):
            blocks.append(Paragraph(_inline_text(child)))
        if child.tail and _significant_text(child.tail):
            blocks.append(Paragraph(_significant_text(child.tail) or ""))
    return tuple(blocks)


def html_to_ast(source: str | bytes, *, xhtml: bool = False) -> DocumentAst:
    if xhtml:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        data = source.encode("utf-8") if isinstance(source, str) else source
        root = etree.fromstring(data, parser)
        body = root.xpath(".//*[local-name()='body']")
        target = body[0] if body else root
    else:
        text = source.decode("utf-8") if isinstance(source, bytes) else source
        target = html.fragment_fromstring(text, create_parent="main")
    return DocumentAst(_blocks(target))
