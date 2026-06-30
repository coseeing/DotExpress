from __future__ import annotations

from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _table_cell(text: str) -> str:
    return " ".join(_normalize_text(text).split()).replace("|", "\\|")


def _render_block_lines(block: Block) -> list[str]:
    if isinstance(block, Heading):
        text = _normalize_text(block.text)
        return [f"{'#' * block.level} {text}"] if text else []
    if isinstance(block, Paragraph):
        text = _normalize_text(block.text)
        return text.splitlines() if text else []
    if isinstance(block, HorizontalRule):
        return ["---"]
    if isinstance(block, Table):
        headers = [_table_cell(cell) for cell in block.headers]
        rows = [[_table_cell(cell) for cell in row] for row in block.rows]
        divider = ["---" for _ in headers]
        rendered = [f"| {' | '.join(headers)} |", f"| {' | '.join(divider)} |"]
        rendered.extend(f"| {' | '.join(row)} |" for row in rows)
        return rendered
    if isinstance(block, BlockQuote):
        child_lines: list[str] = []
        for child in block.blocks:
            lines = _render_block_lines(child)
            if child_lines and lines:
                child_lines.append("")
            child_lines.extend(lines)
        return [f"> {line}" if line else ">" for line in child_lines]
    if isinstance(block, ListBlock):
        return _render_list(block)
    raise TypeError(f"Unsupported block type: {type(block).__name__}")


def _render_list(block: ListBlock, indent: int = 0) -> list[str]:
    lines: list[str] = []
    continuation_prefix = " " * (indent + 2)
    for index, item in enumerate(block.items, start=1):
        marker = f"{index}." if block.ordered else "-"
        item_prefix = " " * indent + marker + " "
        rendered_item: list[str] = []
        first_line = True
        for child in item.blocks:
            child_lines = _render_block_lines(child)
            if not child_lines:
                continue
            if first_line:
                rendered_item.append(item_prefix + child_lines[0])
                rendered_item.extend(continuation_prefix + line for line in child_lines[1:])
                first_line = False
                continue
            if isinstance(child, ListBlock):
                rendered_item.extend(continuation_prefix + line for line in child_lines)
            else:
                rendered_item.append(continuation_prefix + child_lines[0])
                rendered_item.extend(continuation_prefix + line for line in child_lines[1:])
        if rendered_item:
            lines.extend(rendered_item)
    return lines


def render_markdown(document: DocumentAst) -> str:
    rendered_blocks = [lines for block in document.blocks if (lines := _render_block_lines(block))]
    if not rendered_blocks:
        return ""
    return "\n\n".join("\n".join(lines) for lines in rendered_blocks) + "\n"
