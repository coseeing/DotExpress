"""The script files: list, create, import, rename, export, delete (F-18).

A script name maps to ``<name>.py`` in the script folder, as a dictionary name maps to
``<name>.csv``. ``no-processing.py`` is No Processing, the script that changes nothing:
it runs like any script, it is written again when it holds anything else (F-18b), and it
cannot be renamed or deleted.
Every file this module writes goes through ``shared.atomic_write`` (F-8).
"""

from __future__ import annotations

from pathlib import Path

from conversion.preprocessing.user_script import (
    NO_PROCESSING_SCRIPT,
    NO_PROCESSING_SCRIPT_NAME,
    SCRIPT_SUFFIX,
    save_script,
    validate_script,
)
from i18n import N_, _
from shared.atomic_write import write_bytes_atomically, write_text_atomically
from shared.file_targets import is_same_file, refuse_folder_target
from shared.name_validation import normalize_base_name

# How No Processing is shown; translated when shown (F-14 D4).
NO_PROCESSING_DISPLAY_NAME = N_("No Processing")


class ScriptImportSourceError(Exception):
    """The Import source cannot be opened or read: another program holds it, or reading it
    is not permitted (the twin of ``DictionaryImportSourceError``, F-11 D11).

    ``error`` (also ``__cause__``) is the ``PermissionError``. Not an ``OSError``, so a
    caller can give it F-6's reason while an ``OSError`` writing the copy into the script
    folder keeps its own message.
    """

    def __init__(self, error: PermissionError) -> None:
        super().__init__(str(error))
        self.error = error


def is_no_processing_script(name: str) -> bool:
    return name.strip().casefold() == NO_PROCESSING_SCRIPT_NAME


def script_path_for_name(name: str, script_dir: Path) -> Path:
    return Path(script_dir) / f"{name}{SCRIPT_SUFFIX}"


def ensure_no_processing_script(script_dir: Path) -> Path:
    """Write ``no-processing.py`` with its exact text when it is missing or holds anything else (F-18b).

    Conversion runs it like any other script, so its bytes are put back on every refresh.
    A file that cannot be replaced (a folder of that name, a read-only file) is left as it
    is: No Processing is still listed, and converting with it gives the text-processing error.
    """
    directory = Path(script_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = script_path_for_name(NO_PROCESSING_SCRIPT_NAME, directory)
    try:
        if path.read_bytes() == NO_PROCESSING_SCRIPT.encode("utf-8"):
            return path
    except OSError:
        pass  # missing, a folder, or held by another program: try to write it
    try:
        write_text_atomically(path, lambda stream: stream.write(NO_PROCESSING_SCRIPT), encoding="utf-8", newline="")
    except OSError:
        pass  # left as it is; Script Management shows why it cannot be used
    return path


def list_script_names(script_dir: Path) -> list[str]:
    """No Processing first, then the other scripts in the order of the dictionaries (F-18 D1, O1).

    No Processing is always listed, whatever ``no-processing.py`` is or whether it exists
    (F-18 review M-5); a file that cannot be used shows as such in Script Management.
    """
    directory = Path(script_dir)
    stems = [path.stem for path in directory.glob(f"*{SCRIPT_SUFFIX}") if path.is_file()] if directory.is_dir() else []
    others = sorted((stem for stem in stems if not is_no_processing_script(stem)), key=lambda name: (name.casefold(), name))
    return [NO_PROCESSING_SCRIPT_NAME, *others]


def normalize_script_name(name: str) -> str:
    """The name without surrounding spaces; ``NameValidationError`` if it cannot name a script.

    No Processing's internal name, its msgid and its translation are reserved, whatever
    their case (F-18 D4).
    """
    reserved = {NO_PROCESSING_SCRIPT_NAME, NO_PROCESSING_DISPLAY_NAME, _(NO_PROCESSING_DISPLAY_NAME)}
    return normalize_base_name(name, reserved_names=reserved)


def script_exists(script_dir: Path, name: str) -> bool:
    return script_path_for_name(normalize_script_name(name), script_dir).exists()


def create_script(script_dir: Path, name: str, source: str) -> Path:
    """Write a new script; ``FileExistsError`` if a script of that name exists (F-18 D8.1)."""
    path = script_path_for_name(normalize_script_name(name), script_dir)
    if path.exists():
        raise FileExistsError(f"Script '{path.stem}' already exists.")
    save_script(path, source)
    return path


def check_import_suffix(source_path: Path | str) -> None:
    """``ValueError`` (a msgid) unless ``source_path`` ends in ``.py``, whatever its case (F-18 D8.5)."""
    if Path(source_path).suffix.casefold() != SCRIPT_SUFFIX:
        raise ValueError(N_("Only Python files (.py) can be imported."))


def import_script(script_dir: Path, source_path: Path | str, name: str) -> Path:
    """Copy a ``.py`` file that passes the signature rule into the script folder (F-18 D8.5).

    Raises ``ValueError`` (a msgid) for another suffix or a ``main`` that breaks the rule,
    ``SyntaxError``, ``UnicodeDecodeError``, ``ScriptImportSourceError`` when the source
    cannot be opened, and ``FileExistsError`` for a taken name. The copy has the source's
    bytes; nothing is written on any error.
    """
    source = Path(source_path)
    check_import_suffix(source)
    directory = Path(script_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = script_path_for_name(normalize_script_name(name), directory)
    if destination.exists():
        raise FileExistsError(f"Script '{destination.stem}' already exists.")
    try:
        data = source.read_bytes()
    except PermissionError as error:
        raise ScriptImportSourceError(error) from error
    validate_script(data.decode("utf-8-sig"), filename=str(source))
    write_bytes_atomically(destination, lambda stream: stream.write(data))
    return destination


def rename_script(script_dir: Path, source_name: str, new_name: str) -> Path:
    source_normalized = source_name.strip()
    if is_no_processing_script(source_normalized):
        raise ValueError("No Processing cannot be renamed.")
    destination_normalized = normalize_script_name(new_name)
    source_path = script_path_for_name(source_normalized, script_dir)
    destination_path = script_path_for_name(destination_normalized, script_dir)
    if destination_path.exists() and not is_same_file(source_path, destination_path):
        raise FileExistsError(f"Script '{destination_normalized}' already exists.")
    source_path.rename(destination_path)
    return destination_path


def export_script(script_dir: Path, name: str, destination_path: Path | str) -> Path:
    """Copy a script's bytes to ``destination_path``, No Processing's too (F-18b)."""
    destination = Path(destination_path)
    refuse_folder_target(destination)
    source_path = script_path_for_name(name.strip(), script_dir)
    # An existing file there is replaced only once the copy is complete and synced.
    write_bytes_atomically(destination, lambda stream: stream.write(source_path.read_bytes()))
    return destination


def delete_script(script_dir: Path, name: str) -> None:
    """Remove a script; one already removed by another program counts as deleted (F-18 review M-6)."""
    normalized = name.strip()
    if is_no_processing_script(normalized):
        raise ValueError("No Processing cannot be deleted.")
    script_path_for_name(normalized, script_dir).unlink(missing_ok=True)


def resolve_selected_script(names: list[str], saved_name: str | None) -> str:
    """``saved_name`` if it is listed, else No Processing (F-18 D3)."""
    if saved_name and saved_name in names:
        return saved_name
    return NO_PROCESSING_SCRIPT_NAME
