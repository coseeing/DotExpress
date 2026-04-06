from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import zipfile

from name_validation import MAX_NAME_LENGTH, normalize_base_name

DEP_EXTENSION = ".dep"
TXT_EXTENSION = ".txt"
BRL_EXTENSION = ".brl"
PENDING_METADATA_SUFFIX = ".meta.json"


@dataclass(frozen=True)
class Document:
    name: str
    text: str
    braille: str | None


@dataclass(frozen=True)
class BatchIssue:
    path: Path
    reason: str


def get_application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_workspace_directory(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir)
    return get_application_directory() / "workspace"


def ensure_workspace_directory(workspace_dir: Path | None = None) -> Path:
    directory = get_workspace_directory(workspace_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def normalize_document_name(name: str) -> str:
    return normalize_base_name(name)


def document_package_path_for_name(name: str, workspace_dir: Path | None = None) -> Path:
    return get_workspace_directory(workspace_dir) / f"{name}{DEP_EXTENSION}"


def save_document_package(
    path: Path | str,
    document: Document,
    *,
    include_pending_metadata: bool = True,
) -> Path:
    package_path = Path(path)
    normalized_name = normalize_document_name(document.name)
    document = Document(name=normalized_name, text=document.text, braille=document.braille)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{document.name}{TXT_EXTENSION}", document.text)
        archive.writestr(f"{document.name}{BRL_EXTENSION}", document.braille or "")
        if document.braille is None and include_pending_metadata:
            metadata_name = f"{document.name}{PENDING_METADATA_SUFFIX}"
            archive.writestr(metadata_name, json.dumps({"braille_pending": True}, ensure_ascii=False))
    return package_path


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
    auto_convert,
) -> tuple[Document, Exception | None]:
    if document.braille is None:
        try:
            braille = auto_convert(text)
            return Document(name=document.name, text=text, braille=braille), None
        except Exception as exc:
            return Document(name=document.name, text=text, braille=""), exc
    return Document(name=document.name, text=text, braille=braille), None


def list_document_names(workspace_dir: Path | None = None) -> list[str]:
    directory = get_workspace_directory(workspace_dir)
    if not directory.exists():
        return []
    names = [path.stem for path in directory.glob(f"*{DEP_EXTENSION}") if path.is_file()]
    return sorted(names, key=lambda name: (name.casefold(), name))


def load_workspace_documents(workspace_dir: Path | None = None) -> tuple[list[Document], list[Path]]:
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


def batch_import_documents_from_folder(
    directory: Path | str,
    *,
    format_key: str,
    existing_names: set[str],
) -> tuple[list[Document], list[BatchIssue]]:
    folder = Path(directory)
    documents: list[Document] = []
    issues: list[BatchIssue] = []
    seen_names = {name.casefold() for name in existing_names}
    loader = load_document_package if format_key == "dep" else load_text_document
    extension = DEP_EXTENSION if format_key == "dep" else TXT_EXTENSION
    for path in sorted(folder.glob(f"*{extension}"), key=lambda item: (item.stem.casefold(), item.stem)):
        try:
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


def batch_export_documents_to_folder(
    directory: Path | str,
    documents: list[Document],
    *,
    format_key: str,
    overwrite: bool,
) -> list[Path]:
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    suffix = DEP_EXTENSION if format_key == "dep" else BRL_EXTENSION
    conflicts = [folder / f"{document.name}{suffix}" for document in documents if (folder / f"{document.name}{suffix}").exists()]
    if conflicts and not overwrite:
        return conflicts
    for document in documents:
        destination_path = folder / f"{document.name}{suffix}"
        if format_key == "dep":
            save_document_package(destination_path, document, include_pending_metadata=False)
        else:
            export_document_brl(destination_path, document)
    return []


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
