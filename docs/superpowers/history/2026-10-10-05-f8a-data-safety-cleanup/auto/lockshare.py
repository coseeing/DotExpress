"""Hold a file open for reading with a chosen share mode: CreateFileW(GENERIC_READ, share).

Usage: python lockshare.py <path> <seconds> <share>
share: "rw" (others may read and write: an editor), "w" (others may write but not read)
or "none". Prints "locked" once the handle is open. lock.py of 2026-10-09-03 knows only
"r" and "rw"; F-6's lockx.py only "none".
"""
import ctypes
import sys
import time
from ctypes import wintypes

SHARES = {"none": 0, "r": 1, "w": 2, "rw": 3}

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
handle = kernel32.CreateFileW(sys.argv[1], 0x80000000, SHARES[sys.argv[3]], None, 3, 0x80, None)
if handle is None or handle == wintypes.HANDLE(-1).value:
	print("open failed", ctypes.get_last_error(), flush=True)
	sys.exit(1)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
