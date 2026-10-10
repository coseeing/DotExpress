from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from typing import BinaryIO

from documents.formats import ALL_SUPPORTED_FILTER_KEY, get_importable_formats, get_supported_import_filter_keys
from shared.atomic_write import ensure_writable, write_bytes_atomically
from shared.name_validation import normalize_base_name

DEP_EXTENSION = ".dep"
TXT_EXTENSION = ".txt"
BRL_EXTENSION = ".brl"
PENDING_METADATA_SUFFIX = ".meta.json"
DEFAULT_DOCUMENT_NAME = "new"
_LONE_SURROGATE = re.compile(r"[\ud800-\udfff]")


@dataclass(frozen=True)
class Document:
    name: str
    text: str
    braille: str | None


@dataclass(frozen=True)
class BatchIssue:
    path: Path
    reason: str


def create_default_document() -> Document:
    return Document(name=DEFAULT_DOCUMENT_NAME, text="", braille=None)


def ensure_workspace_directory(workspace_dir: Path) -> Path:
    directory = Path(workspace_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def normalize_document_name(name: str) -> str:
    return normalize_base_name(name)


def document_package_path_for_name(name: str, workspace_dir: Path) -> Path:
    return Path(workspace_dir) / f"{name}{DEP_EXTENSION}"


def replace_lone_surrogates(text: str) -> str:
    """Replace every unpaired UTF-16 surrogate with U+FFFD so the text can be encoded as UTF-8; a split pair is joined."""
    if _LONE_SURROGATE.search(text) is None:
        return text
    return text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _encodable(document: Document) -> Document:
    """``document`` with lone surrogates replaced in its text and braille (F-5); pending braille stays ``None``."""
    braille = None if document.braille is None else replace_lone_surrogates(document.braille)
    return Document(name=document.name, text=replace_lone_surrogates(document.text), braille=braille)


def _normalized(document: Document) -> Document:
    return _encodable(Document(name=normalize_document_name(document.name), text=document.text, braille=document.braille))


def _write_package(stream: BinaryIO, document: Document, *, include_pending_metadata: bool) -> None:
    """Write the normalized ``document`` as a package archive to ``stream``, which stays open."""
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{document.name}{TXT_EXTENSION}", document.text)
        archive.writestr(f"{document.name}{BRL_EXTENSION}", document.braille or "")
        if document.braille is None and include_pending_metadata:
            metadata_name = f"{document.name}{PENDING_METADATA_SUFFIX}"
            archive.writestr(metadata_name, json.dumps({"braille_pending": True}, ensure_ascii=False))


def save_document_package(
    path: Path | str,
    document: Document,
    *,
    include_pending_metadata: bool = True,
) -> Path:
    """Write ``document`` as the package at ``path`` through a temporary file (F-3).

    On return the package holds ``document``; on an exception it is unchanged (or still
    absent) and no temporary file is left. A package the user may not write raises
    ``PermissionError`` and is left alone, as the old in-place write did.
    """
    package_path = Path(path)
    document = _normalized(document)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_atomically(
        package_path,
        lambda stream: _write_package(stream, document, include_pending_metadata=include_pending_metadata),
    )
    return package_path


class PackageFiles:
    """The file operations ``move_document_package`` uses; tests pass a model or a fault injector."""

    def ensure_writable(self, path: Path) -> None:
        """Raise ``PermissionError`` if the package at ``path`` exists and the user may not write it."""
        ensure_writable(path)

    def exists(self, path: Path) -> bool:
        return Path(path).exists()

    def write(self, path: Path, document: Document) -> None:
        """Write the package into the new private file ``path`` and flush it to disk."""
        with open(path, "wb") as stream:
            _write_package(stream, _normalized(document), include_pending_metadata=True)
            stream.flush()
            os.fsync(stream.fileno())

    def replace(self, source: Path, destination: Path) -> None:
        os.replace(source, destination)

    def remove(self, path: Path) -> None:
        Path(path).unlink(missing_ok=True)

    def copy_permissions(self, source: Path, destination: Path) -> None:
        """Give ``destination`` the permission bits of ``source``; POSIX only, a no-op elsewhere."""
        if os.name == "posix":
            shutil.copymode(source, destination)

    def temporary_path(self, directory: Path, name: str) -> Path:
        """Create a new empty file ``.<name>.<random>.tmp`` in ``directory`` (created if missing).

        The leading dot does not hide it on Windows; ``*.dep`` never matches it, so the
        workspace never loads it as a package.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=f".{name}.", suffix=".tmp", delete=False) as temporary:
            return Path(temporary.name)


def move_document_package(
    old_path: Path,
    new_path: Path,
    document: Document,
    *,
    files: PackageFiles,
) -> None:
    """Write ``document`` as the package at ``new_path`` and remove the package at ``old_path``.

    Every rename uses this sequence, case-only or not (F-3).

    Safe when both paths name the same file, as a case-only rename does on a case-insensitive
    file system: nothing is written to, replaced onto or removed under a name that can alias
    the other package. The new package is staged in a temporary file, the old one is moved
    aside to another temporary file, then the staged file takes the exact name ``new_path``.

    On return the package exists only at ``new_path``, with that spelling, and holds
    ``document``; on POSIX it keeps the old package's permission bits. On an exception the
    old package is back at ``old_path`` with its spelling and bytes and no temporary file is
    left, unless putting the old package back fails too: then it stays in its ``.tmp`` file.
    Failing to remove the moved-aside old package after the install is ignored; that
    leftover ``.tmp`` file is never loaded as a package.

    An old package the user may not write (a read-only file) raises ``PermissionError``
    before anything is created or moved, as saving it does (F-3).
    """
    old_path = Path(old_path)
    new_path = Path(new_path)
    files.ensure_writable(old_path)
    staged_path = files.temporary_path(new_path.parent, new_path.name)
    try:
        files.write(staged_path, document)
    except BaseException:
        with suppress(OSError):
            files.remove(staged_path)
        raise
    aside_path: Path | None = None
    try:
        if files.exists(old_path):
            aside_path = files.temporary_path(old_path.parent, old_path.name)
            files.replace(old_path, aside_path)
    except BaseException:
        with suppress(OSError):
            files.remove(staged_path)
        if aside_path is not None:
            with suppress(OSError):
                files.remove(aside_path)
        raise
    try:
        if aside_path is not None:
            files.copy_permissions(aside_path, staged_path)
        files.replace(staged_path, new_path)
    except BaseException:
        if aside_path is not None:
            with suppress(OSError):
                files.replace(aside_path, old_path)
        with suppress(OSError):
            files.remove(staged_path)
        raise
    if aside_path is not None:
        with suppress(OSError):
            files.remove(aside_path)


def load_document_package(path: Path | str) -> Document:
    package_path = Path(path)
    if package_path.suffix.casefold() != DEP_EXTENSION:
        raise ValueError("Document package must use the .dep extension.")
    package_name = normalize_document_name(package_path.stem)
    with zipfile.ZipFile(package_path, "r") as archive:
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        txt_names = [name for name in names if name.endswith(".txt")]
        brl_names = [name for name in names if name.endswith(".brl")]
        if len(txt_names) != 1 or len(brl_names) != 1:
            raise ValueError("Document package must contain one .txt and one .brl file.")
        txt_name = txt_names[0]
        brl_name = brl_names[0]
        txt_base = normalize_document_name(Path(txt_name).stem)
        brl_base = normalize_document_name(Path(brl_name).stem)
        if txt_base != brl_base or txt_base != package_name:
            raise ValueError("Document package names do not match.")
        text = archive.read(txt_name).decode("utf-8")
        braille = archive.read(brl_name).decode("utf-8")
        metadata_name = f"{package_name}{PENDING_METADATA_SUFFIX}"
        braille_pending = False
        if metadata_name in names:
            metadata = json.loads(archive.read(metadata_name).decode("utf-8"))
            braille_pending = bool(metadata.get("braille_pending"))
    return Document(name=package_name, text=text, braille=None if braille_pending else braille)


def load_text_document(path: Path | str) -> Document:
    source_path = Path(path)
    if source_path.suffix.casefold() != TXT_EXTENSION:
        raise ValueError("Text document must use the .txt extension.")
    return Document(
        name=normalize_document_name(source_path.stem),
        text=source_path.read_text(encoding="utf-8"),
        braille=None,
    )


IMPORT_LOADERS: dict[str, Callable[[Path | str], Document]] = {
    descriptor.key: descriptor.loader
    for descriptor in get_importable_formats()
    if descriptor.loader is not None
}


def export_document_brl(path: Path | str, document: Document) -> Path:
    destination_path = Path(path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(document.braille or "", encoding="utf-8")
    return destination_path


def prepare_document_for_save(
    document: Document,
    *,
    text: str,
    braille: str,
) -> Document:
    saved_braille = None if document.braille is None else braille
    return _encodable(Document(name=document.name, text=text, braille=saved_braille))


def load_workspace_documents(workspace_dir: Path) -> tuple[list[Document], list[Path]]:
    directory = ensure_workspace_directory(workspace_dir)
    documents: list[Document] = []
    invalid_paths: list[Path] = []
    for path in sorted(directory.glob(f"*{DEP_EXTENSION}"), key=lambda item: (item.stem.casefold(), item.stem)):
        try:
            documents.append(load_document_package(path))
        except Exception:
            invalid_paths.append(path)
    documents.sort(key=lambda document: (document.name.casefold(), document.name))
    return documents, invalid_paths


def batch_import_documents(
    paths: list[Path | str],
    *,
    format_key: str,
    existing_names: set[str],
) -> tuple[list[Document], list[BatchIssue]]:
    documents: list[Document] = []
    issues: list[BatchIssue] = []
    seen_names = {name.casefold() for name in existing_names}
    normalized_format_key = format_key.casefold()
    if normalized_format_key != ALL_SUPPORTED_FILTER_KEY and normalized_format_key not in get_supported_import_filter_keys():
        raise ValueError(f'Unsupported import format: "{format_key}".')
    for path in sorted((Path(path) for path in paths), key=lambda item: (item.stem.casefold(), item.stem)):
        try:
            loader_key = path.suffix.lstrip(".").casefold() if normalized_format_key == ALL_SUPPORTED_FILTER_KEY else normalized_format_key
            loader = IMPORT_LOADERS.get(loader_key)
            if loader is None:
                raise ValueError(f'Unsupported import file type: "{path.suffix}".')
            document = loader(path)
        except Exception as exc:
            issues.append(BatchIssue(path=path, reason=str(exc)))
            continue
        if document.name.casefold() in seen_names:
            issues.append(BatchIssue(path=path, reason=f'Document "{document.name}" already exists.'))
            continue
        seen_names.add(document.name.casefold())
        documents.append(document)
    return documents, issues


def choose_selection_after_delete(names: list[str], deleted_name: str) -> str | None:
    if deleted_name not in names:
        return names[0] if names else None
    index = names.index(deleted_name)
    remaining = [name for name in names if name != deleted_name]
    if not remaining:
        return None
    if index > 0:
        return remaining[index - 1]
    return remaining[0]
