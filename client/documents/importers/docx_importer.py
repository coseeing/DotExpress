from __future__ import annotations

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
