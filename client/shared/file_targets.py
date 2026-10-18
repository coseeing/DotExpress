"""Checks on the file a rename or a copy goes to, shared by dictionaries and scripts (F-18)."""

from __future__ import annotations

import errno
import os
from pathlib import Path


def is_same_file(source: Path, destination: Path) -> bool:
    """Whether ``destination`` names ``source`` itself: a case-only rename on a
    case-insensitive file system, such as ``alpha`` to ``Alpha`` on Windows (F-W6, F-11 D10).

    Another file that only differs in case (a case-sensitive file system) is not the same file.
    """
    try:
        return os.path.samefile(source, destination)
    except OSError:
        return False


def refuse_folder_target(destination: Path) -> None:
    """Raise the error copying onto a folder gives, if ``destination`` is a folder.

    As ``documents.workspace.write_export_text`` gives it for a BRL or HTML export, not a
    failed replace naming the temporary file.
    """
    if not destination.is_dir():
        return
    if os.name == "nt":
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
    raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(destination))
