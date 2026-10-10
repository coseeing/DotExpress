"""The dictionary files: create, import, rename, export, delete.

Every file this module writes goes through ``shared.atomic_write`` (F-8): a failed
write leaves the target as it was (or absent) and no temporary file.
"""

from __future__ import annotations

import csv
import errno
import os
from pathlib import Path
import shutil
from typing import BinaryIO, TextIO

from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name

DEFAULT_DICTIONARY_NAME = "default"
DEFAULT_HEADER = ["text", "braille", "type"]
MAX_DICTIONARY_NAME_LENGTH = MAX_NAME_LENGTH


def dictionary_path_for_name(name: str, dictionary_dir: Path) -> Path:
    return Path(dictionary_dir) / f"{name}.csv"


def _write_header(stream: TextIO) -> None:
    csv.writer(stream).writerow(DEFAULT_HEADER)


def _copy_file_into(source: Path, stream: BinaryIO) -> None:
    """Copy the bytes of ``source`` into ``stream``; an error opening or reading it is raised."""
    with open(source, "rb") as source_stream:
        shutil.copyfileobj(source_stream, stream)


def ensure_default_dictionary(dictionary_dir: Path) -> Path:
    directory = Path(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    default_path = directory / f"{DEFAULT_DICTIONARY_NAME}.csv"
    if not default_path.exists():
        write_text_atomically(default_path, _write_header, encoding="utf-8", newline="")
    return default_path


def list_dictionary_names(dictionary_dir: Path) -> list[str]:
    directory = Path(dictionary_dir)
    if not directory.exists():
        return []
    names = [path.stem for path in directory.glob("*.csv") if path.is_file()]
    return sorted(names, key=lambda name: (name.casefold(), name))


def normalize_dictionary_name(name: str) -> str:
    return normalize_base_name(name, reserved_names={DEFAULT_DICTIONARY_NAME})


def validate_dictionary_csv(path: Path | str) -> None:
    """Raise ValueError if a header is missing; reading every row raises what reading the
    dictionary later would (UnicodeDecodeError, csv.Error, OSError).

    The file is read as ``dictionaries.entries.load_dictionary_rows`` reads it (F-6), so a
    file that Import accepts can also be counted and edited.
    """
    source_path = Path(path)
    with source_path.open("r", newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        fieldnames = reader.fieldnames or []
        if any(field not in fieldnames for field in DEFAULT_HEADER):
            raise ValueError("Dictionary CSV must contain text, braille, and type headers.")
        for _row in reader:
            pass


def create_dictionary(dictionary_dir: Path, name: str) -> Path:
    directory = Path(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    normalized = normalize_dictionary_name(name)
    path = directory / f"{normalized}.csv"
    if path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    write_text_atomically(path, _write_header, encoding="utf-8", newline="")
    return path


def import_dictionary(dictionary_dir: Path, source_path: Path | str, name: str) -> Path:
    directory = Path(dictionary_dir)
    directory.mkdir(parents=True, exist_ok=True)
    normalized = normalize_dictionary_name(name)
    destination_path = directory / f"{normalized}.csv"
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{normalized}' already exists.")
    source = Path(source_path)
    validate_dictionary_csv(source)
    write_bytes_atomically(destination_path, lambda stream: _copy_file_into(source, stream))
    return destination_path


def rename_dictionary(dictionary_dir: Path, source_name: str, new_name: str) -> Path:
    source_normalized = source_name.strip()
    if source_normalized.casefold() == DEFAULT_DICTIONARY_NAME.casefold():
        raise ValueError("Default dictionary cannot be renamed.")
    destination_normalized = normalize_dictionary_name(new_name)
    source_path = dictionary_path_for_name(source_normalized, dictionary_dir)
    destination_path = dictionary_path_for_name(destination_normalized, dictionary_dir)
    if destination_path.exists():
        raise FileExistsError(f"Dictionary '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
    return destination_path


def export_dictionary(dictionary_dir: Path, name: str, destination_path: Path | str) -> Path:
    source_path = dictionary_path_for_name(name.strip(), dictionary_dir)
    destination = Path(destination_path)
    if destination.is_dir():
        # The error copying onto a folder gave, as documents.workspace.write_export_text
        # gives for a BRL or HTML export, not a failed replace naming the temporary file.
        if os.name == "nt":
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
        raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(destination))
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: _copy_file_into(source_path, stream))
    return destination


def delete_dictionary(dictionary_dir: Path, name: str) -> None:
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
