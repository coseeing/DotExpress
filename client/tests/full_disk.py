"""Make writes fail as on a full disk, for the data safety tests (F-8).

``full_disk(folder, after=..., pattern=...)`` patches ``builtins.open`` and ``io.open``
(which ``pathlib``, ``tempfile`` and ``shutil`` call) for the length of a ``with`` block.
A file opened for writing inside ``folder`` whose name matches ``pattern`` takes ``after``
more characters (text) or bytes (binary); the write that would go past them writes what
fits and raises ``OSError(ENOSPC)``, as a full disk does. Reads and other files are not
touched. The same fault reaches the old in-place writers and ``shared.atomic_write``, so a
test sees what each leaves behind. ``tempfile.NamedTemporaryFile`` opens its folder with an
opener; that open counts as one of the folder itself.
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import io
import os
import re
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

_WRITE_MODES = frozenset("wax+")


class _FullDiskStream:
    """A writable stream with ``room`` characters or bytes left before the disk is full."""

    def __init__(self, stream, room: int) -> None:
        self._stream = stream
        self._room = room

    def write(self, data):
        if len(data) > self._room:
            if self._room > 0:
                self._stream.write(data[: self._room])
                self._room = 0
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        self._room -= len(data)
        return self._stream.write(data)

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def __getattr__(self, name: str):
        return getattr(self._stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return self._stream.__exit__(*exc_info)


@contextlib.contextmanager
def full_disk(folder: Path | str, *, after: int = 0, pattern: str = "") -> Iterator[None]:
    """Writes inside ``folder`` to names matching ``pattern`` fail after ``after`` units."""
    real_open = io.open
    root = os.path.normcase(os.path.abspath(folder))
    name_pattern = re.compile(pattern)

    def inside(path: str) -> bool:
        try:
            return os.path.commonpath([os.path.normcase(path), root]) == root
        except ValueError:  # another drive
            return False

    def open_on_a_full_disk(file, mode="r", *args, **kwargs):
        stream = real_open(file, mode, *args, **kwargs)
        if isinstance(file, int) or not _WRITE_MODES & set(mode):
            return stream
        path = os.path.abspath(os.fspath(file))
        if not inside(path) or not name_pattern.search(os.path.basename(path)):
            return stream
        return _FullDiskStream(stream, after)

    with patch.object(builtins, "open", open_on_a_full_disk), patch.object(io, "open", open_on_a_full_disk):
        yield
