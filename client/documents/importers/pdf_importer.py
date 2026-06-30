from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
from pypdf import PdfReader

from .base import ImportedDocument, source_name, validate_source
from .markdown_ast import Block, BlockQuote, DocumentAst, Heading, HorizontalRule, ListBlock, ListItem, Paragraph, Table
from .markdown_renderer import render_markdown

SUPPORTED_ROLES = {
    "H1",
    "H2",
    "H3",
    "H4",
    "H5",
    "H6",
    "P",
    "L",
    "LI",
    "Lbl",
    "LBody",
    "BlockQuote",
    "Table",
    "TR",
    "TH",
    "TD",
    "Artifact",
}

ORDERED_LIST_NUMBERING = {"Decimal", "UpperRoman", "LowerRoman", "UpperAlpha", "LowerAlpha"}


@dataclass(frozen=True)
class StructureContext:
    role_map: dict[str, str]
    page_indexes: dict[Any, int]
    mcid_text: dict[tuple[int, int], str]


def _resolve(value: Any) -> Any:
    get_object = getattr(value, "get_object", None)
    if callable(get_object) and type(value).__module__ != "unittest.mock":
        return get_object()
    return value


def _normalize_role(role: Any, context: StructureContext) -> str:
    value = str(_resolve(role))
    value = context.role_map.get(value, value)
    return value.lstrip("/")


def _children(node: Any) -> list[Any]:
    node = _resolve(node)
    if not hasattr(node, "get"):
        return []
    value = _resolve(node.get("/K", []))
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _page_for(node: Any, context: StructureContext, inherited_page: Any | None) -> Any | None:
    node = _resolve(node)
    if hasattr(node, "get") and node.get("/Pg") is not None:
        return _resolve(node.get("/Pg"))
    return inherited_page


def _page_index(page: Any, context: StructureContext) -> int:
    for key, index in context.page_indexes.items():
        if key is page or key == page or key == id(page):
            return index
    raise ValueError("Tagged PDF reading order is unreliable.")


def _build_page_indexes(reader: PdfReader) -> dict[Any, int]:
    page_indexes: dict[Any, int] = {}
    for index, page in enumerate(reader.pages):
        page_indexes[page] = index
        page_indexes[id(page)] = index
    return page_indexes


def _extract_mcid_text(reader: PdfReader) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], list[str]] = {}
    for page_index, page in enumerate(reader.pages):
        stack: list[int | None] = []

        def before(operator, operands, _cm, _tm) -> None:
            if operator == b"BDC":
                properties = _resolve(operands[1]) if len(operands) > 1 else {}
                mcid = properties.get("/MCID") if hasattr(properties, "get") else None
                stack.append(int(mcid) if mcid is not None else None)
            elif operator == b"BMC":
                stack.append(None)
            elif operator == b"EMC" and stack:
                stack.pop()

        def text_visitor(text, _cm, _tm, _font, _size) -> None:
            if stack and stack[-1] is not None and text:
                result.setdefault((page_index, stack[-1]), []).append(text)

        page.extract_text(visitor_operand_before=before, visitor_text=text_visitor)
    return {key: "".join(parts).strip() for key, parts in result.items() if "".join(parts).strip()}


def _mcid_text_for(page: Any, mcid: int, context: StructureContext) -> str:
    page_index = _page_index(page, context)
    try:
        return context.mcid_text[(page_index, int(mcid))]
    except KeyError as exc:
        raise ValueError("Tagged PDF reading order is unreliable.") from exc


def _flatten_text(item: Any, context: StructureContext, inherited_page: Any | None, active: set[int]) -> str:
    item = _resolve(item)
    if item is None:
        return ""
    if isinstance(item, (str, bytes)):
        return str(item)
    if isinstance(item, (int,)):
        if inherited_page is None:
            raise ValueError("Tagged PDF reading order is unreliable.")
        return _mcid_text_for(inherited_page, int(item), context)
    if isinstance(item, (list, tuple)):
        return "".join(_flatten_text(child, context, inherited_page, active) for child in item)
    if not hasattr(item, "get"):
        return ""
    obj_id = id(item)
    if obj_id in active:
        raise ValueError("Tagged PDF structure cycle detected.")
    active.add(obj_id)
    try:
        if item.get("/Type") == "/MCR":
            page = _page_for(item, context, inherited_page)
            mcid = item.get("/MCID")
            if page is None or mcid is None:
                raise ValueError("Tagged PDF reading order is unreliable.")
            return _mcid_text_for(page, int(mcid), context)
        page = _page_for(item, context, inherited_page)
        parts = [_flatten_text(child, context, page, active) for child in _children(item)]
        return "".join(parts)
    finally:
        active.remove(obj_id)


