from __future__ import annotations

import csv
from pathlib import Path
import shutil
import sys

from name_validation import MAX_NAME_LENGTH, normalize_base_name

DEFAULT_DICTIONARY_NAME = "default"
DEFAULT_HEADER = ["text", "braille", "type"]
MAX_DICTIONARY_NAME_LENGTH = MAX_NAME_LENGTH


def get_application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_dictionary_directory(base_dir: Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir)
    return get_application_directory() / "dictionary"


def dictionary_path_for_name(name: str, dictionary_dir: Path | None = None) -> Path:
    return get_dictionary_directory(dictionary_dir) / f"{name}.csv"


def ensure_default_dictionary(dictionary_dir: Path | None = None) -> Path:
    directory = get_dictionary_directory(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    default_path = directory / f"{DEFAULT_DICTIONARY_NAME}.csv"
    if not default_path.exists():
        with default_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(DEFAULT_HEADER)
    return default_path


def list_dictionary_names(dictionary_dir: Path | None = None) -> list[str]:
    directory = get_dictionary_directory(dictionary_dir)
    if not directory.exists():
        return []
    names = [path.stem for path in directory.glob("*.csv") if path.is_file()]
    return sorted(names, key=lambda name: (name.casefold(), name))


def normalize_dictionary_name(name: str) -> str:
    return normalize_base_name(name, reserved_names={DEFAULT_DICTIONARY_NAME})


def validate_dictionary_csv(path: Path | str) -> None:
    source_path = Path(path)
    with source_path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        fieldnames = reader.fieldnames or []
    if any(field not in fieldnames for field in DEFAULT_HEADER):
        raise ValueError("Dictionary CSV must contain text, braille, and type headers.")


def create_dictionary(dictionary_dir: Path | None, name: str) -> Path:
    directory = get_dictionary_directory(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    normalized = normalize_dictionary_name(name)
    path = directory / f"{normalized}.csv"
    if path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(DEFAULT_HEADER)
    return path


def import_dictionary(dictionary_dir: Path | None, source_path: Path | str, name: str) -> Path:
    directory = get_dictionary_directory(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    normalized = normalize_dictionary_name(name)
    destination_path = directory / f"{normalized}.csv"
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    validate_dictionary_csv(source)
    shutil.copyfile(source, destination_path)
    return destination_path


def export_dictionary(dictionary_dir: Path | None, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    shutil.copyfile(source_path, destination)
    return destination


def delete_dictionary(dictionary_dir: Path | None, name: str) -> None:
    normalized = name.strip()
    if normalized.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
        raise ValueError("Default dictionary cannot be deleted.")
    path = dictionary_path_for_name(normalized, dictionary_dir)
    path.unlink()


def resolve_selected_dictionary(names: list[str], saved_name: str | None) -> str:
    if saved_name and saved_name in names:
        return saved_name
    return DEFAULT_DICTIONARY_NAME if DEFAULT_DICTIONARY_NAME in names else (names[0] if names else DEFAULT_DICTIONARY_NAME)


def choose_selection_after_delete(names: list[str], deleted_name: str) -> str:
    if deleted_name not in names:
        return resolve_selected_dictionary(names, DEFAULT_DICTIONARY_NAME)
    index = names.index(deleted_name)
    remaining = [name for name in names if name != deleted_name]
    if not remaining:
        return DEFAULT_DICTIONARY_NAME
    if index > 0:
        return remaining[index - 1]
    return remaining[0]
