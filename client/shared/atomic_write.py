"""Replace a file without ever leaving it half-written.

``write_text_atomically`` and ``write_bytes_atomically`` write to a temporary file
``.<name>.<random>.tmp`` in the target's directory, flush it to disk and install it
with ``os.replace``. On return the target holds exactly what was written; on an
exception it is unchanged (same bytes, or still absent) and the temporary file is
removed.

Permissions follow a plain ``open(path, "w")``: an existing target the user may
not write raises ``PermissionError`` and is left alone (``ensure_writable``); a new
file gets the default mode for the umask (the kernel applies it); on POSIX a
replaced file's permission bits are kept.
"""

from __future__ import annotations

import contextlib
import errno
import os
import secrets
import stat
from pathlib import Path
from typing import IO, Any, BinaryIO, Callable, TextIO

_ATTEMPTS = 100
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)


def ensure_writable(path: Path | str) -> None:
    """Raise ``PermissionError`` if ``path`` exists and the user may not write it.

    This is the verdict an in-place ``open(path, "w")`` gives; a rename would not ask.
    A missing ``path`` passes.
    """
    target = Path(path)
    if os.path.exists(target) and not os.access(target, os.W_OK):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(target))


def _open_temporary_file(
    destination: Path,
    opener: Callable[[Path, int], int],
    **open_arguments: Any,
) -> IO:
    """Open a new ``.<name>.<random>.tmp`` next to ``destination``; never reuses a file."""
    for _attempt in range(_ATTEMPTS):
        candidate = destination.parent / f".{destination.name}.{secrets.token_hex(8)}.tmp"
        try:
            return open(candidate, opener=opener, **open_arguments)
        except FileExistsError:
            continue
    raise FileExistsError(errno.EEXIST, "No usable temporary file name found", str(destination.parent))


def _existing_mode(destination: Path) -> int | None:
    """The permission bits of ``destination``, or ``None`` if it does not exist."""
    try:
        return stat.S_IMODE(os.stat(destination).st_mode)
    except FileNotFoundError:
        return None


def _write_atomically(destination: Path, write: Callable[[Any], None], **open_arguments: Any) -> None:
    """Write ``destination`` through ``write(stream)`` on a new temporary file, then install it."""
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
        with _open_temporary_file(destination, create_new, **open_arguments) as stream:
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
    ensure_writable(destination)
    _write_atomically(destination, write, mode="w", encoding=encoding, newline=newline)


def write_bytes_atomically(path: Path | str, write: Callable[[BinaryIO], None]) -> None:
    """Write ``path`` through ``write(stream)`` on a binary stream; on an error ``path`` is unchanged.

    The same guarantee as ``write_text_atomically``. The directory must exist.
    """
    destination = Path(path)
    ensure_writable(destination)
    _write_atomically(destination, write, mode="wb")