def _flatten_blocks(item: Any, context: StructureContext, inherited_page: Any | None, active: set[int]) -> tuple[Block, ...]:
    item = _resolve(item)
    if item is None:
        return ()
    if isinstance(item, (list, tuple)):
        blocks: list[Block] = []
        for child in item:
            blocks.extend(_flatten_blocks(child, context, inherited_page, active))
        return tuple(blocks)
    if isinstance(item, (int, str, bytes)) or not hasattr(item, "get"):
        text = _flatten_text(item, context, inherited_page, active).strip()
        return (Paragraph(text),) if text else ()

    obj_id = id(item)
    if obj_id in active:
        raise ValueError("Tagged PDF structure cycle detected.")
    active.add(obj_id)
    try:
        role = _normalize_role(item.get("/S"), context) if item.get("/S") is not None else ""
        page = _page_for(item, context, inherited_page)
        if role in {"H1", "H2", "H3", "H4", "H5", "H6"}:
            text = " ".join(_flatten_text(_children(item), context, page, active).split())
            return (Heading(int(role[1]), text),) if text else ()
        if role == "P":
            text = " ".join(_flatten_text(_children(item), context, page, active).split())
            return (Paragraph(text),) if text else ()
        if role == "Artifact":
            return ()
        if role == "BlockQuote":
            return (BlockQuote(_flatten_blocks(_children(item), context, page, active)),)
        if role == "L":
            ordered = str(_resolve(item.get("/ListNumbering", ""))).lstrip("/") in ORDERED_LIST_NUMBERING
            items: list[ListItem] = []
            for child in _children(item):
                child_role = _normalize_role(child.get("/S"), context) if hasattr(child, "get") and child.get("/S") is not None else ""
                if child_role != "LI":
                    continue
                blocks: list[Block] = []
                for li_child in _children(child):
                    li_role = _normalize_role(li_child.get("/S"), context) if hasattr(li_child, "get") and li_child.get("/S") is not None else ""
                    if li_role == "Lbl":
                        continue
                    if li_role == "LBody":
                        blocks.extend(_flatten_blocks(li_child, context, _page_for(li_child, context, page), active))
                    else:
                        blocks.extend(_flatten_blocks(li_child, context, _page_for(li_child, context, page), active))
                if blocks:
                    items.append(ListItem(tuple(blocks)))
            return (ListBlock(ordered, tuple(items)),) if items else ()
        if role == "Table":
            rows: list[tuple[list[str], bool]] = []
            for row in _children(item):
                row_role = _normalize_role(row.get("/S"), context) if hasattr(row, "get") and row.get("/S") is not None else ""
                if row_role != "TR":
                    continue
                cells: list[str] = []
                has_th = False
                for cell in _children(row):
                    cell_role = _normalize_role(cell.get("/S"), context) if hasattr(cell, "get") and cell.get("/S") is not None else ""
                    if cell_role not in {"TH", "TD"}:
                        continue
                    has_th = has_th or cell_role == "TH"
                    text = " ".join(_flatten_text(_children(cell), context, _page_for(cell, context, page), active).split())
                    cells.append(text)
                if cells:
                    rows.append((cells, has_th))
            if not rows:
                return ()
            width = len(rows[0][0])
            if any(len(cells) != width for cells, _ in rows):
                raise ValueError("Tagged PDF table reading order is unreliable.")
            header_index = next((index for index, (_, has_th) in enumerate(rows) if has_th), 0)
            headers = tuple(rows[header_index][0])
            data_rows = tuple(tuple(cells) for index, (cells, _) in enumerate(rows) if index != header_index)
            return (Table(headers, data_rows),)

        if role in SUPPORTED_ROLES:
            text = " ".join(_flatten_text(_children(item), context, page, active).split())
            if text:
                return (Paragraph(text),)
            return ()

        text = " ".join(_flatten_text(_children(item), context, page, active).split())
        return (Paragraph(text),) if text else ()
    finally:
        active.remove(obj_id)


def _has_tagged_structure(catalog: Any) -> bool:
    catalog = _resolve(catalog)
    if not hasattr(catalog, "get"):
        return False
    mark_info = _resolve(catalog.get("/MarkInfo", {}))
    structure = _resolve(catalog.get("/StructTreeRoot"))
    return bool(getattr(mark_info, "get", lambda *_: None)("/Marked")) and bool(structure) and hasattr(structure, "get") and structure.get("/K") is not None


def _extract_tagged_ast(reader: PdfReader, structure_root: Any) -> DocumentAst:
    root = _resolve(structure_root)
    if not hasattr(root, "get"):
        raise ValueError("Tagged PDF reading order is unreliable.")
    context = StructureContext(
        role_map={str(key): str(_resolve(value)) for key, value in _resolve(root.get("/RoleMap", {})).items()} if hasattr(_resolve(root.get("/RoleMap", {})), "items") else {},
        page_indexes=_build_page_indexes(reader),
        mcid_text=_extract_mcid_text(reader),
    )
    blocks = _flatten_blocks(root.get("/K", []), context, inherited_page=None, active=set())
    if not blocks and context.mcid_text:
        raise ValueError("Tagged PDF reading order is unreliable.")
    return DocumentAst(blocks)


def _extract_plain_text_ast(path: Path) -> DocumentAst:
    paragraphs: list[Paragraph] = []
    with pymupdf.open(path) as document:
        if getattr(document, "needs_pass", False) is True or getattr(document, "is_encrypted", False) is True:
            raise ValueError("Encrypted PDF cannot be imported.")
        for page in document:
            text = page.get_text("text").replace("\r\n", "\n").replace("\r", "\n")
            for part in text.split("\n\n"):
                normalized = "\n".join(line.rstrip() for line in part.splitlines()).strip()
                if normalized:
                    paragraphs.append(Paragraph(normalized))
    return DocumentAst(tuple(paragraphs))


def import_pdf(path: Path | str) -> ImportedDocument:
    source = validate_source(path, ".pdf")
    reader = PdfReader(str(source))
    if getattr(reader, "is_encrypted", False) is True:
        raise ValueError("Encrypted PDF cannot be imported.")
    catalog = _resolve(reader.trailer.get("/Root"))
    ast: DocumentAst | None = None
    if _has_tagged_structure(catalog):
        try:
            ast = _extract_tagged_ast(reader, _resolve(catalog.get("/StructTreeRoot")))
        except (KeyError, TypeError, ValueError):
            ast = None
    if ast is None:
        ast = _extract_plain_text_ast(source)
    return ImportedDocument(source_name(source), render_markdown(ast))
