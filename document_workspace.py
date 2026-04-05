from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import zipfile

from name_validation import MAX_NAME_LENGTH, normalize_base_name

DEP_EXTENSION = ".dep"


@dataclass(frozen=True)
class Document:
    name: str
    text: str
    braille: str


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


def save_document_package(path: Path | str, document: Document) -> Path:
    package_path = Path(path)
    normalized_name = normalize_document_name(document.name)
    document = Document(name=normalized_name, text=document.text, braille=document.braille)
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{document.name}.txt", document.text)
        archive.writestr(f"{document.name}.brl", document.braille)
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
    return Document(name=package_name, text=text, braille=braille)


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
