"""Replace a text file without ever leaving it half-written.

``write_text_atomically`` writes to a temporary file ``.<name>.<random>.tmp`` in
the target's directory, flushes it to disk and installs it with ``os.replace``.
On return the target holds exactly what was written; on an exception it is
unchanged (same bytes, or still absent) and the temporary file is removed.

Permissions follow a plain ``open(path, "w")``: an existing target the user may
not write raises ``PermissionError`` and is left alone; a new file gets the
default mode for the umask (the kernel applies it); on POSIX a replaced file's
permission bits are kept.
"""

from __future__ import annotations

import contextlib
import errno
import os
import secrets
import stat
from pathlib import Path
from typing import Callable, TextIO

_ATTEMPTS = 100
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)


def _open_temporary_file(
    destination: Path,
    opener: Callable[[Path, int], int],
    encoding: str,
    newline: str | None,
) -> TextIO:
    """Open a new ``.<name>.<random>.tmp`` next to ``destination``; never reuses a file."""
    for _attempt in range(_ATTEMPTS):
        candidate = destination.parent / f".{destination.name}.{secrets.token_hex(8)}.tmp"
        try:
            return open(candidate, "w", encoding=encoding, newline=newline, opener=opener)
        except FileExistsError:
            continue
    raise FileExistsError(errno.EEXIST, "No usable temporary file name found", str(destination.parent))


def _existing_mode(destination: Path) -> int | None:
    """The permission bits of ``destination``, or ``None`` if it does not exist."""
    try:
        return stat.S_IMODE(os.stat(destination).st_mode)
    except FileNotFoundError:
        return None


def write_text_atomically(
    path: Path | str,
    write: Callable[[TextIO], None],
    *,
    encoding: str = "utf-8",
    newline: str | None = "",
) -> None:
    """Write ``path`` through ``write(stream)``; on an error ``path`` is unchanged.

    The directory must exist. No temporary file is left unless removing it fails.
    """
    destination = Path(path)
    if os.path.exists(destination) and not os.access(destination, os.W_OK):
        # The verdict the old in-place open("w") gave; a rename would not ask.
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(destination))
    temporary_path: Path | None = None
    installed = False

    def create_new(candidate: Path, _flags: int) -> int:
        # Mode 0o666 lets the kernel apply the umask, as open(path, "w") would; the
        # path is recorded as soon as the file exists, so every failure removes it.
        nonlocal temporary_path
        descriptor = os.open(candidate, _CREATE_FLAGS, 0o666)
        temporary_path = Path(candidate)
        return descriptor

    try:
        with _open_temporary_file(destination, create_new, encoding, newline) as stream:
            write(stream)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "posix":
            mode = _existing_mode(destination)
            if mode is not None:
                os.chmod(temporary_path, mode)
        os.replace(temporary_path, destination)
        installed = True
    finally:
        if not installed and temporary_path is not None:
            with contextlib.suppress(OSError):
                temporary_path.unlink(missing_ok=True)
