from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING

from dual_view.html import render_dual_view_html
from dual_view.model import build_dual_view_model

if TYPE_CHECKING:
    from documents.importers import ImportedDocument


DEP_EXTENSION = ".dep"
BRL_EXTENSION = ".brl"
HTML_EXTENSION = ".html"
ALL_SUPPORTED_FILTER_KEY = "all"


@dataclass(frozen=True)
class DocumentFormatDescriptor:
    key: str
    extension: str
    wildcard_label: str
    loader: Callable[[Path | str], object] | None
    writer: Callable[[Path | str, object], object] | None
    requires_braille: bool
    importable: bool
    exportable: bool


def _load_imported_document(
    path: Path | str,
    importer: Callable[[Path | str], ImportedDocument],
) -> object:
    imported = importer(path)
    from documents.workspace import Document

    return Document(name=imported.name, text=imported.markdown_text, braille=None)


def _load_docx(path: Path | str) -> object:
    from documents.importers import import_docx

    return _load_imported_document(path, import_docx)


def _load_epub(path: Path | str) -> object:
    from documents.importers import import_epub

    return _load_imported_document(path, import_epub)


def _load_pdf(path: Path | str) -> object:
    from documents.importers import import_pdf

    return _load_imported_document(path, import_pdf)


def _load_txt(path: Path | str) -> object:
    from documents.workspace import load_text_document

    return load_text_document(path)


def _load_dep(path: Path | str) -> object:
    from documents.workspace import load_document_package

    return load_document_package(path)


def _write_dep(path: Path | str, document: object) -> object:
    from documents.workspace import save_document_package

    return save_document_package(path, document, include_pending_metadata=False)


def _write_brl(path: Path | str, document: object) -> object:
    from documents.workspace import export_document_brl

    return export_document_brl(path, document)


def _write_html(
    path: Path | str,
    document: object,
    *,
    dual_view_results: tuple[object, ...] = (),
) -> object:
    del document
    html = render_dual_view_html(build_dual_view_model(dual_view_results))
    return Path(path).write_text(html, encoding="utf-8")


DOCUMENT_FORMATS: tuple[DocumentFormatDescriptor, ...] = (
    DocumentFormatDescriptor(
        key="dep",
        extension=DEP_EXTENSION,
        wildcard_label="DEP",
        loader=_load_dep,
        writer=_write_dep,
        requires_braille=False,
        importable=True,
        exportable=True,
    ),
    DocumentFormatDescriptor(
        key="docx",
        extension=".docx",
        wildcard_label="DOCX",
        loader=_load_docx,
        writer=None,
        requires_braille=False,
        importable=True,
        exportable=False,
    ),
    DocumentFormatDescriptor(
        key="epub",
        extension=".epub",
        wildcard_label="EPUB",
        loader=_load_epub,
        writer=None,
        requires_braille=False,
        importable=True,
        exportable=False,
    ),
    DocumentFormatDescriptor(
        key="pdf",
        extension=".pdf",
        wildcard_label="PDF",
        loader=_load_pdf,
        writer=None,
        requires_braille=False,
        importable=True,
        exportable=False,
    ),
    DocumentFormatDescriptor(
        key="txt",
        extension=".txt",
        wildcard_label="TXT",
        loader=_load_txt,
        writer=None,
        requires_braille=False,
        importable=True,
        exportable=False,
    ),
    DocumentFormatDescriptor(
        key="brl",
        extension=BRL_EXTENSION,
        wildcard_label="BRL",
        loader=None,
        writer=_write_brl,
        requires_braille=True,
        importable=False,
        exportable=True,
    ),
    DocumentFormatDescriptor(
        key="html",
        extension=HTML_EXTENSION,
        wildcard_label="HTML",
        loader=None,
        writer=_write_html,
        requires_braille=False,
        importable=False,
        exportable=True,
    ),
)

_FORMAT_BY_KEY = {descriptor.key: descriptor for descriptor in DOCUMENT_FORMATS}


def get_format(key: str) -> DocumentFormatDescriptor:
    try:
        return _FORMAT_BY_KEY[key.casefold()]
    except KeyError as exc:
        raise ValueError(f'Unsupported document format: "{key}".') from exc


def get_importable_formats() -> tuple[DocumentFormatDescriptor, ...]:
    return tuple(descriptor for descriptor in DOCUMENT_FORMATS if descriptor.importable)


ALL_SUPPORTED_FILTER_INDEX = len(get_importable_formats())


def get_exportable_formats() -> tuple[DocumentFormatDescriptor, ...]:
    return tuple(descriptor for descriptor in DOCUMENT_FORMATS if descriptor.exportable)


def build_import_wildcard(translate=lambda value: value) -> str:
    parts: list[str] = []
    for descriptor in get_importable_formats():
        parts.extend(
            (
                f"{translate(descriptor.wildcard_label)} (*{descriptor.extension})",
                f"*{descriptor.extension}",
            )
        )
    all_patterns = ";".join(f"*{descriptor.extension}" for descriptor in get_importable_formats())
    parts.extend((f"{translate('All Supported Files')} ({all_patterns})", all_patterns))
    return "|".join(parts)


def get_import_filter_labels() -> list[str]:
    return [descriptor.wildcard_label for descriptor in get_importable_formats()] + ["All Supported Files"]


def get_import_wildcard_text() -> str:
    return build_import_wildcard()


def get_format_keys(importable: bool | None = None) -> tuple[str, ...]:
    if importable is None:
        return tuple(descriptor.key for descriptor in DOCUMENT_FORMATS)
    return tuple(
        descriptor.key
        for descriptor in DOCUMENT_FORMATS
        if descriptor.importable == importable
    )


def get_supported_import_filter_keys() -> tuple[str, ...]:
    return get_format_keys(importable=True)
