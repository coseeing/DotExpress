from __future__ import annotations

from pathlib import Path

from ebooklib import epub

from .base import ImportedDocument, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_ast import DocumentAst
from .markdown_renderer import render_markdown


def import_epub(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".epub")
    book = epub.read_epub(str(source))
    spine = getattr(book, "spine", None)
    if not spine:
        raise ValueError("EPUB does not contain a readable spine.")

    blocks = []
    for item_id, linear in spine:
        if str(linear).casefold() == "no":
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            raise ValueError(f'EPUB spine item "{item_id}" is missing.')
        chapter = html_to_ast(item.get_content(), xhtml=True)
        blocks.extend(chapter.blocks)
    return ImportedDocument(source_name(source), render_markdown(DocumentAst(tuple(blocks))))
