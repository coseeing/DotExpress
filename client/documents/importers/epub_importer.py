from __future__ import annotations

from pathlib import Path

from ebooklib import epub

from i18n import N_

from .base import ImportedDocument, ImportProblem, source_name, validate_source
from .html_to_ast import html_to_ast
from .markdown_ast import DocumentAst
from .markdown_renderer import render_markdown

# One reason for both problems: the spine item id means nothing to a user (F-12 D3).
_DAMAGED_EPUB = N_("The EPUB file is damaged or has no readable content.")


def import_epub(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".epub")
    book = epub.read_epub(str(source))
    spine = getattr(book, "spine", None)
    if not spine:
        raise ImportProblem("EPUB does not contain a readable spine.", _DAMAGED_EPUB)

    blocks = []
    for item_id, linear in spine:
        if str(linear).casefold() == "no":
            continue
        item = book.get_item_with_id(item_id)
        if item is None:
            raise ImportProblem(f'EPUB spine item "{item_id}" is missing.', _DAMAGED_EPUB)
        chapter = html_to_ast(item.get_content(), xhtml=True)
        blocks.extend(chapter.blocks)
    return ImportedDocument(source_name(source), render_markdown(DocumentAst(tuple(blocks))))
