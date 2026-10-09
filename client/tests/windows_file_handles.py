"""Windows file conditions for tests: real read-only and hidden files, open handles (F-3).

Only Windows-only tests call these helpers. ``hold_open`` opens a file the way another
program would, with ``CreateFileW(GENERIC_READ, share, OPEN_EXISTING)``; sharing checks
apply to every handle, including one held by the test's own process. Each helper
registers its undo with ``addCleanup``, so the undo runs before the clean-up of a
temporary directory registered earlier (clean-ups run last in, first out).
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import stat
import unittest
from pathlib import Path
from typing import Callable

SHARE_READ = 0x1
SHARE_WRITE = 0x2
SHARE_DELETE = 0x4
SHARE_READ_WRITE = SHARE_READ | SHARE_WRITE
# The share modes another program may hold a file with: a zip tool or a viewer shares
# reading only, an editor reading and writing, an antivirus scanner or the search
# indexer usually everything.
SHARE_MODES = (
    ("read", SHARE_READ),
    ("read+write", SHARE_READ_WRITE),
    ("read+delete", SHARE_READ | SHARE_DELETE),
    ("read+write+delete", SHARE_READ_WRITE | SHARE_DELETE),
)

_GENERIC_READ = 0x80000000
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_NORMAL = 0x80
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def _kernel32():
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.SetFileAttributesW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
    kernel32.SetFileAttributesW.restype = wintypes.BOOL
    return kernel32


def hold_open(test_case: unittest.TestCase, path: Path | str, share: int) -> Callable[[], None]:
    """Open ``path`` for reading with ``share``; return a function that closes it.

    The clean-up closes it too if the test has not.
    """
    kernel32 = _kernel32()
    handle = kernel32.CreateFileW(str(path), _GENERIC_READ, share, None, _OPEN_EXISTING, _FILE_ATTRIBUTE_NORMAL, None)
    if handle is None or handle == _INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    closed = False

    def release() -> None:
        nonlocal closed
        if not closed:
            closed = True
            kernel32.CloseHandle(handle)

    test_case.addCleanup(release)
    return release


def make_read_only(test_case: unittest.TestCase, path: Path | str) -> None:
    """Set the read-only attribute of ``path``; the clean-up clears it if the file is still there."""
    target = Path(path)
    os.chmod(target, stat.S_IREAD)
    test_case.addCleanup(_make_writable, target)


def _make_writable(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)


def make_hidden(path: Path | str) -> None:
    """Add the hidden attribute to ``path``, keeping its other attributes."""
    attributes = os.stat(path).st_file_attributes | stat.FILE_ATTRIBUTE_HIDDEN
    if not _kernel32().SetFileAttributesW(str(path), attributes):
        raise ctypes.WinError(ctypes.get_last_error())


def is_hidden(path: Path | str) -> bool:
    return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN)
